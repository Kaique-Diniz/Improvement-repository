"""Diagnóstico Itajubá: A1 por lançamento e escopo histórico explícito."""
from datetime import date

from conversor.domain.canonical import RessalvaLeitura
from conversor.readers.itajuba_pdf import originais, TIPOS
from .passaredo_cadastro import associar as associar_a1

POLITICA='itajuba_nome_e_unidade_por_lancamento_A1@1'
INICIO_ESCOPO=date(2023,12,1)


def associar(lote,cadastro=None):
    lote,pessoas,resumo,revisao=associar_a1(lote,cadastro,obter_originais=originais)
    resumo['politica']=POLITICA
    resumo['documentos_rejeitados_no_cadastro']=sum(len(r.valores_originais)for r in cadastro.ressalvas
        if r.codigo=='ITAJUBA_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO')if cadastro is not None else 0
    resumo['emails_rejeitados_no_cadastro']=sum(r.codigo=='ITAJUBA_EMAIL_INVALIDO_NAO_ATRIBUIDO'for r in cadastro.ressalvas)if cadastro is not None else 0
    notes=list(lote.ressalvas)
    for b in lote.boletos:
        if b.vencimento<INICIO_ESCOPO:
            notes.append(RessalvaLeitura(codigo='ITAJUBA_ESCOPO_ANTERIOR_DEZ2023_REQUER_REVISAO',gravidade='critico',
                registro_id=b.id,origens=b.origens,valores_originais=(b.vencimento.isoformat(),
                    'Limite documental conservador pelo vencimento; competencia e responsabilidade da garantidora nao inferidas.')))
    return lote.model_copy(update={'ressalvas':tuple(notes)}),pessoas,resumo,revisao


def rotulo(original,vencimento,parcela):
    return f'{TIPOS[original["tipo"]]} ({vencimento:%m/%Y})'+(f' - {parcela}'if parcela is not None else '')
