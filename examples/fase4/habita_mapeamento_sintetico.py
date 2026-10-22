"""PDFs criados do zero para verificar campos. Não cria planos ou decisões de cobrança."""
from decimal import Decimal

from examples.fase3.layouts_sinteticos import linhas, pdf_posicionado

CABECALHO = [
    'Inadimplência Atualizada',
    'Condominio: 9999 - CONDOMINIO SINTETICO',
    'Bloco: SINT • Unidade: 000001 TITULAR SINTETICO CPF: (vazio)',
    'Boleto Vencimento Emissão Conta Histórico Valor Multa Atualização Monetária Juros Total',
]


def moeda(valor):
    return format(valor, '.2f').replace('.', ',')


def valores_linha(valores):
    return ' '.join(moeda(v) for v in (*valores, sum(valores, Decimal('0.00'))))


def paginas_mapeamento(cotas, *, quebrar=None, subtotal_divergente=False):
    """quebrar=(índice da cota, índice do componente), repetindo cabeçalho realista."""
    paginas = [list(CABECALHO)]
    total_unidade = [Decimal('0.00')] * 4
    for ci, cota in enumerate(cotas):
        total_boleto = [Decimal('0.00')] * 4
        for ii, item in enumerate(cota['itens']):
            nova_pagina = quebrar == (ci, ii)
            if nova_pagina:
                paginas.append(list(CABECALHO))
            apontamento = (' ' + cota['apontamento']) if cota['apontamento'] else ''
            prefixo = (f"{cota['numero']}{apontamento} {cota['vencimento']} 010926 94 "
                       if ii == 0 or nova_pagina else '1372 ')
            valores = tuple(map(Decimal, item))
            paginas[-1].append(prefixo + 'COMPONENTE SINTETICO ' + valores_linha(valores))
            for i, v in enumerate(valores):
                total_boleto[i] += v
                total_unidade[i] += v
        # A fonte real fecha explicitamente os multicomponentes, não cada cota simples.
        if len(cota['itens']) > 1:
            paginas[-1].append('Total do boleto: ' + valores_linha(total_boleto))
    paginas[-1].append('Total da Unidade: ' + valores_linha(total_unidade))
    if subtotal_divergente:
        subtotal = list(total_unidade)
        subtotal[0] += Decimal('1.00')
        paginas[-1].append('Total do Bloco SINT: ' + valores_linha(subtotal))
    paginas[-1].append('Quantidade de unidades inadimplentes no condominio: 1 Total Geral: '
                       + valores_linha(total_unidade))
    paginas[-1].append('Legenda: A / AJ / J - texto explicativo sintetico, sem lancamento')
    return [linhas(pagina) for pagina in paginas]


def pdf_mapeamento(cotas, **opcoes):
    return pdf_posicionado(paginas_mapeamento(cotas, **opcoes))
