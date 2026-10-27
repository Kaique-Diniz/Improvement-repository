"""Fase 3: leitura canônica. Não avalia elegibilidade, régua ou exportação."""
from pydantic import Field

from conversor.domain.base import Modelo
from conversor.domain.canonical import LoteCanonico, Ocorrencia
from .documents import ocorrencias_documentais
from conversor.domain.recognition import ResultadoReconhecimento
from conversor.readers.contracts import FonteProtegida, RepositorioFontes
from conversor.readers.operational import ContextosCatalogo, RegistroLeitores
from conversor.readers.text_support import ErroLeitura
from conversor.readers.text_support import id_estavel
from .ports import Repositorio
from .recognition_ports import RepositorioAssinaturas
from .recognition import _hash


class LeituraCanonica(Modelo):
    lote: LoteCanonico = Field(repr=False)
    ocorrencias: tuple[Ocorrencia, ...]

    @property
    def bloqueante(self) -> bool:
        return any(o.bloqueante for o in self.ocorrencias)


def resultado_leitura(lote: LoteCanonico, *, processamento_id: str) -> LeituraCanonica:
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    if len(pessoas) != len(lote.pessoas):
        raise ErroLeitura("TITULAR_AMBIGUO")
    alertas = tuple(o for p in lote.pessoas for o in ocorrencias_documentais(p, processamento_id=processamento_id))
    alertas += tuple(Ocorrencia(id=id_estavel("oc_leitura", processamento_id, i, r.codigo),
        processamento_id=processamento_id, codigo=r.codigo, gravidade=r.gravidade,
        escopo="registro" if r.registro_id else "arquivo", registro_id=r.registro_id, origem=r.origens[0])
        for i, r in enumerate(lote.ressalvas))
    return LeituraCanonica(lote=lote, ocorrencias=alertas)


class LerDocumento:
    def __init__(self, repositorio: Repositorio, fontes: RepositorioFontes, assinaturas: RepositorioAssinaturas):
        self.repositorio, self.fontes = repositorio, fontes
        self.assinaturas = assinaturas

    def executar(self, fonte: FonteProtegida, reconhecimento: ResultadoReconhecimento, *, processamento_id: str):
        r = ResultadoReconhecimento.model_validate(reconhecimento.model_dump())
        if r.bloqueante or not r.pronto_para_proxima_etapa or r.selecao is None:
            raise ErroLeitura("RECONHECIMENTO_BLOQUEIA_LEITURA")
        if r.tipo not in ("pdf_texto", "xlsx"):
            raise ErroLeitura("TIPO_NAO_SUPORTADO_PELO_LEITOR")
        if (r.arquivo_id, r.arquivo_hash) != (fonte.arquivo_id, fonte.sha256):
            raise ErroLeitura("FONTE_DIFERE_DO_RECONHECIMENTO")
        estado = self.repositorio.carregar()
        if estado.revisao != r.catalogo_revisao or _hash(estado.catalogo) != r.catalogo_hash:
            raise ErroLeitura("CATALOGO_DIFERE_DO_RECONHECIMENTO")
        assinaturas = self.assinaturas.carregar()
        if _hash(assinaturas) != r.assinaturas_hash or assinaturas.versao != r.assinaturas_versao:
            raise ErroLeitura("ASSINATURAS_DIFEREM_DO_RECONHECIMENTO")
        formato = next((f for f in estado.catalogo.formatos if f.id == r.selecao.versoes.formato_id), None)
        if formato is None or formato.status != "validado":
            raise ErroLeitura("FORMATO_NAO_HOMOLOGADO")
        if formato.tipo_arquivo != r.tipo:
            raise ErroLeitura('TIPO_NAO_SUPORTADO_PELO_LEITOR')
        contextos = ContextosCatalogo(estado.catalogo, r.data_ref)
        contexto = contextos.resolver(fonte, formato_id=formato.id, condominio_id=r.selecao.condominio_id)
        if contexto.administradora_id != r.selecao.versoes.administradora_id:
            raise ErroLeitura("IDENTIDADE_DIFERE_DO_RECONHECIMENTO")
        leitor = RegistroLeitores(self.fontes, contextos).obter(formato.leitor_id, formato.versao)
        lote = leitor.ler(fonte, formato_id=formato.id, condominio_id=r.selecao.condominio_id)
        return resultado_leitura(lote, processamento_id=processamento_id)
