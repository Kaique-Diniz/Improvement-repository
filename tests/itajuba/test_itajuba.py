"""ITJ-01: somente fixtures fictícias, com hashes reais e política A1."""
from collections import Counter
from datetime import date,timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pypdf import PdfReader,PdfWriter

from conversor.domain.itajuba import complemento_unidade
from conversor.domain.documents import resolver_documento
from conversor.readers.itajuba_pdf import LeitorItajubaPDF,originais
from conversor.readers.itajuba_cadastro import LeitorCadastroItajuba
from conversor.readers.itajuba_identity import IdentidadeItajubaNaoComprovada
from conversor.readers.text_support import ContextoLeitura,ErroLeitura
from conversor.web.service import analisar,PedidoDiagnostico,PERFIS,reconhecer
from conversor.web.ephemeral import criar_app_efemero
from tests.web.test_classic_local import boot,ORIGIN
from tests.web.test_ephemeral import Clock
from .fixtures import REF,NOME,CPF,OUTRO_CPF,linha,financeiro,ficha,cadastro


def ler(raw,cad=False):
    parser=LeitorCadastroItajuba()if cad else LeitorItajubaPDF()
    return parser.ler(raw,contexto=ContextoLeitura('condominio_itajuba','bn_planner',parser.formato_id,'cadastro'if cad else'inadimplencia','itajuba'))


def executar(path,raw=None,cad=None,modo='A',ref=REF):
    # Binding confiável exclusivamente da fixture cadastral, nunca da ACL ou
    # conteúdo inferido do arquivo. Produção não homologa uploads automaticamente.
    with pytest.MonkeyPatch.context()as m:
        if cad is not None:m.setitem(PERFIS['itajuba']['fontes_homologacao_sha256'],'cadastro',sha256(cad).hexdigest())
        return analisar(raw if raw is not None else financeiro(),PedidoDiagnostico(data_ref=ref,modo=modo,condominio='itajuba'),
            processamento_id='itajuba_ficticio',destino=path,cadastro=cad,historico=(),estado_historico='nao_disponivel')


def rows(path):
    b=load_workbook(path)
    try:return list(b['Dados'].values)
    finally:b.close()


def test_composicao_original_inquilino_acordo_e_ocorrencias_repetidas():
    first=linha(inquilino='Inquilino Integralmente Ficticio',acordo='1')
    raw=financeiro([('T-01','A-01',[first,first,linha(dias=32)])],quebra=2)
    l=ler(raw);d=originais(l)
    assert len(l.boletos)==3 and len({b.id for b in l.boletos})==3
    assert len(l.unidades)==1 and len({o.pagina for b in l.boletos for o in b.origens})==2
    assert all(b.composicao.total_original==Decimal('105.00')and b.competencia is None for b in l.boletos)
    assert all([i.valor for i in b.composicao.itens]==[Decimal('100'),Decimal('5')]for b in l.boletos)
    assert Counter(v['documento']for v in d.values())=={'Tt_T-01_A-01':3}
    assert list(d.values())[0]['inquilino']=='Inquilino Integralmente Ficticio'
    assert list(d.values())[0]['acordo']=='1' and list(d.values())[1]['ocorrencia']==2
    assert all(o.sha256==sha256(raw).hexdigest()and o.data_fonte==REF for b in l.boletos for o in b.origens)
    assert [b.identificador.split(':')[0]for b in l.boletos]==['itj_000001','itj_000002','itj_000003']


@pytest.mark.parametrize('torre,ap,expected',[('T-01','A-01','QUAT01-LTA0001'),('T-05','D-12','QUAT05-LTD0012')])
def test_codificacao_comprovada_preserva_originais(torre,ap,expected):
    assert complemento_unidade(torre,ap)==expected
    l=ler(financeiro([(torre,ap,[linha()])]))
    assert(l.unidades[0].bloco_original,l.unidades[0].unidade_original)==(torre,ap)


