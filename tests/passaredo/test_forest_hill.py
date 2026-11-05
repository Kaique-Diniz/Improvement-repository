"""Forest Hill: fontes inteiramente fictícias; nenhum exemplo privado no Git."""
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.domain.forest_hill import complemento_unidade, rotulo_descricao
from conversor.domain.template import Template
from conversor.readers.forest_hill import identificar
from conversor.readers.text_support import ErroLeitura
from conversor.web.ephemeral import criar_app_efemero
from conversor.web.service import PedidoDiagnostico, analisar, reconhecer, ler, PERFIS
from .fixtures import CPF, CNPJ, OUTRO_CPF, REF, financeiro, cadastro, debito, ficha

AV = 'AV.P02 231'
RUA = 'RUA 18 347'
SUFIXO = '-CONDOMINIO RESIDENCIAL FOREST HILL'


def fonte(registros=None, **kw):
    return financeiro(registros if registros is not None else [debito(unidade=AV, dias=31)], **kw)


def complemento(registros=None, **kw):
    return cadastro(registros if registros is not None else [ficha(unidade=AV)], **kw)


def executar(path, raw=None, cad=None, modo='A'):
    return analisar(raw if raw is not None else fonte(), PedidoDiagnostico(
        data_ref=REF, modo=modo, condominio='forest_hill'), processamento_id='forest_hill_sintetico',
        destino=path, cadastro=cad, historico=(), estado_historico='nao_disponivel')


def saida(path):
    b=load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:return list(b['Dados'].values)
    finally:b.close()


@pytest.mark.parametrize('unidade,esperado',[(AV,'AVP02-UNI231'),(RUA,'RUA18-UNI0347'),
    ('RUA 01 7','RUA01-UNI0007'),('RUA 03 87','RUA03-UNI0087')])
def test_unidade_documental_sem_perder_original(tmp_path,unidade,esperado):
    assert complemento_unidade(unidade)==esperado
    raw=fonte([debito(unidade=unidade,dias=31)])
    result=executar(tmp_path,raw)
    row=saida(tmp_path)[1]
    assert row[1]==row[24]==esperado+SUFIXO and row[6]==esperado
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    assert canonical['unidades'][0]['unidade_original']==unidade
    assert canonical['unidades'][0]['bloco_original']==''
    assert result['fontes'][0]['sha256']==sha256(raw).hexdigest()


@pytest.mark.parametrize('unidade',['','007','RUA18 347','RUA 18 1234','AV.P2 231',
    'AV.P02 23','AV.P02 231/1','RUA 18 3 extra','RUA  18 347','RUA 18 ３４７'])
def test_gramatica_propria_bloqueia_identidade_estrutural_ambigua(unidade):
    with pytest.raises(ValueError):complemento_unidade(unidade)
    with pytest.raises(ErroLeitura):
        reconhecer(fonte([debito(unidade=unidade)]),perfil_informado='forest_hill')
    with pytest.raises(ErroLeitura):
        reconhecer(complemento([ficha(unidade=unidade)]),cadastro=True,perfil_informado='forest_hill')


@pytest.mark.parametrize('dias,esperado',[(29,0),(30,0),(31,1),(60,1),(61,1)])
def test_prazo_provisorio_estrito_nao_usa_dias_fonte(tmp_path,dias,esperado):
    result=executar(tmp_path,fonte([debito(unidade=AV,dias=dias,dias_fonte=999)]))
    assert result['resumo']['dividas_efetivamente_geradas']==esperado
    assert result['decisoes'][0]['vencimento']==(REF-timedelta(days=dias)).isoformat()
    assert result['cadastro_forest_hill']['dias_informados_divergentes']==1
    assert not result['autoriza_cobranca'] and not result['permite_exportacao_operacional']


