"""Catálogo persistente versionado; não é cadastro de leitores ou de regras ativas."""
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from conversor.domain.integration_identity import CatalogoIdentidadesIntegracao
from conversor.adapters.json_repository import ler_json_bytes
from conversor.application.ports import ErroAplicacao
from conversor.readers.text_support import ErroLeitura


class RepositorioIdentidadesIntegracaoJSON:
    def __init__(self,caminho:Path):self.caminho=Path(caminho)

    def carregar(self):
        try:
            raw=self.caminho.read_bytes()
            catalogo=CatalogoIdentidadesIntegracao.model_validate(ler_json_bytes(raw))
            return catalogo,sha256(raw).hexdigest()
        except(OSError,ValidationError,ErroAplicacao):
            raise ErroLeitura('CATALOGO_IDENTIDADES_INTEGRACAO_INVALIDO')from None
