"""Contratos; não extrai documentos, reconcilia boletos ou aplica réguas."""
from datetime import date
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Data, Dinheiro, Hash, Id, Modelo, Texto


class Origem(Modelo):
    arquivo_id: Id
    sha256: Hash
    leitor_versao: Texto
    pagina: Annotated[int, Field(strict=True, ge=1)] | None = None
    linha: Annotated[int, Field(strict=True, ge=1)] | None = None
    identificador: Id
    data_fonte: Data | None = None
    continuacao_de: Id | None = None


class Gravidade(StrEnum):
    INFORMATIVO = "informativo"
    ALERTA = "alerta"
    CRITICO = "critico"


class Ocorrencia(Modelo):
    id: Id
    processamento_id: Id
    codigo: Id
    gravidade: Gravidade
    escopo: Literal["registro", "arquivo", "processamento"]
    registro_id: Id | None = None
    origem: Origem | None = None

    @property
    def bloqueante(self) -> bool:
        return self.gravidade == Gravidade.CRITICO


class Telefone(Modelo):
    ddd: Annotated[str, Field(pattern=r"^\d{2}$")] = Field(repr=False)
    numero: Annotated[str, Field(pattern=r"^\d{8,9}$")] = Field(repr=False)


class Endereco(Modelo):
    logradouro: str = Field(default="", repr=False)
    numero: str = Field(default="", repr=False)
    complemento: str = Field(default="", repr=False)
    cep: Annotated[str, Field(pattern=r"^(\d{8})?$")] = Field(default="", repr=False)
    bairro: str = Field(default="", repr=False)
    cidade: str = ""
    uf: Annotated[str, Field(pattern=r"^([A-Z]{2})?$")] = ""


class Contato(Modelo):
    telefones: Annotated[tuple[Telefone, ...], Field(max_length=5)] = Field(default=(), repr=False)
    emails: Annotated[tuple[str, ...], Field(max_length=3)] = Field(default=(), repr=False)
    endereco: Endereco = Field(default_factory=Endereco, repr=False)
    origem: Origem | None = None


class Documento(Modelo):
    tipo: Literal["cpf", "cnpj", "outro"]
    valor: str = Field(repr=False)


def cpf_validado(documento: Documento | None) -> str:
    if documento is None or documento.tipo != "cpf":
        return ""
    if not re.fullmatch(r"[0-9.\-\s]+", documento.valor):
        return ""
    cpf = re.sub(r"\D", "", documento.valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return ""
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return ""
    return cpf


class Pessoa(Modelo):
    id: Id
    unidade_id: Id
    nome: str = Field(repr=False)
    documento: Documento | None = Field(default=None, repr=False)
    contato: Contato = Field(default_factory=Contato, repr=False)
    relacao_unidade: Texto
    origem: Origem


class Unidade(Modelo):
    id: Id
    condominio_id: Id
    administradora_id: Id
    bloco_original: str = Field(repr=False)
    unidade_original: Texto = Field(repr=False)
    chave_normalizada: Texto = Field(repr=False)
    normalizador_versao: Texto
    origem: Origem


class ItemComposicao(Modelo):
    codigo: Id
    valor: Dinheiro
    origem: Origem


class Composicao(Modelo):
    itens: Annotated[tuple[ItemComposicao, ...], Field(min_length=1)]
    total_original: Dinheiro

    @model_validator(mode="after")
    def reconciliar(self):
        if len({item.codigo for item in self.itens}) != len(self.itens):
            raise ValueError("ITEM_COMPOSICAO_DUPLICADO")
        if sum((item.valor for item in self.itens), Decimal("0.00")) != self.total_original:
            raise ValueError("SOMA_COMPOSICAO_INCONSISTENTE")
        return self


class Apontamento(Modelo):
    codigo_original: Texto
    namespace_formato: Id
    origem: Origem


class Boleto(Modelo):
    id: Id
    condominio_id: Id
    unidade_id: Id
    identificador: Id  # identidade estável fornecida pelo futuro leitor; não é número de página
    vencimento: Data
    competencia: Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
    emissao: Data | None = None
    composicao: Composicao
    multa: Dinheiro | None = None
    juros: Dinheiro | None = None
    correcao: Dinheiro | None = None
    saldo_acumulado: Dinheiro | None = None
    apontamentos: tuple[Apontamento, ...] = ()
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]

    @property
    def chave_idempotencia(self) -> str:
        dados = [self.condominio_id, self.unidade_id, self.identificador]
        return sha256(json.dumps(dados, separators=(",", ":")).encode()).hexdigest()


class ResultadoCobranca(Modelo):
    processamento_id: Id
    unidade_id: Id
    boleto_id: Id | None = None
    acao: Literal["incluir", "excluir", "adiar", "alertar", "bloquear", "pendente"]
    regra_id: Id
    regra_versao: Texto
    motivo_codigo: Id
    origens: Annotated[tuple[Origem, ...], Field(min_length=1)]
    ocorrencias: tuple[Ocorrencia, ...] = ()

    @model_validator(mode="after")
    def coerencia(self):
        if any(o.processamento_id != self.processamento_id for o in self.ocorrencias):
            raise ValueError("OCORRENCIA_DE_OUTRA_EXECUCAO")
        if self.acao == "incluir" and any(o.bloqueante for o in self.ocorrencias):
            raise ValueError("RESULTADO_COM_BLOQUEIO_NAO_PODE_INCLUIR")
        return self


class LoteCanonico(Modelo):
    unidades: tuple[Unidade, ...]
    boletos: tuple[Boleto, ...]
    pessoas: tuple[Pessoa, ...] = ()

    @model_validator(mode="after")
    def integridade(self):
        unidades = {u.id: u for u in self.unidades}
        if len(unidades) != len(self.unidades):
            raise ValueError("UNIDADE_DUPLICADA")
        chaves = [(u.condominio_id, u.bloco_original, u.chave_normalizada) for u in self.unidades]
        if len(set(chaves)) != len(chaves):
            raise ValueError("UNIDADE_AMBIGUA")
        if len({p.id for p in self.pessoas}) != len(self.pessoas):
            raise ValueError("PESSOA_DUPLICADA")
        if any(p.unidade_id not in unidades for p in self.pessoas):
            raise ValueError("PESSOA_SEM_UNIDADE")
        if len({b.id for b in self.boletos}) != len(self.boletos):
            raise ValueError("BOLETO_DUPLICADO")
        if len({b.chave_idempotencia for b in self.boletos}) != len(self.boletos):
            raise ValueError("DUPLICIDADE_NAO_RECONCILIADA")
        for boleto in self.boletos:
            unidade = unidades.get(boleto.unidade_id)
            if unidade is None or unidade.condominio_id != boleto.condominio_id:
                raise ValueError("BOLETO_SEM_UNIDADE_COMPATIVEL")
        return self
