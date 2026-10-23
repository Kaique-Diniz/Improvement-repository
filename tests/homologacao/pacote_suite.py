"""Suíte explícita para o pacote local ignorado pelo Git; nunca imprime documentos.

Executar: python -m pytest -q tests/homologacao/pacote_suite.py
CONVERSOR_PACOTE_SINTETICO permite apontar outra cópia autorizada do mesmo pacote.
"""
from collections import Counter
from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil

from openpyxl import load_workbook
import pytest

from conversor.domain.canonical import LoteCanonico
from conversor.domain.template import COLUNAS
from conversor.laboratorio.comparison import conferir_resumo_xlsx
from conversor.laboratorio.run import executar_pacote, hashes_pacote, caminho_protegido, ler_json_decimal
from conversor.readers.text_support import ErroLeitura
from examples.fase2.gerar_demo import pdf_sintetico

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / "config_exemplos/laboratorio_pacote.json"


@pytest.fixture(scope="session")
def pacote():
    caminho = Path(os.environ.get("CONVERSOR_PACOTE_SINTETICO",
        RAIZ / "tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor"))
    if not (caminho / "esperado/resultado_esperado.json").is_file():
        pytest.fail("Pacote sintético local ausente; fornecer cópia autorizada no caminho documentado.", pytrace=False)
    return caminho


@pytest.fixture(scope="session")
def execucao(pacote, tmp_path_factory):
    saida = tmp_path_factory.mktemp("pacote-saida")
    antes = hashes_pacote(pacote)
    relatorio = executar_pacote(pacote, saida, CONFIG)
    assert antes == hashes_pacote(pacote)
    return relatorio, saida


@pytest.mark.parametrize("familia,unidades,boletos,dividas,cadastrais", [
    ("habita", 4, 6, 2, 0), ("fl", 4, 5, 2, 3)])
def test_financeiro_e_exclusoes_conferem(execucao, familia, unidades, boletos, dividas, cadastrais):
    relatorio, _ = execucao
    caso = relatorio["casos"][familia]
    assert caso["status"] == "executado_sintetico"
    assert (caso["unidades"], caso["boletos_unicos"], caso["linhas_divida"], caso["linhas_cadastrais"]) == (unidades, boletos, dividas, cadastrais)
    assert all(v["ok"] for v in caso["verificacoes_gabarito"])
    assert caso["divergencias_resumo_xlsx"] == []
    assert relatorio["todos_financeiros_conferem"] and relatorio["fixtures_inalteradas"]


@pytest.mark.parametrize("familia,numero,paginas,valor", [
    ("habita", "80000105", [2, 3], "340.00"), ("fl", "900104", [1, 2], "680.00")])
def test_continuacao_nao_duplica_boletos(execucao, familia, numero, paginas, valor):
    relatorio, _ = execucao
    encontrados = [b for b in relatorio["casos"][familia]["boletos"] if b["boleto"] == numero]
    assert len(encontrados) == 1
    assert encontrados[0]["paginas"] == paginas
    assert Decimal(encontrados[0]["original"]) == Decimal(valor)


@pytest.mark.parametrize("familia", ["habita", "fl"])
def test_layout_identificado_sem_promover_homologacao(execucao, familia):
    relatorio, _ = execucao
    caso = relatorio["casos"][familia]
    assert caso["layout_sintetico_identificado"] == f"{familia}_composicao_sintetico_v1"
    operacional = caso["reconhecimento_operacional"]
    assert operacional["bloqueante"] and not operacional["pronto_para_proxima_etapa"]
    assert "FORMATO_NAO_HOMOLOGADO" in operacional["bloqueios"]
    assert relatorio["homologado_producao"] is False


@pytest.mark.parametrize("familia,linhas", [("habita", 2), ("fl", 5)])
def test_excel_universal_tipos_e_cadastros(execucao, familia, linhas):
    relatorio, saida = execucao
    livro = load_workbook(saida / relatorio["casos"][familia]["arquivo_excel"])
    try:
        aba = livro["Dados"]
        assert tuple(c.value for c in aba[1]) == COLUNAS
        assert aba.max_column == 30 and aba.max_row == linhas + 1
        for linha in list(aba.values)[1:]:
            assert linha[2] is None  # Documentos ausentes/inválidos desta fixture continuam vazios.
            if linha[24] is None:
                assert all(v is None for v in linha[24:])
            else:
                assert isinstance(linha[28], datetime)
                assert isinstance(linha[29], (int, float))
        assert not any(c.data_type == "f" for linha in aba for c in linha)
    finally:
        livro.close()


