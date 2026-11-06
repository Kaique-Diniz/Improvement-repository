"""Regressões sintéticas BPQ-01; não dependem dos documentos privados."""
from datetime import timedelta,date
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import pytest
from openpyxl import load_workbook
from conversor.domain.beach_parque import complemento_unidade,rotulo_descricao
from conversor.domain.documents import resolver_documento
from conversor.readers.beach_parque_xlsx import LeitorBeachParqueXLSX,originais
from conversor.readers.beach_parque_cadastro import LeitorCadastroBeachParque
from conversor.readers.beach_parque_identity import IdentidadeBeachParqueNaoComprovada
from conversor.readers.text_support import ContextoLeitura,ErroLeitura
from conversor.application.beach_parque_cadastro import associar,POLITICA
from conversor.web.service import analisar,ler,reconhecer,PERFIS,PedidoDiagnostico
from .fixtures import financeiro,cadastro,recibo,ficha,dividir,REF,NOME,CPF

PROFILE='terraco_beach_parque'


def contexto(role='inadimplencia'):
    return ContextoLeitura('condominio_terraco_beach_parque','habitacional','beach_parque',role,'3075')

def ler_fin(raw):return LeitorBeachParqueXLSX().ler(raw,contexto=contexto())
def ler_cad(raw):return LeitorCadastroBeachParque().ler(raw,contexto=contexto('cadastro'))
def executar(tmp,raw=None,cad=None,mode='A',ref=REF):
    return analisar(raw if raw is not None else financeiro(),PedidoDiagnostico(data_ref=ref,modo=mode,condominio=PROFILE),
        processamento_id='bpq_ficticio',destino=tmp,cadastro=cad,historico=(),estado_historico='nao_disponivel')
