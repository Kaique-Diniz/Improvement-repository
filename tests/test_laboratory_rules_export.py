from datetime import date, datetime, timedelta
from decimal import Decimal

from openpyxl import load_workbook
import pytest
from pydantic import ValidationError

from conversor.domain.canonical import Apontamento, Boleto, Documento, LoteCanonico, Pessoa
from conversor.domain.template import COLUNAS, Template
from conversor.export.build_lines import PerfilSaidaLaboratorio, construir_linhas
from conversor.export.contract import DividaExportacao, LinhaExportacao
from conversor.export.xlsx import escrever_xlsx
from conversor.readers.text_support import ErroLeitura
from conversor.rules.laboratory import RegraLaboratorio, avaliar


def regra(**dados):
    return RegraLaboratorio(id="regra_lab", dias_exclusivo=30, **dados)


@pytest.mark.parametrize("dias,acao", [(31, "incluir"), (30, "adiar"), (29, "adiar"), (-1, "adiar")])
def test_prazo_estritamente_maior_que_30_dias(unidade, boleto, dias, acao):
    referencia = date(2026, 10, 20)
    alterado = Boleto.model_validate(boleto.model_dump() | {"vencimento": referencia - timedelta(days=dias)})
    lote = LoteCanonico(unidades=(unidade,), boletos=(alterado,))
    assert avaliar(lote, regra(), data_ref=referencia, processamento_id="exec")[0].acao == acao


def test_001_exclui_unidade_inteira_inclusive_boleto_maior(unidade, boleto, origem):
    centavo = Boleto.model_validate(boleto.model_dump() | {"id": "bol_centavo", "identificador": "centavo",
        "composicao": {"itens": [{"codigo": "cota", "valor": "0.01", "origem": origem}], "total_original": "0.01"}})
    lote = LoteCanonico(unidades=(unidade,), boletos=(boleto, centavo))
    decisoes = avaliar(lote, regra(excluir_unidade_valor="0.01"), data_ref=date(2026, 10, 20), processamento_id="exec")
    assert [d.acao for d in decisoes] == ["excluir", "excluir"]
    assert all(d.motivo_codigo == "EXCLUSAO_UNIDADE_VALOR" for d in decisoes)


@pytest.mark.parametrize("codigo,namespace,acao", [("A", "habita_lab", "excluir"), ("AJ", "habita_lab", "excluir"),
    ("J", "habita_lab", "excluir"), ("J", "fl_lab", "incluir"), ("Juridico", "habita_lab", "incluir")])
def test_apontamento_exige_namespace_e_codigo_exatos(unidade, boleto, origem, codigo, namespace, acao):
    ap = Apontamento(codigo_original=codigo, namespace_formato=namespace, origem=origem)
    marcado = Boleto.model_validate(boleto.model_dump() | {"apontamentos": (ap,)})
    lote = LoteCanonico(unidades=(unidade,), boletos=(marcado,))
    decisoes = avaliar(lote, regra(apontamentos_excluintes=("A", "AJ", "J"), namespace_apontamentos="habita_lab"),
        data_ref=date(2026, 10, 20), processamento_id="exec")
    assert decisoes[0].acao == acao


def linha(pessoa, *, cadastral=False, valor="100.10"):
    return LinhaExportacao(processamento_id="exec", registro_id=pessoa.unidade_id, tipo="cadastral" if cadastral else "divida",
        nm_cedente_cedente="CREDOR SINTETICO", cedente="0001", pessoa=pessoa,
        divida=None if cadastral else DividaExportacao(contrato="contrato_sintetico", produto="produto_sintetico",
            nome_divida="competencia_sintetica", parcela=1, vencimento="2026-09-17", valor=valor))


def test_excel_30_colunas_nativas_cpf_vazio_zeros_e_alerta_por_unidade(tmp_path, pessoa):
    destino = tmp_path / "saida.xlsx"
    template = Template(id="tpl", nome="Universal", versao="1", espaco_final_coluna_27=False)
    alertas = escrever_xlsx((linha(pessoa), linha(pessoa, cadastral=True)), template, destino, data_ref=date(2026, 10, 20))
    assert len(alertas) == 1
    livro = load_workbook(destino)
    try:
        aba = livro["Dados"]
        assert tuple(c.value for c in aba[1]) == COLUNAS
        assert aba.max_column == 30
        assert aba["B2"].value == "0001"
        assert aba["C2"].value is None
        assert isinstance(aba["AC2"].value, datetime)
        assert Decimal(str(aba["AD2"].value)) == Decimal("100.10")
        assert all(aba.cell(3, c).value is None for c in range(25, 31))
        assert "NAO HOMOLOGADO" in livro.properties.title
    finally: livro.close()


def test_cnpj_nunca_e_exportado_como_cpf(tmp_path, pessoa):
    pessoa = Pessoa.model_validate(pessoa.model_dump() | {"documento": Documento(tipo="cnpj", valor="00000000000100")})
    destino = tmp_path / "saida.xlsx"
    alertas = escrever_xlsx((linha(pessoa),), Template(id="tpl", nome="Universal", versao="1"), destino, data_ref=date(2026, 10, 20))
    livro = load_workbook(destino)
    try: assert livro["Dados"]["C2"].value is None
    finally: livro.close()
    assert alertas and not alertas[0].bloqueante


