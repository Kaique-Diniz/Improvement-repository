"""Contratos da Fase 4.1. Não avaliam boletos nem autorizam cobranças."""
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Annotated, Literal, Union

from pydantic import BeforeValidator, Field, field_validator, model_validator

from .base import Data, Hash, Id, Modelo, Texto, com_fuso
from .canonical import Origem

Ambiente = Literal['sintetico', 'privado']  # Produção deliberadamente indisponível.
AcaoEvento = Literal['criar', 'submeter', 'rejeitar', 'aprovar', 'ativar', 'revogar']
EstadoPlano = Literal['rascunho', 'aguardando_aprovacao', 'aprovado', 'ativo', 'revogado']
TipoFato = Literal['texto', 'inteiro', 'dinheiro', 'booleano', 'data']
Monetario = Annotated[str, Field(strict=True, pattern=r'^-?(0|[1-9][0-9]*)\.[0-9]{2}$')]
Comparacao = Literal['eq', 'ne', 'gt', 'gte', 'lt', 'lte']


class ErroPlano(ValueError):
    """Código de domínio, sem conteúdo documental ou dependência de aplicação."""


def instante_explicito(valor):
    if isinstance(valor, datetime):
        return com_fuso(valor)
    if isinstance(valor, str) and re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', valor):
        return valor
    raise ValueError('INSTANTE_EXIGE_ISO_COM_FUSO')


Instante = Annotated[datetime, BeforeValidator(instante_explicito)]


def bytes_canonicos(dados) -> bytes:
    return json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def hash_modelo(modelo) -> str:
    return sha256(bytes_canonicos(modelo.model_dump(mode='json'))).hexdigest()


class ValorTexto(Modelo):
    tipo: Literal['texto']
    valor: Texto


class ValorInteiro(Modelo):
    tipo: Literal['inteiro']
    valor: int = Field(strict=True)


class ValorDinheiro(Modelo):
    tipo: Literal['dinheiro']
    valor: Monetario


class ValorBooleano(Modelo):
    tipo: Literal['booleano']
    valor: bool = Field(strict=True)


class ValorData(Modelo):
    tipo: Literal['data']
    valor: Data


ValorFato = Annotated[Union[ValorTexto, ValorInteiro, ValorDinheiro, ValorBooleano, ValorData], Field(discriminator='tipo')]


class PredicadoDias(Modelo):
    tipo: Literal['dias_atraso']
    operador: Comparacao
    valor: int = Field(strict=True)


class PredicadoValor(Modelo):
    tipo: Literal['valor_original']
    operador: Comparacao
    valor: Monetario


class PredicadoApontamento(Modelo):
    tipo: Literal['apontamento']
    codigo: Id
    namespace: Id


class PredicadoFato(Modelo):
    tipo: Literal['fato']
    fato_id: Id
    operador: Comparacao
    valor: ValorFato

    @model_validator(mode='after')
    def operador_tipado(self):
        if self.valor.tipo in ('texto', 'booleano') and self.operador not in ('eq', 'ne'):
            raise ValueError('OPERADOR_INCOMPATIVEL_COM_TIPO')
        return self


class Todas(Modelo):
    tipo: Literal['todas']
    condicoes: Annotated[tuple['Condicao', ...], Field(min_length=1, max_length=32)]


class Qualquer(Modelo):
    tipo: Literal['qualquer']
    condicoes: Annotated[tuple['Condicao', ...], Field(min_length=1, max_length=32)]


class Nao(Modelo):
    tipo: Literal['nao']
    condicao: 'Condicao'


class ExisteBoleto(Modelo):
    tipo: Literal['existe_boleto']
    condicao: 'Condicao'


class TodosBoletos(Modelo):
    tipo: Literal['todos_boletos']
    condicao: 'Condicao'


Condicao = Annotated[Union[PredicadoDias, PredicadoValor, PredicadoApontamento, PredicadoFato,
                           Todas, Qualquer, Nao, ExisteBoleto, TodosBoletos], Field(discriminator='tipo')]
for _modelo in (Todas, Qualquer, Nao, ExisteBoleto, TodosBoletos):
    _modelo.model_rebuild()


class DefinicaoFato(Modelo):
    id: Id
    tipo: TipoFato
    escopo: Literal['unidade', 'boleto']
    exige_fonte_e_vigencia: Literal[True] = True

    @field_validator('exige_fonte_e_vigencia', mode='before')
    @classmethod
    def sem_coercao(cls, valor):
        if valor is not True:
            raise ValueError('FATO_EXIGE_FONTE_E_VIGENCIA')
        return valor


class ClausulaCobranca(Modelo):
    id: Id
    prioridade: int = Field(strict=True, ge=0)
    alvo: Literal['unidade', 'boleto']
    quando: Condicao
    acao: Literal['incluir', 'excluir', 'adiar', 'alertar', 'bloquear']
    motivo_codigo: Id
    fonte_id: Id


