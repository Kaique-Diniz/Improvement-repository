from typing import Protocol

from conversor.domain.recognition import CatalogoAssinaturas, DocumentoSondado


class SondadorDocumento(Protocol):
    def sondar(self, conteudo: bytes, *, arquivo_id: str) -> DocumentoSondado: ...


class RepositorioAssinaturas(Protocol):
    def carregar(self) -> CatalogoAssinaturas: ...
