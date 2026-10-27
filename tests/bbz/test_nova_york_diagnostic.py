from datetime import date
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest
from pydantic import ValidationError

from conversor.web.app import criar_app
from conversor.web.service import analisar,PedidoDiagnostico,reconhecer
from conversor.readers.text_support import ErroLeitura
from tests.web.test_mvp import KEY,aguardar
from tests.bbz.conftest import recibo,unidade


def caso(xlsx):
    return xlsx([unidade(recibos=[recibo(id='99000001',due=date(2026,8,26)),recibo(id='99000002',due=date(2026,8,27))]),
                 unidade(numero='000002',recibos=[recibo(id='99000003',due=date(2026,9,1))])])


@pytest.mark.parametrize('modo,dividas,cadastros',[('A',1,0),('B',1,2)])
def test_exatamente_61_dias_e_modo_B_uma_linha_por_unidade(xlsx,tmp_path,modo,dividas,cadastros):
    r=analisar(caso(xlsx),PedidoDiagnostico(data_ref='2026-10-26',modo=modo),processamento_id='sintetico',destino=tmp_path)
    assert r['resumo']['boletos']==3 and r['resumo']['dividas_efetivamente_geradas']==dividas
    assert r['resumo']['cadastros_adicionais']==cadastros and not r['permite_exportacao_operacional']and not r['autoriza_cobranca']
    decisions={d['boleto']:d for d in r['decisoes']}
    assert decisions['99000001']['situacao']=='elegivel'
    assert decisions['99000002']['situacao']=='nao_elegivel'and decisions['99000003']['situacao']=='nao_elegivel'
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');s=w['Dados'];rows=list(s.values)[1:]
    assert s.max_column==30 and s['AA1'].value=='NM_DIVIDA_CEDENTE'and s['AB2'].value==1
    assert s['AD2'].value==100 and s['B2'].value=='BL-UNI0001-884'and s['G2'].value=='BL-UNI0001'
    assert len([x for x in rows if all(v is None for v in x[24:30])])==cadastros
    assert len({i['unidade_id']for i in r['linhas_teste']if i['tipo']=='cadastral'})==cadastros
    assert all(not d['pendencias_documentais']for d in r['decisoes'])and all(row[2]is None for row in rows)
    w.close()


@pytest.mark.parametrize('marcador',[None,'A','AJ','J','AE'])
def test_centavo_e_marcadores_bbz_nao_herdam_exclusao_tree(xlsx,tmp_path,marcador):
    blob=xlsx([unidade(recibos=[recibo(id='99000001',marcador=marcador),recibo(id='99000002',componentes=[('FICTICIO','0.01')],encargos=('1','2','3'))])])
    r=analisar(blob,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert r['resumo']['dividas_efetivamente_geradas']==2 and not any(d['veto_coletivo']for d in r['decisoes'])
    assert not any('tree_'in a['regra_id']for d in r['decisoes']for a in d['regras_avaliadas'])
    assert r['decisoes'][1]['valor']=='0.01'


@pytest.mark.parametrize('codigo,nome',[('884','CONDOMINIO NOVA YORK PENTHOUSES'),('999','CONDOMINIO FICTICIO'),('287','OUTRO NOME FICTICIO')])
def test_identidade_interna_nao_e_nome_do_arquivo(xlsx,codigo,nome):
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):reconhecer(xlsx(codigo=codigo,nome=nome))


def test_selecao_condominio_divergente_nao_processa(xlsx,tmp_path):
    with pytest.raises(ErroLeitura,match='SELECAO_DIVERGENTE_DO_CABECALHO'):
        analisar(xlsx(),PedidoDiagnostico(data_ref='2026-10-26',modo='A',condominio='plaza'),processamento_id='sintetico',destino=tmp_path)


@pytest.mark.parametrize('data_ref',[None,'','hoje','26/10/2026','2026-02-30'])
def test_data_referencia_explicita_e_valida(data_ref):
    with pytest.raises(ValidationError):PedidoDiagnostico(data_ref=data_ref,modo='A')


def test_zero_nao_e_liberado_como_divida(xlsx,tmp_path):
    r=analisar(xlsx([unidade(recibos=[recibo(componentes=[('FICTICIO','0.00')])])]),
        PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert r['decisoes'][0]['situacao']=='revisao'and'VALOR_ORIGINAL_NAO_POSITIVO'in r['decisoes'][0]['bloqueios']
    assert r['resumo']['dividas_efetivamente_geradas']==0 and not(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').exists()


def test_upload_comum_xlsx_nome_irrelevante_endereco_e_isolamento(xlsx,tmp_path):
    root=tmp_path/'privado';endereco={'logradouro':'RUA APENAS FICTICIA','numero':'001','cep':'00000001','bairro':'BAIRRO FICTICIO','cidade':'CIDADE FICTICIA','uf':'SP'}
    with TestClient(criar_app(root,acesso=KEY))as c:
        assert c.post('/api/session',json={'chave':KEY}).status_code==200
        assert c.put('/api/condominios/adm_bbz/cond_bbz_nova_york/endereco',json={'endereco':endereco,'versao_esperada':0}).status_code==200
        job=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'B'},files={'inadimplencia':('NOME_ENGANOSO.pdf',caso(xlsx),'application/octet-stream')}))
        assert job['estado']=='concluido'and(root/'processamentos'/job['id']/'inadimplencia.xlsx').exists()
        assert job['resultado']['resumo']['dividas_efetivamente_geradas']==1
        assert c.get('/api/processamentos/'+job['id']+'/operacional.xlsx').status_code==409
        w=load_workbook(BytesIO(c.get('/api/processamentos/'+job['id']+'/arquivo-teste.xlsx').content));rows=list(w['Dados'].values)[1:]
        assert len(rows)==3 and all(row[4]==endereco['logradouro']and row[7]=='00000001'for row in rows)
        assert all(w['Dados'].cell(i,8).data_type=='s'for i in range(2,5))
        assert not c.get('/api/condominios/adm_fl/cond_fl/endereco').json()['cadastrado']
        assert not c.get('/api/condominios/adm_habita/cond_habita/endereco').json()['cadastrado'];w.close()
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});assert c.get('/api/condominios/adm_bbz/cond_bbz_nova_york/endereco').json()['endereco']==endereco|{'complemento':''}


