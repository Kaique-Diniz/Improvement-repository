"""Vínculo de destino independente do processamento e da identidade pessoal."""
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import Field, model_validator

from .base import Data, Hash, Modelo, Texto, Id, com_fuso
from .billing_rules import bytes_canonicos
from .canonical import Origem
from .recognition import normalizar_assinatura


def hash_dados(valor):
    return sha256(bytes_canonicos(valor)).hexdigest()


class IdentidadeOrigem(Modelo):
    administradora_id: Id
    empreendimento: Texto
    codigo_original: Texto
    bloco_literal: Texto
    unidade_literal: Texto

    @property
    def codigo_normalizado(self):
        return str(int(self.codigo_original)) if self.codigo_original.isascii() and self.codigo_original.isdigit() else self.codigo_original

    @property
    def id(self):
        # Não depende de unidade_id, arquivo, data, recibo ou destino.
        return hash_dados([self.administradora_id, normalizar_assinatura(self.empreendimento),
            self.codigo_normalizado, self.bloco_literal, self.unidade_literal])


class EvidenciaVinculo(Modelo):
    papel: Literal['financeiro', 'referencia', 'cadastro', 'confronto']
    origem: Origem
    conciliacao_sha256: Hash


class PendenciaDocumental(Modelo):
    id: Hash
    codigo: Literal['DOCUMENTOS_VALIDOS_CONFLITANTES'] = 'DOCUMENTOS_VALIDOS_CONFLITANTES'
    documentos_hmac: tuple[Hash, ...] = Field(min_length=2)
    evidencias: tuple[EvidenciaVinculo, ...] = Field(min_length=1)
    estado: Literal['pendente'] = 'pendente'
    # Sem liberação automática; resolução exige nova comprovação humana futura.


class AprovacaoVinculo(Modelo):
    responsavel: Texto
    sessao_sha256: Hash
    aprovado_em: datetime
    fundamento: Texto
    conteudo_aprovado_sha256: Hash

    @model_validator(mode='after')
    def horario(self):
        com_fuso(self.aprovado_em)
        return self


class VinculoDocumental(Modelo):
    versao_contrato: Literal['1.0'] = '1.0'
    id: Hash
    identidade: IdentidadeOrigem
    codigos_observados: tuple[Texto, ...]
    condominio_destino_id: Id
    codigo_destino: Texto
    versao: int = Field(strict=True, ge=1)
    estado: Literal['candidato', 'aprovado', 'pendente', 'conflitante', 'revogado', 'recusado']
    nome_financeiro_hmac: Hash
    perfil_versao: Texto
    perfil_sha256: Hash
    evidencias: tuple[EvidenciaVinculo, ...] = Field(min_length=2)
    recibos_historicos: tuple[Id, ...] = Field(min_length=1)
    pendencias_documentais: tuple[PendenciaDocumental, ...] = ()
    aprovacao: AprovacaoVinculo | None = None
    registrado_em: datetime
    atualizado_em: datetime
    revalidar_ate: Data | None = None
    condicao_revalidacao: Literal['mudanca_identidade_perfil_ou_evidencia'] = 'mudanca_identidade_perfil_ou_evidencia'
    motivo: Texto

    @model_validator(mode='after')
    def integro(self):
        if self.id != self.identidade.id:
            raise ValueError('CHAVE_DE_VINCULO_INCOMPATIVEL')
        com_fuso(self.registrado_em); com_fuso(self.atualizado_em)
        if self.atualizado_em < self.registrado_em:
            raise ValueError('HORARIO_DE_VINCULO_INCONSISTENTE')
        if not {'financeiro', 'referencia'} <= {e.papel for e in self.evidencias}:
            raise ValueError('COMPROVACAO_ORIGINAL_INCOMPLETA')
        if self.estado == 'aprovado' and self.aprovacao is None:
            raise ValueError('VINCULO_SEM_APROVACAO')
        return self


class EventoVinculo(Modelo):
    sequencia: int = Field(strict=True, ge=1)
    acao: Literal['candidatar', 'aprovar', 'recusar', 'revogar', 'reabrir', 'revisar', 'reter_documento']
    registro: VinculoDocumental
    responsavel: Texto
    sessao_sha256: Hash
    fundamento: Texto
    anterior_sha256: Hash
    assinatura: Hash = Field(repr=False)


class AcervoVinculos(Modelo):
    versao_contrato: Literal['1.0'] = '1.0'
    eventos: tuple[EventoVinculo, ...] = ()

    @property
    def atuais(self):
        return {e.registro.id: e.registro for e in self.eventos}


class SnapshotVinculos(Modelo):
    revisao: int = Field(strict=True, ge=0)
    sha256: Hash
    acervo: AcervoVinculos

    @property
    def registros(self):
        return self.acervo.atuais
