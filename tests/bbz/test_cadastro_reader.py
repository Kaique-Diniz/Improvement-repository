from hashlib import sha256
import json
from io import BytesIO

import pytest

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.bbz_cadastro import FichaCadastroBBZ
from conversor.domain.canonical import documento_validado
from conversor.domain.documents import resolver_documento
from conversor.readers.bbz_cadastro import LeitorCadastroBBZ, identificar
from conversor.readers.operational import RegistroLeitores
from conversor.readers.contracts import FonteProtegida
from conversor.readers.text_support import ContextoLeitura,ErroLeitura
from tests.bbz.cadastro_fixtures import cadastro,ficha,dividir,CPF,CNPJ,NOME


def ler(raw):
    return LeitorCadastroBBZ().ler(raw,contexto=ContextoLeitura('cond_bbz_nova_york','adm_bbz',
        LeitorCadastroBBZ.formato_id,'cadastro','287',LeitorCadastroBBZ.formato_id+'@1'))


def test_rotulos_fragmentados_separados_do_dois_pontos_preservam_associacao():
    def fragmentar(i,rows):
        out=[]
        for x,y,t in rows:
            label=t.split(':',1)[0]
            if label in ('CNPJ','Unidade','Código do cliente'):
                valor=t.split(':',1)[1]
                delta={'CNPJ':24,'Unidade':36,'Código do cliente':68}[label]
                out.extend([(x,y,label),(x+delta,y,':'),(x+delta+5,y,valor)])
            else:out.append((x,y,t))
        return out
    lote=ler(cadastro(mutar=fragmentar))
    assert len(lote.unidades)==1 and resolver_documento(lote.pessoas[0]).valor==CPF


@pytest.mark.parametrize('paginas',[1,2,3])
def test_ficha_entre_paginas_nao_duplica_unidade_nem_contatos(paginas):
    raw=cadastro(dividir(ficha(),paginas));r=ler(raw)
    assert len(r.unidades)==len(r.pessoas)==1 and not r.boletos
    assert resolver_documento(r.pessoas[0]).valor==CPF
    assert len(r.pessoas[0].contato.telefones)==len(r.pessoas[0].contato.emails)==1
    meta=json.loads(r.ressalvas[-1].valores_originais[0]);assert meta['continuidades']==paginas-1
    assert ler(raw).model_dump_json()==r.model_dump_json()


def test_codigo_cliente_compartilhado_nao_e_identidade_de_unidade():
    r=ler(cadastro([ficha('000001'),ficha('000002')],total=2))
    assert len({u.id for u in r.unidades})==2


@pytest.mark.parametrize('bloco,unidade',[('00','000001'),('A','BOXE'),('A','0017'),('B','0017')])
def test_identidade_textual_e_id_compativeis_com_financeiro(bloco,unidade):
    from conversor.readers.bbz_xlsx import LeitorBBZXLSX
    from tests.bbz.conftest import planilha,unidade as u
    raw=cadastro([ficha(unidade,bloco)]);r=ler(raw)
    financeiro=LeitorBBZXLSX().ler(planilha([u(numero=unidade,bloco=bloco)]),contexto=ContextoLeitura(
        'cond_bbz_nova_york','adm_bbz',LeitorBBZXLSX.formato_id,'financeiro','287',LeitorBBZXLSX.formato_id+'@1'))
    assert r.unidades[0].id==financeiro.unidades[0].id
    assert r.unidades[0].unidade_original==unidade and r.unidades[0].bloco_original==bloco


@pytest.mark.parametrize('documento,esperado',[(CPF,CPF),(CNPJ,CNPJ),('00000000190',''),('00000000000190',''),('','')])
def test_documentos_textuais_opcionais_sem_cnpj_do_edificio(documento,esperado):
    r=ler(cadastro([ficha(documento=documento)]));p=r.pessoas[0]
    assert resolver_documento(p).valor==esperado
    assert not resolver_documento(p).bloqueante


