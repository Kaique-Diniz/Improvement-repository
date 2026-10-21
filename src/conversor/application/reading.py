"""Fase 3: leitura canônica. Não avalia elegibilidade, régua ou exportação."""
from pydantic import Field

from conversor.domain.base import Modelo
from conversor.domain.canonical import LoteCanonico, Ocorrencia, cpf_validado
from conversor.domain.recognition import ResultadoReconhecimento
from conversor.readers.contracts import FonteProtegida, RepositorioFontes
from conversor.readers.operational import ContextosCatalogo, RegistroLeitores
from conversor.readers.text_support import ErroLeitura, id_estavel
from .ports import Repositorio
from .recognition import _hash


class LeituraCanonica(Modelo):
    lote: LoteCanonico = Field(repr=False)
    ocorrencias: tuple[Ocorrencia, ...]


def resultado_leitura(lote: LoteCanonico, *, processamento_id: str) -> LeituraCanonica:
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    if len(pessoas) != len(lote.pessoas):
        raise ErroLeitura("TITULAR_AMBIGUO")
    alertas = tuple(Ocorrencia(id=id_estavel("oc_cpf", processamento_id, p.unidade_id),
        processamento_id=processamento_id, codigo="CPF_AUSENTE_OU_INVALIDO", gravidade="alerta", escopo="registro",
        registro_id=p.unidade_id, origem=p.origem) for p in lote.pessoas if not cpf_validado(p.documento))
    return LeituraCanonica(lote=lote, ocorrencias=alertas)


class LerDocumento:
    def __init__(self, repositorio: Repositorio, fontes: RepositorioFontes):
        self.repositorio, self.fontes = repositorio, fontes

    def executar(self, fonte: FonteProtegida, reconhecimento: ResultadoReconhecimento, *, processamento_id: str):
        r = ResultadoReconhecimento.model_validate(reconhecimento.model_dump())
        if r.bloqueante or not r.pronto_para_proxima_etapa or r.selecao is None:
            raise ErroLeitura("RECONHECIMENTO_BLOQUEIA_LEITURA")
        if r.tipo != "pdf_texto":
            raise ErroLeitura("TIPO_NAO_SUPORTADO_PELO_LEITOR")
        if (r.arquivo_id, r.arquivo_hash) != (fonte.arquivo_id, fonte.sha256):
            raise ErroLeitura("FONTE_DIFERE_DO_RECONHECIMENTO")
        estado = self.repositorio.carregar()
        if estado.revisao != r.catalogo_revisao or _hash(estado.catalogo) != r.catalogo_hash:
            raise ErroLeitura("CATALOGO_DIFERE_DO_RECONHECIMENTO")
        formato = next((f for f in estado.catalogo.formatos if f.id == r.selecao.versoes.formato_id), None)
        if formato is None or formato.status != "validado":
            raise ErroLeitura("FORMATO_NAO_HOMOLOGADO")
        contextos = ContextosCatalogo(estado.catalogo, r.data_ref)
        contexto = contextos.resolver(fonte, formato_id=formato.id, condominio_id=r.selecao.condominio_id)
        if contexto.administradora_id != r.selecao.versoes.administradora_id:
            raise ErroLeitura("IDENTIDADE_DIFERE_DO_RECONHECIMENTO")
        leitor = RegistroLeitores(self.fontes, contextos).obter(formato.leitor_id, formato.versao)
        lote = leitor.ler(fonte, formato_id=formato.id, condominio_id=r.selecao.condominio_id)
        return resultado_leitura(lote, processamento_id=processamento_id)
