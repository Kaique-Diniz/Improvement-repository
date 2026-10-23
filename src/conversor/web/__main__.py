import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='MVP local privado do Conversor')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--private-dir', type=Path,
                        default=Path('/workspace/validacao-privada-fase3/mvp'))
    parser.add_argument('--catalogo', type=Path)
    args = parser.parse_args()
    from .app import criar_app
    import uvicorn
    app = criar_app(args.private_dir, catalogo=args.catalogo)
    print(f'Interface: http://{args.host}:{args.port}')
    print(f'Chave de acesso somente no arquivo privado: {args.private_dir / "acesso-local.txt"}')
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
