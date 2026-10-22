"""Contratos do laboratório privado. Nenhum DTO autoriza cobrança/exportação."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Data, Hash, Id, Modelo, Texto
from .billing_evaluation import EntradaSimulacao, RelatorioSimulacao
from .billing_rules import Ambiente, EstadoPlanos, Instante
from .canonical import Ocorrencia, Origem

CATEGORIAS = ('leitura', 'auditoria_lote', 'titularidade', 'documentos')


class FontePrivada(Modelo):
    arquivo_id: Id
    caminho: str = Field(repr=False, min_length=1)
    sha256: Hash
    tamanho: int = Field(strict=True, ge=1)
    papel: Literal['inadimplencia', 'cadastro', 'referencia', 'requisitos', 'evidencia']


class CatalogoImpedimentos(Modelo):
    """Vazio é um resultado revisado, nunca o default de falha de carregamento."""
    id: Id
    categoria: Literal['leitura', 'auditoria_lote', 'titularidade', 'documentos']
    condominio_id: Id
    ocorrencias: tuple[Ocorrencia, ...] = Field(repr=False)
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def unicos(self):
        if len({o.id for o in self.ocorrencias}) != len(self.ocorrencias):
            raise ValueError('OCORRENCIA_DUPLICADA_NO_CATALOGO')
        return self


class RegistroInventariado(Modelo):
    tipo: Literal['unidade', 'boleto', 'pessoa', 'fato', 'ocorrencia', 'cobertura', 'ressalva', 'catalogo']
    id: str
    sha256: Hash


class CampoAusente(Modelo):
    registro_id: Id
    campo: str


class InventarioEntrada(Modelo):
    hash_entrada: Hash
    registros: tuple[RegistroInventariado, ...]
    apontamentos: int = Field(strict=True, ge=0)
    itens_composicao: int = Field(strict=True, ge=0)
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]
    campos_ausentes: tuple[CampoAusente, ...]


class AtestoCompletude(Modelo):
    em: Instante
    data_ref: Data
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id
    inventario_conferido: Literal[True]
    fontes_e_paginas_conferidas: Literal[True]
    catalogos_externos_completos: Literal[True]
    ausencias_conferidas: Literal[True]


class CandidatoPacote(Modelo):
    """Pode ser inventariado antes da revisão; NÃO pode entrar no simulador."""
    schema_version: Literal['1.0'] = '1.0'
    id: Id
    condominio_id: Id
    ambiente: Ambiente
    entrada: EntradaSimulacao = Field(repr=False)
    catalogos: Annotated[tuple[CatalogoImpedimentos, ...], Field(min_length=4, max_length=4)] = Field(repr=False)
    fontes: Annotated[tuple[FontePrivada, ...], Field(min_length=1)] = Field(repr=False)
    inventario: InventarioEntrada = Field(repr=False)

    @model_validator(mode='after')
    def colecoes(self):
        if {c.categoria for c in self.catalogos} != set(CATEGORIAS):
            raise ValueError('CATALOGOS_OBRIGATORIOS_INCOMPLETOS')
        if len({c.id for c in self.catalogos}) != len(self.catalogos):
            raise ValueError('CATALOGO_DUPLICADO')
        if len({f.arquivo_id for f in self.fontes}) != len(self.fontes):
            raise ValueError('FONTE_DUPLICADA')
        if any(c.condominio_id != self.condominio_id for c in self.catalogos):
            raise ValueError('CATALOGO_DE_OUTRO_CONDOMINIO')
        return self


class PacotePrivado(CandidatoPacote):
    atesto: AtestoCompletude = Field(repr=False)


class ExecucaoPrivada(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    id: Id
    condominio_id: Id
    ambiente: Ambiente
    pacote_id: Id
    pacote_hash: Hash
    implementacao_hash: Hash
    estado_planos: EstadoPlanos = Field(repr=False)
    relatorio: RelatorioSimulacao = Field(repr=False)
    em: Instante
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False

    @model_validator(mode='after')
    def vinculos(self):
        from .billing_rules import hash_modelo
        solicitacao = self.relatorio.solicitacao
        if (solicitacao.condominio_id, solicitacao.ambiente) != (self.condominio_id, self.ambiente):
            raise ValueError('RELATORIO_DE_OUTRO_CONTEXTO')
        if self.relatorio.prova_plano.hash_estado != hash_modelo(self.estado_planos):
            raise ValueError('ESTADO_PLANOS_DIVERGE_DA_PROVA')
        return self


class ReproducaoHistorica(Modelo):
    modo: Literal['reproducao_historica_sem_autorizacao_atual'] = 'reproducao_historica_sem_autorizacao_atual'
    execucao_id: Id
    hash_relatorio_original: Hash
    identico: Literal[True] = True
    relatorio: RelatorioSimulacao = Field(repr=False)
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False


class ReciboPrivado(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    repositorio_id: Id
    raiz_hash: Hash
    tipo: Literal['pacote', 'execucao', 'comparacao']
    id: Id
    condominio_id: Id
    ambiente: Ambiente
    sha256: Hash
    responsavel_id: Id
    politica_autorizacao_hash: Hash
    assinatura: Hash = Field(repr=False)
