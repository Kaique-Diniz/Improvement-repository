from typing import Literal

from pydantic import model_validator

from .base import Id, Modelo, Texto

COLUNAS = (
    "NM_CEDENTE_CEDENTE", "CEDENTE", "CPF", "NOME", "ENDERECO", "NUMERO",
    "COMPLEMENTO", "CEP", "BAIRRO", "CIDADE", "UF", "DDD1", "FONE1", "DDD2",
    "FONE2", "DDD3", "FONE3", "DDD4", "FONE4", "DDD5", "FONE5", "EMAIL1",
    "EMAIL2", "EMAIL3", "NM_CONTRATO_CEDENTE", "PRODUTO_CEDENTE", "NM_DIVIDA_CEDENTE",
    "NU_PARCELA", "VENCIMENTO", "VL_PARCELA",
)


class Template(Modelo):
    id: Id
    nome: Texto
    versao: Texto
    nome_aba: Literal["Dados"] = "Dados"
    colunas_logicas: tuple[str, ...] = COLUNAS
    espaco_final_coluna_27: bool = True  # padrão histórico; novas saídas MVP usam False explicitamente

    @model_validator(mode="after")
    def contrato(self):
        if self.colunas_logicas != COLUNAS:
            raise ValueError("TEMPLATE_FORA_DO_CONTRATO_30_COLUNAS")
        return self

    @property
    def cabecalhos_fisicos(self) -> tuple[str, ...]:
        return tuple(c + " " if i == 26 and self.espaco_final_coluna_27 else c for i, c in enumerate(COLUNAS))
