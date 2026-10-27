"""Descrições e competências integralmente sintéticas; não contêm recibos reais."""
from datetime import date
import json

from openpyxl import load_workbook
from pydantic import ValidationError
import pytest

from conversor.application.debt_descriptions import (
    POLITICA_BBZ, interpretar_lote_bbz, interpretar_recibo,
)
from conversor.domain.debt_description import DescricaoRecibo, PoliticaDescricoes, RegraHistorico
from conversor.web.service import PedidoDiagnostico, analisar
from tests.bbz.conftest import recibo, unidade
from tests.bbz.test_bbz_reader import ler


def lote(xlsx, historias, **kw):
    return ler(xlsx([unidade(recibos=[recibo(componentes=[(h, '10.00') for h in historias], **kw)])]))


@pytest.mark.parametrize('mes,numero', [('JAN','01'),('FEV','02'),('MAR','03'),('ABR','04'),('MAI','05'),
    ('JUN','06'),('JUL','07'),('AGO','08'),('SET','09'),('OUT','10'),('NOV','11'),('DEZ','12')])
def test_cota_competencia_explicita_portugues(xlsx,mes,numero):
    b=lote(xlsx,[f'COTA CONDOMINIAL {mes}/2025']).boletos[0];r=interpretar_recibo(b)
    assert r.descricao==f'COTA {numero}/2025' and r.competencia==f'2025-{numero}'
    assert r.estado=='comprovada' and not r.ambigua and not r.alertas
    assert r.identificador_origem==b.identificador and b.competencia is None


@pytest.mark.parametrize('historico',['COTA CONDOMINIAL 08/2025', 'Cota condominial competência: agosto/2025'])
def test_vencimento_nao_define_competencia_e_parcela_nao_entra_no_rotulo(xlsx,tmp_path,historico):
    raw=xlsx([unidade(recibos=[recibo(componentes=[(historico,'100.00')],due=date(2025,12,1))])])
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    d=next(iter(r['descricoes_recibos'].values()))
    assert d['descricao']=='COTA 08/2025'and d['competencia']=='2025-08'
    extraido=json.loads((tmp_path/'canonico_extraido.json').read_text())
    assert extraido['boletos'][0]['competencia']is None
    assert extraido['boletos'][0]['identificador']==d['identificador_origem']
    assert r['manifesto_diagnostico']['canonico_extraido']['nome']=='canonico_extraido.json'
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');s=w['Dados']
    assert s['AA2'].value=='COTA 08/2025'and s['AB2'].value==1 and s['AC2'].value.date()==date(2025,12,1)
    assert s.max_column==30 and s['AA1'].value=='NM_DIVIDA_CEDENTE';w.close()


def test_reembolso_sem_competencia_ou_data_fabricada(xlsx):
    b=lote(xlsx,['REEMBOLSO SINISTRO']).boletos[0];r=interpretar_recibo(b)
    assert r.descricao=='REEMBOLSO SINISTRO'and r.classificacao=='reembolso_sinistro'
    assert r.competencia is None and r.estado_competencia=='nao_aplicavel'


def test_data_do_evento_de_locacao_nao_vira_competencia(xlsx):
    r=interpretar_recibo(lote(xlsx,['LOCAÇÃO DE ESPAÇO 01/07/2025']).boletos[0])
    assert r.descricao=='LOCAÇÃO DE ESPAÇO'and r.estado=='comprovada'
    assert r.competencia is None and r.estado_competencia=='nao_aplicavel'


def test_componentes_compativeis_ordem_e_valor_nao_elegem_natureza(xlsx):
    h=['GAS PISCINA','FUNDO DE RESERVA JUL/2025','COTA CONDOMINIAL AGO/2025','AGUA FRIA JUN/25 2,50 M3',
       'PROJETO SEGURANCA PC. 01/05','FACHADA PC. 01/12','RECOMPOSICAO SALDO 02/10',
       'REFORMA ESPACO PET -PC UNICA','CONSUMO ENERGIA','AGUA QUENTE MAI25 12345 M3','GAS SISTEMA JAN/25']
    for historias in (h,list(reversed(h))):
        r=interpretar_recibo(lote(xlsx,historias).boletos[0])
        assert r.descricao=='COTA 08/2025'and len(r.componentes)==len(h)
        assert r.competencias_encontradas==('2025-08',)


