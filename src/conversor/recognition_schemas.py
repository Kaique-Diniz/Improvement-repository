"""Schemas do reconhecimento separados do contrato congelado da Fase 1."""
import argparse
import json
from pathlib import Path

from conversor.domain.recognition import CatalogoAssinaturas, ResultadoReconhecimento


def documentos():
    for nome, modelo in (("assinaturas", CatalogoAssinaturas), ("resultado", ResultadoReconhecimento)):
        schema = modelo.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:conversor:reconhecimento:1.0:{nome}"
        yield f"{nome}.schema.json", json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path("schemas/reconhecimento/1.0"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        args.saida.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in documentos():
        arquivo = args.saida / nome
        if args.check:
            if not arquivo.exists() or arquivo.read_text(encoding="utf-8") != conteudo:
                print("SCHEMA_RECONHECIMENTO_DESATUALIZADO")
                return 1
        else:
            arquivo.write_text(conteudo, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
