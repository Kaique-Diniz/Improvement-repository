"""Contratos cruzados INT-02; todos os documentos são fictícios."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import pytest
from openpyxl import load_workbook
from fastapi.testclient import TestClient
from conversor.web.service import PERFIS as CONFIG,PedidoDiagnostico,analisar,reconhecer
from conversor.web.ephemeral import criar_app_efemero
from conversor.readers.text_support import ErroLeitura
from conversor.domain.template import COLUNAS
from tests.web.test_classic_local import boot,ORIGIN
from .fixtures import PERFIS,NOME,CPF,caso,homologar


def executar(tmp,c,*,modo='A',cad=True,ref=None):
    return analisar(c.financeiro,PedidoDiagnostico(data_ref=ref or c.ref,modo=modo,condominio=c.perfil),
        processamento_id='int02_ficticio',destino=tmp,cadastro=c.cadastro if cad else None,historico=(),estado_historico='nao_disponivel')

def ler_saida(path):
    w=load_workbook(path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:return list(w['Dados'].values)
    finally:w.close()


@pytest.mark.parametrize('perfil',PERFIS)
def test_reconhecimento_seis_perfis_hash_e_confirmacao(monkeypatch,perfil):
    c=caso(perfil)
    with pytest.raises(ErroLeitura):reconhecer(c.financeiro)
    assert reconhecer(c.financeiro,perfil_informado=perfil)[0]['id']==perfil
    homologar(monkeypatch,[c])
    assert reconhecer(c.financeiro)[0]['id']==perfil
    assert reconhecer(c.cadastro,cadastro=True,perfil_informado=perfil)[0]['id']==perfil
    for outro in PERFIS:
        if outro!=perfil:
            with pytest.raises(ErroLeitura):reconhecer(c.financeiro,perfil_informado=outro)
    # Hash reconhecido nunca autoriza um documento cuja estrutura é inválida.
    bad=b'CONTEUDO FICTICIO INVALIDO'
    monkeypatch.setitem(CONFIG[perfil]['fontes_homologacao_sha256'],'inadimplencia',sha256(bad).hexdigest())
    with pytest.raises(ErroLeitura):reconhecer(bad,perfil_informado=perfil)


@pytest.mark.parametrize('perfil',PERFIS)
@pytest.mark.parametrize('modo',['A','B'])
def test_financeiro_limites_contrato_cadastro_opcional(tmp_path,monkeypatch,perfil,modo):
    c=caso(perfil);homologar(monkeypatch,[c]);a=executar(tmp_path/'sem',c,modo=modo,cad=False);b=executar(tmp_path/'com',c,modo=modo)
    for r in(a,b):
        assert r['resumo']['dividas_efetivamente_geradas']==1
        assert r['resumo']['cadastros_adicionais']==int(modo=='B')
        assert not r['autoriza_cobranca']and not r['permite_exportacao_operacional']
    rows=ler_saida(tmp_path/'com');assert rows[0]==COLUNAS and len(rows)==2+int(modo=='B')
    assert str(Decimal(str(rows[1][29])).quantize(Decimal('.01')))==c.valor
    assert rows[1][2]==CPF and rows[1][3]==NOME
    assert rows[1][28].date()==c.ref-timedelta(days=c.prazo+1)
    assert a['perfil']==b['perfil']==perfil
    canonical=json.loads((tmp_path/'com'/'canonico.json').read_text(encoding='utf-8'))
    assert len(canonical['boletos'])==3
    assert all(o['sha256']==sha256(c.financeiro).hexdigest()for b in canonical['boletos']for o in b['origens'])


@pytest.mark.parametrize('financeiro',PERFIS)
@pytest.mark.parametrize('cadastro',PERFIS)
def test_nenhum_cadastro_cruzado_e_aceito(tmp_path,monkeypatch,financeiro,cadastro):
    a,b=caso(financeiro),caso(cadastro);homologar(monkeypatch,[a,b])
    if financeiro==cadastro:
        assert executar(tmp_path,a)['resumo']['dividas_efetivamente_geradas']==1
    else:
        with pytest.raises(ErroLeitura):executar(tmp_path,replace(a,cadastro=b.cadastro))


@pytest.mark.parametrize('perfil',PERFIS)
@pytest.mark.parametrize('situacao',['divergente','ausente','invalido','multiplo'])
def test_associacoes_conservadoras_sem_excluir_divida(tmp_path,monkeypatch,perfil,situacao):
    c=caso(perfil,nome='Pessoa Ficticia Alfa E Pessoa Ficticia Beta'if situacao=='multiplo'else NOME,
        nome_cad='Pessoa Ficticia Divergente'if situacao=='divergente'else'Pessoa Ficticia Alfa E Pessoa Ficticia Beta'if situacao=='multiplo'else NOME,
        documento=''if situacao=='ausente'else'00000000000'if situacao=='invalido'else CPF)
    homologar(monkeypatch,[c]);r=executar(tmp_path,c)
    assert r['resumo']['dividas_efetivamente_geradas']==1
    row=ler_saida(tmp_path)[1];assert row[2]is None
    assert r['politica_cadastral']==r['cadastro_'+perfil]['politica']
    assert not r['autoriza_cobranca']and not r['permite_exportacao_operacional']


@pytest.mark.parametrize('perfil',PERFIS)
def test_mesmo_vencimento_multiplicidade_e_estabilidade(tmp_path,monkeypatch,perfil):
    p=60 if perfil in('passaredo','parque_santa_monica')else 30
    c=caso(perfil,dias=(p+1,p+1,p));homologar(monkeypatch,[c])
    executar(tmp_path/'a',c);executar(tmp_path/'b',c)
    a,b=ler_saida(tmp_path/'a'),ler_saida(tmp_path/'b')
    assert a==b and len(a)==3 and [r[27]for r in a[1:]]==[1,2]


def test_itajuba_cadastro_novo_nao_e_comprovado_por_escolha():
    c=caso('itajuba')
    with pytest.raises(ErroLeitura,match='CADASTRO_IDENTIDADE_NAO_COMPROVADA'):
        reconhecer(c.cadastro,cadastro=True,perfil_informado='itajuba')


@pytest.mark.parametrize('modo',['A','B'])
def test_itajuba_mesmo_apartamento_em_torres_distintas_isola_documentos_e_contatos(tmp_path,monkeypatch,modo):
    from tests.itajuba import fixtures as f
    c=replace(caso('itajuba'),financeiro=f.financeiro([
        (torre,'A-01',[f.linha(doc='Tt_'+torre+'_A-01',nome=NOME,dias=d)for d in (31,32)])
        for torre in ('T-01','T-02')]),cadastro=f.cadastro([
            f.ficha('T-01','A-01',nome=NOME,documento=f.CPF,telefone='0123-4567',email='torre1@example.invalid'),
            f.ficha('T-02','A-01',nome=NOME,documento=f.OUTRO_CPF,telefone='0234-5678',email='torre2@example.invalid')]))
    homologar(monkeypatch,[c]);r=executar(tmp_path,c,modo=modo)
    rows=ler_saida(tmp_path);assert rows[0]==COLUNAS and len(rows)==5
    assert r['resumo']['dividas_efetivamente_geradas']==4
    assert r['cadastro_itajuba']['associacoes_retidas']==0
    assert r['politica_cadastral']=='itajuba_nome_e_unidade_por_lancamento_A1@1'
    for complemento,documento,telefone,email in (
            ('QUAT01-LTA0001',f.CPF,'01234567','torre1@example.invalid'),
            ('QUAT02-LTA0001',f.OUTRO_CPF,'02345678','torre2@example.invalid')):
        group=[row for row in rows[1:]if row[6]==complemento]
        assert len(group)==2 and [row[27]for row in group]==[1,2]
        assert all(row[2]==documento and not row[11] and row[12]==telefone and row[21]==email for row in group)
        assert all(not any(row[13:21])and not any(row[22:24])for row in group)
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    units={u['id']:(u['bloco_original'],u['unidade_original'])for u in canonical['unidades']}
    assert set(units.values())=={('T-01','A-01'),('T-02','A-01')} and len(units)==2
    assert {b['unidade_id']for b in canonical['boletos']}==set(units)


@pytest.mark.parametrize('modo',['A','B'])
def test_itajuba_retencoes_contam_identidades_com_torre_sem_transferir_contatos(tmp_path,monkeypatch,modo):
    from tests.itajuba import fixtures as f
    c=replace(caso('itajuba'),financeiro=f.financeiro([
        (torre,'A-01',[f.linha(doc='Tt_'+torre+'_A-01',nome=NOME,dias=d)for d in (31,32)])
        for torre in ('T-01','T-02')]),cadastro=f.cadastro([
            f.ficha(torre,'A-01',nome='Outra Pessoa Integralmente Ficticia')for torre in ('T-01','T-02')]))
    homologar(monkeypatch,[c]);r=executar(tmp_path,c,modo=modo)
    assert r['resumo']['dividas_efetivamente_geradas']==4
    assert r['cadastro_itajuba']['associacoes_retidas']==4
    assert r['cadastro_itajuba']['unidades_em_revisao']==2
    assert r['politica_cadastral']=='itajuba_nome_e_unidade_por_lancamento_A1@1'
    rows=ler_saida(tmp_path);assert rows[0]==COLUNAS and len(rows)==5
    assert all(not row[2]and not any(row[11:24])for row in rows[1:])
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    retained={n['registro_id']for n in canonical['ressalvas']if n['codigo']=='PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO'}
    unit_ids={b['unidade_id']for b in canonical['boletos']if b['id']in retained}
    assert len(retained)==4 and len(unit_ids)==2
    assert {(u['bloco_original'],u['unidade_original'])for u in canonical['unidades']if u['id']in unit_ids}=={('T-01','A-01'),('T-02','A-01')}


def test_mesma_sessao_alterna_os_seis_perfis_e_rejeita_cruzamentos(tmp_path,monkeypatch):
    casos=[caso(p)for p in PERFIS];homologar(monkeypatch,casos)
    app=criar_app_efemero(area_temporaria=tmp_path)
    with TestClient(app,base_url=ORIGIN)as client:
        boot(client);previous=None
        for i,c in enumerate(casos):
            # Nome enganoso não decide identidade nem extensão.
            identified=client.post('/api/identificar',files={'inadimplencia':('outro-condominio.pdf',c.financeiro)})
            assert identified.status_code==200 and identified.json()['perfil']==c.perfil
            ctx=identified.json()['contexto']
            for mode in('A','B'):
                form={'data_ref':str(c.ref),'modo':mode,'condominio':c.perfil,'contexto':ctx}
                bad=client.post('/api/conversoes',data=form,files={'inadimplencia':('ficticio.'+c.ext,c.financeiro),'cadastro':('cruzado.'+casos[(i+1)%6].ext_cad,casos[(i+1)%6].cadastro)})
                assert bad.status_code==422
                if previous:
                    invalid=client.post('/api/conversoes',data=dict(form,contexto=previous),files={'inadimplencia':('ficticio.'+c.ext,c.financeiro)})
                    assert invalid.status_code==409
                    assert invalid.json()['detail']=='DOCUMENTO_ALTERADO_IDENTIFIQUE_NOVAMENTE'
                r=client.post('/api/conversoes',data=form,files={'inadimplencia':('ficticio.'+c.ext,c.financeiro),'cadastro':('ficticio.'+c.ext_cad,c.cadastro)})
                assert r.status_code==200;r=r.json()
                assert 'cadastro_'+c.perfil in r and 'revisao_cadastral_'+c.perfil in r
                assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==int(mode=='B')
                assert not any(p.is_file()for p in tmp_path.rglob('*'))
                id_=r['id'];assert client.get(f'/api/conversoes/{id_}/operacional.xlsx').status_code==409
                with TestClient(criar_app_efemero(),base_url=ORIGIN)as other:
                    boot(other);assert other.get(f'/api/conversoes/{id_}/excel').status_code==404
                data=client.get(f'/api/conversoes/{id_}/excel');assert data.status_code==200
                w=load_workbook(BytesIO(data.content));rows=list(w['Dados'].values);w.close()
                assert rows[0]==COLUNAS and len(rows)==2+int(mode=='B')
                assert client.get(f'/api/conversoes/{id_}/excel').status_code==404
            previous=ctx
        assert client.post('/api/identificar',files={'inadimplencia':('ficticio.xlsx',casos[0].financeiro)},headers={'x-csrf-token':'invalido'}).status_code==403
        assert client.get('/api/config',headers={'Origin':'http://origem-ficticia.invalid'}).status_code==403
        assert client.get('/api/config',headers={'Host':'host-ficticio.invalid'}).status_code==400
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('perfil',['parque_santa_monica','vero_encanto','terraco_beach_parque'])
def test_componentes_assinados_de_familias_distintas_nao_se_misturam(tmp_path,monkeypatch,perfil):
    from tests.oma import fixtures as oma
    from tests.beach_parque import fixtures as bpq
    c=caso(perfil,dias=(61,))
    comps=[('DESPESA FICTICIA','100','100','1','2','3'),('ESTORNO FICTICIO','-1.10','-1.10','0','0','0')]
    if perfil=='parque_santa_monica':
        raw=oma.financeiro([('01','000001',NOME,[oma.recibo('991 A',61,comps)])])
    elif perfil=='vero_encanto':
        from tests.vero import fixtures as vero
        raw=vero.financeiro([('A00004',NOME,[vero.recibo(991,61,[(1,'DESPESA FICTICIA','100'),(1,'ESTORNO FICTICIO','-1.10')])])])
    else:
        raw=bpq.financeiro([('A','A00001',NOME,[bpq.recibo('A 991',61,comps)])])
    c=replace(c,financeiro=raw);homologar(monkeypatch,[c]);r=executar(tmp_path,c)
    assert r['resumo']['dividas_efetivamente_geradas']==1
    assert ler_saida(tmp_path)[1][29]==98.9
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    assert len(canonical['boletos'][0]['composicao']['itens'])==2
    assert canonical['boletos'][0]['composicao']['itens'][1]['valor']=='-1.10'


@pytest.mark.parametrize('perfil',['vero_encanto','terraco_beach_parque'])
def test_continuidades_e_registros_especiais_nao_contaminam_outro_perfil(tmp_path,monkeypatch,perfil):
    if perfil=='vero_encanto':
        from tests.vero import fixtures as f
        regular=f.ficha(pessoas=[f.participante(nome=NOME,documento=CPF)])
        ys=sorted({y for x,y,t in regular},reverse=True);cut=ys[8]
        cad=f.cadastro([[r for r in regular if r[1]>=cut],[r for r in regular if r[1]<cut],f.ficha('SINDPR',torre='A')])
        special='SINDPR'
    else:
        from tests.beach_parque import fixtures as f
        cad=f.cadastro(f.dividir(f.ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF),2)+[f.ficha(bloco='0',numero='DANPRI')],total=2)
        special='DANPRI'
    c=replace(caso(perfil),cadastro=cad);homologar(monkeypatch,[c]);r=executar(tmp_path,c,modo='B')
    assert r['resumo']['dividas_efetivamente_geradas']==1
    assert r['resumo']['cadastros_adicionais']==1
    assert all(special not in str(v)for row in ler_saida(tmp_path)[1:]for v in row)
    assert ler_saida(tmp_path)[1][2]==CPF


def test_escopo_itajuba_nao_e_aplicado_a_outra_familia(tmp_path,monkeypatch):
    from datetime import date
    from tests.itajuba import fixtures as itj
    from tests.beach_parque import fixtures as bpq
    a=caso('itajuba');b=caso('terraco_beach_parque')
    a=replace(a,financeiro=itj.financeiro([('T-01','A-01',[itj.linha(vencimento=date(2023,11,30),nome=NOME),itj.linha(vencimento=date(2023,12,1),nome=NOME)])]))
    old=bpq.recibo('1',31);old['vencimento']=date(2023,11,30)
    b=replace(b,financeiro=bpq.financeiro([('A','A00001',NOME,[old])]))
    homologar(monkeypatch,[a,b]);ra=executar(tmp_path/'itj',a);rb=executar(tmp_path/'bpq',b)
    assert ra['resumo']['dividas_efetivamente_geradas']==rb['resumo']['dividas_efetivamente_geradas']==1
    assert any('ITAJUBA_ESCOPO_ANTERIOR_DEZ2023_REQUER_REVISAO'in d['bloqueios']for d in ra['decisoes'])
    assert all('ITAJUBA_ESCOPO_ANTERIOR_DEZ2023_REQUER_REVISAO'not in d['bloqueios']for d in rb['decisoes'])


@pytest.mark.parametrize('perfil',PERFIS)
def test_conflitos_documentais_respeitam_contrato_de_cada_cadastro(tmp_path,monkeypatch,perfil):
    from tests.passaredo import fixtures as t
    from tests.oma import fixtures as o
    from tests.vero import fixtures as v
    from tests.itajuba import fixtures as i
    from tests.beach_parque import fixtures as b
    c=caso(perfil)
    if perfil in('passaredo','forest_hill'):
        cad=t.cadastro([t.ficha(unidade='007'if perfil=='passaredo'else'AV.P02 231',nome=NOME,documento=CPF,outro_documento='00000000272')])
    elif perfil=='parque_santa_monica':cad=o.cadastro([o.ficha(bloco='01',numero='000001',nome=NOME,documento=CPF,segundo_documento='00000000272')])
    elif perfil=='vero_encanto':cad=v.cadastro([v.ficha(pessoas=[v.participante(nome=NOME,documento=CPF,segundo_documento='00000000000191')])])
    elif perfil=='terraco_beach_parque':cad=b.cadastro([b.ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,segundo_documento='00000000272')])
    else:cad=i.cadastro([i.ficha(nome=NOME,documento=CPF),i.ficha(nome=NOME,documento='00000000272')])
    c=replace(c,cadastro=cad);homologar(monkeypatch,[c])
    if perfil=='itajuba':
        # Esse formato exige ficha única por unidade: ambiguidade estrutural
        # rejeita o cadastro inteiro, sem rebaixar a proteção para integrar.
        with pytest.raises(ErroLeitura,match='UNIDADE_DUPLICADA'):executar(tmp_path/'com',c)
        assert executar(tmp_path/'sem',c,cad=False)['resumo']['dividas_efetivamente_geradas']==1
    else:
        r=executar(tmp_path,c);assert r['resumo']['dividas_efetivamente_geradas']==1
        assert ler_saida(tmp_path)[1][2]is None


@pytest.mark.parametrize('perfil',PERFIS)
def test_expiracao_e_encerramento_em_todos_os_perfis(tmp_path,monkeypatch,perfil):
    from tests.web.test_ephemeral import Clock
    from conversor.web.ephemeral import RETENCAO
    c=caso(perfil);homologar(monkeypatch,[c]);clock=Clock();app=criar_app_efemero(area_temporaria=tmp_path,relogio=clock)
    with TestClient(app,base_url=ORIGIN)as client:
        boot(client)
        r=client.post('/api/conversoes',data={'data_ref':str(c.ref),'modo':'A','condominio':perfil},files={'inadimplencia':('ficticio.'+c.ext,c.financeiro),'cadastro':('ficticio.'+c.ext_cad,c.cadastro)})
        assert r.status_code==200;id_=r.json()['id']
        assert client.get('/api/conversoes/'+id_+'/detalhes').status_code==200
        clock.now+=RETENCAO+1
        assert client.get('/api/conversoes/'+id_+'/detalhes').status_code==404
    assert not list(tmp_path.iterdir())
