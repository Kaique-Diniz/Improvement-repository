"""VEC-01: evidências sintéticas; não requer documentos privados."""
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conversor.application.vero_cadastro import associar, POLITICA
from conversor.domain.vero_encanto import complemento_unidade
from conversor.domain.documents import resolver_documento
from conversor.readers.vero_xlsx import LeitorVeroXLSX, originais
from conversor.readers.vero_cadastro import LeitorCadastroVero
from conversor.readers.vero_identity import IdentidadeVeroNaoComprovada
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from conversor.web.service import PERFIS, PedidoDiagnostico, analisar, reconhecer
from conversor.web.ephemeral import criar_app_efemero
from tests.web.test_classic_local import boot, ORIGIN
from tests.web.test_ephemeral import Clock
from .fixtures import REF, NOME, CPF, OUTRO_CPF, CNPJ, financeiro, cadastro, recibo, ficha, participante


def ler(raw,cad=False):
    reader=LeitorCadastroVero() if cad else LeitorVeroXLSX()
    return reader.ler(raw,contexto=ContextoLeitura('condominio_vero_encanto','lello_2',reader.formato_id,
        'cadastro' if cad else 'inadimplencia','vero_encanto'))


def executar(tmp_path,raw=None,cad=None,modo='A',ref=REF):
    return analisar(raw if raw is not None else financeiro(),PedidoDiagnostico(data_ref=ref,modo=modo,condominio='vero_encanto'),
        processamento_id='vero_sintetico',destino=tmp_path,cadastro=cad,historico=(),estado_historico='nao_disponivel')


def rows(path):
    b=load_workbook(path)
    try:return list(b['Dados'].values)
    finally:b.close()


def test_um_recibo_componentes_valorados_e_sem_valor_proveniencia_real():
    raw=financeiro([('A00004',NOME,[recibo(componentes=[(1,'HISTORICO FICTICIO 09/2026','110.10'),(1,'ESTORNO FICTICIO','-10.00'),(2,'MEMORIA',None)])])])
    l=ler(raw);b=l.boletos[0];e=originais(l)[b.id]
    assert len(l.boletos)==1 and len(b.composicao.itens)==2
    assert b.composicao.total_original==Decimal('100.10') and b.competencia is None
    assert b.identificador=='900001' and b.multa==1 and b.juros is None and b.correcao is None
    assert e['valores'][2]=='2.00' and e['correcao_juros_indissociados']
    assert len(e['componentes'])==3 and e['componentes'][2]['valor'] is None
    assert [x['conta']for x in e['componentes']]==['1','1','2']
    assert all(o.sha256==sha256(raw).hexdigest() for o in b.origens)


@pytest.mark.parametrize('unit,expected',[('A00004','BLA-UNI0004'),('B01712','BLB-UNI1712')])
def test_codificacao_textual_e_torres_distintas(unit,expected):
    assert complemento_unidade(unit[0],unit)==expected
    l=ler(financeiro([(unit,NOME,[recibo()])]))
    assert l.unidades[0].unidade_original==unit and l.unidades[0].bloco_original==unit[0]


@pytest.mark.parametrize('unit',['A0004','a00004','C00004','B10004','A00004/1',' A00004','A００００４'])
def test_unidade_nao_documentada_rejeitada(unit):
    with pytest.raises(ValueError):complemento_unidade('A',unit)


@pytest.mark.parametrize('kind',['total','composicao','geral','formula','vencimento','aba','coluna','cabecalho','separador','fechamento','identidade','multicontas','apos_fim','sem_valor','empresa'])
def test_estrutura_e_somas_inconsistentes_nao_aprovam(kind):
    def change(w,s):
        if kind=='total':s['F8']='999'
        if kind=='composicao':s['E10']='999'
        if kind=='geral':s.cell(s.max_row,3,'999')
        if kind=='formula':s['E10']='=1+1'
        if kind=='vencimento':s['B8']='31/02/2026'
        if kind=='aba':s.title='Outra'
        if kind=='coluna':s['G8']='EXTRA'
        if kind=='cabecalho':s['C7']='Atualizado'
        if kind=='separador':s['A9']='EXTRA'
        if kind=='fechamento':s.delete_rows(s.max_row)
        if kind=='identidade':s['B4']='10888 - OUTRO CONDOMINIO FICTICIO'
        if kind=='multicontas':s['B6']='SIM'
        if kind=='apos_fim':s.append(['EXTRA'])
        if kind=='sem_valor':s['E10']=None
        if kind=='empresa':s['B3']='LELLO EMPRESA NAO COMPROVADA'
    with pytest.raises(ErroLeitura):ler(financeiro(mutar=change))


