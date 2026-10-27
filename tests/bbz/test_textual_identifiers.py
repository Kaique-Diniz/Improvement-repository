from datetime import date
import json

import pytest
from pydantic import ValidationError

from conversor.export.identifiers import PerfilIdentificadores,registrar_codigo_integracao
from conversor.readers.text_support import ErroLeitura
from conversor.web.service import analisar,PedidoDiagnostico,PERFIS_SAIDA_PATH
from tests.web.test_template_identifiers import unidade
from tests.bbz.conftest import unidade as unidade_planilha,recibo


def perfil(**kw):
    data={'id':'perfil_ficticio','versao':'1','uso':'diagnostico_nao_operacional','administradora_id':'adm_bbz','condominio_id':'cond_bbz_nova_york',
        'nome_cedente':'ADMINISTRADORA FICTICIA','produto':'CONDOMINIO FICTICIO','largura_unidade':4,'torres':{},'codificador':'bloco_unidade_textual',
        'evidencia':{'arquivo':'configuracao_sintetica.json','sha256':'a'*64,'aba':'declaracao','celulas':{'cedente':'padrao_sintetico'}}}
    return PerfilIdentificadores.model_validate(data|kw)


def u(bloco,numero):return unidade(bloco,numero,condominio='cond_bbz_nova_york',admin='adm_bbz')


@pytest.mark.parametrize('bloco,numero', [('0','BOXE'),('0','CACHOQ'),('0','CALDO'),('A','0017'),('B','0016'),('C','0025'),('I','0022'),('S','0013'),('T','0025')])
def test_codificacao_textual_literal_com_capitalizacao_e_zeros(bloco,numero):
    origem=u(bloco,numero);raw=origem.model_dump();p=perfil()
    assert p.codificar(origem,administradora_id='adm_bbz')==(f'Bloc{bloco}-Uni{numero}',)*2
    assert p.codificar(origem,administradora_id='adm_bbz')==p.codificar(origem,administradora_id='adm_bbz')
    assert origem.model_dump()==raw


@pytest.mark.parametrize('bloco,numero',[('A','00X1'),('00','000017'),('INAT','LOJA_FICTICIA'),('b','BoxeFicticio')])
def test_nao_forca_inteiro_caixa_ou_bloco_zero(bloco,numero):
    code,_=perfil().codificar(u(bloco,numero),administradora_id='adm_bbz')
    assert code==f'Bloc{bloco}-Uni{numero}'


def test_largura_numerica_somente_com_configuracao_explicita_preserva_origem():
    p=perfil(tratamento_unidade_numerica='largura_comprovada');original=u('A','000017')
    assert p.codificar(original,administradora_id='adm_bbz')[0]=='BlocA-Uni0017'
    assert original.unidade_original=='000017'
    assert p.codificar(u('A','00X1'),administradora_id='adm_bbz')[0]=='BlocA-Uni00X1'
    with pytest.raises(ErroLeitura,match='UNIDADE_FORA_DA_LARGURA_DOCUMENTADA'):p.codificar(u('A','12345'),administradora_id='adm_bbz')


def test_nao_habilita_mapeamento_implicito_entre_blocos():
    with pytest.raises(ValidationError,match='CODIFICACAO_TEXTUAL_NAO_PRESUME_EQUIVALENCIA_DE_BLOCOS'):perfil(torres={'INAT':'0'})


@pytest.mark.parametrize('valor',[' UNIDADE','UNIDADE ','LOJA 1','LOJA\x00','LOJA\n1'])
def test_texto_ambiguo_retido(valor):
    with pytest.raises(ErroLeitura,match='IDENTIFICADOR_TEXTUAL_AMBIGUO'):perfil().codificar(u('A',valor),administradora_id='adm_bbz')


def test_colisao_de_representacao_entre_pares_distintos_bloqueia():
    p=perfil();a=u('A-UniB','C');b=u('A','B-UniC');c1,_=p.codificar(a,administradora_id='adm_bbz');c2,_=p.codificar(b,administradora_id='adm_bbz')
    assert c1==c2
    vistos={};registrar_codigo_integracao(vistos,c1,'primeira',a.origem)
    with pytest.raises(ErroLeitura,match='CEDENTE_AMBIGUO_APOS_CODIFICACAO'):registrar_codigo_integracao(vistos,c2,'segunda',b.origem)


def test_controle_de_colisao_idempotente_da_mesma_unidade():
    vistos={};registrar_codigo_integracao(vistos,'CODIGO_FICTICIO','unidade');registrar_codigo_integracao(vistos,'CODIGO_FICTICIO','unidade')
    assert vistos=={'CODIGO_FICTICIO':'unidade'}


def test_fluxo_diagnostico_reutiliza_codificador_textual_e_contrato_sem_duplicacao(xlsx,tmp_path):
    dados=json.loads(PERFIS_SAIDA_PATH.read_bytes());dados[-1]=perfil().model_dump(mode='json')
    path=tmp_path/'perfis.json';path.write_text(json.dumps(dados));raw=xlsx([unidade_planilha(numero='LOJA_FICTICIA',bloco='A')])
    r=analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path/'resultado',perfis_saida=path)
    cod=next(iter(r['codificacao_template']['unidades'].values()))
    assert cod['cedente']==cod['contrato']==cod['complemento']=='BlocA-UniLOJA_FICTICIA'
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not r['autoriza_cobranca']


def test_colisao_no_fluxo_impede_materializacao(xlsx,tmp_path):
    dados=json.loads(PERFIS_SAIDA_PATH.read_bytes());dados[-1]=perfil().model_dump(mode='json')
    path=tmp_path/'perfis.json';path.write_text(json.dumps(dados))
    raw=xlsx([unidade_planilha(numero='C',bloco='A-UniB'),unidade_planilha(numero='B-UniC',bloco='A',recibos=[recibo(id='99000002')])])
    with pytest.raises(ErroLeitura,match='CEDENTE_AMBIGUO_APOS_CODIFICACAO'):
        analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo='A'),processamento_id='sintetico',destino=tmp_path/'resultado',perfis_saida=path)
    assert not(tmp_path/'resultado/TESTE_LOCAL_NAO_IMPORTAR.xlsx').exists()
