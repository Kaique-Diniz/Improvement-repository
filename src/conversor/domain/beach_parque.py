"""Identificadores documentais Beach Parque; nenhum código de destino inferido."""
import re

TORRES = {'A':'ILHABE', 'B':'ANG', 'C':'BUZ', '0':'00'}

def complemento_unidade(bloco, unidade):
    if bloco == '0' and unidade == 'DANPRI':
        return 'BL00-UNIDANPRI'
    if bloco not in ('A','B','C') or not re.fullmatch(re.escape(bloco)+r'[0-9]{5}', unidade):
        raise ValueError('BPQ_UNIDADE_NAO_DOCUMENTADA')
    return f'BL{TORRES[bloco]}-UNI{unidade}'


def rotulo_descricao(descricao, vencimento, parcela):
    """Histórico literal; mês/ano apenas nos padrões documentais homologados."""
    # Lista finita comprovada no template homologado; não inferir competência
    # nem estender a todas as naturezas/administradoras. Histórico fica literal.
    padroes = {
        'CONDOMINIO 08/25', 'CONSUMO AGUA', 'INDIVIDUALIZAÇÃO AGUA 09/10',
        'PROJETO SEGURANÇA 11/61', 'CONSUMO GAS', 'CONSUMO ENERGIA',
        'PROJETO SEGURANÇA 13/36', 'Taxa de condominio', 'taxa de condominio',
        'Enxoval', 'Agua', 'PROJETO SEGURANÇA 10/36',
        'LOCAÇÃO DE VAGA DE MOTO', 'PROJETO SEGURANÇA 11/36', 'SERVIÇOS ELÉTRICOS 3/5',
    }
    com_mes = descricao in padroes
    return descricao + (f' {vencimento:%m/%Y}' if com_mes else '') + (f' - {parcela}' if parcela is not None else ''), com_mes
