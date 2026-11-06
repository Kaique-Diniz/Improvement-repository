"""Identidade textual e apresentação documental Vero Encanto."""
import re


def torre_unidade(codigo):
    if not isinstance(codigo, str) or not re.fullmatch(r'[AB]0[0-9]{4}', codigo):
        raise ValueError('VERO_UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
    return codigo[0], codigo[1:]


def complemento_unidade(bloco, codigo):
    torre, numero = torre_unidade(codigo)
    if bloco != torre:
        raise ValueError('VERO_TORRE_DIVERGENTE')
    return f'BL{torre}-UNI{numero[1:]}'