def test_recibo_duplicado_rejeitado_mesmo_em_outra_unidade():
    for groups in ([('A00004',NOME,[recibo(),recibo()])],[('A00004',NOME,[recibo()]),('B01712',NOME,[recibo()])]):
        with pytest.raises(ErroLeitura,match='RECIBO_DUPLICADO'):ler(financeiro(groups))


@pytest.mark.parametrize('days,expected',[(30,0),(31,1),(32,1)])
def test_limite_em_dias_corridos_e_referencia_explicita(tmp_path,days,expected):
    raw=financeiro([('A00004',NOME,[recibo(dias=days)])])
    r=executar(tmp_path/'hoje',raw)
    assert r['resumo']['dividas_efetivamente_geradas']==expected
    earlier=executar(tmp_path/'ontem',raw,ref=REF-timedelta(days=1))
    assert earlier['resumo']['dividas_efetivamente_geradas']==int(days-1>30)


def test_cadastro_coproprietarios_individuais_sem_primeiro_titular():
    cad=ler(cadastro([ficha(pessoas=[participante(nome='Outra Pessoa Ficticia',documento=OUTRO_CPF,participacao='50,00'),participante(participacao='50,00')])]),True)
    assert len(cad.pessoas)==2 and len({p.id for p in cad.pessoas})==2
    assert {resolver_documento(p).valor for p in cad.pessoas}=={CPF,OUTRO_CPF}
    l,people,summary,review=associar(ler(financeiro()),cad)
    p=people[l.boletos[0].id]
    assert resolver_documento(p).valor==CPF and p.nome==NOME and not review
    assert summary['participacao_percentual_nao_define_titular']
    assert p.contato.telefones[0].ddd=='' and p.contato.telefones[0].numero=='900000001'
    assert len(p.contato.telefones)==1 and 'terceiro@example.invalid' not in p.contato.emails


def test_continuacao_de_participante_entre_paginas_preserva_documentos():
    body=ficha(pessoas=[participante(participacao='50,00'),participante(nome='Outra Pessoa Ficticia',documento=OUTRO_CPF,participacao='50,00')])
    ys=sorted({y for x,y,t in body},reverse=True);cut=ys[8]
    raw=cadastro([[r for r in body if r[1]>=cut],[r for r in body if r[1]<cut]])
    l=ler(raw,True)
    assert len(l.unidades)==1 and len(l.pessoas)==2
    assert {resolver_documento(p).valor for p in l.pessoas}=={CPF,OUTRO_CPF}
    note=next(r for r in l.ressalvas if r.registro_id==l.pessoas[0].id)
    assert {o.pagina for o in note.origens}=={1,2}


@pytest.mark.parametrize('kind',['ausente','invalido','malformado','nome','ambiguo','multiplos','conflito','outro_sem_documento'])
def test_retencao_conservadora_nao_perde_divida(tmp_path,kind):
    p=participante();name=NOME
    if kind=='ausente':p['documento']=''
    if kind=='invalido':p['documento']='11111111111'
    if kind=='malformado':p['documento']='texto'+CPF
    if kind=='nome':name='Nome Financeiro Ficticio Divergente'
    if kind=='multiplos':name=p['nome']='Pessoa Ficticia Um E Pessoa Ficticia Dois'
    if kind=='conflito':p['segundo_documento']=CNPJ
    ps=[p]
    if kind=='ambiguo':ps.append(participante(documento=OUTRO_CPF))
    if kind=='outro_sem_documento':
        ps=[participante(nome='Outro Participante Ficticio'),participante(documento='',participacao='50,00')]
    r=executar(tmp_path,financeiro([('A00004',name,[recibo()])]),cadastro([ficha(pessoas=ps)]))
    assert r['resumo']['dividas_efetivamente_geradas']==1
    assert r['cadastro_vero_encanto']['associacoes_retidas']==1
    row=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')[1]
    assert not row[2] and row[3]==name and not any(row[i] for i in range(11,24))