@pytest.mark.parametrize("familia,campos", [("habita", {"DDD1": 1, "FONE1": 1, "EMAIL1": 2}),
    ("fl", {"DDD1": 4, "FONE1": 4, "EMAIL1": 5})])
def test_divergencias_de_contato_sao_reportadas_com_origem(execucao, familia, campos):
    relatorio, _ = execucao
    comparacao = relatorio["casos"][familia]["comparacao_excel"]
    assert Counter(d["campo"] for d in comparacao["divergencias_conteudo"]) == campos
    assert all(d["pagina"] and d["linha_fonte"] and d["fonte_origem"]
               for d in comparacao["divergencias_conteudo"])
    assert len(comparacao["diferencas_representacao"]) == 2
    assert {d["campo"] for d in comparacao["diferencas_representacao"]} == {"VENCIMENTO"}


def test_cadastro_prioritario_com_alerta_e_original_preservado(execucao):
    relatorio, saida = execucao
    fl = relatorio["casos"]["fl"]
    assert sum(o["codigo"] in ("DOCUMENTO_AUSENTE", "DOCUMENTO_INVALIDO") for o in fl["ocorrencias"]) == 4
    conflitos = [o for o in fl["ocorrencias"] if o["codigo"] == "TITULAR_DIVERGENTE_RESOLVIDO_NO_LAB"]
    assert len(conflitos) == 1 and conflitos[0]["gravidade"] == "alerta"
    anterior = LoteCanonico.model_validate_json((saida / "fl_extraido_antes_cadastro.json").read_bytes())
    atual = LoteCanonico.model_validate_json((saida / "fl_canonico.json").read_bytes())
    unidade = conflitos[0]["registro_id"]
    nome_antes = next(p.nome for p in anterior.pessoas if p.unidade_id == unidade)
    nome_depois = next(p.nome for p in atual.pessoas if p.unidade_id == unidade)
    if nome_antes == nome_depois:
        pytest.fail("Prioridade de titular aprovada para o laboratório não aplicada.", pytrace=False)
    assert conflitos[0]["origem"]["arquivo_id"] == "fl_cadastro"


def test_relatorio_nao_expoe_valores_de_contato(execucao):
    _, saida = execucao
    relatorio = (saida / "relatorio_divergencias.json").read_text()
    for familia in ("habita", "fl"):
        lote = LoteCanonico.model_validate_json((saida / f"{familia}_canonico.json").read_bytes())
        for pessoa in lote.pessoas:
            if pessoa.nome in relatorio:
                pytest.fail("Nome exposto no relatório agregado.", pytrace=False)
            for email in pessoa.contato.emails:
                if email in relatorio:
                    pytest.fail("E-mail exposto no relatório agregado.", pytrace=False)
            for telefone in pessoa.contato.telefones:
                if telefone.numero in relatorio:
                    pytest.fail("Telefone exposto no relatório agregado.", pytrace=False)


def test_mesmos_inputs_produzem_mesmas_saidas(pacote, execucao, tmp_path):
    _, primeira = execucao
    segunda = tmp_path / "repeticao"
    executar_pacote(pacote, segunda, CONFIG)
    assert hashes_pacote(primeira) == hashes_pacote(segunda)


def copiar_pacote(pacote, tmp_path):
    destino = tmp_path / "copia"
    shutil.copytree(pacote, destino)
    return destino