@pytest.mark.parametrize('torre,ap',[('T-06','A-01'),('01','A-01'),('T-01','A-1'),('T-01','E-01'),('T-01','A-001'),('T-01','a-01'),('T-01','A-０１')])
def test_nao_presume_codificacao(torre,ap):
    with pytest.raises(ValueError):complemento_unidade(torre,ap)


@pytest.mark.parametrize('kind',['soma','subtotal','geral','cabecalho','identidade','emissao','paginacao','data','tipo','torre','conteudo_apos_fim','sem_fechamento'])
def test_estrutura_financeira_ou_fechamento_divergente_rejeita(kind):
    def change(pi,rs):
        out=[]
        for x,y,t in rs:
            if kind=='soma'and x==281.4:t='999,00'
            if kind=='subtotal'and x==364:t='999,00'
            if kind=='geral'and x==267.8:t='999,00'
            if kind=='cabecalho'and t=='Tx Cond':t='Atualizado'
            if kind=='identidade'and t=='CONDOMINIO ITAJUBA':t='OUTRO CONDOMINIO FICTICIO'
            if kind=='emissao'and x==774.7:t='31/02/26'
            if kind=='paginacao'and x==525.45:t='2'
            if kind=='data'and x==116.08:t='31/02/2026'
            if kind=='tipo'and x==25.05:t='Outro_T-01_A-01'
            if kind=='torre'and x==535.53:t='T-06'
            if kind=='sem_fechamento'and(t=='Total Geral'or x==267.8):continue
            out.append((x,y,t))
        if kind=='conteudo_apos_fim':out.append((25,400,'EXTRA FICTICIO'))
        return out
    with pytest.raises(ErroLeitura):ler(financeiro(mutar=change))


@pytest.mark.parametrize('kind',['identidade','cabecalho','faltante','reordenada'])
def test_continuacao_tem_identidade_e_paginacao_verificadas(kind):
    raw=financeiro([('T-01','A-01',[linha(),linha(dias=32),linha(dias=33)])],quebra=2,
        mutar=(lambda pi,rs:[(x,y,'OUTRO CONDOMINIO FICTICIO'if pi==2 and t=='CONDOMINIO ITAJUBA'else t)for x,y,t in rs])if kind=='identidade'else None)
    if kind=='cabecalho':
        def change(pi,rs):return rs+([(25,520,'Doc.'),(200,520,'Atualizado')]if pi==2 else[])
        raw=financeiro([('T-01','A-01',[linha(),linha(dias=32)])],quebra=2,mutar=change)
    if kind in('faltante','reordenada'):
        r=PdfReader(BytesIO(raw));w=PdfWriter()
        for page in(list(r.pages)[:-1]if kind=='faltante'else list(reversed(r.pages))):w.add_page(page)
        out=BytesIO();w.write(out);raw=out.getvalue()
    with pytest.raises(ErroLeitura):ler(raw)


@pytest.mark.parametrize('dias,expected',[(29,0),(30,0),(31,1)])
def test_limite_provisorio_e_referencia_explicita(tmp_path,dias,expected):
    raw=financeiro([('T-01','A-01',[linha(dias=dias)])])
    r=executar(tmp_path/'hoje',raw)
    assert r['resumo']['dividas_efetivamente_geradas']==expected
    tomorrow=executar(tmp_path/'amanha',raw,ref=REF+timedelta(days=1))
    assert tomorrow['resumo']['dividas_efetivamente_geradas']==int(dias+1>30)


def test_escopo_novembro_dezembro_preserva_canonico_sem_encaminhar_anterior(tmp_path):
    raw=financeiro([('T-01','A-01',[linha(vencimento=date(2023,11,30)),linha(vencimento=date(2023,12,1))])])
    r=executar(tmp_path,raw)
    assert r['resumo']['boletos']==2 and r['resumo']['dividas_efetivamente_geradas']==1
    anterior=next(d for d in r['decisoes']if d['vencimento']=='2023-11-30')
    assert anterior['situacao']=='revisao'and 'ITAJUBA_ESCOPO_ANTERIOR_DEZ2023_REQUER_REVISAO'in anterior['bloqueios']
    assert len(json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))['boletos'])==2


