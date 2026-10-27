"""Assinaturas e conflitos históricos: apenas fixtures integralmente sintéticas."""
from decimal import Decimal
from io import BytesIO
import json

from openpyxl import load_workbook
import pytest

from conversor.application.debt_descriptions import (POLITICA_BBZ, POLITICA_BBZ_CONDOMINIO,
    POLITICA_BBZ_CONDOMINIO_V11, POLITICAS_BBZ, interpretar_recibo)
from conversor.domain.canonical import Ocorrencia
from conversor.web.service import reconhecer,ler
from tests.bbz.conftest import recibo,unidade
from tests.bbz.cadastro_fixtures import CPF
from tests.bbz.test_innova_diagnostic import financeiro,cadastro_innova,executar,valores


def boleto(componentes):
    raw=financeiro([unidade(recibos=[recibo(componentes=componentes)])])
    p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    return l.boletos[0]


@pytest.mark.parametrize('hist,natureza',[
    ('LOCAÇÃO SALAS','LOCAÇÃO DE SALAS'),('LOCAÇÃO DE SALAS','LOCAÇÃO DE SALAS'),
    ('LOCAÇÃO DE SALAS OUT/31','LOCAÇÃO DE SALAS'),
    ('LOCAÇÃO DE SALAS LOCAÇÃO JUL/2031','LOCAÇÃO DE SALAS'),
    ('FEIRA GASTRONÔMICA 07/2031','FEIRA GASTRONÔMICA'),
    ('FEIRA GASTRONÔMICA 07/2031 FEIRA - JUL/31','FEIRA GASTRONÔMICA'),
    ('ESPORTES REF. 07/2031 BOXE','ESPORTES'),
    ('ESPORTES REF. 07/2031 FIT DANCE','ESPORTES'),
    ('ESPORTES AULAS ABR/31','ESPORTES'),
    ('ESPORTES AULAS- 12 ALUNOS DEZ/31','ESPORTES'),
])
def test_assinaturas_exatas_classificam_natureza_sem_inferir_competencia(hist,natureza):
    b=boleto([(hist,'100.00')]);original=b.model_dump_json()
    d=interpretar_recibo(b,politica=POLITICA_BBZ_CONDOMINIO_V11)
    assert d.estado=='comprovada' and d.descricao==natureza
    assert d.competencia is None and d.estado_competencia=='nao_aplicavel'
    assert b.model_dump_json()==original and len(d.componentes)==1


@pytest.mark.parametrize('hist',[
    'COND DEZ-31','COND JUL-31','LOCAÇÃO DE SALAS ANULADA','LOCAÇÃO DE SALAS OUTRA PESSOA',
    'FEIRA GASTRONÔMICA 07/0000','ESPORTES REF. 07/2031 ATIVIDADE NÃO DOCUMENTADA',
    'OBSERVAÇÃO LOCAÇÃO DE SALAS','LOCAÇÃO DE SALAS PETSHOP',
])
def test_assinaturas_incompletas_ou_texto_livre_permanecem_em_revisao(hist):
    d=interpretar_recibo(boleto([(hist,'100.00')]),politica=POLITICA_BBZ_CONDOMINIO_V11)
    assert d.estado=='pendente' and d.descricao.startswith('RECIBO ') and d.competencia is None


def test_cota_unica_prevalece_com_todos_componentes_preservados():
    b=boleto([('COTA CONDOMINIAL AGO/2031','100'),('LOCAÇÃO DE SALAS','10')])
    d=interpretar_recibo(b,politica=POLITICA_BBZ_CONDOMINIO_V11)
    assert d.estado=='comprovada' and d.descricao=='COTA 08/2031'
    assert len(d.componentes)==2 and sum(c.valor_original for c in d.componentes)==Decimal('110')
    assert 'BBZ_COTA_PRIORIZADA_NA_DESCRICAO' in d.alertas


def test_versoes_anteriores_preservadas_sem_assinaturas_novas():
    b=boleto([('LOCAÇÃO DE SALAS','100')])
    for p in (POLITICA_BBZ,POLITICA_BBZ_CONDOMINIO):
        assert interpretar_recibo(b,politica=p).estado=='pendente'
        assert POLITICAS_BBZ[p.id+'@'+p.versao] is p
    assert POLITICA_BBZ.versao=='1.1.0' and POLITICA_BBZ_CONDOMINIO.versao=='1.0.0'


def test_consumos_mistos_nao_recebem_uma_natureza_principal_por_aproximacao():
    d=interpretar_recibo(boleto([('AGUA - MAI/31','100'),('GAS - MAI/31','10')]),politica=POLITICA_BBZ_CONDOMINIO_V11)
    assert d.estado=='pendente' and len(d.componentes)==2