def rows(tmp):
    w=load_workbook(tmp/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:return list(w['Dados'].values)
    finally:w.close()


@pytest.mark.parametrize('token',['12345678','A 12345678','J 12345678'])
def test_recibo_original_emissao_bruta_e_componentes(token):
    rec=recibo(token,componentes=[('DESPESA FICTICIA','100','100','1','2','3'),('ESTORNO FICTICIO','-1.10','-1.10','0','0','0')])
    raw=financeiro([('A','A00001',NOME,[rec])]);l=ler_fin(raw);b=l.boletos[0];d=originais(l)[b.id]
    assert b.composicao.total_original==Decimal('98.90') and len(b.composicao.itens)==2
    assert b.emissao is None and b.emissao_original=='202608' and b.competencia is None
    assert d['recibo_original']==token and d['componentes'][0]['conta']=='1.01'
    assert d['componentes'][0]['moeda']=='R$' and d['totais'][5]=='104.90'
    assert all(o.sha256==sha256(raw).hexdigest() for o in b.origens)


@pytest.mark.parametrize('bloco,unidade,expected',[('A','A00001','BLILHABE-UNIA00001'),('B','B00001','BLANG-UNIB00001'),('C','C00206','BLBUZ-UNIC00206'),('0','DANPRI','BL00-UNIDANPRI')])
def test_codificacao_documental(bloco,unidade,expected):assert complemento_unidade(bloco,unidade)==expected


@pytest.mark.parametrize('bloco,unidade',[('A','B00001'),('A','A1'),('D','D00001'),('0','OUTRO'),('A','A００００１'),('0','danpri')])
def test_codificacao_rejeita_aliases(bloco,unidade):
    with pytest.raises(ValueError):complemento_unidade(bloco,unidade)


@pytest.mark.parametrize('dias,n',[(29,0),(30,0),(31,1)])
def test_prazo_estrito(tmp_path,dias,n):
    r=executar(tmp_path,financeiro([('A','A00001',NOME,[recibo(dias=dias)])]))
    assert r['resumo']['dividas_efetivamente_geradas']==n
    assert not r['autoriza_cobranca'] and not r['permite_exportacao_operacional']


def test_mudanca_referencia_e_modo_b_por_unidade(tmp_path):
    recs=[recibo('1',40),recibo('2',6),recibo('3',6)]
    raw=financeiro([('A','A00001',NOME,recs),('B','B00001',NOME,[recibo('4',6)])])
    a=executar(tmp_path/'a',raw);b=executar(tmp_path/'b',raw,mode='B')
    assert len(rows(tmp_path/'a'))==2 and len(rows(tmp_path/'b'))==4
    late=executar(tmp_path/'c',raw,ref=REF+timedelta(days=25))
    assert late['resumo']['dividas_efetivamente_geradas']==4
    assert len(rows(tmp_path/'b')[0])==30 and rows(tmp_path/'b')[0][26]=='NM_DIVIDA_CEDENTE'
    assert rows(tmp_path/'a')[1][29]==100.1 and rows(tmp_path/'a')[1][0]=='HABITACIONAL'


def test_ocorrencias_repetidas_e_empates_estaveis(tmp_path):
    recs=[recibo('A 17'),recibo('17'),recibo('17')]
    raw=financeiro([('A','A00001',NOME,recs)])
    l=ler_fin(raw);assert len(l.boletos)==3 and len({b.id for b in l.boletos})==3
    assert [originais(l)[b.id]['recibo_original']for b in l.boletos]==['A 17','17','17']
    x=executar(tmp_path/'a',raw);y=executar(tmp_path/'b',raw)
    assert rows(tmp_path/'a')==rows(tmp_path/'b')
    assert [r[27]for r in rows(tmp_path/'a')[1:]]==[1,2,3]
    assert x['decisoes']==y['decisoes']


@pytest.mark.parametrize('kind',['recibo','unidade','geral','sem_recibo','sem_unidade','sem_final','formula','data','conta','historico','moeda','aba','identidade','coluna','linha_desconhecida','unidade_invalida'])
def test_falhas_estruturais_fechadas(kind):
    def change(w,s):
        idx={label:next(i for i,row in enumerate(s,1)if row[0].value==label)for label in ('Total do Recibo:','Total Geral da Unidade:')}
        if kind in ('recibo','unidade'):s.cell(idx['Total do Recibo:'if kind=='recibo'else'Total Geral da Unidade:'],7,'999')
        if kind=='geral':s.cell(s.max_row,7,'999')
        if kind=='sem_recibo':s.delete_rows(idx['Total do Recibo:'])
        if kind=='sem_unidade':s.delete_rows(idx['Total Geral da Unidade:'])
        if kind=='sem_final':s.delete_rows(s.max_row)
        if kind=='formula':s['G7']='=1+1'
        if kind=='data':s['B7']='99/99/2026'
        if kind=='conta':s['D7']=None
        if kind=='historico':s['E7']=None
        if kind=='moeda':s['F7']='OUTRA'
        if kind=='aba':s.title='Outra'
        if kind=='identidade':s['A2']='Condomínio: 3076 - OUTRO FICTICIO'
        if kind=='coluna':s['M7']='EXTRA'
        if kind=='linha_desconhecida':s.append(['TEXTO FICTICIO'])
        if kind=='unidade_invalida':s['A5']=f'Bloco: A Unidade: B00001 {NOME}'
    with pytest.raises(ErroLeitura):ler_fin(financeiro(mutar=change))


def test_identidade_confirmacao_hash_nao_substitui_estrutura(monkeypatch):
    raw=financeiro()
    with pytest.raises(IdentidadeBeachParqueNaoComprovada):reconhecer(raw)
    assert reconhecer(raw,perfil_informado=PROFILE)[0]['familia']=='habitacional_beach'
    monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    assert reconhecer(raw)[0]['id']==PROFILE
    with pytest.raises(ErroLeitura):reconhecer(raw,perfil_informado='parque_santa_monica')
    bad=financeiro(mutar=lambda w,s:s.__setitem__('G7','=1'))
    monkeypatch.setitem(PERFIS[PROFILE]['fontes_homologacao_sha256'],'inadimplencia',sha256(bad).hexdigest())
    with pytest.raises(ErroLeitura):reconhecer(bad)


def test_cadastro_torres_especial_continuacao_e_papeis():
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,locatario=True,pagador=True)
    pages=dividir(body,2)+[ficha(bloco=b,numero=u,nome=NOME,documento=CPF)for b,u in [('B','B00001'),('C','C00001'),('0','DANPRI')]]
    l=ler_cad(cadastro(pages,total=4));assert len(l.unidades)==4
    fichas=[json.loads(r.valores_originais[0])for r in l.ressalvas if r.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL']
    assert len(fichas)==4 and len(fichas[0]['cabecalhos'])==2
    assert {p['papel']for p in fichas[0]['participantes']}=={'titular','locatario','pagador','unidade'}
    assert resolver_documento(l.pessoas[0]).valor==CPF
    assert 'locatario@example.invalid'not in l.pessoas[0].contato.emails


@pytest.mark.parametrize('nome,doc,retido',[(NOME,CPF,0),('OUTRA PESSOA FICTICIA',CPF,1),(NOME,'',1),(NOME,'00000000000',1),(NOME,'texto '+CPF,1),('FICTICIO UM / FICTICIO DOIS',CPF,1)])
def test_a1_ambiguidade_nao_exclui_divida(tmp_path,nome,doc,retido):
    fin=financeiro([('A','A00001',nome if '/'in nome else NOME,[recibo()])])
    cad=cadastro([ficha(bloco='A',numero='A00001',nome=nome,documento=doc,locatario=True,pagador=True)])
    r=executar(tmp_path,fin,cad)
    assert r['resumo']['dividas_efetivamente_geradas']==1
    assert r['cadastro_'+PROFILE]['associacoes_retidas']==retido
    assert r['cadastro_'+PROFILE]['registros_cadastro']==1
    assert r['cadastro_'+PROFILE]['paginas_cadastro']==1
    assert r['cadastro_'+PROFILE]['continuidades_cadastro']==0
    assert r['politica_cadastral']==POLITICA
    assert r['manifesto_diagnostico']['cadastro_'+PROFILE]['politica']==POLITICA
    assert json.loads((tmp_path/'auditoria.json').read_text(encoding='utf-8'))['politica_cadastral']==POLITICA
    data=rows(tmp_path)[1]
    assert (data[2]is None)==bool(retido)
    assert (any(data[i] is not None for i in (12,14,16,18,20,21)))==bool(not retido)
    assert data[29]==100.1


def test_cadastro_cruzado_paginas_invalidas_e_omitido(tmp_path):
    with pytest.raises(ErroLeitura):executar(tmp_path/'a',cad=cadastro(codigo='0000566',nome='OUTRO FICTICIO'))
    with pytest.raises(ErroLeitura):ler_cad(cadastro(mutar=lambda i,rows:[(x,y,t.replace('Página 1 de 1','Página 2 de 2'))for x,y,t in rows]))
    r=executar(tmp_path/'b');assert r['resumo']['dividas_efetivamente_geradas']==1 and not r['cadastro_'+PROFILE]['fornecido']


@pytest.mark.parametrize('descricao,mes',[('CONSUMO AGUA',True),('Taxa de condominio',True),('PROJETO SEGURANÇA 11/61',True),('COTA FICTICIA 09/2026',False),('ACORDO FICTICIO',False)])
def test_rotulo_literal_e_mes_apenas_apresentacao(descricao,mes):
    rotulo,observado=rotulo_descricao(descricao,REF,2)
    assert observado==mes
    assert rotulo==descricao+(' 10/2026'if mes else'')+' - 2'


@pytest.mark.parametrize('tipo,codigo',[('reenvio','BPQ_REVISAO_BLOQUEIO_REENVIO'),('carta','BPQ_REVISAO_NAO_RECEBER_CARTA'),('litigio','BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO')])
def test_restricoes_provenientes_nao_excluem_financeiro(tmp_path,tipo,codigo):
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF)
    field={'reenvio':'Bloquear reenvio automático de boletos: Sim','carta':'Recebe carta: Não','litigio':'Classificação: Litígio'}[tipo]
    body.append((24,110,field))
    r=executar(tmp_path,cad=cadastro([body]))
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not r['autoriza_cobranca']
    assert codigo in r['decisoes'][0]['alertas_cadastrais']
    assert r['cadastro_'+PROFILE]['restricoes_por_codigo'][codigo]==1
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    ev=next(x for x in canonical['ressalvas']if x['codigo']==codigo)
    assert ev['origens'][0]['sha256'] and ev['valores_originais']==[]


