"""Testes sintéticos da Central de Validação, sem documentos privados."""
from datetime import date, datetime
from decimal import Decimal

from openpyxl import Workbook, load_workbook

from conversor.application.conversion_validation import validar_conversao
from conversor.domain.template import COLUNAS


def _cenario(tmp_path, *, retida=False):
    arq = tmp_path / "saida.xlsx"
    valores = (["Credor", "BLE-UNIA00223-788", "", "Titular fictício"] +
               [""] * 20 + ["Contrato", "Produto", "COTA", 1,
                              date(2026, 7, 5), Decimal("897.88")])
    assert len(valores) == 30
    w = Workbook()
    sh = w.active
    sh.title = "Dados"
    sh.append(COLUNAS)
    sh.append(valores)
    sh["AC2"].number_format = "dd/mm/yyyy"
    w.save(arq)
    w.close()
    infos = [{"tipo": "divida", "boleto_id": "b1", "unidade_id": "u1"}]
    decisoes = [{"id": "b1", "situacao": "elegivel"}]
    return arq, [valores], infos, decisoes


def _validar(arq, registros, infos, decisoes, **extra):
    return validar_conversao(arq, registros=registros, linhas_info=infos,
                            decisoes=decisoes, **extra)


def test_xlsx_correto_apresenta_indicadores(tmp_path):
    r = _validar(*_cenario(tmp_path))
    assert r["estado"] == "conforme"
    assert r["indicadores"]["linhas_divida"] == 1
    assert r["indicadores"]["valor_financeiro_xlsx"] == "897.88"
    assert r["autoriza_cobranca"] is False


def test_alteracao_de_valor_bloqueia(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["AD2"] = 200
    w.save(arq)
    w.close()
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert {e["codigo"] for e in r["erros"]} >= {"CELULA_DIVERGENTE", "SOMA_FINANCEIRA_DIVERGENTE"}


def test_alteracao_de_cabecalho_bloqueia(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["A1"] = "INDEVIDO"
    w.save(arq)
    w.close()
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "CABECALHO_DIVERGENTE" for x in r["erros"])


def test_boleto_nao_elegivel_nao_pode_ser_exportado(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    decisoes[0]["situacao"] = "revisao"
    decisoes[0]["bloqueios"] = ["DESTINO_NAO_COMPROVADO"]
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "BOLETOS_DIVERGENTES" for x in r["erros"])


def test_pendencias_documentais_geram_ressalva_sem_expor_dados(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    r = _validar(arq, registros, infos, decisoes, unidades_contato_retido={"u1"})
    assert r["estado"] == "conforme_com_ressalvas"
    assert r["indicadores"]["linhas_divida"] == 1
    assert "Titular fictício" not in str(r)


def test_documento_em_unidade_retida_e_erro_critico(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["C2"] = "00000000191"
    w.save(arq)
    w.close()
    registros[0][2] = "00000000191"
    r = _validar(arq, registros, infos, decisoes, unidades_contato_retido={"u1"})
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "CONTATO_RETIDO_EXPOSTO" for x in r["erros"])


def test_sem_linhas_nao_e_sucesso(tmp_path):
    path = tmp_path / "nao-criado.xlsx"
    r = validar_conversao(path, registros=[], linhas_info=[], decisoes=[])
    assert r["estado"] == "sem_arquivo"
    assert r["indicadores"]["linhas_divida"] == 0
