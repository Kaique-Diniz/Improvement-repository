import json
from pathlib import Path

import pytest

from conversor.domain.catalog import Catalogo
from conversor.domain.canonical import Origem, Pessoa, Unidade, Boleto

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def dados_catalogo():
    return json.loads((RAIZ / "examples/fase1/catalogo.sintetico.json").read_text())


@pytest.fixture
def catalogo(dados_catalogo):
    return Catalogo.model_validate(dados_catalogo)


@pytest.fixture
def origem():
    return Origem(arquivo_id="fonte_sintetica", sha256="0" * 64,
                  leitor_versao="sintetico-1", pagina=1, linha=3, identificador="linha_3")


@pytest.fixture
def unidade(origem):
    return Unidade(id="unidade_a", condominio_id="cond_sintetico", administradora_id="adm_sintetica_a",
                   bloco_original="TORRE SINTÉTICA", unidade_original="0001-X",
                   chave_normalizada="sintetica:0001-X", normalizador_versao="sintetico-1", origem=origem)


@pytest.fixture
def pessoa(origem, unidade):
    return Pessoa(id="pessoa_sintetica", unidade_id=unidade.id, nome="Pessoa Sintética",
                  relacao_unidade="titular_sintetico", origem=origem)


@pytest.fixture
def boleto(origem, unidade):
    return Boleto(id="boleto_a", condominio_id=unidade.condominio_id, unidade_id=unidade.id,
                  identificador="boleto_sintetico_001", vencimento="2026-09-17", competencia="2026-09",
                  composicao={"itens": [{"codigo": "cota", "valor": "100.10", "origem": origem},
                                        {"codigo": "credito", "valor": "-0.10", "origem": origem}],
                              "total_original": "100.00"}, multa="2.00", juros="1.00",
                  saldo_acumulado="300.00", origens=(origem,))


@pytest.fixture
def tmp_path(tmp_path):
    # Diretório novo de fixture: DACL restrita antes de criar qualquer segredo sintético.
    from conversor.adapters.private_permissions import proteger_novo_windows
    proteger_novo_windows(tmp_path,diretorio=True)
    return tmp_path
