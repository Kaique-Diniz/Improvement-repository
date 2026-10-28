"""WIN: exemplos integralmente sintéticos e sem dados de clientes."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError

from conversor.domain.canonical import Ocorrencia
from conversor.domain.identity import chave_unidade
from conversor.export.identifiers import PerfilIdentificadores
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import analisar, PedidoDiagnostico, reconhecer, ler, PERFIS
from tests.bbz.conftest import planilha, unidade, recibo
from tests.bbz.cadastro_fixtures import cadastro, ficha, CPF
from tests.web.test_mvp import KEY, aguardar

REF=date(2026,10,26)


def financeiro(unidades=None, *, codigo='117', **kwargs):
    return planilha(unidades,codigo=codigo,nome='CONDOMINIO EDIFICIO WIN',**kwargs)


def perfil_sintetico():
    return {'id':'win_ficticio','versao':'1','uso':'diagnostico_nao_operacional','administradora_id':'adm_bbz',
        'condominio_id':'cond_bbz_edificio_win','nome_cedente':'BBZ','produto':'CONDOMINIO FICTICIO WIN',
        'largura_unidade':4,'torres':{},'codificador':'bloco_tipo_unidade','sufixo_cedente':'567',
        'formatos_unidade':[
            {'bloco_original':'0','tipo':'numerica','bloco_cedente':'00','bloco_complemento':'0',
             'prefixo_cedente':'UNID','prefixo_complemento':'UNI','largura_cedente':4,'largura_complemento':1},
            {'bloco_original':'VG','tipo':'literal','bloco_cedente':'00','bloco_complemento':'0','padrao_literal':'VG[0-9]{3}[MPG]'}],
        'evidencia':{'arquivo':'template_integralmente_ficticio.xls','sha256':'a'*64,'aba':'Ficticio',
            'celulas':{'mapa':'B2:G4; somente fixture fabricada'}}}


def executar(tmp_path,raw=None,modo='A',**kwargs):
    path=tmp_path/'perfil_sintetico.json';tmp_path.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps([perfil_sintetico()]))
    return analisar(raw or financeiro(),PedidoDiagnostico(data_ref=REF,modo=modo,condominio='edificio_win'),
        processamento_id='win_sintetico',destino=tmp_path,perfis_saida=path,**kwargs)


def rows(path):
    w=load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');r=list(w['Dados'].values);w.close();return r


@pytest.mark.parametrize('codigo',['117','0117','000117'])
def test_codigo_origem_preservado_sem_confundir_destino(codigo):
    p,c,f=reconhecer(financeiro(codigo=codigo))
    assert c==codigo and p['codigo_easycollector']=='567' and p['condominio_id']=='cond_bbz_edificio_win'
    assert p['identidade_integracao']['codigo_origem_observado']==codigo
    assert f=='bbz_inadimplencia_xlsx_v1' and PERFIS['edificio_win']['dias']==31
    assert PERFIS['edificio_win']['vigente_de'] is None


@pytest.mark.parametrize('codigo,nome',[('567','CONDOMINIO EDIFICIO WIN'),('117','CONDOMINIO NOVA YORK PENTHOUSES'),
    ('287','CONDOMINIO EDIFICIO WIN')])
def test_codigo_e_nome_devem_concordar(codigo,nome):
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):
        reconhecer(planilha(codigo=codigo,nome=nome))


@pytest.mark.parametrize('dias,elegivel',[(30,False),(31,False),(32,True),(61,True),(62,True),(4000,True)])
def test_dias_corridos_antiguidade_nao_vira_filtro_judicial(tmp_path,dias,elegivel):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(due=REF-timedelta(days=dias))])]))
    assert r['resumo']['dividas_efetivamente_geradas']==int(elegivel)
    assert r['resumo']['boletos_nao_selecionados_prazo']==int(not elegivel)


@pytest.mark.parametrize('due',[date(2010,1,5),'05/01/2010','2010-01-05'])
def test_datas_antigas_validas_e_encargos_preservados(tmp_path,due):
    raw=financeiro([unidade(recibos=[recibo(due=due,emissao='01/10',
        componentes=[('COTA CONDOMINIAL JAN/2010','100'),('DESCONTO COTA CONDOMINIAL','-1')],encargos=('2','3','4'))])])
    r=executar(tmp_path,raw);row=rows(tmp_path)[1]
    assert row[26]=='COTA 01/2010' and row[29]==99 and row[28].date()==date(2010,1,5)
    c=json.loads((tmp_path/'canonico.json').read_text())['boletos'][0]
    assert c['emissao'] is None and c['emissao_original']=='01/10'
    assert (Decimal(c['multa']),Decimal(c['correcao']),Decimal(c['juros']))==(Decimal(2),Decimal(3),Decimal(4))
    assert [Decimal(i['valor'])for i in c['composicao']['itens']]==[Decimal(100),Decimal(-1)]


def test_vencimento_com_ano_abreviado_nao_ganha_seculo(tmp_path):
    with pytest.raises(ErroLeitura,match='BBZ_DATA_INVALIDA'):
        executar(tmp_path,financeiro([unidade(recibos=[recibo(due='05/08/16')])]))


@pytest.mark.parametrize('hist,descricao,competencia',[
    ('CONDOMINIO AGO/2016','COTA 08/2016','2016-08'),
    ('CONDOMINIO AGO/16','RECIBO 99000001',None),
    ('COTA CONDOMINIAL AGO/2016','COTA 08/2016','2016-08'),
    ('REEMBOLSO SINISTRO','REEMBOLSO SINISTRO',None),
    ('HISTORICO INSUFICIENTE FICTICIO','RECIBO 99000001',None)])
def test_natureza_documental_sem_inferir_por_emissao_vencimento(tmp_path,hist,descricao,competencia):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(componentes=[(hist,'100')])])]))
    assert rows(tmp_path)[1][26]==descricao and r['decisoes'][0]['competencia']==competencia
    assert r['resumo']['dividas_efetivamente_geradas']==1


@pytest.mark.parametrize('marcador',[None,'A','AJ','J','AE'])
def test_centavo_e_marcadores_nao_aplicam_veto_tree(tmp_path,marcador):
    raw=financeiro([unidade(recibos=[recibo(marcador=marcador,componentes=[('COTA CONDOMINIAL AGO/2016','0.01')],
        due=date(2016,8,5)),recibo(id='99000002')])])
    r=executar(tmp_path,raw);assert r['resumo']['dividas_efetivamente_geradas']==2 and r['resumo']['cotas_excluidas_por_veto']==0
    p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    assert l.boletos[0].composicao.total_original==Decimal('.01') and len(l.boletos[0].apontamentos)==int(bool(marcador))
    assert any(row[29]==.01 for row in rows(tmp_path)[1:])


def test_centavo_componente_nao_e_total_do_recibo(tmp_path):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(componentes=[('COTA CONDOMINIAL AGO/2016','100'),
        ('FUNDO DE RESERVA','0.01')])])]))
    assert rows(tmp_path)[1][29]==100.01 and r['resumo']['dividas_efetivamente_geradas']==1


def test_zero_e_prazo_modob_um_cadastro_por_unidade(tmp_path):
    raw=financeiro([unidade(recibos=[recibo(),recibo(id='99000002',due=REF),
        recibo(id='99000003',componentes=[('AJUSTE FICTICIO','0')])])])
    a=executar(tmp_path/'A',raw);b=executar(tmp_path/'B',raw,modo='B')
    assert a['resumo']['dividas_efetivamente_geradas']==b['resumo']['dividas_efetivamente_geradas']==1
    assert a['resumo']['cadastros_adicionais']==0 and b['resumo']['cadastros_adicionais']==1
    assert b['resumo']['boletos_nao_selecionados_zero']==1 and b['resumo']['boletos_nao_selecionados_prazo']==1
    assert rows(tmp_path/'A')[1]==rows(tmp_path/'B')[1] and all(v is None for v in rows(tmp_path/'B')[-1][24:30])
    assert len(json.loads((tmp_path/'B/canonico_extraido.json').read_text())['boletos'])==3


def test_sem_cadastro_e_estado_explicito_sem_copiar_historico(tmp_path):
    r=executar(tmp_path/'base');ref=(tmp_path/'base/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    w=load_workbook(BytesIO(ref));w['Dados']['C2']=CPF;w['Dados']['M2']='900000001';w['Dados']['V2']='ficticio@example.invalid';out=BytesIO();w.save(out);w.close()
    b=executar(tmp_path/'depois',referencia=out.getvalue())
    assert b['cadastro_complementar']['codigo']=='CADASTRO_GERAL_NAO_FORNECIDO'
    ocorr=[o for o in b['ocorrencias']if o['codigo']=='CADASTRO_GERAL_NAO_FORNECIDO']
    assert len(ocorr)==1 and ocorr[0]['gravidade']=='informativo' and ocorr[0]['escopo']=='processamento'
    row=rows(tmp_path/'depois')[1];assert row[2]is None and all(v is None for v in row[11:24])
    assert (tmp_path/'depois/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==ref
    manifest=json.loads((tmp_path/'depois/manifesto_diagnostico.json').read_text())
    assert manifest['cadastro_complementar']==b['cadastro_complementar']


def test_cadastro_futuro_compativel_zero_origem_e_papel(tmp_path):
    pdf=cadastro([ficha(locatario=True,pagador=True)],codigo='0117',nome='CONDOMINIO EDIFICIO WIN')
    r=executar(tmp_path,financeiro(codigo='000117'),cadastro=pdf)
    assert r['cadastro_complementar']['estado']=='fornecido' and r['cadastro_complementar']['codigo']is None
    assert r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1 and rows(tmp_path)[1][2]==CPF
    assert not any(o['codigo']=='CADASTRO_GERAL_NAO_FORNECIDO'for o in r['ocorrencias'])


def test_cadastro_outro_condominio_bloqueado(tmp_path):
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):
        executar(tmp_path,cadastro=cadastro())


@pytest.mark.parametrize('bloco,numero,cedente,complemento',[
    ('0','000001','BL00-UNID0001-567','BL0-UNI1'),('0','000002','BL00-UNID0002-567','BL0-UNI2'),
    ('VG','VG990M','BL00-VG990M-567','BL0-VG990M')])
def test_codificacao_explicita_nao_padroniza_larguras_nem_bloco_canonico(tmp_path,bloco,numero,cedente,complemento):
    raw=financeiro([unidade(numero=numero,bloco=bloco)]);r=executar(tmp_path,raw);row=rows(tmp_path)[1]
    assert row[1]==row[24]==cedente and row[6]==complemento
    assert r['decisoes'][0]['bloco']==bloco and r['decisoes'][0]['unidade']==numero
    assert len(r['codificacao_template']['unidades'])==1
    evidencia=next(iter(r['codificacao_template']['unidades'].values()))['evidencia_codificacao']
    assert evidencia['formato']['bloco_original']==bloco
    assert evidencia['sha256_original_referencia']=='a'*64 and evidencia['formato']


def test_unidade_fora_do_padrao_documentado_fica_provisoria(tmp_path):
    r=executar(tmp_path,financeiro([unidade(numero='999999')]))
    cod=next(iter(r['codificacao_template']['unidades'].values()))
    assert cod['estado']=='provisorio' and cod['motivo']=='UNIDADE_FORA_DA_LARGURA_DOCUMENTADA'
    assert cod['cedente']=='0/999999' and not r['permite_exportacao_operacional']


@pytest.mark.parametrize('mudanca,erro',[
    ('bloco','FORMATOS_DE_UNIDADE_AMBIGUOS_OU_INCOMPLETOS'),('sufixo','FORMATOS_DE_UNIDADE_AMBIGUOS_OU_INCOMPLETOS'),
    ('torres','FORMATOS_DE_UNIDADE_AMBIGUOS_OU_INCOMPLETOS'),('regex','PADRAO_LITERAL_DE_UNIDADE_INVALIDO'),
    ('numerico','PADRAO_LITERAL_INCOMPATIVEL'),('prefixo','PREFIXO_DE_UNIDADE_INVALIDO')])
def test_formato_ambiguo_ou_inseguro_rejeitado(mudanca,erro):
    p=perfil_sintetico();f=p['formatos_unidade']
    if mudanca=='bloco':f[1]['bloco_original']='0'
    elif mudanca=='sufixo':p['sufixo_cedente']=None
    elif mudanca=='torres':p['torres']={'0':'0'}
    elif mudanca=='regex':f[1]['padrao_literal']='.*'
    elif mudanca=='numerico':f[0]['padrao_literal']='VG[0-9]{3}[MPG]'
    else:f[0]['prefixo_cedente']='1a'
    with pytest.raises(ValidationError,match=erro):PerfilIdentificadores.model_validate(p)


def test_nova_unidade_valida_nao_presume_linha_no_historico(tmp_path):
    r=executar(tmp_path,financeiro([unidade(numero='001234')]))
    c=next(iter(r['codificacao_template']['unidades'].values()))
    assert c['cedente']=='BL00-UNID1234-567' and c['complemento']=='BL0-UNI1234'
    assert 'não presume' in c['evidencia_codificacao']['limite']
    assert not r['permite_exportacao_operacional']


def test_bloqueio_critico_nao_e_contornado(tmp_path):
    raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    o=Ocorrencia(id='bloqueio_ficticio',processamento_id='hist_ficticio',codigo='CRITICO_FICTICIO',
        gravidade='critico',escopo='registro',registro_id=l.unidades[0].id)
    r=executar(tmp_path,raw,historico=(o,))
    assert r['resumo']['dividas_efetivamente_geradas']==0


def test_idempotencia_de_canonico_e_xlsx(tmp_path):
    a=executar(tmp_path/'um');b=executar(tmp_path/'dois')
    assert a['decisoes']==b['decisoes']
    for nome in ('canonico.json','canonico_extraido.json','TESTE_LOCAL_NAO_IMPORTAR.xlsx'):
        assert (tmp_path/'um'/nome).read_bytes()==(tmp_path/'dois'/nome).read_bytes()


def test_upload_comum_e_download_autenticado_sem_cadastro(tmp_path):
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY))as c:
        assert c.get('/api/condominios').status_code==401
        c.post('/api/session',json={'chave':KEY})
        for modo in ('A','B'):
            j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':modo,'condominio':'edificio_win'},
                files={'inadimplencia':('nome_que_nao_comprova_identidade.xlsx',financeiro())}))
            assert j['estado']=='concluido' and j['resultado']['resumo']['dividas_efetivamente_geradas']==1
            assert j['resultado']['cadastro_complementar']['codigo']=='CADASTRO_GERAL_NAO_FORNECIDO'
            assert c.get('/api/processamentos/'+j['id']+'/operacional.xlsx').status_code==409
            w=load_workbook(BytesIO(c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').content));assert w['Dados'].max_column==30;w.close()


def test_abrolhos_e_formato_desconhecido_permanecem_bloqueados():
    with pytest.raises(ErroLeitura,match='CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO'):
        reconhecer(planilha(codigo='575',nome='CONDOMINIO JARDINS DO BRASIL'))
    with pytest.raises(ErroLeitura):reconhecer(b'arquivo inteiramente ficticio')
