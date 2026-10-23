"""Ponta a ponta HTTP com PDFs inteiramente sintéticos; sem fontes privadas."""
from io import BytesIO
import json
from pathlib import Path
import time
from hashlib import sha256

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.domain.template import Template
from conversor.web.app import criar_app
from conversor.web.demo import documentos_demo
from conversor.web.service import reconhecer

KEY = 'chave_de_acesso_inventada_para_teste'


@pytest.fixture
def client(tmp_path):
    app = criar_app(tmp_path / 'privado', acesso=KEY)
    with TestClient(app) as c:
        assert c.post('/api/session', json={'chave': KEY}).status_code == 200
        yield c


def aguardar(client, response):
    assert response.status_code == 202
    id_ = response.json()['id']
    for _ in range(200):
        data = client.get('/api/processamentos/' + id_).json()
        if data['estado'] != 'processando':
            return data
        time.sleep(.01)
    pytest.fail('Processamento não concluiu')


@pytest.mark.parametrize('modo,linhas,cadastrais', [('A', 2, 0), ('B', 3, 1)])
def test_demo_completo_upload_leitura_AB_excel_e_comparacao(client, modo, linhas, cadastrais):
    r = aguardar(client, client.post('/api/exemplo', data={'data_ref':'2026-10-21','modo':modo}))
    assert r['estado'] == 'concluido'
    data = r['resultado']
    assert data['resumo']['unidades'] == 2 and data['resumo']['cotas'] == 3
    assert data['resumo']['elegivel'] == 2 and data['resumo']['nao_elegivel'] == 1
    assert data['resumo']['cadastros_adicionais'] == cadastrais
    assert data['comparacao']['resumo']['valores_coincidentes'] == 2
    assert data['permite_exportacao_operacional'] is False and data['aprovacao_formal_plano'] is False
    download = client.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx')
    assert download.status_code == 200
    book = load_workbook(BytesIO(download.content))
    rows = list(book['Dados'].iter_rows())
    assert len(rows) == linhas + 1
    assert tuple(c.value for c in rows[0]) == Template(id='t',nome='t',versao='1').cabecalhos_fisicos
    docs = [row[2] for row in rows[1:]]
    assert {c.value for c in docs} == {'00000000191','00000000000191'}
    assert all(c.data_type == 's' and c.number_format == '@' for c in docs)
    if modo == 'B':
        assert sum(all(c.value is None for c in row[24:30]) for row in rows[1:]) == 1
    assert client.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code == 409
    relatorio = client.get('/api/processamentos/'+r['id']+'/inconsistencias.json')
    assert relatorio.status_code == 200
    assert relatorio.json()['politica_cadastral'] == 'cadastro_por_unidade@1'
    assert relatorio.json()['reavaliacoes_historicas'] == []
    assert relatorio.json()['permite_exportacao_operacional'] is False
    book.close()


def test_upload_completo_com_historico_vazio_explicitamente_inventariado(tmp_path):
    root = tmp_path/'privado';root.mkdir()
    demo = documentos_demo();specs = {}
    for role, data in demo.items():
        path = root/(role+'.bin');path.write_bytes(data)
        specs[role] = {'path':str(path),'sha256':sha256(data).hexdigest(),'bytes':len(data)}
    (root/'fontes_autorizadas.json').write_text(json.dumps({'casos':[{'id':'fixture','perfil':'plaza',
        'arquivos':specs,'historico':{'vazio_inventariado':True,'registros':0}}]}))
    with TestClient(criar_app(root, acesso=KEY)) as c:
        c.post('/api/session',json={'chave':KEY})
        r=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'B'},
            files={role:(role+('.xlsx'if role=='referencia'else'.pdf'),content) for role,content in demo.items()}))
        assert r['estado']=='concluido' and r['resultado']['resumo']['elegivel']==2
        assert r['resultado']['resumo']['cadastros_adicionais']==1


@pytest.mark.parametrize('modo,linhas', [('A',2), ('B',3)])
def test_upload_sem_inventario_informa_limite_sem_transformar_em_erro_financeiro(client, modo, linhas):
    demo=documentos_demo()
    r=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':modo},
        files={'inadimplencia':('nao_confiar_no_nome.pdf',demo['inadimplencia'])}))
    assert r['estado']=='concluido'
    data=r['resultado']
    assert data['resumo']['elegivel']==2 and data['resumo']['nao_elegivel']==1
    assert not data['resumo'].get('revisao',0)
    assert data['resumo']['linhas_teste']==linhas
    assert data['historico_tecnico']['estado']=='nao_disponivel'
    avisos=[o for o in data['ocorrencias'] if o['codigo']=='HISTORICO_TECNICO_NAO_DISPONIVEL']
    assert len(avisos)==1 and avisos[0]['gravidade']=='informativo'
    assert all(not d['bloqueios']for d in data['decisoes'])
    assert client.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').status_code==200
    assert client.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409
    assert len(data['previa_template']['colunas'])==30
    assert len(data['previa_template']['linhas'])==linhas
    assert all(not l['bloqueada'] and len(l['valores'])==30 for l in data['previa_template']['linhas'])


