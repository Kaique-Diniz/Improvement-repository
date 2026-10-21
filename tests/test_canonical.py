from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from conversor.domain.base import Modelo, Dinheiro
from conversor.domain.canonical import (
    Apontamento, Boleto, Composicao, Contato, Documento, LoteCanonico,
    Ocorrencia, Origem, Pessoa, ResultadoCobranca, cpf_validado,
)


class Valor(Modelo):
    valor: Dinheiro


@pytest.mark.parametrize("valor", [0.1, True, "0.001", "NaN", "Infinity", "1e100", [], {}])
def test_dinheiro_rejeita_float_arredondamento_e_nao_finito(valor):
    with pytest.raises(ValidationError):
        Valor(valor=valor)


def test_decimal_exato_com_credito_e_saldos_separados(boleto):
    assert boleto.composicao.total_original == Decimal("100.00")
    assert boleto.composicao.itens[1].valor == Decimal("-0.10")
    assert boleto.saldo_acumulado == Decimal("300.00")
    assert Boleto.model_validate_json(boleto.model_dump_json()) == boleto
    assert '"100.00"' in boleto.model_dump_json()
    assert isinstance(boleto.vencimento, date)


def test_soma_inconsistente_bloqueia(boleto):
    dados = boleto.composicao.model_dump()
    dados["total_original"] = "99.00"
    with pytest.raises(ValidationError, match="SOMA_COMPOSICAO_INCONSISTENTE"):
        Composicao.model_validate(dados)


def test_item_duplicado_bloqueia(boleto):
    dados = boleto.composicao.model_dump()
    dados["itens"] = [dados["itens"][0], dados["itens"][0]]
    dados["total_original"] = "200.20"
    with pytest.raises(ValidationError, match="ITEM_COMPOSICAO_DUPLICADO"):
        Composicao.model_validate(dados)


@pytest.mark.parametrize("campo,valor", [("origens", []), ("vencimento", "17/09/2026"),
    ("vencimento", 0), ("vencimento", "0"), ("competencia", "2026-13")])
def test_boleto_incompleto_ou_datas_invalidas(boleto, campo, valor):
    with pytest.raises(ValidationError):
        Boleto.model_validate(boleto.model_dump() | {campo: valor})


def test_origem_localizacao_e_hash_invalidos(origem):
    for alteracao in ({"pagina": 0}, {"linha": -1}, {"sha256": "incorreto"}):
        with pytest.raises(ValidationError):
            Origem.model_validate(origem.model_dump() | alteracao)


def test_lote_rejeita_duplicacao_de_continuacao(unidade, boleto, origem):
    continuacao = Origem.model_validate(origem.model_dump() | {"pagina": 2, "continuacao_de": origem.identificador})
    repetido = Boleto.model_validate(boleto.model_dump() | {"id": "boleto_outro", "origens": [continuacao]})
    assert repetido.chave_idempotencia == boleto.chave_idempotencia
    with pytest.raises(ValidationError, match="DUPLICIDADE_NAO_RECONCILIADA"):
        LoteCanonico(unidades=(unidade,), boletos=(boleto, repetido))
    unico = Boleto.model_validate(boleto.model_dump() | {"origens": [origem, continuacao]})
    assert len(LoteCanonico(unidades=(unidade,), boletos=(unico,)).boletos) == 1


def test_relacoes_canonicas(unidade, boleto, pessoa):
    lote = LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,))
    assert LoteCanonico.model_validate_json(lote.model_dump_json()) == lote
    with pytest.raises(ValidationError, match="PESSOA_SEM_UNIDADE"):
        LoteCanonico(unidades=(), boletos=(), pessoas=(pessoa,))
    with pytest.raises(ValidationError, match="BOLETO_SEM_UNIDADE_COMPATIVEL"):
        LoteCanonico(unidades=(), boletos=(boleto,))


def test_pessoa_e_contato_nao_expoem_dados_no_repr(pessoa):
    assert pessoa.nome not in repr(pessoa)
    assert "SENTINELA_PRIVADA" not in repr(Documento(tipo="outro", valor="SENTINELA_PRIVADA"))
    with pytest.raises(ValidationError):
        Contato(emails=tuple(f"sintetico{i}@example.invalid" for i in range(4)))


@pytest.mark.parametrize("documento", [None, Documento(tipo="cnpj", valor="00000000000000"),
    Documento(tipo="cpf", valor="00000000000"), Documento(tipo="cpf", valor="123"),
    Documento(tipo="cpf", valor="12345678901234")])
def test_validador_especifico_cpf_nao_retipa_outros_documentos(documento):
    assert cpf_validado(documento) == ""


def test_cpf_sintetico_algoritmico_com_zero_inicial():
    # Gerado por algoritmo; não veio de cadastro de pessoa. Não comprova identidade real.
    base = "000000001"
    for tamanho in (9, 10):
        soma = sum(int(base[i]) * (tamanho + 1 - i) for i in range(tamanho))
        base += str((soma * 10 % 11) % 10)
    assert cpf_validado(Documento(tipo="cpf", valor=base)) == base
    assert base.startswith("0")


def test_apontamentos_sao_por_namespace_sem_equivalencia_inferida(origem):
    a = Apontamento(codigo_original="J", namespace_formato="formato_a", origem=origem)
    b = Apontamento(codigo_original="Jurídico", namespace_formato="formato_b", origem=origem)
    assert a != b


def test_resultado_nao_inclui_ocorrencia_critica(origem):
    dados = dict(processamento_id="exec_1", unidade_id="unidade_a", regra_id="regra_1", regra_versao="1",
                 motivo_codigo="motivo_sintetico", origens=(origem,))
    ocorrencia = Ocorrencia(id="oc_1", processamento_id="exec_1", codigo="SOMA_INCONSISTENTE",
                           gravidade="critico", escopo="registro", registro_id="boleto_a", origem=origem)
    with pytest.raises(ValidationError, match="RESULTADO_COM_BLOQUEIO"):
        ResultadoCobranca(**dados, acao="incluir", ocorrencias=(ocorrencia,))
    assert ResultadoCobranca(**dados, acao="bloquear", ocorrencias=(ocorrencia,)).acao == "bloquear"
    alerta = Ocorrencia.model_validate(ocorrencia.model_dump() | {"gravidade": "alerta", "codigo": "CPF_AUSENTE"})
    assert ResultadoCobranca(**dados, acao="incluir", ocorrencias=(alerta,)).acao == "incluir"
