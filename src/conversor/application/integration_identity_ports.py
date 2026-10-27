"""Porta de consulta; o consumidor não depende do armazenamento JSON."""
from typing import Protocol
from conversor.domain.integration_identity import CatalogoIdentidadesIntegracao


class RepositorioIdentidadesIntegracao(Protocol):
    def carregar(self) -> tuple[CatalogoIdentidadesIntegracao,str]:
        """Snapshot validado e hash do conteúdo consultado."""
        ...
