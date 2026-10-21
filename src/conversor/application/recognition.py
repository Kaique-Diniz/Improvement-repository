"""Reconhecimento determinístico: nunca escolhe pelo maior score entre concorrentes."""
from datetime import date
from hashlib import sha256
import json
import re

from conversor.domain.catalog import Catalogo, ReferenciasVersoes
from conversor.domain.recognition import (
    CatalogoAssinaturas, DocumentoSondado, EvidenciaReconhecimento, Motivo,
    PontuacaoFormato, ResultadoReconhecimento, SelecaoReconhecimento, normalizar_assinatura,
)
from .ports import ErroAplicacao, Repositorio
from .recognition_ports import RepositorioAssinaturas


normalizar = normalizar_assinatura


def _hash(modelo) -> str:
    dados = modelo.model_dump(mode="json", exclude_computed_fields=True)
    return sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _contem(texto: str, marcador: str) -> bool:
    inicio = r"(?<!\w)" if marcador[0].isalnum() else ""
    fim = r"(?!\w)" if marcador[-1].isalnum() else ""
    return re.search(inicio + re.escape(marcador) + fim, texto) is not None


def _campos(texto: str):
    for linha in texto.splitlines():
        partes = re.split(r"\s*:\s*|\t+", linha.strip(), maxsplit=1)
        if len(partes) == 2:
            yield normalizar(partes[0]), partes[1]


def _valor_corresponde(recebido: str, identificador) -> bool:
    esperado = identificador.valor
    if identificador.tipo == "cnpj":
        if not re.fullmatch(r"[0-9./\-\s]+", recebido):
            return False
        recebido, esperado = re.sub(r"\D", "", recebido), re.sub(r"\D", "", esperado)
    return normalizar(recebido) == normalizar(esperado)


def _campo_corresponde(texto: str, identificador) -> bool:
    return any(rotulo == normalizar(identificador.rotulo) and _valor_corresponde(valor, identificador)
               for rotulo, valor in _campos(texto))


def _identidades(sonda, entidades, campo_id, grupo):
    candidatos, evidencias = [], []
    desconhecidos = False
    identificadores = [i for entidade in entidades for i in entidade.identificadores]
    for fragmento in sonda.fragmentos:
        for rotulo, valor in _campos(fragmento.texto):
            esperados = [i for i in identificadores if normalizar(i.rotulo) == rotulo]
            if esperados and not any(_valor_corresponde(valor, i) for i in esperados):
                desconhecidos = True
    for entidade in sorted(entidades, key=lambda e: getattr(e, campo_id)):
        for fragmento in sonda.fragmentos:
            if all(_campo_corresponde(fragmento.texto, i) for i in entidade.identificadores):
                id_ = getattr(entidade, campo_id)
                candidatos.append(id_)
                evidencias.extend(EvidenciaReconhecimento(grupo=grupo, entidade_id=id_, marcador_id=i.id,
                                  localizador=fragmento.localizador) for i in entidade.identificadores)
                break
    return tuple(candidatos), evidencias, desconhecidos


def _validar_referencias(catalogo: Catalogo, assinaturas: CatalogoAssinaturas):
    for entidades, referencias, campo in (
        (catalogo.formatos, assinaturas.layouts, "formato_id"),
        (catalogo.administradoras, assinaturas.administradoras, "administradora_id"),
        (catalogo.condominios, assinaturas.condominios, "condominio_id"),
    ):
        ids = {e.id for e in entidades}
        if any(getattr(r, campo) not in ids for r in referencias):
            raise ErroAplicacao("ASSINATURAS_COM_REFERENCIA_INEXISTENTE")


