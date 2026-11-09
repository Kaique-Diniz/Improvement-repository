"""BPQ-04: somente pessoas, documentos e contatos fictícios."""
import json

import pytest

from conversor.application.beach_parque_cadastro import (
    POLITICA, POLITICA_B1, associar, _titular_individual_comprovado,
)
from conversor.application.passaredo_cadastro import responsabilidade_multipla_sem_vinculo_empresarial
from conversor.domain.documents import evidencias_documento, resolver_documento
from conversor.domain.template import COLUNAS
from .fixtures import CPF, NOME, cadastro, dividir, ficha, financeiro, recibo
from .test_beach_parque import executar, ler_cad, ler_fin, rows, PROFILE

NOME_COMPOSTO = 'PESSOA FICTICIA E INVENTADA'
CONTATOS = ['Celular - (11) 91234-5678', 'Telefone - 0123-4567', 'E-mail - titular@example.invalid']


def fontes(nome=NOME_COMPOSTO, documento=CPF, contatos=None, *, nome_cad=None, **kw):
    fin = financeiro([('A','A00001',nome,[recibo('101',31),recibo('102',30)])])
    body = ficha(bloco='A',numero='A00001',nome=nome_cad or nome,documento=documento,
        contatos=CONTATOS if contatos is None else contatos,**kw)
    return fin,body


@pytest.mark.parametrize('modo',['A','B'])
@pytest.mark.parametrize('documento',[CPF,'000.000.001-91'])
def test_sobrenome_terminal_exige_ficha_fisica_individual_documentada(tmp_path,modo,documento):
    fin,body=fontes(documento=documento)
    if '.'in documento:body=[(x,y,t.replace('CNPJ: '+documento,'CPF: '+documento))for x,y,t in body]
    pdf=cadastro([body]);c=ler_cad(pdf)
    # O padrão dos demais condomínios permanece conservador e inalterado.
    assert responsabilidade_multipla_sem_vinculo_empresarial(NOME_COMPOSTO,evidencias_documento(c.pessoas[0]))
    result=executar(tmp_path,fin,pdf,mode=modo);table=rows(tmp_path)
    assert len(table)==2+int(modo=='B')and table[0]==COLUNAS
    assert all(r[2]==CPF and r[3]==NOME_COMPOSTO for r in table[1:])
    assert all(r[11:15]==('11','912345678',None,'01234567')and r[21]=='titular@example.invalid'for r in table[1:])
    assert table[1][29]==100.1
    assert result['cadastro_'+PROFILE]['associacoes_retidas']==0
    assert result['cadastro_'+PROFILE]['lancamentos_individuais_com_conectivo_comprovados']==2
    assert result['politica_cadastral']==POLITICA=='beach_parque_titular_nominal_documento_valido_A1@1.1'
    if modo=='B':
        assert table[-1][24:]==(None,)*6
        decision=result['modo_b_cadastral_beach_parque']
        assert decision['politica']==POLITICA_B1=='beach_parque_linha_cadastral_individual_comprovada_B1@1.1'
        assert decision['politica_a1']==POLITICA and decision['decisoes'][0]['politica_a1']==POLITICA
        assert decision['decisoes'][0]['comprovada']
    for filename in ('auditoria.json','manifesto_diagnostico.json'):
        persisted=json.loads((tmp_path/filename).read_text(encoding='utf-8'))
        if modo=='B':assert persisted['modo_b_cadastral_beach_parque']==result['modo_b_cadastral_beach_parque']
    assert not result['autoriza_cobranca']and not result['permite_exportacao_operacional']


@pytest.mark.parametrize('nome',[
    'PESSOA FICTICIA / OUTRA INVENTADA', 'PESSOA FICTICIA ; OUTRA INVENTADA',
    'PESSOA E OUTRA', 'PESSOA FICTICIA E OUTRA INVENTADA',
    'PESSOA FICTICIA E OUTRA E INVENTADA',
])
def test_listas_dois_nomes_e_identidade_ambigua_continuam_retidos(tmp_path,nome):
    fin,body=fontes(nome=nome)
    r=executar(tmp_path,fin,cadastro([body]),mode='B');table=rows(tmp_path)
    assert len(table)==3 and table[1][29]==100.1
    assert all(not row[2]and not any(row[11:24])for row in table[1:])
    assert r['cadastro_'+PROFILE]['associacoes_retidas']==2
    assert r['modo_b_cadastral_beach_parque']['decisoes'][0]['estado']=='BPQ_B1_RESPONSAVEIS_MULTIPLOS'


