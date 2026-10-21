"""Geração determinística dos JSON Schemas versionados; contratos Python são a fonte."""
import argparse
import json
from pathlib import Path

from conversor.adapters.json_repository import Manifesto
from conversor.domain.catalog import Catalogo
from conversor.domain.canonical import LoteCanonico, ResultadoCobranca
from conversor.export.contract import LinhaExportacao
from conversor.readers.contracts import ClassificacaoFormato

MODELOS = {"catalogo": Catalogo, "canonico": LoteCanonico, "resultado_cobranca": ResultadoCobranca,
           "linha_exportacao": LinhaExportacao, "classificacao": ClassificacaoFormato, "manifesto": Manifesto}


def documentos():
    for nome, modelo in MODELOS.items():
        schema = modelo.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:conversor:1.0:{nome}"
        yield f"{nome}.schema.json", json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path("schemas/1.0"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        args.saida.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in documentos():
        arquivo = args.saida / nome
        if args.check:
            if not arquivo.exists() or arquivo.read_text(encoding="utf-8") != conteudo:
                print("SCHEMA_DESATUALIZADO")
                return 1
        else:
            arquivo.write_text(conteudo, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
