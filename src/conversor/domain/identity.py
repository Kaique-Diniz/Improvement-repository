"""Normalização estrutural reversível pelas chaves originais; não resolve titularidade."""


def chave_unidade(bloco: str, numero: str) -> str:
    def norm(valor):
        return str(int(valor)) if valor.isascii() and valor.isdigit() else valor.upper()
    return norm(bloco) + '/' + norm(numero)


def nomes_do_registro(nome: str) -> frozenset[str]:
    """Só nomes completos separados explicitamente; sem correspondência parcial."""
    return frozenset(' '.join(n.split()).casefold() for n in nome.split('/') if n.strip())


def nomes_compativeis(a: str, b: str) -> bool:
    a, b = nomes_do_registro(a), nomes_do_registro(b)
    return bool(a and b) and (a <= b or b <= a)
