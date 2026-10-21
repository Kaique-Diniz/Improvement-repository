from datetime import date
from typing import Protocol

from conversor.domain.base import Modelo
from conversor.domain.catalog import (Administradora, Catalogo, Condominio, Formato,
                                     PerfilCondominio, Processamento, RegraCobranca)
from conversor.domain.canonical import Ocorrencia
from conversor.domain.template import Template


class ErroAplicacao(Exception):
    """Código estável, seguro para CLI/logs; nunca carrega o documento recebido."""


class Estado(Modelo):
    revisao: int
    catalogo: Catalogo


class Repositorio(Protocol):
    """Unidade de trabalho atômica, implementável em JSON ou SQL."""
    def carregar(self) -> Estado: ...
    def salvar(self, catalogo: Catalogo, *, revisao_esperada: int) -> Estado: ...


class RepositorioAdministradoras(Protocol):
    def get_administradora(self, id_: str) -> Administradora: ...


class RepositorioCondominios(Protocol):
    def get_condominio(self, id_: str) -> Condominio: ...
    def encontrar_condominio(self, administradora_id: str, codigo: str) -> Condominio: ...


class RepositorioFormatos(Protocol):
    def get_formato(self, id_: str) -> Formato: ...
    def formatos_da_administradora(self, administradora_id: str) -> tuple[Formato, ...]: ...


class RepositorioPerfis(Protocol):
    def get_perfil(self, id_: str) -> PerfilCondominio: ...


class RepositorioRegras(Protocol):
    def get_regra(self, id_: str) -> RegraCobranca: ...
    def regra_aprovada(self, condominio_id: str, data_ref: date) -> RegraCobranca: ...


class RepositorioTemplates(Protocol):
    def get_template(self, id_: str) -> Template: ...


class RepositorioHistorico(Protocol):
    def get_processamento(self, id_: str) -> Processamento: ...
    def salvar_processamento(self, processamento: Processamento, *, revisao_esperada: int) -> Estado: ...
    def salvar_ocorrencia(self, ocorrencia: Ocorrencia, *, revisao_esperada: int) -> Estado: ...
