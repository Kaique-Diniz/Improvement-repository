"""Comparar reconhecimento ou JSON canônico contra gabaritos revisados, sem expor dados."""
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from conversor.adapters.document_probe import SondadorLocal
from conversor.adapters.json_repository import RepositorioJSON, ler_json_bytes
from conversor.adapters.signature_repository import AssinaturasJSON
from conversor.application.ports import ErroAplicacao
from conversor.application.recognition import ReconhecerDocumento
from conversor.domain.base import Data, Id, Modelo
from conversor.domain.canonical import LoteCanonico


class Caso(Modelo):
    id: Id
    arquivo: str
    data_ref: Data
    reconhecimento_esperado: str
    canonico_esperado: str
    canonico_obtido: str


class ManifestoHomologacao(Modelo):
    schema_version: Literal["1.0"]
    casos: tuple[Caso, ...] = Field(min_length=1)


class GabaritoReconhecimento(Modelo):
    tipo: str
    estado: Literal["conhecido_validado", "desconhecido", "ambiguo"]
    formato_id: Id | None
    administradora_id: Id | None
    condominio_id: Id | None
    bloqueios: tuple[str, ...]


def _caminho(raiz: Path, relativo: str):
    caminho = (raiz / relativo).resolve()
    if not caminho.is_relative_to(raiz.resolve()):
        raise ErroAplicacao("HOMOLOGACAO_CAMINHO_INVALIDO")
    return caminho


def _json(arquivo: Path):
    with arquivo.open("rb") as fonte:
        conteudo = fonte.read(20 * 1024 * 1024 + 1)
    if len(conteudo) > 20 * 1024 * 1024:
        raise ErroAplicacao("HOMOLOGACAO_LIMITE_EXCEDIDO")
    return ler_json_bytes(conteudo)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--raiz", type=Path, required=True)
    parser.add_argument("--etapa", choices=("reconhecimento", "contrato-canonico"), required=True)
    parser.add_argument("--dados", type=Path)
    parser.add_argument("--assinaturas", type=Path)
    args = parser.parse_args(argv)
    if args.etapa == "reconhecimento" and (args.dados is None or args.assinaturas is None):
        parser.error("reconhecimento exige --dados e --assinaturas")
    try:
        manifesto = ManifestoHomologacao.model_validate(_json(args.manifesto))
        if len({c.id for c in manifesto.casos}) != len(manifesto.casos):
            raise ErroAplicacao("HOMOLOGACAO_CASO_DUPLICADO")
        for caso in manifesto.casos:
            if args.etapa == "reconhecimento":
                fonte = SondadorLocal().sondar_arquivo(_caminho(args.raiz, caso.arquivo), arquivo_id=caso.id)
                resultado = ReconhecerDocumento(RepositorioJSON(args.dados), AssinaturasJSON(args.assinaturas)).executar(fonte, data_ref=caso.data_ref)
                esperado = GabaritoReconhecimento.model_validate(_json(_caminho(args.raiz, caso.reconhecimento_esperado)))
                selecao = resultado.selecao
                obtido = GabaritoReconhecimento(tipo=resultado.tipo, estado=resultado.estado,
                    formato_id=selecao.versoes.formato_id if selecao else None,
                    administradora_id=selecao.versoes.administradora_id if selecao else None,
                    condominio_id=selecao.condominio_id if selecao else None,
                    bloqueios=tuple(resultado.bloqueios))
            else:
                # Só compara resultados de um leitor; não existe extração PDF financeira aqui.
                esperado = LoteCanonico.model_validate(_json(_caminho(args.raiz, caso.canonico_esperado)))
                obtido = LoteCanonico.model_validate(_json(_caminho(args.raiz, caso.canonico_obtido)))
            if obtido != esperado:
                print(json.dumps({"erro": "GABARITO_DIVERGENTE", "caso_id": caso.id}))
                return 1
        print(json.dumps({"status": "comparacoes_ok", "casos": len(manifesto.casos), "etapa": args.etapa}))
        return 0
    except ErroAplicacao as erro:
        print(json.dumps({"erro": str(erro)}))
    except ValidationError:
        print('{"erro":"HOMOLOGACAO_CONTRATO_INVALIDO"}')
    except OSError:
        print('{"erro":"HOMOLOGACAO_ARQUIVO_INDISPONIVEL"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
