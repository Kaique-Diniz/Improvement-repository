"""Resolução documental, independente de cobrança e de persistência."""
from pydantic import Field

from .base import Modelo
from .canonical import EvidenciaDocumento, Pessoa, documento_validado


class ResolucaoDocumento(Modelo):
    valor: str = Field(pattern=r"^(?:[0-9]{11}|[0-9]{14})?$", repr=False,
                       description="Documento normalizado para a coluna literal CPF: texto de 11 ou 14 dígitos, ou vazio.")
    codigos: tuple[str, ...]
    bloqueante: bool
    evidencias: tuple[EvidenciaDocumento, ...] = Field(repr=False)


def evidencias_documento(pessoa: Pessoa) -> tuple[EvidenciaDocumento, ...]:
    fontes = list(pessoa.evidencias_documentais)
    if pessoa.documento is not None:
        principal = EvidenciaDocumento(documento=pessoa.documento, origem=pessoa.documento_origem or pessoa.origem,
                                      titular_id=pessoa.id)
        if principal not in fontes:
            fontes.append(principal)
    return tuple(fontes)


def resolver_documento(pessoa: Pessoa) -> ResolucaoDocumento:
    fontes = evidencias_documento(pessoa)
    validos = [(f, documento_validado(f.documento)) for f in fontes]
    unicos = {(f.documento.tipo, valor) for f, valor in validos if valor}
    codigos = []
    if not fontes:
        codigos.append("DOCUMENTO_AUSENTE")
    if any(not valor for _, valor in validos):
        codigos.append("DOCUMENTO_INVALIDO")
    conflito = len(unicos) > 1
    associacao_pendente = any(valor and f.titular_id != pessoa.id for f, valor in validos)
    if conflito:
        codigos.append("DOCUMENTOS_CONFLITANTES")
    if associacao_pendente:
        codigos.append("DOCUMENTO_TITULAR_NAO_CONFIRMADO")
    bloqueante = conflito or associacao_pendente
    valor = next(iter(unicos))[1] if len(unicos) == 1 and not bloqueante else ""
    return ResolucaoDocumento(valor=valor, codigos=tuple(codigos), bloqueante=bloqueante, evidencias=fontes)
