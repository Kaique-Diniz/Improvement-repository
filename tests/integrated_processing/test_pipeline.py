from datetime import date

import pytest

from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import hash_modelo
from tests.synthetic_processing.test_tree_conditions import composicao


@pytest.mark.parametrize('modo', ['A', 'B'])
@pytest.mark.parametrize('dias,elegivel', [(31, True), (30, False)])
def test_processamento_completo_persistencia_e_reproducao(integrado, modo, dias, elegivel):
    c = integrado(specs=[{'dias': dias}], modo=modo)
    estado = c.repo.carregar()
    r = c.executar()
    assert bool(r.projecao.boletos_divida) == elegivel
    assert bool(r.projecao.candidatos_cadastrais) == (modo == 'B' and not elegivel)
    assert c.armazenamento.carregar_processamento(r.id) == r
    assert c.servico.reproduzir(r.id).projecao == r.projecao
    assert c.repo.carregar() == estado  # Nenhuma aprovação/ativação automática.
    assert not r.autoriza_cobranca and not r.permite_exportacao_operacional
    assert not r.atesto_humano_emitido
    assert r.ato.funcao == 'operador' and r.ato.responsavel_id == 'gestor'
    assert not hasattr(c.preparacao.candidato, 'atesto')


@pytest.mark.parametrize('codigo', ['A', 'AJ', 'J'])
def test_apontamentos_e_cotas_validas_na_mesma_unidade(integrado, codigo):
    c = integrado(specs=[{'ap': codigo}, {'dias': 31}], modo='B')
    r = c.executar()
    assert r.projecao.boletos_divida == ('boleto_1',)
    assert len(r.projecao.candidatos_cadastrais) == 1
    assert r.projecao.candidatos_cadastrais[0].divida is None
    assert r.projecao.candidatos_cadastrais[0].boletos_nao_elegiveis == ('boleto_0',)


@pytest.mark.parametrize('encargos', [False, True])
def test_centavo_original_integral_com_e_sem_encargos(integrado, origem, encargos):
    spec = {'composicao': composicao(origem, '0.01')}
    if encargos:spec |= {'multa': '2.00', 'juros': '3.00', 'correcao': '4.00'}
    c = integrado(specs=[spec, {'composicao': composicao(origem, '0.01', '99.99')}], modo='B')
    antes = hash_modelo(c.preparacao)
    r = c.executar()
    assert r.projecao.boletos_divida == ('boleto_1',)
    assert hash_modelo(c.armazenamento.carregar_preparacao_tecnica(c.preparacao.id)) == antes


def test_reprocessamento_idempotente_mesmo_recibo_e_sem_novos_eventos(integrado):
    c = integrado(modo='B')
    a = c.executar()
    path, recibo = c.armazenamento._paths('processamento_sintetico', a.id)
    antes = (path.read_bytes(), recibo.read_bytes(), path.stat().st_mtime_ns, recibo.stat().st_mtime_ns)
    assert c.executar() == a
    assert antes == (path.read_bytes(), recibo.read_bytes(), path.stat().st_mtime_ns, recibo.stat().st_mtime_ns)


def test_mesmo_id_com_modo_diferente_nao_sobrescreve_historico(integrado):
    c = integrado(specs=[{'dias': 31}, {'dias': 30}])
    original = c.executar()
    with pytest.raises(ErroAplicacao, match='PROCESSAMENTO_IMUTAVEL_COM_PEDIDO_DIVERGENTE'):
        c.servico.executar(c.pedido.model_copy(update={'modo_cadastro': 'B'}), credencial=c.gestor)
    assert c.armazenamento.carregar_processamento(original.id) == original


def test_modos_e_datas_distintos_em_historico_independente(integrado):
    c = integrado(specs=[{'dias': 30}])
    a = c.executar()
    b = c.servico.executar(c.pedido.model_copy(update={'processamento_id': 'ensaio_seguinte',
        'modo_cadastro': 'B', 'data_ref': date(2026, 10, 22)}), credencial=c.gestor)
    assert not a.projecao.boletos_divida and b.projecao.boletos_divida == ('boleto_0',)
    assert c.servico.reproduzir(a.id).projecao == a.projecao
    assert c.servico.reproduzir(b.id).projecao == b.projecao
    assert a.pedido.data_ref != a.estado_planos.acervo.registros[0].conteudo.vigente_de


def test_sem_regra_aplicavel_exige_revisao_sem_cadastro(integrado):
    def editar(p):
        p['regras'] = [p['regras'][0]]  # Só centavo, que é falso para esta cota.
    c = integrado(editar_plano=editar, modo='B')
    r = c.executar()
    assert not r.projecao.boletos_divida and not r.projecao.candidatos_cadastrais
    assert r.projecao.relatorio_motor.boletos[0].situacao == 'pendente_revisao'


@pytest.mark.parametrize('modo,quantidade_cadastro', [('A', 0), ('B', 1)])
def test_demonstracao_completa_seis_cotas_sinteticas(integrado, origem, modo, quantidade_cadastro):
    c = integrado(specs=[{'dias': 31}, {'dias': 30}, {'composicao': composicao(origem, '0.01')},
                        {'ap': 'A'}, {'ap': 'AJ'}, {'ap': 'J'}], modo=modo)
    original = c.executar()
    r = original.projecao
    assert r.boletos_divida == ('boleto_0',)
    assert sum(d.situacao == 'excluido' for d in r.relatorio_motor.boletos) == 5
    assert len(r.candidatos_cadastrais) == quantidade_cadastro
    assert not r.retencoes_cadastrais
    assert c.servico.reproduzir(original.id).projecao == r
    assert c.executar() == original
