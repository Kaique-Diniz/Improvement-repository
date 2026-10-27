"""Adaptação das três gramáticas existentes ao protocolo Leitor; sem aprovar formatos."""
from datetime import date
from hashlib import sha256
import re

from pydantic import ValidationError

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import LoteCanonico, Unidade
from conversor.domain.catalog import Catalogo
from conversor.domain.recognition import normalizar_assinatura
from .cadastro import LeitorCadastroFLSintetico
from .contracts import FonteProtegida, RepositorioFontes, ResolutorContexto
from .fl import LeitorFLSintetico
from .habita import LeitorHabitaSintetico
from .habita_real import LeitorHabitaReal
from .fl_real import LeitorFLReal
from .cadastro_real import LeitorCadastroFLReal
from .bbz_xlsx import LeitorBBZXLSX, identificar as identificar_bbz
from .text_support import ContextoLeitura, ErroLeitura


GRAMATICAS = {
    LeitorHabitaSintetico.formato_id: (LeitorHabitaSintetico, ("Inadimplencia Atualizada", "Bloco:", "Unidade:")),
    LeitorFLSintetico.formato_id: (LeitorFLSintetico, ("Inadimplencia com composicao", "Venc.", "Comp.", "Saldo")),
    LeitorCadastroFLSintetico.formato_id: (LeitorCadastroFLSintetico, ("W045A", "Proprietario")),
    LeitorHabitaReal.formato_id: (LeitorHabitaReal, ("Inadimplencia Atualizada", "Bloco:", "Unidade:", "Emissao", "Monetaria")),
    LeitorFLReal.formato_id: (LeitorFLReal, ("Inadimplencia com composicao", "Venc.", "Comp.", "Saldo", "W002A")),
    LeitorCadastroFLReal.formato_id: (LeitorCadastroFLReal, ("W045A", "Unidade", "CPF/CNPJ")),
}

LEITORES_XLSX = {LeitorBBZXLSX.formato_id: LeitorBBZXLSX}


def validar_assinatura_para_leitura(conteudo: bytes, leitor_id: str):
    """Verificação estrutural; nunca produz classificação conhecido_validado."""
    if leitor_id in LEITORES_XLSX:
        identificar_bbz(conteudo)
        return
    sonda = SondadorLocal().sondar(conteudo, arquivo_id="verificacao_estrutural")
    if sonda.bloqueios or not sonda.completo or sonda.tipo != "pdf_texto":
        raise ErroLeitura("PDF_NAO_EXTRAIVEL_COM_SEGURANCA")
    textos = [normalizar_assinatura(p.texto) for p in sonda.fragmentos]
    def contem(texto, marcador):
        m = normalizar_assinatura(marcador)
        return re.search((r"(?<!\w)" if m[0].isalnum() else "") + re.escape(m)
                         + (r"(?!\w)" if m[-1].isalnum() else ""), texto) is not None
    candidatos = [id_ for id_, (_, marcadores) in GRAMATICAS.items()
                  if any(all(contem(t, m) for m in marcadores) for t in textos)]
    # Layout real é distinguido por estrutura, não pelo nome do condomínio.
    reais = {
        'habita_composicao_real_v1': any('•' in t and 'emissao' in t and 'monetaria' in t for t in textos),
        'fl_composicao_real_v1': any(re.search(r'w002a\s+.*?\([0-9]+\)',t) for t in textos),
        'cadastro_fl_real_v1': any('cpf/cnpj'in t and re.search(r'w045a\s+.*?\([0-9]+\)',t) for t in textos),
    }
    candidatos = [id_ for id_ in candidatos if not id_.endswith('_real_v1') or reais.get(id_)]
    for id_ in tuple(candidatos):
        if id_.endswith('_sintetico_v1') and reais.get(id_.replace('_sintetico_v1','_real_v1')):
            candidatos.remove(id_)
    if not candidatos:
        raise ErroLeitura("FORMATO_DESCONHECIDO")
    if len(candidatos) > 1:
        raise ErroLeitura("FORMATO_AMBIGUO")
    if candidatos[0] != leitor_id:
        raise ErroLeitura("FORMATO_DIVERGENTE_DO_LEITOR")


