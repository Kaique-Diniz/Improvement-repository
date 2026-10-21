"""Regressão individual das 21 diferenças; requer o pacote sintético autorizado."""
import json
import shutil

from openpyxl import load_workbook
import pytest

from conversor.laboratorio.review import revisar
from conversor.readers.text_support import ErroLeitura
from .pacote_suite import pacote, execucao, CONFIG


@pytest.fixture(scope="session")
def revisao(pacote, execucao):
    _, saida = execucao
    return revisar(pacote, saida, CONFIG)


@pytest.mark.parametrize("caso,celula,classificacao,motivo", [
    ("habita", "L2", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("habita", "M2", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("habita", "V2", "inconsistencia_do_gabarito", "GABARITO_EMAIL_DIFERE_DA_FONTE"),
    ("habita", "V3", "inconsistencia_do_gabarito", "GABARITO_CONTEM_EMAIL_AUSENTE_DA_FONTE"),
    ("habita", "AC2", "problema_de_representacao_no_excel", "GABARITO_TEXTO_ISO_SAIDA_DATA_NATIVA_CONFORME_CONTRATO"),
    ("habita", "AC3", "problema_de_representacao_no_excel", "GABARITO_TEXTO_ISO_SAIDA_DATA_NATIVA_CONFORME_CONTRATO"),
    ("fl", "L2", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "M2", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "V2", "inconsistencia_do_gabarito", "GABARITO_EMAIL_DIFERE_DA_FONTE"),
    ("fl", "L3", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "M3", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "V3", "inconsistencia_do_gabarito", "GABARITO_EMAIL_DIFERE_DA_FONTE"),
    ("fl", "L4", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "M4", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "V4", "inconsistencia_do_gabarito", "GABARITO_EMAIL_DIFERE_DA_FONTE"),
    ("fl", "L5", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "M5", "inconsistencia_do_gabarito", "GABARITO_OMITE_CONTATO_DOCUMENTADO"),
    ("fl", "V5", "inconsistencia_do_gabarito", "GABARITO_EMAIL_DIFERE_DA_FONTE"),
    ("fl", "V6", "inconsistencia_do_gabarito", "GABARITO_CONTEM_EMAIL_AUSENTE_DA_FONTE"),
    ("fl", "AC2", "problema_de_representacao_no_excel", "GABARITO_TEXTO_ISO_SAIDA_DATA_NATIVA_CONFORME_CONTRATO"),
    ("fl", "AC5", "problema_de_representacao_no_excel", "GABARITO_TEXTO_ISO_SAIDA_DATA_NATIVA_CONFORME_CONTRATO"),
])
def test_cada_celula_conferida_com_fonte_canonico_excel_e_gabarito(revisao, caso, celula, classificacao, motivo):
    encontrados = [i for i in revisao["itens"] if (i["caso"], i["celula"]) == (caso, celula)]
    assert len(encontrados) == 1
    item = encontrados[0]
    assert item["classificacao"] == classificacao and item["motivo"] == motivo
    assert item["fonte_confere_com_canonico"] and item["canonico_confere_com_excel"]
    assert item["pagina"] and item["linha_fonte"]
    assert item["status"] == ("pendente_revisao_gabarito" if classificacao == "inconsistencia_do_gabarito" else "esclarecida_sem_correcao")


def test_resumo_nao_oculta_diferencas_nem_aprova_producao(revisao):
    assert revisao["total"] == 21
    assert revisao["classificacoes"] == {"erro_de_extracao": 0, "erro_de_normalizacao": 0,
        "problema_de_representacao_no_excel": 4, "inconsistencia_do_gabarito": 17}
    assert revisao["correcoes_em_leitores_ou_regras"] == 0
    assert revisao["homologado_producao"] is False
    assert revisao["fixtures_inalteradas"]


@pytest.mark.parametrize("alteracao,codigo", [
    ("email_canonico", "FONTE_E_CANONICO_DIVERGEM_NAO_CLASSIFICAR_GABARITO"),
    ("telefone_normalizado", "FONTE_E_CANONICO_DIVERGEM_NAO_CLASSIFICAR_GABARITO"),
    ("email_excel", "CANONICO_E_EXCEL_DIVERGEM_NAO_CLASSIFICAR_GABARITO"),
    ("data_texto", "EXCEL_NAO_CONTEM_DATA_NATIVA_INTEGRA"),
    ("data_dia_errado", "DATAS_NAO_EQUIVALENTES"),
])
def test_diagnostico_nao_acusa_gabarito_se_etapas_anteriores_falharem(pacote, execucao, tmp_path, alteracao, codigo):
    _, saida = execucao
    copia = tmp_path / "execucao"
    shutil.copytree(saida, copia)
    if alteracao in ("email_canonico", "telefone_normalizado"):
        canonico = copia / "habita_canonico.json"
        dados = json.loads(canonico.read_text())
        contato = dados["pessoas"][0]["contato"]
        if alteracao == "email_canonico":
            contato["emails"] = ["regressao@example.invalid"]
        else:
            contato["telefones"][0]["ddd"] = "21"
        canonico.write_text(json.dumps(dados))
    else:
        excel = copia / "habita_resultado_laboratorio.xlsx"
        livro = load_workbook(excel)
        try:
            aba = livro["Dados"]
            if alteracao == "email_excel":
                aba["V2"] = "regressao@example.invalid"
            elif alteracao == "data_texto":
                aba["AC2"] = aba["AC2"].value.date().isoformat()
            else:
                aba["AC2"] = aba["AC2"].value.replace(day=1)
            livro.save(excel)
        finally:
            livro.close()
    with pytest.raises(ErroLeitura, match=codigo):
        revisar(pacote, copia, CONFIG)


def test_revisao_nao_expoe_contatos(revisao, execucao):
    _, saida = execucao
    texto = json.dumps(revisao)
    for caso in ("habita", "fl"):
        pessoas = json.loads((saida / f"{caso}_canonico.json").read_text())["pessoas"]
        for pessoa in pessoas:
            valores = [pessoa["nome"]] + pessoa["contato"]["emails"] + [t["numero"] for t in pessoa["contato"]["telefones"]]
            if any(valor in texto for valor in valores):
                pytest.fail("Dado cadastral exposto na revisão individual.", pytrace=False)
