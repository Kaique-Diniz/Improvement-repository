"""PSM-01: somente fontes e identidades de laboratório."""
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import re

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.domain.oma import complemento_unidade
from conversor.domain.documents import resolver_documento
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.oma_xlsx import LeitorOMAXLSX,originais
from conversor.readers.oma_cadastro import LeitorCadastroOMA
from conversor.readers.text_support import ContextoLeitura,ErroLeitura
from conversor.web import ephemeral as ep
from conversor.web.service import PERFIS,PedidoDiagnostico,analisar,reconhecer,ler
from tests.web.test_classic_local import boot,ORIGIN,ADDRESS
from tests.web.test_ephemeral import Clock
from .fixtures import financeiro,cadastro,recibo,ficha,dividir,REF,NOME,CPF

PROFILE='parque_santa_monica'


def contexto(role='inadimplencia'):
    return ContextoLeitura('condominio_parque_santa_monica','oma',
        'oma_cadastro_pdf_v1' if role=='cadastro' else 'oma_inadimplencia_xlsx_v1',role,PROFILE)


def ler_fin(raw):return LeitorOMAXLSX().ler(raw,contexto=contexto())


def ler_cad(raw):return LeitorCadastroOMA().ler(raw,contexto=contexto('cadastro'))


def executar(tmp,raw=None,cad=None,mode='A',**kw):
    return analisar(raw if raw is not None else financeiro(),PedidoDiagnostico(data_ref=REF,modo=mode,condominio=PROFILE),
        processamento_id='psm_ficticio',destino=tmp,cadastro=cad,historico=(),estado_historico='nao_disponivel',**kw)


def rows(tmp):
    w=load_workbook(tmp/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:return list(w['Dados'].values)
    finally:w.close()


def test_recibo_com_componentes_negativos_sufixo_e_encargos_separados():
    rec=recibo(componentes=[('DESPESA FICTICIA','100','100','1','2','3'),('ESTORNO FICTICIO','-1,10','-1,10','0','0','0')])
    raw=financeiro([('01','000001',NOME,[rec])]);l=ler_fin(raw);b=l.boletos[0]
    assert len(l.boletos)==1 and len(b.composicao.itens)==2
    assert b.composicao.total_original==Decimal('98.90') and b.composicao.itens[1].valor==Decimal('-1.10')
    assert (b.multa,b.correcao,b.juros)==(Decimal(1),Decimal(2),Decimal(3))
    assert b.identificador=='12345678.A' and originais(l)[b.id]['recibo']=='12345678 A'
    assert b.competencia is None and b.emissao is None and b.emissao_original=='202608'
    assert all(o.sha256==sha256(raw).hexdigest() for o in b.origens)


@pytest.mark.parametrize('bloco,unidade,esperado',[('01','000001','BL01-UNI0001'),('01','00017S','BL01-UNI017S'),('02','000001','BL02-UNI0001'),('01','00017s','BL01-UNI017S')])
def test_codificacao_preserva_sufixo_e_bloco(bloco,unidade,esperado):
    assert complemento_unidade(bloco,unidade)==esperado


@pytest.mark.parametrize('bloco,unidade',[('1','000001'),('01','001'),('01','00017X'),('01','010001'),('01','000017S'),('01','０００００１')])
def test_codificacao_nao_inventa_larguras_ou_aliases(bloco,unidade):
    with pytest.raises(ValueError):complemento_unidade(bloco,unidade)


@pytest.mark.parametrize('dias,expected',[(59,0),(60,0),(61,1),(90,1),(91,1)])
def test_prazo_estrito_vencimento_e_nao_emissao(tmp_path,dias,expected):
    r=executar(tmp_path,financeiro([('01','000001',NOME,[recibo(dias=dias)])]))
    assert r['resumo']['dividas_efetivamente_geradas']==expected
    assert r['decisoes'][0]['vencimento']==(REF-timedelta(days=dias)).isoformat()
    assert not r['autoriza_cobranca'] and not r['permite_exportacao_operacional']


@pytest.mark.parametrize('kind',['posicao','recibo_total','unidade_total','geral_total','resumo','resumo_incompleto','formula','data','sem_fechamento','sem_total_unidade','sem_componente','apos_fim','aba','identidade','coluna'])
def test_estrutura_ambigua_ou_totais_divergentes_bloqueiam(kind):
    def change(w,s):
        indexes={name:[i for i,row in enumerate(s,1) if any(c.value==name for c in row)] for name in ('Total do recibo:','Total da unidade:','Total acumulado:')}
        if kind=='posicao':s['B1']='Inadimplência\nPosição em: 99/99/2026'
        if kind=='recibo_total':s.cell(indexes['Total do recibo:'][0],7,'999')
        if kind=='unidade_total':s.cell(indexes['Total da unidade:'][0],7,'999')
        if kind=='geral_total':s.cell(indexes['Total acumulado:'][0],7,'999')
        if kind=='resumo':s.cell(indexes['Total da unidade:'][-1],7,'999')
        if kind=='resumo_incompleto':s.delete_rows(s.max_row)
        if kind=='formula':s['G6']='=1+1'
        if kind=='data':s['B6']='99/99/2026'
        if kind=='sem_fechamento':s.delete_rows(indexes['Total do recibo:'][0])
        if kind=='sem_total_unidade':s.delete_rows(indexes['Total da unidade:'][0])
        if kind=='sem_componente':s['E6']=''
        if kind=='apos_fim':s.append(['CONTEUDO FICTICIO'])
        if kind=='aba':s.title='Outra'
        if kind=='identidade':s['A2']='Condomínio: OUTRO CONDOMINIO FICTICIO'
        if kind=='coluna':s['M6']='DADO EXTRA FICTICIO'
    with pytest.raises(ErroLeitura):ler_fin(financeiro(mutar=change))


def test_hash_homologado_exige_estrutura_e_identidade(monkeypatch):
    raw=financeiro();monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    assert reconhecer(raw)[0]['id']==PROFILE
    with pytest.raises(ErroLeitura,match='CONFLITANTE'):reconhecer(raw,perfil_informado='passaredo')
    bad=financeiro(mutar=lambda w,s:s.__setitem__('G6','=1+1'))
    monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],'inadimplencia',sha256(bad).hexdigest())
    with pytest.raises(ErroLeitura):reconhecer(bad)