def test_conteudo_formula_e_texto_literal_e_saida_deterministica(tmp_path, pessoa):
    pessoa = Pessoa.model_validate(pessoa.model_dump() | {"nome": '=HYPERLINK("https://example.invalid")'})
    template = Template(id="tpl", nome="Universal", versao="1")
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    for destino in (a, b): escrever_xlsx((linha(pessoa),), template, destino, data_ref=date(2026, 10, 20))
    assert a.read_bytes() == b.read_bytes()
    livro = load_workbook(a, data_only=False)
    try: assert livro["Dados"]["D2"].data_type == "s"
    finally: livro.close()


def test_valor_sem_precisao_excel_bloqueia_sem_publicar(tmp_path, pessoa):
    destino = tmp_path / "saida.xlsx"
    with pytest.raises(ErroLeitura, match="PRECISAO_XLSX_INCOMPATIVEL"):
        escrever_xlsx((linha(pessoa, valor="999999999999999.99"),), Template(id="tpl", nome="Universal", versao="1"), destino,
                      data_ref=date(2026, 10, 20))
    assert not destino.exists()


def test_construcao_nao_aceita_resultado_de_outra_unidade(unidade, boleto, pessoa):
    lote = LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,))
    d = avaliar(lote, regra(), data_ref=date(2026, 10, 20), processamento_id="exec")[0]
    d = type(d).model_validate(d.model_dump() | {"unidade_id": "unidade_errada"})
    perfil = PerfilSaidaLaboratorio(codificador="habita_bloco_unidade", nome_cedente="SINTETICO", produto="SINTETICO")
    with pytest.raises(ErroLeitura, match="RESULTADO_DE_OUTRA_EXECUCAO_OU_UNIDADE"):
        construir_linhas(lote, (d,), perfil, politica_cadastro="nunca", processamento_id="exec")


def test_regra_nao_admite_apontamento_sem_namespace():
    with pytest.raises(ValidationError):
        regra(apontamentos_excluintes=("J",))


@pytest.mark.parametrize("politica,cadastrais", [("nunca", 0), ("unidades_com_boleto_adiado", 1),
    ("todas_unidades", 1), ("unidades_sem_divida", 0)])
def test_cadastro_unico_para_unidade_com_divida_e_boleto_adiado(unidade, boleto, pessoa, politica, cadastrais):
    unidade = type(unidade).model_validate(unidade.model_dump() | {"bloco_original": "1", "unidade_original": "000001"})
    futuro = Boleto.model_validate(boleto.model_dump() | {"id": "bol_futuro", "identificador": "futuro", "vencimento": "2026-10-10"})
    lote = LoteCanonico(unidades=(unidade,), boletos=(boleto, futuro), pessoas=(pessoa,))
    decisoes = avaliar(lote, regra(), data_ref=date(2026, 10, 20), processamento_id="exec")
    perfil = PerfilSaidaLaboratorio(codificador="habita_bloco_unidade", nome_cedente="SINTETICO", produto="SINTETICO")
    linhas, _ = construir_linhas(lote, decisoes, perfil, politica_cadastro=politica, processamento_id="exec")
    assert sum(l.tipo == "divida" for l in linhas) == 1
    assert sum(l.tipo == "cadastral" for l in linhas) == cadastrais


def test_colisao_de_cedente_normalizado_bloqueia(unidade, pessoa):
    primeira = type(unidade).model_validate(unidade.model_dump() | {"bloco_original": "1", "unidade_original": "000001"})
    segunda = type(unidade).model_validate(primeira.model_dump() | {"id": "outra_unidade", "unidade_original": "0001", "chave_normalizada": "outra:0001"})
    outra = Pessoa.model_validate(pessoa.model_dump() | {"id": "outra_pessoa", "unidade_id": segunda.id})
    lote = LoteCanonico(unidades=(primeira, segunda), pessoas=(pessoa, outra), boletos=())
    perfil = PerfilSaidaLaboratorio(codificador="habita_bloco_unidade", nome_cedente="SINTETICO", produto="SINTETICO")
    with pytest.raises(ErroLeitura, match="CEDENTE_AMBIGUO_APOS_CODIFICACAO"):
        construir_linhas(lote, (), perfil, politica_cadastro="todas_unidades", processamento_id="exec")


def test_exportacao_nao_escolhe_ultimo_titular_silenciosamente(unidade, pessoa):
    outra = Pessoa.model_validate(pessoa.model_dump() | {"id": "outra_pessoa"})
    lote = LoteCanonico(unidades=(unidade,), pessoas=(pessoa, outra), boletos=())
    perfil = PerfilSaidaLaboratorio(codificador="habita_bloco_unidade", nome_cedente="SINTETICO", produto="SINTETICO")
    with pytest.raises(ErroLeitura, match="TITULAR_AMBIGUO"):
        construir_linhas(lote, (), perfil, politica_cadastro="todas_unidades", processamento_id="exec")
