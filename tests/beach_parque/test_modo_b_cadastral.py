"""BPQ-B1: fixtures fictícias; dívida e pessoa-base não são alteradas."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
import json

import pytest
from openpyxl import load_workbook

from conversor.application.beach_parque_cadastro import associar, resolver_linha_cadastral, POLITICA_B1
from conversor.domain.canonical import Contato, RessalvaLeitura
from conversor.domain.template import COLUNAS
from conversor.application.beach_parque_cadastro import POLITICA
from conversor.readers.text_support import ErroLeitura
from .fixtures import financeiro,cadastro,ficha,recibo,NOME,CPF,REF
from .test_beach_parque import executar,rows,ler_fin,ler_cad,PROFILE


def cad(contatos=None,nome=NOME,documento=CPF,**kw):
    return cadastro([ficha(bloco='A',numero='A00001',nome=nome,documento=documento,contatos=contatos,**kw)])


def originais_b1(raw=None,pdf=None):
    lote=ler_fin(raw if raw is not None else financeiro([('A','A00001',NOME,[recibo('1',29),recibo('2',30)])]))
    cadastral=ler_cad(pdf if pdf is not None else cad())
    lote,pessoas,resumo,_=associar(lote,cadastral)
    decisions=[{'id':b.id,'unidade_id':b.unidade_id,'situacao_financeira':'excluido'}for b in lote.boletos]
    return lote,lote.unidades[0],lote.pessoas[0],decisions,pessoas,cadastral


def b1(result):return result['modo_b_cadastral_beach_parque']
def cadrows(tmp):return [r for r in rows(tmp)[1:]if r[29]is None]


@pytest.mark.parametrize('dias',[29,30,31])
@pytest.mark.parametrize('nome,documento',[(NOME,CPF),('EMPRESA FICTICIA ALFA E BETA LTDA','00000000000191')])
def test_b1_limite_nome_documento_textual_e_financeiro_vazio(tmp_path,dias,nome,documento):
    fin=financeiro([('A','A00001',nome,[recibo('1',dias)])]);pdf=cad(nome=nome,documento=documento)
    result=executar(tmp_path,fin,pdf,mode='B');table=rows(tmp_path)
    assert table[0]==COLUNAS and len(table)==2
    if dias>30:
        assert result['resumo']['cadastros_adicionais']==0 and b1(result)['decisoes']==[]
        assert table[1][29]==100.1
    else:
        assert result['resumo']['cadastros_adicionais']==1
        assert table[1][2]==documento and table[1][3]==nome
        assert all(v is None for v in table[1][24:30])
        assert all(table[1][i]is None for i in (4,5,7,8,9,10))
        assert b1(result)['decisoes'][0]['estado']=='BPQ_B1_ASSOCIACAO_COMPROVADA'
        book=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
        try:assert book['Dados']['C2'].data_type=='s'and book['Dados']['C2'].number_format=='@'
        finally:book.close()
    assert not result['autoriza_cobranca']and not result['permite_exportacao_operacional']


@pytest.mark.parametrize('anotacao',['',' - atualizado em 10/01/2025.',' (alterado em 10/01/2025)'])
def test_contatos_do_titular_preservam_bpq02_e_evidencia(tmp_path,anotacao):
    cells=['Celular - (11) 91234-5678'+anotacao,'Telefone - 0123-4567'+anotacao,
        'E-mail - titular@example.invalid'+anotacao,'E-mail - segundo@example.invalid'+anotacao]
    fin=financeiro([('A','A00001',NOME,[recibo('1',30),recibo('2',29)])]);pdf=cad(cells)
    result=executar(tmp_path,fin,pdf,mode='B');table=cadrows(tmp_path)
    assert len(table)==1 and table[0][2]==CPF
    assert table[0][11:15]==('11','912345678',None,'01234567')
    assert table[0][21:24]==('titular@example.invalid','segundo@example.invalid',None)
    d=b1(result)['decisoes'][0]
    assert len(d['lancamentos_relevantes'])==2 and d['comprovada']and d['exportada']
    assert any(o['sha256']==sha256(pdf).hexdigest()for o in d['origens'])
    assert any(o['sha256']==sha256(fin).hexdigest()for o in d['origens'])
    assert all(o['pagina']or o['linha']for o in d['origens'])
    manifesto=json.loads((tmp_path/'manifesto_diagnostico.json').read_text(encoding='utf-8'))
    auditoria=json.loads((tmp_path/'auditoria.json').read_text(encoding='utf-8'))
    assert manifesto['modo_b_cadastral_beach_parque']==auditoria['modo_b_cadastral_beach_parque']==b1(result)
    assert b1(result)['politica']==POLITICA_B1 and result['politica_cadastral']==POLITICA
    serialized=json.dumps(b1(result))
    assert CPF not in serialized and NOME not in serialized and 'example.invalid'not in serialized


@pytest.mark.parametrize('situacao,estado',[
    ('divergente','BPQ_B1_NOME_DIVERGENTE'),('multiplo','BPQ_B1_RESPONSAVEIS_MULTIPLOS'),
    ('ausente','BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'),('invalido','BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'),
    ('conflitante','BPQ_B1_DOCUMENTO_CONFLITANTE'),('pagador','BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'),
    ('locatario','BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'),('sem_cadastro','BPQ_B1_CADASTRO_NAO_FORNECIDO'),
])
def test_b1_retido_nao_altera_linha_ou_numero_de_dividas(tmp_path,situacao,estado):
    nome='FICTICIO UM / FICTICIO DOIS'if situacao=='multiplo'else NOME
    cnome='OUTRO RESPONSAVEL FICTICIO'if situacao=='divergente'else nome
    doc=''if situacao in ('ausente','pagador','locatario')else'00000000000'if situacao=='invalido'else CPF
    pdf=cad(nome=cnome,documento=doc,pagador=situacao=='pagador',locatario=situacao=='locatario',
        segundo_documento='00000000272'if situacao=='conflitante'else None)
    fin=financeiro([('A','A00001',nome,[recibo('1',31),recibo('2',30)])])
    result=executar(tmp_path,fin,None if situacao=='sem_cadastro'else pdf,mode='B')
    assert result['resumo']['dividas_efetivamente_geradas']==1 and result['resumo']['cadastros_adicionais']==1
    line=cadrows(tmp_path)[0]
    assert line[3]==nome and line[2]is None and not any(line[11:24])
    assert b1(result)['decisoes'][0]['estado']==estado
    assert not b1(result)['decisoes'][0]['comprovada']


@pytest.mark.parametrize('contato',['Celular - (11) 91234-5678 - telefone do filho',
    'E-mail - terceiro@example.invalid - contato do locatário','Celular - (11) 91234-5678 - verificar titular'])
def test_b1_nao_recupera_terceiro_ou_anotacao_ambigua(tmp_path,contato):
    result=executar(tmp_path,financeiro([('A','A00001',NOME,[recibo('1',30)])]),cad([contato]),mode='B')
    assert cadrows(tmp_path)[0][2]==CPF and not any(cadrows(tmp_path)[0][11:24])
    assert b1(result)['decisoes'][0]['comprovada'] # documento aprovado não aprova contato ambíguo


@pytest.mark.parametrize('mutacao,estado',[
    ('pessoas_distintas','BPQ_B1_RESPONSAVEIS_MULTIPLOS'),
    ('origem_de_outra_divida','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('sem_evidencia','BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'),
    ('documento_diferente','BPQ_B1_DOCUMENTO_CONFLITANTE'),
    ('pessoa_de_outra_unidade','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('base_de_outra_pessoa','BPQ_B1_NOME_DIVERGENTE'),
    ('contato_terceiro','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('critico','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('critico_global','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('a1_retida','BPQ_B1_NOME_DIVERGENTE'),
    ('sem_nao_elegivel','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('cadastro_outra_torre','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
    ('dois_titulares','BPQ_B1_ASSOCIACAO_INSUFICIENTE'),
])
def test_prova_de_cada_lancamento_nao_e_substituida_por_objeto_pessoa(mutacao,estado):
    lote,u,p,ds,people,c=originais_b1();people=dict(people);id1,id2=[d['id']for d in ds]
    if mutacao=='pessoas_distintas':people[id2]=people[id2].model_copy(update={'nome':'OUTRA PESSOA FICTICIA'})
    if mutacao=='origem_de_outra_divida':people[id2]=people[id1]
    if mutacao=='sem_evidencia':people[id2]=people[id2].model_copy(update={'documento':None,'evidencias_documentais':()})
    if mutacao=='documento_diferente':
        ev=people[id2].evidencias_documentais[0];ev=ev.model_copy(update={'documento':ev.documento.model_copy(update={'valor':'00000000272'})})
        people[id2]=people[id2].model_copy(update={'evidencias_documentais':(ev,)})
    if mutacao=='pessoa_de_outra_unidade':people[id2]=people[id2].model_copy(update={'unidade_id':'outra_unidade_ficticia'})
    if mutacao=='base_de_outra_pessoa':p=p.model_copy(update={'nome':'OUTRA PESSOA FICTICIA'})
    if mutacao=='contato_terceiro':people[id2]=people[id2].model_copy(update={'contato':Contato(emails=('terceiro@example.invalid',))})
    if mutacao in ('critico','critico_global','a1_retida'):
        note=RessalvaLeitura(codigo='BLOQUEIO_FICTICIO'if mutacao.startswith('critico')else'PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO',
            registro_id='arquivo_ficticio'if mutacao=='critico_global'else id2,
            gravidade='critico'if mutacao.startswith('critico')else'alerta',origens=(people[id2].origem,))
        lote=lote.model_copy(update={'ressalvas':lote.ressalvas+(note,)})
    if mutacao=='sem_nao_elegivel':ds=[dict(d,situacao_financeira='elegivel_na_simulacao')for d in ds]
    if mutacao=='cadastro_outra_torre':c=c.model_copy(update={'unidades':(c.unidades[0].model_copy(update={'bloco_original':'B'}),)})
    if mutacao=='dois_titulares':c=c.model_copy(update={'pessoas':c.pessoas+(c.pessoas[0].model_copy(update={'id':'outro_titular_ficticio'}),)})
    out,d=resolver_linha_cadastral(lote,u,p,ds,people,c)
    assert out is None and d['estado']==estado and not d['comprovada']


def test_nome_de_elegivel_nao_autoriza_outro_responsavel_na_linha_cadastral():
    raw=financeiro([('A','A00001',NOME,[recibo('1',31),recibo('2',30)])])
    lote,u,p,ds,people,c=originais_b1(raw)
    ds[0]['situacao_financeira']='elegivel_na_simulacao'
    people[ds[1]['id']]=people[ds[1]['id']].model_copy(update={'nome':'OUTRO RESPONSAVEL FICTICIO'})
    out,d=resolver_linha_cadastral(lote,u,p,ds,people,c)
    assert out is None and d['lancamentos_relevantes']==[ds[1]['id']]and d['estado']=='BPQ_B1_NOME_DIVERGENTE'


def test_torres_semelhantes_contatos_isolados_e_unidade_sem_cadastro(tmp_path):
    fin=financeiro([(b,b+'00001',NOME,[recibo(str(i),30)])for i,b in enumerate(('A','B','C'),1)])
    pdf=cadastro([ficha(bloco=b,numero=b+'00001',nome=NOME,documento=doc,contatos=[f'E-mail - torre{b.lower()}@example.invalid'])
        for b,doc in [('A',CPF),('B','00000000272')]],total=2)
    result=executar(tmp_path,fin,pdf,mode='B');lines=cadrows(tmp_path)
    assert len(lines)==3
    byid={r[6]:r for r in lines}
    assert byid['BLILHABE-UNIA00001'][2]==CPF and byid['BLILHABE-UNIA00001'][21]=='torrea@example.invalid'
    assert byid['BLANG-UNIB00001'][2]=='00000000272' and byid['BLANG-UNIB00001'][21]=='torreb@example.invalid'
    assert byid['BLBUZ-UNIC00001'][2]is None and not any(byid['BLBUZ-UNIC00001'][11:24])
    assert len(b1(result)['decisoes'])==3


def test_cadastro_cruzado_rejeitado_e_template_nao_e_cadastro(tmp_path):
    from conversor.web.service import analisar,PedidoDiagnostico
    fin=financeiro([('A','A00001',NOME,[recibo('1',30)])])
    with pytest.raises(ErroLeitura):executar(tmp_path/'outro',fin,cadastro(codigo='3076',nome='OUTRO FICTICIO'),mode='B')
    executar(tmp_path/'referencia',fin,cad(),mode='B')
    # Nenhum dado do XLSX de referência é consultado pelo resolvedor B1.
    result=analisar(fin,PedidoDiagnostico(data_ref=REF,modo='B',condominio=PROFILE),
        processamento_id='bpq03_referencia_ficticia',destino=tmp_path/'sem',cadastro=None,
        referencia=(tmp_path/'referencia/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes(),
        historico=(),estado_historico='nao_disponivel')
    assert cadrows(tmp_path/'sem')[0][2]is None
    assert b1(result)['decisoes'][0]['estado']=='BPQ_B1_CADASTRO_NAO_FORNECIDO'


def test_b1_determinismo_ab_financeiro_e_xlsx_sem_codigo_executavel(tmp_path):
    fin=financeiro([('A','A00001',NOME,[recibo('1',31),recibo('2',30),recibo('3',29)])])
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF)
    body.extend([(24,110,'Bloquear reenvio automático de boletos: Sim'),(216,110,'Recebe carta: Não'),(24,100,'Classificação: Litígio')])
    pdf=cadastro([body]);results={m:executar(tmp_path/m,fin,pdf,mode=m)for m in('A','B')}
    executar(tmp_path/'B2',fin,pdf,mode='B')
    a,b=rows(tmp_path/'A'),rows(tmp_path/'B')
    assert b==rows(tmp_path/'B2')and a[0]==b[0]==COLUNAS
    assert a[1:]==[r for r in b[1:]if r[29]is not None]
    assert len(a)==2 and len(b)==3 and all(v is None for v in cadrows(tmp_path/'B')[0][24:30])
    assert 'modo_b_cadastral_beach_parque'not in results['A']
    assert results['A']['decisoes']==results['B']['decisoes']
    assert results['B']['cadastro_'+PROFILE]['restricoes_por_codigo']=={
        'BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO':1,'BPQ_REVISAO_BLOQUEIO_REENVIO':1,'BPQ_REVISAO_NAO_RECEBER_CARTA':1}
    assert not results['B']['autoriza_cobranca']and not results['B']['permite_exportacao_operacional']
    file=tmp_path/'B/TESTE_LOCAL_NAO_IMPORTAR.xlsx'
    book=load_workbook(file)
    try:assert not any(c.data_type=='f'for row in book['Dados']for c in row)and not book._external_links
    finally:book.close()
    with ZipFile(file)as z:
        assert not any('vbaProject' in n or 'externalLinks/' in n for n in z.namelist())


@pytest.mark.parametrize('mode',['A','B'])
def test_http_auditoria_b1_condicional_sessao_download_e_descarte(tmp_path,mode):
    from fastapi.testclient import TestClient
    from conversor.web.ephemeral import criar_app_efemero
    from tests.web.test_classic_local import boot,ORIGIN
    fin=financeiro([('A','A00001',NOME,[recibo('1',31),recibo('2',30)])]);pdf=cad()
    app=criar_app_efemero(area_temporaria=tmp_path)
    with TestClient(app,base_url=ORIGIN)as client:
        boot(client)
        r=client.post('/api/conversoes',data={'data_ref':str(REF),'modo':mode,'condominio':PROFILE},
            files={'inadimplencia':('FICTICIO.xlsx',fin),'cadastro':('FICTICIO.pdf',pdf)})
        assert r.status_code==200
        id_=r.json()['id'];detail=client.get('/api/conversoes/'+id_+'/detalhes')
        assert detail.status_code==200
        key='modo_b_cadastral_beach_parque'
        if mode=='B':
            assert detail.json()[key]['politica']==POLITICA_B1
            assert detail.json()[key]['decisoes'][0]['comprovada']
        else:assert key not in detail.json()
        with TestClient(criar_app_efemero(),base_url=ORIGIN)as other:
            boot(other);assert other.get('/api/conversoes/'+id_+'/detalhes').status_code==404
            assert other.get('/api/conversoes/'+id_+'/excel').status_code==404
        assert client.get('/api/conversoes/'+id_+'/operacional.xlsx').status_code==409
        download=client.get('/api/conversoes/'+id_+'/excel');assert download.status_code==200
        book=load_workbook(BytesIO(download.content));table=list(book['Dados'].values);book.close()
        assert len(table)==2+int(mode=='B')and table[0]==COLUNAS
        if mode=='B':assert table[-1][2]==CPF and not any(table[-1][24:])
        assert client.get('/api/conversoes/'+id_+'/detalhes').status_code==404
        assert not any(p.is_file()for p in tmp_path.rglob('*'))
    assert not list(tmp_path.iterdir())
