"""Preparação 4.3B: fonte sintética → canônico → predicados puros, sem planos ativos."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

import pytest

from conversor.application.reading import resultado_leitura
from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.billing_rules import PlanoCobranca, PredicadoApontamento, PredicadoDias, PredicadoValor
from conversor.readers.contracts import FonteProtegida
from conversor.readers.operational import RegistroLeitores
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from conversor.rules.conditions import ContextoCondicao, avaliar_condicao
from examples.fase3.layouts_sinteticos import pdf_posicionado
from examples.fase4.habita_mapeamento_sintetico import paginas_mapeamento, pdf_mapeamento

FIXTURE = json.loads(Path('tests/fixtures/synthetic/habita_mapeamento_4_3b.json').read_text())
FORMATO = 'fmt_habita_sintetico_mapeamento'
VERSAO = 'habita_composicao_real_v1@1'


def ler(blob):
    class Fontes:
        def ler(self, fonte):
            return blob

    class Contextos:
        def resolver(self, fonte, *, formato_id, condominio_id):
            return ContextoLeitura(condominio_id, 'adm_sintetica', formato_id,
                                   fonte.arquivo_id, '9999', leitor_versao=VERSAO)

    fonte = FonteProtegida(arquivo_id='pdf_inventado_mapeamento', sha256=sha256(blob).hexdigest())
    lote = RegistroLeitores(Fontes(), Contextos()).obter('habita_composicao_real_v1', '1').ler(
        fonte, formato_id=FORMATO, condominio_id='cond_sintetico_mapeamento')
    return lote


def observar(lote, boleto, condicao, *, cobertura=False, data_ref=None):
    # Plano didático apenas em memória para respeitar o contrato do contexto.
    # Sem repositório, aprovação, assinatura, ativação ou execução do motor.
    plano = PlanoCobranca(id='inspecao_sintetica', condominio_id=lote.unidades[0].condominio_id,
                         versao='0.0.1', natureza='sintetico', vigente_de='2026-01-01',
                         fontes=(boleto.origens[0],), regras=({
                             'id': 'predicado_didatico', 'prioridade': 0, 'alvo': 'boleto',
                             'quando': condicao, 'acao': 'alertar', 'motivo_codigo': 'TESTE_CAMPO',
                             'fonte_id': boleto.origens[0].identificador},))
    covers = (CoberturaApontamentos(boleto_id=boleto.id, namespace=FORMATO,
                                   origens=boleto.origens),) if cobertura else ()
    entrada = EntradaSimulacao(lote=lote, fatos=(), ocorrencias_anteriores=(),
                              coberturas_apontamentos=covers)
    ctx = ContextoCondicao(plano=plano, entrada=entrada,
                          data_ref=data_ref or date.fromisoformat(FIXTURE['data_ref']),
                          unidade=lote.unidades[0], boleto=boleto)
    return avaliar_condicao(condicao, ctx)


@pytest.fixture
def lote():
    return ler(pdf_mapeamento(FIXTURE['cotas']))


@pytest.mark.parametrize('indice', range(6))
def test_mapeia_original_integral_e_encargos_separados(lote, indice):
    spec = FIXTURE['cotas'][indice]
    b = lote.boletos[indice]
    assert b.composicao.total_original == Decimal(spec['esperado_original'])
    assert tuple(i.valor for i in b.composicao.itens) == tuple(Decimal(v[0]) for v in spec['itens'])
    assert (b.multa, b.correcao, b.juros) == tuple(
        sum((Decimal(item[i]) for item in spec['itens']), Decimal('0.00')) for i in (1, 2, 3))
    assert b.composicao.total_original + b.multa + b.correcao + b.juros == Decimal(spec['esperado_atualizado'])
    assert b.saldo_acumulado is None and b.competencia is None
    passo = observar(lote, b, PredicadoValor(tipo='valor_original', operador='eq', valor='0.01'))
    assert passo.resultado == spec['predicado_centavo']
    assert passo.observados[0].valor == spec['esperado_original']
    assert set(passo.origens) == set(b.origens)


def test_componente_centavo_nao_e_valor_integral_da_cota(lote):
    b = lote.boletos[0]
    assert b.composicao.itens[0].valor == Decimal('0.01')
    assert b.composicao.total_original == Decimal('150.00')
    assert observar(lote, b, PredicadoValor(tipo='valor_original', operador='eq', valor='0.01')).resultado == 'falso'


def test_centavo_integral_independe_do_total_com_encargos(lote):
    b = lote.boletos[1]
    assert b.composicao.total_original == Decimal('0.01')
    assert b.multa + b.correcao + b.juros == Decimal('0.09')
    assert observar(lote, b, PredicadoValor(tipo='valor_original', operador='eq', valor='0.01')).resultado == 'verdadeiro'


def test_total_centavo_com_varios_componentes_sem_componente_positivo_centavo(lote):
    b = lote.boletos[5]
    assert all(i.valor != Decimal('0.01') for i in b.composicao.itens)
    assert observar(lote, b, PredicadoValor(tipo='valor_original', operador='eq', valor='0.01')).resultado == 'verdadeiro'


@pytest.mark.parametrize('indice,codigo', [(2, 'A'), (3, 'AJ'), (4, 'J')])
def test_apontamento_associado_somente_ao_boleto_correto(lote, indice, codigo):
    b = lote.boletos[indice]
    assert len(lote.unidades) == 1 and len(lote.boletos) == 6
    assert len(b.apontamentos) == 1
    ap = b.apontamentos[0]
    assert ap.codigo_original == codigo and ap.namespace_formato == FORMATO
    assert ap.origem == b.composicao.itens[0].origem
    condicao = PredicadoApontamento(tipo='apontamento', codigo=codigo, namespace=FORMATO)
    assert observar(lote, b, condicao).resultado == 'verdadeiro'
    assert observar(lote, lote.boletos[0], condicao, cobertura=True).resultado == 'falso'
    assert lote.boletos[0].apontamentos == ()


@pytest.mark.parametrize('codigo', ['A', 'AJ', 'J'])
def test_codigo_em_legenda_observacao_descricao_nao_cria_apontamento(codigo):
    cotas = deepcopy(FIXTURE['cotas'][:1])
    paginas = paginas_mapeamento(cotas)
    paginas[0] = [(x, y, text.replace('COMPONENTE SINTETICO', f'DESCRICAO {codigo} SINTETICA'))
                  for x, y, text in paginas[0]]
    paginas[0].append((31, 50, f'Observacao: {codigo} em texto livre, sem apontamento'))
    l = ler(pdf_posicionado(paginas))
    assert l.boletos[0].apontamentos == ()
    assert any(codigo in item.descricao_original for item in l.boletos[0].composicao.itens)
    p = PredicadoApontamento(tipo='apontamento', codigo=codigo, namespace=FORMATO)
    assert observar(l, l.boletos[0], p, cobertura=True).resultado == 'falso'
    assert observar(l, l.boletos[0], p).resultado == 'indeterminado'


@pytest.mark.parametrize('indice,codigo', [(2, 'A'), (3, 'AJ'), (4, 'J')])
@pytest.mark.parametrize('dias', [-5, 0, 30, 31])
def test_fato_apontamento_nao_depende_de_vencimento(indice, codigo, dias):
    l = ler(pdf_mapeamento(FIXTURE['cotas']))
    b = l.boletos[indice]
    data_ref = b.vencimento + timedelta(days=dias)
    p = PredicadoApontamento(tipo='apontamento', codigo=codigo, namespace=FORMATO)
    assert observar(l, b, p, data_ref=data_ref).resultado == 'verdadeiro'


@pytest.mark.parametrize('dias,esperado', [(-1, 'falso'), (0, 'falso'), (29, 'falso'), (30, 'falso'), (31, 'verdadeiro')])
def test_prazo_estrito_corridos_com_data_explicita(lote, dias, esperado):
    b = lote.boletos[0]
    passo = observar(lote, b, PredicadoDias(tipo='dias_atraso', operador='gt', valor=30),
                     data_ref=b.vencimento + timedelta(days=dias))
    assert passo.resultado == esperado and passo.observados[0].valor == dias


def test_continuidade_realista_preserva_total_codigo_e_hash():
    blob = pdf_mapeamento(FIXTURE['cotas'], quebrar=(3, 1))
    l = ler(blob)
    b = l.boletos[3]
    assert len(l.boletos) == 6 and len(b.composicao.itens) == 2
    assert b.composicao.total_original == Decimal('50.00')
    assert {o.pagina for o in b.origens} == {1, 2}
    assert b.composicao.itens[1].origem.continuacao_de == b.composicao.itens[0].origem.identificador
    assert len(b.apontamentos) == 1 and b.apontamentos[0].codigo_original == 'AJ'
    assert b.apontamentos[0].origem.pagina == 1
    assert all(o.sha256 == sha256(blob).hexdigest() and o.leitor_versao == VERSAO for o in b.origens)
    assert ler(blob) == l


def test_sem_ponto_nao_e_cobertura_negativa_presumida_e_namespace_nao_e_equivalente(lote):
    b = lote.boletos[4]
    p = PredicadoApontamento(tipo='apontamento', codigo='J', namespace='outro_formato')
    assert observar(lote, b, p).resultado == 'indeterminado'
    assert observar(lote, b, p, cobertura=True).resultado == 'indeterminado'
    assert b.apontamentos[0].namespace_formato == FORMATO


def test_soma_de_fechamento_divergente_nao_vira_centavo():
    paginas = paginas_mapeamento(FIXTURE['cotas'][:1])
    paginas[0] = [(x, y, 'Total do boleto: 0,01 0,00 0,00 0,00 0,01'
                  if text.startswith('Total do boleto:') else text)
                  for x, y, text in paginas[0]]
    with pytest.raises(ErroLeitura, match='SOMA_BOLETO_INCONSISTENTE'):
        ler(pdf_posicionado(paginas))


def test_subtotal_critico_preservado_com_todos_boletos_evidencias():
    l = ler(pdf_mapeamento(FIXTURE['cotas'], subtotal_divergente=True))
    r = resultado_leitura(l, processamento_id='verificacao_sintetica_mapeamento')
    assert len(l.boletos) == 6
    assert r.bloqueante and any(o.codigo == 'SUBTOTAL_BLOCO_DIVERGENTE' and o.bloqueante
                               and o.escopo == 'arquivo' for o in r.ocorrencias)
    assert [b.apontamentos[0].codigo_original for b in l.boletos if b.apontamentos] == ['A', 'AJ', 'J']


def test_apontamento_aj_nao_casa_com_codigo_a_parcial(lote):
    p = PredicadoApontamento(tipo='apontamento', codigo='A', namespace=FORMATO)
    assert observar(lote, lote.boletos[3], p, cobertura=True).resultado == 'falso'


def test_codigo_na_posicao_apontamento_desconhecido_bloqueia():
    cotas = deepcopy(FIXTURE['cotas'][2:3])
    cotas[0]['apontamento'] = 'X'
    with pytest.raises(ErroLeitura, match='CABECALHO_BOLETO_INVALIDO'):
        ler(pdf_mapeamento(cotas))


def test_apontamento_divergente_em_continuacao_nao_e_escolhido():
    paginas = paginas_mapeamento(FIXTURE['cotas'], quebrar=(3, 1))
    paginas[1] = [(x, y, text.replace('91000004 AJ ', '91000004 J ')) for x, y, text in paginas[1]]
    with pytest.raises(ErroLeitura, match='DUPLICIDADE_NAO_RECONCILIADA'):
        ler(pdf_posicionado(paginas))


@pytest.mark.parametrize('dias', [-5, 0, 30, 31])
def test_fato_centavo_integral_independe_do_vencimento(lote, dias):
    b = lote.boletos[1]
    condicao = PredicadoValor(tipo='valor_original', operador='eq', valor='0.01')
    assert observar(lote, b, condicao, data_ref=b.vencimento + timedelta(days=dias)).resultado == 'verdadeiro'
