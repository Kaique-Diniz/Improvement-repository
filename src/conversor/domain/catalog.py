from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .base import Data, Hash, Id, Modelo, Texto, com_fuso
from .canonical import Endereco, Ocorrencia, Origem
from .template import Template


class Administradora(Modelo):
    id: Id
    nome: Texto
    identificadores: tuple[Texto, ...] = ()
    ativo: bool = True


class Aprovacao(Modelo):
    responsavel_id: Id
    evidencia_id: Id
    em: datetime

    _fuso = field_validator("em")(com_fuso)


class Formato(Modelo):
    id: Id
    nome: Texto
    versao: Texto
    tipo_arquivo: Literal["pdf_texto", "pdf_imagem", "xlsx", "csv"]
    status: Literal["rascunho", "validado"] = "rascunho"
    administradora_ids: tuple[Id, ...]
    marcadores: tuple[Texto, ...]
    leitor_id: Id
    aprovacao: Aprovacao | None = None

    @model_validator(mode="after")
    def aprovado(self):
        if self.status == "validado" and self.aprovacao is None:
            raise ValueError("FORMATO_EXIGE_HOMOLOGACAO")
        return self


class VinculoAdministradora(Modelo):
    administradora_id: Id
    inicio: Data
    fim: Data | None = None  # intervalo [inicio, fim)

    @model_validator(mode="after")
    def intervalo(self):
        if self.fim is not None and self.fim <= self.inicio:
            raise ValueError("INTERVALO_INVALIDO")
        return self


class Condominio(Modelo):
    id: Id
    nome: Texto
    administradora_id: Id
    codigo_na_administradora: Texto
    perfil_version_id: Id
    formato_ids: Annotated[tuple[Id, ...], Field(min_length=1)]
    vinculos: Annotated[tuple[VinculoAdministradora, ...], Field(min_length=1)]
    ativo: bool = True

    @model_validator(mode="after")
    def historico(self):
        ordenados = sorted(self.vinculos, key=lambda v: v.inicio)
        if tuple(ordenados) != self.vinculos:
            raise ValueError("VINCULOS_FORA_DE_ORDEM")
        abertos = [v for v in self.vinculos if v.fim is None]
        if len(abertos) != 1 or abertos[0] != self.vinculos[-1]:
            raise ValueError("EXIGE_UM_VINCULO_ATUAL")
        if abertos[0].administradora_id != self.administradora_id:
            raise ValueError("ADMINISTRADORA_ATUAL_DIVERGENTE")
        for anterior, atual in zip(self.vinculos, self.vinculos[1:]):
            if anterior.fim is None or anterior.fim > atual.inicio:
                raise ValueError("VINCULOS_SOBREPOSTOS")
        if len(set(self.formato_ids)) != len(self.formato_ids):
            raise ValueError("FORMATO_REPETIDO")
        return self


class PerfilCondominio(Modelo):
    id: Id
    condominio_id: Id
    versao: Texto
    template_id: Id
    regra_id: Id
    cadastro_antecipado: bool
    codificador_cedente: Id
    nome_cedente: Texto | None = None
    produto_cedente: Texto | None = None
    endereco: Endereco | None = Field(default=None, repr=False)
    status: Literal["rascunho", "aprovado"] = "rascunho"
    aprovacao: Aprovacao | None = None

    @model_validator(mode="after")
    def aprovado(self):
        if self.status == "aprovado" and self.aprovacao is None:
            raise ValueError("PERFIL_EXIGE_APROVACAO")
        return self


class CondicaoRegra(Modelo):
    """Contrato declarativo apenas; Fase 1 não interpreta nem executa condições."""
    campo: Id
    operador: Literal["igual", "contem", "maior_que", "maior_ou_igual", "dias_atraso"]
    valor: str
    alcance: Literal["boleto", "unidade", "condominio"]
    acao: Literal["incluir", "excluir", "adiar", "alertar", "bloquear"]
    prioridade: Annotated[int, Field(strict=True, ge=0)]


class RegraCobranca(Modelo):
    id: Id
    condominio_id: Id
    versao: Texto
    status: Literal["rascunho", "aprovada"] = "rascunho"
    vigente_de: Data
    vigente_ate: Data | None = None
    condicoes: tuple[CondicaoRegra, ...] = ()
    fonte: Origem | None = None
    aprovacao: Aprovacao | None = None

    @model_validator(mode="after")
    def coerencia(self):
        if self.vigente_ate is not None and self.vigente_ate <= self.vigente_de:
            raise ValueError("VIGENCIA_INVALIDA")
        if self.status == "aprovada" and (self.aprovacao is None or self.fonte is None or not self.condicoes):
            raise ValueError("REGRA_EXIGE_APROVACAO_FONTE_E_CONDICOES")
        return self


class ReferenciasVersoes(Modelo):
    administradora_id: Id
    formato_id: Id
    perfil_id: Id
    regra_id: Id
    template_id: Id


class Processamento(Modelo):
    id: Id
    condominio_id: Id
    status: Literal["pendente", "bloqueado", "concluido"]
    data_ref: Data
    iniciado_em: datetime
    versoes: ReferenciasVersoes
    arquivo_hashes: Annotated[tuple[Hash, ...], Field(min_length=1)]
    unidades: Annotated[int, Field(strict=True, ge=0)] = 0
    boletos: Annotated[int, Field(strict=True, ge=0)] = 0
    linhas: Annotated[int, Field(strict=True, ge=0)] = 0

    _fuso = field_validator("iniciado_em")(com_fuso)


