"""Conferência pós-escrita do XLSX diagnóstico; não modifica a seleção financeira.

Lê os bytes efetivamente gerados e compara com as linhas planejadas. A conferência
não atesta titularidade nem substitui o confronto do relatório financeiro de origem.
Os resultados agregados não incluem CPF, telefone, e-mail ou nome de pessoas.
"""
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from conversor.domain.template import COLUNAS


def _igual(obtido, esperado):
    if isinstance(esperado, Decimal):
        try:
            return type(obtido) in (int, float) and Decimal(str(obtido)) == esperado
        except (InvalidOperation, ValueError):
            return False
    if isinstance(esperado, date):
        return isinstance(obtido, datetime) and obtido.date() == esperado
    if isinstance(esperado, int):
        return type(obtido) is int and obtido == esperado
    if isinstance(esperado, str):
        return ("" if obtido is None else obtido) == esperado and (
            obtido is None or isinstance(obtido, str))
    return obtido == esperado


def validar_conversao(path: Path, *, registros, linhas_info, decisoes,
                      escopo_destino=None, unidades_contato_retido=()):
    """Retorna um relatório verificável; erros críticos impedem o download.

    registros: tuplas de 30 valores materializadas pelo contrato de exportação;
    linhas_info: correspondência entre linha, boleto e unidade do diagnóstico.
    """
    registros = tuple(tuple(r) for r in registros)
    linhas_info = tuple(linhas_info)
    decisoes = tuple(decisoes)
    retidas = set(unidades_contato_retido)
    erros = []
    avisos = []
    limite = 30

    def erro(codigo, detalhe, linha=None, coluna=None):
        if len(erros) < limite:
            item = {"codigo": codigo, "descricao": detalhe}
            if linha is not None:
                item["linha"] = linha
            if coluna is not None:
                item["coluna"] = coluna
            erros.append(item)

    if len(linhas_info) != len(registros):
        erro("METADADOS_DIVERGENTES", "Quantidade de vínculos de rastreio diferente das linhas previstas.")

    dividas = [m for m in linhas_info if m.get("tipo") == "divida"]
    cadastros = [m for m in linhas_info if m.get("tipo") == "cadastral"]
    selecionados = Counter(d["id"] for d in decisoes if d.get("situacao") == "elegivel")
    exportados = Counter(m.get("boleto_id") for m in dividas)
    if selecionados != exportados:
        erro("BOLETOS_DIVERGENTES", "Boletos efetivamente planejados não correspondem às decisões elegíveis.")

    permitidas = None
    if escopo_destino is not None:
        permitidas = {u.unidade_id for u in escopo_destino.unidades
                      if u.estado == "comprovado_documentalmente"}
        if any(m.get("unidade_id") not in permitidas for m in linhas_info):
            erro("UNIDADE_FORA_DO_ESCOPO", "Há linha planejada para unidade sem pertencimento comprovado.")

    if any(m.get("tipo") not in ("divida", "cadastral") for m in linhas_info):
        erro("TIPO_LINHA_INESPERADO", "Há metadados de linha com tipo desconhecido.")

    total_esperado = sum((r[29] for r, m in zip(registros, linhas_info)
                          if m.get("tipo") == "divida"), Decimal("0"))
    total_obtido = Decimal("0")
    linhas_lidas = 0

    if registros:
        if not path.is_file():
            erro("ARQUIVO_AUSENTE", "O XLSX planejado não está disponível para conferência.")
        else:
            try:
                workbook = load_workbook(path, read_only=True, data_only=False, keep_links=False)
                try:
                    if workbook.sheetnames != ["Dados"]:
                        erro("ABAS_DIVERGENTES", "O XLSX deve conter somente a aba Dados.")
                    if "Dados" in workbook.sheetnames:
                        aba = workbook["Dados"]
                        if aba.max_column != 30:
                            erro("QUANTIDADE_COLUNAS_INVALIDA", "O XLSX não possui exatamente 30 colunas.")
                        cabecalho = next(aba.iter_rows(min_row=1, max_row=1, values_only=True), ())
                        if tuple(cabecalho) != COLUNAS:
                            erro("CABECALHO_DIVERGENTE", "Os nomes ou a ordem das 30 colunas divergiram.")
                        for n, cells in enumerate(aba.iter_rows(min_row=2), start=2):
                            linhas_lidas += 1
                            indice = n - 2
                            if indice >= len(registros):
                                erro("LINHA_EXCEDENTE", "Há linha adicional no XLSX.", linha=n)
                                continue
                            esperado = registros[indice]
                            if len(cells) != 30:
                                erro("COLUNAS_NA_LINHA", "Linha com quantidade inesperada de colunas.", linha=n)
                                continue
                            for col, (cell, exp) in enumerate(zip(cells, esperado), start=1):
                                if cell.data_type == "f":
                                    erro("FORMULA_NO_XLSX", "Fórmula detectada no arquivo de teste.", n, col)
                                if not _igual(cell.value, exp):
                                    erro("CELULA_DIVERGENTE", "Valor ou tipo diverge da linha planejada.", n, col)
                            meta = linhas_info[indice] if indice < len(linhas_info) else {}
                            if meta.get("tipo") == "cadastral":
                                if any(c.value not in (None, "") for c in cells[24:30]):
                                    erro("FINANCEIRO_EM_CADASTRO", "Cadastro adicional contém campos financeiros.", n)
                            elif meta.get("tipo") == "divida":
                                valor = cells[29].value
                                if type(valor) not in (int, float) or valor <= 0:
                                    erro("VALOR_DIVIDA_INVALIDO", "Valor financeiro inválido.", n, 30)
                                else:
                                    total_obtido += Decimal(str(valor))
                                if not isinstance(cells[28].value, datetime):
                                    erro("VENCIMENTO_INVALIDO", "Vencimento não é uma data Excel.", n, 29)
                            if meta.get("unidade_id") in retidas:
                                if any(c.value not in (None, "") for c in
                                       (cells[2], *cells[11:24])):
                                    erro("CONTATO_RETIDO_EXPOSTO", "Documento ou contato de unidade retida presente.", n)
                            if cells[2].value not in (None, ""):
                                if cells[2].data_type != "s" or cells[2].number_format != "@":
                                    erro("DOCUMENTO_SEM_TEXTO", "Documento não está preservado como texto.", n, 3)
                finally:
                    workbook.close()
            except (OSError, ValueError, BadZipFile, InvalidFileException, KeyError):
                erro("XLSX_ILEGIVEL", "Não foi possível conferir a integridade do XLSX.")
    elif path.exists():
        erro("ARQUIVO_INESPERADO", "Há XLSX embora nenhuma linha estivesse planejada.")

    if linhas_lidas != len(registros) and registros:
        erro("TOTAL_LINHAS_DIVERGENTE", "Quantidade de linhas no XLSX difere do planejado.")
    if total_obtido != total_esperado and registros:
        erro("SOMA_FINANCEIRA_DIVERGENTE", "A soma financeira do XLSX difere da soma das linhas planejadas.")

    pendentes = Counter(m for d in decisoes if d.get("situacao") == "revisao"
                        for m in (d.get("bloqueios") or ["CONDICAO_INDETERMINADA"]))
    if pendentes:
        avisos.append({"codigo": "BOLETOS_EM_REVISAO", "quantidade": sum(
            d.get("situacao") == "revisao" for d in decisoes),
            "descricao": "Há boletos retidos pela análise; não foram automaticamente liberados."})
    if retidas:
        avisos.append({"codigo": "CONTATOS_DOCUMENTAIS_RETIDOS", "quantidade": len(retidas),
                       "descricao": "Unidades com documento ou contato protegido por conflito documental."})
    if escopo_destino is not None and len(permitidas) < len(escopo_destino.unidades):
        avisos.append({"codigo": "ESCOPO_NAO_COMPROVADO",
                       "quantidade": len(escopo_destino.unidades) - len(permitidas),
                       "descricao": "Unidades sem prova de pertencimento permanecem fora do XLSX."})

    estado = ("erro_critico" if erros else "sem_arquivo" if not registros
              else "conforme_com_ressalvas" if avisos else "conforme")
    return {
        "versao": "validacao_conversao@1",
        "estado": estado,
        "autoriza_cobranca": False,
        "permite_exportacao_operacional": False,
        "limite": "Verifica arquivo gerado versus linhas planejadas e bloqueios conhecidos; "
                  "não atesta fidelidade integral ao documento original, titularidade ou cobrança.",
        "indicadores": {
            "boletos_analisados": len(decisoes),
            "boletos_elegiveis": sum(d.get("situacao") == "elegivel" for d in decisoes),
            "boletos_em_revisao": sum(d.get("situacao") == "revisao" for d in decisoes),
            "linhas_divida": len(dividas),
            "linhas_cadastrais": len(cadastros),
            "linhas_lidas_xlsx": linhas_lidas,
            "unidades_no_xlsx": len({m.get("unidade_id") for m in linhas_info}),
            "unidades_escopo_comprovado": len(permitidas) if permitidas is not None else None,
            "unidades_escopo_pendente": (len(escopo_destino.unidades) - len(permitidas)
                                        if escopo_destino is not None else None),
            "valor_financeiro_xlsx": f"{total_obtido:.2f}",
            "valor_financeiro_planejado": f"{total_esperado:.2f}",
        },
        "motivos_retencao": [{"codigo": k, "quantidade": v}
                             for k, v in sorted(pendentes.items())],
        "erros": erros,
        "avisos": avisos,
    }