def preparar_referencia(tmp_path,*,documento='00000000272',mutar=None):
    raw=financeiro();pdf=cadastro_innova();base=tmp_path/'base'
    executar(base,raw,cadastro=pdf)
    before=(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    w=load_workbook(BytesIO(before));s=w['Dados'];s['C2']=documento
    if mutar:mutar(w,s)
    out=BytesIO();w.save(out);w.close()
    return raw,pdf,out.getvalue(),before


def test_documentos_validos_conflitantes_retidos_sem_retirar_divida(tmp_path):
    raw,pdf,ref,before=preparar_referencia(tmp_path)
    r=executar(tmp_path/'depois',raw,cadastro=pdf,referencia=ref)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['boletos_retidos']==0
    info=next(iter(r['cadastro_bbz']['unidades'].values()))
    assert info['estado']=='associacao_retida' and len(info['conflitos_referencia'])==1
    assert info['projecao_antes_da_retencao']['evidencias_documentais'][0]['documento']['valor']==CPF
    assert info['conflitos_referencia'][0]['documento_historico']=='00000000272'
    row=valores(tmp_path/'depois')[1]
    assert row[2] is None and all(v is None for v in row[11:24])
    assert row[29]==100 and r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==0
    assert r['decisoes'][0]['contato']['documento']=='revisao'
    assert r['cadastro_bbz']['resumo']['documentos_ausentes']==0
    canonico=json.loads((tmp_path/'depois/canonico.json').read_text())
    o=next(o for o in canonico['ressalvas']if o['codigo']=='BBZ_DOCUMENTO_HISTORICO_CONFLITANTE_ASSOCIACAO_RETIDA')
    assert {orig['arquivo_id'] for orig in o['origens']}=={'inadimplencia','cadastro','referencia'}
    assert info['financeiro_original']['nome']==row[3]
    assert not r['permite_exportacao_operacional'] and not r['autoriza_cobranca']


@pytest.mark.parametrize('documento',[CPF,'000.000.001-91','00000000270',''])
def test_referencia_identica_formatada_invalida_ou_ausente_nao_fabrica_conflito(tmp_path,documento):
    raw,pdf,ref,before=preparar_referencia(tmp_path,documento=documento)
    r=executar(tmp_path/'depois',raw,cadastro=pdf,referencia=ref)
    assert next(iter(r['cadastro_bbz']['unidades'].values()))['estado']=='vinculado'
    assert (tmp_path/'depois/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==before


@pytest.mark.parametrize('campo,valor',[('D2','OUTRA IDENTIDADE FICTICIA'),('Z2','OUTRO CONDOMINIO FICTICIO'),
    ('B2','CODIGO NAO COMPROVADO'),('G2','COMPLEMENTO NAO COMPROVADO')])
def test_nao_funde_identidades_ou_condominios_por_referencia_parcial(tmp_path,campo,valor):
    raw,pdf,ref,before=preparar_referencia(tmp_path,mutar=lambda w,s:setattr(s[campo],'value',valor))
    r=executar(tmp_path/'depois',raw,cadastro=pdf,referencia=ref)
    assert next(iter(r['cadastro_bbz']['unidades'].values()))['estado']=='vinculado'
    assert (tmp_path/'depois/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==before


def test_evidencias_repetidas_em_linhas_distintas_permanecem_sem_dupla_retencao(tmp_path):
    def duplicar(w,s):s.append([c.value for c in s[2]])
    raw,pdf,ref,before=preparar_referencia(tmp_path,mutar=duplicar)
    r=executar(tmp_path/'depois',raw,cadastro=pdf,referencia=ref)
    info=next(iter(r['cadastro_bbz']['unidades'].values()))
    assert len(info['conflitos_referencia'])==2 and r['cadastro_bbz']['resumo']['associacoes_retidas']==1
    assert {e['origem']['linha'] for e in info['conflitos_referencia']}=={2,3}


def test_retencao_cadastral_nao_remove_bloqueio_critico_preexistente(tmp_path):
    raw,pdf,ref,before=preparar_referencia(tmp_path);p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    critico=Ocorrencia(id='critico_ficticio',processamento_id='hist_ficticio',codigo='RETENCAO_CRITICA_FICTICIA',
        gravidade='critico',escopo='registro',registro_id=l.unidades[0].id)
    r=executar(tmp_path/'depois',raw,cadastro=pdf,referencia=ref,historico=(critico,))
    assert r['resumo']['dividas_efetivamente_geradas']==0
    assert any(o['codigo']=='RETENCAO_CRITICA_FICTICIA'for o in r['ocorrencias'])
