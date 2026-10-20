from typing import Annotated, Literal, Protocol

from pydantic import Field, model_validator

from conversor.domain.base import Hash, Id, Modelo
from conversor.domain.canonical import LoteCanonico


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


class Leitor(Protocol):
    """Implementações futuras registradas por leitor_id/versão, nunca por condomínio."""
    def ler(self, fonte: FonteProtegida, *, formato_id: str, condominio_id: str) -> LoteCanonico: ...
