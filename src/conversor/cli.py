import argparse
import json
from pathlib import Path
import sys

from pydantic import ValidationError

from conversor.adapters.json_repository import RepositorioJSON, ler_json_bytes
from conversor.application.configuration import COLECOES, Configuracao
from conversor.application.ports import ErroAplicacao
from conversor.domain.catalog import Catalogo


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Conversor de Inadimplência — fundação, sem conversão nesta fase")
    parser.add_argument("--dados", type=Path, required=True, help="Diretório local protegido; nunca comitar")
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("init", help="Inicializar catálogo vazio, sem sobrescrever existente")
    comandos.add_parser("validar", help="Validar schema, hashes e relações do snapshot ativo")
    listar = comandos.add_parser("listar", help="Listar somente IDs; não exibe dados pessoais")
    listar.add_argument("colecao", choices=COLECOES)
    importar = comandos.add_parser("importar", help="Importar catálogo completo e consistente")
    importar.add_argument("arquivo", type=Path)
    gravar = comandos.add_parser("gravar", help="Criar/atualizar registro de configuração")
    gravar.add_argument("colecao", choices=COLECOES)
    gravar.add_argument("arquivo", type=Path)
    excluir = comandos.add_parser("excluir", help="Excluir registro não referenciado/não imutável")
    excluir.add_argument("colecao", choices=COLECOES)
    excluir.add_argument("id")
    for comando in (importar, gravar, excluir):
        comando.add_argument("--revisao", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        repo = RepositorioJSON(args.dados)
        servico = Configuracao(repo)
        if args.comando == "init":
            estado = servico.inicializar()
        elif args.comando == "validar":
            estado = repo.carregar()
        elif args.comando == "listar":
            print(json.dumps({"ids": servico.listar_ids(args.colecao)}))
            return 0
        elif args.comando == "importar":
            bruto = ler_json_bytes(args.arquivo.read_bytes())
            if not isinstance(bruto, dict) or bruto.get("schema_version") != "1.0":
                raise ErroAplicacao("SCHEMA_NAO_SUPORTADO")
            estado = servico.importar(Catalogo.model_validate(bruto), revisao_esperada=args.revisao)
        elif args.comando == "gravar":
            registro = ler_json_bytes(args.arquivo.read_bytes())
            if not isinstance(registro, dict):
                raise ErroAplicacao("REGISTRO_INVALIDO")
            estado = servico.gravar(args.colecao, registro, revisao_esperada=args.revisao)
        else:
            estado = servico.excluir(args.colecao, args.id, revisao_esperada=args.revisao)
        print(json.dumps({"status": "ok", "revisao": estado.revisao, "schema_version": "1.0"}))
        return 0
    except ErroAplicacao as erro:
        print(json.dumps({"erro": str(erro)}), file=sys.stderr)
    except (ValidationError, TypeError):
        print('{"erro":"CONTRATO_INVALIDO"}', file=sys.stderr)
    except OSError:
        print('{"erro":"FALHA_ACESSO_ARQUIVO"}', file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
