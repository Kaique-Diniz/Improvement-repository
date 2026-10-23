"""Avaliação pura de condições 4.1, sem decisão financeira ou I/O."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import operator

from conversor.domain.billing_rules import (PlanoCobranca, Todas, Qualquer, Nao, ExisteBoleto,
    TodosBoletos, PredicadoDias, PredicadoValor, PredicadoApontamento, PredicadoFato,
    ValorInteiro, ValorDinheiro, ErroPlano, hash_modelo)
from conversor.domain.billing_evaluation import EntradaSimulacao, PassoCondicao
from conversor.domain.canonical import Boleto, Unidade

OPERADORES = {'eq':operator.eq, 'ne':operator.ne, 'gt':operator.gt,
              'gte':operator.ge, 'lt':operator.lt, 'lte':operator.le}


def valor_comparavel(valor):
    return Decimal(valor.valor) if valor.tipo == 'dinheiro' else valor.valor


def origens_unicas(origens):
    mapa = {hash_modelo(o):o for o in origens}
    return tuple(mapa[k]for k in sorted(mapa))


def combinar(tipo, resultados):
    if tipo in ('todas','todos_boletos'):
        if 'falso'in resultados:return 'falso'
        return 'indeterminado'if'indeterminado'in resultados else'verdadeiro'
    if 'verdadeiro'in resultados:return'verdadeiro'
    return'indeterminado'if'indeterminado'in resultados else'falso'


@dataclass(frozen=True)
class ContextoCondicao:
    plano: PlanoCobranca
    entrada: EntradaSimulacao
    data_ref: date
    unidade: Unidade
    boleto: Boleto | None = None


def avaliar_condicao(condicao, contexto: ContextoCondicao, caminho='raiz') -> PassoCondicao:
    """Resultado diagnóstico; não pode autorizar cobrança ou exportação."""
    c=condicao;ctx=contexto;b=ctx.boleto
    if hasattr(c,'operador')and c.operador not in OPERADORES:
        raise ErroPlano('OPERADOR_NAO_SUPORTADO')
    def passo(resultado,motivo,*,filhos=(),origens=(),observados=(),fatos_ids=()):
        return PassoCondicao(caminho=caminho,tipo=c.tipo,resultado=resultado,motivo_codigo=motivo,
            boleto_id=b.id if b else None,filhos=filhos,
            origens=origens_unicas((*origens,*(o for f in filhos for o in f.origens))),
            observados=observados,fatos_ids=tuple(sorted(set((*fatos_ids,*(x for f in filhos for x in f.fatos_ids))))))
    if isinstance(c,(Todas,Qualquer)):
        filhos=tuple(avaliar_condicao(f,ctx,f'{caminho}.{i}')for i,f in enumerate(c.condicoes))
        return passo(combinar(c.tipo,[f.resultado for f in filhos]),'LOGICA_COMPOSTA',filhos=filhos)
    if isinstance(c,Nao):
        filho=avaliar_condicao(c.condicao,ctx,caminho+'.0')
        inverso={'verdadeiro':'falso','falso':'verdadeiro','indeterminado':'indeterminado'}
        return passo(inverso[filho.resultado],'NEGACAO_TRES_VALORES',filhos=(filho,))
    if isinstance(c,(ExisteBoleto,TodosBoletos)):
        boletos=sorted((x for x in ctx.entrada.lote.boletos if x.unidade_id==ctx.unidade.id),key=lambda x:x.id)
        filhos=tuple(avaliar_condicao(c.condicao,ContextoCondicao(ctx.plano,ctx.entrada,ctx.data_ref,ctx.unidade,x),
                                 caminho+'.'+x.id)for x in boletos)
        if not filhos:
            return passo('indeterminado'if isinstance(c,TodosBoletos)else'falso','UNIDADE_SEM_BOLETOS')
        return passo(combinar(c.tipo,[f.resultado for f in filhos]),'QUANTIFICADOR_EXPLICITO',filhos=filhos)
    if isinstance(c,(PredicadoDias,PredicadoValor)):
        if b is None:return passo('indeterminado','BOLETO_NAO_DISPONIVEL')
        if isinstance(c,PredicadoDias):
            observado=ValorInteiro(tipo='inteiro',valor=(ctx.data_ref-b.vencimento).days);esperado=c.valor
        else:
            observado=ValorDinheiro(tipo='dinheiro',valor=format(b.composicao.total_original,'.2f'));esperado=Decimal(c.valor)
        resultado=OPERADORES[c.operador](valor_comparavel(observado),esperado)
        return passo('verdadeiro'if resultado else'falso','COMPARACAO_TIPADA',origens=b.origens,observados=(observado,))
    if isinstance(c,PredicadoApontamento):
        if b is None:return passo('indeterminado','BOLETO_NAO_DISPONIVEL')
        positivos=[a for a in b.apontamentos if a.namespace_formato==c.namespace and a.codigo_original==c.codigo]
        if positivos:return passo('verdadeiro','APONTAMENTO_EXPLICITO',origens=tuple(a.origem for a in positivos))
        cobertura=next((x for x in ctx.entrada.coberturas_apontamentos if x.boleto_id==b.id and x.namespace==c.namespace),None)
        if cobertura:return passo('falso','AUSENCIA_COM_COBERTURA_EXPLICITA',origens=cobertura.origens)
        return passo('indeterminado','APONTAMENTO_SEM_COBERTURA',origens=b.origens)
    if isinstance(c,PredicadoFato):
        definicao=next(f for f in ctx.plano.fatos if f.id==c.fato_id)
        if definicao.escopo=='boleto'and b is None:
            return passo('indeterminado','BOLETO_NAO_DISPONIVEL')
        fatos=[f for f in ctx.entrada.fatos if f.fato_id==c.fato_id and f.unidade_id==ctx.unidade.id
               and (f.boleto_id==b.id if definicao.escopo=='boleto'and b else f.boleto_id is None)]
        fatos=sorted(fatos,key=lambda f:f.id)
        vigentes=[f for f in fatos if f.vigente_de<=ctx.data_ref and(f.vigente_ate is None or ctx.data_ref<f.vigente_ate)]
        fontes=tuple(o for f in fatos for o in f.origens)
        ids=tuple(f.id for f in fatos)
        if not vigentes:return passo('indeterminado','FATO_AUSENTE_OU_FORA_VIGENCIA',origens=fontes,fatos_ids=ids)
        observados=tuple(f.valor for f in vigentes)
        if any(f.confirmacao!='comprovado'for f in vigentes):
            return passo('indeterminado','FATO_NAO_CONFIRMADO',origens=fontes,observados=observados,fatos_ids=ids)
        valores={valor_comparavel(f.valor)for f in vigentes}
        if len(valores)!=1:return passo('indeterminado','FATOS_CONTRADITORIOS',origens=fontes,observados=observados,fatos_ids=ids)
        resultado=OPERADORES[c.operador](next(iter(valores)),valor_comparavel(c.valor))
        return passo('verdadeiro'if resultado else'falso','FATO_COMPROVADO',origens=fontes,observados=observados,fatos_ids=ids)
    raise ErroPlano('CONDICAO_NAO_SUPORTADA')
