"""Gera quatro cadastros inteiramente sintéticos; somente homologação do importador."""
import argparse
from datetime import date
from pathlib import Path

from conversor.domain.canonical import Documento, Origem, Pessoa
from conversor.domain.template import Template
from conversor.export.contract import LinhaExportacao
from conversor.export.xlsx import escrever_xlsx


def gerar(destino: Path):
    origem = Origem(arquivo_id='fixture_documental_sintetica', sha256='0'*64,
        leitor_versao='ensaio-documental-1', pagina=1, identificador='fixture')
    documentos = (Documento(tipo='cpf',valor='00000000191'),
                  Documento(tipo='cnpj',valor='00000000000191'), None,
                  Documento(tipo='cnpj',valor='00000000000000'))
    linhas=[]
    for indice,doc in enumerate(documentos,1):
        pessoa=Pessoa(id=f'pessoa_sintetica_{indice}',unidade_id=f'unidade_sintetica_{indice}',
            nome=f'TITULAR SINTETICO {indice} - SOMENTE HOMOLOGACAO',documento=doc,
            relacao_unidade='fixture_sem_identidade_real',origem=origem)
        linhas.append(LinhaExportacao(processamento_id='ensaio_documental',registro_id=pessoa.unidade_id,
            tipo='cadastral',nm_cedente_cedente='CREDOR SINTETICO - NAO PRODUCAO',
            cedente=f'SINTETICO-{indice:04d}',pessoa=pessoa))
    return escrever_xlsx(linhas,Template(id='tpl_sintetico',nome='Universal',versao='1'),destino,
                         data_ref=date(2026,10,21))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',required=True,type=Path)
    args=parser.parse_args()
    gerar(args.saida)
    print('ENSAIO_SINTETICO_GERADO_NAO_HOMOLOGADO')
