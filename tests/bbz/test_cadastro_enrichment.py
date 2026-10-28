from datetime import date
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.domain.canonical import Ocorrencia
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import analisar,PedidoDiagnostico,reconhecer,ler
from tests.bbz.conftest import planilha,unidade,recibo
from tests.bbz.cadastro_fixtures import cadastro,ficha,NOME,CPF,CNPJ
from tests.web.test_mvp import KEY,aguardar


def analisar_ficha(tmp_path,*,rows=None,modo='A',financeiro=None,total=1,**kwargs):
    raw=financeiro or planilha()
    return analisar(raw,PedidoDiagnostico(data_ref='2026-10-26',modo=modo),processamento_id='sintetico',
        destino=tmp_path,cadastro=cadastro(rows or [ficha()],total=total),**kwargs)


def linhas(tmp_path):
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(w['Dados'].values);w.close();return rows


def test_reconhecimento_identidade_sem_filename_e_codigo_origem_com_zeros():
    p,c,l=reconhecer(cadastro(),cadastro=True)
    assert p['codigo_easycollector']=='884'and c=='287'and l=='bbz_cadastro_geral_pdf_v1'


@pytest.mark.parametrize('documento',[CPF,CNPJ])
def test_documento_cadastral_com_nome_comprovado_textual_e_zero_inicial(tmp_path,documento):
    r=analisar_ficha(tmp_path,rows=[ficha(documento=documento)])
    assert r['resumo']['dividas_efetivamente_geradas']==1
    assert r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');s=w['Dados']
    assert s['C2'].value==documento and s['C2'].data_type=='s'and s['C2'].number_format=='@'
    assert s['D2'].value==NOME and s.max_column==30;w.close()


@pytest.mark.parametrize('documento',['','00000000190','00000000000190'])
def test_documentos_opcionais_ausentes_invalidos_nao_alteram_elegibilidade(tmp_path,documento):
    r=analisar_ficha(tmp_path,rows=[ficha(documento=documento)])
    assert r['resumo']['dividas_efetivamente_geradas']==1 and linhas(tmp_path)[1][2]is None
    assert not r['permite_exportacao_operacional']and not r['autoriza_cobranca']


def test_conflito_titular_nao_transfere_cpf_contatos_nem_muda_nome_financeiro(tmp_path):
    r=analisar_ficha(tmp_path,rows=[ficha(nome='OUTRO TITULAR TOTALMENTE FICTICIO')])
    row=linhas(tmp_path)[1]
    assert row[3]==NOME and row[2]is None and all(v is None for v in row[11:24])
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['cadastro_bbz']['resumo']['conflitos_titulares']==1
    info=next(iter(r['cadastro_bbz']['unidades'].values()))
    assert info['estado']=='associacao_retida'and info['cadastro_original']['nome']!=info['financeiro_original']['nome']
    assert any(o['codigo']=='TITULAR_DIVERGENTE_ENTRE_FONTES'and o['gravidade']=='alerta'for o in r['ocorrencias'])


def test_conflito_de_documentos_retido_na_associacao_sem_liberacao_silenciosa(tmp_path):
    r=analisar_ficha(tmp_path,rows=[ficha(segundo_documento='00000000272')])
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==1
    assert r['resumo']['dividas_efetivamente_geradas']==1 and linhas(tmp_path)[1][2]is None
    f=next(iter(r['cadastro_bbz']['unidades'].values()))['ficha']
    assert len(next(p for p in f['participantes']if p['papel']=='titular')['documentos'])==2


def test_proprietario_distinto_do_locatario_pagador_e_obs_nao_misturam_contatos(tmp_path):
    r=analisar_ficha(tmp_path,rows=[ficha(locatario=True,pagador=True,
        observacao='CPF: 00000000272; EMAIL outro@example.invalid')])
    row=linhas(tmp_path)[1]
    assert row[2]==CPF and row[21]=='titular@example.invalid'
    assert 'locatario@example.invalid'not in row and 'outro@example.invalid'not in row
    info=next(iter(r['cadastro_bbz']['unidades'].values()))
    assert info['estado']=='vinculado'and {'locatario','pagador'}<=set(info['dados_nao_utilizados_por_papel'])


def test_documento_somente_do_pagador_nao_completa_o_titular(tmp_path):
    r=analisar_ficha(tmp_path,rows=[ficha(documento='',pagador=True)])
    assert linhas(tmp_path)[1][2]is None and r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==0


@pytest.mark.parametrize('codigo',['BBZ_CADASTRO_FICHA_ORIGINAL','BBZ_CADASTRO_IDENTIDADE_E_COMPLETUDE'])
def test_contrato_cadastral_incompleto_tem_erro_explicito(codigo):
    from conversor.application.bbz_cadastro import cruzar_cadastro_bbz
    raw=planilha();p,c,l=reconhecer(raw);fin,_=ler(raw,p,c,l,'inadimplencia')
    pdf=cadastro();p,c,l=reconhecer(pdf,cadastro=True);cad,_=ler(pdf,p,c,l,'cadastro')
    incompleto=cad.model_copy(update={'ressalvas':tuple(r for r in cad.ressalvas if r.codigo!=codigo)})
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_CONTRATO_INCOMPLETO'):cruzar_cadastro_bbz(fin,incompleto)