class Catalogo(Modelo):
    schema_version: Literal["1.0"] = "1.0"
    administradoras: tuple[Administradora, ...] = ()
    condominios: tuple[Condominio, ...] = ()
    formatos: tuple[Formato, ...] = ()
    perfis_condominio: tuple[PerfilCondominio, ...] = ()
    regras_cobranca: tuple[RegraCobranca, ...] = ()
    templates: tuple[Template, ...] = ()
    processamentos: tuple[Processamento, ...] = ()
    ocorrencias: tuple[Ocorrencia, ...] = ()

    @model_validator(mode="after")
    def integridade(self):
        colecoes = {nome: getattr(self, nome) for nome in type(self).model_fields if nome != "schema_version"}
        mapas = {nome: {item.id: item for item in itens} for nome, itens in colecoes.items()}
        for nome, itens in colecoes.items():
            if len(mapas[nome]) != len(itens):
                raise ValueError("ID_DUPLICADO")

        def referencia(colecao, id_):
            if id_ not in mapas[colecao]:
                raise ValueError("REFERENCIA_INEXISTENTE")
            return mapas[colecao][id_]

        def unico(itens):
            if len(set(itens)) != len(itens):
                raise ValueError("CHAVE_UNICA_VIOLADA")

        unico([(c.administradora_id, c.codigo_na_administradora) for c in self.condominios])
        for itens in (self.formatos, self.templates):
            unico([(i.nome, i.versao) for i in itens])
        for itens in (self.perfis_condominio, self.regras_cobranca):
            unico([(i.condominio_id, i.versao) for i in itens])
        for formato in self.formatos:
            for adm in formato.administradora_ids:
                referencia("administradoras", adm)
        for condo in self.condominios:
            adm = referencia("administradoras", condo.administradora_id)
            if condo.ativo and not adm.ativo:
                raise ValueError("ADMINISTRADORA_INATIVA")
            for vinculo in condo.vinculos:
                referencia("administradoras", vinculo.administradora_id)
            perfil = referencia("perfis_condominio", condo.perfil_version_id)
            if perfil.condominio_id != condo.id:
                raise ValueError("PERFIL_DE_OUTRO_CONDOMINIO")
            for formato_id in condo.formato_ids:
                formato = referencia("formatos", formato_id)
                if condo.administradora_id not in formato.administradora_ids:
                    raise ValueError("FORMATO_INCOMPATIVEL_COM_ADMINISTRADORA")
        for perfil in self.perfis_condominio:
            referencia("condominios", perfil.condominio_id)
            referencia("templates", perfil.template_id)
            regra = referencia("regras_cobranca", perfil.regra_id)
            if regra.condominio_id != perfil.condominio_id:
                raise ValueError("REGRA_DE_OUTRO_CONDOMINIO")
        for regra in self.regras_cobranca:
            referencia("condominios", regra.condominio_id)
        aprovadas = [r for r in self.regras_cobranca if r.status == "aprovada"]
        for i, regra in enumerate(aprovadas):
            for outra in aprovadas[i + 1:]:
                if regra.condominio_id == outra.condominio_id and (
                    regra.vigente_de < (outra.vigente_ate or date.max)
                    and outra.vigente_de < (regra.vigente_ate or date.max)
                ):
                    raise ValueError("REGRAS_APROVADAS_SOBREPOSTAS")
        for proc in self.processamentos:
            condo = referencia("condominios", proc.condominio_id)
            refs = proc.versoes
            referencia("administradoras", refs.administradora_id)
            formato = referencia("formatos", refs.formato_id)
            perfil = referencia("perfis_condominio", refs.perfil_id)
            regra = referencia("regras_cobranca", refs.regra_id)
            referencia("templates", refs.template_id)
            if (perfil.condominio_id != condo.id or regra.condominio_id != condo.id
                    or perfil.regra_id != regra.id or perfil.template_id != refs.template_id
                    or refs.administradora_id not in formato.administradora_ids):
                raise ValueError("VERSOES_INCOMPATIVEIS")
            vinculos = [v for v in condo.vinculos if v.inicio <= proc.data_ref and (v.fim is None or proc.data_ref < v.fim)]
            if len(vinculos) != 1 or vinculos[0].administradora_id != refs.administradora_id:
                raise ValueError("VINCULO_HISTORICO_INCOMPATIVEL")
            if proc.status == "concluido" and (
                formato.status != "validado" or regra.status != "aprovada"
                or perfil.status != "aprovado"
                or not (regra.vigente_de <= proc.data_ref and (regra.vigente_ate is None or proc.data_ref < regra.vigente_ate))
            ):
                raise ValueError("PROCESSAMENTO_EXIGE_CONFIGURACAO_APROVADA")
        for ocorrencia in self.ocorrencias:
            proc = referencia("processamentos", ocorrencia.processamento_id)
            if proc.status == "concluido" and ocorrencia.bloqueante:
                raise ValueError("PROCESSAMENTO_CONCLUIDO_COM_BLOQUEIO")
        return self
