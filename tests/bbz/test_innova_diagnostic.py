"""Piloto INNOVA: somente documentos desenhados do zero, sem dados de clientes."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import analisar, PedidoDiagnostico, reconhecer, ler, PERFIS
from tests.bbz.conftest import planilha, unidade, recibo
from tests.bbz.cadastro_fixtures import cadastro, ficha, dividir, CPF
from tests.web.test_mvp import KEY, aguardar

REF = date(2026, 10, 26)


def financeiro(unidades=None, **kwargs):
    return planilha(unidades, codigo='1392', nome='CONDOMINIO INNOVA BLUE', **kwargs)


def cadastro_innova(paginas=None, **kwargs):
    return cadastro(paginas, codigo='001392', nome='CONDOMINIO INNOVA BLUE', **kwargs)


def executar(tmp_path, raw=None, modo='A', **kwargs):
    return analisar(raw or financeiro(), PedidoDiagnostico(data_ref=REF, modo=modo, condominio='innova_blue'),
        processamento_id='sintetico_innova', destino=tmp_path, **kwargs)


def valores(path):
    w = load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    rows = list(w['Dados'].values); w.close()
    return rows


def test_identidade_e_perfil_exclusivos_sem_sufixo_363():
    p, codigo, formato = reconhecer(financeiro())
    assert codigo == '1392' and p['codigo_easycollector'] == '363'
    assert p['condominio_id'] == 'cond_bbz_innova_blue' and formato == 'bbz_inadimplencia_xlsx_v1'
    assert PERFIS['nova_york']['dias'] == 60 and PERFIS['innova_blue']['dias'] == 31
    assert PERFIS['innova_blue']['vigente_de'] is None


@pytest.mark.parametrize('bloco,numero', [('0','LOJA_FICTICIA'),('A','000017'),('B','0016'),
    ('C','0025'),('I','0022'),('S','0013'),('T','0025'),('INAT','PASTEL'),('A','00X1')])
def test_identificadores_preservam_bloco_e_grafia_com_largura_comprovada(tmp_path, bloco, numero):
    r = executar(tmp_path, financeiro([unidade(bloco=bloco, numero=numero)]))
    row = valores(tmp_path)[1]
    esperado = f'Bloc{bloco}-Uni' + ((numero.lstrip('0') or '0').zfill(4) if numero.isdigit() else numero)
    assert row[0] == 'BBZ' and row[1] == row[6] == row[24] == esperado
    assert row[25] == 'INNOVA BLUE' and r['decisoes'][0]['bloco'] == bloco
    assert not r['permite_exportacao_operacional'] and not r['autoriza_cobranca']


@pytest.mark.parametrize('dias,esperado', [(30,'nao_elegivel'), (31,'nao_elegivel'), (32,'elegivel')])
def test_limite_diagnostico_estrito_por_referencia_explicita(tmp_path, dias, esperado):
    r = executar(tmp_path, financeiro([unidade(recibos=[recibo(due=REF-timedelta(days=dias))])]))
    assert r['decisoes'][0]['situacao'] == esperado


@pytest.mark.parametrize('marcador', ['A','AJ','J','AE',None])
def test_marcadores_e_centavo_nao_herdam_exclusoes_tree(tmp_path, marcador):
    raw = financeiro([unidade(recibos=[recibo(marcador=marcador, componentes=[('COTA CONDOMINIAL AGO/2026','0.01')]),
        recibo(id='99000002')])])
    r = executar(tmp_path, raw)
    assert r['resumo']['dividas_efetivamente_geradas'] == 2 and r['resumo']['cotas_excluidas_por_veto'] == 0
    p,c,f = reconhecer(raw); lote,_ = ler(raw,p,c,f,'financeiro')
    assert [a.codigo_original for a in lote.boletos[0].apontamentos] == ([marcador] if marcador else [])


@pytest.mark.parametrize('sem_historico,encargos', [(False,('0','0','0')), (True,('0','0','0')), (False,('1','0','0'))])
def test_zero_original_nao_gera_divida_mas_motiva_um_cadastro(tmp_path, sem_historico, encargos):
    def mutar(w,s):
        if sem_historico:s['D7']=None; s['E7']=None
    raw = financeiro([unidade(recibos=[recibo(componentes=[('AJUSTE FICTICIO','0')],encargos=encargos),
        recibo(id='99000002',componentes=[('COTA CONDOMINIAL AGO/2026','100')])])],mutar=mutar)
    r = executar(tmp_path, raw, modo='B')
    assert r['resumo']['dividas_efetivamente_geradas'] == r['resumo']['cadastros_adicionais'] == 1
    assert r['resumo']['boletos_nao_selecionados_zero'] == 1 and r['resumo']['boletos_retidos'] == 0
    assert all(v is None for v in valores(tmp_path)[-1][24:30])
    zero = next(d for d in r['decisoes'] if d['valor']=='0.00')
    assert zero['motivo_selecao']=='valor_original_zero' and zero['situacao']=='nao_elegivel'


@pytest.mark.parametrize('campo', ['D7','E7','G7','L7'])
def test_nao_aceita_componente_incompleto_ou_financeiro_adulterado(tmp_path,campo):
    def mutar(w,s):
        if campo in ('D7','E7'):s[campo]=None
        else:s[campo]=101
    with pytest.raises(ErroLeitura):executar(tmp_path, financeiro(mutar=mutar))


def test_recibo_zerado_sem_hist_com_encargo_nao_e_presumido(tmp_path):
    def mutar(w,s):s['D7']=None; s['E7']=None
    raw=financeiro([unidade(recibos=[recibo(componentes=[('AJUSTE','0')],encargos=('1','0','0'))])],mutar=mutar)
    with pytest.raises(ErroLeitura,match='BBZ_COMPONENTE_INCOMPLETO'):executar(tmp_path,raw)


def test_componentes_negativos_preservados_e_descricao_cota_prioritaria(tmp_path):
    raw=financeiro([unidade(recibos=[recibo(componentes=[('COTA CONDOMINIAL AGO/2026','100'),
        ('DESCONTO COTA CONDOMINIAL','-10'),('LOCAÇÃO DE ESPAÇO 01/08/2026','5')])])])
    r=executar(tmp_path,raw);row=valores(tmp_path)[1]
    assert row[26]=='COTA 08/2026' and row[29]==95
    assert [Decimal(i['valor']) for i in r['decisoes'][0]['componentes']]==[Decimal(100),Decimal(-10),Decimal(5)]


@pytest.mark.parametrize('paginas', [1,2,3])
def test_cadastro_layout_deslocado_preserva_papeis_e_continuidades(tmp_path,paginas):
    def deslocar(i,rows):
        out=[]
        for x,y,t in rows:
            if t.startswith('Condomínio:'):t=t.replace('Condomínio:','Condominio:')
            x={468:464.46,161:159.79,481:476.57}.get(x,x)
            out.append((x,y,t))
        return out
    pdf=cadastro_innova(dividir(ficha(locatario=True,pagador=True),paginas),mutar=deslocar)
    r=executar(tmp_path,cadastro=pdf)
    assert r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1
    assert r['cadastro_bbz']['resumo']['continuidades']==paginas-1
    row=valores(tmp_path)[1]; assert row[2]==CPF and 'locatario@example.invalid' not in row


def test_associacao_incompativel_retida_sem_suprimir_divida(tmp_path):
    r=executar(tmp_path,cadastro=cadastro_innova([ficha(nome='OUTRO TITULAR FICTICIO')]))
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==1
    assert valores(tmp_path)[1][2] is None and r['resumo']['dividas_efetivamente_geradas']==1


def test_cadastro_nova_york_nao_e_associado_ao_innova(tmp_path):
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):
        executar(tmp_path,cadastro=cadastro())


def test_colisao_apos_normalizacao_bloqueia(tmp_path):
    raw=financeiro([unidade(numero='0017'),unidade(numero='000017',recibos=[recibo(id='99000002')])])
    with pytest.raises(ErroLeitura,match='BBZ_UNIDADE_DUPLICADA'):executar(tmp_path,raw)


def test_inat_e_zero_sao_blocos_distintos_sem_equivalencia(tmp_path):
    raw=financeiro([unidade(bloco='INAT',numero='PASTEL'),unidade(bloco='0',numero='PASTEL',recibos=[recibo(id='99000002')])])
    r=executar(tmp_path,raw)
    assert r['resumo']['unidades']==2
    assert {v[1] for v in valores(tmp_path)[1:]}=={'BlocINAT-UniPASTEL','Bloc0-UniPASTEL'}


def test_upload_opcional_modos_e_download_autenticado(tmp_path):
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY)) as c:
        c.post('/api/session',json={'chave':KEY})
        raw=financeiro([unidade(recibos=[recibo(),recibo(id='99000002',componentes=[('AJUSTE','0')])])])
        for modo in ('A','B'):
            r=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':modo,'condominio':'innova_blue'},
                files={'inadimplencia':('nome_irrelevante.xlsx',raw),'cadastro':('outro_nome.pdf',cadastro_innova())}))
            assert r['estado']=='concluido'
            assert r['resultado']['resumo']['dividas_efetivamente_geradas']==1
            assert r['resultado']['resumo']['cadastros_adicionais']==(modo=='B')
            assert c.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409
            w=load_workbook(BytesIO(c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').content))
            assert w['Dados'].max_column==30 and w['Dados']['C2'].data_type=='s';w.close()


@pytest.mark.parametrize('componentes,rotulo,competencia', [
    ([('COND AGO/2026','100')], 'COTA 08/2026','2026-08'),
    ([('COND AGO/26','100')], 'RECIBO 99000001',None),
    ([('CONDOMÍNIO AGO/2026','100'),('LOCAÇÃO DE ESPAÇO 01/08/2026','5')], 'COTA 08/2026','2026-08'),
    ([('CONDOMINIO AGO/2026','100'),('CONDOMINIO JUL/2026','5')], 'RECIBO 99000001',None),
    ([('CONDOMINIO AGO/2026','100'),('CONDOMINIO AGO/26','5')], 'RECIBO 99000001',None),
    ([('CONDOMINIO','100')], 'RECIBO 99000001',None),
    ([('REEMBOLSO SINISTRO','100')], 'REEMBOLSO SINISTRO',None),
])
def test_politica_documental_sem_inferir_competencia(tmp_path,componentes,rotulo,competencia):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(componentes=componentes)])]))
    assert valores(tmp_path)[1][26]==rotulo and r['decisoes'][0]['competencia']==competencia


def test_assinatura_condominio_nao_altera_politica_historica_nova_york(tmp_path):
    raw=planilha([unidade(recibos=[recibo(componentes=[('CONDOMINIO AGO/2026','100')])])])
    r=analisar(raw,PedidoDiagnostico(data_ref=REF,modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert valores(tmp_path)[1][26]=='RECIBO 99000001'
    assert next(iter(r['descricoes_recibos'].values()))['politica_versao']=='1.1.0'


@pytest.mark.parametrize('documento', ['', '00000000190','00000000000191'])
def test_documento_opcional_invalido_e_cnpj_textual(tmp_path,documento):
    r=executar(tmp_path,cadastro=cadastro_innova([ficha(documento=documento)]))
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');c=w['Dados']['C2']
    assert c.value==('00000000000191' if len(documento)==14 else None)
    if c.value:assert c.data_type=='s' and c.number_format=='@'
    assert r['resumo']['dividas_efetivamente_geradas']==1;w.close()


def test_cpf_conflitante_retido_sem_transferir_contatos(tmp_path):
    r=executar(tmp_path,cadastro=cadastro_innova([ficha(segundo_documento='00000000272')]))
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==1
    row=valores(tmp_path)[1];assert row[2] is None and all(v is None for v in row[11:24])


def test_fiscal_na_posicao_correta_continua_obrigatorio(tmp_path):
    def mutar(i,rows):return [(464.46 if t.startswith('CNPJ:') else x,y,'CNPJ:' if t.startswith('CNPJ:') else t) for x,y,t in rows]
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_IDENTIDADE_INCOMPLETA'):
        executar(tmp_path,cadastro=cadastro_innova(mutar=mutar))


@pytest.mark.parametrize('sufixo,esperado', [(' - 1','SUFIXO_HISTORICO_DE_PARCELA_SEPARADO'),
    (' - 2','DESCRICAO_DOCUMENTAL_DIFERE_DO_HISTORICO'),
    (' / OBSERVACAO','DESCRICAO_DOCUMENTAL_DIFERE_DO_HISTORICO')])
def test_sufixo_historico_so_e_formatacao_quando_comprovado(tmp_path,sufixo,esperado):
    raw=financeiro([unidade(recibos=[recibo(componentes=[('COND AGO/2026','100')])])])
    executar(tmp_path/'antes',raw)
    before=(tmp_path/'antes/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    w=load_workbook(BytesIO(before));w['Dados']['AA2']='COTA 08/2026'+sufixo
    out=BytesIO();w.save(out);w.close()
    r=executar(tmp_path/'depois',raw,referencia=out.getvalue())
    assert any(d['codigo']==esperado for d in r['comparacao']['contrato_atual']['divergencias'])
    assert (tmp_path/'depois/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==before


def test_politica_nao_registrada_nao_e_substituida_silenciosamente(tmp_path,monkeypatch):
    monkeypatch.setitem(PERFIS,'innova_blue',dict(PERFIS['innova_blue'],politica_descricoes='nao_registrada@9'))
    with pytest.raises(ErroLeitura,match='POLITICA_DESCRICOES_BBZ_NAO_REGISTRADA'):executar(tmp_path)


@pytest.mark.parametrize('codigo,nome', [('117','CONDOMINIO EDIFICIO WIN'),
    ('286','CONDOMINIO EDIFICIO NOVA REBOUÇAS'), ('575','CONDOMINIO JARDINS DO BRASIL')])
def test_condominios_bbz_respeitam_habilitacao_incremental(codigo,nome):
    if codigo=='286':
        perfil,origem,_=reconhecer(planilha(codigo=codigo,nome=nome))
        assert origem=='286' and perfil['id']=='nova_reboucas'
    else:
        with pytest.raises(ErroLeitura,match='CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO'):
            reconhecer(planilha(codigo=codigo,nome=nome))