class PoliticasCobranca(Modelo):
    prioridade: Literal['maior_numero'] = 'maior_numero'
    restricao_unidade: Literal['excluir_ou_bloquear_prevalece'] = 'excluir_ou_bloquear_prevalece'
    permissao_unidade: Literal['nao_libera_boleto_inelegivel'] = 'nao_libera_boleto_inelegivel'
    empate_incompativel: Literal['revisao_humana'] = 'revisao_humana'
    lacuna: Literal['sem_inclusao_presumida'] = 'sem_inclusao_presumida'
    bloqueios_criticos: Literal['imutaveis_e_superiores'] = 'imutaveis_e_superiores'


class PlanoCobranca(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    id: Id
    condominio_id: Id
    versao: Annotated[str, Field(pattern=r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')]
    natureza: Literal['sintetico', 'operacional']
    vigente_de: Data
    vigente_ate: Data | None = None
    fontes: Annotated[tuple[Origem, ...], Field(min_length=1)]
    fatos: tuple[DefinicaoFato, ...] = ()
    politicas: PoliticasCobranca = Field(default_factory=PoliticasCobranca)
    regras: Annotated[tuple[ClausulaCobranca, ...], Field(min_length=1, max_length=1000)]

    @model_validator(mode='after')
    def integridade(self):
        if self.vigente_ate is not None and self.vigente_ate <= self.vigente_de:
            raise ValueError('VIGENCIA_INVALIDA')
        for itens, chave in ((self.regras, 'id'), (self.fontes, 'identificador'), (self.fatos, 'id')):
            if len({getattr(i, chave) for i in itens}) != len(itens):
                raise ValueError('IDENTIFICADOR_DUPLICADO')
        fontes = {f.identificador for f in self.fontes}
        fatos = {f.id: f for f in self.fatos}
        for regra in self.regras:
            if regra.fonte_id not in fontes:
                raise ValueError('FONTE_DA_REGRA_INEXISTENTE')
            quantidade = 0
            def verificar(c, escopo, profundidade):
                nonlocal quantidade
                quantidade += 1
                if quantidade > 256 or profundidade > 16:
                    raise ValueError('CONDICAO_EXCEDE_LIMITE')
                if isinstance(c, (Todas, Qualquer)):
                    for filho in c.condicoes:
                        verificar(filho, escopo, profundidade + 1)
                elif isinstance(c, Nao):
                    verificar(c.condicao, escopo, profundidade + 1)
                elif isinstance(c, (ExisteBoleto, TodosBoletos)):
                    if escopo != 'unidade':
                        raise ValueError('QUANTIFICADOR_FORA_DA_UNIDADE')
                    verificar(c.condicao, 'boleto', profundidade + 1)
                elif isinstance(c, PredicadoFato):
                    fato = fatos.get(c.fato_id)
                    if fato is None or fato.tipo != c.valor.tipo:
                        raise ValueError('FATO_INEXISTENTE_OU_TIPO_DIVERGENTE')
                    if fato.escopo == 'boleto' and escopo != 'boleto':
                        raise ValueError('FATO_FORA_DO_ESCOPO')
                elif escopo != 'boleto':
                    raise ValueError('PREDICADO_BOLETO_EXIGE_QUANTIFICADOR')
            verificar(regra.quando, regra.alvo, 1)
        return self


class EventoPlano(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    sequencia: int = Field(strict=True, ge=1)
    ambiente: Ambiente
    plano_id: Id
    condominio_id: Id
    versao: str
    hash_conteudo: Hash
    acao: AcaoEvento
    responsavel_id: Id
    em: Instante
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id
    data_ref: Data | None = None
    hash_anterior: Hash
    politica_autorizacao_hash: Hash
    assinatura: Hash = Field(repr=False)

    _fuso = field_validator('em')(com_fuso)

    @model_validator(mode='after')
    def referencia(self):
        if (self.acao == 'ativar') != (self.data_ref is not None):
            raise ValueError('DATA_REF_EXIGIDA_SOMENTE_NA_ATIVACAO')
        if not self.fundamento.strip():
            raise ValueError('FUNDAMENTO_OBRIGATORIO')
        return self


class RegistroPlano(Modelo):
    conteudo: PlanoCobranca
    hash_conteudo: Hash
    estado: EstadoPlano


class AcervoPlanos(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    ambiente: Ambiente
    registros: tuple[RegistroPlano, ...] = ()
    eventos: tuple[EventoPlano, ...] = ()


class EstadoPlanos(Modelo):
    revisao: int = Field(strict=True, ge=0)
    acervo: AcervoPlanos


class ComandoPlano(Modelo):
    acao: AcaoEvento
    plano: PlanoCobranca | None = None
    plano_id: Id
    em: Instante
    fundamento: Texto = Field(repr=False)
    evidencia_id: Id
    data_ref: Data | None = None

    _fuso = field_validator('em')(com_fuso)

    @model_validator(mode='after')
    def completo(self):
        if (self.acao == 'criar') != (self.plano is not None):
            raise ValueError('CONTEUDO_SOMENTE_NA_CRIACAO')
        if self.plano and self.plano.id != self.plano_id:
            raise ValueError('IDENTIDADE_DO_COMANDO_DIVERGENTE')
        if (self.acao == 'ativar') != (self.data_ref is not None):
            raise ValueError('DATA_REF_EXIGIDA_SOMENTE_NA_ATIVACAO')
        if not self.fundamento.strip():
            raise ValueError('FUNDAMENTO_OBRIGATORIO')
        return self
