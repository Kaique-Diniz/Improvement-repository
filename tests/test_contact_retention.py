"""Motivos distintos e sobrepostos; sem dados de documentos reais."""
from types import SimpleNamespace as Obj
import json

import pytest

from conversor.application.contact_retention import classificar_retencoes
from conversor.application.conversion_validation import validar_conversao
from conversor.web.service import analisar,PedidoDiagnostico
from tests.test_conversion_validation import _cenario
from tests.bbz.test_abrolhos import financeiro,referencia,cadastral,REF
from tests.bbz.conftest import unidade,recibo
from tests.bbz.cadastro_fixtures import ficha


def test_65_sem_pertencimento_e_dois_conflitos_sao_evidencias_distintas():
    escopo=Obj(unidades=[Obj(unidade_id=f'u{i}',estado='nao_comprovado')for i in range(65)])
    cad={'unidades':{f'u{i}':{'estado':'escopo_nao_comprovado','motivos':['DESTINO_TORRE_NAO_COMPROVADO'],
                            'dados_retidos':['documentos','telefones','emails']}for i in range(65)}}
    pendencias={f'c{i}':[Obj(codigo='DOCUMENTOS_VALIDOS_CONFLITANTES')]for i in range(2)}
    r=classificar_retencoes(pendencias_persistentes=pendencias,cadastro=cad,escopo=escopo)
    assert len(r)==67
    assert sum('PERTENCIMENTO_NAO_COMPROVADO'in motivos for motivos in r.values())==65
    assert sum('CONFLITO_DOCUMENTAL'in motivos for motivos in r.values())==2
    assert not any(set(m)-{'PERTENCIMENTO_NAO_COMPROVADO','CONFLITO_DOCUMENTAL'}for m in r.values())


def test_sobreposicao_e_outros_motivos_nao_sao_deduzidos_por_subtracao():
    escopo=Obj(unidades=[Obj(unidade_id='ambos',estado='nao_comprovado')])
    cad={'unidades':{'outro':{'dados_retidos':['documentos','emails'],'motivos':['TITULAR_DIVERGENTE_ENTRE_FONTES']},
                     'sem_motivo':{'dados_retidos':['documentos'],'motivos':[]}}}
    r=classificar_retencoes(pendencias_persistentes={'ambos':[Obj(codigo='DOCUMENTOS_VALIDOS_CONFLITANTES')]},cadastro=cad,escopo=escopo)
    assert set(r['ambos'])=={'PERTENCIMENTO_NAO_COMPROVADO','CONFLITO_DOCUMENTAL'}
    assert r['outro']==('OUTRA_RESTRICAO_CADASTRAL',)and r['sem_motivo']==('MOTIVO_NAO_CLASSIFICADO',)


def test_chamada_legada_preserva_campos_sem_afirmar_conflito_inexistente(tmp_path):
    arq,reg,infos,ds=_cenario(tmp_path)
    r=validar_conversao(arq,registros=reg,linhas_info=infos,decisoes=ds,unidades_contato_retido={'u1'})
    assert r['versao']=='validacao_conversao@2'
    i=r['indicadores'];assert i['unidades_contato_retido']==i['linhas_com_contato_retido']==1
    assert i['unidades_conflito_documental']==0 and i['unidades_outros_dados_protegidos']==1
    assert i['linhas_financeiras_contatos_retidos']==1
    assert not any(v['codigo']=='CONFLITO_DOCUMENTAL_IDENTIFICADO'for v in r['registros'])


def test_unidade_com_varios_motivos_e_contada_uma_vez_em_cada_conjunto(tmp_path):
    arq,reg,infos,ds=_cenario(tmp_path)
    r=validar_conversao(arq,registros=reg,linhas_info=infos,decisoes=ds,
        motivos_contato_retido={'u1':('CONFLITO_DOCUMENTAL','CONFLITO_DOCUMENTAL','OUTRA_RESTRICAO_CADASTRAL')})
    i=r['indicadores'];assert i['unidades_contato_retido']==i['unidades_conflito_documental']==i['unidades_outros_dados_protegidos']==1


@pytest.mark.parametrize('modo',['A','B'])
def test_fluxo_real_do_servico_separa_unidades_de_boletos_e_conflitos(tmp_path,modo):
    raw=financeiro([
        unidade(bloco='D',numero='A00001',recibos=[recibo(),recibo(id='99000002',due=REF)]),
        unidade(bloco='E',numero='A00002',recibos=[recibo(id='99000003')]),
        unidade(bloco='D',numero='A00003',recibos=[recibo(id='99000004'),recibo(id='99000005')])])
    def docs(w,s):
        for n in range(2,s.max_row+1):s.cell(n,3).value='00000000272'
    ref=referencia(raw,incluir={'D/A00001','E/A00002'},mutar=docs)
    cad=cadastral([ficha(bloco='D',numero='A00001'),ficha(bloco='E',numero='A00002'),ficha(bloco='D',numero='A00003')],total=3)
    result=analisar(raw,PedidoDiagnostico(data_ref=REF,modo=modo),processamento_id='indicadores_sinteticos',destino=tmp_path,referencia=ref,cadastro=cad)
    v=result['validacao_conversao'];i=v['indicadores']
    assert v['estado']=='conforme_com_ressalvas'
    assert (i['unidades_escopo_comprovado'],i['unidades_escopo_pendente'],i['unidades_conflito_documental'])==(2,1,2)
    assert i['unidades_contato_retido']==3 and i['unidades_outros_dados_protegidos']==0
    assert i['boletos_em_revisao']==2 and i['linhas_financeiras_contatos_retidos']==2
    assert i['linhas_divida']==2 and i['linhas_cadastrais']==(1 if modo=='B'else 0)
    assert i['linhas_com_contato_retido']==2
    assert not any(v['codigo']=='CONFLITO_DOCUMENTAL_IDENTIFICADO'and v.get('unidade')=='A00003'for v in v['registros'])
    assert all(token not in json.dumps(v)for token in ('00000000191','00000000272','CONTATO INTEGRALMENTE FICTICIO'))
    assert not result['autoriza_cobranca']and not result['permite_exportacao_operacional']
