import json
from pathlib import Path
import subprocess
import sys

from conversor.cli import main
from conversor.schemas import documentos

RAIZ = Path(__file__).resolve().parents[1]


def test_cli_fluxo_local_e_repeticao_segura(tmp_path, capsys):
    dados = str(tmp_path / "dados")
    base = ["--dados", dados]
    assert main(base + ["init"]) == 0
    assert json.loads(capsys.readouterr().out)["revisao"] == 1
    assert main(base + ["init"]) == 2
    assert json.loads(capsys.readouterr().err)["erro"] == "CONFLITO_DE_REVISAO"
    assert main(base + ["importar", str(RAIZ / "examples/fase1/catalogo.sintetico.json"), "--revisao", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["revisao"] == 2
    assert main(base + ["validar"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert main(base + ["listar", "condominios"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ids": ["cond_sintetico"]}


def test_cli_nao_expoe_entrada_invalida_ou_token_sentinela(tmp_path, capsys):
    segredo_sintetico = "SENTINELA_NUNCA_LOGAR"
    arquivo = tmp_path / "entrada.json"
    arquivo.write_text(json.dumps({"schema_version": "1.0", "senha": segredo_sintetico}))
    assert main(["--dados", str(tmp_path / "dados"), "importar", str(arquivo), "--revisao", "0"]) == 2
    captura = capsys.readouterr()
    assert captura.out == ""
    assert json.loads(captura.err) == {"erro": "CONTRATO_INVALIDO"}
    assert segredo_sintetico not in captura.err
    assert not (tmp_path / "dados/current.json").exists()


def test_cli_em_subprocesso_preserva_exit_status(tmp_path):
    resultado = subprocess.run([sys.executable, "-m", "conversor.cli", "--dados", str(tmp_path / "dados"), "validar"],
                               capture_output=True, text=True, check=False)
    assert resultado.returncode == 2
    assert json.loads(resultado.stderr)["erro"] == "REPOSITORIO_NAO_INICIALIZADO"


def test_schemas_versionados_correspondem_aos_contratos():
    for nome, conteudo in documentos():
        assert (RAIZ / "schemas/1.0" / nome).read_text() == conteudo
        schema = json.loads(conteudo)
        assert schema["additionalProperties"] is False
