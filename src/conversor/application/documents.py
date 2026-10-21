"""Ocorrências estruturadas; valores documentais ficam apenas na auditoria protegida."""
from hashlib import sha256

from conversor.domain.canonical import Ocorrencia, Pessoa
from conversor.domain.documents import resolver_documento


def ocorrencias_documentais(pessoa: Pessoa, *, processamento_id: str) -> tuple[Ocorrencia, ...]:
    resolucao = resolver_documento(pessoa)
    return tuple(Ocorrencia(
        id="documento:" + sha256(f"{processamento_id}:{pessoa.unidade_id}:{codigo}".encode()).hexdigest(),
        processamento_id=processamento_id, codigo=codigo,
        gravidade="critico" if codigo in ("DOCUMENTOS_CONFLITANTES", "DOCUMENTO_TITULAR_NAO_CONFIRMADO") else "alerta",
        escopo="registro", registro_id=pessoa.unidade_id, origem=pessoa.documento_origem or pessoa.origem,
        evidencias_documentais=resolucao.evidencias,
    ) for codigo in resolucao.codigos)
