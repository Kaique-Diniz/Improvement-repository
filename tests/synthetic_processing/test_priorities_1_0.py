"""Proposta 1/0 em memória: sem repositório, assinaturas, aprovações ou atestos.

Os diagnósticos sem guarda isolam a ordem numérica do motor. Eles não são uma
configuração TREE real nem substituem a guarda obrigatória da proposta.
"""
from datetime import timedelta
import json
from pathlib import Path

import pytest

from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.billing_rules import PlanoCobranca, hash_modelo
from conversor.domain.canonical import Apontamento, Boleto, LoteCanonico
from conversor.rules.engine import avaliar_regras, resolver_candidatos
from tests.synthetic_processing.conftest import DATA_REF, NAMESPACE
from tests.synthetic_processing.test_tree_conditions import composicao


@pytest.fixture
def diagnosticar(origem, unidade, boleto):
    def executar(*, specs, guarda=True, exclusao=1, prazo=0, inverter_ordem=False,
                 bloqueio_unidade=False):
        dados = json.loads(Path('examples/fase4/tree_43b1.sintetico.json').read_text())
        for r in dados['regras']:
            r['prioridade'] = exclusao if r['id'] in {
                'tree_centavo', 'tree_apontamento_a', 'tree_apontamento_aj', 'tree_apontamento_j'} else prazo
            if r['id'] == 'tree_prazo_30' and not guarda:
                r['quando'] = r['quando']['condicoes'][0]
        if bloqueio_unidade:
            dados['regras'].append({'id': 'bloqueio_diagnostico', 'prioridade': 0,
                'alvo': 'unidade', 'quando': {'tipo': 'existe_boleto', 'condicao': {
                    'tipo': 'dias_atraso', 'operador': 'gt', 'valor': 30}},
                'acao': 'bloquear', 'motivo_codigo': 'BLOQUEIO_SOMENTE_DIAGNOSTICO',
                'fonte_id': 'tree_prazo_30'})
        if inverter_ordem:dados['regras'].reverse()
        plano = PlanoCobranca.model_validate(dados)
        boletos, covers = [], []
        for n, spec in enumerate(specs):
            ap = (Apontamento(codigo_original=spec['ap'], namespace_formato=NAMESPACE,
                              origem=origem),) if spec.get('ap') else ()
            b = Boleto.model_validate(boleto.model_dump() | {
                'id': f'cota_diagnostica_{n}', 'identificador': f'inventado_{n}',
                'vencimento': DATA_REF - timedelta(days=spec.get('dias', 31)),
                'apontamentos': ap,
                'composicao': composicao(origem, spec.get('original', '100.00'))})
            boletos.append(b)
            if spec.get('cobertura', True):
                covers.append(CoberturaApontamentos(boleto_id=b.id, namespace=NAMESPACE, origens=b.origens))
        entrada = EntradaSimulacao(lote=LoteCanonico(unidades=(unidade,), boletos=tuple(boletos)),
            fatos=(), ocorrencias_anteriores=(), coberturas_apontamentos=tuple(covers))
        antes = hash_modelo(entrada)
        unidade_avals = avaliar_regras(plano, entrada, DATA_REF, unidade)
        resultados = []
        for b in boletos:
            avals = avaliar_regras(plano, entrada, DATA_REF, unidade, b)
            resultados.append((resolver_candidatos(unidade_avals, avals), avals))
        assert hash_modelo(entrada) == antes
        return plano, tuple(resultados)
    return executar


@pytest.mark.parametrize('guarda', [False, True])
@pytest.mark.parametrize('spec,id_exclusao', [({'original': '0.01'}, 'tree_centavo'),
    ({'ap': 'A'}, 'tree_apontamento_a'), ({'ap': 'AJ'}, 'tree_apontamento_aj'),
    ({'ap': 'J'}, 'tree_apontamento_j')])
def test_prioridade_um_exclui_e_preserva_prazo_avaliado(diagnosticar, guarda, spec, id_exclusao):
    plano, ((decisao, avals),) = diagnosticar(specs=[spec], guarda=guarda)
    assert decisao.situacao == 'excluido' and decisao.regras == (id_exclusao,)
    assert len(avals) == len(plano.regras) == 6
    ex = next(a for a in avals if a.regra_id == id_exclusao)
    inc = next(a for a in avals if a.regra_id == 'tree_prazo_30')
    assert ex.prioridade == 1 and inc.prioridade == 0
    assert ex.passo.resultado == 'verdadeiro' and ex.passo.origens
    assert inc.passo.resultado == ('falso' if guarda else 'verdadeiro')
    assert inc.passo.origens  # A inclusão de menor nível continua na auditoria.


@pytest.mark.parametrize('codigo', ['A', 'AJ', 'J'])
@pytest.mark.parametrize('guarda', [False, True])
def test_duas_exclusoes_mesma_cota_conservam_ambos_motivos(diagnosticar, codigo, guarda):
    _, ((d, avals),) = diagnosticar(specs=[{'original': '0.01', 'ap': codigo}], guarda=guarda)
    assert d.situacao == 'excluido'
    assert set(d.regras) == {'tree_centavo', 'tree_apontamento_' + codigo.lower()}
    assert len([a for a in avals if a.prioridade == 1 and a.passo.resultado == 'verdadeiro']) == 2


@pytest.mark.parametrize('exclusao,prazo,esperado', [(1, 0, 'excluido'),
    (0, 1, 'elegivel_na_simulacao'), (0, 0, 'pendente_revisao')])
def test_contraprova_generica_da_ordem_numerica_sem_guarda(diagnosticar, exclusao, prazo, esperado):
    # Função diagnóstica pura; os dois últimos casos NÃO são propostas TREE.
    _, ((d, avals),) = diagnosticar(specs=[{'original': '0.01'}], guarda=False,
                                   exclusao=exclusao, prazo=prazo)
    assert d.situacao == esperado
    assert {a.acao for a in avals if a.passo.resultado == 'verdadeiro'} == {'incluir', 'excluir'}


@pytest.mark.parametrize('centavo', [False, True])
def test_indeterminado_nao_e_silenciado_por_prioridade_ou_exclusao(diagnosticar, centavo):
    spec = {'cobertura': False, 'original': '0.01' if centavo else '100.00'}
    _, ((d, avals),) = diagnosticar(specs=[spec])
    assert d.situacao == 'pendente_revisao' and d.revisao_humana
    assert any(a.passo.resultado == 'indeterminado' for a in avals)
    if centavo:
        assert next(a for a in avals if a.regra_id == 'tree_centavo').passo.resultado == 'verdadeiro'


def test_duas_cotas_mesma_unidade_resultados_distintos_e_ordem_deterministica(diagnosticar):
    specs = [{'ap': 'AJ'}, {'dias': 31}]
    a = diagnosticar(specs=specs)
    b = diagnosticar(specs=specs, inverter_ordem=True)
    assert a[1] == b[1]
    assert [d.situacao for d, _ in a[1]] == ['excluido', 'elegivel_na_simulacao']
    assert all(av.unidade_id == a[1][0][1][0].unidade_id for _, avals in a[1] for av in avals)


def test_bloqueio_unidade_nao_e_disputado_por_prioridades_de_boleto(diagnosticar):
    _, rs = diagnosticar(specs=[{'original': '0.01'}, {'dias': 31}], bloqueio_unidade=True)
    assert [d.situacao for d, _ in rs] == ['bloqueado', 'bloqueado']
    assert all('bloqueio_diagnostico' in d.regras for d, _ in rs)
