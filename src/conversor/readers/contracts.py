from typing import Annotated, Literal, Protocol, TYPE_CHECKING, runtime_checkable

from pydantic import Field, model_validator

from conversor.domain.base import Hash, Id, Modelo
from conversor.domain.canonical import LoteCanonico

if TYPE_CHECKING:
    from .text_support import ContextoLeitura


class ClassificacaoFormato(Modelo):
    estado: Literal["conhecido_validado", "desconhecido", "ambiguo"]
    candidatos: tuple[Id, ...] = ()
    evidencia_hashes: Annotated[tuple[Hash, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def coerencia(self):
        quantidade = len(set(self.candidatos))
        if quantidade != len(self.candidatos):
            raise ValueError("CANDIDATO_DUPLICADO")
        if ((self.estado == "conhecido_validado" and quantidade != 1)
                or (self.estado == "desconhecido" and quantidade != 0)
                or (self.estado == "ambiguo" and quantidade < 2)):
            raise ValueError("CLASSIFICACAO_INCONSISTENTE")
        return self

    @property
    def bloqueante(self) -> bool:
        return self.estado != "conhecido_validado"


class FonteProtegida(Modelo):
    arquivo_id: Id
    sha256: Hash


class RepositorioFontes(Protocol):
    def ler(self, fonte: FonteProtegida) -> bytes: ...


class ResolutorContexto(Protocol):
    def resolver(self, fonte: FonteProtegida, *, formato_id: str, condominio_id: str) -> "ContextoLeitura": ...


@runtime_checkable
class Leitor(Protocol):
    """Adaptadores por leitor_id/versão; retornam o mesmo contrato inclusive para Cadastro."""
    def ler(self, fonte: FonteProtegida, *, formato_id: str, condominio_id: str) -> LoteCanonico: ...
