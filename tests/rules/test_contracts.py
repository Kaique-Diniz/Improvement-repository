from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json

import pytest
from pydantic import ValidationError

from conversor.billing_schemas import documentos, main
from conversor.domain.billing_rules import ComandoPlano, PlanoCobranca, hash_modelo


def test_roundtrip_hash_e_politicas_corrigidas(plano):
    assert PlanoCobranca.model_validate_json(plano.model_dump_json()) == plano
    assert hash_modelo(plano) == hash_modelo(PlanoCobranca.model_validate(plano.model_dump()))
    assert plano.politicas.permissao_unidade == 'nao_libera_boleto_inelegivel'
    assert plano.politicas.restricao_unidade == 'excluir_ou_bloquear_prevalece'


@pytest.mark.parametrize('campo,valor', [('estado', 'aprovado'), ('aprovacao', True), ('senha', 'sentinela'),
    ('schema_version','99'), ('versao','1'), ('versao','01.0.0'), ('vigente_de','21/10/2026'),
    ('vigente_ate','2026-01-01'), ('vigente_ate','2025-12-31'), ('natureza','producao'), ('regras',[])])
def test_plano_rejeita_campos_improprios_e_versoes(dados_plano,campo,valor):
    dados_plano[campo]=valor
    with pytest.raises(ValidationError): PlanoCobranca.model_validate(dados_plano)


