"""Evidências cadastrais por papel, sem alterar os contratos canônicos históricos."""
from typing import Literal
from pydantic import Field
from .base import Id, Modelo
from .canonical import Documento, Origem, Telefone

PapelBBZ = Literal['titular', 'locatario', 'pagador', 'unidade', 'correspondencia', 'geral', 'observacoes']


class CampoCadastroBBZ(Modelo):
    papel: PapelBBZ
    secao: str
    campo: str
    valor_original: str = Field(repr=False)
    origem: Origem
    x_inicio: float = Field(ge=0, allow_inf_nan=False)
    x_fim: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)


class ParticipanteBBZ(Modelo):
    papel: PapelBBZ
    nome: str = Field(default='', repr=False)
    documentos: tuple[tuple[Documento, Origem], ...] = Field(default=(), repr=False)
    telefones: tuple[tuple[Telefone, Origem], ...] = Field(default=(), repr=False)
    emails: tuple[tuple[str, Origem], ...] = Field(default=(), repr=False)


class FichaCadastroBBZ(Modelo):
    unidade_id: Id
    codigo_cliente_original: str = Field(repr=False)
    cabecalhos: tuple[Origem, ...]
    participantes: tuple[ParticipanteBBZ, ...] = Field(repr=False)
    campos: tuple[CampoCadastroBBZ, ...] = Field(repr=False)
    alertas: tuple[str, ...] = ()
