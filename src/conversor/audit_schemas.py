"""Schemas aditivos de reconciliação 1.0 e pacotes 1.1; preserva os schemas antigos."""
import argparse
import json
from pathlib import Path

from conversor.domain.audit_identity import (CandidatoReconciliado, PacoteReconciliado,
    ReconciliacaoOcorrencias, ReciboReconciliacao, VinculoOcorrencia, PreparacaoTecnica, ReciboPreparacaoTecnica)

MODELOS = {
    'auditoria/1.0/reconciliacao': ReconciliacaoOcorrencias,
    'auditoria/1.0/recibo': ReciboReconciliacao,
    'auditoria/1.0/vinculo': VinculoOcorrencia,
    'auditoria/1.0/preparacao_tecnica': PreparacaoTecnica,
    'auditoria/1.0/recibo_preparacao_tecnica': ReciboPreparacaoTecnica,
    'simulacao-privada/1.1/candidato': CandidatoReconciliado,
    'simulacao-privada/1.1/pacote': PacoteReconciliado,
}


def documentos():
    for nome, modelo in MODELOS.items():
        schema = modelo.model_json_schema(mode='validation')
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = 'urn:conversor:' + nome.replace('/', ':')
        yield nome + '.schema.json', json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=Path('schemas'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    for nome, conteudo in documentos():
        path = args.saida / nome
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != conteudo:
                print('SCHEMA_DE_AUDITORIA_DESATUALIZADO')
                return 1
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(conteudo, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
