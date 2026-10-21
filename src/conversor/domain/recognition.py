"""Contratos de reconhecimento: evidências de conteúdo, sem valores financeiros."""
from enum import StrEnum
from typing import Annotated, Literal
import re
import unicodedata

from pydantic import Field, field_validator, model_validator

from .base import Data, Hash, Id, Modelo, Texto
from .catalog import Aprovacao, ReferenciasVersoes


def normalizar_assinatura(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto).casefold()
    return " ".join("".join(c for c in decomposto if not unicodedata.combining(c)).split())


class TipoDocumento(StrEnum):
    PDF_TEXTO = "pdf_texto"
    PDF_IMAGEM = "pdf_imagem"
    PDF_MISTO = "pdf_misto"
    XLSX = "xlsx"
    CSV = "csv"
    DESCONHECIDO = "desconhecido"


class Motivo(StrEnum):
    TIPO_NAO_SUPORTADO = "TIPO_NAO_SUPORTADO"
    DOCUMENTO_INVALIDO = "DOCUMENTO_INVALIDO"
    DOCUMENTO_PROTEGIDO = "DOCUMENTO_PROTEGIDO"
    LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
    SONDA_INCOMPLETA = "SONDA_INCOMPLETA"
    PDF_SEM_TEXTO = "PDF_SEM_TEXTO"
    PDF_MISTO = "PDF_MISTO"
    ARQUIVO_VAZIO = "ARQUIVO_VAZIO"
    CSV_INVALIDO = "CSV_INVALIDO"
    FORMATO_DESCONHECIDO = "FORMATO_DESCONHECIDO"
    FORMATO_AMBIGUO = "FORMATO_AMBIGUO"
    FORMATO_NAO_HOMOLOGADO = "FORMATO_NAO_HOMOLOGADO"
    ASSINATURAS_NAO_HOMOLOGADAS = "ASSINATURAS_NAO_HOMOLOGADAS"
    ADMINISTRADORA_DESCONHECIDA = "ADMINISTRADORA_DESCONHECIDA"
    ADMINISTRADORA_AMBIGUA = "ADMINISTRADORA_AMBIGUA"
    CONDOMINIO_DESCONHECIDO = "CONDOMINIO_DESCONHECIDO"
    CONDOMINIO_AMBIGUO = "CONDOMINIO_AMBIGUO"
    VINCULO_INCOMPATIVEL = "VINCULO_INCOMPATIVEL"
    FORMATO_INCOMPATIVEL = "FORMATO_INCOMPATIVEL"
    ENTIDADE_INATIVA = "ENTIDADE_INATIVA"
    PERFIL_NAO_APROVADO = "PERFIL_NAO_APROVADO"
    REGRA_NAO_APROVADA = "REGRA_NAO_APROVADA"
    REGRA_FORA_DA_VIGENCIA = "REGRA_FORA_DA_VIGENCIA"


class FragmentoSondagem(Modelo):
    localizador: Id  # pagina_1, aba_1: não usa nome de arquivo, aba ou pessoa
    texto: str = Field(repr=False, exclude=True)


class DocumentoSondado(Modelo):
    arquivo_id: Id
    arquivo_hash: Hash
    sondador_versao: Literal["1.0.0"] = "1.0.0"
    tipo: TipoDocumento
    fragmentos: tuple[FragmentoSondagem, ...] = Field(default=(), repr=False, exclude=True)
    completo: bool = True
    bloqueios: tuple[Motivo, ...] = ()


class MarcadorLayout(Modelo):
    id: Id
    texto: Texto = Field(repr=False)
    peso: Annotated[int, Field(strict=True, ge=1, le=100)] = 1
    obrigatorio: bool = True

    @field_validator("texto")
    @classmethod
    def nao_vazio(cls, valor):
        if not normalizar_assinatura(valor):
            raise ValueError("MARCADOR_VAZIO")
        return valor


class AssinaturaLayout(Modelo):
    id: Id
    versao: Texto
    formato_id: Id
    marcadores: Annotated[tuple[MarcadorLayout, ...], Field(min_length=2, max_length=50)]
    minimo_pontos: Annotated[int, Field(strict=True, ge=2)]

    @model_validator(mode="after")
    def consistente(self):
        if len({m.id for m in self.marcadores}) != len(self.marcadores):
            raise ValueError("MARCADOR_DUPLICADO")
        if len({normalizar_assinatura(m.texto) for m in self.marcadores}) != len(self.marcadores):
            raise ValueError("TEXTO_MARCADOR_DUPLICADO")
        if sum(m.obrigatorio for m in self.marcadores) < 2:
            raise ValueError("ASSINATURA_EXIGE_DOIS_MARCADORES_OBRIGATORIOS")
        if self.minimo_pontos > sum(m.peso for m in self.marcadores):
            raise ValueError("LIMIAR_INATINGIVEL")
        return self


