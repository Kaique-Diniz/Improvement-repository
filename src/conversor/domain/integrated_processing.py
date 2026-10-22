"""Contratos aditivos 4.3B.2A: somente ensaios sintéticos, sem atesto humano."""
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import Hash, Id, Modelo, Texto
from .billing_rules import EstadoPlanos, Instante, hash_modelo
from .catalog import Administradora, Condominio
from .private_simulation import ReciboPrivado
from .synthetic_processing import ProjecaoProcessamentoSintetico, SolicitacaoProcessamentoSintetico


class DocumentoReguaSintetica(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    natureza: Literal['sintetico']
    id: Id
    versao: Texto
    condominio_id: Id
    regra_ids: tuple[Id, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def regras_unicas(self):
        if len(set(self.regra_ids)) != len(self.regra_ids):
            raise ValueError('REGRA_DUPLICADA_NA_FONTE_SINTETICA')
        return self


class ReferenciaReguaSintetica(Modelo):
    arquivo_id: Id
    versao: Texto
    sha256: Hash


class PedidoProcessamentoIntegrado(SolicitacaoProcessamentoSintetico):
    preparacao_id: Id
    preparacao_hash: Hash
    administradora_id: Id
    regua: ReferenciaReguaSintetica
    operador_id: Id
    em: Instante
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id

    @field_validator('fundamento')
    @classmethod
    def fundamento_explicito(cls, valor):
        if not valor.strip():
            raise ValueError('FUNDAMENTO_OPERADOR_OBRIGATORIO')
        return valor

    def solicitacao_sintetica(self):
        return SolicitacaoProcessamentoSintetico.model_validate({
            k: getattr(self, k) for k in SolicitacaoProcessamentoSintetico.model_fields})


class IdentidadeOperador(Modelo):
    responsavel_id: Id
    politica_autorizacao_hash: Hash


class AtoOperadorSintetico(IdentidadeOperador):
    funcao: Literal['operador'] = 'operador'
    acao: Literal['processar_ensaio_sintetico'] = 'processar_ensaio_sintetico'
    em: Instante
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id


class ExecucaoIntegradaSintetica(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    versao_fluxo: Literal['4.3B.2A'] = '4.3B.2A'
    id: Id
    condominio_id: Id
    ambiente: Literal['sintetico'] = 'sintetico'
    pedido: PedidoProcessamentoIntegrado = Field(repr=False)
    administradora: Administradora = Field(repr=False)
    condominio: Condominio = Field(repr=False)
    estado_planos: EstadoPlanos = Field(repr=False)
    projecao: ProjecaoProcessamentoSintetico = Field(repr=False)
    ato: AtoOperadorSintetico
    implementacao_hash: Hash
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False
    atesto_humano_emitido: Literal[False] = False

    @model_validator(mode='after')
    def vinculos(self):
        p = self.pedido
        rel = self.projecao.relatorio_motor
        esperado = p.solicitacao_sintetica().model_dump(exclude={'modo_cadastro'})
        if (self.id != p.processamento_id or self.condominio_id != p.condominio_id
                or rel.solicitacao.model_dump() != esperado
                or self.projecao.modo_cadastro != p.modo_cadastro):
            raise ValueError('EXECUCAO_INTEGRADA_DE_OUTRO_PEDIDO')
        if (self.administradora.id != p.administradora_id or self.condominio.id != p.condominio_id
                or self.condominio.administradora_id != p.administradora_id
                or not self.administradora.ativo or not self.condominio.ativo):
            raise ValueError('VINCULO_ADMINISTRADORA_CONDOMINIO_INVALIDO')
        if self.estado_planos.acervo.ambiente != 'sintetico':
            raise ValueError('ESTADO_INTEGRADO_NAO_SINTETICO')
        if rel.prova_plano.hash_estado != hash_modelo(self.estado_planos):
            raise ValueError('ESTADO_INTEGRADO_DIVERGE_DA_PROVA')
        if (self.ato.responsavel_id, self.ato.em, self.ato.evidencia_id, self.ato.fundamento) != (
                p.operador_id, p.em, p.evidencia_id, p.fundamento):
            raise ValueError('ATO_INTEGRADO_DIVERGE_DO_PEDIDO')
        return self


class ReproducaoIntegradaSintetica(Modelo):
    modo: Literal['historico_sintetico_sem_autorizacao_atual'] = 'historico_sintetico_sem_autorizacao_atual'
    execucao_id: Id
    hash_execucao: Hash
    projecao: ProjecaoProcessamentoSintetico = Field(repr=False)
    identico: Literal[True] = True
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False


class ReciboProcessamentoSintetico(ReciboPrivado):
    tipo: Literal['processamento_sintetico'] = 'processamento_sintetico'
    ambiente: Literal['sintetico'] = 'sintetico'
