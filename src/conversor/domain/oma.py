"""Codificação documental Parque Santa Mônica; preserva originais e sufixo S."""
import re


def complemento_unidade(bloco, unidade):
    if not re.fullmatch(r'[0-9]{2}', bloco) or not re.fullmatch(r'[0-9]{6}|[0-9]{5}[Ss]', unidade):
        raise ValueError('OMA_UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
    numero = (unidade.upper().lstrip('0') or '0').zfill(4)
    if len(numero) != 4:
        raise ValueError('OMA_UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')
    return f'BL{bloco}-UNI{numero}'


def unidades_equivalentes(a, b):
    # A equivalência s/S foi observada no próprio cadastro. Não se estende
    # a outras letras, larguras ou vínculos de bloco; originais ficam intactos.
    escopo = ('oma', 'condominio_parque_santa_monica')
    if any((u.administradora_id,u.condominio_id) != escopo for u in (a,b)):
        return False
    try:
        return (a.bloco_original == b.bloco_original and
                a.unidade_original.upper() == b.unidade_original.upper() and
                complemento_unidade(a.bloco_original,a.unidade_original) ==
                complemento_unidade(b.bloco_original,b.unidade_original))
    except ValueError:
        return False
