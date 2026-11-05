import argparse
from pathlib import Path
import sys


def main_legado(argv):
    parser = argparse.ArgumentParser(description='MVP local privado do Conversor')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--private-dir', type=Path,
                        default=Path('/workspace/validacao-privada-fase3/mvp'))
    parser.add_argument('--catalogo', type=Path)
    parser.add_argument('--perfis-saida', type=Path, help='JSON privado de perfis de saída diagnóstica, fora do Git')
    args = parser.parse_args(argv)
    from .app import criar_app
    import uvicorn
    app = criar_app(args.private_dir, catalogo=args.catalogo, perfis_saida=args.perfis_saida)
    print(f'Interface: http://{args.host}:{args.port}')
    print(f'Chave de acesso somente no arquivo privado: {args.private_dir / "acesso-local.txt"}')
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level='warning')


def main():
    argv = sys.argv[1:]
    if '--legado-persistente' in argv:
        return main_legado([arg for arg in argv if arg != '--legado-persistente'])
    from .ephemeral import main as main_efemero
    return main_efemero()


if __name__ == '__main__':
    main()
