"""Nenhum arquivo ou registro privado é necessário para executar estes testes."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook

REF = date(2026, 10, 7)
CPF = '11144477735'
OUTRO_CPF = '52998224725'
CNPJ = '11222333000181'
FINANCEIRO = ('Unidade', 'Responsável', 'Descrição', 'Vencimento', 'Dias',
    'Valor', 'Juros', 'Multa', 'Correção', 'Honorários', 'Atual')
CADASTRO = ('Unidade', 'Responsável', 'Email', 'CPF/CNPJ', 'Fração', 'Fone',
    'Celular', 'Habilitado', 'Alugado', 'Pets', 'Condôminos', 'RG', 'CPF',
    'Profissão', 'Veículos', 'Desde', 'Endereço')


def debito(*, unidade='007', nome='Pessoa Fictícia Alfa', dias=61, valor='100.10',
           descricao='DESPESA FICTÍCIA SEM COMPETÊNCIA', dias_fonte=None, encargos=('0', '0', '0', '0')):
    juros, multa, correcao, honorarios = map(Decimal, encargos)
    original = Decimal(valor)
    return [unidade, nome, descricao, REF-timedelta(days=dias), dias if dias_fonte is None else dias_fonte,
        str(original), str(juros), str(multa), str(correcao), str(honorarios),
        str(original+juros+multa+correcao+honorarios)]


def ficha(*, unidade='007', nome='Pessoa Fictícia Alfa', documento=CPF, outro_documento='',
          email='pessoa.ficticia@example.invalid', fone='(11) 99999-0000'):
    return [unidade, nome, email, documento, '', fone, '', 'Sim', 'Não', '', '', '',
        outro_documento, '', '', '', 'Rua Fictícia, 10, Bairro Fictício, 01001000, Cidade Fictícia, SP']


def planilha(colunas, registros, *, mutar=None):
    book = Workbook(); sheet = book.active; sheet.title = 'Sheet1'
    book.properties.created = datetime(2000, 1, 1)
    book.properties.modified = datetime(2000, 1, 1)
    sheet.append(colunas)
    for row in registros: sheet.append(row)
    sheet.append([])
    sheet.append([f'{len(registros)} item(ns)'])
    sheet.append(['Gerado em 07/10/2026 12:00'])
    if mutar: mutar(book, sheet)
    stream = BytesIO()
    try: book.save(stream); return stream.getvalue()
    finally: book.close()


def financeiro(registros=None, **kwargs):
    return planilha(FINANCEIRO, registros if registros is not None else [debito()], **kwargs)


def cadastro(registros=None, **kwargs):
    return planilha(CADASTRO, registros if registros is not None else [ficha()], **kwargs)