def test_tipos_documentais_nao_copiam_rotulos_errados_do_historico(tmp_path):
    raw=financeiro([('T-01','A-01',[linha(doc=kind+'_T-01_A-01',acordo='1')for kind in('Tt','Mlt','Ext','AcT')])])
    r=executar(tmp_path,raw);table=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert [v[26].split(' (')[0]for v in table[1:]]==['COTA CONDOMINIAL','MULTA','COTA EXTRA','ACORDO']
    assert [v[27]for v in table[1:]]==[1,2,3,4]
    assert all(v[26].endswith(' - '+str(v[27]))for v in table[1:])
    assert r['resumo']['dividas_efetivamente_geradas']==4
    assert r['decisoes'][0]['documento_financeiro_original']=='Tt_T-01_A-01'
    assert r['decisoes'][0]['evidencia_documental_itajuba']['acordo']=='1'


def test_desempate_estavel_em_vencimentos_iguais_sem_consumir_parcela_excluida(tmp_path):
    repetido=linha(doc='Ext_T-01A-01',dias=31)
    raw=financeiro([('T-01','A-01',[
        linha(doc='Mlt900000',dias=30),repetido,linha(dias=32),
        linha(doc='Mlt900001',dias=31),repetido])],quebra=3)
    resultados=[executar(tmp_path/nome,raw)for nome in('primeira','segunda')]
    tabelas=[rows(tmp_path/nome/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')for nome in('primeira','segunda')]
    assert resultados[0]['resumo']['boletos']==5
    assert resultados[0]['resumo']['dividas_efetivamente_geradas']==4
    assert tabelas[0]==tabelas[1]
    assert [r[27]for r in tabelas[0][1:]]==[1,2,3,4]
    assert [r[26].split(' (')[0]for r in tabelas[0][1:]]==[
        'COTA CONDOMINIAL','COTA EXTRA','MULTA','COTA EXTRA']
    assert tabelas[0][1][28].date()==REF-timedelta(days=32)
    assert all(r[28].date()==REF-timedelta(days=31)for r in tabelas[0][2:])
    assert (tmp_path/'primeira/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'segunda/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()


@pytest.mark.parametrize('doc,tipo',[('Tt_T-01_A-01','Tt'),('Mlt900001','Mlt'),('Ext_T-01A-01','Ext'),('AcT-01A-01','AcT')])
def test_formatos_documentais_preservados_sem_exigir_codigo_exclusivo(doc,tipo):
    lote=ler(financeiro([('T-01','A-01',[linha(doc=doc),linha(doc=doc,dias=32)])]))
    dados=originais(lote)
    assert len(lote.boletos)==2 and len({b.id for b in lote.boletos})==2
    assert all(d['documento']==doc and d['tipo']==tipo for d in dados.values())


def test_subtotal_ausente_registrado_sem_inventar_conferencia_local(tmp_path):
    def omitir_primeiro(pi,rs):
        ys=[y for x,y,t in rs if t=='Total Unidade']
        return [(x,y,t)for x,y,t in rs if y!=ys[0]]
    raw=financeiro([('T-01','A-01',[linha()]),('T-02','B-01',[linha()])],mutar=omitir_primeiro)
    lote=ler(raw)
    assert len(lote.boletos)==2 and sum(r.codigo=='ITAJUBA_SUBTOTAL_NAO_IMPRESSO'for r in lote.ressalvas)==1
    r=executar(tmp_path,raw)
    assert r['resumo']['dividas_efetivamente_geradas']==2


def test_associacao_a1_por_lancamento_nao_transfere_documento_do_atual_ao_antigo(tmp_path):
    antigo='Outro Responsavel Totalmente Ficticio'
    raw=financeiro([('T-01','A-01',[linha(nome=antigo),linha(nome=NOME,dias=32)])])
    r=executar(tmp_path,raw,cadastro())
    table=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    byname={row[3]:row for row in table[1:]}
    assert byname[NOME][2]==CPF and not byname[antigo][2] and not any(byname[antigo][11:24])
    assert r['cadastro_itajuba']['associacoes_retidas']==1 and r['resumo']['dividas_efetivamente_geradas']==2


@pytest.mark.parametrize('bad',['11111111111','texto-'+CPF,''])
def test_documento_invalido_preserva_evidencia_e_divida(tmp_path,bad):
    cad=cadastro([ficha(documento=bad)])
    canonical=ler(cad,True)
    assert canonical.pessoas[0].documento is None
    if bad:assert any(bad in r.valores_originais for r in canonical.ressalvas)
    r=executar(tmp_path,cad=cad)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')[1][2]


@pytest.mark.parametrize('email',['123456','codigo com espacos','titular@example.invalid texto','sem-arroba'])
def test_email_nao_inventado_nem_telefone_parcial(tmp_path,email):
    cad=cadastro([ficha(telefone='123456789012345',celular='0123-4567',email=email)])
    p=ler(cad,True).pessoas[0]
    assert not p.contato.emails and len(p.contato.telefones)==1
    assert p.contato.telefones[0].ddd==''and p.contato.telefones[0].numero=='01234567'
    r=executar(tmp_path,cad=cad)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['cadastro_itajuba']['emails_rejeitados_no_cadastro']==1


def test_inad_prop_nao_gera_boleto_e_unidades_sem_cadastro_nao_perdem_dividas(tmp_path):
    raw=financeiro([('T-01','A-01',[linha()]),('T-02','B-03',[linha()])])
    cad=cadastro([ficha(),ficha('T-05','D-04',inad='100000000')])
    assert not ler(cad,True).boletos
    r=executar(tmp_path,raw,cad)
    assert r['resumo']['dividas_efetivamente_geradas']==2 and r['cadastro_itajuba']['lancamentos_sem_cadastro']==1


@pytest.mark.parametrize('mode',['A','B'])
def test_modos_30_colunas_metadados_e_valores_originais(tmp_path,mode):
    r=executar(tmp_path,modo=mode)
    table=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert len(table)==2 and len(table[0])==30 and table[0][26]=='NM_DIVIDA_CEDENTE'
    row=table[1];assert row[0]=='BN PLANNER'and row[1]=='QUAT01-LTA0001-CONDOMINIO ITAJUBA'
    assert row[6]=='QUAT01-LTA0001'and row[24]==row[1]and row[25]=='CONDOMINIO ITAJUBA'
    assert Decimal(str(row[29]))==Decimal('105')and row[27]==1
    assert r['resumo']['cadastros_adicionais']==0
    manifest=json.loads((tmp_path/'manifesto_diagnostico.json').read_text(encoding='utf-8'))
    audit=json.loads((tmp_path/'auditoria.json').read_text(encoding='utf-8'))
    assert r['politica_cadastral']==manifest['cadastro_itajuba']['politica']==audit['politica_cadastral']=='itajuba_nome_e_unidade_por_lancamento_A1@1'
    assert not r['permite_exportacao_operacional']and not r['autoriza_cobranca']


def test_modo_b_unico_cadastro_e_multiplicidade_nome_bloqueia_linha_extra(tmp_path):
    raw=financeiro([('T-01','A-01',[linha(dias=29),linha(dias=30)]),('T-02','B-01',[linha(dias=29),linha(dias=31,nome='Outro Ficticio')])])
    r=executar(tmp_path,raw,modo='B')
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==1


def test_determinismo_bytes_identicos_e_hash_real_diferente(tmp_path):
    raw=financeiro();a=executar(tmp_path/'a',raw);b=executar(tmp_path/'b',raw)
    assert a['decisoes']==b['decisoes']
    assert(tmp_path/'a/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'b/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    other=financeiro([('T-01','A-01',[linha(outros='6')])]);c=executar(tmp_path/'c',other)
    assert a['fontes'][0]['sha256']==sha256(raw).hexdigest()!=c['fontes'][0]['sha256']


def test_identidade_pdf_nova_exige_confirmacao_hash_nao_dispensa_estrutura(monkeypatch):
    raw=financeiro()
    with pytest.raises(IdentidadeItajubaNaoComprovada):reconhecer(raw)
    assert reconhecer(raw,perfil_informado='itajuba')[0]['id']=='itajuba'
    monkeypatch.setitem(PERFIS['itajuba']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    assert reconhecer(raw)[0]['id']=='itajuba'
    with pytest.raises(ErroLeitura):reconhecer(raw,perfil_informado='parque_santa_monica')
    bad=financeiro(mutar=lambda pi,rs:[(x,y,'OUTRO CONDOMINIO FICTICIO'if t=='CONDOMINIO ITAJUBA'else t)for x,y,t in rs])
    monkeypatch.setitem(PERFIS['itajuba']['fontes_homologacao_sha256'],'inadimplencia',sha256(bad).hexdigest())
    with pytest.raises(ErroLeitura):reconhecer(bad)


def test_cadastro_sem_identidade_nao_e_homologado_pela_selecao_manual(monkeypatch):
    raw=cadastro()
    with pytest.raises(ErroLeitura,match='CADASTRO_IDENTIDADE_NAO_COMPROVADA'):reconhecer(raw,cadastro=True,perfil_informado='itajuba')
    monkeypatch.setitem(PERFIS['itajuba']['fontes_homologacao_sha256'],'cadastro',sha256(raw).hexdigest())
    assert reconhecer(raw,cadastro=True,perfil_informado='itajuba')[0]['id']=='itajuba'
    with pytest.raises(ErroLeitura):reconhecer(raw,cadastro=True,perfil_informado='passaredo')


@pytest.mark.parametrize('kind',['formula','coluna','aba','titulo','duplicado'])
def test_cadastro_estruturalmente_invalido_rejeitado(kind):
    def change(w,s):
        if kind=='formula':s['H3']='=1+1'
        if kind=='coluna':s['I3']='EXTRA'
        if kind=='aba':s.title='Outra'
        if kind=='titulo':s['A1']='OUTRO DOCUMENTO'
        if kind=='duplicado':s.append(ficha())
    with pytest.raises(ErroLeitura):ler(cadastro(mutar=change),True)


def test_web_download_sessao_csrf_e_descarte(tmp_path,monkeypatch):
    cad=cadastro();monkeypatch.setitem(PERFIS['itajuba']['fontes_homologacao_sha256'],'cadastro',sha256(cad).hexdigest())
    app=criar_app_efemero(area_temporaria=tmp_path,relogio=Clock())
    with TestClient(app,base_url=ORIGIN)as c:
        boot(c);files={'inadimplencia':('nome-nao-identifica.pdf',financeiro())}
        assert c.post('/api/identificar',files=files).status_code==409
        ident=c.post('/api/identificar',files=files,data={'condominio':'itajuba'});assert ident.status_code==200
        converted=c.post('/api/conversoes',data={'condominio':'itajuba','data_ref':str(REF),'modo':'A','contexto':ident.json()['contexto']},
            files={**files,'cadastro':('cadastro-ficticio.xlsx',cad)})
        assert converted.status_code==200
        id_=converted.json()['id'];assert not list(app.state.ciclo.root.iterdir())
        assert c.get('/api/conversoes/'+id_+'/operacional.xlsx').status_code==409
        other=TestClient(app,base_url=ORIGIN)
        try:boot(other);assert other.get('/api/conversoes/'+id_+'/excel').status_code==404
        finally:other.close()
        no_csrf=c.headers.pop('x-csrf-token');assert c.get('/api/conversoes/'+id_+'/excel').status_code==403
        c.headers['x-csrf-token']=no_csrf
        output=c.get('/api/conversoes/'+id_+'/excel');assert output.status_code==200
        assert len(rows(BytesIO(output.content))[0])==30
        assert c.get('/api/conversoes/'+id_+'/excel').status_code==404
