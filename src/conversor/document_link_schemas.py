"""Schemas aditivos; escopo 1.0 e demais contratos históricos são preservados."""
import argparse
import json
from pathlib import Path

from conversor.domain.document_links import AcervoVinculos, VinculoDocumental, SnapshotVinculos
from conversor.domain.document_scope import EscopoDestinoPersistente

MODELOS={'vinculos/1.0/acervo':AcervoVinculos,'vinculos/1.0/vinculo':VinculoDocumental,
    'vinculos/1.0/snapshot':SnapshotVinculos,'escopo-destino/1.1/escopo':EscopoDestinoPersistente}


def documentos():
    for nome,modelo in MODELOS.items():
        schema=modelo.model_json_schema(mode='validation');schema['$schema']='https://json-schema.org/draft/2020-12/schema'
        schema['$id']='urn:conversor:'+nome.replace('/',':')
        yield nome+'.schema.json',json.dumps(schema,ensure_ascii=False,sort_keys=True,indent=2)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for nome,conteudo in documentos():
        p=Path('schemas')/nome
        if args.check:
            if not p.exists()or p.read_text(encoding='utf-8')!=conteudo:print('SCHEMA_VINCULOS_DESATUALIZADO');return 1
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(conteudo,encoding='utf-8')
    return 0


if __name__=='__main__':raise SystemExit(main())