def test_ordem_parcelas_contrato_30_e_modo_b_nao_duplica(tmp_path):
    group=[recibo('11111111',90),recibo('11111112 A',61),recibo('11111113',59),recibo('11111114',60)]
    raw=financeiro([('01','000001',NOME,group),('01','00017S',NOME,[recibo('11111115',61)])])
    a=executar(tmp_path/'a',raw);b=executar(tmp_path/'b',raw,mode='B')
    output=rows(tmp_path/'a');extended=rows(tmp_path/'b')
    assert a['resumo']['dividas_efetivamente_geradas']==3 and len(output)==4
    assert len(extended)==5 # Uma única linha cadastral, mesmo com dois recibos não elegíveis.
    assert len(output[0])==30 and output[0][26]=='NM_DIVIDA_CEDENTE'
    assert [r[27] for r in output[1:3]]==[1,2]
    assert output[1][26].startswith('COTA ') and output[1][29]==100.1
    assert output[1][1]=='BL01-UNI0001-PARQUE SANTA MONICA'
    assert output[-1][6]=='BL01-UNI017S'
    canonical=json.loads((tmp_path/'a'/'canonico.json').read_text(encoding='utf-8'))
    assert len(canonical['boletos'])==5 and all(b['competencia'] is None for b in canonical['boletos'])


def test_dois_blocos_com_mesma_unidade_tem_ids_distintos():
    lote=ler_fin(financeiro([('01','000001',NOME,[recibo()]),('02','000001',NOME,[recibo()])]))
    assert len({b.id for b in lote.boletos})==2 and len({u.id for u in lote.unidades})==2