class ContextosCatalogo:
    def __init__(self, catalogo: Catalogo, data_ref: date):
        self.catalogo, self.data_ref = catalogo, data_ref

    def resolver(self, fonte, *, formato_id, condominio_id):
        formato = next((f for f in self.catalogo.formatos if f.id == formato_id), None)
        condo = next((c for c in self.catalogo.condominios if c.id == condominio_id), None)
        if formato is None or condo is None or formato.id not in condo.formato_ids or formato.tipo_arquivo not in ("pdf_texto", "xlsx"):
            raise ErroLeitura("CONTEXTO_DE_LEITURA_INCOMPATIVEL")
        if (formato.tipo_arquivo == 'xlsx') != (formato.leitor_id in LEITORES_XLSX):
            raise ErroLeitura('TIPO_DIVERGENTE_DO_LEITOR')
        vinculos = [v for v in condo.vinculos if v.inicio <= self.data_ref and (v.fim is None or self.data_ref < v.fim)]
        if len(vinculos) != 1 or vinculos[0].administradora_id not in formato.administradora_ids:
            raise ErroLeitura("VINCULO_HISTORICO_INCOMPATIVEL")
        adm = next(a for a in self.catalogo.administradoras if a.id == vinculos[0].administradora_id)
        if not condo.ativo or not adm.ativo:
            raise ErroLeitura("ENTIDADE_INATIVA")
        return ContextoLeitura(condo.id, adm.id, formato.id, fonte.arquivo_id, condo.codigo_na_administradora,
                               leitor_versao=f"{formato.leitor_id}@{formato.versao}")


class AdaptadorLeitorPDF:
    def __init__(self, leitor_id: str, versao: str, fontes: RepositorioFontes, contextos: ResolutorContexto):
        if leitor_id not in GRAMATICAS or versao != "1":
            raise ErroLeitura("LEITOR_OU_VERSAO_NAO_REGISTRADO")
        self.leitor_id, self.versao = leitor_id, versao
        self.fontes, self.contextos = fontes, contextos

    def ler(self, fonte: FonteProtegida, *, formato_id: str, condominio_id: str) -> LoteCanonico:
        contexto = self.contextos.resolver(fonte, formato_id=formato_id, condominio_id=condominio_id)
        if (contexto.formato_id, contexto.condominio_id, contexto.arquivo_id) != (formato_id, condominio_id, fonte.arquivo_id):
            raise ErroLeitura("CONTEXTO_DE_LEITURA_INCOMPATIVEL")
        if contexto.leitor_versao != f"{self.leitor_id}@{self.versao}":
            raise ErroLeitura("LEITOR_DIVERGENTE_DO_CONTEXTO")
        conteudo = self.fontes.ler(fonte)
        if sha256(conteudo).hexdigest() != fonte.sha256:
            raise ErroLeitura("HASH_FONTE_DIVERGENTE")
        validar_assinatura_para_leitura(conteudo, self.leitor_id)
        try:
            obtido = GRAMATICAS[self.leitor_id][0]().ler(conteudo, contexto=contexto)
            if self.leitor_id == LeitorCadastroFLSintetico.formato_id:
                unidades = tuple(Unidade(id=p.unidade_id, condominio_id=c, administradora_id=contexto.administradora_id,
                    bloco_original=b, unidade_original=u, chave_normalizada=f"{b}/{u}",
                    normalizador_versao="identidade_textual_lab_v1", origem=p.origem) for (c, b, u), p in obtido.items())
                obtido = LoteCanonico(unidades=unidades, pessoas=tuple(obtido.values()), boletos=())
            lote = LoteCanonico.model_validate(obtido.model_dump())
        except ValidationError:
            raise ErroLeitura("CONTRATO_DE_LEITURA_INVALIDO") from None
        if any(u.condominio_id != condominio_id or u.administradora_id != contexto.administradora_id for u in lote.unidades):
            raise ErroLeitura("LEITURA_RETORNOU_IDENTIDADE_DIVERGENTE")
        def conferir_origens(valor):
            if isinstance(valor, dict):
                if {"arquivo_id", "sha256", "leitor_versao", "identificador"} <= valor.keys():
                    if ((valor["arquivo_id"], valor["sha256"], valor["leitor_versao"]) !=
                        (fonte.arquivo_id, fonte.sha256, contexto.leitor_versao)
                        or valor.get("pagina") is None or valor.get("linha") is None):
                        raise ErroLeitura("PROVENIENCIA_DE_LEITURA_INCONSISTENTE")
                for item in valor.values(): conferir_origens(item)
            elif isinstance(valor, (tuple, list)):
                for item in valor: conferir_origens(item)
        conferir_origens(lote.model_dump())
        return lote


