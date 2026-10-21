"""Validação independente da fonte de planos, vinculada à autoridade configurada."""
from typing import Protocol

from conversor.domain.billing_rules import EstadoPlanos


class VerificadorEstadoPlanos(Protocol):
    def conferir(self, estado: EstadoPlanos) -> None:
        """Exigir revisão atual, aprovação autêntica e integridade contra a autoridade."""
        ...
