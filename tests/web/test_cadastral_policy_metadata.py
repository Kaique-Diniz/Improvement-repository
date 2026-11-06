"""Rastreabilidade cadastral com fontes integralmente sintéticas."""
import json

import pytest

from conversor.web.service import PedidoDiagnostico, analisar
from tests.oma import fixtures as oma
from tests.passaredo import fixtures as auto_gestao


@pytest.mark.parametrize('perfil,politica', [
    ('passaredo', 'passaredo_nome_e_unidade_por_lancamento@1.1'),
    ('forest_hill', 'passaredo_nome_e_unidade_por_lancamento@1.1'),
    ('parque_santa_monica', 'oma_identidade_nominal_documento_valido_A1@1'),
])
@pytest.mark.parametrize('com_cadastro', [False, True])
@pytest.mark.parametrize('modo', ['A', 'B'])
def test_politica_consistente_no_resultado_manifesto_e_auditoria(
        tmp_path, perfil, politica, com_cadastro, modo):
    if perfil == 'parque_santa_monica':
        financeiro = oma.financeiro()
        cadastro = oma.cadastro() if com_cadastro else None
        data_ref = oma.REF
    else:
        unidade = 'AV.P02 231' if perfil == 'forest_hill' else '007'
        financeiro = auto_gestao.financeiro([auto_gestao.debito(unidade=unidade)])
        cadastro = auto_gestao.cadastro([auto_gestao.ficha(unidade=unidade)]) if com_cadastro else None
        data_ref = auto_gestao.REF

    resultado = analisar(financeiro, PedidoDiagnostico(
        data_ref=data_ref, modo=modo, condominio=perfil),
        processamento_id='politica_sintetica', destino=tmp_path, cadastro=cadastro,
        historico=(), estado_historico='nao_disponivel')

    manifesto = json.loads((tmp_path / 'manifesto_diagnostico.json').read_text(encoding='utf-8'))
    auditoria = json.loads((tmp_path / 'auditoria.json').read_text(encoding='utf-8'))
    chave_cadastro = 'cadastro_' + perfil
    chave_revisao = 'revisao_cadastral_' + perfil

    assert resultado['politica_cadastral'] == politica
    assert resultado[chave_cadastro]['politica'] == politica
    assert manifesto[chave_cadastro] == resultado[chave_cadastro]
    assert resultado['manifesto_diagnostico'] == manifesto
    assert auditoria['politica_cadastral'] == politica
    assert auditoria[chave_cadastro] == resultado[chave_cadastro]
    assert auditoria['manifesto_diagnostico'] == manifesto
    assert auditoria[chave_revisao] == resultado[chave_revisao]
