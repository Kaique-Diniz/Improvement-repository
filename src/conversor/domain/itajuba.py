"""Codificação documental Itajubá; não altera identidades originais."""
import re

TORRES = {f'T-0{i}':f'T0{i}' for i in range(1,6)}


def complemento_unidade(torre, apartamento):
    if torre not in TORRES or not re.fullmatch(r'[ABCD]-[0-9]{2}',apartamento):
        raise ValueError('ITAJUBA_UNIDADE_NAO_DOCUMENTADA')
    return f'QUA{TORRES[torre]}-LT{apartamento[0]}{apartamento[2:].zfill(4)}'
