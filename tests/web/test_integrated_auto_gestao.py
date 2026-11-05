"""INT-01: integração real com fontes exclusivamente fictícias e hashes reais."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.web import ephemeral as ep
from conversor.web.service import PERFIS,reconhecer,ler
from conversor.readers.auto_gestao_identity import PERFIS_TABULARES,IdentidadeTabularNaoComprovada
from conversor.readers.passaredo_canonical import ler_financeiro as isolado_passaredo
from conversor.readers.forest_hill import ler_financeiro as isolado_forest
from conversor.readers.text_support import ErroLeitura
from tests.passaredo.fixtures import financeiro,cadastro,debito,ficha,REF
from tests.web.test_classic_local import boot,ORIGIN,ADDRESS
from tests.web.test_ephemeral import Clock

PROFILES=('passaredo','forest_hill')
UNITS={'passaredo':('007','008'),'forest_hill':('AV.P02 231','RUA 18 347')}


def debt(profile,**kw):return debito(unidade=UNITS[profile][0],dias=61 if profile=='passaredo' else 31,**kw)

def raw(profile,rows=None,**kw):return financeiro(rows if rows is not None else [debt(profile)],**kw)

def cad(profile,rows=None):return cadastro(rows if rows is not None else [ficha(unidade=UNITS[profile][0])])

def bind(monkeypatch,profile,content,role='inadimplencia'):
    monkeypatch.setitem(PERFIS[profile]['fontes_homologacao_sha256'],role,sha256(content).hexdigest())


@pytest.fixture
def app(tmp_path):return ep.criar_app_efemero(area_temporaria=tmp_path,relogio=Clock())


@pytest.fixture
def client(app):
    with TestClient(app,base_url=ORIGIN) as c:boot(c);yield c


def identify(c,content,profile='auto'):
    return c.post('/api/identificar',data={'condominio':profile},files={'inadimplencia':('nome-enganoso.xlsx',content)})


def convert(c,content,profile='auto',cadastro=None,context=None,mode='A'):
    fields={'data_ref':str(REF),'modo':mode,'condominio':profile}
    if context:fields['contexto']=context
    files={'inadimplencia':('nome-nao-comprova-condominio.xlsx',content)}
    if cadastro is not None:files['cadastro']=('cadastro.xlsx',cadastro)
    return c.post('/api/conversoes',data=fields,files=files)


def rows(c,id_):
    r=c.get('/api/conversoes/'+id_+'/excel');assert r.status_code==200
    b=load_workbook(BytesIO(r.content))
    try:return list(b['Dados'].values)
    finally:b.close()


@pytest.mark.parametrize('profile',PROFILES)
def test_hashs_homologados_auto_escolhem_perfil_gramatica_e_leitor(client,monkeypatch,profile):
    contents={p:raw(p) for p in PROFILES}
    for p,content in contents.items():bind(monkeypatch,p,content)
    content=contents[profile]
    perfil,code,reader=reconhecer(content,perfil_informado='auto')
    assert perfil['id']==profile and reader==profile+'_inadimplencia_xlsx_v1'
    canonical,ctx=ler(content,perfil,code,reader,'inadimplencia')
    assert canonical.unidades[0].unidade_original==UNITS[profile][0]
    assert canonical.unidades[0].condominio_id==PERFIS[profile]['condominio_id']
    assert ctx.formato_id==reader
    r=convert(client,content,cadastro=cad(profile));assert r.status_code==200
    result=r.json();assert result['perfil']==profile and 'cadastro_'+profile in result
    other=next(p for p in PROFILES if p!=profile)
    assert 'cadastro_'+other not in result
    assert result['cadastro_'+profile]['documentos_validos_vinculados']==1
    output=rows(client,result['id']);assert len(output)==2 and len(output[0])==30 and output[0][26]=='NM_DIVIDA_CEDENTE'


@pytest.mark.parametrize('profile',PROFILES)
def test_novo_layout_compativel_so_sugere_confirmacao(client,profile):
    content=raw(profile)
    with pytest.raises(IdentidadeTabularNaoComprovada) as error:reconhecer(content)
    assert error.value.candidatos==(profile,)
    r=identify(client,content);assert r.status_code==409
    assert r.json()['confirmacao_necessaria'] and [p['id'] for p in r.json()['candidatos']]==[profile]
    assert not client.app.state.ciclo.results
    confirmed=identify(client,content,profile);assert confirmed.status_code==200
    result=convert(client,content,profile,context=confirmed.json()['contexto'])
    assert result.status_code==200 and result.json()['perfil']==profile


@pytest.mark.parametrize('profile',PROFILES)
def test_hash_conhecido_com_gramatica_do_outro_perfil_falha(client,monkeypatch,profile):
    other=next(p for p in PROFILES if p!=profile);content=raw(other)
    bind(monkeypatch,profile,content)
    with pytest.raises(ErroLeitura,match='INCOMPATIVEL'):reconhecer(content)
    assert identify(client,content).status_code==422
    assert not client.app.state.ciclo.results


@pytest.mark.parametrize('profile',PROFILES)
@pytest.mark.parametrize('kind',['fechamento','formula','aba'])
def test_hash_registrado_nao_ignora_estrutura(client,monkeypatch,profile,kind):
    def change(w,s):
        if kind=='fechamento':s.cell(s.max_row-1,1).value='99 item(ns)'
        if kind=='formula':s['F2']='=1+1'
        if kind=='aba':s.title='Outra'
    content=raw(profile,mutar=change);bind(monkeypatch,profile,content)
    assert identify(client,content).status_code==422
    assert convert(client,content).status_code==422
    assert not list(client.app.state.ciclo.root.iterdir())


@pytest.mark.parametrize('profile',PROFILES)
def test_selecao_manual_conflita_com_identidade_comprovada(client,monkeypatch,profile):
    content=raw(profile);bind(monkeypatch,profile,content)
    other=next(p for p in PROFILES if p!=profile)
    assert identify(client,content,other).status_code==422
    assert convert(client,content,other).status_code==422


@pytest.mark.parametrize('profile',PROFILES)
@pytest.mark.parametrize('known_cad',[False,True])
def test_cadastro_cruzado_nao_e_aplicado_mesmo_com_colunas_iguais(client,monkeypatch,profile,known_cad):
    other=next(p for p in PROFILES if p!=profile);content=raw(profile);wrong=cad(other)
    bind(monkeypatch,profile,content)
    if known_cad:bind(monkeypatch,other,wrong,'cadastro')
    response=convert(client,content,cadastro=wrong)
    assert response.status_code==422 and not client.app.state.ciclo.results
    assert not list(client.app.state.ciclo.root.iterdir())


@pytest.mark.parametrize('units',[('007','RUA 18 347'),('TORRE X CASA 1',),()])
def test_nenhum_perfil_compativel_rejeita_sem_sugestao_presumida(client,units):
    content=financeiro([debito(unidade=u) for u in units])
    r=identify(client,content)
    assert r.status_code==422 and not r.json().get('confirmacao_necessaria')
    assert not client.app.state.ciclo.administracao.contextos


def test_multiplos_candidatos_compativeis_exigem_escolha_sem_primeiro_padrao(client,monkeypatch):
    # Perfil de laboratório somente na fixture: mesma gramática numérica válida,
    # exercitando sobreposição real de predicados sem mudar perfis de produção.
    laboratorio=replace(PERFIS_TABULARES['passaredo'],id='laboratorio')
    monkeypatch.setitem(PERFIS_TABULARES,'laboratorio',laboratorio)
    monkeypatch.setitem(PERFIS,'laboratorio',dict(PERFIS['passaredo'],id='laboratorio',
        nome='Perfil Fictício Compatível',fontes_homologacao_sha256={}))
    r=identify(client,raw('passaredo'))
    assert r.status_code==409 and {p['id'] for p in r.json()['candidatos']}=={'passaredo','laboratorio'}
    assert not client.app.state.ciclo.administracao.contextos
    assert identify(client,raw('passaredo'),'passaredo').status_code==200


def test_forest_despachado_pelo_callback_proprio(client,monkeypatch):
    calls=[]
    for profile in PROFILES:
        original=PERFIS_TABULARES[profile]
        def spy(content,*,contexto,original=original,profile=profile):
            calls.append(profile);return original.financeiro(content,contexto=contexto)
        monkeypatch.setitem(PERFIS_TABULARES,profile,replace(original,financeiro=spy))
    content=raw('forest_hill');bind(monkeypatch,'forest_hill',content)
    assert identify(client,content).status_code==200 and calls==['forest_hill']


@pytest.mark.parametrize('profile',PROFILES)
def test_regressao_financeira_ids_limites_duplicidades_e_rotulos(client,monkeypatch,profile):
    limit=60 if profile=='passaredo' else 30;u=UNITS[profile][0]
    repeated=debito(unidade=u,dias=limit+1,valor='12.34')
    content=raw(profile,[debito(unidade=u,dias=limit-1),debito(unidade=u,dias=limit),repeated,repeated.copy(),
        debito(unidade=u,dias=90,descricao='Acordo 1/2',valor='23.45',encargos=('1','2','3','4'))])
    bind(monkeypatch,profile,content)
    p,code,reader=reconhecer(content);_,ctx=ler(content,p,code,reader,'inadimplencia')
    expected=(isolado_passaredo if profile=='passaredo' else isolado_forest)(content,contexto=ctx)
    r=convert(client,content);assert r.status_code==200;result=r.json()
    detail=client.get('/api/conversoes/'+result['id']+'/detalhes').json()
    assert set(detail['boletos'])=={b.id for b in expected.boletos}
    assert result['resumo']['dividas_efetivamente_geradas']==3
    output=rows(client,result['id']);assert [r[27] for r in output[1:]]==[1,2,3]
    assert [r[29] for r in output[1:]]==[23.45,12.34,12.34]
    label='Acordo 1/2 07/2026 - 1' if profile=='forest_hill' else 'Acordo 1/2'
    assert output[1][26]==label
    assert len({d['id'] for d in detail['decisoes']})==5
    assert all(d['competencia'] is None for d in detail['decisoes'])


@pytest.mark.parametrize('profile',PROFILES)
@pytest.mark.parametrize('mode',['A','B'])
def test_cadastro_divergente_retido_sem_excluir_divida_em_ambos_modos(client,monkeypatch,profile,mode):
    limit=60 if profile=='passaredo' else 30;u=UNITS[profile][0]
    content=raw(profile,[debito(unidade=u,dias=limit+1),debito(unidade=u,dias=limit)])
    bind(monkeypatch,profile,content)
    cadastro=cad(profile,[ficha(unidade=u,nome='Pessoa Fictícia Divergente')])
    r=convert(client,content,cadastro=cadastro,mode=mode);assert r.status_code==200
    result=r.json();assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['cadastro_'+profile]['associacoes_retidas']==2
    assert len(result['revisao_cadastral_'+profile])==1
    output=rows(client,result['id']);assert all(row[2] is None and row[12] is None for row in output[1:])
    assert len(output)==(2 if mode=='A' else 3)


@pytest.mark.parametrize('profile',PROFILES)
def test_metricas_avisos_e_evidencias_cadastrais_tem_chaves_do_perfil(client,monkeypatch,profile):
    u,v=UNITS[profile]
    content=raw(profile,[debito(unidade=u,dias=90),debito(unidade=v,dias=90)])
    bind(monkeypatch,profile,content)
    cadastro=cad(profile,[ficha(unidade=u,nome='Pessoa Fictícia Divergente'),
        ficha(unidade=v,documento='MALFORMADO_FICTICIO',fone='0123-4567')])
    r=convert(client,content,cadastro=cadastro);assert r.status_code==200;result=r.json()
    assert result['cadastro_'+profile]['associacoes_retidas']==1
    assert result['cadastro_'+profile]['documentos_rejeitados_no_cadastro']==1
    assert result['resumo']['dividas_efetivamente_geradas']==2
    assert result['revisao_cadastral_'+profile][0]['motivo']=='PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO'
    assert 'MALFORMADO_FICTICIO' not in r.text


def test_configuracoes_contextos_e_resultados_isolam_os_dois_condominios(client,monkeypatch):
    ids={};contexts={}
    for profile in PROFILES:
        content=raw(profile);bind(monkeypatch,profile,content)
        ctx=identify(client,content).json()['contexto'];contexts[profile]=ctx
        if profile=='passaredo':
            saved=client.put('/api/contextos/'+ctx+'/configuracao',json={'revisao_esperada':0,'endereco':ADDRESS,'mapeamentos':[]})
            assert saved.status_code==200
        r=convert(client,content,context=ctx).json();ids[profile]=r['id']
        detail=client.get('/api/conversoes/'+r['id']+'/detalhes').json()
        assert detail['endereco_condominio']['cadastrado']==(profile=='passaredo')
    assert convert(client,raw('forest_hill'),context=contexts['passaredo']).status_code==409
    assert client.get('/api/conversoes/'+ids['forest_hill']+'/excel',headers={'origin':'http://outro.invalid'}).status_code==403
    assert client.get('/api/conversoes/'+ids['forest_hill']+'/operacional.xlsx').status_code==409
    rows(client,ids['passaredo'])
    assert client.get('/api/conversoes/'+ids['passaredo']+'/detalhes').status_code==404
    assert client.get('/api/conversoes/'+ids['forest_hill']+'/detalhes').status_code==200
    owner=client.cookies.get('conversor_session');old_headers=dict(client.headers);client.cookies.clear();boot(client)
    assert client.get('/api/contextos/'+contexts['forest_hill']+'/configuracao').status_code==404
    assert client.get('/api/conversoes/'+ids['forest_hill']+'/excel').status_code==404
    client.cookies.clear();client.cookies.set('conversor_session',owner);client.headers.update(old_headers)
    runtime=client.app.state.ciclo;runtime.relogio.now+=ep.RETENCAO+1;runtime.limpar()
    assert not runtime.results and not runtime.administracao.contextos
    assert not list(runtime.root.iterdir())
