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
    assert client.get('/api/processamentos/'+r['id']+'/inconsistencias.json').status_code == 200
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


def test_upload_sem_inventario_preserva_revisao_e_nao_libera_excel(client):
    demo=documentos_demo()
    r=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-21','modo':'B'},
        files={'inadimplencia':('nao_confiar_no_nome.pdf',demo['inadimplencia'])}))
    assert r['estado']=='concluido'
    assert r['resultado']['resumo']['revisao']==3
    assert r['resultado']['resumo']['linhas_teste']==0
    assert all('INVENTARIO_EXTERNO_AUSENTE_OU_DIVERGENTE'in d['motivos']for d in r['resultado']['decisoes'])
    assert client.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').status_code==409


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
