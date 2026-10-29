"""Todos os nomes/documentos são fictícios; aprovações só de fixtures sintéticas."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest
from tests.fs_support import symlink_ou_skip_1314

from conversor.adapters.document_links_json import RepositorioVinculosJSON
from conversor.application.document_links import candidatos_documentais
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.document_links import IdentidadeOrigem
from conversor.domain.document_scope import EscopoDestinoDiagnostico, EscopoDestinoPersistente
from conversor.export.identifiers import selecionar_perfil
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import analisar,PedidoDiagnostico,PERFIS_SAIDA_PATH,reconhecer,ler
from tests.bbz.test_abrolhos import financeiro,referencia,cadastral,REF,rows
from tests.bbz.conftest import unidade,recibo
from tests.bbz.cadastro_fixtures import ficha
from tests.web.test_mvp import KEY,aguardar

SESSION='a'*64


def repo(tmp):
    root=tmp/'privado';root.mkdir(mode=0o700,exist_ok=True);return RepositorioVinculosJSON(root)


def executar(tmp,r,raw=None,ref=None,cad=None,modo='A',**kw):
    return analisar(raw or financeiro(),PedidoDiagnostico(data_ref=REF,modo=modo),processamento_id='ensaio_sintetico',
        destino=tmp,cadastro=cad,referencia=ref,repositorio_vinculos=r,**kw)


def decidir(r,acao='aprovar',*,id_=None,**kwargs):
    s=r.consultar();reg=s.registros[id_]if id_ else next(iter(s.registros.values()))
    args=dict(acao=acao,revisao_esperada=s.revisao,conteudo_sha256=hash_modelo(reg),responsavel='Revisor sintetico',
        sessao_sha256=SESSION,fundamento='Conferencia sintetica das fontes',confirmar_evidencias=True)
    args.update(kwargs);return r.decidir(reg.id,**args)


def iniciar(tmp,r,*,raw=None,ref=None,cad=None):
    raw=raw or financeiro();return executar(tmp/'com_referencia',r,raw,referencia(raw)if ref is None else ref,cad)


def test_vazio_nao_aprova_nem_exige_inventario_codex(tmp_path):
    r=repo(tmp_path);s=r.consultar();assert s.revisao==0 and not s.registros
    out=executar(tmp_path/'saida',r)
    assert out['resumo']['boletos']==out['resumo']['elegiveis_pela_regua']==1
    assert out['resumo']['dividas_efetivamente_geradas']==0
    assert out['escopo_destino']['resumo_cadastro']['pendentes']==1


def test_candidato_nao_e_aprovacao_e_historico_nao_usa_unidade_id_como_chave(tmp_path):
    r=repo(tmp_path);out=iniciar(tmp_path,r);s=r.consultar();v=next(iter(s.registros.values()))
    assert out['resumo']['dividas_efetivamente_geradas']==1 and v.estado=='candidato'and not v.aprovacao
    assert v.id!=out['decisoes'][0]['unidade_id']and v.id==v.identidade.id
    assert not executar(tmp_path/'sem_template',r)['arquivo_teste_disponivel']
    assert len({e.origem.sha256 for e in v.evidencias})==2


def test_aprovacao_explicita_reutilizada_sem_template_apos_reiniciar(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r,cad=cadastral());decidir(r)
    outro=RepositorioVinculosJSON(r.privado)
    out=executar(tmp_path/'sem_ref',outro,cad=cadastral());withref=executar(tmp_path/'com_ref',outro,ref=referencia(financeiro()),cad=cadastral())
    assert out['resumo']['dividas_efetivamente_geradas']==1
    assert rows(tmp_path/'sem_ref')==rows(tmp_path/'com_ref')
    assert out['escopo_destino']['resumo_cadastro']['comprovadas_cadastro_persistente']==1
    assert out['escopo_destino']['referencia_sha256']is None
    assert out['escopo_destino']['unidades'][0]['evidencias'][0]['sha256']!=sha256(financeiro()).hexdigest()
    assert not out['permite_exportacao_operacional']and not withref['autoriza_cobranca']


def test_novos_recibos_novo_arquivo_sem_trocar_identidade_evidencia_original(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);old=next(iter(r.consultar().registros.values()))
    raw=financeiro([unidade(bloco='D',numero='A00001',recibos=[recibo(id='99000099',due=date(2026,6,1))])])
    out=executar(tmp_path/'outro_mes',r,raw)
    assert out['resumo']['dividas_efetivamente_geradas']==1
    assert out['decisoes'][0]['unidade_id']not in old.recibos_historicos
    assert next(iter(r.consultar().registros.values())).id==old.id


@pytest.mark.parametrize('bloco,numero',[('E','A00001'),('D','A00002'),('D','B00001'),('0','1SS001')])
def test_unidade_nova_ou_torre_semelhante_nao_herda_vinculo(tmp_path,bloco,numero):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    raw=financeiro([unidade(bloco='D',numero='A00001'),unidade(bloco=bloco,numero=numero,recibos=[recibo(id='99000002')])])
    out=executar(tmp_path/'novas',r,raw,modo='B');assert out['resumo']['boletos']==2 and out['resumo']['dividas_efetivamente_geradas']==1
    assert out['escopo_destino']['resumo_cadastro']['pendentes']==1


@pytest.mark.parametrize('codigo',['575','0575','000575'])
def test_chave_preserva_literals_e_normaliza_somente_codigo_origem(tmp_path,codigo):
    a=IdentidadeOrigem(administradora_id='adm_ficticia',empreendimento='EMPRESA FICTICIA',codigo_original='575',bloco_literal='D',unidade_literal='A00001')
    b=IdentidadeOrigem.model_validate(a.model_dump()|{'codigo_original':codigo});assert a.id==b.id and b.codigo_original==codigo
    assert b.id!=IdentidadeOrigem.model_validate(a.model_dump()|{'unidade_literal':'A1'}).id
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);out=executar(tmp_path/'codigo',r,financeiro(codigo=codigo))
    assert out['resumo']['dividas_efetivamente_geradas']==1


@pytest.mark.parametrize('confirmacao,responsavel,fundamento',[(False,'Revisor ficticio','Fundamento'),(True,' ','Fundamento'),(True,'Revisor ficticio',' ')])
def test_nao_aprova_sem_confirmacao_responsavel_e_fundamento(tmp_path,confirmacao,responsavel,fundamento):
    r=repo(tmp_path);iniciar(tmp_path,r)
    with pytest.raises(ErroLeitura):decidir(r,confirmar_evidencias=confirmacao,responsavel=responsavel,fundamento=fundamento)
    assert next(iter(r.consultar().registros.values())).estado=='candidato'


@pytest.mark.parametrize('acao',['revogar','recusar'])
def test_revogacao_e_recusa_nao_sao_contornadas_pela_mesma_referencia(tmp_path,acao):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r,acao)
    for i,ref in enumerate((None,referencia(financeiro()))):
        out=executar(tmp_path/str(i),r,ref=ref,modo='B');assert out['resumo']['dividas_efetivamente_geradas']==out['resumo']['cadastros_adicionais']==0


def test_mudanca_nome_suspende_sem_trocar_titular_ou_liberar_outra_cota(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    raw=financeiro([unidade(bloco='D',numero='A00001')|{'nome':'OUTRO TITULAR INTEIRAMENTE FICTICIO'}])
    out=executar(tmp_path/'mudou',r,raw)
    assert out['resumo']['dividas_efetivamente_geradas']==0
    assert next(iter(r.consultar().registros.values())).motivo=='IDENTIDADE_FINANCEIRA_ALTERADA'
    assert executar(tmp_path/'antigo',r)['resumo']['dividas_efetivamente_geradas']==0


@pytest.mark.parametrize('celula,valor',[('Z2','OUTRA TORRE FICTICIA'),('AD2',999),('D2','OUTRO TITULAR FICTICIO')])
def test_referencia_nova_contraditoria_persiste_revisao(tmp_path,celula,valor):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    ref=referencia(financeiro(),mutar=lambda w,s:setattr(s[celula],'value',valor))
    out=executar(tmp_path/'contradiz',r,ref=ref)
    assert out['resumo']['dividas_efetivamente_geradas']==0
    assert next(iter(r.consultar().registros.values())).estado=='conflitante'
    assert executar(tmp_path/'sem_ref',r)['resumo']['dividas_efetivamente_geradas']==0


def test_revalidacao_por_data_explicita(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r,revalidar_ate=date(2026,10,25))
    assert executar(tmp_path/'venceu',r)['resumo']['dividas_efetivamente_geradas']==0
    assert next(iter(r.consultar().registros.values())).motivo=='VINCULO_EXIGE_REVALIDACAO'


def test_conflito_documental_independente_de_pertencimento_sem_template(tmp_path):
    r=repo(tmp_path);raw=financeiro();ref=referencia(raw,mutar=lambda w,s:setattr(s['C2'],'value','00000000272'))
    iniciar(tmp_path,r,ref=ref,cad=cadastral());s=decidir(r);reg=next(iter(s.registros.values()))
    assert reg.estado=='aprovado'and len(reg.pendencias_documentais)==1
    out=executar(tmp_path/'sem_ref',r,cad=cadastral())
    assert out['resumo']['dividas_efetivamente_geradas']==1 and out['cadastro_bbz']['resumo']['documentos_retidos_revisao']==1
    assert rows(tmp_path/'sem_ref')[1][2]is None and all(v is None for v in rows(tmp_path/'sem_ref')[1][11:24])
    text=r.path.read_text();assert '00000000272'not in text and '00000000191'not in text
    # Uma versão diferente de Cadastro não apaga um conflito histórico ainda pendente.
    out=executar(tmp_path/'outro_cad',r,cad=cadastral([ficha(bloco='D',numero='A00001',documento='00000000272')]))
    assert out['cadastro_bbz']['resumo']['documentos_retidos_revisao']==1


def test_sem_cadastro_informa_retencao_persistente(tmp_path):
    r=repo(tmp_path);raw=financeiro();ref=referencia(raw,mutar=lambda w,s:setattr(s['C2'],'value','00000000272'))
    iniciar(tmp_path,r,ref=ref,cad=cadastral());decidir(r)
    out=executar(tmp_path/'sem_cad',r)
    assert any(o['codigo']=='BBZ_CONFLITO_DOCUMENTAL_PERSISTENTE'for o in out['ocorrencias'])


@pytest.mark.parametrize('adulteracao',['json','estado','assinatura','schema','chave_ausente','evidencia'])
def test_corrupcao_nao_reinicializa_nem_aprova_e_mantem_financeiro_visivel(tmp_path,adulteracao):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    if adulteracao=='json':r.path.write_text('{INVALIDO')
    elif adulteracao=='chave_ausente':r.key.unlink()
    elif adulteracao=='evidencia':next(r.fontes.iterdir()).write_bytes(b'EVIDENCIA ALTERADA')
    else:
        data=json.loads(r.path.read_text())
        if adulteracao=='estado':data['acervo']['eventos'][0]['registro']['estado']='aprovado'
        elif adulteracao=='assinatura':data['assinatura']='0'*64
        else:data['acervo']['versao_contrato']='99.0'
        r.path.write_text(json.dumps(data))
    before=r.path.read_bytes()
    with pytest.raises(ErroLeitura):r.consultar()
    out=executar(tmp_path/'out',r);assert out['resumo']['boletos']==out['resumo']['elegiveis_pela_regua']==1 and out['resumo']['dividas_efetivamente_geradas']==0
    assert r.path.read_bytes()==before


@pytest.mark.parametrize('caminho',['registro.json','chave.bin','escrita.lock','evidencias','cabecas'])
def test_symlinks_rejeitados_sem_escrever_no_destino(tmp_path,caminho):
    r=repo(tmp_path);target=tmp_path/'externo';target.write_text('SENTINELA FICTICIA')
    symlink_ou_skip_1314(r.raiz/caminho,target)
    with pytest.raises(ErroLeitura):r.consultar()
    assert target.read_text()=='SENTINELA FICTICIA'


def test_raiz_link_ancestral_recusados(tmp_path):
    root=tmp_path/'origem';root.mkdir(mode=0o700);link=tmp_path/'link';symlink_ou_skip_1314(link,root,target_is_directory=True)
    with pytest.raises(ErroLeitura):RepositorioVinculosJSON(link/'interno')
    with pytest.raises(RuntimeError,match='AREA_PRIVADA_NAO_PODE_SER_LINK'):criar_app(link/'antes_de_gravar',acesso=KEY)
    assert not(root/'antes_de_gravar').exists()


def test_raiz_git_recusada_sem_depender_de_symlink():
    with pytest.raises(ErroLeitura):RepositorioVinculosJSON(Path(__file__).resolve().parents[2])


def test_concorrencia_aprovacao_cas_apenas_uma_acao_e_aceita(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);s=r.consultar();v=next(iter(s.registros.values()))
    def acao(_):
        try:
            r.decidir(v.id,acao='aprovar',revisao_esperada=s.revisao,conteudo_sha256=hash_modelo(v),responsavel='Revisor sintetico',sessao_sha256=SESSION,fundamento='Ensaio concorrente',confirmar_evidencias=True);return 'ok'
        except ErroLeitura:return 'conflito'
    with ThreadPoolExecutor(max_workers=2)as pool:assert sorted(pool.map(acao,range(2)))==['conflito','ok']
    assert r.consultar().revisao==2


def test_snapshot_alterado_impede_geracao(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);s=decidir(r);decidir(r,'revogar')
    with pytest.raises(ErroLeitura,match='VINCULOS_ALTERADOS_REPROCESSAR'):
        with r.conferir_snapshot(s):pytest.fail('Snapshot antigo aceito')


def test_importacao_idempotente_e_historico_aprovacao_hash_exato(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);s=r.consultar();raw=r.path.read_bytes()
    iniciar(tmp_path/'de_novo',r);assert r.path.read_bytes()==raw
    aprovado=decidir(r);v=next(iter(aprovado.registros.values()))
    assert v.aprovacao.conteudo_aprovado_sha256==hash_modelo(next(iter(s.registros.values())))
    assert aprovado.acervo.eventos[0]==s.acervo.eventos[0]
    assert r.consultar()==aprovado


def test_destinos_incompativeis_nao_podem_ser_aprovados_para_mesma_origem(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);s=decidir(r);v=next(iter(s.registros.values()))
    other=v.model_copy(update={'condominio_destino_id':'cond_ficticio_outro','codigo_destino':'999','estado':'candidato','aprovacao':None})
    with pytest.raises(ErroLeitura,match='DESTINO_CONFLITANTE'):
        r.candidatar((other,),revisao_esperada=s.revisao,responsavel='Ficticio',sessao_sha256=SESSION)


def test_contrato_11_e_manifesto_mantem_fontes_antigas_verificadas(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);out=executar(tmp_path/'sem_ref',r)
    obj=dict(out['escopo_destino']);obj.pop('sha256_conteudo');m=EscopoDestinoPersistente.model_validate(obj)
    assert m.versao.endswith('1.1.0')and m.cadastro_sha256==r.consultar().sha256
    manifest=json.loads((tmp_path/'sem_ref/manifesto_diagnostico.json').read_text())
    assert manifest['escopo_destino']['cadastro_persistente']['cadastro_sha256']==m.cadastro_sha256
    obj['hashes_fontes_verificadas']=[]
    with pytest.raises(ValueError,match='EVIDENCIA_NAO_VERIFICADA'):EscopoDestinoPersistente.model_validate(obj)


def test_modo_b_equivalente_cadastros_uma_vez_sem_divida(tmp_path):
    r=repo(tmp_path);raw=financeiro([unidade(bloco='D',numero='A00001',recibos=[recibo(due=date(2026,7,1)),recibo(id='99000002',due=REF),recibo(id='99000003',due=REF)])])
    iniciar(tmp_path,r,raw=raw);decidir(r)
    for m in ('A','B'):executar(tmp_path/m,r,raw,modo=m)
    assert rows(tmp_path/'A')[1]==rows(tmp_path/'B')[1]
    assert len(rows(tmp_path/'B'))==3 and all(v is None for v in rows(tmp_path/'B')[-1][24:30])


def test_api_autenticada_aprovacao_individual_e_persistencia_servidor(tmp_path):
    root=tmp_path/'mvp';raw=financeiro()
    with TestClient(criar_app(root,acesso=KEY))as c:
        assert c.get('/api/vinculos').status_code==401
        assert c.post('/api/vinculos/'+('0'*64)+'/decisao',json={}).status_code==401
        c.post('/api/session',json={'chave':KEY})
        j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},files={'inadimplencia':('fin.xlsx',raw),'referencia':('ref.xlsx',referencia(raw))}))
        assert j['estado']=='concluido'
        s=c.get('/api/vinculos').json();v=s['registros'][0]
        data={'acao':'aprovar','revisao_esperada':s['revisao'],'conteudo_sha256':v['conteudo_sha256'],'responsavel':'Revisor ficticio','fundamento':'Conferi a unidade ficticia','confirmar_evidencias':True}
        assert c.post('/api/vinculos/'+v['id']+'/decisao',json=data,headers={'Origin':'https://example.invalid'}).status_code==403
        assert c.post('/api/vinculos/'+v['id']+'/decisao',json=data|{'confirmar_evidencias':False}).status_code==409
        assert c.post('/api/vinculos/'+v['id']+'/decisao',json=data).status_code==200
        assert c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').status_code==409
        assert c.post('/api/vinculos/'+v['id']+'/decisao',json=data).status_code==409
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});assert c.get('/api/vinculos').json()['registros'][0]['estado']=='aprovado'
        j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'B'},files={'inadimplencia':('novo.xlsx',raw)}))
        assert j['estado']=='concluido'and j['resultado']['resumo']['dividas_efetivamente_geradas']==1
        assert c.get('/api/processamentos/'+j['id']+'/operacional.xlsx').status_code==409


def test_rollback_de_json_assinado_e_exclusao_nao_apagam_revogacao(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);aprovado=r.path.read_bytes();decidir(r,'revogar');r.path.write_bytes(aprovado)
    with pytest.raises(ErroLeitura):r.consultar()
    # Renomear um checkpoint antigo não pode torná-lo a revisão confiável atual.
    antigo=sorted(r.cabecas.iterdir())[-2].read_bytes()
    (r.cabecas/'99999999999999999999.json').write_bytes(antigo)
    with pytest.raises(ErroLeitura):r.consultar()
    r.path.unlink()
    with pytest.raises(ErroLeitura):r.consultar()


def test_mudanca_de_perfil_evidencia_nova_guardada_para_revisao(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    data=json.loads(PERFIS_SAIDA_PATH.read_text());next(p for p in data if p['condominio_id']=='cond_bbz_abrolhos')['versao']='2.0'
    path=r.privado/'perfil_sintetico.json';path.write_text(json.dumps(data))
    out=executar(tmp_path/'perfil',r,perfis_saida=path)
    assert out['resumo']['dividas_efetivamente_geradas']==0
    v=next(iter(r.consultar().registros.values()));assert v.motivo=='PERFIL_DE_IDENTIFICACAO_ALTERADO'
    assert any(e.papel=='confronto'for e in v.evidencias)


def test_contradicao_conserva_origem_e_hash_da_nova_referencia(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);raw=financeiro()
    ref=referencia(raw,mutar=lambda w,s:setattr(s['Z2'],'value','OUTRA TORRE FICTICIA'))
    executar(tmp_path/'nova_prova',r,ref=ref)
    v=next(iter(r.consultar().registros.values()))
    ev=[e for e in v.evidencias if e.papel=='confronto'and e.origem.sha256==sha256(ref).hexdigest()]
    assert ev and ev[0].origem.linha==2
    assert(r.fontes/(sha256(ref).hexdigest()+'.bin')).read_bytes()==ref


def test_adulteracao_referencia_preservada_bloqueia_mesmo_sem_reenvio(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r)
    v=next(iter(r.consultar().registros.values()));ref=next(e for e in v.evidencias if e.papel=='referencia')
    (r.fontes/(ref.origem.sha256+'.bin')).write_bytes(b'PK ADULTERADO')
    assert executar(tmp_path/'out',r)['resumo']['dividas_efetivamente_geradas']==0


def test_referencia_atual_invalida_nao_libera_registro(tmp_path):
    from conversor.application.document_links import resolver_vinculos
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    ps=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_text()),administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
    scope,_=resolver_vinculos(r,l,financeiro=raw,referencia=b'PK incompleto',perfil=p,perfil_saida=ps,codigo=c,data_ref=REF)
    assert not scope.permitidas


def test_historico_10_ainda_tem_restricao_original(tmp_path):
    from conversor.adapters.scope_reference import delimitar_escopo_destino
    raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia');ps=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_text()),administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
    old=delimitar_escopo_destino(l,referencia=referencia(raw),perfil_saida=ps,perfil=p,codigo_origem=c)
    data=old.model_dump();data['referencia_sha256']='f'*64
    with pytest.raises(ValueError,match='EVIDENCIA_DE_OUTRA_FONTE'):EscopoDestinoDiagnostico.model_validate(data)


def test_schemas_novos_correspondem_aos_contratos():
    from conversor.document_link_schemas import documentos
    for nome,texto in documentos():assert(Path(__file__).resolve().parents[2]/'schemas'/nome).read_text()==texto


def test_falha_atomica_preserva_json_anterior_e_retem_revisao_parcial(tmp_path,monkeypatch):
    import conversor.adapters.document_links_json as storage
    r=repo(tmp_path);iniciar(tmp_path,r);raw=r.path.read_bytes()
    def falhar(*a,**kw):raise OSError('FALHA SINTETICA')
    monkeypatch.setattr(storage,'escrever_json',falhar)
    with pytest.raises(ErroLeitura):decidir(r)
    assert r.path.read_bytes()==raw
    with pytest.raises(ErroLeitura):r.consultar()  # Checkpoint pendente não é tratado como aprovação.


def test_fonte_em_link_com_mesmos_bytes_tambem_e_recusada(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);fonte=next(r.fontes.iterdir());outside=tmp_path/'fonte_externa'
    outside.write_bytes(fonte.read_bytes());outside.chmod(0o600);fonte.unlink();symlink_ou_skip_1314(fonte,outside)
    with pytest.raises(ErroLeitura):r.consultar()


def test_api_reapresentacao_revalida_bytes_originais_e_cas(tmp_path):
    with TestClient(criar_app(tmp_path/'mvp',acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});raw=financeiro()
        j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},
            files={'inadimplencia':('f.xlsx',raw),'referencia':('r.xlsx',referencia(raw))}))
        s=c.get('/api/vinculos').json();data={'revisao_esperada':s['revisao'],'responsavel':'Revisor de teste'}
        url='/api/vinculos/candidatos/'+j['id']
        assert c.post(url,json=data).status_code==200
        assert c.post(url,json=data|{'revisao_esperada':0}).status_code==409
        path=tmp_path/'mvp/processamentos'/j['id']/'referencia.xlsx';path.write_bytes(b'PK ALTERADO')
        assert c.post(url,json=data).status_code==409


def test_perda_de_historico_nao_e_tratada_como_cadastro_novo(tmp_path):
    r=repo(tmp_path);iniciar(tmp_path,r);decidir(r);r.path.unlink()
    out=executar(tmp_path/'perdeu',r,ref=referencia(financeiro()))
    assert out['resumo']['dividas_efetivamente_geradas']==0 and not r.path.exists()


def test_cadastro_fornecido_so_depois_da_aprovacao_reutiliza_prova_fiscal_antiga(tmp_path):
    r=repo(tmp_path);raw=financeiro();ref=referencia(raw,mutar=lambda w,s:setattr(s['C2'],'value','00000000272'))
    iniciar(tmp_path,r,ref=ref);decidir(r)  # Aprova somente o pertencimento, sem Cadastro.
    out=executar(tmp_path/'cadastro_posterior',r,cad=cadastral())
    assert out['resumo']['dividas_efetivamente_geradas']==1
    assert out['cadastro_bbz']['resumo']['documentos_retidos_revisao']==1
    assert rows(tmp_path/'cadastro_posterior')[1][2]is None


def test_fonte_por_caminho_nao_e_aceita_no_lugar_de_hash(tmp_path):
    r=repo(tmp_path)
    with pytest.raises(ErroLeitura):r.ler_fonte('../arquivo')