@pytest.mark.parametrize('cenario',[
    'ausente','invalido','dois_documentos','tipo_juridica','sem_tipo','sem_ficha','ficha_corrompida',
    'outro_titular','documento_outro_papel','origem_incorreta','outro_cabecalho','dois_titulares',
])
def test_conectivo_nao_substitui_prova_estrutural(cenario):
    fin,body=fontes(documento=''if cenario=='ausente'else'00000000000'if cenario=='invalido'else CPF,
        segundo_documento='00000000272'if cenario=='dois_documentos'else None)
    if cenario in ('tipo_juridica','sem_tipo'):
        body=[(x,y,t.replace('Física','Jurídica'))for x,y,t in body if not(cenario=='sem_tipo'and t.startswith('Tipo de pessoa:'))]
    c=ler_cad(cadastro([body]));p=c.pessoas[0]
    note=next(n for n in c.ressalvas if n.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL')
    value=json.loads(note.valores_originais[0])
    if cenario=='sem_ficha':c=c.model_copy(update={'ressalvas':tuple(n for n in c.ressalvas if n!=note)})
    elif cenario=='ficha_corrompida':
        c=c.model_copy(update={'ressalvas':tuple(note.model_copy(update={'valores_originais':('invalida',)})if n==note else n for n in c.ressalvas)})
    elif cenario in ('outro_titular','documento_outro_papel','origem_incorreta','outro_cabecalho','dois_titulares'):
        owner=next(v for v in value['participantes']if v['papel']=='titular')
        if cenario=='outro_titular':owner['nome']='OUTRA PESSOA FICTICIA'
        if cenario=='documento_outro_papel':owner['papel']='pagador'
        if cenario=='origem_incorreta':owner['documentos'][0][1]['linha']+=1
        if cenario=='outro_cabecalho':value['cabecalhos'][0]['linha']+=1
        if cenario=='dois_titulares':value['participantes'].append(dict(owner))
        new_note=note.model_copy(update={'valores_originais':(json.dumps(value),)})
        c=c.model_copy(update={'ressalvas':tuple(new_note if n==note else n for n in c.ressalvas)})
    assert _titular_individual_comprovado(p,c)is None
    _,people,summary,_=associar(ler_fin(fin),c)
    assert all(not resolver_documento(p).valor and not p.contato.telefones and not p.contato.emails for p in people.values())
    assert summary['associacoes_retidas']==2


@pytest.mark.parametrize('contatos',[
    [],['Telefone - 0123-4567'],['E-mail - titular@example.invalid'],CONTATOS,
])
@pytest.mark.parametrize('nome',[NOME,NOME_COMPOSTO])
def test_cpf_independe_de_telefone_e_email(tmp_path,contatos,nome):
    fin,body=fontes(nome=nome,contatos=contatos)
    # A fixture base fornece contatos padrão quando recebe []; removê-los explicitamente.
    if not contatos:body=[(x,y,t)for x,y,t in body if not t.startswith(('Celular -','E-mail -'))]
    r=executar(tmp_path,fin,cadastro([body]),mode='B');table=rows(tmp_path)
    assert len(table)==3 and all(row[2]==CPF for row in table[1:])
    assert all(bool(any(row[11:21]))==any(t.startswith(('Celular','Telefone'))for t in contatos)for row in table[1:])
    assert all(bool(any(row[21:24]))==any(t.startswith('E-mail')for t in contatos)for row in table[1:])
    assert r['modo_b_cadastral_beach_parque']['decisoes'][0]['comprovada']


@pytest.mark.parametrize('papel',['pagador','locatario'])
def test_cpf_de_terceiro_proximo_ou_em_outra_pagina_nao_vira_titular(tmp_path,papel):
    fin,body=fontes(nome=NOME,documento='',**{papel:True})
    pdf=cadastro(dividir(body,2));c=ler_cad(pdf)
    assert not resolver_documento(c.pessoas[0]).valor
    ficha_original=json.loads(next(n.valores_originais[0]for n in c.ressalvas if n.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL'))
    participant=next(p for p in ficha_original['participantes']if p['papel']==papel)
    assert len(participant['documentos'])==1
    result=executar(tmp_path,fin,pdf,mode='B')
    assert all(not row[2]and not any(row[11:24])for row in rows(tmp_path)[1:])
    assert result['modo_b_cadastral_beach_parque']['decisoes'][0]['estado']=='BPQ_B1_DOCUMENTO_TITULAR_AUSENTE'


def test_continuacao_de_ficha_individual_preserva_papel_e_documento(tmp_path):
    fin,body=fontes()
    result=executar(tmp_path,fin,cadastro(dividir(body,3)),mode='B')
    assert all(row[2]==CPF for row in rows(tmp_path)[1:])
    assert result['modo_b_cadastral_beach_parque']['decisoes'][0]['comprovada']


@pytest.mark.parametrize('anotacao',[
    'incluído em 10/01/2025','incluída em 10/01/2025.','Incluido em 10/01/2025',
    'incluído em 31/02/2025','incluído em 10/01/2025 - telefone do filho',
    'anotação desconhecida','verificar titular','excluído em 10/01/2025',
])
def test_inclusao_datada_apenas_no_titular_individual_comprovado(tmp_path,anotacao):
    fin,body=fontes(contatos=['Celular - (11) 91234-5678','E-mail - titular@example.invalid'])
    # Segunda coluna real: rótulo, número e anotação cruzam a divisão x=392.
    y=next(y for x,y,t in body if t.startswith('Celular -'))
    body.extend([(305,y,'Celular - (12) 99876-5432 -'),(398,y,anotacao)])
    pdf=cadastro([body]);c=ler_cad(pdf)
    # A gramática geral BPQ-02 continua sem promover uma anotação desconhecida.
    assert len(c.pessoas[0].contato.telefones)==1
    result=executar(tmp_path,fin,pdf,mode='B');table=rows(tmp_path)
    aprovado=anotacao in ('incluído em 10/01/2025','incluída em 10/01/2025.','Incluido em 10/01/2025')
    assert all(row[2]==CPF and row[11:13]==('11','912345678')for row in table[1:])
    assert all(row[13:15]==(('12','998765432')if aprovado else(None,None))for row in table[1:])
    assert result['modo_b_cadastral_beach_parque']['decisoes'][0]['comprovada']


@pytest.mark.parametrize('nome',[NOME,'PESSOA E OUTRA','EMPRESA FICTICIA ALFA E BETA LTDA'])
def test_inclusao_desconhecida_nao_e_recuperada_globalmente(tmp_path,nome):
    document='00000000000191'if nome.startswith('EMPRESA')else CPF
    fin,body=fontes(nome=nome,documento=document,contatos=['Celular - (11) 91234-5678 - incluído em 10/01/2025'])
    r=executar(tmp_path,fin,cadastro([body]),mode='B')
    assert all(not any(row[11:21])for row in rows(tmp_path)[1:])
    if nome.startswith('EMPRESA'):assert all(row[2]==document for row in rows(tmp_path)[1:])


def test_divergencia_nominal_nao_e_resolvida_por_cpf_disponivel(tmp_path):
    fin,body=fontes(nome_cad='OUTRA FICTICIA E INVENTADA')
    r=executar(tmp_path,fin,cadastro([body]),mode='B')
    assert all(not row[2]and not any(row[11:24])for row in rows(tmp_path)[1:])
    assert r['modo_b_cadastral_beach_parque']['decisoes'][0]['estado']=='BPQ_B1_NOME_DIVERGENTE'


@pytest.mark.parametrize('falha',['outro_titular_documental','duas_fichas','dois_titulares_com_cpfs_distintos','cpf_rotulado_pagador'])
def test_prova_nao_aceita_duplicidade_ou_transferencia_de_participante(falha):
    _,body=fontes();c=ler_cad(cadastro([body]));p=c.pessoas[0]
    note=next(n for n in c.ressalvas if n.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL')
    if falha=='outro_titular_documental':
        p=p.model_copy(update={'evidencias_documentais':tuple(e.model_copy(update={'titular_id':'outro_ficticio'})for e in p.evidencias_documentais)})
    elif falha=='duas_fichas':c=c.model_copy(update={'ressalvas':c.ressalvas+(note,)})
    else:
        value=json.loads(note.valores_originais[0])
        if falha=='dois_titulares_com_cpfs_distintos':
            owner=next(v for v in value['participantes']if v['papel']=='titular')
            other=json.loads(json.dumps(owner));other['nome']='OUTRO TITULAR FICTICIO'
            other['documentos'][0][0]['valor']='00000000272';value['participantes'].append(other)
        else:
            for field in value['campos']:
                if field['secao']=='dados pessoais'and field['valor_original'].startswith('CPF:'):field['papel']='pagador'
        replacement=note.model_copy(update={'valores_originais':(json.dumps(value),)})
        c=c.model_copy(update={'ressalvas':tuple(replacement if n==note else n for n in c.ressalvas)})
    assert _titular_individual_comprovado(p,c)is None


def test_cpf_na_mesma_linha_geometrica_do_pagador_nao_atribui_titular(tmp_path):
    fin,body=fontes(nome=NOME,documento='',contatos=[])
    body=[(x,y,'CPF: 00000000272')if x==398 and t=='CPF: 'else(x,y,t)for x,y,t in body]
    body=[(x,y,t)for x,y,t in body if not t.startswith(('Celular -','E-mail -'))]
    pdf=cadastro([body]);c=ler_cad(pdf)
    original=json.loads(next(n.valores_originais[0]for n in c.ressalvas if n.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL'))
    cpf=next(v for v in original['campos']if v['valor_original']=='CPF: 00000000272')
    assert cpf['papel']=='pagador'and cpf['secao']=='dados gerais'and cpf['x_inicio']==392
    assert not resolver_documento(c.pessoas[0]).valor
    r=executar(tmp_path,fin,pdf,mode='B')
    assert r['resumo']['dividas_efetivamente_geradas']==1 and r['resumo']['cadastros_adicionais']==1
    assert all(not row[2]and not any(row[11:24])for row in rows(tmp_path)[1:])


@pytest.mark.parametrize('campos,aprovado',[
    (['Nome: PESSOA FICTICIA','Nome: OUTRA'],False),
    (['Nome: OUTRA PESSOA FICTICIA'],False),
    (['Responsáveis: PESSOA FICTICIA E OUTRA'],False),
    (['Titulares: PESSOA FICTICIA E OUTRA'],False),
    (['Nome completo: OUTRA PESSOA FICTICIA'],False),
    (['Identificação adicional: OUTRA PESSOA FICTICIA'],False),
    (['Nome: PESSOA FICTICIA E OUTRA'],True),
])
def test_nomes_explicitos_na_ficha_prevalecem_sobre_cabecalho_e_cpf(tmp_path,campos,aprovado):
    # Mesmo cabeçalho financeiro/cadastral, CPF válido e Tipo de pessoa: Física.
    # A prova de dois responsáveis nos campos originais nunca pode ser descartada.
    nome='PESSOA FICTICIA E OUTRA'
    fin,body=fontes(nome=nome)
    y=next(y for x,y,t in body if t.startswith('Tipo de pessoa:'))
    body.extend((24,y-i-1,texto)for i,texto in enumerate(campos))
    pdf=cadastro([body]);c=ler_cad(pdf)
    original=json.loads(next(n.valores_originais[0]for n in c.ressalvas if n.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL'))
    assert all(any(c['valor_original']==texto and c['papel']=='titular'and c['secao']=='dados pessoais'
        for c in original['campos'])for texto in campos)
    result=executar(tmp_path,fin,pdf,mode='B');table=rows(tmp_path)
    assert len(table)==3 and table[1][29]==100.1 and table[0]==COLUNAS
    assert all(bool(row[2])==aprovado for row in table[1:])
    assert result['modo_b_cadastral_beach_parque']['decisoes'][0]['comprovada']==aprovado
    if not aprovado:
        assert all(not any(row[11:24])for row in table[1:])
        assert result['modo_b_cadastral_beach_parque']['decisoes'][0]['estado']=='BPQ_B1_RESPONSAVEIS_MULTIPLOS'
