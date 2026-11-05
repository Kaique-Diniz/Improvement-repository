"""UX-01: sessão técnica, CSRF e metadados administrativos somente sintéticos."""
from hashlib import sha256
from io import BytesIO
import asyncio

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.readers.text_support import ErroLeitura
from conversor.web import ephemeral as ep
from conversor.web.service import PERFIS,reconhecer
from conversor.web.demo import documentos_demo
from tests.passaredo.fixtures import financeiro,cadastro,ficha,debito
from tests.web.test_ephemeral import Clock

ORIGIN='http://127.0.0.1'
DATE={'data_ref':'2026-10-07','modo':'A'}
ADDRESS={'logradouro':'Rua Inteiramente Fictícia','numero':'42','cep':'01001000','bairro':'Bairro Fictício','cidade':'Cidade Fictícia','uf':'SP'}


@pytest.fixture
def app(tmp_path):return ep.criar_app_efemero(area_temporaria=tmp_path,relogio=Clock())


def boot(c):
    r=c.get('/');assert r.status_code==200 and 'login-form' not in r.text
    token=c.get('/api/sessao').json()['csrf']
    c.headers.update({'origin':ORIGIN,'x-csrf-token':token})


@pytest.fixture
def client(app):
    with TestClient(app,base_url=ORIGIN) as c:boot(c);yield c


def identify(c,raw,choice='auto'):
    return c.post('/api/identificar',data={'condominio':choice},files={'inadimplencia':('nome-sem-identidade.xlsx',raw)})


def convert(c,raw,**data):
    return c.post('/api/conversoes',data=DATE|data,files={'inadimplencia':('outro-nome.xlsx',raw)})


def output(c,id_):
    r=c.get('/api/conversoes/'+id_+'/excel');assert r.status_code==200
    b=load_workbook(BytesIO(r.content));rows=list(b['Dados'].values);b.close();return rows


def test_sem_senha_interface_classica_e_cookie_host_only(client):
    html=client.get('/').text
    for label in ('Conversor Inteligente','Preparar análise','Dados do condomínio','torres / unidades','Prévia das 30 colunas'):assert label in html
    assert 'type="password"' not in html
    assert client.get('/api/sessao').json()['sessao_automatica']
    # A factory sem acesso não aceita login por chave como inicialização alternativa.
    assert client.post('/api/sessao',json={'chave':'nao-deve-ser-usada'}).status_code==405
    raw=client.get('/').headers
    assert raw['cache-control']=='no-store' and 'frame-ancestors' in raw['content-security-policy']
    with TestClient(ep.criar_app_efemero(),base_url=ORIGIN) as other:
        response=other.get('/');cookie=response.headers['set-cookie'].lower()
        assert 'httponly' in cookie and 'samesite=strict' in cookie and 'domain=' not in cookie


