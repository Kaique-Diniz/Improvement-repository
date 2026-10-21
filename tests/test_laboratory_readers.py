from decimal import Decimal

import pytest

from conversor.application.enrichment import complementar_cadastro
from conversor.domain.canonical import Endereco, LoteCanonico
from conversor.readers.cadastro import LeitorCadastroFLSintetico
from conversor.readers.fl import LeitorFLSintetico
from conversor.readers.habita import LeitorHabitaSintetico
from conversor.readers.text_support import ContextoLeitura, ErroLeitura, dinheiro_brl
from examples.fase2.gerar_demo import pdf_sintetico


@pytest.fixture
def habita_textos():
    cabecalho = "Inadimplencia Atualizada\nAmostra sintetica\nCondominio: 9999 - LAB\n"
    return [cabecalho + "Bloco: DEP  Unidade: 000001  PESSOA SINTETICA  CPF: (ausente)\n"
            "10000001  10/07/26  202607  94  CONDOMINIO JULHO/2026  300,00  6,00  2,00  308,00\n"
            "--- CONTINUA NA PAGINA SEGUINTE ---",
            cabecalho + "CONTINUACAO DO BOLETO 10000001 DA UNIDADE DEP-000001\n"
            "1372 FUNDO DE RESERVA 40,00 0,00 0,00 40,00\n"
            "Total do boleto: 340,00 6,00 2,00 348,00\nTotal da Unidade: 340,00 6,00 2,00 348,00"]


@pytest.fixture
def fl_textos():
    cabecalho = "FL CONDOMINIOS - Relatorio W002A\nW002A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\nInadimplencia com composicao\n"
    return [cabecalho + "0001 TORRE A - PESSOA SINTETICA\nVenc. Comp. Cod. Descricao Valor Saldo\n"
            "17/09/26 09/2026 900001 CONDOMINIO 1.000,00 1.000,00\n"
            "AGUA DESCONTO (20,00) 980,00\n--- CONTINUA NA PAGINA 2 ---",
            cabecalho + "CONTINUACAO DO BOLETO 900001 - 0001 TORRE A\nGAS 20,00 1.000,00\n"
            "FIM DO RELATORIO: 1 UNIDADES E 1 BOLETOS"]


def ctx(familia):
    leitor = LeitorHabitaSintetico if familia == "habita" else LeitorFLSintetico
    return ContextoLeitura("cond_lab", "adm_lab", leitor.formato_id, "fonte_lab", "9999" if familia == "habita" else "LAB")


def test_habita_continuado_total_original_separado_de_acrescimos(habita_textos):
    lote = LeitorHabitaSintetico().ler(pdf_sintetico(habita_textos), contexto=ctx("habita"))
    assert len(lote.unidades) == len(lote.boletos) == 1
    boleto = lote.boletos[0]
    assert boleto.composicao.total_original == Decimal("340.00")
    assert (boleto.multa, boleto.juros) == (Decimal("6.00"), Decimal("2.00"))
    assert {o.pagina for o in boleto.origens} == {1, 2}
    assert any(o.continuacao_de for o in boleto.origens)
    assert boleto.emissao is None
    assert boleto.competencia == "2026-07"


@pytest.mark.parametrize("falha,codigo", [("continuidade", "CONTINUACAO_DIVERGENTE"), ("soma", "SOMA_BOLETO_INCONSISTENTE"),
    ("data", "DATA_DE_BOLETO_INVALIDA"), ("desconhecido", "LINHA_FINANCEIRA_NAO_RECONHECIDA"),
    ("unidade_total", "TOTAL_UNIDADE_AUSENTE"), ("item_repetido", "SOMA_BOLETO_INCONSISTENTE")])
def test_habita_rejeita_erros_sem_silenciar(habita_textos, falha, codigo):
    textos = list(habita_textos)
    if falha == "continuidade": textos[1] = textos[1].replace("CONTINUACAO DO BOLETO 10000001", "CONTINUACAO DO BOLETO 10000002")
    elif falha == "soma": textos[1] = textos[1].replace("Total do boleto: 340,00", "Total do boleto: 999,00")
    elif falha == "data": textos[0] = textos[0].replace("10/07/26", "99/07/26")
    elif falha == "desconhecido": textos[1] = textos[1].replace("1372 FUNDO", "REGISTRO DESCONHECIDO FUNDO")
    elif falha == "unidade_total": textos[1] = textos[1].split("\nTotal da Unidade")[0]
    elif falha == "item_repetido": textos[1] = textos[1].replace("1372 FUNDO DE RESERVA 40,00 0,00 0,00 40,00", "1372 FUNDO DE RESERVA 40,00 0,00 0,00 40,00\n1372 FUNDO DE RESERVA 40,00 0,00 0,00 40,00")
    with pytest.raises(ErroLeitura, match=codigo):
        LeitorHabitaSintetico().ler(pdf_sintetico(textos), contexto=ctx("habita"))


def test_habita_continuacao_incompleta_bloqueia_com_pagina(habita_textos):
    with pytest.raises(ErroLeitura, match="CONTINUACAO_AUSENTE") as erro:
        LeitorHabitaSintetico().ler(pdf_sintetico(habita_textos[:1]), contexto=ctx("habita"))
    assert erro.value.pagina == 1


