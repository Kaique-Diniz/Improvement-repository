from copy import deepcopy
from datetime import date

import pytest

from conversor.application.ports import ErroAplicacao
from conversor.domain.recognition import Motivo, ResultadoReconhecimento


@pytest.mark.parametrize("documento,condominio,formato", [
    ("habita_tree", "cond_tree_sintetico", "fmt_habita_sintetico_v1"),
    ("fl_plaza", "cond_plaza_sintetico", "fmt_fl_sintetico_v1"),
    ("habita_outro_condominio", "cond_outro_sintetico", "fmt_habita_sintetico_v1"),
])
def test_familias_e_reuso_em_outro_condominio(reconhecer, textos_sinteticos, documento, condominio, formato):
    resultado = reconhecer(textos_sinteticos[documento])
    assert resultado.estado == "conhecido_validado"
    assert resultado.selecao.condominio_id == condominio
    assert resultado.selecao.versoes.formato_id == formato
    assert resultado.pronto_para_proxima_etapa
    assert not resultado.bloqueante
    assert resultado.evidencias
    assert all(p.cobertura_percentual == 100 for p in resultado.pontuacoes if p.elegivel)


def test_mesmos_dados_versoes_e_data_produzem_mesmo_resultado(reconhecer, textos_sinteticos):
    a = reconhecer(textos_sinteticos["habita_tree"])
    b = reconhecer(textos_sinteticos["habita_tree"])
    assert a.model_dump_json() == b.model_dump_json()
    assert ResultadoReconhecimento.model_validate_json(a.model_dump_json()) == a


def test_logo_ou_nome_de_condominio_nao_sao_classificacao(reconhecer):
    resultado = reconhecer(["HABITA\nTREE MORUMBI\nCódigo Condomínio: SYN-TREE"])
    assert resultado.estado == "desconhecido"
    assert resultado.bloqueante
    assert resultado.selecao is None


def test_normalizacao_de_acentos_caixa_e_espacos(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0].replace("Inadimplência Atualizada", "INADIMPLENCIA   ATUALIZADA")
    texto = texto.replace("Código", "CODIGO").replace("Bloco: ", "Bloco:")
    assert reconhecer([texto]).pronto_para_proxima_etapa