def test_hash_exato_auto_mas_layout_novo_exige_confirmacao(client,monkeypatch):
    raw=financeiro()
    assert identify(client,raw).status_code==409
    monkeypatch.setitem(PERFIS['passaredo']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    identified=identify(client,raw);assert identified.status_code==200 and identified.json()['perfil']=='passaredo'
    r=convert(client,raw);assert r.status_code==200 and r.json()['perfil']=='passaredo'
    rows=output(client,r.json()['id']);assert len(rows[0])==30 and rows[0][26]=='NM_DIVIDA_CEDENTE'
    different=financeiro([debito(valor='101.11')])
    suggested=identify(client,different);assert suggested.status_code==409 and suggested.json()['confirmacao_necessaria']
    assert identify(client,different,'passaredo').status_code==200


@pytest.mark.parametrize('tipo',['fechamento','formula','aba'])
def test_hash_homologado_nao_aceita_estrutura_invalida(client,monkeypatch,tipo):
    def change(w,s):
        if tipo=='fechamento':s.cell(s.max_row-1,1).value='99 item(ns)'
        if tipo=='formula':s['F2']='=1+1'
        if tipo=='aba':s.title='Outra'
    raw=financeiro(mutar=change)
    monkeypatch.setitem(PERFIS['passaredo']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    assert identify(client,raw).status_code==422
    assert convert(client,raw).status_code==422
    assert not list(client.app.state.ciclo.root.iterdir())


def test_outro_condominio_e_futuro_forest_nao_viram_passaredo(client,monkeypatch):
    raw=financeiro()
    monkeypatch.setitem(PERFIS,'forest_futuro',dict(PERFIS['passaredo'],id='forest_futuro',
        fontes_homologacao_sha256={'inadimplencia':sha256(raw).hexdigest()}))
    with pytest.raises(ErroLeitura,match='AINDA_NAO_IMPLEMENTADO'):reconhecer(raw)
    with pytest.raises(ErroLeitura,match='CONFLITANTE'):reconhecer(raw,perfil_informado='passaredo')
    assert identify(client,raw,'passaredo').status_code==422
    assert identify(client,documentos_demo()['inadimplencia'],'passaredo').status_code==422


def test_hash_conflitante_em_dois_perfis_bloqueia(client,monkeypatch):
    raw=financeiro();h=sha256(raw).hexdigest()
    monkeypatch.setitem(PERFIS['passaredo']['fontes_homologacao_sha256'],'inadimplencia',h)
    monkeypatch.setitem(PERFIS,'outro',dict(PERFIS['passaredo'],id='outro'))
    assert identify(client,raw).status_code==422


@pytest.mark.parametrize('method,path,headers',[
    ('post','/api/conversoes',{'x-csrf-token':''}),
    ('post','/api/conversoes',{'x-csrf-token':'falso'}),
    ('post','/api/conversoes',{'origin':'http://atacante.invalid'}),
    ('post','/api/conversoes',{'origin':''}),
    ('get','/api/config',{'sec-fetch-site':'cross-site'}),
    ('get','/api/config',{'sec-fetch-site':'same-site'}),
    ('get','/',{'sec-fetch-site':'cross-site'}),
    ('get','/api/config',{'origin':'http://127.0.0.1:9999'}),
])
def test_csrf_origem_cruzada_inclusive_get_bloqueados(client,method,path,headers):
    assert getattr(client,method)(path,headers=headers).status_code==403
    assert not client.app.state.ciclo.results


def test_host_externo_e_excesso_identificacao_bloqueados(client):
    assert client.get('/',headers={'host':'malicioso.invalid'}).status_code==400
    runtime=client.app.state.ciclo;runtime.slots.acquire();runtime.slots.acquire()
    try:assert identify(client,financeiro()).status_code==503
    finally:runtime.slots.release();runtime.slots.release()


def test_endereco_vinculado_ao_perfil_e_sessao_corretos(client):
    raw=financeiro();ctx=identify(client,raw,'passaredo').json();url='/api/contextos/'+ctx['contexto']+'/configuracao'
    payload={'revisao_esperada':0,'endereco':ADDRESS,'mapeamentos':[]}
    r=client.put(url,json=payload);assert r.status_code==200 and r.json()['revisao']==1
    assert client.put(url,json=payload).status_code==409
    assert client.put(url,json=payload|{'condominio_id':'outro'}).status_code==422
    # Endereço retornado pode ser reenviado ao registrar uma torre, sem levar
    # complemento individual ao contrato administrativo de seis campos.
    assert client.put(url,json={'revisao_esperada':1,'endereco':r.json()['endereco'],
        'mapeamentos':[{'bloco':'Z','codigo':'99'}]}).status_code==200
    result=convert(client,raw,contexto=ctx['contexto'],condominio='passaredo').json()
    detail=client.get('/api/conversoes/'+result['id']+'/detalhes').json()
    assert detail['endereco_condominio']['cadastrado']
    rows=output(client,result['id']);row=rows[1]
    assert tuple(row[i] for i in (4,5,7,8,9,10))==tuple(ADDRESS[n] for n in ('logradouro','numero','cep','bairro','cidade','uf'))
    assert row[6]=='BL-UNI0007'
    other=convert(client,documentos_demo()['inadimplencia'],data_ref='2026-10-21').json()
    assert not client.get('/api/conversoes/'+other['id']+'/detalhes').json()['endereco_condominio']['cadastrado']
    # Outra sessão não consulta o contexto nem reutiliza a configuração.
    owner=client.cookies.get('conversor_session');old_headers=dict(client.headers)
    client.cookies.clear();boot(client)
    assert client.get(url).status_code==404
    new=convert(client,raw,condominio='passaredo').json()
    assert not client.get('/api/conversoes/'+new['id']+'/detalhes').json()['endereco_condominio']['cadastrado']
    client.cookies.clear();client.cookies.set('conversor_session',owner);client.headers.update(old_headers)


def test_contexto_nao_pode_ser_reutilizado_com_outros_bytes(client):
    raw=financeiro();ctx=identify(client,raw,'passaredo').json()['contexto']
    assert convert(client,financeiro([debito(valor='200.00')]),contexto=ctx,condominio='passaredo').status_code==409


def test_mapeamentos_propostos_nao_inventam_prova(client):
    ctx=identify(client,documentos_demo()['inadimplencia']).json()
    url='/api/contextos/'+ctx['contexto']+'/configuracao'
    r=client.put(url,json={'revisao_esperada':0,'endereco':None,'mapeamentos':[
        {'bloco':'A','codigo':'1'},{'bloco':'B','codigo':'99'},{'bloco':'Z','codigo':'9'}]})
    assert r.status_code==200
    assert [(m['estado'],m['aplicado']) for m in r.json()['mapeamentos']]==[('comprovado',True),('conflitante',False),('pendente',False)]
    assert 'não comprova' in r.json()['limite']


def test_detalhes_expiram_sao_isolados_e_download_exige_csrf(client):
    r=convert(client,documentos_demo()['inadimplencia'],data_ref='2026-10-21').json();url='/api/conversoes/'+r['id']
    assert client.get(url+'/detalhes').json()['previa_template']['colunas'][26]=='NM_DIVIDA_CEDENTE'
    assert client.get(url+'/excel',headers={'x-csrf-token':''}).status_code==403
    owner=client.cookies.get('conversor_session');headers=dict(client.headers);client.cookies.clear();boot(client)
    assert client.get(url+'/detalhes').status_code==404 and client.get(url+'/excel').status_code==404
    client.cookies.clear();client.cookies.set('conversor_session',owner);client.headers.update(headers)
    runtime=client.app.state.ciclo;runtime.relogio.now+=ep.RETENCAO+1;runtime.limpar()
    assert client.get(url+'/detalhes').status_code==404 and not runtime.results


@pytest.mark.parametrize('falha',[False,True])
def test_resposta_previa_ativa_nao_perde_bytes_nem_vira_historico(client,falha):
    r=convert(client,documentos_demo()['inadimplencia'],data_ref='2026-10-21').json();runtime=client.app.state.ciclo;id_=r['id'];owner=client.cookies.get('conversor_session')
    result=runtime.obter(id_,owner);result.ativos+=1;response=ep.PreviaTemporaria(runtime,id_,result.detalhes)
    async def send(message):
        if message['type']=='http.response.body':
            assert runtime.apagar(id_,owner) and id_ in runtime.results and response.body
            if falha:raise OSError('FALHA_FICTICIA_DE_RESPOSTA')
    async def receive():return {'type':'http.request','body':b''}
    if falha:
        with pytest.raises(OSError):asyncio.run(response({'type':'http'},receive,send))
    else:asyncio.run(response({'type':'http'},receive,send))
    assert id_ not in runtime.results and response.body==b''


def test_encerramento_remove_contextos_configs_e_sem_arquivos_administrativos(app):
    with TestClient(app,base_url=ORIGIN) as c:
        boot(c);ctx=identify(c,financeiro(),'passaredo').json()['contexto']
        c.put('/api/contextos/'+ctx+'/configuracao',json={'revisao_esperada':0,'endereco':ADDRESS,'mapeamentos':[]})
        assert not list(app.state.ciclo.root.iterdir());root=app.state.ciclo.root
    assert not root.exists() and not app.state.ciclo.administracao.contextos and not app.state.ciclo.administracao.configs


def test_cli_padrao_ignora_antiga_variavel_e_nao_aceita_host_publico(monkeypatch):
    import uvicorn
    calls=[]
    monkeypatch.setenv('CONVERSOR_CHAVE_LOCAL','curta-e-ignorada')
    monkeypatch.setattr(uvicorn,'run',lambda app,**kw:calls.append((app,kw)))
    monkeypatch.setattr('sys.argv',['conversor-web'])
    ep.main()
    assert calls[0][0].state.ciclo.sem_login and calls[0][1]['host']=='127.0.0.1' and calls[0][1]['port']==8000
    monkeypatch.setattr('sys.argv',['conversor-web','--host','0.0.0.0'])
    with pytest.raises(SystemExit):ep.main()


def test_validacao_configuracao_nao_devolve_conteudo_submetido(client):
    ctx=identify(client,financeiro(),'passaredo').json()['contexto']
    sentinel='CONTEUDO_FICTICIO_NAO_EXIBIR'
    r=client.put('/api/contextos/'+ctx+'/configuracao',json={'revisao_esperada':0,
        'endereco':ADDRESS|{'cep':sentinel},'mapeamentos':[]})
    assert r.status_code==422 and sentinel not in r.text


def test_orcamento_global_inclui_excel_e_detalhes(client,monkeypatch):
    raw=documentos_demo()['inadimplencia']
    r=convert(client,raw,data_ref='2026-10-21').json();runtime=client.app.state.ciclo
    result=runtime.results[r['id']]
    assert result.detalhes and result.excel
    monkeypatch.setattr(ep,'MAX_CACHE',len(result.excel)+len(result.detalhes))
    assert convert(client,raw,data_ref='2026-10-21').status_code==503
    assert len(runtime.results)==1 and not list(runtime.root.iterdir())
    assert client.get('/api/conversoes/'+r['id']+'/detalhes').status_code==200
