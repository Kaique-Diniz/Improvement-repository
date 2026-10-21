from copy import deepcopy
import json

import pytest

from conversor.adapters.json_repository import RepositorioJSON
from conversor.domain.catalog import Catalogo
from conversor.domain.canonical import LoteCanonico
from examples.fase2.gerar_demo import pdf_sintetico
from homologacao.runner import main


@pytest.fixture
def caso_local(tmp_path):
    caso = {"id": "caso_sintetico", "arquivo": "fonte.pdf", "data_ref": "2026-10-21",
            "reconhecimento_esperado": "reconhecimento.esperado.json", "canonico_esperado": "canonico.esperado.json",
            "canonico_obtido": "canonico.obtido.json"}
    manifesto = tmp_path / "manifesto.json"
    manifesto.write_text(json.dumps({"schema_version": "1.0", "casos": [caso]}))
    return tmp_path, caso, ["--manifesto", str(manifesto), "--raiz", str(tmp_path)]


def test_sem_amostras_nao_existe_homologacao_aprovada(caso_local, capsys):
    _, _, args = caso_local
    assert main(args + ["--etapa", "contrato-canonico"]) == 2
    assert json.loads(capsys.readouterr().out)["erro"] == "HOMOLOGACAO_ARQUIVO_INDISPONIVEL"


def test_harness_reconhece_e_compara_sem_aprovar_configuracao(caso_local, dados_reconhecimento,
    assinaturas_reconhecimento, textos_sinteticos, capsys):
    raiz, caso, args = caso_local
    repo = RepositorioJSON(raiz / "dados")
    repo.salvar(Catalogo.model_validate(dados_reconhecimento), revisao_esperada=0)
    arquivo_assinaturas = raiz / "assinaturas.json"
    arquivo_assinaturas.write_text(json.dumps(assinaturas_reconhecimento))
    (raiz / caso["arquivo"]).write_bytes(pdf_sintetico(textos_sinteticos["habita_tree"]))
    gabarito = {"tipo": "pdf_texto", "estado": "conhecido_validado", "formato_id": "fmt_habita_sintetico_v1",
                "administradora_id": "adm_habita_sintetica", "condominio_id": "cond_tree_sintetico", "bloqueios": []}
    esperado = raiz / caso["reconhecimento_esperado"]
    esperado.write_text(json.dumps(gabarito))
    args += ["--etapa", "reconhecimento", "--dados", str(repo.raiz), "--assinaturas", str(arquivo_assinaturas)]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["casos"] == 1
    gabarito["condominio_id"] = "cond_errado"
    esperado.write_text(json.dumps(gabarito))
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["erro"] == "GABARITO_DIVERGENTE"
    assert repo.carregar().revisao == 1


def test_comparador_preparado_para_boleto_continuado_sem_implementar_extrator(caso_local, unidade, boleto, origem, capsys):
    raiz, caso, args = caso_local
    dados = boleto.model_dump(mode="json")
    continuacao = origem.model_dump(mode="json") | {"pagina": 2, "continuacao_de": origem.identificador, "identificador": "linha_p2"}
    dados["origens"].append(continuacao)
    lote = LoteCanonico.model_validate({"unidades": [unidade.model_dump(mode="json")], "boletos": [dados]})
    for chave in ("canonico_esperado", "canonico_obtido"):
        (raiz / caso[chave]).write_text(lote.model_dump_json())
    assert main(args + ["--etapa", "contrato-canonico"]) == 0
    resultado = capsys.readouterr().out
    assert json.loads(resultado)["status"] == "comparacoes_ok"
    assert "100.00" not in resultado


@pytest.mark.parametrize("falha,status", [("campo", 1), ("duplicidade", 2), ("float", 2), ("soma", 2)])
def test_gabarito_detecta_erros_de_campos_continuidade_e_valores(caso_local, unidade, boleto, falha, status, capsys):
    raiz, caso, args = caso_local
    lote = LoteCanonico(unidades=(unidade,), boletos=(boleto,))
    (raiz / caso["canonico_esperado"]).write_text(lote.model_dump_json())
    obtido = lote.model_dump(mode="json")
    if falha == "campo": obtido["boletos"][0]["competencia"] = "2026-08"
    elif falha == "duplicidade":
        repetido = deepcopy(obtido["boletos"][0])
        repetido["id"] = "outra_pagina_mesmo_boleto"
        obtido["boletos"].append(repetido)
    elif falha == "float": obtido["boletos"][0]["composicao"]["total_original"] = 100.00
    elif falha == "soma": obtido["boletos"][0]["composicao"]["total_original"] = "999.00"
    (raiz / caso["canonico_obtido"]).write_text(json.dumps(obtido))
    assert main(args + ["--etapa", "contrato-canonico"]) == status
    saida = capsys.readouterr().out
    assert "100.00" not in saida
    assert "SYN" not in saida


def test_manifesto_nao_acessa_arquivos_fora_da_raiz(caso_local, capsys):
    raiz, caso, args = caso_local
    caso["canonico_esperado"] = "../dados_fora.json"
    (raiz / "manifesto.json").write_text(json.dumps({"schema_version": "1.0", "casos": [caso]}))
    assert main(args + ["--etapa", "contrato-canonico"]) == 2
    assert json.loads(capsys.readouterr().out)["erro"] == "HOMOLOGACAO_CAMINHO_INVALIDO"
