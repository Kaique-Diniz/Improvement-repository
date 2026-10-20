from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from conversor.domain.catalog import Catalogo
from conversor.readers.contracts import ClassificacaoFormato

APROVACAO = {"responsavel_id": "homologador_sintetico", "evidencia_id": "teste_sintetico", "em": "2026-01-01T00:00:00Z"}


def aprovar(dados, origem):
    dados = deepcopy(dados)
    dados["formatos"][0].update(status="validado", aprovacao=deepcopy(APROVACAO))
    dados["perfis_condominio"][0].update(status="aprovado", aprovacao=deepcopy(APROVACAO))
    dados["regras_cobranca"][0].update(status="aprovada", aprovacao=deepcopy(APROVACAO), fonte=origem.model_dump(mode="json"),
        condicoes=[{"campo": "campo_sintetico", "operador": "igual", "valor": "apenas_teste",
                    "alcance": "boleto", "acao": "alertar", "prioridade": 0}])
    return dados


def processamento(status="pendente"):
    return {"id": "exec_1", "condominio_id": "cond_sintetico", "status": status,
            "data_ref": "2026-10-20", "iniciado_em": "2026-10-20T12:00:00-03:00",
            "versoes": {"administradora_id": "adm_sintetica_a", "formato_id": "formato_sintetico_v1",
                        "perfil_id": "perfil_sintetico_v1", "regra_id": "regra_sintetica_v1", "template_id": "template_universal_v1"},
            "arquivo_hashes": ["0" * 64]}


def test_exemplo_somente_rascunhos_e_formato_compartilhado(catalogo):
    assert catalogo.regras_cobranca[0].status == "rascunho"
    assert not catalogo.regras_cobranca[0].condicoes
    assert len(catalogo.formatos[0].administradora_ids) == 2
    assert Catalogo.model_validate_json(catalogo.model_dump_json()) == catalogo


@pytest.mark.parametrize("colecao,campo,valor", [
    ("condominios", "administradora_id", "inexistente"),
    ("condominios", "perfil_version_id", "inexistente"),
    ("condominios", "formato_ids", ["inexistente"]),
    ("perfis_condominio", "template_id", "inexistente"),
    ("perfis_condominio", "regra_id", "inexistente"),
    ("regras_cobranca", "condominio_id", "inexistente"),
    ("formatos", "administradora_ids", ["inexistente"]),
])
def test_integridade_referencial(dados_catalogo, colecao, campo, valor):
    dados_catalogo[colecao][0][campo] = valor
    with pytest.raises(ValidationError):
        Catalogo.model_validate(dados_catalogo)


def test_ids_e_codigos_unicos(dados_catalogo):
    dados_catalogo["administradoras"].append(dados_catalogo["administradoras"][0])
    with pytest.raises(ValidationError, match="ID_DUPLICADO"):
        Catalogo.model_validate(dados_catalogo)


@pytest.mark.parametrize("vinculos", [[],
    [{"administradora_id": "adm_sintetica_a", "inicio": "2026-01-01", "fim": "2026-02-01"}],
    [{"administradora_id": "adm_sintetica_a", "inicio": "2026-01-01"},
     {"administradora_id": "adm_sintetica_b", "inicio": "2026-02-01"}],
    [{"administradora_id": "adm_sintetica_b", "inicio": "2026-01-01"}],
    [{"administradora_id": "adm_sintetica_b", "inicio": "2026-01-01", "fim": "2026-03-01"},
     {"administradora_id": "adm_sintetica_a", "inicio": "2026-02-01"}],
])
def test_exatamente_uma_administradora_atual_sem_sobreposicao(dados_catalogo, vinculos):
    dados_catalogo["condominios"][0]["vinculos"] = vinculos
    with pytest.raises(ValidationError):
        Catalogo.model_validate(dados_catalogo)


def test_mudanca_administradora_preserva_execucao_historica(dados_catalogo):
    dados_catalogo["condominios"][0].update(administradora_id="adm_sintetica_b", vinculos=[
        {"administradora_id": "adm_sintetica_a", "inicio": "2026-01-01", "fim": "2026-11-01"},
        {"administradora_id": "adm_sintetica_b", "inicio": "2026-11-01"}])
    dados_catalogo["processamentos"] = [processamento()]
    assert Catalogo.model_validate(dados_catalogo).processamentos[0].versoes.administradora_id == "adm_sintetica_a"
    dados_catalogo["processamentos"][0]["data_ref"] = "2026-11-01"
    with pytest.raises(ValidationError, match="VINCULO_HISTORICO_INCOMPATIVEL"):
        Catalogo.model_validate(dados_catalogo)


def test_aprovacao_requer_evidencia_e_fuso(dados_catalogo, origem):
    dados = aprovar(dados_catalogo, origem)
    dados["processamentos"] = [processamento("concluido")]
    assert Catalogo.model_validate(dados).processamentos[0].status == "concluido"
    dados["formatos"][0]["aprovacao"]["em"] = "2026-01-01T00:00:00"
    with pytest.raises(ValidationError, match="HORARIO_EXIGE_FUSO"):
        Catalogo.model_validate(dados)


def test_rascunho_nao_pode_ser_usado_como_aprovado(dados_catalogo):
    dados_catalogo["processamentos"] = [processamento("concluido")]
    with pytest.raises(ValidationError, match="PROCESSAMENTO_EXIGE_CONFIGURACAO_APROVADA"):
        Catalogo.model_validate(dados_catalogo)


def test_regras_aprovadas_sobrepostas_sao_bloqueadas(dados_catalogo, origem):
    dados = aprovar(dados_catalogo, origem)
    regra = deepcopy(dados["regras_cobranca"][0])
    regra.update(id="regra_sintetica_v2", versao="2")
    dados["regras_cobranca"].append(regra)
    with pytest.raises(ValidationError, match="REGRAS_APROVADAS_SOBREPOSTAS"):
        Catalogo.model_validate(dados)


@pytest.mark.parametrize("estado,candidatos,bloqueante", [
    ("desconhecido", (), True), ("ambiguo", ("formato_a", "formato_b"), True),
    ("conhecido_validado", ("formato_a",), False),
])
def test_estados_de_classificacao_sao_explicitos(estado, candidatos, bloqueante):
    contrato = ClassificacaoFormato(estado=estado, candidatos=candidatos, evidencia_hashes=("0" * 64,))
    assert contrato.bloqueante is bloqueante


@pytest.mark.parametrize("estado,candidatos", [("conhecido_validado", ()), ("ambiguo", ("formato_a",)),
    ("desconhecido", ("formato_a",)), ("conhecido_validado", ("formato_a", "formato_b"))])
def test_classificacao_nao_pode_presumir_selecao(estado, candidatos):
    with pytest.raises(ValidationError):
        ClassificacaoFormato(estado=estado, candidatos=candidatos, evidencia_hashes=("0" * 64,))
