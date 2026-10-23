from datetime import date
from decimal import Decimal

import pytest

from conversor.domain.canonical import Boleto, LoteCanonico
from tests.evaluation.conftest import regra, fato


@pytest.mark.parametrize('acao_maior,acao_menor,situacao',[('incluir','excluir','elegivel_na_simulacao'),
    ('excluir','incluir','excluido'),('adiar','incluir','pendente_revisao')])
def test_prioridade_maior_no_boleto(preparar,acao_maior,acao_menor,situacao):
    s,r,e,p=preparar(regras=(regra('menor',acao=acao_menor,prioridade=1),regra('maior',acao=acao_maior,prioridade=9)))
    d=s.executar(r,e).boletos[0]
    assert d.situacao==situacao and d.regras_decisivas==('maior',)
    assert len(d.avaliacoes)==2


@pytest.mark.parametrize('acao1,acao2',[('incluir','excluir'),('incluir','adiar'),('excluir','adiar')])
def test_empates_incompativeis_exigem_revisao(preparar,acao1,acao2):
    s,r,e,p=preparar(regras=(regra('a',acao=acao1),regra('b',acao=acao2)))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='pendente_revisao' and d.motivo_codigo=='EMPATE_INCOMPATIVEL'and d.revisao_humana
    assert d.regras_decisivas==('a','b')


def test_empate_compativel_preserva_ambas_as_justificativas(preparar):
    s,r,e,p=preparar(regras=(regra('z'),regra('a')))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='elegivel_na_simulacao' and d.regras_decisivas==('a','z')


@pytest.mark.parametrize('alvo',['unidade','boleto'])
def test_bloqueio_de_regra_nao_e_superado_por_permissao(preparar,alvo):
    s,r,e,p=preparar(regras=(regra('permissao',prioridade=999),regra('bloqueio',acao='bloquear',prioridade=1,alvo=alvo)))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='bloqueado'and d.revisao_humana


def test_empate_com_bloqueio_permanece_bloqueado_e_auditado(preparar):
    s,r,e,p=preparar(regras=(regra('permitir'),regra('bloquear',acao='bloquear')))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='bloqueado'and d.motivo_regras=='EMPATE_INCOMPATIVEL_COM_BLOQUEIO'
    assert d.revisao_humana and d.regras_decisivas==('bloquear','permitir')


@pytest.mark.parametrize('acao',['incluir','excluir','adiar','alertar'])
def test_regras_falsas_nao_autorizam_nem_excluem(preparar,acao):
    s,r,e,p=preparar(regras=(regra(acao=acao,quando={'tipo':'valor_original','operador':'eq','valor':'777.00'}),))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='pendente_revisao'and d.motivo_codigo=='SEM_REGRA_DE_BOLETO_APLICAVEL'


def test_alerta_sozinho_nao_autoriza(preparar):
    s,r,e,p=preparar(regras=(regra('aviso',acao='alertar'),))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='pendente_revisao'and d.avaliacoes[0].passo.resultado=='verdadeiro'


def test_alerta_acumula_sem_suprimir_decisao_individual(preparar):
    s,r,e,p=preparar(regras=(regra('aviso',acao='alertar',prioridade=999),regra('incluir')))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='elegivel_na_simulacao'and d.regras_decisivas==('incluir',)
    assert {a.regra_id for a in d.avaliacoes}=={'aviso','incluir'}


def test_permissao_generica_unidade_nao_libera_boleto(preparar):
    s,r,e,p=preparar(regras=(regra('permitir_unidade',alvo='unidade'),))
    assert s.executar(r,e).boletos[0].situacao=='pendente_revisao'


def test_permissao_unidade_nao_anula_ineligibilidade_individual(preparar):
    s,r,e,p=preparar(regras=(regra('permitir_unidade',alvo='unidade',prioridade=999),regra('excluir_boleto',acao='excluir')))
    assert s.executar(r,e).boletos[0].situacao=='excluido'


