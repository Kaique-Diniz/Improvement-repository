"""ABROLHOS: documentos desenhados do zero, sem dados reais de clientes."""
from datetime import date,timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json

from openpyxl import Workbook,load_workbook
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from conversor.domain.canonical import Ocorrencia
from conversor.domain.document_scope import EscopoDestinoDiagnostico
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.template import COLUNAS
from conversor.readers.text_support import ErroLeitura
from conversor.web.service import analisar,PedidoDiagnostico,reconhecer,ler
from conversor.web.app import criar_app
from tests.bbz.conftest import planilha,unidade,recibo
from tests.bbz.cadastro_fixtures import cadastro,ficha,dividir,CPF
from tests.web.test_mvp import KEY,aguardar
REF=date(2026,10,26)


def financeiro(units=None,*,codigo='575',**kwargs):
    return planilha(units or [unidade(bloco='D',numero='A00001',recibos=[recibo(due=date(2026,7,5),componentes=[('CONDOMINIO JUL/2026','100')])])],
        codigo=codigo,nome='CONDOMINIO JARDINS DO BRASIL',**kwargs)


def referencia(raw,*,incluir=None,produto='JARDINS DO BRASIL ABROLHOS',mutar=None):
    p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia');ps={p.unidade_id:p for p in l.pessoas};us={u.id:u for u in l.unidades}
    w=Workbook();s=w.active;s.title='Dados';s.append(COLUNAS)
    for b in l.boletos:
        u=us[b.unidade_id]
        if incluir is not None and u.chave_normalizada not in incluir:continue
        comp=f'BL{u.bloco_original}-UNI{u.unidade_original}';ced=comp+'-788';r=[None]*30
        r[0]='BBZ';r[1]=ced;r[3]=ps[u.id].nome;r[6]=comp;r[24:30]=[ced,produto,'COTA 07/2026',1,b.vencimento,float(b.composicao.total_original)];s.append(r)
    if mutar:mutar(w,s)
    out=BytesIO();w.save(out);w.close();return out.getvalue()


def cadastral(paginas=None,**kwargs):
    return cadastro(paginas or [ficha(bloco='D',numero='A00001')],codigo='0575',nome='CONDOMINIO JARDINS DO BRASIL',**kwargs)


def executar(tmp_path,raw=None,*,ref=True,modo='A',**kwargs):
    raw=raw or financeiro()
    return analisar(raw,PedidoDiagnostico(data_ref=REF,modo=modo,condominio='abrolhos'),
        processamento_id='abrolhos_sintetico',destino=tmp_path,referencia=referencia(raw)if ref is True else ref,**kwargs)


def rows(path):
    w=load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');r=list(w['Dados'].values);w.close();return r


@pytest.mark.parametrize('codigo',['575','0575','000575'])
def test_empreendimento_reconhecido_nao_equivale_a_torre(codigo,tmp_path):
    raw=financeiro(codigo=codigo);p,c,f=reconhecer(raw)
    assert p['codigo_easycollector']=='788'and c==codigo
    r=executar(tmp_path,raw,ref=None,cadastro=cadastral(),modo='B')
    assert r['resumo']['elegiveis_pela_regua']==1 and r['resumo']['dividas_efetivamente_geradas']==0
    assert r['resumo']['cadastros_adicionais']==0
    assert r['decisoes'][0]['bloqueios']==['DESTINO_TORRE_NAO_COMPROVADO']
    assert r['cadastro_bbz']['resumo']['unidades_financeiras_sem_escopo']==1
    assert next(iter(r['cadastro_bbz']['unidades'].values()))['estado']=='escopo_nao_comprovado'


@pytest.mark.parametrize('dias,contagem',[(59,0),(60,0),(61,1),(91,1),(400,1)])
def test_prazo_estrito_por_referencia_explicita_sem_veto_judicial(tmp_path,dias,contagem):
    raw=financeiro([unidade(bloco='D',numero='A00001',recibos=[recibo(due=REF-timedelta(days=dias))])])
    r=executar(tmp_path,raw);assert r['resumo']['dividas_efetivamente_geradas']==contagem
    assert r['resumo']['boletos_nao_selecionados_prazo']==1-contagem


def test_dois_blocos_mesmo_numero_nao_misturam_torres(tmp_path):
    raw=financeiro([unidade(bloco='D',numero='A00001'),unidade(bloco='E',numero='A00001',recibos=[recibo(id='99000002')])])
    ref=referencia(raw,incluir={'D/A00001'})
    r=executar(tmp_path,raw,ref=ref,cadastro=cadastral([ficha(bloco='D',numero='A00001'),ficha(bloco='E',numero='A00001',documento='00000000272')],total=2))
    assert r['resumo']['boletos']==2 and r['resumo']['elegiveis_pela_regua']==2 and r['resumo']['dividas_efetivamente_geradas']==1
    assert rows(tmp_path)[1][2]==CPF and rows(tmp_path)[1][1]=='BLD-UNIA00001-788'
    assert r['cadastro_bbz']['resumo']['unidades_financeiras_localizadas']==1
    assert r['cadastro_bbz']['resumo']['unidades_cadastrais_fora_da_selecao_comprovada']==1


