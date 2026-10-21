"""Gramática Habita recriada do pacote sintético; não homologada para PDFs reais."""
from decimal import Decimal
import re

from conversor.domain.canonical import Contato, Documento, Pessoa
from .text_support import AcumuladorLeitura, ContextoLeitura, TextoPDF, VALOR_BRL, data_curta, dinheiro_brl, telefone

QUATRO = rf"({VALOR_BRL})\s+({VALOR_BRL})\s+({VALOR_BRL})\s+({VALOR_BRL})"
INICIO = re.compile(rf"^(\d{{8}})\s+(?:([A-Z]+)\s+)?(\d{{2}}/\d{{2}}/\d{{2}})\s+(\d{{6}})\s+(\d+)\s+(.+?)\s+{QUATRO}$")
ITEM = re.compile(rf"^(\d+)\s+(.+?)\s+{QUATRO}$")
UNIDADE = re.compile(r"^Bloco:\s*(\w+)\s+Unidade:\s*(\w+)\s+(.+?)\s+CPF:\s*(.+)$")


class LeitorHabitaSintetico:
    formato_id = "habita_composicao_sintetico_v1"

    def ler(self, conteudo: bytes, *, contexto: ContextoLeitura):
        fonte = TextoPDF(conteudo, contexto)
        cabecalhos = [re.search(r"^Condominio:\s*(\d+)\s*-", l.texto) for p in fonte.paginas for l in p]
        codigos = {m[1] for m in cabecalhos if m}
        if codigos != {contexto.codigo_condominio}:
            from .text_support import ErroLeitura
            raise ErroLeitura("CONDOMINIO_DIVERGENTE")
        acc = AcumuladorLeitura(fonte)
        totalizadas = set()
        for pagina, linhas in enumerate(fonte.paginas, 1):
            for linha in linhas:
                texto = linha.texto.strip()
                if match := UNIDADE.fullmatch(texto):
                    bloco, unidade, nome, cpf = match.groups()
                    documento = Documento(tipo="cpf", valor=cpf) if re.fullmatch(r"[0-9.\-]+", cpf) else None
                    acc.unidade(bloco, unidade, nome, linha, documento)
                elif texto.startswith("Celular:"):
                    if acc.atual is None: acc.falhar("CONTATO_SEM_UNIDADE", linha)
                    match = re.fullmatch(r"Celular:\s*(.+?)\s+E-mail:\s*(\S+)", texto)
                    if not match: acc.falhar("CONTATO_INCOMPLETO", linha)
                    pessoa = acc.pessoas[acc.atual.id]
                    contato = Contato(telefones=(telefone(match[1]),), emails=(match[2],), origem=fonte.origem(linha))
                    acc.pessoas[acc.atual.id] = Pessoa.model_validate(pessoa.model_dump() | {"contato": contato})
                elif match := INICIO.fullmatch(texto):
                    numero, ap, venc, periodo, conta, historico, *valores = match.groups()
                    competencia = periodo[:4] + "-" + periodo[4:]
                    acc.iniciar(numero, data_curta(venc, linha), competencia, linha, ap)
                    self._item(acc, linha, valores)
                elif match := ITEM.fullmatch(texto):
                    self._item(acc, linha, match.groups()[-4:])
                elif match := re.fullmatch(rf"Total do boleto:\s*{QUATRO}", texto):
                    if acc.boleto is None: acc.falhar("TOTAL_SEM_BOLETO", linha)
                    esperado = tuple(map(dinheiro_brl, match.groups()))
                    atual = (sum((i.valor for i in acc.boleto.itens), Decimal("0.00")), acc.boleto.multa, acc.boleto.juros)
                    if atual != esperado[:3] or sum(atual) != esperado[3]: acc.falhar("SOMA_BOLETO_INCONSISTENTE", linha)
                    acc.finalizar()
                elif match := re.fullmatch(rf"Total da Unidade:\s*{QUATRO}", texto):
                    acc.finalizar()
                    if acc.atual is None: acc.falhar("TOTAL_SEM_UNIDADE", linha)
                    boletos = [b for b in acc.boletos if b.unidade_id == acc.atual.id]
                    original = sum((b.composicao.total_original for b in boletos), Decimal("0.00"))
                    multa = sum((b.multa for b in boletos), Decimal("0.00"))
                    juros = sum((b.juros for b in boletos), Decimal("0.00"))
                    valores = tuple(map(dinheiro_brl, match.groups()))
                    if (original, multa, juros, original+multa+juros) != valores: acc.falhar("SOMA_UNIDADE_INCONSISTENTE", linha)
                    totalizadas.add(acc.atual.id)
                elif texto.startswith("--- CONTINUA"):
                    acc.marcar_continuacao(linha)
                elif match := re.fullmatch(r"CONTINUACAO DO BOLETO (\d+) DA UNIDADE (\w+)-(\w+)", texto):
                    acc.continuar(match[1], match[2], match[3], linha)
                elif re.search(rf"{VALOR_BRL}$", texto):
                    acc.falhar("LINHA_FINANCEIRA_NAO_RECONHECIDA", linha)
            acc.fim_pagina(pagina)
        lote = acc.resultado()
        if totalizadas != {u.id for u in lote.unidades}:
            from .text_support import ErroLeitura
            raise ErroLeitura("TOTAL_UNIDADE_AUSENTE")
        return lote

    @staticmethod
    def _item(acc, linha, valores):
        valor, multa, juros, total = map(dinheiro_brl, valores)
        if valor + multa + juros != total: acc.falhar("SOMA_ITEM_INCONSISTENTE", linha)
        if acc.pendente: acc.falhar("CONTINUACAO_NAO_CONFIRMADA", linha)
        origem = acc.origem_item(linha)
        acc.boleto.item(valor, origem, multa=multa, juros=juros)
