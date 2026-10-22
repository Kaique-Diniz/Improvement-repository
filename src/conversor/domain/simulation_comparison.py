"""Vínculos revisados com referência, sem gerar linhas de exportação operacional."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Hash, Id, Modelo, Texto
from .canonical import Origem
from .template import COLUNAS, Template


class VinculoReferencia(Modelo):
    linha: int = Field(strict=True, ge=2)
    unidade_id: Id
    pessoa_id: Id | None = None
    tipo: Literal['divida', 'cadastral']
    boletos_ids: tuple[Id, ...]
    criterio_valor: Literal['soma_originais_para_comparacao'] = 'soma_originais_para_comparacao'

    @model_validator(mode='after')
    def tipo_linha(self):
        if (self.tipo == 'divida') != bool(self.boletos_ids):
            raise ValueError('VINCULO_DE_DIVIDA_INCOMPATIVEL')
        return self


class MapeamentoReferencia(Modelo):
    referencia_id: Id
    referencia_hash: Hash
    evidencia_revisao_id: Id
    fundamento: Texto = Field(repr=False)
    vinculos: Annotated[tuple[VinculoReferencia, ...], Field(min_length=1)] = Field(repr=False)

    @model_validator(mode='after')
    def sem_duplicidades(self):
        if len({v.linha for v in self.vinculos}) != len(self.vinculos):
            raise ValueError('LINHA_DE_REFERENCIA_DUPLICADA')
        boletos = [b for v in self.vinculos for b in v.boletos_ids]
        if len(set(boletos)) != len(boletos):
            raise ValueError('BOLETO_VINCULADO_MAIS_DE_UMA_VEZ')
        return self


class DivergenciaSimulacao(Modelo):
    categoria: Literal['regras', 'dados', 'formatacao', 'nao_avaliavel']
    motivo_codigo: Id
    linha: int | None = None
    coluna: str | None = None
    unidade_id: Id | None = None
    boletos_ids: tuple[Id, ...] = ()
    esperado_hash: Hash | None = None
    observado_hash: Hash | None = None
    origens: tuple[Origem, ...] = ()
    exige_revisao_humana: Literal[True] = True


class ComparacaoPrivada(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    id: Id
    condominio_id: Id
    ambiente: Literal['sintetico', 'privado']
    execucao_id: Id
    execucao_hash: Hash
    comparador_versao: Literal['4.3A.0'] = '4.3A.0'
    comparador_hash: Hash
    template: Template
    mapeamento: MapeamentoReferencia = Field(repr=False)
    divergencias: tuple[DivergenciaSimulacao, ...] = Field(repr=False)
    colunas: Annotated[tuple[str, ...], Field(min_length=30, max_length=30)]
    colunas_nao_avaliadas: tuple[str, ...]
    cobertura_referencia_completa: bool
    referencia_e_gabarito_absoluto: Literal[False] = False
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False

    @model_validator(mode='after')
    def contrato(self):
        if self.colunas != COLUNAS:
            raise ValueError('COMPARACAO_FORA_DO_TEMPLATE_UNIVERSAL')
        return self
