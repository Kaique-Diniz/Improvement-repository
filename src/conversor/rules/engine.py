"""Candidatos e resolução pura. Somente o serviço verificado produz o relatório."""
from dataclasses import dataclass

from conversor.domain.billing_evaluation import AvaliacaoRegra
from .conditions import ContextoCondicao, avaliar_condicao


@dataclass(frozen=True)
class ResolucaoDiagnostica:
    situacao: str
    motivo: str
    regras: tuple[str, ...]
    revisao_humana: bool


def avaliar_regras(plano,entrada,data_ref,unidade,boleto=None):
    alvo='boleto'if boleto else'unidade'
    fontes={f.identificador:f for f in plano.fontes}
    return tuple(AvaliacaoRegra(regra_id=r.id,plano_versao=plano.versao,prioridade=r.prioridade,
        alvo=r.alvo,unidade_id=unidade.id,boleto_id=boleto.id if boleto else None,
        acao=r.acao,motivo_codigo=r.motivo_codigo,fonte_regra=fontes[r.fonte_id],condicao=r.quando,
        passo=avaliar_condicao(r.quando,ContextoCondicao(plano,entrada,data_ref,unidade,boleto)))
        for r in sorted(plano.regras,key=lambda r:(-r.prioridade,r.id))if r.alvo==alvo)


def resolver_candidatos(unidade,boleto):
    """Política conservadora; o relatório mantém todos os candidatos e razões.

    Bloqueios de segurança são aplicados fora desta função e dominam este resultado.
    Adiar não autoriza: fica pendente. Permissão de unidade é apenas contexto.
    """
    todos=(*unidade,*boleto)
    def decisao(situacao,motivo,regras):
        return ResolucaoDiagnostica(situacao,motivo,tuple(sorted({r.regra_id for r in regras})),
            situacao in ('bloqueado','pendente_revisao'))
    verdadeiros=[r for r in todos if r.passo.resultado=='verdadeiro'and r.acao!='alertar']
    conflitos={}
    # Empates de ações diferentes no maior nível aplicável do mesmo escopo.
    for alvo in ('unidade','boleto'):
        candidatos=[r for r in verdadeiros if r.alvo==alvo]
        if candidatos:
            maior=max(r.prioridade for r in candidatos)
            empatados=[r for r in candidatos if r.prioridade==maior]
            if len({r.acao for r in empatados})>1:
                conflitos[alvo]=empatados
    bloqueios=[r for r in verdadeiros if r.acao=='bloquear']
    if bloqueios:
        motivo='EMPATE_INCOMPATIVEL_COM_BLOQUEIO'if conflitos else'REGRA_DE_BLOQUEIO'
        return decisao('bloqueado',motivo,(*bloqueios,*(r for rs in conflitos.values()for r in rs)))
    incertos_unidade=[r for r in unidade if r.passo.resultado=='indeterminado'and r.acao!='alertar']
    if incertos_unidade:return decisao('pendente_revisao','CONDICAO_INDETERMINADA',incertos_unidade)
    if 'unidade'in conflitos:return decisao('pendente_revisao','EMPATE_INCOMPATIVEL',conflitos['unidade'])
    exclusoes=[r for r in verdadeiros if r.alvo=='unidade'and r.acao=='excluir']
    if exclusoes:return decisao('excluido','EXCLUSAO_TERMINAL_DA_UNIDADE',exclusoes)
    adiamentos=[r for r in verdadeiros if r.alvo=='unidade'and r.acao=='adiar']
    if adiamentos:return decisao('pendente_revisao','ADIAMENTO_DA_UNIDADE_REQUER_REVISAO',adiamentos)
    incertos=[r for r in boleto if r.passo.resultado=='indeterminado'and r.acao!='alertar']
    if incertos:return decisao('pendente_revisao','CONDICAO_INDETERMINADA',incertos)
    if 'boleto'in conflitos:return decisao('pendente_revisao','EMPATE_INCOMPATIVEL',conflitos['boleto'])
    candidatos=[r for r in verdadeiros if r.alvo=='boleto']
    if not candidatos:return decisao('pendente_revisao','SEM_REGRA_DE_BOLETO_APLICAVEL',())
    maior=max(r.prioridade for r in candidatos)
    vencedores=[r for r in candidatos if r.prioridade==maior]
    acao=vencedores[0].acao
    situacoes={'incluir':'elegivel_na_simulacao','excluir':'excluido','adiar':'pendente_revisao'}
    motivos={'incluir':'REGRA_INDIVIDUAL_SATISFEITA','excluir':'EXCLUSAO_INDIVIDUAL',
             'adiar':'BOLETO_ADIADO_POR_REGRA'}
    return decisao(situacoes[acao],motivos[acao],vencedores)
