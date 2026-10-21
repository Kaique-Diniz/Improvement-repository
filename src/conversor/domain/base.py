from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated
import re

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


Id = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")]
Texto = Annotated[str, Field(min_length=1, max_length=500)]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def validar_dinheiro(valor: object) -> Decimal:
    if isinstance(valor, (bool, float)) or not isinstance(valor, (str, int, Decimal)):
        raise ValueError("DINHEIRO_EXIGE_DECIMAL_OU_TEXTO")
    try:
        numero = Decimal(valor)
        if not numero.is_finite():
            raise ValueError("DINHEIRO_FORA_DO_CONTRATO")
        centavos = numero.quantize(Decimal("0.01"))
        if numero != centavos:
            raise ValueError("DINHEIRO_EXIGE_CENTAVOS_EXATOS")
        return centavos
    except InvalidOperation:
        raise ValueError("DINHEIRO_INVALIDO") from None


Dinheiro = Annotated[Decimal, BeforeValidator(validar_dinheiro)]


def validar_data(valor: object):
    if type(valor) is date or (isinstance(valor, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor)):
        return valor
    raise ValueError("DATA_EXIGE_ISO_EXPLICITA")


Data = Annotated[date, BeforeValidator(validar_data)]


def com_fuso(valor: datetime) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError("HORARIO_EXIGE_FUSO")
    return valor