def test_layout_e_hash_nao_substituem_selecao_explicita(monkeypatch):
    raw=fonte()
    monkeypatch.setitem(PERFIS['forest_hill']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    with pytest.raises(ErroLeitura,match='INFORME_PERFIL'):reconhecer(raw)
    assert reconhecer(raw,perfil_informado='forest_hill')[0]['id']=='forest_hill'
    with pytest.raises(ErroLeitura):reconhecer(financeiro(),perfil_informado='forest_hill')


@pytest.mark.parametrize('tipo',['fechamento','formula','aba','apos_fechamento','geracao'])
def test_selecao_nao_dispensa_estrutura_e_fechamento(tipo):
    def mutar(w,s):
        if tipo=='fechamento':s.cell(s.max_row-1,1).value='1631 item(ns)'
        if tipo=='formula':s['F2']='=1+1'
        if tipo=='aba':s.title='Outra'
        if tipo=='apos_fechamento':s.append(['CONTEUDO FICTICIO NAO AUTORIZADO'])
        if tipo=='geracao':s.cell(s.max_row,1).value='Gerado em 99/99/2026 12:00'
    with pytest.raises(ErroLeitura):reconhecer(fonte(mutar=mutar),perfil_informado='forest_hill')


def test_colisao_de_codificacao_nao_funde_unidades(tmp_path):
    with pytest.raises(ErroLeitura,match='CEDENTE_AMBIGUO'):
        executar(tmp_path,fonte([debito(unidade='RUA 18 7'),debito(unidade='RUA 18 007')]))


@pytest.mark.parametrize('descricao,mes',[
    ('DESPESA FICTICIA',False),('COTA FICTICIA',False),('Acordo 1/12',True),
    ('Acordo 1/12 - 2/24',True),('ACORDO ESPECIAL FICTICIO',True),
    ('ACORDO 123/2025 - 1/12',False),('acordo 42/2026',False),
    ('Taxa de roçagem',True),('Multa de Infração',True),('Multa por Infração 321',True),
    ('HONORARIOS FICTICIOS',False),('COBRANCA JUDICIAL FICTICIA',False),
])
def test_rotulo_documental_nao_altera_original_financeiro(tmp_path,descricao,mes):
    raw=fonte([debito(unidade=AV,dias=31,descricao=descricao,valor='123.45',encargos=('1','2','3','4'))])
    result=executar(tmp_path,raw)
    row=saida(tmp_path)[1]
    esperado=descricao+(f' {REF-timedelta(days=31):%m/%Y}' if mes else '')+' - 1'
    assert row[26]==esperado and row[29]==123.45 and row[27]==1
    assert result['decisoes'][0]['competencia'] is None
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    original=next(json.loads(r['valores_originais'][0]) for r in canonical['ressalvas'] if r['codigo']=='PASSAREDO_LANCAMENTO_ORIGINAL')
    assert original['descricao']==descricao and original['honorarios']=='4.00' and original['atual']=='133.45'
    assert result['resumo']['dividas_efetivamente_geradas']==1


def test_duplicidades_e_parcelas_elegiveis_nao_sao_perdidas(tmp_path):
    item=debito(unidade=AV,dias=31,valor='12.34')
    result=executar(tmp_path,fonte([debito(unidade=AV,dias=30),item,item.copy(),
        debito(unidade=AV,dias=60,descricao='Acordo 1/2',valor='23.45')]))
    rows=saida(tmp_path)
    assert len(rows)==4 and [r[27] for r in rows[1:]]==[1,2,3]
    assert [r[29] for r in rows[1:]]==[23.45,12.34,12.34]
    assert len({x['boleto_id'] for x in result['linhas_teste']})==3
    assert rows[0]==Template(id='t',nome='t',versao='1.1',espaco_final_coluna_27=False).cabecalhos_fisicos
    assert all(len(r)==30 for r in rows) and rows[0][26]=='NM_DIVIDA_CEDENTE'


def test_cadastro_opcional_retencao_cadastral_nao_exclui_financeiro(tmp_path):
    cad=complemento([ficha(unidade=AV,nome='Pessoa Ficticia Divergente')])
    result=executar(tmp_path,cad=cad)
    assert result['cadastro_forest_hill']['associacoes_retidas']==1
    assert result['resumo']['dividas_efetivamente_geradas']==1
    row=saida(tmp_path)[1]
    assert row[2] is None and row[11] is None and row[21] is None
    assert row[3]=='Pessoa Fictícia Alfa'


@pytest.mark.parametrize('documento,secundario,esperado,retido',[
    (CPF,'',CPF,0),('00000000191','','00000000191',0),
    ('texto ficticio '+CPF,'',None,0),('11111111111','',None,0),('',CPF,CPF,0),
    (CPF,OUTRO_CPF,None,1),
])
def test_cadastro_reutiliza_validacoes_a1_sem_copiar_template(tmp_path,documento,secundario,esperado,retido):
    result=executar(tmp_path,cad=complemento([ficha(unidade=AV,documento=documento,
        outro_documento=secundario,fone='0123-4567;123456789012')]))
    row=saida(tmp_path)[1]
    assert row[2]==esperado and result['cadastro_forest_hill']['associacoes_retidas']==retido
    if not retido:
        assert row[11] is None and row[12]=='01234567' and row[14] is None
    if documento.startswith('texto') or documento=='11111111111':
        canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
        assert any(documento in r['valores_originais'] for r in canonical['ressalvas'] if r['codigo']=='PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO')


@pytest.mark.parametrize('nome,retido',[
    ('Empresa Ficticia Alfa E Beta Ltda',0),('Pessoa Ficticia Alfa / Pessoa Ficticia Beta',1),
])
def test_cnpj_nao_substitui_evidencia_de_titularidade(tmp_path,nome,retido):
    result=executar(tmp_path,fonte([debito(unidade=AV,nome=nome,dias=31)]),
        complemento([ficha(unidade=AV,nome=nome,documento=CNPJ)]))
    assert result['cadastro_forest_hill']['associacoes_retidas']==retido
    assert saida(tmp_path)[1][2]==(None if retido else CNPJ)


def test_entradas_identicas_preservam_ids_decisoes_e_xlsx(tmp_path):
    raw=fonte([debito(unidade=AV,dias=31),debito(unidade=RUA,dias=61)])
    cad=complemento([ficha(unidade=AV),ficha(unidade=RUA)])
    a=executar(tmp_path/'a',raw,cad);b=executar(tmp_path/'b',raw,cad)
    assert a['decisoes']==b['decisoes'] and a['linhas_teste']==b['linhas_teste']
    assert saida(tmp_path/'a')==saida(tmp_path/'b')


def test_template_divergente_nao_substitui_documento_comprovado(tmp_path):
    raw=fonte();cad=complemento()
    executar(tmp_path/'base',raw,cad)
    b=load_workbook(tmp_path/'base'/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:
        b['Dados']['C2']=OUTRO_CPF
        b['Dados']['D2']='Pessoa Ficticia Sem Vinculo'
        stream=BytesIO();b.save(stream)
    finally:b.close()
    result=analisar(raw,PedidoDiagnostico(data_ref=REF,modo='A',condominio='forest_hill'),
        processamento_id='forest_hill_sintetico',destino=tmp_path/'confronto',cadastro=cad,
        referencia=stream.getvalue(),historico=(),estado_historico='nao_disponivel')
    assert saida(tmp_path/'confronto')[1][2]==CPF
    assert saida(tmp_path/'confronto')[1][3]=='Pessoa Fictícia Alfa'
    assert result['resumo']['dividas_efetivamente_geradas']==1


def test_autenticacao_isolamento_erro_e_descarte_efemero(tmp_path,caplog):
    app=criar_app_efemero(acesso='chave-ficticia-forest-hill',area_temporaria=tmp_path)
    with TestClient(app,base_url='http://127.0.0.1') as c:
        assert c.post('/api/conversoes').status_code==401
        c.post('/api/sessao',json={'chave':'chave-ficticia-forest-hill'})
        assert any(p['id']=='forest_hill' for p in c.get('/api/config').json()['perfis'])
        r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':'forest_hill'},
            files={'inadimplencia':('qualquer-nome.xlsx',fonte()),'cadastro':('cadastro.xlsx',complemento())})
        assert r.status_code==200
        result=r.json();url='/api/conversoes/'+result['id']
        assert result['cadastro_forest_hill']['documentos_validos_vinculados']==1
        assert not list(app.state.ciclo.root.iterdir())
        other=TestClient(app,base_url='http://127.0.0.1')
        try:
            assert other.get(url+'/excel').status_code==401
            other.post('/api/sessao',json={'chave':'chave-ficticia-forest-hill'})
            assert other.get(url+'/excel').status_code==404
        finally:
            other.close()
        assert c.get(url+'/operacional.xlsx').status_code==409
        download=c.get(url+'/excel');assert download.status_code==200
        assert c.get(url+'/excel').status_code==404
        assert not list(app.state.ciclo.root.iterdir())
        bad=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':'forest_hill'},
            files={'inadimplencia':('invalido.xlsx',b'CONTEUDO_FICTICIO_NAO_EXIBIR')})
        assert bad.status_code==422 and 'CONTEUDO_FICTICIO_NAO_EXIBIR' not in bad.text+caplog.text
        assert not list(app.state.ciclo.root.iterdir())
