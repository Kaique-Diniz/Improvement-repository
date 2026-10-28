"""Conversão privada, explícita e auditada de template BIFF8; não é leitor financeiro.

Não executa fórmulas, macros ou links. O original permanece imutável. A saída é
somente uma referência para comparação, nunca o XLSX operacional do conversor.
"""
import argparse
from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
import os
from pathlib import Path
import re
from struct import unpack_from
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900, to_excel

from conversor.adapters.private_json import escrever_json
from conversor.adapters.private_simulation_json import conferir_local_privado
from conversor.domain.template import COLUNAS
from conversor.readers.text_support import ErroLeitura


def converter_referencia_xls(conteudo, *, revisar_cabecalho_y=False):
    import xlrd
    from xlrd.compdoc import CompDoc

    if len(conteudo) > 20 * 1024 * 1024 or not conteudo.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ErroLeitura('REFERENCIA_XLS_BIFF8_INVALIDA')
    try:
        composto = CompDoc(conteudo, logfile=StringIO())
        if any('vba' in e.name.lower() or e.name.lower() == 'macros' for e in composto.dirlist):
            raise ErroLeitura('REFERENCIA_XLS_CONTEUDO_ATIVO')
        stream = composto.get_named_stream('Workbook')
        if not stream:
            raise ErroLeitura('REFERENCIA_XLS_BIFF8_INVALIDA')
        pos = 0
        while pos + 4 <= len(stream):
            codigo, tamanho = unpack_from('<HH', stream, pos)
            if pos + 4 + tamanho > len(stream):
                raise ErroLeitura('REFERENCIA_XLS_TRUNCADA')
            if codigo in (0x0006, 0x002F):  # FORMULA / FILEPASS: não usar resultados em cache.
                raise ErroLeitura('REFERENCIA_XLS_FORMULA_OU_PROTECAO')
            if codigo == 0x0085 and tamanho >= 6 and stream[pos + 9] != 0:  # BOUNDSHEET não planilha.
                raise ErroLeitura('REFERENCIA_XLS_CONTEUDO_ATIVO')
            pos += 4 + tamanho
        antigo = xlrd.open_workbook(file_contents=conteudo, formatting_info=True, logfile=StringIO())
        if antigo.biff_version != 80 or antigo.nsheets != 1:
            raise ErroLeitura('REFERENCIA_XLS_AMBIGUA_OU_NAO_SUPORTADA')
        aba = antigo.sheet_by_index(0)
        if aba.ncols != 30 or not 1 <= aba.nrows <= 100000:
            raise ErroLeitura('REFERENCIA_XLS_FORA_DO_TEMPLATE')
        headers = tuple(str(aba.cell_value(0, j)).strip() for j in range(30))
        esperado = list(COLUNAS)
        corrigir_y = headers[24] == COLUNAS[26] and headers != COLUNAS
        if corrigir_y:
            if not revisar_cabecalho_y:
                raise ErroLeitura('REFERENCIA_XLS_CABECALHO_Y_EXIGE_REVISAO')
            esperado[24] = COLUNAS[26]
        if headers != tuple(esperado):
            raise ErroLeitura('REFERENCIA_XLS_CABECALHO_INCOMPATIVEL')
        novo = Workbook()
        novo.epoch = CALENDAR_MAC_1904 if antigo.datemode else CALENDAR_WINDOWS_1900
        novo.properties.created = novo.properties.modified = datetime(2000, 1, 1)
        destino = novo.active
        destino.title = aba.name
        celulas = []
        textuais = {1, 2, 5, 7, *range(11, 21)}
        limitacoes = []
        for i in range(aba.nrows):
            for j in range(30):
                c = aba.cell(i, j)
                formato = antigo.format_map[antigo.xf_list[c.xf_index].format_key].format_str
                valor = c.value
                if c.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    valor = None
                elif c.ctype == xlrd.XL_CELL_DATE:
                    valor = xlrd.xldate_as_datetime(c.value, antigo.datemode)
                elif c.ctype == xlrd.XL_CELL_ERROR:
                    raise ErroLeitura('REFERENCIA_XLS_CELULA_COM_ERRO')
                elif c.ctype == xlrd.XL_CELL_BOOLEAN:
                    valor = bool(c.value)
                elif c.ctype == xlrd.XL_CELL_NUMBER:
                    if c.value.is_integer():
                        valor = int(c.value)
                    if i and j in textuais:
                        if re.fullmatch('0{2,}', formato) and isinstance(valor, int) and valor >= 0:
                            valor = str(valor).zfill(len(formato))
                        else:
                            limitacoes.append({'linha': i + 1, 'coluna': j + 1,
                                'codigo': 'CAMPO_TEXTUAL_HISTORICO_NUMERICO_SEM_ZEROS_COMPROVADOS'})
                if not i:
                    valor = COLUNAS[j]
                out = destino.cell(i + 1, j + 1, valor)
                out.number_format = formato
                if isinstance(valor, str):
                    out.data_type = 's'  # até texto começando por '=' é literal.
                if valor is not None:
                    celulas.append({'linha': i + 1, 'coluna': j + 1, 'tipo_original': c.ctype,
                        'valor_original': c.value, 'formato_original': formato,
                        'valor_convertido': valor.isoformat() if isinstance(valor, datetime) else valor})
        memoria = BytesIO()
        novo.save(memoria)
        novo.close()
        # Repetir a conversão dos mesmos bytes produz a mesma referência/hash.
        normalizado = BytesIO()
        with ZipFile(memoria) as original, ZipFile(normalizado, 'w', compression=ZIP_DEFLATED) as final:
            for nome in sorted(original.namelist()):
                raw = original.read(nome)
                if nome == 'docProps/core.xml':
                    raw = re.sub(rb'(<dcterms:modified[^>]*>).*?(</dcterms:modified>)',
                        rb'\g<1>2000-01-01T00:00:00Z\g<2>', raw)
                info = ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                final.writestr(info, raw)
        convertido = normalizado.getvalue()
        conferir = load_workbook(BytesIO(convertido), data_only=False, keep_links=False)
        try:
            for e in celulas:
                obtido = conferir[aba.name].cell(e['linha'], e['coluna'])
                previsto = destino.cell(e['linha'], e['coluna']).value
                if isinstance(previsto, datetime):
                    igual = obtido.value == previsto and abs(to_excel(previsto, novo.epoch) - e['valor_original']) < 1e-9
                else:
                    igual = obtido.value == previsto and type(obtido.value) is type(previsto)
                if not igual or obtido.data_type == 'f':
                    raise ErroLeitura('REFERENCIA_XLS_CONVERSAO_NAO_RECONCILIADA')
        finally:
            conferir.close()
        return convertido, {'versao': 'conversao_referencia_biff8@1', 'somente_comparacao': True,
            'sha256_original': sha256(conteudo).hexdigest(), 'bytes_original': len(conteudo),
            'sha256_convertido': sha256(convertido).hexdigest(), 'aba': aba.name,
            'linhas_incluindo_cabecalho': aba.nrows, 'colunas': 30, 'datemode': antigo.datemode,
            'cabecalhos_originais': [aba.cell_value(0, j) for j in range(30)],
            'cabecalho_y_revisado_explicitamente': corrigir_y,
            'formulas_macros_links_executados': False, 'celulas_conferidas': celulas,
            'limitacoes': limitacoes, 'original_modificado': False}
    except ErroLeitura:
        raise
    except Exception:
        raise ErroLeitura('REFERENCIA_XLS_LEITURA_SEGURA_FALHOU') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origem', type=Path, required=True)
    parser.add_argument('--destino', type=Path, required=True, help='Diretório privado já existente, fora do Git.')
    parser.add_argument('--revisar-cabecalho-y', action='store_true')
    args = parser.parse_args()
    origem = conferir_local_privado(args.origem, arquivo=True)
    destino = conferir_local_privado(args.destino)
    xlsx = destino / 'referencia_convertida.xlsx'
    manifesto = destino / 'conversao_referencia_privada.json'
    if xlsx.exists() or manifesto.exists():
        raise ErroLeitura('REFERENCIA_CONVERTIDA_JA_EXISTE')
    conteudo, auditoria = converter_referencia_xls(origem.read_bytes(), revisar_cabecalho_y=args.revisar_cabecalho_y)
    with tempfile.NamedTemporaryFile(dir=destino, delete=False) as arq:
        temporario = Path(arq.name)
        try:
            arq.write(conteudo)
            arq.flush()
            os.fsync(arq.fileno())
            os.replace(temporario, xlsx)
        finally:
            temporario.unlink(missing_ok=True)
    escrever_json(manifesto, auditoria | {'origem_privada': str(origem), 'convertido_privado': str(xlsx)})
    print('Referência convertida e conferida. Original preservado; manifesto privado disponível.')


if __name__ == '__main__':
    main()
