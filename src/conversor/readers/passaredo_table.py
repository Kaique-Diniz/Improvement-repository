"""Estrutura tabular Passaredo: cabeçalho, itens e fechamento observado.

Não lê nomes de arquivos nem infere identidade de condomínio ou código destino.
"""
from datetime import datetime
from io import BytesIO
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.adapters.xlsx_reader import ler_planilha
from .text_support import ErroLeitura


def tabela(conteudo, *, arquivo_id, obrigatorias, permitidas):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id=arquivo_id)
    if sonda.tipo != 'xlsx' or sonda.bloqueios or not sonda.completo:
        raise ErroLeitura('XLSX_NAO_EXTRAIVEL_COM_SEGURANCA')
    livro = load_workbook(BytesIO(conteudo), data_only=False, keep_links=False)
    try:
        if len(livro.worksheets) != 1 or livro.active.title != 'Sheet1':
            raise ErroLeitura('PASSAREDO_ABA_NAO_RECONHECIDA')
        if any(c.data_type == 'f' for row in livro.active for c in row):
            raise ErroLeitura('PASSAREDO_FORMULA_NAO_SUPORTADA')
    finally:
        livro.close()
    plan = ler_planilha(conteudo, arquivo_id=arquivo_id, aba='Sheet1')
    campos = {c for c, _ in plan.colunas}
    if not set(obrigatorias) <= campos:
        raise ErroLeitura('PASSAREDO_COLUNAS_AUSENTES')
    if not campos <= set(permitidas):
        raise ErroLeitura('PASSAREDO_COLUNAS_NAO_RECONHECIDAS')
    itens, contagem, gerado = [], None, False
    for registro in plan.linhas:
        unidade = str(registro.get('UNIDADE') or '').strip()
        isolado = all(v is None or str(v).strip() == '' for k, v in registro.items()
                      if k not in ('UNIDADE', '__linha__'))
        contador = re.fullmatch(r'(\d+)\s+item\s*\((?:s|ns)\)', unidade, re.I)
        emissao = re.fullmatch(r'Gerado em (\d{2}/\d{2}/\d{4} \d{2}:\d{2})', unidade, re.I)
        if contador and isolado and contagem is None:
            contagem = int(contador[1])
        elif emissao and isolado and contagem is not None and not gerado:
            try:
                datetime.strptime(emissao[1], '%d/%m/%Y %H:%M')
            except ValueError:
                raise ErroLeitura('PASSAREDO_EMISSAO_INVALIDA') from None
            gerado = True
        elif contagem is not None or gerado:
            raise ErroLeitura('PASSAREDO_CONTEUDO_APOS_FECHAMENTO', linha=registro['__linha__'])
        else:
            itens.append(registro)
    if contagem != len(itens) or not gerado:
        raise ErroLeitura('PASSAREDO_FECHAMENTO_AUSENTE_OU_DIVERGENTE')
    plan.linhas = itens
    return plan