def test_palavra_parcial_nao_e_marcador(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["fl_plaza"][0].replace("Saldo", "Saldos")
    resultado = reconhecer([texto])
    assert resultado.estado == "desconhecido"
    pontuacao = next(p for p in resultado.pontuacoes if p.formato_id == "fmt_fl_sintetico_v1")
    assert pontuacao.pontos == 3
    assert not pontuacao.elegivel


def test_marcadores_nao_sao_colados_de_paginas_distintas(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0]
    primeira, segunda = texto.split("Bloco:")
    resultado = reconhecer([primeira, "Bloco:" + segunda])
    assert resultado.estado == "desconhecido"
    assert resultado.bloqueante


def test_dois_layouts_no_documento_sao_ambiguos(reconhecer, textos_sinteticos):
    resultado = reconhecer(textos_sinteticos["habita_tree"] + textos_sinteticos["fl_plaza"])
    assert resultado.estado == "ambiguo"
    assert resultado.bloqueios == (Motivo.FORMATO_AMBIGUO,)
    assert resultado.selecao is None


def test_maior_score_nao_oculta_outro_candidato(reconhecer, textos_sinteticos, dados_reconhecimento, assinaturas_reconhecimento):
    formato = deepcopy(dados_reconhecimento["formatos"][0])
    formato.update(id="fmt_concorrente", nome="Layout Concorrente", status="rascunho", aprovacao=None)
    dados_reconhecimento["formatos"].append(formato)
    assinatura = deepcopy(assinaturas_reconhecimento["layouts"][0])
    assinatura.update(id="assinatura_concorrente", formato_id="fmt_concorrente")
    assinatura["marcadores"] = assinatura["marcadores"][:2]
    assinatura["minimo_pontos"] = 2
    assinaturas_reconhecimento["layouts"].append(assinatura)
    resultado = reconhecer(textos_sinteticos["habita_tree"])
    assert resultado.estado == "ambiguo"
    assert sorted(p.pontos for p in resultado.pontuacoes if p.elegivel) == [2, 4]
    assert resultado.selecao is None


@pytest.mark.parametrize("alvo", ["formato", "assinaturas"])
def test_rascunho_nao_vira_formato_homologado(reconhecer, textos_sinteticos, dados_reconhecimento, assinaturas_reconhecimento, alvo):
    if alvo == "formato":
        dados_reconhecimento["formatos"][0].update(status="rascunho", aprovacao=None)
    else:
        assinaturas_reconhecimento.update(status="rascunho", aprovacao=None)
    resultado = reconhecer(textos_sinteticos["habita_tree"])
    assert resultado.estado == "desconhecido"
    assert resultado.bloqueante


@pytest.mark.parametrize("campo,motivo", [
    ("Código Administradora: ADM-SYN-H", Motivo.ADMINISTRADORA_DESCONHECIDA),
    ("Código Condomínio: SYN-TREE", Motivo.CONDOMINIO_DESCONHECIDO),
])
def test_nao_infere_identidade_pelo_layout_ou_unico_cadastro(reconhecer, textos_sinteticos, campo, motivo):
    texto = textos_sinteticos["habita_tree"][0].replace(campo, "Identificação ausente")
    resultado = reconhecer([texto])
    assert resultado.estado == "desconhecido"
    assert motivo in resultado.bloqueios
    assert resultado.selecao is None


def test_codigo_exige_valor_inteiro_nao_substring(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0].replace("SYN-TREE", "SYN-TREE-99")
    assert Motivo.CONDOMINIO_DESCONHECIDO in reconhecer([texto]).bloqueios


def test_duas_identidades_nao_sao_desempatadas_pelo_formato(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0] + "\nCódigo Administradora: ADM-SYN-F\nCódigo Condomínio: SYN-PLAZA"
    resultado = reconhecer([texto])
    assert resultado.estado == "ambiguo"
    assert Motivo.ADMINISTRADORA_AMBIGUA in resultado.bloqueios
    assert Motivo.CONDOMINIO_AMBIGUO in resultado.bloqueios
    assert resultado.selecao is None


def test_mesmo_formato_com_dois_condominios_bloqueia(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0] + "\nCódigo Condomínio: SYN-OUTRO"
    resultado = reconhecer([texto])
    assert resultado.estado == "ambiguo"
    assert resultado.bloqueios == (Motivo.CONDOMINIO_AMBIGUO,)


def test_identidades_conflitantes_com_vinculo_bloqueiam(reconhecer, textos_sinteticos):
    texto = textos_sinteticos["habita_tree"][0].replace("ADM-SYN-H", "ADM-SYN-F")
    resultado = reconhecer([texto])
    assert Motivo.VINCULO_INCOMPATIVEL in resultado.bloqueios
    assert resultado.selecao is None


def test_formato_correto_para_condominio_errado_nao_processa(reconhecer, textos_sinteticos, dados_reconhecimento):
    dados_reconhecimento["formatos"][1]["administradora_ids"].append("adm_habita_sintetica")
    dados_reconhecimento["condominios"][0]["formato_ids"] = ["fmt_fl_sintetico_v1"]
    resultado = reconhecer(textos_sinteticos["habita_tree"])
    assert resultado.estado == "desconhecido"
    assert resultado.bloqueios == (Motivo.FORMATO_INCOMPATIVEL,)


def test_reconhecer_nao_aprova_perfil_ou_regra(reconhecer, textos_sinteticos, dados_reconhecimento):
    dados_reconhecimento["perfis_condominio"][0].update(status="rascunho", aprovacao=None)
    dados_reconhecimento["regras_cobranca"][0].update(status="rascunho", aprovacao=None)
    resultado = reconhecer(textos_sinteticos["habita_tree"])
    assert resultado.estado == "conhecido_validado"
    assert resultado.selecao.versoes.perfil_id == "perfil_tree_v1"
    assert resultado.bloqueios == (Motivo.PERFIL_NAO_APROVADO, Motivo.REGRA_NAO_APROVADA)
    assert not resultado.pronto_para_proxima_etapa


def test_data_explicita_consulta_vinculo_e_vigencia(reconhecer, textos_sinteticos, dados_reconhecimento):
    resultado = reconhecer(textos_sinteticos["habita_tree"], data_ref=date(2025, 12, 31))
    assert resultado.bloqueios == (Motivo.VINCULO_INCOMPATIVEL,)
    dados_reconhecimento["regras_cobranca"][0]["vigente_ate"] = "2026-10-21"
    resultado = reconhecer(textos_sinteticos["habita_tree"])
    assert resultado.estado == "conhecido_validado"
    assert Motivo.REGRA_FORA_DA_VIGENCIA in resultado.bloqueios


def test_cnpj_condominio_so_vale_no_rotulo_configurado(reconhecer, textos_sinteticos, assinaturas_reconhecimento):
    # CNPJ estrutural sintético; não representa nem valida uma pessoa jurídica real.
    identificador = assinaturas_reconhecimento["condominios"][0]["identificadores"][0]
    identificador.update(tipo="cnpj", rotulo="CNPJ do Condomínio", valor="00000000000100")
    texto = textos_sinteticos["habita_tree"][0].replace("Código Condomínio: SYN-TREE", "CNPJ do Proprietário: 00.000.000/0001-00")
    assert Motivo.CONDOMINIO_DESCONHECIDO in reconhecer([texto]).bloqueios
    assert reconhecer([texto.replace("CNPJ do Proprietário", "CNPJ do Condomínio")]).pronto_para_proxima_etapa


def test_resultado_nao_expoe_conteudo_ou_nomes(reconhecer, textos_sinteticos):
    sentinela = "SENTINELA_PRIVADA_NAO_LOGAR"
    resultado = reconhecer([textos_sinteticos["habita_tree"][0] + "\n" + sentinela])
    publico = resultado.model_dump_json()
    assert sentinela not in publico
    assert "Inadimplência Atualizada" not in publico
    assert "SYN-TREE" not in publico
    assert "texto" not in type(resultado.evidencias[0]).model_fields


def test_referencias_inexistentes_falham_explicitamente(reconhecer, textos_sinteticos, assinaturas_reconhecimento):
    assinaturas_reconhecimento["layouts"][0]["formato_id"] = "formato_inexistente"
    with pytest.raises(ErroAplicacao, match="ASSINATURAS_COM_REFERENCIA_INEXISTENTE"):
        reconhecer(textos_sinteticos["habita_tree"])


@pytest.mark.parametrize("campo,motivo", [("Código Condomínio: OUTRO-NAO-CADASTRADO", Motivo.CONDOMINIO_AMBIGUO),
    ("Código Administradora: ADM-NAO-CADASTRADA", Motivo.ADMINISTRADORA_AMBIGUA)])
def test_identidade_conhecida_nao_oculta_outro_codigo_desconhecido(reconhecer, textos_sinteticos, campo, motivo):
    resultado = reconhecer([textos_sinteticos["habita_tree"][0] + "\n" + campo])
    assert resultado.estado == "ambiguo"
    assert motivo in resultado.bloqueios
    assert resultado.selecao is None


@pytest.mark.parametrize("tipo", ["xlsx", "csv"])
def test_reconhecimento_de_assinatura_por_tipo_real(reconhecer, textos_sinteticos, dados_reconhecimento, tipo):
    from io import StringIO
    import csv
    from test_probe import xlsx_sintetico
    dados_reconhecimento["formatos"][0]["tipo_arquivo"] = tipo
    linhas = []
    for linha in textos_sinteticos["habita_tree"][0].splitlines():
        linhas.append(linha.split(":", 1) if linha.startswith("Código") else [linha, ""])
    if tipo == "xlsx":
        conteudo = xlsx_sintetico(linhas)
    else:
        destino = StringIO(newline="")
        csv.writer(destino, delimiter=";").writerows(linhas)
        conteudo = destino.getvalue().encode()
    resultado = reconhecer(conteudo)
    assert resultado.tipo == tipo
    assert resultado.pronto_para_proxima_etapa


def test_mesmo_formato_em_outra_administradora_sem_copiar_leitor(reconhecer, textos_sinteticos, dados_reconhecimento):
    dados_reconhecimento["formatos"][0]["administradora_ids"].append("adm_fl_sintetica")
    condo = dados_reconhecimento["condominios"][2]
    condo["administradora_id"] = "adm_fl_sintetica"
    condo["vinculos"][0]["administradora_id"] = "adm_fl_sintetica"
    texto = textos_sinteticos["habita_outro_condominio"][0].replace("ADM-SYN-H", "ADM-SYN-F")
    resultado = reconhecer([texto])
    assert resultado.pronto_para_proxima_etapa
    assert resultado.selecao.versoes.formato_id == "fmt_habita_sintetico_v1"
    assert resultado.selecao.versoes.administradora_id == "adm_fl_sintetica"


def test_reconhecimento_preserva_vinculo_historico_em_vez_de_usar_apenas_atual(reconhecer, textos_sinteticos, dados_reconhecimento):
    dados_reconhecimento["formatos"][0]["administradora_ids"].append("adm_fl_sintetica")
    condo = dados_reconhecimento["condominios"][0]
    condo.update(administradora_id="adm_fl_sintetica", vinculos=[
        {"administradora_id": "adm_habita_sintetica", "inicio": "2026-01-01", "fim": "2026-11-01"},
        {"administradora_id": "adm_fl_sintetica", "inicio": "2026-11-01"}])
    resultado = reconhecer(textos_sinteticos["habita_tree"], data_ref=date(2026, 10, 21))
    assert resultado.pronto_para_proxima_etapa
    assert resultado.selecao.versoes.administradora_id == "adm_habita_sintetica"
    novo = reconhecer(textos_sinteticos["habita_tree"], data_ref=date(2026, 11, 1))
    assert Motivo.VINCULO_INCOMPATIVEL in novo.bloqueios
