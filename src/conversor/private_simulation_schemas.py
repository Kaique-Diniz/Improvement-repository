"""Schemas do incremento 4.3A; independentes dos contratos 4.1/4.2."""
import argparse
import json
from pathlib import Path

from conversor.domain.private_simulation import CandidatoPacote, PacotePrivado, ExecucaoPrivada, ReciboPrivado, ReproducaoHistorica
from conversor.domain.rule_preparation import MatrizPreliminar
from conversor.domain.simulation_comparison import ComparacaoPrivada, MapeamentoReferencia

MODELOS = {'candidato': CandidatoPacote, 'pacote': PacotePrivado, 'execucao': ExecucaoPrivada, 'recibo': ReciboPrivado,
           'reproducao': ReproducaoHistorica, 'comparacao': ComparacaoPrivada,
           'mapeamento': MapeamentoReferencia, 'matriz_preliminar': MatrizPreliminar}


def documentos():
    for nome, modelo in MODELOS.items():
        schema = modelo.model_json_schema(mode='validation')
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = 'urn:conversor:simulacao-privada:1.0:' + nome
        yield nome + '.schema.json', json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=Path('schemas/simulacao-privada/1.0'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if not args.check:
        args.saida.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in documentos():
        path = args.saida / nome
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != conteudo:
                print('SCHEMA_PRIVADO_DESATUALIZADO')
                return 1
        else:
            path.write_text(conteudo, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