def test_proprietario_locatario_pagador_separados_e_observacoes_nao_definem_pessoas():
    raw=cadastro([ficha(locatario=True,pagador=True,observacao='CPF: 00000000272; E-mail - nao_usar@example.invalid')]);r=ler(raw)
    assert resolver_documento(r.pessoas[0]).valor==CPF
    f=FichaCadastroBBZ.model_validate_json(next(x for x in r.ressalvas if x.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL').valores_originais[0])
    ps={p.papel:p for p in f.participantes}
    assert ps['titular'].nome==NOME and ps['locatario'].nome!=NOME and ps['pagador'].nome!=NOME
    assert documento_validado(ps['locatario'].documentos[0][0])=='00000000272'
    assert documento_validado(ps['pagador'].documentos[0][0])=='00000000272'
    assert r.pessoas[0].contato.emails==('titular@example.invalid',)
    assert all(t.numero!='900000002'for t in r.pessoas[0].contato.telefones)


def test_mesmo_documento_repetido_por_papel_nao_produz_falso_conflito():
    p=ler(cadastro([ficha()])).pessoas[0]
    assert len(p.evidencias_documentais)==1 and not resolver_documento(p).bloqueante


def test_ficha_inteira_duplicada_na_pagina_seguinte_nao_e_continuacao():
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_FICHA_REPETIDA'):
        ler(cadastro([ficha(),ficha()],total=1))


def test_rotulo_em_observacao_nao_muda_papel_ou_fornece_cpf():
    rows=ficha(documento='');final=min(y for x,y,t in rows)
    rows += [(24,final-12,'Dados pessoais'),(217,final-24,'CPF: '+CPF)]
    assert not resolver_documento(ler(cadastro([rows])).pessoas[0]).valor


def test_documento_muda_coluna_mas_permanece_na_secao_explicita():
    def mover(i,rows):return [(398 if x==217 and t.startswith('CPF:')else x,y,t)for x,y,t in rows]
    assert resolver_documento(ler(cadastro(mutar=mover)).pessoas[0]).valor==CPF


def test_locatario_no_fim_da_pagina_acima_do_rodape_nao_e_perdido():
    rows=ficha(locatario=True)
    i=next(i for i,r in enumerate(rows)if r[2]=='Unidade alugada')
    primeira=rows[:i]+[(rows[i][0],53.36,rows[i][2]),(rows[i+1][0],43.72,rows[i+1][2])]
    segunda=[r for r in rows if r[1]==727]+rows[i+2:]
    r=ler(cadastro([primeira,segunda]));f=FichaCadastroBBZ.model_validate_json(next(
        x for x in r.ressalvas if x.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL').valores_originais[0])
    p=next(p for p in f.participantes if p.papel=='locatario')
    assert p.nome=='LOCATARIO TOTALMENTE FICTICIO'and len(p.documentos)==1


def test_documentos_distintos_na_mesma_identidade_sao_preservados():
    p=ler(cadastro([ficha(segundo_documento='00000000272')])).pessoas[0]
    assert len(p.evidencias_documentais)==2 and resolver_documento(p).bloqueante


def test_telefones_sem_ddd_pareados_deduplicados_e_excedentes_auditados():
    contatos=['Celular - (11) 90000-0001','Celular - 90000-0001','Celular - (11) 90000-0001']
    contatos += [f'Telefone residencial - 2000-00{i:02d}'for i in range(6)]
    contatos += [f'E-mail - contato{i}@example.invalid'for i in range(4)]
    r=ler(cadastro([ficha(contatos=contatos)]));p=r.pessoas[0]
    assert len(p.contato.telefones)==5 and len(p.contato.emails)==3
    assert [(t.ddd,t.numero)for t in p.contato.telefones[:2]]==[('11','900000001'),('','900000001')]
    assert any(x.codigo=='CONTATOS_EXCEDENTES_PRESERVADOS'for x in r.ressalvas)
    f=FichaCadastroBBZ.model_validate_json(next(x for x in r.ressalvas if x.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL').valores_originais[0])
    titular=next(p for p in f.participantes if p.papel=='titular')
    assert len(titular.telefones)==9 and len(titular.emails)==4


def test_prefixo_telefonico_ambiguo_nao_e_convertido_em_ddd_inventado():
    for telefone in ('(011) 2000-0001','01120000001'):
        r=ler(cadastro([ficha(contatos=['Telefone residencial - '+telefone])]))
        assert not r.pessoas[0].contato.telefones
        assert any(x.codigo=='TELEFONE_NAO_SEGMENTADO'for x in r.ressalvas)


@pytest.mark.parametrize('email',['sem_arroba','nome@example..invalid','nome@-example.invalid','nome.@example.invalid'])
def test_email_malformado_nao_e_corrigido(email):
    r=ler(cadastro([ficha(contatos=['E-mail - '+email])]))
    assert not r.pessoas[0].contato.emails
    assert any(x.codigo=='EMAIL_NAO_SEGMENTADO'for x in r.ressalvas)


@pytest.mark.parametrize('mudanca,codigo',[
    (lambda i,rs:[r for r in rs if 'Total de Unidade'not in r[2]],'BBZ_CADASTRO_RESUMO_AUSENTE'),
    (lambda i,rs:[r for r in rs if 'Emitido em'not in r[2]],'BBZ_CADASTRO_PAGINACAO_INCOMPLETA'),
    (lambda i,rs:[(x,y,t.replace('Página 1 de 1','Página 1 de 2'))for x,y,t in rs],'BBZ_CADASTRO_PAGINACAO_INCOMPLETA'),
    (lambda i,rs:[(x,y,t.replace('Total de Unidade 1','Total de Unidade 2'))for x,y,t in rs],'BBZ_CADASTRO_CONTAGEM_UNIDADES_DIVERGENTE'),
    (lambda i,rs:[(x,y,t.replace('Relatório de Unidades - Completo','OUTRO FORMATO FICTICIO'))for x,y,t in rs],'FORMATO_DESCONHECIDO'),
])
def test_incompletude_e_formato_desconhecido_bloqueados(mudanca,codigo):
    with pytest.raises(ErroLeitura,match=codigo):ler(cadastro(mutar=mudanca))


def test_cabecalho_repetido_no_meio_da_pagina_e_repeticao_antiga_bloqueiam():
    rows=ficha();header=[(x,130,t)for x,y,t in rows if y==727]
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_UNIDADE_DUPLICADA'):ler(cadastro([rows+header]))
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_UNIDADE_DUPLICADA'):
        ler(cadastro([ficha('000001'),ficha('000002'),ficha('000001')],total=2))


def test_continuacao_sem_header_e_header_divergente_nao_misturam_contatos():
    pages=dividir(ficha(),2)
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_CONTINUACAO_SEM_CABECALHO'):
        ler(cadastro([pages[0],[r for r in pages[1]if r[1]!=727]]))
    pages[1]=[(x,y,t.replace(NOME,'OUTRO TITULAR FICTICIO'))for x,y,t in pages[1]]
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_CONTINUACAO_DIVERGENTE'):ler(cadastro(pages))


def test_nome_mesmo_numero_em_blocos_distintos_nao_funde_e_colisao_normalizada_retida():
    assert len(ler(cadastro([ficha(bloco='A'),ficha(bloco='B')],total=2)).unidades)==2
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_COLISAO_IDENTIDADE_NORMALIZADA'):
        ler(cadastro([ficha('001'),ficha('0001')],total=2))


def test_header_condominio_inconsistente_entre_paginas_bloqueia():
    def mutar(i,rs):return [(x,y,t.replace('000287','000999')if i==2 else t)for x,y,t in rs]
    with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_CONDOMINIO_DIVERGENTE'):
        ler(cadastro(dividir(ficha(),2),mutar=mutar))


def test_zero_codigo_origem_e_fiscal_sao_evidencias_distintas():
    info=identificar(cadastro());assert info['codigo']=='287'and info['codigos_originais']==('000287',)
    assert info['cnpj']!=CPF and info['unidades_resumo']==1


@pytest.mark.parametrize('protecao,permitido',[('permitida',True),('negada',False),('senha',False)])
def test_criptografia_sem_senha_so_com_permissao_explicitamente_extraivel(protecao,permitido):
    raw=cadastro(protecao=protecao)
    assert SondadorLocal().sondar(raw,arquivo_id='teste').bloqueios
    if permitido:assert len(ler(raw).unidades)==1
    else:
        with pytest.raises(ErroLeitura,match='BBZ_CADASTRO_EXTRACAO_NAO_AUTORIZADA'):ler(raw)


def test_adapter_operacional_confere_hash_e_origens_sem_expor_campos():
    raw=cadastro();fonte=FonteProtegida(arquivo_id='cadastro',sha256=sha256(raw).hexdigest())
    class Fontes:
        def ler(self,f):return raw
    class Contextos:
        def resolver(self,f,**kw):return ContextoLeitura('cond_bbz_nova_york','adm_bbz',LeitorCadastroBBZ.formato_id,'cadastro','287',LeitorCadastroBBZ.formato_id+'@1')
    r=RegistroLeitores(Fontes(),Contextos()).obter(LeitorCadastroBBZ.formato_id,'1').ler(fonte,formato_id=LeitorCadastroBBZ.formato_id,condominio_id='cond_bbz_nova_york')
    assert all(o.pagina and o.linha and o.sha256==fonte.sha256 for o in r.ressalvas[-1].origens)
