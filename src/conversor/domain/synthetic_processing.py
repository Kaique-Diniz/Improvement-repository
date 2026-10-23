"""Decisões A/B somente para simulação sintética; não são linhas de Excel."""
from typing import Literal

from pydantic import Field, model_validator

from .base import Hash, Id, Modelo
from .billing_evaluation import RelatorioSimulacao, SolicitacaoSimulacao
from .billing_rules import hash_modelo
from .canonical import Origem


class SolicitacaoProcessamentoSintetico(SolicitacaoSimulacao):
    ambiente: Literal['sintetico']
    modo_cadastro: Literal['A', 'B']  # Obrigatório, sem default silencioso.


class CandidatoCadastroSimulado(Modelo):
    unidade_id: Id
    tipo: Literal['somente_cadastral'] = 'somente_cadastral'
    divida: Literal[None] = None
    boletos_nao_elegiveis: tuple[Id, ...] = Field(min_length=1)
    motivo_codigo: Literal['UNIDADE_COM_COTA_EXCLUIDA_NA_SIMULACAO'] = 'UNIDADE_COM_COTA_EXCLUIDA_NA_SIMULACAO'
    origens: tuple[Origem, ...] = Field(min_length=1)


class RetencaoCadastroSimulado(Modelo):
    unidade_id: Id
    motivo_codigo: Literal['UNIDADE_COM_BLOQUEIO_OU_REVISAO']
    boletos_retidos: tuple[Id, ...] = Field(min_length=1)


class ProjecaoProcessamentoSintetico(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    versao_projecao: Literal['4.3B.1'] = '4.3B.1'
    modo_cadastro: Literal['A', 'B']
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False
    relatorio_motor: RelatorioSimulacao = Field(repr=False)
    hash_relatorio_motor: Hash
    boletos_divida: tuple[Id, ...]
    candidatos_cadastrais: tuple[CandidatoCadastroSimulado, ...]
    retencoes_cadastrais: tuple[RetencaoCadastroSimulado, ...]

    @model_validator(mode='after')
    def integridade_da_projecao(self):
        rel = self.relatorio_motor
        if rel.solicitacao.ambiente != 'sintetico':
            raise ValueError('PROJECAO_SOMENTE_SINTETICA')
        if self.hash_relatorio_motor != hash_modelo(rel):
            raise ValueError('HASH_RELATORIO_DA_PROJECAO_DIVERGENTE')
        esperados = tuple(d.boleto_id for d in rel.boletos if d.situacao == 'elegivel_na_simulacao')
        if self.boletos_divida != esperados:
            raise ValueError('DIVIDAS_DA_PROJECAO_DIVERGENTES')
        if self.modo_cadastro == 'A' and (self.candidatos_cadastrais or self.retencoes_cadastrais):
            raise ValueError('MODO_A_NAO_PROJETA_CADASTRO')
        ids = [c.unidade_id for c in self.candidatos_cadastrais]
        if len(set(ids)) != len(ids):
            raise ValueError('CADASTRO_ADICIONAL_DUPLICADO')
        for c in self.candidatos_cadastrais:
            ds = [d for d in rel.boletos if d.unidade_id == c.unidade_id]
            if any(d.situacao in ('bloqueado', 'pendente_revisao') for d in ds):
                raise ValueError('CADASTRO_NAO_CONTORNA_RETENCAO')
            excluidos = tuple(d.boleto_id for d in ds if d.situacao == 'excluido')
            if not excluidos or c.boletos_nao_elegiveis != excluidos:
                raise ValueError('CADASTRO_SEM_COTAS_EXCLUIDAS_COMPROVADAS')
        return self

    @property
    def hash_auditoria(self) -> str:
        """Inclui modo A/B e versão da projeção, além da prova/hash do plano no relatório."""
        return hash_modelo(self)