@pytest.mark.parametrize('produto',['OUTRA TORRE FICTICIA','JARDINS DO BRASIL',''])
def test_produto_generico_ou_outra_torre_nao_comprova_destino(tmp_path,produto):
    raw=financeiro();r=executar(tmp_path,raw,ref=referencia(raw,produto=produto))
    assert r['resumo']['dividas_efetivamente_geradas']==0
    assert all(u['estado']=='nao_comprovado'for u in r['escopo_destino']['unidades'])


@pytest.mark.parametrize('campo,valor',[('B2','BLOCO ERRADO'),('G2','BLD-UNIA99999'),('Y2','CONTRATO ERRADO'),
    ('D2','OUTRA IDENTIDADE FICTICIA'),('AD2',101),('AC2',date(2025,1,1)),('A2','OUTRA ADMINISTRADORA')])
def test_confronto_exige_identidade_recibo_original_e_data(tmp_path,campo,valor):
    raw=financeiro();ref=referencia(raw,mutar=lambda w,s:setattr(s[campo],'value',valor))
    r=executar(tmp_path,raw,ref=ref);assert r['resumo']['dividas_efetivamente_geradas']==0


def test_referencia_contraditoria_preserva_evidencias_e_retem(tmp_path):
    def duplicar(w,s):r=[c.value for c in s[2]];r[25]='OUTRA TORRE FICTICIA';s.append(r)
    raw=financeiro();r=executar(tmp_path,raw,ref=referencia(raw,mutar=duplicar));u=r['escopo_destino']['unidades'][0]
    assert u['motivo_codigo']=='REFERENCIA_DESTINO_CONFLITANTE' and len(u['evidencias'])==2
    assert r['resumo']['dividas_efetivamente_geradas']==0


@pytest.mark.parametrize('bloco,numero',[('0','1SS001'),('D','B00001'),('D','C00001'),('E','B00001')])
def test_literal_bloco_unidade_preservado(tmp_path,bloco,numero):
    raw=financeiro([unidade(bloco=bloco,numero=numero)]);r=executar(tmp_path,raw)
    row=rows(tmp_path)[1];assert row[1]==row[24]==f'BL{bloco}-UNI{numero}-788' and row[6]==f'BL{bloco}-UNI{numero}'
    assert r['decisoes'][0]['bloco']==bloco and r['decisoes'][0]['unidade']==numero


def test_prefixo_nao_documentado_permanece_sem_autorizacao(tmp_path):
    raw=financeiro([unidade(bloco='OUTRO',numero='A00001')]);r=executar(tmp_path,raw)
    assert r['resumo']['dividas_efetivamente_geradas']==0


@pytest.mark.parametrize('codigo',[None,'A','AJ','J','AE'])
def test_marcadores_e_centavo_preservados_sem_herdar_tree(tmp_path,codigo):
    raw=financeiro([unidade(bloco='D',numero='A00001',recibos=[recibo(marcador=codigo,componentes=[('CONDOMINIO JUL/2026','0.01')])])])
    r=executar(tmp_path,raw);assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cotas_excluidas_por_veto']==0
    assert Decimal(r['decisoes'][0]['valor'])==Decimal('.01')


def test_zero_negativos_componentes_e_modo_b(tmp_path):
    raw=financeiro([unidade(bloco='D',numero='A00001',recibos=[recibo(componentes=[('CONDOMINIO JUL/2026','100'),('DESCONTO COTA CONDOMINIAL','-1')]),recibo(id='99000002',componentes=[('AJUSTE','0')]),recibo(id='99000003',due=REF)])])
    a=executar(tmp_path/'A',raw);b=executar(tmp_path/'B',raw,modo='B')
    assert a['resumo']['dividas_efetivamente_geradas']==b['resumo']['dividas_efetivamente_geradas']==1
    assert b['resumo']['cadastros_adicionais']==1 and b['resumo']['boletos']==3
    assert rows(tmp_path/'A')[1]==rows(tmp_path/'B')[1] and rows(tmp_path/'B')[1][29]==99
    assert all(v is None for v in rows(tmp_path/'B')[-1][24:30])


