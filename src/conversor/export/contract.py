from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from conversor.domain.base import Data, Dinheiro, Id, Modelo, Texto
from conversor.domain.canonical import Ocorrencia, Pessoa
from conversor.domain.documents import resolver_documento
from conversor.application.documents import ocorrencias_documentais
from conversor.domain.template import COLUNAS, Template


class DividaExportacao(Modelo):
    contrato: Texto
    produto: Texto
    nome_divida: Texto
    parcela: Annotated[int, Field(strict=True, ge=1)]
    vencimento: Data
    valor: Annotated[Dinheiro, Field(gt=0)]


class LinhaExportacao(Modelo):
    """DTO para futuro escritor XLSX; não decide elegibilidade financeira."""
    processamento_id: Id
    registro_id: Id
    tipo: Literal["cadastral", "divida"]
    nm_cedente_cedente: Texto
    cedente: Texto
    pessoa: Pessoa = Field(repr=False)
    divida: DividaExportacao | None = None
    ocorrencias: tuple[Ocorrencia, ...] = ()

    @model_validator(mode="after")
    def coerencia(self):
        if (self.tipo == "divida") != (self.divida is not None):
            raise ValueError("TIPO_DE_LINHA_INCOMPATIVEL")
        if any(o.processamento_id != self.processamento_id for o in self.ocorrencias):
            raise ValueError("OCORRENCIA_DE_OUTRA_EXECUCAO")
        if any(o.bloqueante for o in self.ocorrencias):
            raise ValueError("LINHA_COM_BLOQUEIO")
        if resolver_documento(self.pessoa).bloqueante:
            raise ValueError("CADASTRO_DOCUMENTAL_EXIGE_REVISAO_HUMANA")
        return self


class LinhaMaterializada(Modelo):
    valores: Annotated[tuple[str | int | date | Dinheiro, ...], Field(min_length=30, max_length=30, repr=False)]
    ocorrencias: tuple[Ocorrencia, ...]


def materializar(linha: LinhaExportacao) -> LinhaMaterializada:
    linha = LinhaExportacao.model_validate(linha.model_dump())
    documento = resolver_documento(linha.pessoa).valor
    ocorrencias = list(linha.ocorrencias)
    for ocorrencia in ocorrencias_documentais(linha.pessoa, processamento_id=linha.processamento_id):
        if ocorrencia not in ocorrencias:
            ocorrencias.append(ocorrencia)
    pessoa = linha.pessoa
    endereco = pessoa.contato.endereco
    valores = [linha.nm_cedente_cedente, linha.cedente, documento, pessoa.nome,
               endereco.logradouro, endereco.numero, endereco.complemento, endereco.cep,
               endereco.bairro, endereco.cidade, endereco.uf]
    for i in range(5):
        tel = pessoa.contato.telefones[i] if i < len(pessoa.contato.telefones) else None
        valores.extend([tel.ddd if tel else "", tel.numero if tel else ""])
    valores.extend([pessoa.contato.emails[i] if i < len(pessoa.contato.emails) else "" for i in range(3)])
    if linha.divida is None:
        valores.extend([""] * 6)
    else:
        divida = linha.divida
        valores.extend([divida.contrato, divida.produto, divida.nome_divida,
                        divida.parcela, divida.vencimento, divida.valor])
    return LinhaMaterializada(valores=tuple(valores), ocorrencias=tuple(ocorrencias))