def test_sem_autenticacao_e_sessoes_isoladas(tmp_path):
    app=criar_app(tmp_path/'privado',acesso=KEY)
    with TestClient(app) as a, TestClient(app) as b:
        assert a.get('/').status_code==200
        assert a.get('/api/config').status_code==401
        a.post('/api/session',json={'chave':KEY})
        r=aguardar(a,a.post('/api/exemplo',data={'data_ref':'2026-10-21','modo':'A'}))
        b.post('/api/session',json={'chave':KEY})
        assert b.get('/api/processamentos/'+r['id']).status_code==404
        assert b.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').status_code==404
        assert a.post('/api/exemplo',headers={'Origin':'https://outro.invalid'},data={'data_ref':'2026-10-21','modo':'A'}).status_code==403


@pytest.mark.parametrize('dados',[{'modo':'A'},{'data_ref':'2026-10-21'},{'data_ref':'hoje','modo':'A'},{'data_ref':'2026-10-21','modo':'C'}])
def test_parametros_explicitos_e_invalidos(client,dados):
    assert client.post('/api/exemplo',data=dados).status_code==422


def test_selecao_manual_nao_sobrepoe_cabecalho(client):
    r=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'A','condominio':'tree'},
        files={'inadimplencia':('tree.pdf',documentos_demo()['inadimplencia'])}))
    assert r['estado']=='erro' and r['codigo']=='SELECAO_DIVERGENTE_DO_CABECALHO'


def test_pdf_desconhecido_e_invalido_nao_vira_dados(client):
    assert client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'A'},
        files={'inadimplencia':('arquivo.pdf',b'nao e PDF')}).status_code==422
    r=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'A'},
        files={'inadimplencia':('arquivo.pdf',b'%PDF-invalido')}))
    assert r['estado']=='erro' and r['codigo']=='PDF_NAO_EXTRAIVEL_COM_SEGURANCA'


def test_identificacao_fiscal_do_condominio_no_titulo_nao_muda_nome_ou_cpf_titular():
    from examples.fase3.layouts_sinteticos import habita_paginas, pdf_posicionado
    paginas=habita_paginas()
    paginas=[[(x,y,t.replace('CONDOMINIO SINTETICO','TREE MORUMBI CNPJ: 00.000.000/0001-91'))
              for x,y,t in pagina] for pagina in paginas]
    perfil,codigo,leitor=reconhecer(pdf_posicionado(paginas))
    assert perfil['id']=='tree' and codigo=='9999' and leitor=='habita_composicao_real_v1'


def test_vinculo_historico_nao_substitui_valor_atual_ou_forca_gabarito(tmp_path):
    from conversor.web.service import analisar,PedidoDiagnostico
    demo=documentos_demo()
    book=load_workbook(BytesIO(demo['referencia']))
    book['Dados'].cell(2,30,999)
    out=BytesIO();book.save(out);book.close()
    r=analisar(demo['inadimplencia'],PedidoDiagnostico(data_ref='2026-10-21',modo='A'),
        processamento_id='comparacao_sintetica',destino=tmp_path,cadastro=demo['cadastro'],referencia=out.getvalue(),
        mapeamento_referencia=[{'linha_excel':2,'unidade':'A/1','boleto':'900001','confere':True}])
    assert r['comparacao']['linhas'][0]['codigo']=='VALOR_ORIGINAL_DIVERGENTE'
    assert r['comparacao']['resumo']['dados']==1
    assert next(d['valor']for d in r['decisoes']if d['cota']=='900001')=='85.00'
    assert r['resumo']['elegivel']==2


def test_anotacao_extra_na_referencia_e_reportada_sem_mudar_o_template(tmp_path):
    from conversor.web.service import analisar,PedidoDiagnostico
    demo=documentos_demo();book=load_workbook(BytesIO(demo['referencia']))
    book['Dados'].cell(6,31,'Anotacao sintetica fora do template')
    out=BytesIO();book.save(out);book.close()
    r=analisar(demo['inadimplencia'],PedidoDiagnostico(data_ref='2026-10-21',modo='A'),
        processamento_id='referencia_com_anotacao',destino=tmp_path,cadastro=demo['cadastro'],referencia=out.getvalue())
    assert r['comparacao']['resumo']['valores_coincidentes']==2
    assert r['comparacao']['resumo']['anotacoes_fora_das_30_colunas']==1
    assert any(x['codigo']=='REFERENCIA_CONTEM_ANOTACAO_FORA_DO_TEMPLATE' for x in r['comparacao']['linhas'])
    output=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert output['Dados'].max_column==30
    output.close()


