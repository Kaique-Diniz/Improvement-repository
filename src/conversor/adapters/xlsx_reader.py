"""Leitor genérico de XLSX para diagnóstico e fontes tabulares homologadas."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
import unicodedata

from openpyxl.utils import column_index_from_string
from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.readers.text_support import ErroLeitura

MOEDA_BRL = re.compile(r"^\(?\s*(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?(?:\s*(?:R\$\s*)?)?\)?$")

def decodificar_moeda(valor):
    if valor is None:
        return Decimal("0.00")
    if isinstance(valor, bool):
        raise ErroLeitura("VALOR_MONETARIO_INVALIDO")
    if isinstance(valor, int):
        return Decimal(valor).quantize(Decimal("0.01"))
    if isinstance(valor, float):
        try:
            numero = Decimal(repr(valor)).quantize(Decimal("0.01"))
        except InvalidOperation:
            raise ErroLeitura("VALOR_MONETARIO_INVALIDO") from None
        return numero
    
    texto = str(valor).strip()
    if not texto:
        return Decimal("0.00")
    
    negativo = texto.startswith("(") and texto.endswith(")")
    limpo = re.sub(r"[Rr]\$|\s|\(", "", texto).replace(")", "")
    
    if "," in limpo:
        inteiro, _, fracao = limpo.rpartition(",")
        inteiro = inteiro.replace(".", "")
        fracao = (fracao + "00")[:2]
    else:
        if limpo.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
            inteiro, fracao = limpo.replace(".", ""), "00"
        else:
            inteiro, _, fracao = limpo.partition(".")
            fracao = (fracao + "00")[:2]
            
    if not re.fullmatch(r"-?\d+", inteiro):
        raise ErroLeitura("VALOR_MONETARIO_INVALIDO")
        
    numero = Decimal(f"{inteiro.lstrip('-')}.{fracao}")
    return -numero if (negativo or limpo.startswith("-")) else numero

def cabecalho_normalizado(nome):
    if nome is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(nome).strip().upper())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9]+", "_", texto).strip("_")
    return texto

class LinhasXLSX:
    def __init__(self, aba, colunas, linhas):
        self.aba_nome = aba.title
        self.colunas = colunas
        self.linhas = linhas

    def __len__(self):
        return len(self.linhas)

def ler_planilha(conteudo: bytes, *, arquivo_id: str, aba=None, cabecalho_linha=1, max_linhas=100_000):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id=arquivo_id)
    if sonda.tipo != "xlsx" or sonda.bloqueios or not sonda.completo:
        raise ErroLeitura("XLSX_NAO_EXTRAIVEL_COM_SEGURANCA")
        
    try:
        livro = load_workbook(BytesIO(conteudo), data_only=True, keep_links=False)
    except Exception:
        raise ErroLeitura("XLSX_INVALIDO") from None

    try:
        if aba is None:
            if len(livro.worksheets) == 0:
                raise ErroLeitura("XLSX_SEM_ABA")
            folha = livro.worksheets[0]
        else:
            try:
                folha = livro[aba]
            except KeyError:
                raise ErroLeitura("XLSX_ABA_INEXISTENTE") from None

        celulas = list(folha.iter_rows())
        if len(celulas) > max_linhas:
            raise ErroLeitura("LIMITE_LINHAS_EXCEDIDO")
            
        try:
            cab = celulas[cabecalho_linha - 1]
        except IndexError:
            raise ErroLeitura("XLSX_SEM_CABECALHO") from None

        colunas = []
        for indice, celula in enumerate(cab):
            rotulo = "" if celula.value is None else str(celula.value).strip()
            if not rotulo:
                break
            colunas.append((cabecalho_normalizado(rotulo), rotulo))

        if not colunas:
            raise ErroLeitura("XLSX_SEM_CABECALHO")

        chaves = [c for c, _ in colunas]
        if len(set(chaves)) != len(chaves):
            raise ErroLeitura("XLSX_COLUNAS_DUPLICADAS")

        registros = []
        for numero, fila in enumerate(celulas[cabecalho_linha:], start=cabecalho_linha + 1):
            valores = [celula.value for celula in fila[: len(colunas)]]
            extras = [celula.value for celula in fila[len(colunas):]]
            
            if any(v is not None for v in extras):
                raise ErroLeitura("XLSX_COLUNAS_NAO_RECONHECIDAS", linha=numero)
            if all(v is None or str(v).strip() == "" for v in valores):
                continue

            registro = {chave: valor for (chave, _), valor in zip(colunas, valores)}
            registro["__linha__"] = numero
            registros.append(registro)

        return LinhasXLSX(folha, tuple(colunas), tuple(registros))
    finally:
        livro.close()

def celula_data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor is None:
        raise ErroLeitura("DATA_INVALIDA")
    
    texto = str(valor).strip()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if not m:
        raise ErroLeitura("DATA_INVALIDA")
    
    dia, mes, ano = (int(g) for g in m.groups())
    try:
        return date(ano, mes, dia)
    except ValueError:
        raise ErroLeitura("DATA_INVALIDA") from None
