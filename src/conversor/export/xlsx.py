"""Escrita atômica do contrato universal, com tipos nativos e verificação de centavos."""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import os
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import re

from openpyxl import Workbook, load_workbook

from conversor.domain.template import Template
from conversor.readers.text_support import ErroLeitura
from .contract import materializar


def escrever_xlsx(linhas, template: Template, destino: Path, *, data_ref: date,
                  titulo="LABORATORIO SINTETICO - NAO HOMOLOGADO PARA PRODUCAO"):
    registros = tuple(materializar(linha) for linha in linhas)
    workbook = Workbook()
    aba = workbook.active
    aba.title = template.nome_aba
    workbook.properties.title = titulo
    workbook.properties.creator = "Conversor Inteligente de Inadimplencia"
    instante = datetime(data_ref.year, data_ref.month, data_ref.day, tzinfo=timezone.utc)
    workbook.properties.created = workbook.properties.modified = instante
    aba.append(template.cabecalhos_fisicos)
    for registro in registros:
        aba.append(registro.valores)
        for celula in aba[aba.max_row]:
            if isinstance(celula.value, str):
                celula.data_type = "s"  # texto literal, nunca fórmula/macros vindas de fonte
                if celula.column == 3:
                    celula.number_format = "@"
            elif isinstance(celula.value, date):
                celula.number_format = "dd/mm/yyyy"
            elif isinstance(celula.value, Decimal):
                celula.number_format = "0.00"
    memoria = BytesIO()
    workbook.save(memoria)
    workbook.close()
    # openpyxl atualiza modified ao salvar. Normalizamos metadados e timestamps ZIP.
    buffer = BytesIO()
    with ZipFile(BytesIO(memoria.getvalue())) as original, ZipFile(buffer, "w", compression=ZIP_DEFLATED) as final:
        for nome in sorted(original.namelist()):
            conteudo = original.read(nome)
            if nome == "docProps/core.xml":
                conteudo = re.sub(rb'(<dcterms:modified[^>]*>).*?(</dcterms:modified>)',
                                 lambda m: m[1] + instante.strftime("%Y-%m-%dT%H:%M:%SZ").encode() + m[2], conteudo)
            info = ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            final.writestr(info, conteudo)
    conteudo = buffer.getvalue()
    conferir = load_workbook(BytesIO(conteudo), read_only=True, data_only=False)
    try:
        valores = list(conferir["Dados"].iter_rows(values_only=True))
        if tuple(valores[0]) != template.cabecalhos_fisicos or len(valores) != len(registros) + 1:
            raise ErroLeitura("XLSX_FORA_DO_CONTRATO")
        for obtido, registro in zip(valores[1:], registros):
            documento = registro.valores[2]
            if documento and (not isinstance(obtido[2], str) or obtido[2] != documento):
                raise ErroLeitura("DOCUMENTO_XLSX_INCOMPATIVEL")
            valor = registro.valores[-1]
            if isinstance(valor, Decimal) and Decimal(str(obtido[-1])) != valor:
                raise ErroLeitura("PRECISAO_XLSX_INCOMPATIVEL")
            if registro.valores[-2] != "" and not isinstance(obtido[-2], datetime):
                raise ErroLeitura("DATA_XLSX_INCOMPATIVEL")
        for row in conferir["Dados"].iter_rows(min_row=2, min_col=3, max_col=3):
            if row[0].value is not None and (row[0].data_type != "s" or row[0].number_format != "@"):
                raise ErroLeitura("DOCUMENTO_XLSX_INCOMPATIVEL")
    finally:
        conferir.close()
    destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=destino.parent, prefix=".excel-", suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, destino)
    finally:
        if temporario is not None: temporario.unlink(missing_ok=True)
    ocorrencias = {o.id: o for registro in registros for o in registro.ocorrencias}
    return tuple(ocorrencias.values())