def test_modo_B_nao_inclui_todo_cadastro_e_campos_de_divida_ficam_vazios(tmp_path):
    raw=planilha([unidade(recibos=[recibo(),recibo(id='99000002',due=date(2026,10,1))])])
    r=analisar_ficha(tmp_path,rows=[ficha(),ficha('000002')],modo='B',financeiro=raw,total=2)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==1
    assert r['cadastro_bbz']['resumo']['unidades_cadastrais_lidas']==2
    assert r['cadastro_bbz']['resumo']['unidades_financeiras_localizadas']==1
    assert len(linhas(tmp_path))==3 and all(v is None for v in linhas(tmp_path)[-1][24:30])


def test_mesmo_cliente_em_duas_unidades_nao_transfere_documentos(tmp_path):
    raw=planilha([unidade(),unidade(numero='000002',recibos=[recibo(id='99000002')])])
    r=analisar_ficha(tmp_path,rows=[ficha(),ficha('000002',documento='00000000272')],financeiro=raw,total=2)
    assert [row[2]for row in linhas(tmp_path)[1:]]==[CPF,'00000000272']


def test_bloqueio_critico_financeiro_nao_e_contornado_por_cadastro(tmp_path):
    raw=planilha();p,c,l=reconhecer(raw);lote,_=ler(raw,p,c,l,'inadimplencia')
    o=Ocorrencia(id='critico_ficticio',processamento_id='hist_sintetico',codigo='RETENCAO_FICTICIA',
        gravidade='critico',escopo='registro',registro_id=lote.unidades[0].id)
    r=analisar_ficha(tmp_path,financeiro=raw,historico=(o,))
    assert r['resumo']['dividas_efetivamente_geradas']==0 and r['reavaliacoes_historicas']==[]
    assert any(x['codigo']=='RETENCAO_FICTICIA'for x in r['ocorrencias'])


def test_endereco_privado_tem_prioridade_e_cobranca_externa_nunca_e_aplicada(tmp_path):
    from conversor.export.identifiers import EnderecoPadrao
    dados={'logradouro':'Rua Privada Ficticia','numero':'77','bairro':'Bairro Privado','cidade':'Cidade Privada','uf':'SP','cep':'00000009'}
    config=EnderecoPadrao(endereco=dados,evidencia={'arquivo':'config_ficticia.json','sha256':'a'*64,
        'aba':'configuracao_sintetica','celulas':{'endereco':'declaracao_sintetica'}})
    r=analisar_ficha(tmp_path,buscar_endereco=lambda a,c:config)
    row=linhas(tmp_path)[1]
    assert row[4]=='Rua Privada Ficticia'and row[5]=='77'and row[7]=='00000009'
    assert row[6]=='BL-UNI0001'and r['cadastro_bbz']['divergencias_endereco_configurado']
    assert 'Rua de Correspondencia'not in row[4]


@pytest.mark.parametrize('codigo,nome',[('117','CONDOMINIO EDIFICIO WIN'),('999','OUTRO CONDOMINIO FICTICIO')])
def test_cadastro_respeita_habilitacao_incremental(codigo,nome):
    if codigo=='117':
        assert reconhecer(cadastro(codigo=codigo,nome=nome),cadastro=True)[0]['id']=='edificio_win'
        return
    with pytest.raises(ErroLeitura,match='CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO|CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):
        reconhecer(cadastro(codigo=codigo,nome=nome),cadastro=True)


def test_upload_comum_com_e_sem_cadastro_autenticacao_download_e_reinicio(tmp_path):
    area=tmp_path/'privado'
    with TestClient(criar_app(area,acesso=KEY))as c:
        assert c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'A'},files={'inadimplencia':('f.xlsx',planilha())}).status_code==401
        c.post('/api/session',json={'chave':KEY})
        r=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'B'},files={
            'inadimplencia':('QUALQUER_NOME.xlsx',planilha()),'cadastro':('OUTRO_NOME.pdf',cadastro(protecao='permitida'))}))
        assert r['estado']=='concluido'and r['resultado']['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1
        assert c.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409
        raw=c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').content
        w=load_workbook(BytesIO(raw));assert w['Dados']['C2'].value==CPF;w.close()
        r2=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'A'},files={'inadimplencia':('QUALQUER_NOME.xlsx',planilha())}))
        assert 'cadastro_bbz'not in r2['resultado']and r2['resultado']['resumo']['dividas_efetivamente_geradas']==1
        assert (area/'processamentos'/r['id']/'cadastro_bbz_original.json').exists()
    with TestClient(criar_app(area,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        assert c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').status_code==404
        novo=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'A'},files={
            'inadimplencia':('f.xlsx',planilha()),'cadastro':('c.pdf',cadastro())}))
        assert novo['resultado']['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1
