"""Composição FL do laboratório; Saldo é acumulado e jamais vira valor do boleto."""
from decimal import Decimal
import re

from .text_support import AcumuladorLeitura, ContextoLeitura, ErroLeitura, TextoPDF, VALOR_BRL, data_curta, dinheiro_brl

INICIO = re.compile(rf"^(\d{{2}}/\d{{2}}/\d{{2}})\s+(\d{{2}})/(\d{{4}})\s+(\d+)\s+(.+?)\s+({VALOR_BRL})\s+({VALOR_BRL})$")
ITEM = re.compile(rf"^([A-Z][A-Z\s]+?)\s+({VALOR_BRL})\s+({VALOR_BRL})$")
UNIDADE = re.compile(r"^(\w+)\s+TORRE\s+(\w+)\s*-\s*(.+)$")


class LeitorFLSintetico:
    formato_id = "fl_composicao_sintetico_v1"

    def ler(self, conteudo: bytes, *, contexto: ContextoLeitura):
        fonte = TextoPDF(conteudo, contexto)
        # W002A é código do relatório, não identificação do condomínio.
        codigos = {m[1].strip() for p in fonte.paginas for l in p
                   if (m := re.fullmatch(r"W\w+ CONDOMINIO EDIFICIO (.+?) \(AMOSTRA SINTETICA\)", l.texto))}
        if codigos != {contexto.codigo_condominio}:
            raise ErroLeitura("CONDOMINIO_DIVERGENTE")
        acc = AcumuladorLeitura(fonte)
        saldos = {}
        contagem = None
        for pagina, linhas in enumerate(fonte.paginas, 1):
            for linha in linhas:
                texto = linha.texto.strip()
                if match := UNIDADE.fullmatch(texto):
                    unidade, bloco, nome = match.groups()
                    acc.unidade(bloco, unidade, re.sub(r"\s*\(Proprietario\)$", "", nome), linha)
                elif match := INICIO.fullmatch(texto):
                    venc, mes, ano, numero, descricao, valor, saldo = match.groups()
                    acc.iniciar(numero, data_curta(venc, linha), f"{ano}-{mes}", linha)
                    self._item(acc, linha, valor, saldo, saldos)
                elif match := ITEM.fullmatch(texto):
                    self._item(acc, linha, match[2], match[3], saldos)
                elif texto.startswith("--- CONTINUA"):
                    acc.marcar_continuacao(linha)
                elif match := re.fullmatch(r"CONTINUACAO DO BOLETO (\d+) - (\w+) TORRE (\w+)", texto):
                    acc.continuar(match[1], match[3], match[2], linha)
                elif match := re.fullmatch(r"FIM DO RELATORIO: (\d+) UNIDADES E (\d+) BOLETOS", texto):
                    acc.finalizar()
                    contagem = tuple(map(int, match.groups()))
                elif re.search(rf"{VALOR_BRL}$", texto):
                    acc.falhar("LINHA_FINANCEIRA_NAO_RECONHECIDA", linha)
            acc.fim_pagina(pagina)
        lote = acc.resultado()
        if contagem is None or contagem != (len(lote.unidades), len(lote.boletos)):
            raise ErroLeitura("CONTAGEM_DE_RELATORIO_INCONSISTENTE")
        return lote

    @staticmethod
    def _item(acc, linha, valor, saldo, saldos):
        origem = acc.origem_item(linha)
        if acc.pendente: acc.falhar("CONTINUACAO_NAO_CONFIRMADA", linha)
        valor, saldo = dinheiro_brl(valor), dinheiro_brl(saldo)
        anterior = saldos.get(acc.atual.id, Decimal("0.00"))
        if anterior + valor != saldo:
            acc.falhar("SALDO_ACUMULADO_INCONSISTENTE", linha)
        saldos[acc.atual.id] = saldo
        acc.boleto.item(valor, origem, saldo=saldo)