def test_empresa_com_e_e_cnpj_comprovado_nao_e_retida(tmp_path):
    name='Empresa Ficticia Alfa E Beta LTDA'
    r=executar(tmp_path,financeiro([('A00004',name,[recibo()])]),cadastro([ficha(pessoas=[participante(nome=name,documento=CNPJ,tipo='Jurídica')])]))
    assert r['cadastro_vero_encanto']['documentos_validos_vinculados']==1


def test_mesmo_documento_em_participantes_com_nomes_diferentes_retem(tmp_path):
    raw=cadastro([ficha(pessoas=[participante(participacao='50,00'),
        participante(nome='Outra Pessoa Ficticia',participacao='50,00')])])
    r=executar(tmp_path,cad=raw)
    assert r['cadastro_vero_encanto']['retencoes_por_motivo']=={'VERO_DOCUMENTOS_CONFLITANTES_CADASTRO':1}
    assert not rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')[1][2]
    assert r['resumo']['dividas_efetivamente_geradas']==1


def test_participante_nominal_valido_nao_herda_ausencia_do_coproprietario(tmp_path):
    raw=cadastro([ficha(pessoas=[participante(participacao='50,00'),
        participante(nome='Outra Pessoa Ficticia',documento='',participacao='50,00')])])
    r=executar(tmp_path,cad=raw)
    assert r['cadastro_vero_encanto']['documentos_validos_vinculados']==1
    assert rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')[1][2]==CPF


def test_cnpj_invalido_nao_atribuido_sem_excluir_divida(tmp_path):
    name='Empresa Integralmente Ficticia LTDA'
    raw=financeiro([('A00004',name,[recibo()])])
    cad=cadastro([ficha(pessoas=[participante(nome=name,documento='11111111111111',tipo='Jurídica')])])
    r=executar(tmp_path,raw,cad)
    assert r['cadastro_vero_encanto']['retencoes_por_motivo']=={'VERO_DOCUMENTO_INVALIDO_ASSOCIACAO_RETIDA':1}
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')[1][2]


@pytest.mark.parametrize('modo',['A','B'])
def test_modoref_30_campos_original_rotulo_auditoria(tmp_path,modo):
    raw=financeiro([('A00004',NOME,[recibo(900002,days)for days in [31]]+[recibo(900001,30)]),('B01712',NOME,[recibo(900003,32)])])
    r=executar(tmp_path,raw,modo=modo)
    table=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert len(table[0])==30 and table[0][26]=='NM_DIVIDA_CEDENTE'
    assert r['resumo']['dividas_efetivamente_geradas']==2 and r['resumo']['cadastros_adicionais']==(modo=='B')
    assert all(row[0]=='LELLO_2' for row in table[1:])
    debts=[row for row in table[1:]if row[29]is not None]
    assert all(Decimal(str(row[29]))==Decimal('100.10')for row in debts)
    assert debts[0][26]=='COTA 10/2026 - 1' and debts[0][1]=='BLA-UNI0004-DI 31 I – VERO ENCANTO'
    manifest=json.loads((tmp_path/'manifesto_diagnostico.json').read_text(encoding='utf-8'))
    audit=json.loads((tmp_path/'auditoria.json').read_text(encoding='utf-8'))
    assert r['politica_cadastral']==manifest['cadastro_vero_encanto']['politica']==audit['politica_cadastral']==POLITICA
    assert not r['autoriza_cobranca'] and not r['permite_exportacao_operacional']


