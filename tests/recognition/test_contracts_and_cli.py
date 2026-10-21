from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from conversor.adapters.json_repository import RepositorioJSON
from conversor.adapters.signature_repository import AssinaturasJSON
from conversor.application.ports import ErroAplicacao
from conversor.cli import main
from conversor.domain.catalog import Catalogo
from conversor.domain.recognition import CatalogoAssinaturas
from conversor.recognition_schemas import documentos
from examples.fase2.gerar_demo import catalogo_sintetico, pdf_sintetico


@pytest.mark.parametrize("mudanca", ["aprovacao", "duplicata", "logo", "limiar", "vazio", "equivalentes"])
def test_assinaturas_inconsistentes_nao_sao_carregadas(assinaturas_reconhecimento, mudanca):
    dados = assinaturas_reconhecimento
    if mudanca == "aprovacao": dados["aprovacao"] = None
    elif mudanca == "duplicata": dados["layouts"].append(deepcopy(dados["layouts"][0]))
    elif mudanca == "logo": dados["layouts"][0]["marcadores"] = dados["layouts"][0]["marcadores"][:1]
    elif mudanca == "limiar": dados["layouts"][0]["minimo_pontos"] = 999
    elif mudanca == "vazio": dados["layouts"][0]["marcadores"][0]["texto"] = "   "
    elif mudanca == "equivalentes":
        dados["layouts"][0]["marcadores"][1]["texto"] = "INADIMPLENCIA   ATUALIZADA"
    with pytest.raises(ValidationError):
        CatalogoAssinaturas.model_validate(dados)


@pytest.mark.parametrize("conteudo,codigo", [
    ('{"schema_version":"2.0"}', "ASSINATURAS_SCHEMA_NAO_SUPORTADO"),
    ('{"schema_version":"1.0","token":"SENTINELA_NAO_LOGAR"}', "ASSINATURAS_INVALIDAS"),
    ('{"schema_version":"1.0","schema_version":"1.0"}', "JSON_COM_CHAVE_DUPLICADA"),
])
def test_repositorio_assinaturas_erros_seguros(tmp_path, conteudo, codigo):
    arquivo = tmp_path / "assinaturas.json"
    arquivo.write_text(conteudo)
    with pytest.raises(ErroAplicacao, match=codigo) as erro:
        AssinaturasJSON(arquivo).carregar()
    assert "SENTINELA_NAO_LOGAR" not in str(erro.value)


def test_cli_reconhece_sem_confirmacao_e_bloqueia_conteudo_desconhecido(tmp_path, dados_reconhecimento, assinaturas_reconhecimento,
    textos_sinteticos, capsys):
    raiz = tmp_path / "dados"
    RepositorioJSON(raiz).salvar(Catalogo.model_validate(dados_reconhecimento), revisao_esperada=0)
    assinaturas = tmp_path / "assinaturas.json"
    assinaturas.write_text(json.dumps(assinaturas_reconhecimento))
    fonte = tmp_path / "nome_enganoso_fl_plaza.pdf"
    fonte.write_bytes(pdf_sintetico(textos_sinteticos["habita_tree"]))
    args = ["--dados", str(raiz), "reconhecer", str(fonte), "--arquivo-id", "fonte_sintetica",
            "--assinaturas", str(assinaturas), "--data-ref", "2026-10-21"]
    assert main(args) == 0
    resultado = json.loads(capsys.readouterr().out)
    assert resultado["selecao"]["condominio_id"] == "cond_tree_sintetico"
    assert resultado["pronto_para_proxima_etapa"]
    fonte.write_bytes(pdf_sintetico(["SENTINELA_PRIVADA_NAO_LOGAR"]))
    assert main(args) == 3
    captura = capsys.readouterr()
    assert "SENTINELA_PRIVADA_NAO_LOGAR" not in captura.out + captura.err
    assert json.loads(captura.out)["selecao"] is None
    assert RepositorioJSON(raiz).carregar().revisao == 1  # sondagem não grava ou aprova


def test_cli_rejeita_data_invalida_sem_mostrar_caminho(tmp_path, capsys):
    args = ["--dados", str(tmp_path / "dados"), "reconhecer", str(tmp_path / "fonte_privada.pdf"), "--arquivo-id", "fonte",
            "--assinaturas", str(tmp_path / "assinaturas.json"), "--data-ref", "21/10/2026"]
    assert main(args) == 2
    assert json.loads(capsys.readouterr().err) == {"erro": "DATA_REF_INVALIDA"}


def test_exemplos_comprometidos_permanecem_rascunhos():
    raiz = Path(__file__).resolve().parents[2]
    exemplo = CatalogoAssinaturas.model_validate_json((raiz / "examples/fase2/assinaturas.sinteticas.json").read_text())
    assert exemplo.status == "rascunho"
    assert exemplo.aprovacao is None
    assert all(f.status == "rascunho" for f in catalogo_sintetico().formatos)


def test_schemas_reconhecimento_versionados():
    raiz = Path(__file__).resolve().parents[2]
    for nome, conteudo in documentos():
        assert (raiz / "schemas/reconhecimento/1.0" / nome).read_text(encoding="utf-8") == conteudo
