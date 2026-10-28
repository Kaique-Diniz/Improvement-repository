"""NOVA REBOUÇAS: fontes fabricadas do zero; nenhum dado pessoal de clientes."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.domain.canonical import Ocorrencia
from conversor.export.identifiers import EnderecoPadrao
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web.service import analisar, PedidoDiagnostico, reconhecer, ler, PERFIS
from tests.bbz.conftest import planilha, unidade, recibo
from tests.bbz.cadastro_fixtures import cadastro, ficha, dividir, CPF, ENDERECO
from tests.web.test_mvp import KEY, aguardar

REF = date(2026, 10, 26)


def financeiro(unidades=None, **kwargs):
    return planilha(unidades, codigo='286', nome='CONDOMINIO EDIFICIO NOVA REBOUÇAS', **kwargs)


def cadastral(paginas=None, *, ano=2025, **kwargs):
    def mutar(i, rows):
        return [(x,y,t.replace('Emitido em 26/10/2026', f'Emitido em 26/10/{ano}')) for x,y,t in rows]
    return cadastro(paginas, codigo='0286', nome='CONDOMINIO EDIFICIO NOVA REBOUÇAS', mutar=mutar, **kwargs)


def executar(path, raw=None, modo='A', **kwargs):
    return analisar(raw or financeiro(), PedidoDiagnostico(data_ref=REF, modo=modo, condominio='nova_reboucas'),
        processamento_id='reboucas_sintetico', destino=path, **kwargs)


def linhas(path):
    w=load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(w['Dados'].values);w.close();return rows


def test_identidade_financeira_e_cadastral_nao_dependem_do_filename():
    p,c,f=reconhecer(financeiro());pc,cc,fc=reconhecer(cadastral(),cadastro=True)
    assert c==cc=='286' and p['codigo_easycollector']==pc['codigo_easycollector']=='696'
    assert p['condominio_id']==pc['condominio_id']=='cond_bbz_nova_reboucas'
    assert f=='bbz_inadimplencia_xlsx_v1' and fc=='bbz_cadastro_geral_pdf_v1'
    assert PERFIS['nova_reboucas']['vigente_de'] is None


@pytest.mark.parametrize('codigo,nome', [('696','CONDOMINIO EDIFICIO NOVA REBOUÇAS'),
    ('286','CONDOMINIO NOVA YORK PENTHOUSES'),('287','CONDOMINIO EDIFICIO NOVA REBOUÇAS')])
def test_codigo_destino_nao_substitui_identidade_documental(codigo,nome):
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):
        reconhecer(planilha(codigo=codigo,nome=nome))


@pytest.mark.parametrize('dias,elegivel',[(29,False),(30,False),(31,True),(32,True)])
def test_prazo_estrito_diagnostico_dias_corridos(tmp_path,dias,elegivel):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(due=REF-timedelta(days=dias))])]))
    assert r['resumo']['dividas_efetivamente_geradas']==int(elegivel)
    assert r['decisoes'][0]['situacao']==('elegivel' if elegivel else 'nao_elegivel')


@pytest.mark.parametrize('numero,bloco,esperado', [('000001','0','BL0-UNI0001-696'),
    ('0102','0','BL0-UNI0102-696'),('00X1','0',None),('000001','B',None)])
def test_codificador_comprovado_sem_inventar_identificadores(tmp_path,numero,bloco,esperado):
    r=executar(tmp_path,financeiro([unidade(numero=numero,bloco=bloco)]))
    codigo=next(iter(r['codificacao_template']['unidades'].values()))
    if esperado:
        assert codigo['cedente']==codigo['contrato']==esperado
        assert codigo['complemento']==esperado.rsplit('-',1)[0]
    else:
        assert codigo['estado']=='provisorio' and codigo['motivo']
    assert r['decisoes'][0]['unidade']==numero and r['decisoes'][0]['bloco']==bloco


@pytest.mark.parametrize('marcador',[None,'A','AJ','J','AE'])
def test_marcadores_e_centavo_nao_importam_vetos_tree(tmp_path,marcador):
    raw=financeiro([unidade(recibos=[recibo(marcador=marcador,
        componentes=[('COTA CONDOMINIAL AGO/2026','0.01')]),recibo(id='99000002')])])
    r=executar(tmp_path,raw)
    assert r['resumo']['dividas_efetivamente_geradas']==2 and r['resumo']['cotas_excluidas_por_veto']==0
    p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    assert [a.codigo_original for a in l.boletos[0].apontamentos]==([marcador] if marcador else [])


@pytest.mark.parametrize('cad',[False,True])
def test_modos_a_b_zero_multiplos_recibos_e_parcelas(tmp_path,cad):
    raw=financeiro([unidade(recibos=[recibo(componentes=[('COTA CONDOMINIAL AGO/2026','100'),
        ('CONSUMO ENERGIA','10')]),recibo(id='99000002',due=REF),
        recibo(id='99000003',componentes=[('AJUSTE FICTICIO','0')])])])
    args={'cadastro':cadastral()} if cad else {}
    a=executar(tmp_path/'A',raw,**args);b=executar(tmp_path/'B',raw,modo='B',**args)
    assert a['resumo']['dividas_efetivamente_geradas']==b['resumo']['dividas_efetivamente_geradas']==1
    assert a['resumo']['cadastros_adicionais']==0 and b['resumo']['cadastros_adicionais']==1
    ar,br=linhas(tmp_path/'A'),linhas(tmp_path/'B')
    assert ar[1]==br[1] and ar[1][26:]==('COTA 08/2026',1,ar[1][28],110)
    assert all(v is None for v in br[-1][24:30]) and len(br[0])==30
    extracted=json.loads((tmp_path/'B/canonico_extraido.json').read_text())
    assert len(extracted['boletos'])==3 and len(extracted['boletos'][0]['composicao']['itens'])==2


@pytest.mark.parametrize('ano,alerta',[(2025,True),(2026,False)])
def test_emissao_cadastro_nao_e_vigencia_nem_atesto(tmp_path,ano,alerta):
    r=executar(tmp_path,cadastro=cadastral(ano=ano))
    temporal=r['cadastro_bbz']['referencia_temporal']
    assert temporal['periodo_anterior']==alerta and not temporal['atualidade_atestada']
    assert temporal['data_referencia_processamento']==REF.isoformat()
    assert temporal['emissoes'][0]['emitido_em'].startswith(str(ano))
    assert temporal['emissoes'][0]['fuso_documental'] is None
    assert temporal['emissoes'][0]['origem']['pagina']==1
    assert any(o['codigo']=='BBZ_CADASTRO_PERIODO_ANTERIOR'for o in r['ocorrencias'])==alerta
    assert linhas(tmp_path)[1][2]==CPF and r['resumo']['dividas_efetivamente_geradas']==1


@pytest.mark.parametrize('paginas',[1,2,3])
def test_continuidades_preservam_papeis_locacao_pagador(tmp_path,paginas):
    r=executar(tmp_path,cadastro=cadastral(dividir(ficha(locatario=True,pagador=True),paginas)))
    stats=r['cadastro_bbz']['resumo']
    assert stats['continuidades']==paginas-1 and stats['unidades_cadastrais_lidas']==1
    assert len(r['cadastro_bbz']['referencia_temporal']['emissoes'])==paginas
    row=linhas(tmp_path)[1]
    assert row[2]==CPF and 'locatario@example.invalid'not in row and row[4]not in ('Rua de Correspondencia',)
    info=next(iter(r['cadastro_bbz']['unidades'].values()))
    assert {'locatario','pagador'}<={p['papel']for p in info['ficha']['participantes']}


@pytest.mark.parametrize('doc',['','00000000190','00000000000191'])
def test_documentos_opcionais_e_cnpj_com_zero_textual(tmp_path,doc):
    r=executar(tmp_path,cadastro=cadastral([ficha(documento=doc)]))
    assert r['resumo']['dividas_efetivamente_geradas']==1
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');c=w['Dados']['C2']
    assert c.value==('00000000000191' if len(doc)==14 else None)
    if c.value:assert c.data_type=='s' and c.number_format=='@'
    w.close()


@pytest.mark.parametrize('mudanca',[{'nome':'OUTRO TITULAR FICTICIO'}, {'segundo_documento':'00000000272'}])
def test_associacao_inconclusiva_retem_contato_sem_mudar_financeiro(tmp_path,mudanca):
    r=executar(tmp_path,cadastro=cadastral([ficha(**mudanca)]))
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==1
    assert r['resumo']['dividas_efetivamente_geradas']==1
    row=linhas(tmp_path)[1];assert row[2] is None and all(v is None for v in row[11:24])


def test_cpf_repetido_em_mesma_identidade_nao_e_conflito(tmp_path):
    r=executar(tmp_path,cadastro=cadastral([ficha(segundo_documento=CPF)]))
    assert r['cadastro_bbz']['resumo']['documentos_validos_vinculados']==1
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==0 and linhas(tmp_path)[1][2]==CPF


def test_defasagem_documental_no_mesmo_ano_tambem_e_rastreada(tmp_path):
    from conversor.application.bbz_cadastro import registrar_temporalidade_cadastro
    raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    e={'emitido_em':'2026-10-25T12:00:00','origem':l.unidades[0].origem.model_dump(mode='json')}
    novo,a=registrar_temporalidade_cadastro(l,{},(e,),data_ref=REF)
    assert a['referencia_temporal']['periodo_anterior'] and novo.boletos==l.boletos
    assert novo.ressalvas[-1].codigo=='BBZ_CADASTRO_PERIODO_ANTERIOR'


def test_contatos_malformados_sem_inferir_ddd(tmp_path):
    r=executar(tmp_path,cadastro=cadastral([ficha(contatos=['Celular - 90000-0001',
        'Celular - 90000-0001','E-mail - invalido@@example.invalid','E-mail - titular@example.invalid'])]))
    row=linhas(tmp_path)[1]
    assert row[11] is None and row[12]=='900000001' and row[13] is None and row[14] is None
    assert row[21]=='titular@example.invalid' and row[22] is None
    assert any(o['codigo']=='EMAIL_NAO_SEGMENTADO'for o in r['ocorrencias'])


def test_144_unidades_do_cadastro_nao_viram_144_linhas(tmp_path):
    pdf=cadastral([ficha(),ficha('000002'),ficha('000003')],total=3)
    r=executar(tmp_path,modo='B',cadastro=pdf)
    assert r['cadastro_bbz']['resumo']['unidades_cadastrais_lidas']==3
    assert r['cadastro_bbz']['resumo']['unidades_financeiras_localizadas']==1
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==0


def test_outro_condominio_nao_associa_e_fontes_alfanumericas_preservadas(tmp_path):
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):
        executar(tmp_path,cadastro=cadastro())
    raw=financeiro([unidade(numero='00X1')]);p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    cad, _=ler(cadastral([ficha(numero='00X1')]),p,c,'bbz_cadastro_geral_pdf_v1','cadastro')
    assert l.unidades[0].id==cad.unidades[0].id and cad.unidades[0].unidade_original=='00X1'


@pytest.mark.parametrize('hist,rotulo',[
    ('CONDOMINIO AGO/2026','COTA 08/2026'),('COTA CONDOMINIAL AGO/2026','COTA 08/2026'),
    ('LOCAÇÃO DE SALAS','LOCAÇÃO DE SALAS'),('NATUREZA FICTICIA DESCONHECIDA','RECIBO 99000001'),
    ('COND AGO/26','RECIBO 99000001')])
def test_descricoes_compartilhadas_sem_inferir_competencia(tmp_path,hist,rotulo):
    r=executar(tmp_path,financeiro([unidade(recibos=[recibo(componentes=[(hist,'100')])])]))
    assert linhas(tmp_path)[1][26]==rotulo
    if rotulo.startswith('RECIBO'):assert r['decisoes'][0]['competencia'] is None


def test_endereco_privado_por_condominio_preserva_complemento(tmp_path):
    config=EnderecoPadrao(endereco={'logradouro':'Rua Ficticia Privada','numero':'9','cep':'00000001'},
        evidencia={'arquivo':'config_sintetica','sha256':'a'*64,'aba':'declaracao','celulas':{'endereco':'usuario'}})
    consultas=[]
    def buscar(adm,cond):consultas.append((adm,cond));return config
    r=executar(tmp_path,cadastro=cadastral(),buscar_endereco=buscar)
    row=linhas(tmp_path)[1]
    assert consultas==[('adm_bbz','cond_bbz_nova_reboucas')]
    assert row[4:8]==('Rua Ficticia Privada','9','BL0-UNI0001','00000001')
    assert r['cadastro_bbz']['divergencias_endereco_configurado']


def test_bloqueio_critico_permanece(tmp_path):
    raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    o=Ocorrencia(id='critico_ficticio',processamento_id='hist_sintetico',codigo='CRITICO_FICTICIO',
        gravidade='critico',escopo='registro',registro_id=l.unidades[0].id)
    r=executar(tmp_path,raw,cadastro=cadastral(),historico=(o,))
    assert r['resumo']['dividas_efetivamente_geradas']==0


def test_idempotencia_financeira_e_cadastral(tmp_path):
    raw=financeiro();pdf=cadastral()
    a=executar(tmp_path/'primeiro',raw,cadastro=pdf);b=executar(tmp_path/'segundo',raw,cadastro=pdf)
    assert a==b
    for f in ('canonico.json','canonico_extraido.json','TESTE_LOCAL_NAO_IMPORTAR.xlsx'):
        assert (tmp_path/'primeiro'/f).read_bytes()==(tmp_path/'segundo'/f).read_bytes()


def test_upload_download_com_e_sem_cadastro_e_autenticacao(tmp_path):
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY)) as c:
        assert c.get('/api/condominios').status_code==401
        c.post('/api/session',json={'chave':KEY})
        for mode in ('A','B'):
            r=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':mode,'condominio':'nova_reboucas'},
                files={'inadimplencia':('arquivo_sem_identidade.xlsx',financeiro()),'cadastro':('cadastro.pdf',cadastral())}))
            assert r['estado']=='concluido' and r['resultado']['cadastro_bbz']['referencia_temporal']['periodo_anterior']
            assert c.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409
            w=load_workbook(BytesIO(c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').content))
            assert w['Dados'].max_column==30;w.close()
        r=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},files={'inadimplencia':('f.xlsx',financeiro())}))
        assert r['resultado']['resumo']['dividas_efetivamente_geradas']==1 and 'cadastro_bbz'not in r['resultado']


@pytest.mark.parametrize('codigo,nome',[('117','CONDOMINIO EDIFICIO WIN'),('575','CONDOMINIO JARDINS DO BRASIL')])
def test_outros_condominios_nao_habilitados(codigo,nome):
    with pytest.raises(ErroLeitura,match='CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO'):
        reconhecer(planilha(codigo=codigo,nome=nome))