def test_hash_real_entradas_identicas_determinismo(tmp_path):
    raw=financeiro();r1=executar(tmp_path/'um',raw);r2=executar(tmp_path/'dois',raw)
    assert r1['decisoes']==r2['decisoes']
    assert (tmp_path/'um/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'dois/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    other=financeiro([('A00004',NOME,[recibo(900002)])]);r3=executar(tmp_path/'tres',other)
    assert r1['fontes'][0]['sha256']==sha256(raw).hexdigest()!=r3['fontes'][0]['sha256']


def test_identidade_nova_exige_confirmacao_e_hash_nao_dispensa_gramatica(monkeypatch):
    raw=financeiro()
    with pytest.raises(IdentidadeVeroNaoComprovada):reconhecer(raw)
    assert reconhecer(raw,perfil_informado='vero_encanto')[0]['id']=='vero_encanto'
    monkeypatch.setitem(PERFIS['vero_encanto']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    assert reconhecer(raw)[0]['id']=='vero_encanto'
    bad=financeiro(mutar=lambda w,s:s.cell(s.max_row,3,'999'))
    monkeypatch.setitem(PERFIS['vero_encanto']['fontes_homologacao_sha256'],'inadimplencia',sha256(bad).hexdigest())
    with pytest.raises(ErroLeitura):reconhecer(bad)
    with pytest.raises(ErroLeitura):reconhecer(raw,perfil_informado='passaredo')


def test_cadastro_outro_condominio_ou_torre_incompativel_rejeita():
    with pytest.raises(ErroLeitura,match='IDENTIDADE_DIVERGENTE'):ler(cadastro(referencia='99999-10'),True)
    def change(i,rs):return [(x,y,'TORRE B'if t=='TORRE A'else t)for x,y,t in rs]
    with pytest.raises(ErroLeitura,match='TORRE_DIVERGENTE'):ler(cadastro(mutar=change),True)


def test_registro_textual_auxiliar_nao_prova_unidade_financeira(tmp_path):
    raw=cadastro([ficha(),ficha('APOIOX')])
    cad=ler(raw,True)
    assert len(cad.unidades)==2 and len(cad.pessoas)==2
    assert sum(r.codigo=='VERO_REGISTRO_CADASTRAL_SEM_CODIFICACAO_FINANCEIRA' for r in cad.ressalvas)==1
    r=executar(tmp_path,cad=raw)
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['cadastro_vero_encanto']['documentos_validos_vinculados']==1


@pytest.mark.parametrize('modo',['A','B'])
def test_sindpr_na_ultima_pagina_isolado_sem_transferir_documento_ou_contatos(tmp_path,modo):
    regular=ficha(pessoas=[participante(documento='',participacao='50,00'),
        participante(nome='Outro Condomino Integralmente Ficticio',participacao='50,00')])
    especial=ficha('SINDPR',[participante(documento=OUTRO_CPF)],torre='A')

    def contatos_especiais(i,registros):
        if i!=1:return registros
        valores={'titular@example.invalid':'especial@example.invalid',
            'boleto@example.invalid':'boleto-especial@example.invalid','90000-0001':'(55) 90000-0055'}
        return [(x,y,valores.get(t,t))for x,y,t in registros]

    raw=cadastro([regular,especial],mutar=contatos_especiais)
    cad=ler(raw,True)
    por_codigo={u.unidade_original:u for u in cad.unidades}
    contagem=Counter(p.unidade_id for p in cad.pessoas)
    assert set(por_codigo)=={'A00004','SINDPR'}
    assert contagem[por_codigo['A00004'].id]==2 and contagem[por_codigo['SINDPR'].id]==1
    pessoa_especial=next(p for p in cad.pessoas if p.unidade_id==por_codigo['SINDPR'].id)
    assert pessoa_especial.origem.pagina==2 and resolver_documento(pessoa_especial).valor==OUTRO_CPF
    assert pessoa_especial.contato.emails==('especial@example.invalid','boleto-especial@example.invalid')
    assert pessoa_especial.contato.telefones[0].ddd=='55'
    nota=next(r for r in cad.ressalvas if r.codigo=='VERO_REGISTRO_CADASTRAL_SEM_CODIFICACAO_FINANCEIRA')
    assert nota.registro_id==por_codigo['SINDPR'].id and nota.valores_originais==('SINDPR',)
    with pytest.raises(ValueError):complemento_unidade('A','SINDPR')

    financeiro_raw=financeiro([('A00004',NOME,[recibo(900001,31),recibo(900002,30)])])
    lote=ler(financeiro_raw)
    _,pessoas,resumo,_=associar(lote,cad)
    assert resumo['documentos_validos_vinculados']==0
    assert all(not resolver_documento(p).valor and not p.contato.emails and not p.contato.telefones for p in pessoas.values())
    resultado=executar(tmp_path,financeiro_raw,raw,modo=modo)
    assert resultado['resumo']['dividas_efetivamente_geradas']==1
    assert resultado['resumo']['cadastros_adicionais']==int(modo=='B')
    tabela=rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert len(tabela[0])==30 and len(tabela)-1==1+int(modo=='B')
    assert all(not row[2] and not any(row[11:24]) for row in tabela[1:])
    assert all('SINDPR' not in str(v) for row in tabela[1:] for v in row)


def test_documento_malformado_preservado_na_evidencia_sem_atribuicao():
    original='texto-arbitrario-'+CPF
    cad=ler(cadastro([ficha(pessoas=[participante(documento=original)])]),True)
    assert cad.pessoas[0].documento is None and not cad.pessoas[0].evidencias_documentais
    note=next(r for r in cad.ressalvas if r.codigo=='VERO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO')
    assert note.valores_originais==(original,)


def test_modo_b_uma_linha_por_unidade_inclusive_sem_divida_elegivel(tmp_path):
    raw=financeiro([('A00004',NOME,[recibo(900001,31),recibo(900002,30),recibo(900003,29)]),
        ('B01712',NOME,[recibo(900004,30),recibo(900005,29)])])
    r=executar(tmp_path,raw,modo='B')
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==2
    assert len(rows(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx'))==4


@pytest.mark.parametrize('kind',['unidade_duplicada','nome_ausente','participacao_invalida','nome_duplicado'])
def test_cadastro_estruturalmente_ambiguo_rejeitado(kind):
    pages=[ficha()]
    if kind=='unidade_duplicada':pages=[ficha()+[(x,y-260,t)for x,y,t in ficha()]]
    if kind=='nome_ausente':pages=[[(x,y,t)for x,y,t in ficha() if not(x==143 and t==NOME)]]
    if kind=='participacao_invalida':pages=[ficha(pessoas=[participante(participacao='101,00')])]
    if kind=='nome_duplicado':
        body=ficha();name=[(x,y-7,t)for x,y,t in body if y==681];pages=[body+name]
    with pytest.raises(ErroLeitura):ler(cadastro(pages),True)


def test_fluxo_web_confirmacao_download_isolamento_e_descarte(tmp_path):
    app=criar_app_efemero(area_temporaria=tmp_path,relogio=Clock())
    with TestClient(app,base_url=ORIGIN) as c:
        boot(c)
        raw=financeiro();f={'inadimplencia':('nome-enganoso.xlsx',raw)}
        identify=c.post('/api/identificar',files=f);assert identify.status_code==409
        confirmed=c.post('/api/identificar',data={'condominio':'vero_encanto'},files=f)
        assert confirmed.status_code==200
        r=c.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':'vero_encanto','contexto':confirmed.json()['contexto']},
            files={**f,'cadastro':('cadastro-ficticio.pdf',cadastro())})
        assert r.status_code==200
        result=r.json();id_=result['id']
        assert result['cadastro_vero_encanto']['documentos_validos_vinculados']==1
        assert not list(app.state.ciclo.root.iterdir())
        assert c.get('/api/conversoes/'+id_+'/operacional.xlsx').status_code==409
        other=TestClient(app,base_url=ORIGIN)
        try:
            boot(other);assert other.get('/api/conversoes/'+id_+'/excel').status_code==404
        finally:
            other.close()
        download=c.get('/api/conversoes/'+id_+'/excel');assert download.status_code==200
        assert len(rows(BytesIO(download.content))[0])==30
        assert c.get('/api/conversoes/'+id_+'/excel').status_code==404
