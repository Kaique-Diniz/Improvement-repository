"""Reabertura explícita: somente vínculos e evidências inteiramente sintéticos."""
from concurrent.futures import ThreadPoolExecutor
import json

from fastapi.testclient import TestClient
import pytest

from conversor.adapters.document_links_json import RepositorioVinculosJSON
from conversor.application.document_links import comprovar_reabertura
from conversor.domain.billing_rules import hash_modelo
from conversor.export.identifiers import selecionar_perfil
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import PERFIS_SAIDA_PATH, reconhecer, ler
from tests.bbz.test_persistent_links import repo, iniciar, decidir, executar, SESSION
from tests.bbz.test_abrolhos import financeiro, referencia, cadastral, REF, rows
from tests.bbz.conftest import unidade, recibo
from tests.web.test_mvp import KEY, aguardar


def prova_original(r, id_=None):
    s=r.consultar();v=s.registros[id_]if id_ else next(iter(s.registros.values()))
    hashes={p:next(e.origem.sha256 for e in v.evidencias if e.papel==p)for p in ('financeiro','referencia')}
    raw=r.ler_fonte(hashes['financeiro']);ref=r.ler_fonte(hashes['referencia'])
    p,c,f=reconhecer(raw);lote,_=ler(raw,p,c,f,'inadimplencia')
    saida=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_bytes()),
        administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
    return comprovar_reabertura(r,v,lote,financeiro=raw,referencia=ref,perfil=p,perfil_saida=saida,codigo=c)


def revogado(tmp):
    r=repo(tmp);iniciar(tmp,r);decidir(r);decidir(r,'revogar');return r


def test_reabre_sem_aprovar_preserva_historico_checkpoints_fontes_e_outros_vinculos(tmp_path):
    raw=financeiro([unidade(bloco='D',numero='A00001'),
        unidade(bloco='E',numero='A00002',recibos=[recibo(id='99000002')])])
    r=repo(tmp_path);iniciar(tmp_path,r,raw=raw)
    for id_ in r.consultar().registros:decidir(r,id_=id_)
    id_,outro_id=r.consultar().registros;decidir(r,'revogar',id_=id_)
    antes=r.consultar();outro=antes.registros[outro_id];v=antes.registros[id_]
    preservados={p:p.read_bytes()for p in [r.key,*r.cabecas.iterdir(),*r.fontes.iterdir()]}
    novo=decidir(r,'reabrir',id_=id_,comprovacao_reabertura=prova_original(r,id_))
    candidato=novo.registros[id_]
    assert candidato.estado=='candidato'and candidato.aprovacao is None
    assert candidato.versao==v.versao+1 and candidato.evidencias==v.evidencias
    assert candidato.registrado_em==v.registrado_em and candidato.recibos_historicos==v.recibos_historicos
    assert novo.acervo.eventos[:-1]==antes.acervo.eventos and novo.acervo.eventos[-1].acao=='reabrir'
    assert novo.registros[outro_id]==outro
    assert all(p.read_bytes()==b for p,b in preservados.items())
    r=RepositorioVinculosJSON(r.privado);assert r.consultar()==novo
    assert executar(tmp_path/'antes_nova_aprovacao',r,raw)['resumo']['dividas_efetivamente_geradas']==1
    aprovado=decidir(r,id_=id_)
    assert aprovado.registros[id_].aprovacao.conteudo_aprovado_sha256==hash_modelo(candidato)
    assert executar(tmp_path/'depois_nova_aprovacao',r,raw)['resumo']['dividas_efetivamente_geradas']==2
    assert aprovado.registros[outro_id]==outro


@pytest.mark.parametrize('falha',['confirmacao','responsavel','fundamento','prova','revisao','hash','validade'])
def test_reabertura_exige_confirmacao_justificativa_prova_e_cas(tmp_path,falha):
    r=revogado(tmp_path);before=r.path.read_bytes();args={'comprovacao_reabertura':prova_original(r)}
    args.update({'confirmacao':{'confirmar_evidencias':False},'responsavel':{'responsavel':' '},
        'fundamento':{'fundamento':' '},'prova':{'comprovacao_reabertura':None},
        'revisao':{'revisao_esperada':0},'hash':{'conteudo_sha256':'0'*64},
        'validade':{'revalidar_ate':REF}}[falha])
    with pytest.raises(ErroLeitura):decidir(r,'reabrir',**args)
    assert r.path.read_bytes()==before


@pytest.mark.parametrize('estado',['candidato','aprovado','recusado','pendente','conflitante'])
def test_nao_reabre_outros_estados_nem_recusa_definitiva(tmp_path,estado):
    r=repo(tmp_path);iniciar(tmp_path,r)
    if estado=='aprovado':decidir(r)
    elif estado=='recusado':decidir(r,'recusar')
    elif estado in ('pendente','conflitante'):
        v=next(iter(r.consultar().registros.values()))
        r.observar(v.id,motivo='DESTINO_PERSISTENTE_CONFLITANTE'if estado=='conflitante'else'IDENTIDADE_FINANCEIRA_ALTERADA')
    before=r.path.read_bytes()
    with pytest.raises(ErroLeitura):decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
    assert r.path.read_bytes()==before


