from datetime import date
from decimal import Decimal

import pytest
from pydantic import TypeAdapter

from conversor.domain.billing_rules import Condicao, ErroPlano, PredicadoDias
from conversor.domain.billing_evaluation import CoberturaApontamentos
from conversor.domain.canonical import Apontamento, Boleto, LoteCanonico
from conversor.rules.conditions import ContextoCondicao, avaliar_condicao
from tests.evaluation.conftest import fato, regra


@pytest.mark.parametrize('operador,valor,esperado', [
    ('eq',34,'verdadeiro'),('ne',34,'falso'),('gt',34,'falso'),('gte',34,'verdadeiro'),
    ('lt',34,'falso'),('lte',34,'verdadeiro'),('gt',33,'verdadeiro'),('lt',35,'verdadeiro')])
def test_dias_limites_explicitos(preparar,operador,valor,esperado):
    r=regra(quando={'tipo':'dias_atraso','operador':operador,'valor':valor})
    serv,req,entrada,p=preparar(regras=(r,));ctx=ContextoCondicao(p,entrada,req.data_ref,entrada.lote.unidades[0],entrada.lote.boletos[0])
    passo=avaliar_condicao(p.regras[0].quando,ctx)
    assert passo.resultado==esperado and passo.observados[0].valor==34 and passo.origens


def test_vencimento_futuro_tem_atraso_assinado(preparar):
    serv,req,entrada,p=preparar(data_ref=date(2026,9,16))
    c=PredicadoDias(tipo='dias_atraso',operador='eq',valor=-1)
    passo=avaliar_condicao(c,ContextoCondicao(p,entrada,req.data_ref,entrada.lote.unidades[0],entrada.lote.boletos[0]))
    assert passo.resultado=='verdadeiro' and passo.observados[0].valor==-1


@pytest.mark.parametrize('operador,valor,esperado', [('eq','100.00','verdadeiro'),('ne','100.00','falso'),
    ('gt','100.00','falso'),('gte','100.00','verdadeiro'),('lt','100.01','verdadeiro'),('lte','99.99','falso')])
def test_valor_original_sem_somar_encargos_ou_saldo(preparar,operador,valor,esperado):
    serv,req,e,p=preparar(regras=(regra(quando={'tipo':'valor_original','operador':operador,'valor':valor}),))
    passo=avaliar_condicao(p.regras[0].quando,ContextoCondicao(p,e,req.data_ref,e.lote.unidades[0],e.lote.boletos[0]))
    assert passo.resultado==esperado and passo.observados[0].valor=='100.00'
    assert e.lote.boletos[0].saldo_acumulado==Decimal('300.00')


@pytest.mark.parametrize('tipo,valor,tipo_esperado,esperado,operador,resultado', [
    ('booleano',False,'booleano',False,'eq','verdadeiro'),
    ('texto','status_literal','texto','STATUS_LITERAL','eq','falso'),
    ('inteiro',12,'inteiro',11,'gt','verdadeiro'),
    ('dinheiro','0.10','dinheiro','0.09','gt','verdadeiro'),
    ('data','2026-10-01','data','2026-10-02','lt','verdadeiro')])
def test_fatos_tipados_sem_normalizacao_presumida(preparar,tipo,valor,tipo_esperado,esperado,operador,resultado):
    decl=({'id':'juridico','tipo':tipo,'escopo':'unidade'},)
    quando={'tipo':'fato','fato_id':'juridico','operador':operador,'valor':{'tipo':tipo_esperado,'valor':esperado}}
    s,r,e,p=preparar(regras=(regra(quando=quando),),definicoes=decl,fatos=(fato(tipo=tipo,valor=valor),))
    passo=avaliar_condicao(p.regras[0].quando,ContextoCondicao(p,e,r.data_ref,e.lote.unidades[0],e.lote.boletos[0]))
    assert passo.resultado==resultado and passo.fatos_ids==('f1',) and passo.origens


