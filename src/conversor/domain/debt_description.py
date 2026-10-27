"""Contratos de interpretação descritiva; não autorizam nem calculam cobranças."""
from typing import Annotated, Literal
import re

from pydantic import Field, model_validator

from .base import Dinheiro, Hash, Id, Modelo, Texto
from .canonical import Origem

Competencia = Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class RegraHistorico(Modelo):
    id: Id
    padrao: Texto
    papel: Literal['principal', 'acessorio', 'ajuste']
    natureza: Id | None = None
    rotulo: Texto | None = None
    natureza_competencia: bool = False
    naturezas_compativeis: tuple[Id, ...] = ()

    @model_validator(mode='after')
    def coerencia(self):
        try:
            regex = re.compile(self.padrao)
        except re.error:
            raise ValueError('PADRAO_DE_HISTORICO_INVALIDO') from None
        if self.papel == 'principal':
            if not self.natureza or not self.rotulo:
                raise ValueError('NATUREZA_PRINCIPAL_EXIGE_ROTULO')
        elif not self.naturezas_compativeis:
            raise ValueError('COMPONENTE_ACESSORIO_EXIGE_CONTEXTO')
        elif self.natureza or self.rotulo or self.natureza_competencia or regex.groupindex:
            raise ValueError('ACESSORIO_NAO_DEFINE_NATUREZA_OU_COMPETENCIA')
        if ('mes' in regex.groupindex) != ('ano' in regex.groupindex):
            raise ValueError('COMPETENCIA_EXIGE_MES_E_ANO')
        return self


class PoliticaDescricoes(Modelo):
    id: Id
    versao: Texto
    namespace_formato: Id
    regras: Annotated[tuple[RegraHistorico, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def integridade(self):
        if len({r.id for r in self.regras}) != len(self.regras):
            raise ValueError('REGRA_DESCRICAO_DUPLICADA')
        rotulos = {}
        for r in self.regras:
            if r.papel == 'principal':
                valor = (r.rotulo, r.natureza_competencia)
                if r.natureza in rotulos and rotulos[r.natureza] != valor:
                    raise ValueError('ROTULOS_DE_NATUREZA_CONFLITANTES')
                rotulos[r.natureza] = valor
        return self


class ComponenteInterpretado(Modelo):
    codigo: Id
    historico_original: str = Field(repr=False)
    valor_original: Dinheiro
    origem: Origem
    origem_historico: Origem
    aba: str | None = None
    conta: str | None = None
    origem_conta: Origem | None = None
    resultado: Literal['reconhecido', 'nao_reconhecido', 'ambiguo']
    regras_candidatas: tuple[Id, ...] = ()
    papel: Literal['principal', 'acessorio', 'ajuste'] | None = None
    natureza: Id | None = None
    competencia: Competencia | None = None


class DescricaoRecibo(Modelo):
    condominio_id: Id
    unidade_id: Id
    boleto_id: Id
    identificador_origem: Id
    descricao: Texto
    estado: Literal['comprovada', 'pendente']
    classificacao: Id
    competencia: Competencia | None = None
    estado_competencia: Literal['comprovada', 'ausente', 'conflitante', 'nao_aplicavel']
    competencias_encontradas: tuple[Competencia, ...] = ()
    ambigua: bool
    justificativa: Texto
    alertas: tuple[Id, ...] = ()
    politica_id: Id
    politica_versao: Texto
    politica_sha256: Hash
    componentes: tuple[ComponenteInterpretado, ...] = Field(repr=False)
    origens: tuple[Origem, ...]
