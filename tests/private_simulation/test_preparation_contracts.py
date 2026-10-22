import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from conversor.domain.billing_rules import PlanoCobranca
from conversor.domain.private_simulation import AtestoCompletude, CandidatoPacote, ExecucaoPrivada, PacotePrivado, ReproducaoHistorica
from conversor.domain.rule_preparation import MatrizPreliminar, pendencias_da_matriz
from conversor.domain.simulation_comparison import MapeamentoReferencia
from conversor.private_simulation_schemas import documentos, main


def matriz():
    return MatrizPreliminar.model_validate_json(Path('examples/fase4/matriz_preliminar_4_3A.json').read_text())


def test_matriz_cobre_apenas_levantamento_humano():
    m = matriz()
    assert len(m.regras) == 8
    assert {r.condominio_referencia for r in m.regras} == {'TREE_MORUMBI', 'PLAZA_MAYOR_IPIRANGA'}
    assert not m.autoriza_ativacao
    assert all(r.situacao_aprovacao == 'pendente_aprovacao_humana' for r in m.regras)
    assert all(r.prioridade is None and r.vigente_de is None for r in m.regras)
    assert all(r.evidencia == 'SOLICITACAO_4_3A' for r in m.regras)
    assert {id_ for id_, _ in pendencias_da_matriz(m)} == {r.id for r in m.regras}
    with pytest.raises(ValidationError):
        PlanoCobranca.model_validate(m.model_dump())


def test_matriz_identifica_contradicao_sem_executar_regra():
    m = matriz()
    base = m.regras[0]
    outra = base.model_copy(update={'id': 'tree_centavo_z', 'acao': 'incluir'})
    m = m.model_copy(update={'regras': (base, outra)})
    assert ('tree_centavo_z', 'ACOES_CONTRADITORIAS_EXIGEM_REVISAO') in pendencias_da_matriz(m)


def test_matriz_nao_acusa_conflito_em_vigencias_separadas():
    m = matriz()
    from datetime import date
    base = m.regras[0].model_copy(update={'vigente_de': date(2026, 1, 1), 'vigente_ate': date(2026, 2, 1)})
    outra = base.model_copy(update={'id': 'tree_centavo_z', 'acao': 'incluir', 'vigente_de': date(2026, 2, 1), 'vigente_ate': None})
    assert not any(c == 'ACOES_CONTRADITORIAS_EXIGEM_REVISAO' for _, c in pendencias_da_matriz(m.model_copy(update={'regras': (base, outra)})))


@pytest.mark.parametrize('campo', ['inventario_conferido', 'fontes_e_paginas_conferidas', 'catalogos_externos_completos', 'ausencias_conferidas'])
def test_atesto_nao_aceita_conferencia_parcial(laboratorio, campo):
    c = laboratorio()
    dados = c.pacote.atesto.model_dump(); dados[campo] = False
    with pytest.raises(ValidationError):
        AtestoCompletude.model_validate(dados)


def test_schemas_publicados_sincronizados_e_sem_objetos_abertos():
    assert main(['--check']) == 0
    for _, texto in documentos():
        schema = json.loads(texto)
        assert schema['additionalProperties'] is False
        assert schema['$schema'].endswith('2020-12/schema')


@pytest.mark.parametrize('flag', ['autoriza_cobranca', 'permite_exportacao_operacional'])
def test_nao_existe_upgrade_operacional_por_edicao_json(laboratorio, flag):
    c = laboratorio(); c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    execucao = c.executar()
    dados = execucao.model_dump(); dados[flag] = True
    with pytest.raises(ValidationError):
        ExecucaoPrivada.model_validate(dados)
    replay = c.servico.reproduzir(execucao.id)
    dados = replay.model_dump(); dados[flag] = True
    with pytest.raises(ValidationError):
        ReproducaoHistorica.model_validate(dados)


def test_mapeamento_nao_aceita_duplicar_saldo_por_boleto(laboratorio):
    c = laboratorio()
    dados = c.mapeamento.model_dump(mode='json')
    outra = dict(dados['vinculos'][0]); outra['linha'] = 3
    dados['vinculos'].append(outra)
    with pytest.raises(ValidationError):
        MapeamentoReferencia.model_validate(dados)


def test_candidato_sem_atesto_nao_pode_ser_registrado_ou_simulado(laboratorio):
    c = laboratorio()
    dados = c.pacote.model_dump(); del dados['atesto']
    candidato = CandidatoPacote.model_validate(dados)
    from conversor.application.ports import ErroAplicacao
    with pytest.raises(ErroAplicacao, match='CONTRATO_PRIVADO_INVALIDO'):
        c.armazenamento.gravar_pacote(candidato, credencial=c.gestor)
    with pytest.raises(ErroAplicacao):
        c.executar()
