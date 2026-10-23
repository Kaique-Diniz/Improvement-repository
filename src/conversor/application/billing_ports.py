"""Porta transacional: não oferece salvar snapshot arbitrário/aprovar via importação."""
from dataclasses import dataclass, field
from typing import Protocol

from conversor.domain.billing_rules import ComandoPlano, EstadoPlanos
from .ports import ErroAplicacao


@dataclass(frozen=True)
class CredencialOperador:
    segredo: str = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.segredo, str) or len(self.segredo) < 32:
            raise ErroAplicacao('CREDENCIAL_INVALIDA')


class RepositorioPlanos(Protocol):
    def carregar(self) -> EstadoPlanos: ...
    def executar(self, comando: ComandoPlano, *, credencial: CredencialOperador,
                 revisao_esperada: int) -> EstadoPlanos: ...
