"""Planos aprovados só em temporários, com a autoridade sintética do 4.1."""
from datetime import date

import pytest

from tests.rules.conftest import seguranca, gestor, repo
from tests.rules.test_plan_repository import aprovar, executar
from conversor.application.billing_evaluation import SimularCobranca
from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.domain.billing_evaluation import EntradaSimulacao, SolicitacaoSimulacao, FatoEvidenciado
from conversor.domain.billing_rules import PlanoCobranca, hash_modelo
from conversor.domain.canonical import LoteCanonico, Origem


def regra(id_='inclusao_didatica',*,acao='incluir',prioridade=10,alvo='boleto',quando=None):
    condicao=quando or {'tipo':'valor_original','operador':'gt','valor':'0.00'}
    if alvo=='unidade'and quando is None:condicao={'tipo':'existe_boleto','condicao':condicao}
    return {'id':id_,'prioridade':prioridade,'alvo':alvo,'quando':condicao,'acao':acao,
            'motivo_codigo':'MOTIVO_SINTETICO','fonte_id':'requisito_didatico'}


def fato(id_='f1',*,valor=True,tipo='booleano',fato_id='juridico',unidade_id='unidade_a',boleto_id=None,
         vigente_de='2026-01-01',vigente_ate='2027-01-01',confirmacao='comprovado'):
    return FatoEvidenciado(id=id_,fato_id=fato_id,condominio_id='cond_sintetico',unidade_id=unidade_id,
        boleto_id=boleto_id,valor={'tipo':tipo,'valor':valor},vigente_de=vigente_de,vigente_ate=vigente_ate,
        confirmacao=confirmacao,origens=(Origem(arquivo_id='comprovante_'+id_,sha256='0'*64,
            leitor_versao='fixture_sintetica',pagina=1,linha=1,identificador='linha_fato'),))


@pytest.fixture
def preparar(repo,gestor,origem,unidade,boleto,pessoa):
    def construir(*,regras=None,definicoes=(),lote=None,fatos=(),ocorrencias=(),coberturas=(),data_ref=date(2026,10,21),ativar=True,estado=None):
        plano=PlanoCobranca(id='plano_simulacao',condominio_id='cond_sintetico',versao='1.0.0',natureza='sintetico',
            vigente_de='2026-01-01',vigente_ate='2027-01-01',
            fontes=(Origem(arquivo_id='requisitos_sinteticos',sha256='0'*64,leitor_versao='fixture4.2',pagina=1,
                           linha=1,identificador='requisito_didatico'),),fatos=definicoes,regras=regras or (regra(),))
        estado=estado or('ativo'if ativar else'aprovado')
        for acao,nome in [('criar','rascunho'),('submeter','aguardando_aprovacao'),('aprovar','aprovado'),('ativar','ativo')]:
            executar(repo,plano,gestor,acao,data_ref=date(2026,10,21)if acao=='ativar'else None)
            if estado==nome:break
        entrada=EntradaSimulacao(lote=lote or LoteCanonico(unidades=(unidade,),boletos=(boleto,),pessoas=(pessoa,)),
            fatos=fatos,ocorrencias_anteriores=ocorrencias,coberturas_apontamentos=coberturas)
        solicitacao=SolicitacaoSimulacao(processamento_id='simulacao_sintetica',condominio_id=plano.condominio_id,
            plano_id=plano.id,plano_versao=plano.versao,plano_hash=hash_modelo(plano),ambiente='sintetico',data_ref=data_ref)
        return SimularCobranca(repo,VerificadorPlanosJSON(repo)),solicitacao,entrada,plano
    return construir