def test_fl_composto_desconto_e_saldo_sem_duplicacao(fl_textos):
    lote = LeitorFLSintetico().ler(pdf_sintetico(fl_textos), contexto=ctx("fl"))
    boleto = lote.boletos[0]
    assert len(lote.boletos) == 1
    assert boleto.composicao.total_original == Decimal("1000.00")
    assert [i.valor for i in boleto.composicao.itens] == [Decimal("1000.00"), Decimal("-20.00"), Decimal("20.00")]
    assert {o.pagina for o in boleto.origens} == {1, 2}


@pytest.mark.parametrize("falha,codigo", [("saldo", "SALDO_ACUMULADO_INCONSISTENTE"), ("contagem", "CONTAGEM_DE_RELATORIO_INCONSISTENTE"),
    ("continuidade", "CONTINUACAO_DIVERGENTE"), ("sem_controle", "CONTAGEM_DE_RELATORIO_INCONSISTENTE")])
def test_fl_rejeita_saldo_continuidade_e_contagem_inconsistentes(fl_textos, falha, codigo):
    textos = list(fl_textos)
    if falha == "saldo": textos[1] = textos[1].replace("GAS 20,00 1.000,00", "GAS 20,00 9.999,00")
    elif falha == "contagem": textos[1] = textos[1].replace("1 UNIDADES", "2 UNIDADES")
    elif falha == "continuidade": textos[1] = textos[1].replace("0001 TORRE A", "0002 TORRE A")
    elif falha == "sem_controle": textos[1] = textos[1].split("FIM DO RELATORIO")[0]
    with pytest.raises(ErroLeitura, match=codigo):
        LeitorFLSintetico().ler(pdf_sintetico(textos), contexto=ctx("fl"))


@pytest.mark.parametrize("valor,esperado", [("1.200,10", "1200.10"), ("(20,01)", "-20.01"), ("-0,01", "-0.01")])
def test_brl_decimal_com_sinal_exato(valor, esperado):
    assert dinheiro_brl(valor) == Decimal(esperado)


@pytest.mark.parametrize("valor", ["1.20,00", "0.01", "(20,00", "NaN"])
def test_brl_erro_de_formato_nao_e_arredondado(valor):
    with pytest.raises(ErroLeitura): dinheiro_brl(valor)


def test_cadastro_chave_completa_cpf_ausente_e_contato(fl_textos):
    texto = "FL CONDOMINIOS\nW045A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\n" \
            "0001 TORRE A  PESSOA SINTETICA  Proprietario  Rua Exemplo, 10  (vazio)  teste@example.invalid\n+55 11 90000-0001"
    cadastro = LeitorCadastroFLSintetico().ler(pdf_sintetico([texto]), contexto=ctx("fl"))
    assert set(cadastro) == {("cond_lab", "A", "0001")}
    pessoa = next(iter(cadastro.values()))
    assert pessoa.documento is None
    assert len(pessoa.contato.telefones) == 1
    lote = LeitorFLSintetico().ler(pdf_sintetico(fl_textos), contexto=ctx("fl"))
    enriquecido = complementar_cadastro(lote, cadastro, Endereco(cep="00000000"))
    assert enriquecido.pessoas[0].contato.endereco.cep == "00000000"


def test_conflito_de_titular_bloqueia_por_padrao(fl_textos):
    texto = "W045A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\n" \
            "0001 TORRE A  OUTRO TITULAR SINTETICO  Proprietario  Rua Exemplo, 10  (vazio)  (vazio)"
    cadastro = LeitorCadastroFLSintetico().ler(pdf_sintetico([texto]), contexto=ctx("fl"))
    lote = LeitorFLSintetico().ler(pdf_sintetico(fl_textos), contexto=ctx("fl"))
    with pytest.raises(ErroLeitura, match="TITULAR_DIVERGENTE"):
        complementar_cadastro(lote, cadastro, Endereco())


def test_prioridade_cadastro_somente_com_politica_explicita_e_auditoria(fl_textos):
    texto = "W045A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\n" \
            "0001 TORRE A  OUTRO TITULAR SINTETICO  Proprietario  Rua Exemplo, 10  (vazio)  (vazio)"
    cadastro = LeitorCadastroFLSintetico().ler(pdf_sintetico([texto]), contexto=ctx("fl"))
    lote = LeitorFLSintetico().ler(pdf_sintetico(fl_textos), contexto=ctx("fl"))
    original = lote.model_dump_json()
    politica = "cadastro_confirmado_no_laboratorio"
    with pytest.raises(ErroLeitura, match="RESOLUCAO_DE_TITULAR_EXIGE_AUDITORIA"):
        complementar_cadastro(lote, cadastro, Endereco(), politica_titular=politica)
    alertas = []
    resultado = complementar_cadastro(lote, cadastro, Endereco(), politica_titular=politica,
                                    processamento_id="exec_lab", alertas=alertas)
    assert resultado.pessoas[0].nome == next(iter(cadastro.values())).nome
    assert resultado.pessoas[0].documento is None
    assert lote.model_dump_json() == original
    assert len(alertas) == 1
    assert alertas[0].codigo == "TITULAR_DIVERGENTE_RESOLVIDO_NO_LAB"
    assert alertas[0].registro_id == lote.unidades[0].id
    assert not alertas[0].bloqueante and alertas[0].origem.pagina == 1


def test_enriquecimento_nao_escolhe_ultimo_titular_silenciosamente(unidade, pessoa):
    outra = type(pessoa).model_validate(pessoa.model_dump() | {"id": "outra_pessoa"})
    lote = LoteCanonico(unidades=(unidade,), pessoas=(pessoa, outra), boletos=())
    with pytest.raises(ErroLeitura, match="TITULAR_AMBIGUO"):
        complementar_cadastro(lote, {}, Endereco())
