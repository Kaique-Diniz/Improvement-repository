"""Normalização estrutural reversível pelas chaves originais; não resolve titularidade."""


def chave_unidade(bloco: str, numero: str) -> str:
    def norm(valor):
        return str(int(valor)) if valor.isascii() and valor.isdigit() else valor.upper()
    return norm(bloco) + '/' + norm(numero)
