import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from conversor.readers.text_support import ErroLeitura
from .run import executar_pacote


def main(argv=None):
    parser = argparse.ArgumentParser(description="Comparar pacote sintético local; sem homologação de produção")
    parser.add_argument("--pacote", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config_exemplos/laboratorio_pacote.json"))
    args = parser.parse_args(argv)
    try:
        relatorio = executar_pacote(args.pacote, args.saida, args.config)
        print(json.dumps({"financeiro_confere": relatorio["todos_financeiros_conferem"],
            "divergencias_excel": relatorio["divergencias_excel"], "fixtures_inalteradas": relatorio["fixtures_inalteradas"],
            "homologado_producao": False}))
        if not relatorio["fixtures_inalteradas"] or not relatorio["todos_financeiros_conferem"]: return 2
        return 1 if relatorio["divergencias_excel"] else 0
    except ErroLeitura as erro:
        print(json.dumps({"erro": erro.codigo, "pagina": erro.pagina, "linha": erro.linha}))
    except (ValidationError, ValueError, KeyError, OSError):
        print('{"erro":"PACOTE_OU_CONFIGURACAO_INVALIDA"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