def test_bbz_rejeita_cadastro_pdf_de_outra_administradora(xlsx,tmp_path):
    from conversor.web.demo import documentos_demo
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):
        analisar(xlsx(),PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path,
                 cadastro=documentos_demo()['cadastro'])


def test_referencia_historica_por_cabecalho_30_colunas_sem_alterar_saida(xlsx,tmp_path):
    raw=caso(xlsx);base=tmp_path/'base'
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=base)
    wb=load_workbook(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');wb.active.title='HISTORICO FICTICIO';out=BytesIO();wb.save(out);wb.close()
    after=tmp_path/'depois'
    rr=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=after,referencia=out.getvalue())
    assert rr['comparacao']['resumo']['valores_coincidentes']==1
    assert(after/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()


def test_regra_sem_vigencia_comprovada_nao_ganha_data_inventada(xlsx,tmp_path):
    from conversor.web.service import PERFIS
    assert PERFIS['nova_york']['vigente_de']is None and PERFIS['nova_york']['vigente_ate']is None
    r=analisar(xlsx(),PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert not r['aprovacao_formal_plano']and not r['autoriza_cobranca']


@pytest.mark.parametrize('escopo',['arquivo','registro'])
def test_critico_anterior_bbz_nao_e_contornado_por_prazo(xlsx,tmp_path,escopo):
    from conversor.domain.canonical import Ocorrencia
    from conversor.web.service import ler
    blob=xlsx();p,c,l=reconhecer(blob);lote,_=ler(blob,p,c,l,'inadimplencia')
    oc=Ocorrencia(id='critico_sintetico',processamento_id='execucao_anterior',codigo='RETENCAO_FICTICIA',
        gravidade='critico',escopo=escopo,registro_id=lote.unidades[0].id if escopo=='registro'else None)
    r=analisar(blob,PedidoDiagnostico(data_ref='2026-10-26',modo='B'),processamento_id='sintetico',destino=tmp_path,historico=(oc,))
    assert r['resumo']['dividas_efetivamente_geradas']==0 and r['decisoes'][0]['situacao_financeira']=='elegivel_na_simulacao'
    assert r['decisoes'][0]['situacao']=='revisao'and'RETENCAO_FICTICIA'in r['decisoes'][0]['bloqueios']
    assert any(o['id']=='critico_sintetico'for o in r['ocorrencias'])and not r['autoriza_cobranca']


def test_referencia_mais_de_uma_aba_compativel_e_ambigua(xlsx,tmp_path):
    base=tmp_path/'base';raw=xlsx()
    analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=base)
    w=load_workbook(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');w.active.title='HISTORICO FICTICIO';w.copy_worksheet(w.active)
    out=BytesIO();w.save(out);w.close()
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path/'novo',referencia=out.getvalue())
    assert r['comparacao']['codigo']=='REFERENCIA_ABA_AMBIGUA_OU_INVALIDA'
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not r['autoriza_cobranca']


def test_perfis_privados_antigos_nao_precisam_incluir_novo_condominio(xlsx,tmp_path):
    from conversor.web.service import PERFIS_SAIDA_PATH
    private=tmp_path/'perfis_saida.json';data=json.loads(PERFIS_SAIDA_PATH.read_bytes())
    private.write_text(json.dumps([p for p in data if p['administradora_id']!='adm_bbz']))
    old=private.read_bytes()
    r=analisar(xlsx(),PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path/'saida',perfis_saida=private)
    assert all(p['cedente']=='BL-UNI0001-884'and p['estado']=='codificado_para_teste'for p in r['codificacao_template']['unidades'].values())
    assert private.read_bytes()==old


@pytest.mark.parametrize('segundo_valor,coincidencias', [('200.00',2),('100.00',0)])
def test_referencia_nao_agrega_recibos_distintos_mesmo_vencimento(xlsx,tmp_path,segundo_valor,coincidencias):
    raw=xlsx([unidade(recibos=[recibo(id='99000001'),recibo(id='99000002',componentes=[('FICTICIO',segundo_valor)])])])
    base=tmp_path/'base';analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=base)
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path/'depois',
        referencia=(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes())
    assert r['comparacao']['resumo'].get('valores_coincidentes',0)==coincidencias
    assert r['resumo']['dividas_efetivamente_geradas']==2
