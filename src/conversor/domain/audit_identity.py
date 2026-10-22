"""Identidade de importação, sem alterar o registro histórico nem sua decisão."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Hash, Id, Modelo, Texto
from .billing_rules import Ambiente, bytes_canonicos, hash_modelo
from .canonical import Ocorrencia, Origem
from .private_simulation import (CandidatoPacote, FontePrivada, InventarioEntrada,
                                 AtestoCompletude, ReciboPrivado)


class FonteHistorico(Modelo):
    arquivo: FontePrivada
    namespace: Literal['operacional', 'documental']
    produtor_id: Id
    produtor_versao: Texto
    estrutura: Literal['lista_ocorrencias', 'casos_documentais']


class LocalizacaoHistorica(Modelo):
    arquivo_id: Id
    arquivo_sha256: Hash
    ponteiro_json: Annotated[str, Field(pattern=r'^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$')]
    namespace: Literal['operacional', 'documental']
    produtor_id: Id
    produtor_versao: Texto


def id_auditoria(localizacao, original):
    from hashlib import sha256
    dados = {'algoritmo': 'ocorrencia-importada-1.0',
             'localizacao': localizacao.model_dump(mode='json'), 'original': original.model_dump(mode='json')}
    return 'auditoria:v1:' + sha256(bytes_canonicos(dados)).hexdigest()


class VinculoOcorrencia(Modelo):
    id_interno: Id
    id_legado: Id
    hash_original: Hash
    hash_registro_bruto: Hash
    localizacao: LocalizacaoHistorica
    original: Ocorrencia = Field(repr=False)

    @model_validator(mode='after')
    def integridade(self):
        if self.id_legado != self.original.id or self.hash_original != hash_modelo(self.original):
            raise ValueError('REGISTRO_LEGADO_DIVERGE_DO_MAPEAMENTO')
        if self.id_interno != id_auditoria(self.localizacao, self.original):
            raise ValueError('IDENTIDADE_INTERNA_DE_AUDITORIA_INVALIDA')
        return self

    def para_entrada(self):
        # Projeção local: só o ID muda; o objeto original continua integral neste vínculo.
        return self.original.model_copy(update={'id': self.id_interno})


class ReconciliacaoOcorrencias(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    identificacao_versao: Literal['ocorrencia-importada-1.0'] = 'ocorrencia-importada-1.0'
    modo: Literal['reconciliacao_tecnica_sem_decisao'] = 'reconciliacao_tecnica_sem_decisao'
    id: Id
    condominio_id: Id
    ambiente: Ambiente
    fontes: Annotated[tuple[FonteHistorico, ...], Field(min_length=1)] = Field(repr=False)
    registros: tuple[VinculoOcorrencia, ...] = Field(repr=False)
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False

    @model_validator(mode='after')
    def integridade(self):
        fontes = {f.arquivo.arquivo_id: f for f in self.fontes}
        if len(fontes) != len(self.fontes):
            raise ValueError('FONTE_HISTORICA_DUPLICADA')
        if len({r.id_interno for r in self.registros}) != len(self.registros):
            raise ValueError('IDENTIDADE_INTERNA_DUPLICADA')
        locais = {(r.localizacao.arquivo_id, r.localizacao.ponteiro_json) for r in self.registros}
        if len(locais) != len(self.registros):
            raise ValueError('LOCALIZACAO_HISTORICA_DUPLICADA')
        for r in self.registros:
            f = fontes.get(r.localizacao.arquivo_id)
            if f is None or (f.arquivo.sha256, f.namespace, f.produtor_id, f.produtor_versao) != (
                    r.localizacao.arquivo_sha256, r.localizacao.namespace,
                    r.localizacao.produtor_id, r.localizacao.produtor_versao):
                raise ValueError('VINCULO_HISTORICO_SEM_FONTE_COMPATIVEL')
        return self

    def ocorrencias(self):
        return tuple(r.para_entrada() for r in sorted(self.registros, key=lambda r: r.id_interno))


def origem_historico(fonte):
    return Origem(arquivo_id=fonte.arquivo.arquivo_id, sha256=fonte.arquivo.sha256,
        leitor_versao=fonte.produtor_versao, identificador='historico:' + fonte.arquivo.arquivo_id)


class InventarioReconciliado(InventarioEntrada):
    reconciliacao_hash: Hash


class CandidatoReconciliado(CandidatoPacote):
    schema_version: Literal['1.1'] = '1.1'
    reconciliacao: ReconciliacaoOcorrencias = Field(repr=False)
    inventario: InventarioReconciliado = Field(repr=False)


class PacoteReconciliado(CandidatoReconciliado):
    atesto: AtestoCompletude = Field(repr=False)


class ReciboReconciliacao(ReciboPrivado):
    tipo: Literal['reconciliacao'] = 'reconciliacao'


class PreparacaoTecnica(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    id: Id
    condominio_id: Id
    ambiente: Ambiente
    modo: Literal['integridade_tecnica_sem_atesto_humano'] = 'integridade_tecnica_sem_atesto_humano'
    candidato: CandidatoReconciliado = Field(repr=False)
    autoriza_cobranca: Literal[False] = False
    permite_exportacao_operacional: Literal[False] = False

    @model_validator(mode='after')
    def contexto(self):
        if (self.condominio_id, self.ambiente) != (self.candidato.condominio_id, self.candidato.ambiente):
            raise ValueError('PREPARACAO_TECNICA_DE_OUTRO_CONTEXTO')
        return self


class ReciboPreparacaoTecnica(ReciboPrivado):
    tipo: Literal['preparacao_tecnica'] = 'preparacao_tecnica'