@pytest.mark.parametrize('fatos,motivo', [
    ((),'FATO_AUSENTE_OU_FORA_VIGENCIA'),
    ((fato(vigente_ate='2026-10-21'),),'FATO_AUSENTE_OU_FORA_VIGENCIA'),
    ((fato(vigente_de='2026-10-22'),),'FATO_AUSENTE_OU_FORA_VIGENCIA'),
    ((fato(confirmacao='nao_confirmado'),),'FATO_NAO_CONFIRMADO'),
    ((fato(),fato('f2',valor=False)),'FATOS_CONTRADITORIOS')])
def test_lacunas_contradicoes_e_vigencias(preparar,fatos,motivo):
    c={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(regras=(regra(quando=c),),definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),fatos=fatos)
    passo=s.executar(r,e).boletos[0].avaliacoes[0].passo
    assert passo.resultado=='indeterminado'and passo.motivo_codigo==motivo


@pytest.mark.parametrize('tipo,esperado', [('todas','falso'),('qualquer','verdadeiro')])
def test_logica_tres_valores_nao_bloqueia_ramo_irrelevante(preparar,tipo,esperado):
    constante={'tipo':'valor_original','operador':'eq','valor':'99.99'if tipo=='todas'else'100.00'}
    ausente={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(regras=(regra(quando={'tipo':tipo,'condicoes':[constante,ausente]}),),
        definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},))
    passo=s.executar(r,e).boletos[0].avaliacoes[0].passo
    assert passo.resultado==esperado and len(passo.filhos)==2
    assert passo.filhos[1].resultado=='indeterminado'


@pytest.mark.parametrize('valor,esperado', [('100.00','falso'),('99.99','verdadeiro')])
def test_negacao(preparar,valor,esperado):
    s,r,e,p=preparar(regras=(regra(quando={'tipo':'nao','condicao':{'tipo':'valor_original','operador':'eq','valor':valor}}),))
    assert s.executar(r,e).boletos[0].avaliacoes[0].passo.resultado==esperado


def test_negacao_de_desconhecido_nao_vira_permissao(preparar):
    c={'tipo':'nao','condicao':{'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}}
    s,r,e,p=preparar(regras=(regra(quando=c),),definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},))
    assert s.executar(r,e).boletos[0].situacao=='pendente_revisao'


@pytest.mark.parametrize('apontamento,cobertura,resultado', [('J',False,'verdadeiro'),('AJ',False,'indeterminado'),
    (None,False,'indeterminado'),('AJ',True,'falso'),(None,True,'falso')])
def test_apontamento_exige_namespace_e_cobertura_negativa(preparar,boleto,unidade,origem,apontamento,cobertura,resultado):
    aps=(Apontamento(codigo_original=apontamento,namespace_formato='namespace_teste',origem=origem),)if apontamento else()
    b=Boleto.model_validate(boleto.model_dump()|{'apontamentos':aps})
    lote=LoteCanonico(unidades=(unidade,),boletos=(b,))
    cob=(CoberturaApontamentos(boleto_id=b.id,namespace='namespace_teste',origens=(origem,)),)if cobertura else()
    s,r,e,p=preparar(lote=lote,coberturas=cob,regras=(regra(quando={'tipo':'apontamento','codigo':'J','namespace':'namespace_teste'}),))
    assert s.executar(r,e).boletos[0].avaliacoes[0].passo.resultado==resultado


def test_operador_adulterado_nao_e_executado(preparar):
    s,r,e,p=preparar()
    c=PredicadoDias(tipo='dias_atraso',operador='eq',valor=34).model_copy(update={'operador':'eval'})
    with pytest.raises(ErroPlano,match='OPERADOR_NAO_SUPORTADO'):
        avaliar_condicao(c,ContextoCondicao(p,e,r.data_ref,e.lote.unidades[0],e.lote.boletos[0]))