@pytest.mark.parametrize('partes',[1,2,3])
def test_cadastro_compartilhado_continuidades_papeis_e_excedentes(tmp_path,partes):
    pdf=cadastral(dividir(ficha(bloco='D',numero='A00001',locatario=True,pagador=True,
        contatos=['Celular - 90000-0001','E-mail - titular@example.invalid','E-mail - titular@example.invalid']),partes))
    r=executar(tmp_path,cadastro=pdf);row=rows(tmp_path)[1]
    assert row[2]==CPF and row[11]is None and row[12]=='900000001' and row[21]=='titular@example.invalid' and row[22]is None
    assert r['cadastro_bbz']['resumo']['continuidades']==partes-1
    assert row[4]!='Rua de Correspondencia' and 'locatario@example.invalid'not in row


@pytest.mark.parametrize('doc',['','00000000190','00000000000191'])
def test_documentos_opcionais_invalidos_ou_cnpj_textual(tmp_path,doc):
    r=executar(tmp_path,cadastro=cadastral([ficha(bloco='D',numero='A00001',documento=doc)]))
    assert r['resumo']['dividas_efetivamente_geradas']==1
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');c=w['Dados']['C2']
    assert c.value==('00000000000191'if len(doc)==14 else None)
    if c.value:assert c.data_type=='s'and c.number_format=='@'
    w.close()


def test_documentos_validos_conflitantes_retidos_sem_trocar_titular(tmp_path):
    r=executar(tmp_path,cadastro=cadastral([ficha(bloco='D',numero='A00001',segundo_documento='00000000272')]))
    assert r['cadastro_bbz']['resumo']['associacoes_retidas']==1 and rows(tmp_path)[1][2]is None
    assert r['resumo']['dividas_efetivamente_geradas']==1


def test_cadastro_outro_condominio_e_financeiro_no_campo_cadastro_rejeitados(tmp_path):
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):executar(tmp_path,cadastro=cadastro())
    with pytest.raises(ErroLeitura):executar(tmp_path,cadastro=financeiro())


def test_modelo_versionado_integridade_e_reprocessamento_sem_confiar_snapshot(tmp_path):
    raw=financeiro();ref=referencia(raw);a=executar(tmp_path/'A',raw,ref=ref);b=executar(tmp_path/'B',raw,ref=ref)
    assert (tmp_path/'A/escopo_destino.json').read_bytes()==(tmp_path/'B/escopo_destino.json').read_bytes()
    assert (tmp_path/'A/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'B/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    obj=dict(a['escopo_destino']);h=obj.pop('sha256_conteudo');m=EscopoDestinoDiagnostico.model_validate(obj)
    assert hash_modelo(m)==h and m.referencia_sha256==sha256(ref).hexdigest() and m.atesto_humano is None
    obj['referencia_sha256']='a'*64
    with pytest.raises(ValidationError,match='EVIDENCIA_DE_OUTRA_FONTE'):EscopoDestinoDiagnostico.model_validate(obj)
    (tmp_path/'B/escopo_destino.json').write_text('{"estado":"aprovado"}')
    c=executar(tmp_path/'C',raw,ref=None)
    assert c['resumo']['dividas_efetivamente_geradas']==0


def test_bloqueio_critico_preexistente_nunca_e_liberado(tmp_path):
    raw=financeiro();p,c,f=reconhecer(raw);l,_=ler(raw,p,c,f,'inadimplencia')
    o=Ocorrencia(id='critico_ficticio',processamento_id='hist_ficticio',codigo='CRITICO_FICTICIO',gravidade='critico',escopo='registro',registro_id=l.unidades[0].id)
    r=executar(tmp_path,raw,historico=(o,));assert r['resumo']['dividas_efetivamente_geradas']==0


def test_upload_nome_cadastro_xlsx_e_referencia_e_download_autenticado(tmp_path):
    raw=financeiro();ref=referencia(raw)
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY))as c:
        assert c.get('/api/condominios').status_code==401;c.post('/api/session',json={'chave':KEY})
        for mode in ('A','B'):
            r=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':mode,'condominio':'abrolhos'},files={'inadimplencia':('Cadastro.xlsx',raw),'referencia':('ref.xlsx',ref),'cadastro':('pessoas.pdf',cadastral())}))
            assert r['estado']=='concluido'and r['resultado']['resumo']['boletos']==1 and r['resultado']['resumo']['dividas_efetivamente_geradas']==1
            assert c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').status_code==200
            assert c.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409


def test_colisao_de_chave_normalizada_rejeitada(tmp_path):
    raw=financeiro([unidade(bloco='0',numero='000001'),unidade(bloco='00',numero='1',recibos=[recibo(id='99000002')])])
    with pytest.raises(ErroLeitura,match='BBZ_UNIDADE_DUPLICADA'):executar(tmp_path,raw,ref=None)
