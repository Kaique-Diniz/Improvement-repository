"""Portas novas, sem alterar os repositórios/formatos históricos 1.0/1.1."""
from typing import Protocol

from conversor.domain.audit_identity import PreparacaoTecnica
from conversor.domain.integrated_processing import (
    DocumentoReguaSintetica, ExecucaoIntegradaSintetica, IdentidadeOperador,
    PedidoProcessamentoIntegrado, ReferenciaReguaSintetica,
)
from .billing_ports import CredencialOperador


class AutenticadorEnsaioSintetico(Protocol):
    def autenticar(self, pedido: PedidoProcessamentoIntegrado,
                   credencial: CredencialOperador) -> IdentidadeOperador: ...


class RepositorioProcessamentosSinteticos(Protocol):
    ambiente: str
    def carregar_preparacao_tecnica(self, id_: str) -> PreparacaoTecnica: ...
    def carregar_regua(self, preparacao_id: str, referencia: ReferenciaReguaSintetica) -> DocumentoReguaSintetica: ...
    def salvar_processamento(self, execucao: ExecucaoIntegradaSintetica,
                            *, credencial: CredencialOperador) -> ExecucaoIntegradaSintetica: ...
    def carregar_processamento(self, id_: str) -> ExecucaoIntegradaSintetica: ...
