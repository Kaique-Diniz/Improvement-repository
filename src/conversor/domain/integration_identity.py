"""Identidade do destino separada de códigos auxiliares e de famílias de layout."""
from typing import Annotated

from pydantic import Field, model_validator

from .base import Id, Modelo, Texto
from .recognition import normalizar_assinatura

CodigoEasyCollector = Annotated[str, Field(strict=True, pattern=r'^[0-9]{1,20}$')]


def nome_documental(nome):
    nome=normalizar_assinatura(nome)
    for prefixo in ('condominio edificio ','condominio do edificio ','condominio ','edificio '):
        if nome.startswith(prefixo):return nome[len(prefixo):].strip()
    return nome


class IdentidadeIntegracao(Modelo):
    codigo_easycollector: CodigoEasyCollector
    administradora_id: Id
    condominio_id: Id
    nome_integracao: Texto
    nomes_documentais: Annotated[tuple[Texto,...],Field(min_length=1)]
    codigos_origem: tuple[Texto,...] = ()

    @model_validator(mode='after')
    def unicos(self):
        if len(set(self.codigos_origem))!=len(self.codigos_origem):raise ValueError('CODIGO_ORIGEM_DUPLICADO')
        return self


class CatalogoIdentidadesIntegracao(Modelo):
    schema_versao: str = Field(default='1.0',pattern=r'^1\.0$')
    versao: Texto
    origem_codigos_destino: str = Field(default='decisao_responsavel',pattern=r'^decisao_responsavel$')
    identidades: tuple[IdentidadeIntegracao,...]

    @model_validator(mode='after')
    def integridade(self):
        if len({i.codigo_easycollector for i in self.identidades})!=len(self.identidades):
            raise ValueError('CODIGO_EASYCOLLECTOR_DUPLICADO')
        if len({(i.administradora_id,i.condominio_id)for i in self.identidades})!=len(self.identidades):
            raise ValueError('IDENTIDADE_INTEGRACAO_DUPLICADA')
        # Código de origem é auxiliar: não é chave global do destino.
        # Reutilização/ambiguidade documental é tratada na associação por conteúdo.
        return self

    def candidatos(self,nome,codigo_origem):
        return tuple(i for i in self.identidades
            if nome_documental(nome)in{nome_documental(n)for n in i.nomes_documentais}
            and(not i.codigos_origem or codigo_origem in i.codigos_origem))
