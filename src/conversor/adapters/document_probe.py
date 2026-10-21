"""Sondagem local para assinaturas. Não produz Pessoa, Unidade, Boleto ou valores."""
import csv
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO, StringIO
import logging
from pathlib import Path
import warnings
from zipfile import BadZipFile, ZipFile

from defusedxml.ElementTree import fromstring
from openpyxl import load_workbook
from pypdf import PdfReader

from conversor.application.ports import ErroAplicacao
from conversor.domain.recognition import DocumentoSondado, FragmentoSondagem, Motivo, TipoDocumento

# Bibliotecas de parsing não podem enviar trechos de documentos ao logger da aplicação.
for _namespace in ("pypdf", "openpyxl"):
    _logger = logging.getLogger(_namespace)
    _logger.addHandler(logging.NullHandler())
    _logger.propagate = False


@dataclass(frozen=True)
class LimitesSondagem:
    bytes_arquivo: int = 20 * 1024 * 1024
    paginas: int = 1000
    caracteres: int = 5_000_000
    bytes_stream_pdf: int = 20 * 1024 * 1024
    arquivos_zip: int = 1000
    bytes_descompactados: int = 100 * 1024 * 1024
    abas: int = 100
    linhas_planilha: int = 100_000
    colunas_planilha: int = 200
    celulas: int = 200_000


class _Limite(Exception):
    pass


class _Protegido(Exception):
    pass