@pytest.mark.parametrize('historias,codigo', [
    (['COTA CONDOMINIAL AGO/2025','REEMBOLSO SINISTRO'],'BBZ_NATUREZAS_MISTAS'),
    (['COTA CONDOMINIAL AGO/2025','COBRANCA EXTRAORDINARIA'],'BBZ_NATUREZAS_MISTAS'),
    (['COTA CONDOMINIAL AGO/2025','LOCACAO DE ESPACO 01/07/2025'],'BBZ_NATUREZAS_MISTAS'),
    (['COTA CONDOMINIAL AGO/2025','LANCAMENTO DESCONHECIDO FICTICIO'],'BBZ_HISTORICO_NAO_RECONHECIDO_OU_AMBIGUO'),
    (['GAS PISCINA'],'BBZ_NATUREZA_PRINCIPAL_NAO_COMPROVADA'),
    (['COTA CONDOMINIAL AGO/2025','COTA CONDOMINIAL SET/2025'],'BBZ_COMPETENCIAS_CONFLITANTES'),
    (['COTA CONDOMINIAL AGO/2025','COTA CONDOMINIAL'],'BBZ_COMPETENCIA_PARCIAL_NOS_PRINCIPAIS'),
    (['REEMBOLSO SINISTRO','FUNDO DE RESERVA'],'BBZ_COMPONENTE_DE_OUTRA_OBRIGACAO'),
])
def test_evidencia_insuficiente_ou_diferentes_obrigacoes_tem_descricao_neutra(xlsx,historias,codigo):
    b=lote(xlsx,historias).boletos[0];r=interpretar_recibo(b)
    assert r.descricao==f'RECIBO {b.identificador}'and r.estado=='pendente'and r.ambigua
    assert codigo in r.alertas and r.competencia is None
    assert len(r.componentes)==len(historias)


def test_cota_sem_competencia_nao_herda_periodo_de_acessorio(xlsx):
    r=interpretar_recibo(lote(xlsx,['COTA CONDOMINIAL','FUNDO DE RESERVA AGO/2025']).boletos[0])
    assert r.descricao=='COTA'and r.competencia is None and r.estado_competencia=='ausente'
    assert 'BBZ_COMPETENCIA_AUSENTE'in r.alertas


def test_competencia_invalida_nao_ganha_seculo_ou_correcao_por_inferencia(xlsx):
    for texto in ('COTA CONDOMINIAL AGO/25','COTA CONDOMINIAL AGO/0000','COTA CONDOMINIAL 13/2025'):
        r=interpretar_recibo(lote(xlsx,[texto]).boletos[0])
        assert r.estado=='pendente'and r.competencia is None and r.descricao.startswith('RECIBO ')


def test_historico_vazio_ou_legenda_nao_define_natureza(xlsx):
    b=lote(xlsx,['FICTICIO']).boletos[0]
    for historia in ('','OBSERVACAO COTA CONDOMINIAL AGO/2025','LEGENDA REEMBOLSO SINISTRO','A AJ J AE'):
        item=b.composicao.itens[0].model_copy(update={'descricao_original':historia})
        mod=b.model_copy(update={'composicao':b.composicao.model_copy(update={'itens':(item,)})})
        assert interpretar_recibo(mod).estado=='pendente'


@pytest.mark.parametrize('marcador',[None,'A','AJ','J','AE'])
def test_marcadores_e_negativos_nao_mudam_descricao_ou_selecao(xlsx,tmp_path,marcador):
    raw=xlsx([unidade(recibos=[recibo(marcador=marcador,componentes=[('COTA CONDOMINIAL AGO/2025','120.00'),
                                                                 ('DESCONTO COTA CONDOMINIAL','-20.00')])])])
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['decisoes'][0]['valor']=='100.00'
    desc=next(iter(r['descricoes_recibos'].values()))
    assert desc['descricao']=='COTA 08/2025'and desc['componentes'][1]['valor_original']=='-20.00'
    assert not r['autoriza_cobranca']and not r['permite_exportacao_operacional']


def test_valor_zero_continua_retido_sem_perda_da_descricao(xlsx,tmp_path):
    raw=xlsx([unidade(recibos=[recibo(componentes=[('COTA CONDOMINIAL AGO/2025','0.00')])])])
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path)
    assert r['resumo']['dividas_efetivamente_geradas']==0 and r['decisoes'][0]['valor']=='0.00'
    assert next(iter(r['descricoes_recibos'].values()))['descricao']=='COTA 08/2025'
    assert 'VALOR_ORIGINAL_NAO_POSITIVO'in r['decisoes'][0]['bloqueios']


