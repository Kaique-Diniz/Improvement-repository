"""Gramática e apresentação documentais Forest Hill; sem regras de cobrança."""
import re
import unicodedata


def complemento_unidade(texto: str) -> str:
    avenida = re.fullmatch(r'AV\.P([0-9]{2}) ([0-9]{3})', texto)
    if avenida:
        return f'AVP{avenida[1]}-UNI{avenida[2]}'
    rua = re.fullmatch(r'RUA ([0-9]{2}) ([0-9]{1,3})', texto)
    if rua:
        return f'RUA{rua[1]}-UNI{rua[2].zfill(4)}'
    raise ValueError('FOREST_HILL_UNIDADE_NAO_RECONHECIDA')


def rotulo_descricao(descricao, vencimento, parcela):
    """Mês do vencimento é apresentação, nunca competência ou novo cálculo."""
    texto = ''.join(c for c in unicodedata.normalize('NFKD', descricao.casefold())
                    if not unicodedata.combining(c))
    # Referências de acordo com sufixo de quatro dígitos já compõem o rótulo
    # documental. Não tratá-las como uma parcela nem acrescentar outro mês.
    acordo_sem_referencia = re.search(r'\bacordo\b', texto) and not re.search(r'/[0-9]{4}\b', texto)
    com_mes = bool(acordo_sem_referencia or re.fullmatch(
        r'taxa de rocagem|multa de infracao|multa por infracao [0-9]+', texto))
    base = descricao + (f' {vencimento:%m/%Y}' if com_mes else '')
    return base + (f' - {parcela}' if parcela is not None else ''), com_mes
