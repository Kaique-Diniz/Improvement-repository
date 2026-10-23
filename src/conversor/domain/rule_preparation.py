"""Levantamento não executável. Não é PlanoCobranca e não possui ativação."""
from typing import Annotated, Literal

from pydantic import Field

from .base import Data, Id, Modelo, Texto


class CondicaoLevantamento(Modelo):
    campo: Literal['valor_boleto_a_confirmar', 'apontamento', 'dias_atraso', 'juridico_e_prazo', 'cadastro_antecipado']
    operador: Literal['eq', 'gt', 'a_confirmar']
    valor: str | int | None
    namespace: Id | None = None


class RegraEmLevantamento(Modelo):
    id: Id
    condominio_referencia: Literal['TREE_MORUMBI', 'PLAZA_MAYOR_IPIRANGA']
    condicao: CondicaoLevantamento
    escopo: Literal['unidade', 'boleto', 'a_confirmar']
    acao: Literal['excluir', 'incluir', 'bloquear', 'a_confirmar']
    prioridade: Annotated[int, Field(strict=True, ge=0)] | None = None
    vigente_de: Data | None = None
    vigente_ate: Data | None = None
    evidencia: Literal['SOLICITACAO_4_3A']
    situacao_aprovacao: Literal['pendente_aprovacao_humana'] = 'pendente_aprovacao_humana'
    questoes_humanas: Annotated[tuple[Texto, ...], Field(min_length=1)]


class MatrizPreliminar(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    finalidade: Literal['levantamento_nao_executavel'] = 'levantamento_nao_executavel'
    autoriza_ativacao: Literal[False] = False
    regras: Annotated[tuple[RegraEmLevantamento, ...], Field(min_length=1)]


def pendencias_da_matriz(matriz):
    """Triagem estrutural conservadora; não interpreta semântica de textos livres."""
    pendencias = []
    ids = set()
    for r in matriz.regras:
        if r.id in ids:
            pendencias.append((r.id, 'IDENTIFICADOR_DUPLICADO'))
        ids.add(r.id)
        if r.prioridade is None or r.vigente_de is None:
            pendencias.append((r.id, 'PRIORIDADE_OU_VIGENCIA_INCOMPLETA'))
        if r.escopo == 'a_confirmar' or r.acao == 'a_confirmar' or r.condicao.operador == 'a_confirmar':
            pendencias.append((r.id, 'SEMANTICA_OPERACIONAL_AMBIGUA'))
        if r.vigente_de and r.vigente_ate and r.vigente_ate <= r.vigente_de:
            pendencias.append((r.id, 'VIGENCIA_CONTRADITORIA'))
        for anterior in matriz.regras:
            if anterior.id >= r.id or anterior.condominio_referencia != r.condominio_referencia:
                continue
            # Só sinaliza contradição comprovável por condições idênticas; nunca supõe equivalência textual.
            if (anterior.condicao == r.condicao and anterior.escopo == r.escopo and
                    anterior.acao != r.acao and 'a_confirmar' not in (anterior.acao, r.acao) and
                    anterior.prioridade == r.prioridade):
                if (anterior.vigente_ate and r.vigente_de and anterior.vigente_ate <= r.vigente_de) or (
                        r.vigente_ate and anterior.vigente_de and r.vigente_ate <= anterior.vigente_de):
                    continue
                pendencias.append((r.id, 'ACOES_CONTRADITORIAS_EXIGEM_REVISAO'))
    return tuple(sorted(set(pendencias)))
