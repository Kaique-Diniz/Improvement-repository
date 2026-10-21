"""Schemas estruturais da Fase 4.1; aprovação exige autoridade, não só schema."""
import argparse
import json
from pathlib import Path

from conversor.adapters.billing_authority import RegistroAutoridade
from conversor.adapters.billing_json import ManifestoPlanos
from conversor.domain.billing_rules import AcervoPlanos, ComandoPlano, EstadoPlanos, EventoPlano, PlanoCobranca

MODELOS = {'plano': PlanoCobranca, 'comando': ComandoPlano, 'evento': EventoPlano,
           'acervo': AcervoPlanos, 'estado': EstadoPlanos, 'manifesto': ManifestoPlanos,
           'autoridade': RegistroAutoridade}


def documentos():
    for nome, modelo in MODELOS.items():
        schema = modelo.model_json_schema(mode='validation')
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = 'urn:conversor:regras:1.0:' + nome
        yield nome + '.schema.json', json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=Path('schemas/regras/1.0'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if not args.check:
        args.saida.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in documentos():
        path = args.saida / nome
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != conteudo:
                print('SCHEMA_DE_REGRAS_DESATUALIZADO')
                return 1
        else:
            path.write_text(conteudo, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