def test_exclusao_unidade_atinge_boleto_gatilho_e_demais(preparar,unidade,boleto):
    b2=Boleto.model_validate(boleto.model_dump()|{'id':'boleto_b','identificador':'sintetico_002',
        'vencimento':'2026-10-20','composicao':{'total_original':'7.00','itens':[{'codigo':'teste',
        'valor':'7.00','origem':boleto.origens[0]}]}})
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,b2))
    cond={'tipo':'existe_boleto','condicao':{'tipo':'valor_original','operador':'eq','valor':'7.00'}}
    s,r,e,p=preparar(lote=lote,regras=(regra('excluir_unidade',alvo='unidade',acao='excluir',quando=cond,prioridade=1),
        regra('incluir_individual',prioridade=999)))
    rel=s.executar(r,e)
    assert [d.situacao for d in rel.boletos]==['excluido','excluido']
    assert rel.unidades[0].situacao=='excluido'
    for d in rel.boletos:
        assert d.motivo_codigo=='EXCLUSAO_TERMINAL_DA_UNIDADE'
        assert d.regras_decisivas==('excluir_unidade',)
        q=d.avaliacoes[0].passo
        gatilho=next(f for f in q.filhos if f.resultado=='verdadeiro')
        assert gatilho.boleto_id=='boleto_b'and gatilho.origens


def test_empate_de_unidade_exige_revisao_integral(preparar):
    s,r,e,p=preparar(regras=(regra('unidade_excluir',acao='excluir',alvo='unidade'),
        regra('unidade_incluir',alvo='unidade'),regra('boleto_incluir',prioridade=100)))
    assert s.executar(r,e).boletos[0].situacao=='pendente_revisao'


def test_exclusao_individual_nao_exclui_outro_boleto(preparar,unidade,boleto):
    b2=Boleto.model_validate(boleto.model_dump()|{'id':'boleto_b','identificador':'sintetico002','vencimento':'2026-10-20'})
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,b2))
    s,r,e,p=preparar(lote=lote,regras=(regra('base'),regra('excluir',acao='excluir',prioridade=99,
        quando={'tipo':'dias_atraso','operador':'gt','valor':20})))
    rel=s.executar(r,e)
    assert [d.situacao for d in rel.boletos]==['excluido','elegivel_na_simulacao']
    assert rel.unidades[0].motivo_codigo=='UNIDADE_COM_DECISOES_MISTAS'


@pytest.mark.parametrize('alvo',['unidade','boleto'])
def test_fato_indeterminado_impede_inclusao_mesmo_com_regra_permissiva(preparar,alvo):
    cond={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(regras=(regra('base',prioridade=100),regra('incerta',alvo=alvo,acao='excluir',quando=cond,prioridade=1)),
        definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='pendente_revisao'and d.regras_decisivas==('incerta',)


@pytest.mark.parametrize('alvo',['unidade','boleto'])
def test_adiar_retencao_sem_autorizacao(preparar,alvo):
    s,r,e,p=preparar(regras=(regra('adiamento',acao='adiar',alvo=alvo),))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='pendente_revisao'and d.revisao_humana


@pytest.mark.parametrize('quantificador,resultado',[('existe_boleto','falso'),('todos_boletos','indeterminado')])
def test_unidade_vazia_nao_e_incluida_por_quantificador(preparar,unidade,quantificador,resultado):
    lote=LoteCanonico(unidades=(unidade,),boletos=())
    s,r,e,p=preparar(lote=lote,regras=(regra('regra_unidade',alvo='unidade',quando={
        'tipo':quantificador,'condicao':{'tipo':'valor_original','operador':'gt','valor':'0.00'}}),))
    rel=s.executar(r,e)
    assert not rel.boletos and rel.unidades[0].situacao=='pendente_revisao'
    assert rel.unidades[0].avaliacoes[0].passo.resultado==resultado


@pytest.mark.parametrize('operador,valor,situacao',[('gt','0.00','excluido'),('eq','100.00','elegivel_na_simulacao')])
def test_todos_boletos_avalia_o_conjunto_inteiro(preparar,unidade,boleto,operador,valor,situacao):
    b2=Boleto.model_validate(boleto.model_dump()|{'id':'boleto_b','identificador':'sintetico002',
        'composicao':{'total_original':'7.00','itens':[{'codigo':'teste','valor':'7.00','origem':boleto.origens[0]}]}})
    cond={'tipo':'todos_boletos','condicao':{'tipo':'valor_original','operador':operador,'valor':valor}}
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,b2)),regras=(
        regra('restricao',alvo='unidade',acao='excluir',quando=cond),regra('permissao_boleto')))
    rel=s.executar(r,e)
    assert all(d.situacao==situacao for d in rel.boletos)
    assert len(rel.unidades[0].avaliacoes[0].passo.filhos)==2