def test_documento_so_pagador_nao_vira_titular_e_malformado_tem_evidencia(tmp_path):
    body=ficha(bloco='0',numero='DANPRI',nome=NOME,documento='texto '+CPF,pagador=True)
    raw=financeiro([('0','DANPRI',NOME,[recibo()])]);c=ler_cad(cadastro([body]))
    assert not resolver_documento(c.pessoas[0]).valor
    assert any(r.codigo=='PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO'and r.valores_originais==('texto '+CPF,)for r in c.ressalvas)
    r=executar(tmp_path,raw,cadastro([body]));assert rows(tmp_path)[1][2]is None
    assert r['resumo']['dividas_efetivamente_geradas']==1


def test_documentos_validos_conflitantes_retidos(tmp_path):
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,segundo_documento='00000000272')
    r=executar(tmp_path,cad=cadastro([body]))
    assert r['cadastro_'+PROFILE]['retencoes_por_motivo']=={'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO':1}
    assert rows(tmp_path)[1][2]is None and r['resumo']['dividas_efetivamente_geradas']==1


def test_contato_terceiro_e_cnpj_empresarial_sem_transferencia_implicita(tmp_path):
    empresa='LABORATORIO E SERVICOS FICTICIOS LTDA'
    body=ficha(bloco='A',numero='A00001',nome=empresa,documento='00000000000191',contatos=['E-mail - titular@example.invalid'])
    body.extend([(240,300,'Telefone/e-mail da unidade'),(24,288,'E-mail - terceiro@example.invalid'),(24,270,'Observações: Telefone de terceiro 90000-0099')])
    raw=financeiro([('A','A00001',empresa,[recibo()])]);r=executar(tmp_path,raw,cadastro([body]))
    output=rows(tmp_path)[1]
    assert output[2]=='00000000000191' and output[21]=='titular@example.invalid'
    assert 'terceiro@example.invalid'not in output and '900000099'not in output
    assert r['cadastro_'+PROFILE]['associacoes_retidas']==0


def test_componente_zerado_sem_conta_ou_historico_e_incompleto():
    def change(w,s):
        s['D7']=None;s['E7']=None
    raw=financeiro([('A','A00001',NOME,[recibo(componentes=[('FICTICIO','0','0','0','0','0')])])],mutar=change)
    with pytest.raises(ErroLeitura,match='BPQ_COMPONENTE_INCOMPLETO'):ler_fin(raw)


def test_original_do_fechamento_nao_e_principal_nem_atualizado(tmp_path):
    raw=financeiro([('A','A00001',NOME,[recibo(componentes=[('ORIGINAL FICTICIO','130.17','90.17','1','2','3')])])])
    l=ler_fin(raw);d=originais(l)[l.boletos[0].id]
    assert d['totais']==['130.17','90.17','1.00','2.00','3.00','96.17']
    executar(tmp_path,raw)
    assert rows(tmp_path)[1][29]==130.17