def test_pdf_continuidade_cabecalho_contatos_por_papel_e_administrativo():
    body=ficha(bloco='01',numero='000001',nome=NOME,documento=CPF,contatos=['Celular - 0123-4567','E-mail - cliente@example.invalid'])
    body += [(240,300,'Telefone/e-mail da unidade'),(24,288,'E-mail - unidade@example.invalid')]
    partes=dividir(body,2)
    partes.append(ficha(bloco='0',numero='ADMINI',nome='REGISTRO ADMINISTRATIVO FICTICIO'))
    lote=ler_cad(cadastro(partes,total=2))
    assert len(lote.unidades)==2
    pessoa=next(p for p in lote.pessoas if p.nome==NOME)
    assert resolver_documento(pessoa).valor==CPF
    assert pessoa.contato.telefones[0].ddd=='' and pessoa.contato.telefones[0].numero=='01234567'
    assert pessoa.contato.emails==('cliente@example.invalid',)
    fichas=[json.loads(r.valores_originais[0]) for r in lote.ressalvas if r.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL']
    assert any(p['papel']=='unidade' and p['emails'] for f in fichas for p in f['participantes'])
    assert any(len(f['cabecalhos'])==2 for f in fichas)


@pytest.mark.parametrize('nome,documento,retido,exportado',[(NOME,CPF,0,CPF),(NOME,'00000000000',1,None),(NOME,'texto arbitrario '+CPF,1,None),(NOME,'',1,None),('Pessoa Ficticia Divergente',CPF,1,None),('Pessoa Ficticia A / Pessoa Ficticia B',CPF,1,None)])
def test_associacao_a1_documento_e_multiplicidade(tmp_path,nome,documento,retido,exportado):
    finance_name=nome if '/' in nome else NOME
    raw=financeiro([('01','000001',finance_name,[recibo()])])
    cad=cadastro([ficha(bloco='01',numero='000001',nome=nome,documento=documento)])
    result=executar(tmp_path,raw,cad)
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['cadastro_'+PROFILE]['associacoes_retidas']==retido
    assert rows(tmp_path)[1][2]==exportado
    if retido:
        assert rows(tmp_path)[1][12] is None and rows(tmp_path)[1][21] is None
    if documento.startswith('texto'):
        assert documento in (tmp_path/'canonico.json').read_text(encoding='utf-8')


def test_pdf_s_minusculo_equivale_sem_apagar_original(tmp_path):
    raw=financeiro([('01','00017S',NOME,[recibo()])])
    cad=cadastro([ficha(bloco='01',numero='00017s',nome=NOME,documento=CPF)])
    assert ler_cad(cad).unidades[0].unidade_original=='00017s'
    assert executar(tmp_path,raw,cad)['cadastro_'+PROFILE]['documentos_validos_vinculados']==1
    assert rows(tmp_path)[1][2]==CPF


def test_cadastro_outro_condominio_nao_e_aceito(tmp_path):
    with pytest.raises(ErroLeitura):executar(tmp_path,cad=cadastro(nome='OUTRO CONDOMINIO FICTICIO'))


def test_pdf_locatario_explicitamente_vazio_nao_atribui_identidade():
    body=ficha(bloco='01',numero='000001',nome=NOME,locatario=True)
    body=[(x,y,'Locatário:') if t.startswith('Locatário:') else (x,y,t) for x,y,t in body]
    assert len(ler_cad(cadastro([body])).pessoas)==1


def test_fluxo_classico_confirmacao_csrf_sessao_previa_download_descarte(tmp_path,monkeypatch):
    app=ep.criar_app_efemero(area_temporaria=tmp_path,relogio=Clock());raw=financeiro()
    with TestClient(app,base_url=ORIGIN) as c:
        boot(c)
        files={'inadimplencia':('nao-e-identidade.xlsx',raw)}
        p=c.post('/api/identificar',files=files)
        assert p.status_code==409 and [x['id'] for x in p.json()['candidatos']]==[PROFILE]
        monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
        p=c.post('/api/identificar',files=files);assert p.status_code==200 and p.json()['perfil']==PROFILE
        token=p.json()['contexto']
        assert c.put('/api/contextos/'+token+'/configuracao',json={'revisao_esperada':0,'endereco':ADDRESS,'mapeamentos':[]}).status_code==200
        for mode in ('A','B'):
            r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':mode,'contexto':token},files=files|{'cadastro':('cadastro.pdf',cadastro())})
            assert r.status_code==200
            data=r.json();assert data['cadastro_'+PROFILE]['documentos_validos_vinculados']==1
            url='/api/conversoes/'+data['id']
            assert c.get(url+'/operacional.xlsx').status_code==409
            assert c.get(url+'/excel',headers={'origin':'http://hostil.invalid'}).status_code==403
            other=TestClient(app,base_url=ORIGIN)
            try:
                boot(other);assert other.get(url+'/excel').status_code==404
            finally:
                other.close()
            detail=c.get(url+'/detalhes').json();assert len(detail['previa_template']['colunas'])==30
            assert c.get(url+'/excel').status_code==200 and c.get(url+'/detalhes').status_code==404
            assert not list(app.state.ciclo.root.iterdir())
        assert c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A'},files=files,headers={'x-csrf-token':'falso'}).status_code==403
        r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A'},files=files)
        assert r.status_code==200
        app.state.ciclo.relogio.now+=901;app.state.ciclo.limpar()
        assert not app.state.ciclo.results


def test_cnpj_empresarial_concordante_e_documentos_conflitantes(tmp_path):
    nome='Empresa Totalmente Ficticia Alfa E Beta Ltda'
    raw=financeiro([('01','000001',nome,[recibo()])])
    cad=cadastro([ficha(bloco='01',numero='000001',nome=nome,documento='11222333000181')])
    assert executar(tmp_path/'ok',raw,cad)['cadastro_'+PROFILE]['associacoes_retidas']==0
    assert rows(tmp_path/'ok')[1][2]=='11222333000181'
    cad=cadastro([ficha(bloco='01',numero='000001',nome=nome,documento='11222333000181',segundo_documento=CPF)])
    assert executar(tmp_path/'conflito',raw,cad)['cadastro_'+PROFILE]['associacoes_retidas']==1
    assert rows(tmp_path/'conflito')[1][2] is None


@pytest.mark.parametrize('telefone,expected',[('0123-4567','01234567'),('123456789','123456789'),('12345678901234',None),('texto 01234567',None)])
def test_telefone_nao_extrai_fragmentos_maiores(tmp_path,telefone,expected):
    cad=cadastro([ficha(bloco='01',numero='000001',nome=NOME,contatos=['Celular - '+telefone])])
    executar(tmp_path,cad=cad)
    row=rows(tmp_path)[1]
    assert row[11] is None and row[12]==expected


@pytest.mark.parametrize('protecao,status',[('permitida',200),('negada',422),('senha',422)])
def test_pdf_protegido_so_senha_vazia_e_extracao_autorizada(tmp_path,protecao,status):
    app=ep.criar_app_efemero(area_temporaria=tmp_path)
    with TestClient(app,base_url=ORIGIN) as c:
        boot(c)
        r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':PROFILE},
            files={'inadimplencia':('fonte.xlsx',financeiro()),'cadastro':('cadastro.pdf',cadastro(protecao=protecao))})
        assert r.status_code==status
        if status==200:assert r.json()['cadastro_'+PROFILE]['documentos_validos_vinculados']==1
        else:assert not app.state.ciclo.results
        assert not list(app.state.ciclo.root.iterdir())