class ReconhecerDocumento:
    def __init__(self, repositorio: Repositorio, assinaturas: RepositorioAssinaturas):
        self.repositorio = repositorio
        self.assinaturas = assinaturas

    def executar(self, documento: DocumentoSondado, *, data_ref: date) -> ResultadoReconhecimento:
        if type(data_ref) is not date:
            raise ErroAplicacao("DATA_REF_INVALIDA")
        estado = self.repositorio.carregar()  # uma revisão consistente por reconhecimento
        catalogo = estado.catalogo
        assinaturas = self.assinaturas.carregar()
        _validar_referencias(catalogo, assinaturas)
        base = dict(sondador_versao=documento.sondador_versao, arquivo_id=documento.arquivo_id,
                    arquivo_hash=documento.arquivo_hash, catalogo_hash=_hash(catalogo),
                    assinaturas_hash=_hash(assinaturas), catalogo_revisao=estado.revisao,
                    assinaturas_versao=assinaturas.versao, data_ref=data_ref, tipo=documento.tipo)
        evidencias, pontuacoes = [], []
        adms, condos = (), ()

        def resultado(estado_resultado, bloqueios, selecao=None):
            return ResultadoReconhecimento(**base, estado=estado_resultado, bloqueios=tuple(bloqueios),
                selecao=selecao, pontuacoes=tuple(pontuacoes), administradora_candidatos=adms,
                condominio_candidatos=condos, evidencias=tuple(evidencias))

        if documento.bloqueios or not documento.completo:
            return resultado("desconhecido", documento.bloqueios or (Motivo.SONDA_INCOMPLETA,))
        if documento.tipo not in ("pdf_texto", "xlsx", "csv"):
            return resultado("desconhecido", (Motivo.TIPO_NAO_SUPORTADO,))

        formatos = {f.id: f for f in catalogo.formatos}
        aptas = []
        for assinatura in sorted(assinaturas.layouts, key=lambda a: a.id):
            formato = formatos[assinatura.formato_id]
            if formato.tipo_arquivo != documento.tipo:
                continue
            maximo = sum(m.peso for m in assinatura.marcadores)
            opcoes = []
            for fragmento in documento.fragmentos:
                texto = normalizar(fragmento.texto)
                presentes = [m for m in assinatura.marcadores if _contem(texto, normalizar(m.texto))]
                pontos = sum(m.peso for m in presentes)
                elegivel = (pontos >= assinatura.minimo_pontos and
                            all(m in presentes for m in assinatura.marcadores if m.obrigatorio))
                opcoes.append((elegivel, pontos, fragmento, presentes))
            if not opcoes:
                continue
            # Elegibilidade precede score; empate preserva a primeira localização do documento.
            elegivel, pontos, fragmento, presentes = max(opcoes, key=lambda o: (o[0], o[1]))
            pontuacoes.append(PontuacaoFormato(formato_id=formato.id, assinatura_id=assinatura.id,
                assinatura_versao=assinatura.versao, pontos=pontos, maximo=maximo,
                cobertura_percentual=pontos * 100 // maximo, elegivel=elegivel))
            evidencias.extend(EvidenciaReconhecimento(grupo="layout", entidade_id=formato.id, marcador_id=m.id,
                localizador=fragmento.localizador) for m in presentes)
            if elegivel:
                aptas.append(assinatura)
        if not aptas:
            return resultado("desconhecido", (Motivo.FORMATO_DESCONHECIDO,))
        if len(aptas) != 1:
            return resultado("ambiguo", (Motivo.FORMATO_AMBIGUO,))
        assinatura = aptas[0]
        formato = formatos[assinatura.formato_id]
        nao_homologados = []
        if formato.status != "validado":
            nao_homologados.append(Motivo.FORMATO_NAO_HOMOLOGADO)
        if assinaturas.status != "homologado":
            nao_homologados.append(Motivo.ASSINATURAS_NAO_HOMOLOGADAS)
        if nao_homologados:
            return resultado("desconhecido", nao_homologados)

        adms, provas, adm_desconhecida = _identidades(documento, assinaturas.administradoras, "administradora_id", "administradora")
        evidencias.extend(provas)
        condos, provas, condo_desconhecido = _identidades(documento, assinaturas.condominios, "condominio_id", "condominio")
        evidencias.extend(provas)
        if len(adms) > 1 or len(condos) > 1 or (adms and adm_desconhecida) or (condos and condo_desconhecido):
            motivos = []
            if len(adms) > 1 or (adms and adm_desconhecida): motivos.append(Motivo.ADMINISTRADORA_AMBIGUA)
            if len(condos) > 1 or (condos and condo_desconhecido): motivos.append(Motivo.CONDOMINIO_AMBIGUO)
            return resultado("ambiguo", motivos)
        if not adms or not condos:
            motivos = []
            if not adms: motivos.append(Motivo.ADMINISTRADORA_DESCONHECIDA)
            if not condos: motivos.append(Motivo.CONDOMINIO_DESCONHECIDO)
            return resultado("desconhecido", motivos)
        adm = next(a for a in catalogo.administradoras if a.id == adms[0])
        condo = next(c for c in catalogo.condominios if c.id == condos[0])
        if not adm.ativo or not condo.ativo:
            return resultado("desconhecido", (Motivo.ENTIDADE_INATIVA,))
        vinculos = [v for v in condo.vinculos if v.inicio <= data_ref and (v.fim is None or data_ref < v.fim)]
        if len(vinculos) != 1 or vinculos[0].administradora_id != adm.id:
            return resultado("desconhecido", (Motivo.VINCULO_INCOMPATIVEL,))
        if adm.id not in formato.administradora_ids or formato.id not in condo.formato_ids:
            return resultado("desconhecido", (Motivo.FORMATO_INCOMPATIVEL,))
        perfil = next(p for p in catalogo.perfis_condominio if p.id == condo.perfil_version_id)
        regra = next(r for r in catalogo.regras_cobranca if r.id == perfil.regra_id)
        selecao = SelecaoReconhecimento(condominio_id=condo.id, assinatura_id=assinatura.id,
            assinatura_versao=assinatura.versao, versoes=ReferenciasVersoes(administradora_id=adm.id,
            formato_id=formato.id, perfil_id=perfil.id, regra_id=regra.id, template_id=perfil.template_id))
        motivos = []
        if perfil.status != "aprovado": motivos.append(Motivo.PERFIL_NAO_APROVADO)
        if regra.status != "aprovada": motivos.append(Motivo.REGRA_NAO_APROVADA)
        if not (regra.vigente_de <= data_ref and (regra.vigente_ate is None or data_ref < regra.vigente_ate)):
            motivos.append(Motivo.REGRA_FORA_DA_VIGENCIA)
        return resultado("conhecido_validado", motivos, selecao)