class IdentificadorForte(Modelo):
    id: Id
    rotulo: Texto = Field(repr=False)
    valor: Texto = Field(repr=False)
    tipo: Literal["codigo", "texto", "cnpj"] = "codigo"

    @model_validator(mode="after")
    def nao_vazio(self):
        if not normalizar_assinatura(self.rotulo) or not normalizar_assinatura(self.valor):
            raise ValueError("IDENTIFICADOR_VAZIO")
        if self.tipo == "cnpj" and (not re.fullmatch(r"[0-9./\-\s]+", self.valor)
                                   or len(re.sub(r"\D", "", self.valor)) != 14):
            raise ValueError("IDENTIFICADOR_CNPJ_INVALIDO")
        return self


class IdentidadeAdministradora(Modelo):
    administradora_id: Id
    identificadores: Annotated[tuple[IdentificadorForte, ...], Field(min_length=1)]


class IdentidadeCondominio(Modelo):
    condominio_id: Id
    identificadores: Annotated[tuple[IdentificadorForte, ...], Field(min_length=1)]


class CatalogoAssinaturas(Modelo):
    # Contrato independente: não altera snapshots/schema 1.0 aprovados na Fase 1.
    schema_version: Literal["1.0"] = "1.0"
    versao: Texto
    status: Literal["rascunho", "homologado"] = "rascunho"
    aprovacao: Aprovacao | None = None
    layouts: tuple[AssinaturaLayout, ...]
    administradoras: tuple[IdentidadeAdministradora, ...]
    condominios: tuple[IdentidadeCondominio, ...]

    @model_validator(mode="after")
    def consistente(self):
        if self.status == "homologado" and self.aprovacao is None:
            raise ValueError("ASSINATURAS_EXIGEM_HOMOLOGACAO")
        for valores in (
            [a.id for a in self.layouts], [a.formato_id for a in self.layouts],
            [a.administradora_id for a in self.administradoras], [c.condominio_id for c in self.condominios],
        ):
            if len(set(valores)) != len(valores):
                raise ValueError("ASSINATURA_OU_IDENTIDADE_DUPLICADA")
        for entidade in (*self.administradoras, *self.condominios):
            if len({i.id for i in entidade.identificadores}) != len(entidade.identificadores):
                raise ValueError("IDENTIFICADOR_DUPLICADO")
        return self


class EvidenciaReconhecimento(Modelo):
    grupo: Literal["layout", "administradora", "condominio"]
    entidade_id: Id
    marcador_id: Id
    localizador: Id


class PontuacaoFormato(Modelo):
    formato_id: Id
    assinatura_id: Id
    assinatura_versao: Texto
    pontos: Annotated[int, Field(strict=True, ge=0)]
    maximo: Annotated[int, Field(strict=True, ge=1)]
    cobertura_percentual: Annotated[int, Field(strict=True, ge=0, le=100)]
    elegivel: bool


class SelecaoReconhecimento(Modelo):
    condominio_id: Id
    assinatura_id: Id
    assinatura_versao: Texto
    versoes: ReferenciasVersoes


class ResultadoReconhecimento(Modelo):
    schema_version: Literal["1.0"] = "1.0"
    motor_versao: Literal["1.0.0"] = "1.0.0"
    sondador_versao: Texto
    arquivo_id: Id
    arquivo_hash: Hash
    catalogo_hash: Hash
    assinaturas_hash: Hash
    catalogo_revisao: Annotated[int, Field(strict=True, ge=0)]
    assinaturas_versao: Texto
    data_ref: Data
    tipo: TipoDocumento
    estado: Literal["conhecido_validado", "desconhecido", "ambiguo"]
    pontuacoes: tuple[PontuacaoFormato, ...] = ()
    administradora_candidatos: tuple[Id, ...] = ()
    condominio_candidatos: tuple[Id, ...] = ()
    selecao: SelecaoReconhecimento | None = None
    evidencias: tuple[EvidenciaReconhecimento, ...] = ()
    bloqueios: tuple[Motivo, ...] = ()
    bloqueante: bool = False
    pronto_para_proxima_etapa: bool = False

    @model_validator(mode="before")
    @classmethod
    def preencher_flags(cls, dados):
        if isinstance(dados, dict):
            dados = dict(dados)
            bloqueante = bool(dados.get("bloqueios"))
            dados.setdefault("bloqueante", bloqueante)
            dados.setdefault("pronto_para_proxima_etapa", dados.get("estado") == "conhecido_validado" and not bloqueante)
        return dados

    @model_validator(mode="after")
    def consistente(self):
        if (self.estado == "conhecido_validado") != (self.selecao is not None):
            raise ValueError("RECONHECIMENTO_SEM_SELECAO_UNICA")
        if self.estado != "conhecido_validado" and not self.bloqueios:
            raise ValueError("RECONHECIMENTO_NAO_RESOLVIDO_EXIGE_BLOQUEIO")
        if self.bloqueante != bool(self.bloqueios) or self.pronto_para_proxima_etapa != (
            self.estado == "conhecido_validado" and not self.bloqueios
        ):
            raise ValueError("FLAGS_RECONHECIMENTO_INCONSISTENTES")
        return self