@pytest.mark.parametrize('cenario', ['conflito_documental','divergencia_de_nomes'])
def test_upload_novo_preserva_conflitos_reais_e_exibe_linhas_retidas(client, cenario):
    from tests.web.test_unit_contacts import documentos
    dados = (documentos(docs=('00000000191','00000000272')) if cenario=='conflito_documental'
             else documentos('OUTRA PESSOA SINTETICA'))
    r=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'B'},
        files={role:(role+'.pdf',content)for role,content in dados.items()if role!='referencia'}))
    data=r['resultado']
    assert data['historico_tecnico']['estado']=='nao_disponivel'
    assert data['resumo']['revisao']==2 and data['resumo']['elegivel']==1
    codigo='DOCUMENTOS_CONFLITANTES'if cenario=='conflito_documental'else'TITULAR_DIVERGENTE'
    assert all(codigo in d['bloqueios']for d in data['decisoes']if d['bloco']=='A')
    previa=data['previa_template']['linhas']
    retidas=[l for l in previa if l['bloco']=='A']
    assert len(retidas)==2 and all(l['bloqueada']and codigo in l['motivos']for l in retidas)
    assert len([l for l in retidas if l['tipo']=='cadastral'])==1
    if cenario=='conflito_documental':assert all(l['valores']is None for l in retidas)
    else:assert all(len(l['valores'])==30 for l in retidas)
    assert all(not l['bloqueada']for l in previa if l['bloco']=='B')
    wb=load_workbook(BytesIO(client.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').content))
    assert wb['Dados'].max_row==2 and wb['Dados'].max_column==30
    wb.close()
    rel=client.get('/api/processamentos/'+r['id']+'/inconsistencias.json').json()
    assert rel['previa_template']==data['previa_template'] and not rel['permite_exportacao_operacional']


def catalogo_historico_sintetico(root):
    """Registro técnico verificável, sem aprovação ou atesto de produção."""
    from conversor.adapters.audit_history import reconstruir_reconciliacao
    from conversor.domain.audit_identity import FonteHistorico
    from conversor.domain.canonical import Ocorrencia
    from conversor.web.service import ler, PERFIS
    demo=documentos_demo()
    lote,_=ler(demo['inadimplencia'],PERFIS['plaza'],'9999','fl_composicao_real_v1','inadimplencia')
    o=Ocorrencia(id='bloqueio_previo',processamento_id='anterior_sintetico',codigo='DOCUMENTOS_CONFLITANTES',
        gravidade='critico',escopo='registro',registro_id=lote.unidades[0].id,origem=lote.unidades[0].origem)
    original=root/'ocorrencias.json';original.write_text(json.dumps([o.model_dump(mode='json')]))
    fonte=FonteHistorico(arquivo={'arquivo_id':'historico_sintetico','caminho':str(original),
        'sha256':sha256(original.read_bytes()).hexdigest(),'tamanho':original.stat().st_size,'papel':'evidencia'},
        namespace='documental',produtor_id='fixture',produtor_versao='1',estrutura='lista_ocorrencias')
    rec=reconstruir_reconciliacao(id_='rec_sintetica',condominio_id=PERFIS['plaza']['condominio_id'],ambiente='sintetico',fontes=(fonte,))
    history=root/'historico.json';history.write_text(rec.model_dump_json())
    def spec(path,content):
        return {'path':str(path),'bytes':len(content),'sha256':sha256(content).hexdigest()}
    caso={'id':'sintetico','perfil':'plaza','arquivos':{role:spec(root/(role+'.bin'),data)for role,data in demo.items()},
        'historico':spec(history,history.read_bytes())|{'registros':1}}
    (root/'fontes_autorizadas.json').write_text(json.dumps({'casos':[caso]}))
    return demo,history


@pytest.mark.parametrize('cenario',['carregado','arquivo_historico_ausente','cadastro_divergente','catalogo_corrompido'])
def test_upload_nao_descarta_bloqueio_conhecido_ou_falha_de_integridade(tmp_path, cenario):
    root=tmp_path/'privado';root.mkdir()
    demo,history=catalogo_historico_sintetico(root)
    if cenario=='arquivo_historico_ausente':history.unlink()
    if cenario=='catalogo_corrompido':(root/'fontes_autorizadas.json').write_text('{')
    if cenario=='cadastro_divergente':
        from tests.web.test_unit_contacts import documentos
        demo['cadastro']=documentos()['cadastro']
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        r=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'B'},
            files={role:(role+'.pdf',data)for role,data in demo.items()if role!='referencia'}))
        assert r['estado']=='concluido'
        data=r['resultado']
        assert data['historico_tecnico']['estado']==('carregado'if cenario=='carregado'else'divergente')
        if cenario in ('carregado','cadastro_divergente'):
            assert any(o['codigo']=='DOCUMENTOS_CONFLITANTES'and o['gravidade']=='critico'for o in data['ocorrencias'])
            assert all('DOCUMENTOS_CONFLITANTES'in d['pendencias_documentais']for d in data['decisoes']if d['bloco']=='A')
        if cenario!='carregado':
            assert data['resumo']['revisao']==3 and not data['arquivo_teste_disponivel']
            assert all('INVENTARIO_EXTERNO_AUSENTE_OU_DIVERGENTE'in d['bloqueios']for d in data['decisoes'])
        assert not data['autoriza_cobranca']and not data['permite_exportacao_operacional']