@pytest.mark.parametrize('campo,valor',[
    ('condominio_destino_id','cond_outro_sintetico'),('codigo_destino','999'),
    ('nome_financeiro_hmac','b'*64),('perfil_sha256','c'*64),('perfil_versao','999.0'),
    ('recibos_historicos',('recibo_inexistente',)),
])
def test_prova_incompativel_nao_pode_reabrir(tmp_path,campo,valor):
    r=revogado(tmp_path);before=r.path.read_bytes();p=prova_original(r).model_copy(update={campo:valor})
    with pytest.raises(ErroLeitura,match='CONTEXTO_ATUAL_INCOMPATIVEL'):
        decidir(r,'reabrir',comprovacao_reabertura=p)
    assert r.path.read_bytes()==before


@pytest.mark.parametrize('momento',['antes','depois'])
@pytest.mark.parametrize('motivo',['DESTINO_PERSISTENTE_CONFLITANTE','IDENTIDADE_FINANCEIRA_ALTERADA',
    'PERFIL_DE_IDENTIFICACAO_ALTERADO','REFERENCIA_ATUAL_CONTRADITORIA_OU_NAO_CONCILIADA','VINCULO_EXIGE_REVALIDACAO'])
def test_restricoes_antes_ou_depois_da_revogacao_continuam_bloqueantes(tmp_path,momento,motivo):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);v=next(iter(r.consultar().registros.values()))
    if momento=='depois':decidir(r,'revogar')
    r.observar(v.id,motivo=motivo)
    if momento=='antes':decidir(r,'revogar')
    assert next(iter(r.consultar().registros.values())).estado=='revogado'
    before=r.path.read_bytes()
    with pytest.raises(ErroLeitura,match='RESTRICAO_EXIGE_NOVA_COMPROVACAO'):
        decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
    assert r.path.read_bytes()==before


def test_processar_referencia_contraditoria_apos_revogar_preserva_restricao(tmp_path):
    r=revogado(tmp_path)
    ref=referencia(financeiro(),mutar=lambda w,s:setattr(s['Z2'],'value','TORRE FICTICIA DIFERENTE'))
    executar(tmp_path/'confronto',r,ref=ref)
    v=next(iter(r.consultar().registros.values()))
    assert v.estado=='revogado'and any(e.papel=='confronto'for e in v.evidencias)
    with pytest.raises(ErroLeitura):decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))


@pytest.mark.parametrize('adulteracao',['fonte','chave','json','checkpoint'])
def test_adulteracao_rejeita_reabertura_sem_reparar_arquivos(tmp_path,adulteracao):
    r=revogado(tmp_path);proof=prova_original(r);s=r.consultar();v=next(iter(s.registros.values()))
    path={'fonte':next(r.fontes.iterdir()),'chave':r.key,'json':r.path,
          'checkpoint':sorted(r.cabecas.iterdir())[-1]}[adulteracao]
    path.write_bytes(b'ADULTERACAO SINTETICA');before={p:p.read_bytes()for p in (r.path,r.key,path)}
    with pytest.raises(ErroLeitura):
        r.decidir(v.id,acao='reabrir',revisao_esperada=s.revisao,conteudo_sha256=hash_modelo(v),
            responsavel='Revisor ficticio',sessao_sha256=SESSION,fundamento='Ensaio sintetico',
            confirmar_evidencias=True,comprovacao_reabertura=proof)
    assert all(p.read_bytes()==b for p,b in before.items())


def test_reabertura_concorrente_aceita_so_um_evento(tmp_path):
    r=revogado(tmp_path);proof=prova_original(r);s=r.consultar();v=next(iter(s.registros.values()))
    def acao(_):
        try:
            r.decidir(v.id,acao='reabrir',revisao_esperada=s.revisao,conteudo_sha256=hash_modelo(v),
                responsavel='Revisor ficticio',sessao_sha256=SESSION,fundamento='Reabertura sintetica',
                confirmar_evidencias=True,comprovacao_reabertura=proof)
            return 'ok'
        except ErroLeitura:return 'conflito'
    with ThreadPoolExecutor(max_workers=2)as pool:assert sorted(pool.map(acao,range(2)))==['conflito','ok']
    assert r.consultar().revisao==s.revisao+1
    assert next(iter(r.consultar().registros.values())).estado=='candidato'