def test_gabarito_financeiro_nao_alimenta_resultados(pacote, execucao, tmp_path):
    copia = copiar_pacote(pacote, tmp_path)
    esperado = copia / "esperado/resultado_esperado.json"
    dados = json.loads(esperado.read_text())
    dados["habita"]["boletos_elegiveis"]["80000101"] = 99999
    esperado.write_text(json.dumps(dados))
    resultado = executar_pacote(copia, tmp_path / "saida", CONFIG)
    assert not resultado["todos_financeiros_conferem"]
    caso = resultado["casos"]["habita"]
    assert not next(v for v in caso["verificacoes_gabarito"] if v["campo"] == "boletos_elegiveis")["ok"]
    _, anterior = execucao
    assert (anterior / caso["arquivo_excel"]).read_bytes() == (tmp_path / "saida" / caso["arquivo_excel"]).read_bytes()


@pytest.mark.parametrize("coluna,codigo", [(4, "RESUMO_VENCIMENTO_DIVERGENTE"),
    (5, "RESUMO_COMPETENCIA_DIVERGENTE"), (6, "RESUMO_VALOR_DIVERGENTE")])
def test_resumo_independente_detecta_divergencias(pacote, execucao, tmp_path, coluna, codigo):
    _, saida = execucao
    lote = LoteCanonico.model_validate_json((saida / "fl_canonico.json").read_bytes())
    livro = load_workbook(pacote / "fl/fl_blocos_resumo_sintetico.xlsx")
    alterado = tmp_path / "resumo.xlsx"
    try:
        livro["Resumo"].cell(2, coluna).value = {4: "2000-01-01", 5: "01/2000", 6: 99999}[coluna]
        livro.save(alterado)
    finally:
        livro.close()
    assert codigo in {d["codigo"] for d in conferir_resumo_xlsx(alterado, lote)}


def test_fonte_desconhecida_bloqueia_excel(pacote, tmp_path):
    copia = copiar_pacote(pacote, tmp_path)
    (copia / "habita/habita_tree_sintetico.pdf").write_bytes(pdf_sintetico(["AMOSTRA SINTETICA\nFORMATO DESCONHECIDO"]))
    saida = tmp_path / "saida"
    resultado = executar_pacote(copia, saida, CONFIG)
    assert resultado["casos"]["habita"]["codigo"] == "LAYOUT_DESCONHECIDO"
    assert not (saida / "habita_resultado_laboratorio.xlsx").exists()


def test_identidade_de_outro_condominio_bloqueia(pacote, tmp_path):
    dados = json.loads(CONFIG.read_text())
    next(c for c in dados["casos"] if c["familia"] == "habita")["codigo_condominio_leitor"] = "9999"
    config = tmp_path / "config.json"
    config.write_text(json.dumps(dados))
    saida = tmp_path / "saida"
    resultado = executar_pacote(pacote, saida, config)
    assert resultado["casos"]["habita"]["status"] == "bloqueado"
    assert not (saida / "habita_resultado_laboratorio.xlsx").exists()


def test_assinaturas_ambiguas_bloqueiam_ambos_os_leitores(pacote, tmp_path):
    dados = json.loads(CONFIG.read_text())
    for caso in dados["casos"]:
        caso["marcadores"] = ["AMOSTRA", "CONDOMINIO"]
    config = tmp_path / "ambiguo.json"
    config.write_text(json.dumps(dados))
    saida = tmp_path / "saida"
    resultado = executar_pacote(pacote, saida, config)
    assert all(c["codigo"] == "LAYOUT_AMBIGUO" for c in resultado["casos"].values())
    assert not list(saida.glob("*.xlsx"))


def test_destino_nao_pode_sobrescrever_fixture(pacote):
    with pytest.raises(ErroLeitura, match="SAIDA_DEVE_SER_SEPARADA_DAS_FIXTURES"):
        executar_pacote(pacote, pacote / "saida", CONFIG)


def test_caminho_fora_do_pacote_e_rejeitado(tmp_path):
    with pytest.raises(ErroLeitura, match="CAMINHO_FORA_DO_PACOTE"):
        caminho_protegido(tmp_path, "../fora.pdf")


@pytest.mark.parametrize("conteudo", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_json_invalido_e_rejeitado_sem_logar_conteudo(tmp_path, conteudo):
    arquivo = tmp_path / "invalido.json"
    arquivo.write_text(conteudo)
    with pytest.raises(ErroLeitura):
        ler_json_decimal(arquivo)
