from datetime import date
from decimal import Decimal
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from conversor.domain.canonical import Documento, Ocorrencia, Pessoa
from conversor.export.contract import COLUNAS, DividaExportacao, LinhaExportacao, Template, materializar


def linha(pessoa, **campos):
    return LinhaExportacao(processamento_id="exec_1", registro_id="registro_1", tipo="cadastral",
                           nm_cedente_cedente="Credor Sintético", cedente="0001-X", pessoa=pessoa, **campos)


def test_30_colunas_conferidas_contra_documento_normativo():
    texto = (Path(__file__).resolve().parents[1] / "04_DICIONARIO_TEMPLATE.md").read_text()
    documentadas = re.findall(r"^\|\s*\d+\s*\|\s*`([^`]+)`", texto, re.MULTILINE)
    assert tuple(documentadas) == COLUNAS
    assert len(COLUNAS) == 30
    template = Template(id="template_1", nome="Universal", versao="1")
    assert template.nome_aba == "Dados"
    assert template.cabecalhos_fisicos[26] == "NM_DIVIDA_CEDENTE "
    assert template.colunas_logicas[26] == "NM_DIVIDA_CEDENTE"
    sem_espaco = Template.model_validate(template.model_dump() | {"espaco_final_coluna_27": False})
    assert sem_espaco.cabecalhos_fisicos == COLUNAS


@pytest.mark.parametrize("colunas", [COLUNAS[:-1], tuple(reversed(COLUNAS)), COLUNAS + ("EXTRA",)])
def test_template_incompativel_rejeitado(colunas):
    with pytest.raises(ValidationError):
        Template(id="template_1", nome="Universal", versao="1", colunas_logicas=colunas)


@pytest.mark.parametrize("documento", [None, {"tipo": "cnpj", "valor": "00000000000000"},
                                      {"tipo": "cpf", "valor": "invalido"}])
def test_cadastral_30_valores_cpf_vazio_alerta_e_seis_vazios(pessoa, documento):
    pessoa = Pessoa.model_validate(pessoa.model_dump() | {"documento": documento})
    resultado = materializar(linha(pessoa))
    assert len(resultado.valores) == 30
    assert resultado.valores[2] == ""
    assert resultado.valores[24:] == ("",) * 6
    assert len(resultado.ocorrencias) == 1
    assert not resultado.ocorrencias[0].bloqueante
    assert resultado == materializar(linha(pessoa))


def test_divida_tem_seis_campos_tipados_e_valor_exato(pessoa):
    divida = DividaExportacao(contrato="contrato_sintetico", produto="produto_sintetico", nome_divida="2026-09",
                            parcela=1, vencimento="2026-09-17", valor="100.10")
    dados = linha(pessoa).model_dump() | {"tipo": "divida", "divida": divida}
    resultado = materializar(LinhaExportacao.model_validate(dados))
    assert resultado.valores[24:] == ("contrato_sintetico", "produto_sintetico", "2026-09", 1, date(2026, 9, 17), Decimal("100.10"))
    assert isinstance(resultado.valores[-1], Decimal)
    assert isinstance(resultado.valores[-2], date)


def test_zeros_telefones_emails_e_complemento_independentes(pessoa):
    pessoa = Pessoa.model_validate(pessoa.model_dump() | {"contato": {
        "endereco": {"cep": "00000001", "numero": "01A", "complemento": "TORRE SINTÉTICA"},
        "telefones": [{"ddd": "01", "numero": "000000001"}], "emails": ["sintetico@example.invalid"]}})
    valores = materializar(linha(pessoa)).valores
    assert valores[1] == "0001-X"
    assert valores[5:8] == ("01A", "TORRE SINTÉTICA", "00000001")
    assert valores[11:15] == ("01", "000000001", "", "")
    assert valores[21:24] == ("sintetico@example.invalid", "", "")


def test_cpf_algoritmico_permanece_texto_com_zero_na_saida(pessoa):
    base = "000000001"
    for tamanho in (9, 10):
        soma = sum(int(base[i]) * (tamanho + 1 - i) for i in range(tamanho))
        base += str((soma * 10 % 11) % 10)
    pessoa = Pessoa.model_validate(pessoa.model_dump() | {"documento": {"tipo": "cpf", "valor": base}})
    resultado = materializar(linha(pessoa))
    assert resultado.valores[2] == base
    assert isinstance(resultado.valores[2], str)
    assert resultado.ocorrencias == ()


def test_linha_de_divida_incompleta_e_bloqueios_rejeitados(pessoa):
    with pytest.raises(ValidationError):
        LinhaExportacao.model_validate(linha(pessoa).model_dump() | {"tipo": "divida"})
    critico = Ocorrencia(id="oc_1", processamento_id="exec_1", codigo="UNIDADE_AMBIGUA",
                        gravidade="critico", escopo="registro")
    with pytest.raises(ValidationError, match="LINHA_COM_BLOQUEIO"):
        linha(pessoa, ocorrencias=(critico,))
    with pytest.raises(ValidationError, match="LINHA_COM_BLOQUEIO"):
        materializar(linha(pessoa).model_copy(update={"ocorrencias": (critico,)}))


def test_alerta_cpf_tem_id_estavel_e_distinto_entre_execucoes(pessoa):
    primeira = linha(pessoa)
    segunda = LinhaExportacao.model_validate(primeira.model_dump() | {"processamento_id": "exec_2"})
    assert materializar(primeira).ocorrencias[0].id != materializar(segunda).ocorrencias[0].id
    assert materializar(primeira) == materializar(primeira)


@pytest.mark.parametrize("valor", [0, "-1.00", "0.001", 0.1])
def test_valor_de_divida_invalido(valor):
    with pytest.raises(ValidationError):
        DividaExportacao(contrato="c", produto="p", nome_divida="d", parcela=1, vencimento="2026-01-01", valor=valor)