class AdaptadorLeitorXLSX:
    """Mesmos protocolos e integridade; localização de planilha não é página PDF."""
    def __init__(self, leitor_id, versao, fontes, contextos):
        if leitor_id not in LEITORES_XLSX or versao != '1':
            raise ErroLeitura('LEITOR_OU_VERSAO_NAO_REGISTRADO')
        self.leitor_id,self.versao,self.fontes,self.contextos = leitor_id,versao,fontes,contextos

    def ler(self, fonte, *, formato_id, condominio_id):
        ctx = self.contextos.resolver(fonte,formato_id=formato_id,condominio_id=condominio_id)
        if (ctx.formato_id,ctx.condominio_id,ctx.arquivo_id,ctx.leitor_versao) != (
                formato_id,condominio_id,fonte.arquivo_id,self.leitor_id+'@'+self.versao):
            raise ErroLeitura('CONTEXTO_DE_LEITURA_INCOMPATIVEL')
        conteudo=self.fontes.ler(fonte)
        if sha256(conteudo).hexdigest()!=fonte.sha256:raise ErroLeitura('HASH_FONTE_DIVERGENTE')
        try:
            lote=LEITORES_XLSX[self.leitor_id]().ler(conteudo,contexto=ctx)
            lote=LoteCanonico.model_validate(lote.model_dump())
        except ValidationError:
            raise ErroLeitura('CONTRATO_DE_LEITURA_INVALIDO') from None
        if any((u.condominio_id,u.administradora_id)!=(condominio_id,ctx.administradora_id)for u in lote.unidades):
            raise ErroLeitura('LEITURA_RETORNOU_IDENTIDADE_DIVERGENTE')
        def conferir(valor):
            if isinstance(valor,dict):
                if {'arquivo_id','sha256','leitor_versao','identificador'}<=valor.keys():
                    if ((valor['arquivo_id'],valor['sha256'],valor['leitor_versao'])!=(fonte.arquivo_id,fonte.sha256,ctx.leitor_versao)
                            or valor.get('pagina')is not None or valor.get('linha')is None
                            or not valor['identificador'].startswith(f"xlsx_aba1_r{valor['linha']}_")):
                        raise ErroLeitura('PROVENIENCIA_DE_LEITURA_INCONSISTENTE')
                for v in valor.values():conferir(v)
            elif isinstance(valor,(tuple,list)):
                for v in valor:conferir(v)
        conferir(lote.model_dump())
        return lote


class RegistroLeitores:
    def __init__(self, fontes: RepositorioFontes, contextos: ResolutorContexto):
        self._leitores = {(id_, "1"): AdaptadorLeitorPDF(id_, "1", fontes, contextos) for id_ in GRAMATICAS}
        self._leitores.update({(id_,'1'):AdaptadorLeitorXLSX(id_,'1',fontes,contextos) for id_ in LEITORES_XLSX})

    def obter(self, leitor_id: str, versao: str) -> AdaptadorLeitorPDF:
        if (leitor_id, versao) not in self._leitores:
            raise ErroLeitura("LEITOR_OU_VERSAO_NAO_REGISTRADO")
        return self._leitores[(leitor_id, versao)]
