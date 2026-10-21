"""Entrada e relatório de simulação. Reutiliza planos/valores do contrato 4.1."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Data, Hash, Id, Modelo
from .billing_rules import Ambiente, Condicao, ValorFato
from .canonical import LoteCanonico, Ocorrencia, Origem, RessalvaLeitura

Verdade = Literal['verdadeiro', 'falso', 'indeterminado']
SituacaoSimulada = Literal['elegivel_na_simulacao', 'excluido', 'bloqueado', 'pendente_revisao']
AcaoRegra = Literal['incluir', 'excluir', 'adiar', 'alertar', 'bloquear']


class FatoEvidenciado(Modelo):
    id: Id
    fato_id: Id
    condominio_id: Id
    unidade_id: Id
    boleto_id: Id | None = None
    valor: ValorFato = Field(repr=False)
    vigente_de: Data
    vigente_ate: Data | None = None
    confirmacao: Literal['comprovado', 'nao_confirmado']
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def intervalo(self):
        if self.vigente_ate is not None and self.vigente_ate <= self.vigente_de:
            raise ValueError('VIGENCIA_DO_FATO_INVALIDA')
        return self


class CoberturaApontamentos(Modelo):
    """Evidência explícita de completude de um campo/namespace, não um default."""
    boleto_id: Id
    namespace: Id
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]


class EntradaSimulacao(Modelo):
    lote: LoteCanonico = Field(repr=False)
    fatos: tuple[FatoEvidenciado, ...] = Field(repr=False)
    ocorrencias_anteriores: tuple[Ocorrencia, ...] = Field(repr=False)
    coberturas_apontamentos: tuple[CoberturaApontamentos, ...] = Field(repr=False)

    @model_validator(mode='after')
    def unicos(self):
        if len({f.id for f in self.fatos}) != len(self.fatos):
            raise ValueError('FATO_ID_DUPLICADO')
        if len({o.id for o in self.ocorrencias_anteriores}) != len(self.ocorrencias_anteriores):
            raise ValueError('OCORRENCIA_ID_DUPLICADA')
        if len({(c.boleto_id,c.namespace) for c in self.coberturas_apontamentos}) != len(self.coberturas_apontamentos):
            raise ValueError('COBERTURA_DUPLICADA')
        return self


class SolicitacaoSimulacao(Modelo):
    processamento_id: Id
    condominio_id: Id
    plano_id: Id
    plano_versao: str
    plano_hash: Hash
    ambiente: Ambiente
    data_ref: Data


class PassoCondicao(Modelo):
    caminho: str
    tipo: str
    resultado: Verdade
    motivo_codigo: Id
    boleto_id: Id | None = None
    observados: tuple[ValorFato, ...] = Field(default=(), repr=False)
    fatos_ids: tuple[Id, ...] = ()
    origens: tuple[Origem, ...] = ()
    filhos: tuple['PassoCondicao', ...] = ()


class AvaliacaoRegra(Modelo):
    regra_id: Id
    plano_versao: str
    prioridade: int
    alvo: Literal['unidade','boleto']
    unidade_id: Id
    boleto_id: Id | None
    acao: AcaoRegra
    motivo_codigo: Id
    fonte_regra: Origem
    condicao: Condicao = Field(repr=False)
    passo: PassoCondicao = Field(repr=False)


class DecisaoBoletoSimulada(Modelo):
    unidade_id: Id
    boleto_id: Id
    situacao: SituacaoSimulada
    motivo_codigo: Id
    motivo_regras: Id
    revisao_humana: bool
    regras_decisivas: tuple[Id, ...]
    avaliacoes: tuple[AvaliacaoRegra, ...] = Field(repr=False)
    ocorrencias_preservadas: tuple[Ocorrencia, ...] = Field(repr=False)
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]


class DecisaoUnidadeSimulada(Modelo):
    unidade_id: Id
    situacao: SituacaoSimulada
    motivo_codigo: Id
    avaliacoes: tuple[AvaliacaoRegra, ...] = Field(repr=False)
    boletos_ids: tuple[Id, ...]
    origens: tuple[Origem, ...]


class ProvaPlanoSimulado(Modelo):
    revisao_repositorio: int = Field(strict=True, ge=1)
    hash_estado: Hash
    aprovacao_sequencia: int = Field(strict=True, ge=1)
    aprovacao_hash: Hash
    ativacao_sequencia: int = Field(strict=True, ge=1)
    ativacao_hash: Hash


class RelatorioSimulacao(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    motor_versao: Literal['4.2.0'] = '4.2.0'
    modo: Literal['somente_simulacao'] = 'somente_simulacao'
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False
    solicitacao: SolicitacaoSimulacao
    prova_plano: ProvaPlanoSimulado
    hash_entrada: Hash
    unidades: tuple[DecisaoUnidadeSimulada, ...] = Field(repr=False)
    boletos: tuple[DecisaoBoletoSimulada, ...] = Field(repr=False)
    ocorrencias_anteriores: tuple[Ocorrencia, ...] = Field(repr=False)
    ressalvas_origem: tuple[RessalvaLeitura, ...] = Field(repr=False)
    fatos_recebidos: tuple[FatoEvidenciado, ...] = Field(repr=False)
    coberturas_recebidas: tuple[CoberturaApontamentos, ...] = Field(repr=False)
