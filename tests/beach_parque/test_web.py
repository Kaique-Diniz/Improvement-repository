"""Fluxo sintético de sessão/download/limpeza, sem documentos de clientes."""
from hashlib import sha256
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from conversor.web.ephemeral import criar_app_efemero
from conversor.web.service import PERFIS
from tests.web.test_classic_local import boot,ORIGIN,ADDRESS
from tests.web.test_ephemeral import Clock
from .fixtures import financeiro,cadastro,recibo,NOME,REF

PROFILE='terraco_beach_parque'


@pytest.mark.parametrize('modo',['A','B'])
def test_navegador_http_30_colunas_e_descarte(tmp_path,monkeypatch,modo):
    raw=financeiro([('A','A00001',NOME,[recibo('1',31),recibo('2',30),recibo('3',29)])]);cad=cadastro()
    for role,data in [('inadimplencia',raw),('cadastro',cad)]:monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],role,sha256(data).hexdigest())
    clock=Clock();app=criar_app_efemero(area_temporaria=tmp_path,relogio=clock)
    with TestClient(app,base_url=ORIGIN)as c:
        boot(c);identified=c.post('/api/identificar',files={'inadimplencia':('ficticio.xlsx',raw)})
        assert identified.status_code==200 and identified.json()['perfil']==PROFILE
        ctx=identified.json()['contexto']
        saved=c.put(f'/api/contextos/{ctx}/configuracao',json={'revisao_esperada':0,'endereco':ADDRESS,'mapeamentos':[]})
        assert saved.status_code==200
        data={'data_ref':str(REF),'modo':modo,'condominio':PROFILE,'contexto':ctx}
        r=c.post('/api/conversoes',data=data,files={'inadimplencia':('ficticio.xlsx',raw),'cadastro':('ficticio.pdf',cad)})
        assert r.status_code==200;r=r.json();id_=r['id']
        assert r['resumo']['dividas_efetivamente_geradas']==1
        assert r['resumo']['cadastros_adicionais']==int(modo=='B')
        assert not r['permite_exportacao_operacional']and not r['autoriza_cobranca']
        assert not any(p.is_file()for p in tmp_path.rglob('*'))
        details=c.get(f'/api/conversoes/{id_}/detalhes').json()
        assert details['decisoes'][0]['recibo_original']=='1'
        assert len(details['previa_template']['colunas'])==30
        assert c.get(f'/api/conversoes/{id_}/operacional.xlsx').status_code==409
        with TestClient(criar_app_efemero(),base_url=ORIGIN)as outsider:
            boot(outsider);assert outsider.get(f'/api/conversoes/{id_}/excel').status_code==404
        out=c.get(f'/api/conversoes/{id_}/excel');assert out.status_code==200
        w=load_workbook(BytesIO(out.content));rows=list(w['Dados'].values);w.close()
        assert len(rows)==2+int(modo=='B')and len(rows[0])==30 and rows[0][26]=='NM_DIVIDA_CEDENTE'
        assert rows[1][4]==ADDRESS['logradouro']and rows[1][1]=='BLILHABE-UNIA00001-TERRAÇO BEACH PARQUE'
        assert c.get(f'/api/conversoes/{id_}/excel').status_code==404
        # Protection remains independent of valid BPQ grammar.
        assert c.post('/api/identificar',files={'inadimplencia':('ficticio.xlsx',raw)},headers={'x-csrf-token':'invalido'}).status_code==403
        assert c.get('/api/config',headers={'Origin':'http://origem-ficticia.invalid'}).status_code==403
        assert c.get('/api/config',headers={'Host':'host-ficticio.invalid'}).status_code==400
    assert not list(tmp_path.iterdir())


def test_confirmacao_nativa_diagnostico_nao_auto_novo(tmp_path):
    app=criar_app_efemero(area_temporaria=tmp_path)
    with TestClient(app,base_url=ORIGIN)as c:
        boot(c);raw=financeiro()
        r=c.post('/api/identificar',files={'inadimplencia':('nome-nao-prova.xlsx',raw)})
        assert r.status_code==409 and r.json()['candidatos'][0]['id']==PROFILE
        assert c.post('/api/identificar',data={'condominio':PROFILE},files={'inadimplencia':('qualquer.xlsx',raw)}).status_code==200
