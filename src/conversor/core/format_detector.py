"""Detecção de tipo de fonte (format_detector).

Camada fina sobre ``SondadorLocal``: decide a família do arquivo (pdf_texto,
xlsx, csv, bloqueado) sem ler conteúdo sensível e sem classificar layout de
administradora — isso continua papel dos leitores/GRAMATICAS.

XLSX é detectado pela assinatura ZIP + parts de workbook (ooxml), igual ao
critério já usado pelo caminho BBZ.
"""
from dataclasses import dataclass

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.recognition import DocumentoSondado, TipoDocumento

FORMATOS_TEXTO = ("pdf_texto", "xlsx", "csv")


@dataclass(frozen=True)
class DeteccaoFormato:
    tipo: str                     # "pdf_texto" | "xlsx" | "csv" | "desconhecido" | "bloqueado"
    completo: bool
    bloqueios: tuple[str, ...]

    @property
    def suportado(self) -> bool:
        return self.tipo in FORMATOS_TEXTO and self.completo and not self.bloqueios


def detectar_bytes(conteudo: bytes, *, arquivo_id: str = "deteccao") -> DeteccaoFormato:
    sonda: DocumentoSondado = SondadorLocal().sondar(conteudo, arquivo_id=arquivo_id)
    if sonda.bloqueios:
        return DeteccaoFormato("bloqueado", sonda.completo, tuple(str(b) for b in sonda.bloqueios))
    return DeteccaoFormato(str(sonda.tipo), sonda.completo, ())


def detectar_arquivo(caminho) -> DeteccaoFormato:
    """Detecção por sondagem local; nunca abre o arquivo duas vezes além do necessário."""
    from pathlib import Path

    sonda = SondadorLocal().sondar_arquivo(Path(caminho), arquivo_id=Path(caminho).name)
    if sonda.bloqueios:
        return DeteccaoFormato("bloqueado", sonda.completo, tuple(str(b) for b in sonda.bloqueios))
    return DeteccaoFormato(str(sonda.tipo), sonda.completo, ())


def eh_xlsx(conteudo: bytes) -> bool:
    return detectar_bytes(conteudo).tipo == str(TipoDocumento.XLSX)


__all__ = ["DeteccaoFormato", "detectar_bytes", "detectar_arquivo", "eh_xlsx"]
