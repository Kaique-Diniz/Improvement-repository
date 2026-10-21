from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from conversor.domain.base import Dinheiro, Id, Modelo
from conversor.domain.canonical import LoteCanonico, ResultadoCobranca


class RegraLaboratorio(Modelo):
    escopo: Literal["somente_testes_sinteticos"] = "somente_testes_sinteticos"
    id: Id
    versao: str = "1"
    dias_exclusivo: Annotated[int, Field(strict=True, ge=0)]
    excluir_unidade_valor: Dinheiro | None = None
    apontamentos_excluintes: tuple[str, ...] = ()
    namespace_apontamentos: Id | None = None
    cadastro: Literal["nunca", "unidades_com_boleto_adiado", "todas_unidades", "unidades_sem_divida"] = "nunca"

    @model_validator(mode="after")
    def exigir_namespace(self):
        if self.apontamentos_excluintes and self.namespace_apontamentos is None:
            raise ValueError("apontamentos exigem namespace explícito")
        return self


def avaliar(lote: LoteCanonico, regra: RegraLaboratorio, *, data_ref: date, processamento_id: str):
    if type(data_ref) is not date:
        raise ValueError("data de referência deve ser date explícita")
    lote = LoteCanonico.model_validate(lote.model_dump())
    resultados = []
    for unidade in lote.unidades:
        boletos = [b for b in lote.boletos if b.unidade_id == unidade.id]
        gatilho, motivo = None, None
        for boleto in boletos:
            if regra.excluir_unidade_valor is not None and boleto.composicao.total_original == regra.excluir_unidade_valor:
                gatilho, motivo = boleto, "EXCLUSAO_UNIDADE_VALOR"
                break
            if any(a.namespace_formato == regra.namespace_apontamentos and a.codigo_original in regra.apontamentos_excluintes
                   for a in boleto.apontamentos):
                gatilho, motivo = boleto, "EXCLUSAO_UNIDADE_APONTAMENTO"
                break
        for boleto in boletos:
            if gatilho is not None:
                acao, codigo, origens = "excluir", motivo, gatilho.origens
            elif (data_ref - boleto.vencimento).days > regra.dias_exclusivo:
                acao, codigo, origens = "incluir", "PRAZO_ELEGIVEL", boleto.origens
            else:
                acao, codigo, origens = "adiar", "PRAZO_NAO_ATINGIDO", boleto.origens
            resultados.append(ResultadoCobranca(processamento_id=processamento_id, unidade_id=unidade.id,
                boleto_id=boleto.id, acao=acao, regra_id=regra.id, regra_versao=regra.versao,
                motivo_codigo=codigo, origens=origens))
    return tuple(resultados)
