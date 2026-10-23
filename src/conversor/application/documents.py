"""Ocorrências estruturadas; valores documentais ficam apenas na auditoria protegida."""
from hashlib import sha256

from conversor.domain.canonical import Ocorrencia, Pessoa
from conversor.domain.documents import resolver_documento
from conversor.domain.billing_rules import bytes_canonicos


def id_documental_legado(*, processamento_id: str, unidade_id: str, codigo: str) -> str:
    """Identificação v1 preservada para rastreamento; não usar para novas ocorrências."""
    return 'documento:' + sha256(f'{processamento_id}:{unidade_id}:{codigo}'.encode()).hexdigest()


def ocorrencias_documentais(pessoa: Pessoa, *, processamento_id: str) -> tuple[Ocorrencia, ...]:
    resolucao = resolver_documento(pessoa)
    ocorrencias = []
    for codigo in resolucao.codigos:
        legado = Ocorrencia(
            id=id_documental_legado(processamento_id=processamento_id, unidade_id=pessoa.unidade_id, codigo=codigo),
            processamento_id=processamento_id, codigo=codigo,
            gravidade=('critico' if codigo in ('DOCUMENTOS_CONFLITANTES', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO')
                       else 'informativo' if codigo == 'DOCUMENTO_AUSENTE' else 'alerta'),
            escopo='registro', registro_id=pessoa.unidade_id, origem=pessoa.documento_origem or pessoa.origem,
            evidencias_documentais=resolucao.evidencias)
        conteudo = {'identificacao_versao': 'documento-2.0', 'pessoa_id': pessoa.id,
                    'ocorrencia': legado.model_dump(mode='json')}
        id_ = 'documento:v2:' + sha256(bytes_canonicos(conteudo)).hexdigest()
        ocorrencias.append(legado.model_copy(update={'id': id_}))
    return tuple(ocorrencias)