def test_rastreabilidade_conta_celulas_hash_e_idempotencia_sem_mutar_extracao(xlsx):
    original=lote(xlsx,['COTA CONDOMINIAL AGO/2025','FUNDO DE RESERVA AGO/2025']);antes=original.model_dump_json()
    enriquecido,desc=interpretar_lote_bbz(original);de_novo,desc2=interpretar_lote_bbz(enriquecido)
    assert original.model_dump_json()==antes and original.boletos[0].competencia is None
    assert enriquecido.boletos[0].competencia=='2025-08'
    assert enriquecido.model_dump_json()==de_novo.model_dump_json()and desc==desc2
    b=enriquecido.boletos[0];d=desc[b.id]
    assert d.identificador_origem==original.boletos[0].identificador and d.boleto_id==original.boletos[0].id
    for c in d.componentes:
        assert c.conta and c.aba=='RELATORIO SINTETICO'
        assert c.origem_historico.identificador.endswith('_E')and c.origem_conta.identificador.endswith('_D')
        assert c.origem_historico.sha256==b.origens[0].sha256 and c.origem_historico.linha==c.origem.linha
    assert len(d.politica_sha256)==64 and d.politica_versao=='1.0.0'


def test_conflito_com_competencia_canonica_nao_e_sobrescrito(xlsx):
    original=lote(xlsx,['COTA CONDOMINIAL AGO/2025'])
    b=original.boletos[0].model_copy(update={'competencia':'2025-09'})
    enriched,desc=interpretar_lote_bbz(original.model_copy(update={'boletos':(b,)}))
    assert enriched.boletos[0].competencia=='2025-09'and desc[b.id].estado=='pendente'
    assert 'BBZ_COMPETENCIAS_CONFLITANTES'in desc[b.id].alertas


def test_ambiguidade_de_regras_nao_escolhe_a_primeira(xlsx):
    extra=RegraHistorico(id='sobreposta',padrao='.*',papel='principal',natureza='teste',rotulo='TESTE')
    p=PoliticaDescricoes.model_validate(POLITICA_BBZ.model_dump()|{'regras':(*POLITICA_BBZ.regras,extra)})
    r=interpretar_recibo(lote(xlsx,['COTA CONDOMINIAL AGO/2025']).boletos[0],politica=p)
    assert r.estado=='pendente'and r.componentes[0].resultado=='ambiguo'
    assert len(r.componentes[0].regras_candidatas)==2


def test_nova_natureza_por_politica_sem_condominio_ou_recibo_fixo(xlsx):
    regra=RegraHistorico(id='taxa_sintetica',padrao='TAXA DE MUDANCA',papel='principal',
                        natureza='taxa_mudanca',rotulo='TAXA DE MUDANÇA')
    p=PoliticaDescricoes(id='politica_futura_sintetica',versao='1',namespace_formato=POLITICA_BBZ.namespace_formato,regras=(regra,))
    r=interpretar_recibo(lote(xlsx,['TAXA DE MUDANCA']).boletos[0],politica=p)
    assert r.classificacao=='taxa_mudanca'and r.descricao=='TAXA DE MUDANÇA'


def test_politica_tipagem_schema_e_regras_conflitantes():
    assert 'componentes'in DescricaoRecibo.model_json_schema()['properties']
    with pytest.raises(ValidationError,match='REGRA_DESCRICAO_DUPLICADA'):
        PoliticaDescricoes.model_validate(POLITICA_BBZ.model_dump()|{'regras':(POLITICA_BBZ.regras[0],)*2})


def test_regex_invalida_rejeitada_sem_regra_parcial():
    with pytest.raises(ValidationError,match='PADRAO_DE_HISTORICO_INVALIDO'):
        RegraHistorico(id='invalida',padrao='[',papel='principal',natureza='teste',rotulo='TESTE')


def test_mesmo_historico_de_outro_namespace_nao_e_classificado(xlsx):
    b=lote(xlsx,['COTA CONDOMINIAL AGO/2025']).boletos[0]
    item=b.composicao.itens[0];origem=item.origem.model_copy(update={'leitor_versao':'fl_inadimplencia_real_v1@1'})
    outro=b.model_copy(update={'composicao':b.composicao.model_copy(update={'itens':(item.model_copy(update={'origem':origem}),)})})
    assert interpretar_recibo(outro).estado=='pendente'


@pytest.mark.parametrize('modo',[ 'A','B'])
def test_alerta_de_descricao_nao_exclui_divida_e_modos_nao_alteram_financeiro(xlsx,tmp_path,modo):
    raw=xlsx([unidade(recibos=[recibo(),recibo(id='99000002',due=date(2026,10,1))])])
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo=modo),processamento_id='sintetico',destino=tmp_path)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==(1 if modo=='B'else 0)
    assert len(r['descricoes_recibos'])==2 and r['decisoes'][0]['situacao']=='elegivel'
    assert any(o['codigo']=='BBZ_CLASSIFICACAO_DESCRICAO_PENDENTE'and o['gravidade']=='alerta'for o in r['ocorrencias'])
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(w['Dados'].values)
    assert len(rows[0])==30 and rows[1][26]=='RECIBO 99000001'
    if modo=='B':assert all(v is None for v in rows[-1][24:30])
    w.close()
