"""Schemas aditivos do ensaio sintético integrado; nenhum schema histórico muda."""
import argparse
import json
from pathlib import Path

from conversor.domain.integrated_processing import (
    DocumentoReguaSintetica, ExecucaoIntegradaSintetica, PedidoProcessamentoIntegrado,
    ReciboProcessamentoSintetico, ReproducaoIntegradaSintetica,
)

MODELOS = {'regua': DocumentoReguaSintetica, 'pedido': PedidoProcessamentoIntegrado,
           'execucao': ExecucaoIntegradaSintetica, 'recibo': ReciboProcessamentoSintetico,
           'reproducao': ReproducaoIntegradaSintetica}


def documentos():
    for nome, modelo in MODELOS.items():
        schema = modelo.model_json_schema(mode='validation')
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = 'urn:conversor:ensaio-integrado-sintetico:1.0:' + nome
        yield nome + '.schema.json', json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida', type=Path, default=Path('schemas/ensaio-integrado-sintetico/1.0'))
    p.add_argument('--check', action='store_true')
    args = p.parse_args(argv)
    if not args.check:
        args.saida.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in documentos():
        path = args.saida / nome
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != conteudo:
                print('SCHEMA_ENSAIO_INTEGRADO_DESATUALIZADO')
                return 1
        else:
            path.write_text(conteudo, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