class SondadorLocal:
    def __init__(self, limites: LimitesSondagem | None = None):
        self.limites = limites or LimitesSondagem()

    def sondar_arquivo(self, arquivo: Path, *, arquivo_id: str) -> DocumentoSondado:
        try:
            with arquivo.open("rb") as fonte:
                conteudo = fonte.read(self.limites.bytes_arquivo + 1)
        except OSError:
            raise ErroAplicacao("FALHA_ACESSO_FONTE") from None
        # Não calcula hash parcial fingindo ser o hash do arquivo inteiro.
        if len(conteudo) > self.limites.bytes_arquivo:
            raise ErroAplicacao("LIMITE_ARQUIVO_EXCEDIDO")
        return self.sondar(conteudo, arquivo_id=arquivo_id)

    def sondar(self, conteudo: bytes, *, arquivo_id: str) -> DocumentoSondado:
        base = dict(arquivo_id=arquivo_id, arquivo_hash=sha256(conteudo).hexdigest())
        tipo = TipoDocumento.DESCONHECIDO
        try:
            if len(conteudo) > self.limites.bytes_arquivo:
                raise _Limite
            if not conteudo:
                return DocumentoSondado(**base, tipo=tipo, bloqueios=(Motivo.ARQUIVO_VAZIO,))
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                if conteudo.startswith(b"%PDF-"):
                    tipo = TipoDocumento.PDF_TEXTO
                    return self._pdf(conteudo, base)
                if conteudo.startswith(b"PK"):
                    tipo = TipoDocumento.XLSX
                    return self._xlsx(conteudo, base)
                return self._csv(conteudo, base)
        except _Limite:
            return DocumentoSondado(**base, tipo=tipo, completo=False, bloqueios=(Motivo.LIMITE_EXCEDIDO,))
        except _Protegido:
            return DocumentoSondado(**base, tipo=tipo, completo=False, bloqueios=(Motivo.DOCUMENTO_PROTEGIDO,))
        except Exception:
            # Erros do parser podem conter texto/caminhos privados: só código estável sai do adapter.
            return DocumentoSondado(**base, tipo=tipo, completo=False, bloqueios=(Motivo.DOCUMENTO_INVALIDO,))

    def _pdf(self, conteudo, base):
        leitor = PdfReader(BytesIO(conteudo), strict=True)
        if leitor.is_encrypted:
            raise _Protegido
        if len(leitor.pages) > self.limites.paginas:
            raise _Limite
        fragmentos, vazias, total, tem_imagem = [], 0, 0, False
        for numero, pagina in enumerate(leitor.pages, 1):
            stream = pagina.get_contents()
            if stream is not None and len(stream.get_data()) > self.limites.bytes_stream_pdf:
                raise _Limite
            texto = pagina.extract_text() or ""
            total += len(texto)
            if total > self.limites.caracteres:
                raise _Limite
            if texto.strip():
                fragmentos.append(FragmentoSondagem(localizador=f"pagina_{numero}", texto=texto))
            else:
                vazias += 1
                recursos = pagina.get("/Resources", {})
                recursos = recursos.get_object() if hasattr(recursos, "get_object") else recursos
                objetos = recursos.get("/XObject", {})
                objetos = objetos.get_object() if hasattr(objetos, "get_object") else objetos
                tem_imagem = tem_imagem or any(o.get_object().get("/Subtype") == "/Image" for o in objetos.values())
        if not fragmentos:
            tipo = TipoDocumento.PDF_IMAGEM if tem_imagem else TipoDocumento.DESCONHECIDO
            return DocumentoSondado(**base, tipo=tipo, completo=False,
                                    bloqueios=(Motivo.PDF_SEM_TEXTO,))
        if vazias:
            return DocumentoSondado(**base, tipo=TipoDocumento.PDF_MISTO, completo=False,
                                    bloqueios=(Motivo.PDF_MISTO,))
        return DocumentoSondado(**base, tipo=TipoDocumento.PDF_TEXTO, fragmentos=tuple(fragmentos))

    def _xlsx(self, conteudo, base):
        with ZipFile(BytesIO(conteudo)) as arquivo:
            infos = arquivo.infolist()
            nomes = [i.filename for i in infos]
            if len(infos) > self.limites.arquivos_zip or sum(i.file_size for i in infos) > self.limites.bytes_descompactados:
                raise _Limite
            if len(set(nomes)) != len(nomes):
                raise BadZipFile
            if "[Content_Types].xml" not in nomes or "xl/workbook.xml" not in nomes:
                return DocumentoSondado(**base, tipo=TipoDocumento.DESCONHECIDO, bloqueios=(Motivo.TIPO_NAO_SUPORTADO,))
            if any(i.flag_bits & 1 for i in infos):
                raise _Protegido
            if any("vbaproject" in n.lower() or n.startswith("xl/externalLinks/") for n in nomes):
                raise _Protegido
            for nome in nomes:
                if nome.endswith((".xml", ".rels")):
                    fromstring(arquivo.read(nome), forbid_dtd=True)  # antes de openpyxl
        livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=False, keep_links=False)
        try:
            if len(livro.worksheets) > self.limites.abas:
                raise _Limite
            fragmentos, total, celulas = [], 0, 0
            for numero, aba in enumerate(livro.worksheets, 1):
                if (aba.max_row or 0) > self.limites.linhas_planilha or (aba.max_column or 0) > self.limites.colunas_planilha:
                    raise _Limite
                # Metadados de dimensão podem estar errados: percorrer o XML real até o fim.
                aba.reset_dimensions()
                linhas = []
                for indice, linha in enumerate(aba.iter_rows(), 1):
                    celulas += len(linha)
                    if (indice > self.limites.linhas_planilha or len(linha) > self.limites.colunas_planilha
                            or celulas > self.limites.celulas):
                        raise _Limite
                    valores = [str(c.value) if c.value is not None and c.data_type != "f" else "" for c in linha]
                    texto = "\t".join(valores).strip()
                    total += len(texto)
                    if total > self.limites.caracteres:
                        raise _Limite
                    linhas.append(texto)
                fragmentos.append(FragmentoSondagem(localizador=f"aba_{numero}", texto="\n".join(linhas)))
            return DocumentoSondado(**base, tipo=TipoDocumento.XLSX, fragmentos=tuple(fragmentos))
        finally:
            livro.close()

    def _csv(self, conteudo, base):
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeError:
            return DocumentoSondado(**base, tipo=TipoDocumento.DESCONHECIDO, bloqueios=(Motivo.TIPO_NAO_SUPORTADO,))
        if "\x00" in texto:
            return DocumentoSondado(**base, tipo=TipoDocumento.DESCONHECIDO, bloqueios=(Motivo.TIPO_NAO_SUPORTADO,))
        if len(texto) > self.limites.caracteres:
            raise _Limite
        candidatas = []
        for separador in (";", ",", "\t"):
            try:
                linhas = list(csv.reader(StringIO(texto, newline=""), delimiter=separador, strict=True))
            except csv.Error:
                continue
            if len(linhas) < 2 or not linhas[0] or len(linhas[0]) < 2:
                continue
            if len(linhas) > self.limites.linhas_planilha or sum(map(len, linhas)) > self.limites.celulas:
                raise _Limite
            if all(len(linha) == len(linhas[0]) for linha in linhas):
                candidatas.append(linhas)
        if len(candidatas) != 1:
            return DocumentoSondado(**base, tipo=TipoDocumento.DESCONHECIDO, bloqueios=(Motivo.CSV_INVALIDO,))
        linhas = candidatas[0]
        # Limites estruturais são verificados antes de produzir qualquer evidência.
        if len(linhas[0]) > self.limites.colunas_planilha:
            raise _Limite
        return DocumentoSondado(**base, tipo=TipoDocumento.CSV, fragmentos=(
            FragmentoSondagem(localizador="csv_1", texto="\n".join("\t".join(l) for l in linhas)),))