def test_nova_aprovacao_apos_reabrir_nao_remove_documentos_e_contatos_retidos(tmp_path):
    r=repo(tmp_path);raw=financeiro()
    ref=referencia(raw,mutar=lambda w,s:setattr(s['C2'],'value','00000000272'))
    iniciar(tmp_path,r,ref=ref,cad=cadastral());decidir(r);decidir(r,'revogar')
    antes=next(iter(r.consultar().registros.values())).pendencias_documentais
    decidir(r,'reabrir',comprovacao_reabertura=prova_original(r));decidir(r)
    assert next(iter(r.consultar().registros.values())).pendencias_documentais==antes
    out=executar(tmp_path/'sem_ref',r,cad=cadastral())
    assert out['resumo']['dividas_efetivamente_geradas']==1
    assert out['cadastro_bbz']['resumo']['documentos_retidos_revisao']==1
    assert rows(tmp_path/'sem_ref')[1][2]is None
    assert all(v is None for v in rows(tmp_path/'sem_ref')[1][11:24])
    assert not out['permite_exportacao_operacional']and not out['autoriza_cobranca']


def test_candidato_reaberto_pode_ser_recusado_ou_novamente_revogado(tmp_path):
    r=revogado(tmp_path);decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
    decidir(r,'revogar');decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
    decidir(r,'recusar');assert next(iter(r.consultar().registros.values())).estado=='recusado'
    with pytest.raises(ErroLeitura):decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))


def test_revogacao_exige_confirmacao_e_nao_muda_acervo_se_cancelada(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);before=r.path.read_bytes()
    with pytest.raises(ErroLeitura,match='REVOGACAO_EXIGE_CONFIRMACAO_EXPLICITA'):
        decidir(r,'revogar',confirmar_evidencias=False)
    assert r.path.read_bytes()==before


def test_api_reabertura_autenticada_cas_conferencia_e_aprovacao_separada(tmp_path):
    root=tmp_path/'mvp';raw=financeiro()
    with TestClient(criar_app(root,acesso=KEY))as c:
        assert c.post('/api/vinculos/'+('0'*64)+'/decisao',json={'acao':'reabrir'}).status_code==401
        c.post('/api/session',json={'chave':KEY})
        j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},
            files={'inadimplencia':('f.xlsx',raw),'referencia':('r.xlsx',referencia(raw))}))
        assert j['estado']=='concluido'
        def payload(acao):
            s=c.get('/api/vinculos').json();v=s['registros'][0]
            return '/api/vinculos/'+v['id']+'/decisao',dict(acao=acao,revisao_esperada=s['revisao'],
                conteudo_sha256=v['conteudo_sha256'],responsavel='Revisor ficticio',fundamento='Conferencia sintetica',confirmar_evidencias=True)
        for acao in ('aprovar','revogar'):
            url,data=payload(acao);assert c.post(url,json=data).status_code==200
        url,data=payload('reabrir')
        assert c.post(url,json=data,headers={'Origin':'https://example.invalid'}).status_code==403
        assert c.post(url,json=data|{'confirmar_evidencias':False}).status_code==409
        assert c.post(url,json=data|{'fundamento':' '}).status_code==409
        assert c.post(url,json=data|{'comprovacao_reabertura':{}}).status_code==422
        novo=c.post(url,json=data);assert novo.status_code==200
        v=novo.json()['registros'][0];assert v['estado']=='candidato'and v['aprovacao']is None
        assert c.post(url,json=data).status_code==409
        url,data=payload('aprovar');assert c.post(url,json=data|{'confirmar_evidencias':False}).status_code==409
        assert c.post(url,json=data).status_code==200
        assert [e['acao']for e in c.get('/api/vinculos').json()['historico']]==['candidatar','aprovar','revogar','reabrir','aprovar']
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        assert c.get('/api/vinculos').json()['registros'][0]['estado']=='aprovado'


def test_api_reabertura_rejeita_perfil_atual_modificado(tmp_path):
    root=tmp_path/'mvp';root.mkdir(mode=0o700)
    r=RepositorioVinculosJSON(root);iniciar(tmp_path,r);decidir(r);s=decidir(r,'revogar')
    v=next(iter(s.registros.values()));profiles=json.loads(PERFIS_SAIDA_PATH.read_bytes())
    next(p for p in profiles if p['condominio_id']=='cond_bbz_abrolhos')['versao']='999.0'
    (root/'perfis_saida.json').write_text(json.dumps(profiles));before=r.path.read_bytes()
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        res=c.post('/api/vinculos/'+v.id+'/decisao',json=dict(acao='reabrir',revisao_esperada=s.revisao,
            conteudo_sha256=hash_modelo(v),responsavel='Revisor ficticio',fundamento='Conferencia sintetica',confirmar_evidencias=True))
        assert res.status_code==409 and res.json()['detail']=='REABERTURA_CONTEXTO_ATUAL_INCOMPATIVEL'
    assert r.path.read_bytes()==before