@pytest.mark.parametrize('quando', [
    {'tipo':'dias_atraso','operador':'aproximadamente','valor':30},
    {'tipo':'dias_atraso','operador':'gt','valor':True},
    {'tipo':'dias_atraso','operador':'gt','valor':30.1},
    {'tipo':'dias_atraso','operador':'gt','valor':'30'},
    {'tipo':'valor_original','operador':'eq','valor':0.01},
    {'tipo':'valor_original','operador':'eq','valor':'0.001'},
    {'tipo':'valor_original','operador':'eq','valor':'NaN'},
    {'tipo':'valor_original','operador':'eq','valor':'1e2'},
    {'tipo':'apontamento','codigo':'J'},
    {'tipo':'expressao','python':'True'},
    {'tipo':'todas','condicoes':[]},
    {'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}},
])
def test_predicados_tipados_sem_coercao_ou_codigo(dados_plano,quando):
    dados_plano['regras'][0]['quando']=quando
    with pytest.raises(ValidationError): PlanoCobranca.model_validate(dados_plano)


@pytest.mark.parametrize('tipo,valor', [('texto','juridico_sintetico'),('booleano',True),('inteiro',10),
    ('dinheiro','10.00'),('data','2026-10-21')])
def test_fatos_tipados_declarados_sem_valor_presumido(dados_plano,tipo,valor):
    dados_plano['fatos']=[{'id':'fato_sintetico','tipo':tipo,'escopo':'unidade'}]
    dados_plano['regras'][0]['quando']={'tipo':'fato','fato_id':'fato_sintetico','operador':'eq','valor':{'tipo':tipo,'valor':valor}}
    assert PlanoCobranca.model_validate(dados_plano).fatos[0].exige_fonte_e_vigencia


@pytest.mark.parametrize('mutacao', ['regra_duplicada','fonte_duplicada','fato_duplicado','fonte_ausente','fato_tipo','fato_escopo','operador_fato','limite','quantificador'])
def test_referencias_limites_e_escopos(dados_plano,mutacao):
    regra=dados_plano['regras'][0]
    if mutacao=='regra_duplicada':dados_plano['regras']*=2
    elif mutacao=='fonte_duplicada':dados_plano['fontes']*=2
    elif mutacao=='fato_duplicado':dados_plano['fatos']=[{'id':'x','tipo':'texto','escopo':'unidade'}]*2
    elif mutacao=='fonte_ausente':regra['fonte_id']='inexistente'
    elif mutacao in ('fato_tipo','fato_escopo','operador_fato'):
        dados_plano['fatos']=[{'id':'x','tipo':'texto','escopo':'boleto'}]
        regra['quando']={'tipo':'fato','fato_id':'x','operador':'gt'if mutacao=='operador_fato'else'eq',
            'valor':{'tipo':'inteiro','valor':1}if mutacao=='fato_tipo'else{'tipo':'texto','valor':'x'}}
        if mutacao=='fato_escopo':regra['alvo']='unidade'
    elif mutacao=='limite':
        for _ in range(17):regra['quando']={'tipo':'nao','condicao':regra['quando']}
    else:regra['quando']={'tipo':'existe_boleto','condicao':regra['quando']}
    with pytest.raises(ValidationError):PlanoCobranca.model_validate(dados_plano)


def test_exclusao_unidade_quantificador_e_arvore_sem_executar(dados_plano):
    r=dados_plano['regras'][0];r['alvo']='unidade';r['acao']='excluir'
    r['quando']={'tipo':'qualquer','condicoes':[
        {'tipo':'existe_boleto','condicao':{'tipo':'apontamento','codigo':'J','namespace':'namespace_sintetico'}},
        {'tipo':'todos_boletos','condicao':{'tipo':'nao','condicao':{'tipo':'valor_original','operador':'ne','valor':'0.01'}}}]}
    p=PlanoCobranca.model_validate(dados_plano)
    assert p.regras[0].alvo=='unidade'


@pytest.mark.parametrize('politica,valor', [('bloqueios_criticos','ignorar'),('permissao_unidade','libera_todos'),
    ('restricao_unidade','boleto_prevalece'),('empate_incompativel','primeira_regra'),('lacuna','incluir')])
def test_politicas_nao_podem_contornar_restricoes(dados_plano,politica,valor):
    dados_plano['politicas'][politica]=valor
    with pytest.raises(ValidationError):PlanoCobranca.model_validate(dados_plano)


def test_hash_inclui_condominio_versao_fontes_condicoes_e_politicas(plano):
    for campo,valor in [('versao','2.0.0'),('condominio_id','cond_outro'),('vigente_ate','2028-01-01')]:
        outro=PlanoCobranca.model_validate(plano.model_dump()|{campo:valor})
        assert hash_modelo(outro)!=hash_modelo(plano)
    dados=plano.model_dump();dados['regras'][0]['prioridade']=999
    assert hash_modelo(PlanoCobranca.model_validate(dados))!=hash_modelo(plano)
    with pytest.raises(ValidationError):plano.versao='2.0.0'


@pytest.mark.parametrize('acao', ['criar','submeter','aprovar','ativar','revogar','rejeitar'])
def test_comandos_exigem_informacoes_explicitas(plano,acao):
    dados={'acao':acao,'plano_id':plano.id,'em':'2026-10-21T10:00:00Z','fundamento':'Exemplo sintético','evidencia_id':'evidencia_teste'}
    if acao=='criar':dados['plano']=plano
    if acao=='ativar':dados['data_ref']='2026-10-21'
    comando=ComandoPlano.model_validate(dados)
    assert comando.em.tzinfo is not None
    for campo in ('em','fundamento','evidencia_id'):
        sem=deepcopy(dados);sem.pop(campo)
        with pytest.raises(ValidationError):ComandoPlano.model_validate(sem)


@pytest.mark.parametrize('mudanca', [{'em':'2026-10-21T10:00:00'}, {'fundamento':'  '},
    {'data_ref':'2026-10-21'}, {'responsavel_id':'autoproclamado'}, {'aprovado':True}])
def test_comando_rejeita_identidade_injetada_e_dados_ambiguos(plano,mudanca):
    dados={'acao':'submeter','plano_id':plano.id,'em':'2026-10-21T10:00:00Z','fundamento':'Sintético','evidencia_id':'teste'}|mudanca
    with pytest.raises(ValidationError):ComandoPlano.model_validate(dados)


def test_schemas_publicados_reproduziveis_e_sem_campos_extras(tmp_path):
    assert main(['--check'])==0
    assert main(['--saida',str(tmp_path)])==0
    for nome,conteudo in documentos():
        assert (tmp_path/nome).read_text()==conteudo
        schema=json.loads(conteudo)
        assert schema['$schema'].endswith('2020-12/schema') and schema['additionalProperties']is False
    (tmp_path/'plano.schema.json').write_text('{}')
    assert main(['--saida',str(tmp_path),'--check'])==1


@pytest.mark.parametrize('em',[1720000000,1720000000.5,True,'2026-10-21','2026-10-21T12:00:00'])
def test_instante_nao_e_epoch_nem_data_sem_fuso(plano,em):
    with pytest.raises(ValidationError):
        ComandoPlano(acao='submeter',plano_id=plano.id,em=em,fundamento='Sintético',evidencia_id='teste')


def test_fato_nao_pode_omitir_exigencia_de_fonte_por_coercao(dados_plano):
    dados_plano['fatos']=[{'id':'x','tipo':'texto','escopo':'unidade','exige_fonte_e_vigencia':1}]
    with pytest.raises(ValidationError):PlanoCobranca.model_validate(dados_plano)