def test_pdf_protegido_nao_habilita_outro_perfil(tmp_path):
    from tests.passaredo.fixtures import financeiro as passaredo
    app=ep.criar_app_efemero(area_temporaria=tmp_path)
    with TestClient(app,base_url=ORIGIN) as c:
        boot(c)
        r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':'passaredo'},
            files={'inadimplencia':('fonte.xlsx',passaredo()),'cadastro':('cadastro.pdf',cadastro(protecao='permitida'))})
        assert r.status_code==422 and not app.state.ciclo.results


def test_revisao_cadastral_nao_funde_numeros_de_blocos_distintos(tmp_path):
    raw=financeiro([('01','000001',NOME,[recibo()]),('02','000001',NOME,[recibo()])])
    cad=cadastro([ficha(bloco=b,numero='000001',nome='Pessoa Ficticia Divergente') for b in ('01','02')],total=2)
    result=executar(tmp_path,raw,cad)
    assert result['resumo']['dividas_efetivamente_geradas']==2
    assert result['cadastro_'+PROFILE]['unidades_em_revisao']==2
    assert {r['unidade'] for r in result['revisao_cadastral_'+PROFILE]}=={'01/000001','02/000001'}


def test_descricao_bbz_com_termo_monetario_nao_vira_familia_oma():
    from tests.bbz.conftest import planilha,unidade,recibo as recibo_bbz
    raw=planilha([unidade(recibos=[recibo_bbz(componentes=[('Atualização Monetária FICTICIA','100.00')])])])
    profile,code,reader=reconhecer(raw)
    assert profile['id']=='nova_york' and reader=='bbz_inadimplencia_xlsx_v1'
