"""Regressões de papéis e continuidade: somente documentos fictícios."""
import json

import pytest
from openpyxl import load_workbook

from conversor.domain.documents import resolver_documento
from conversor.domain.canonical import Documento, documento_validado
from conversor.readers.oma_cadastro import LeitorCadastroOMA
from tests.oma.fixtures import NOME, CPF, cadastro, ficha, dividir, financeiro, recibo
from tests.oma.test_oma import contexto, executar


def ficha_sem_cpf_titular_com_pagador():
    body=ficha(bloco='01',numero='000001',nome=NOME,documento='',
        contatos=['Celular - 0123-4567','E-mail - titular@example.invalid'])
    # Só o campo da seção Dados gerais/Dados do pagador, à direita.
    # O CPF de Dados pessoais, na coluna intermediária, permanece vazio.
    return [(x,y,'CPF: '+CPF) if x==398 and text=='CPF: ' else (x,y,text)
            for x,y,text in body]


@pytest.mark.parametrize('continua',[False,True])
def test_pagador_valido_nao_substitui_cpf_ausente_do_titular(tmp_path,continua):
    body=ficha_sem_cpf_titular_com_pagador()
    pages=dividir(body,2) if continua else [body]
    raw=cadastro(pages)
    lote=LeitorCadastroOMA().ler(raw,contexto=contexto('cadastro'))
    assert len(lote.unidades)==len(lote.pessoas)==1
    assert resolver_documento(lote.pessoas[0]).valor==''
    ev=next(r for r in lote.ressalvas if r.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL')
    original=json.loads(ev.valores_originais[0])
    titular=next(p for p in original['participantes'] if p['papel']=='titular')
    pagador=next(p for p in original['participantes'] if p['papel']=='pagador')
    assert titular['documentos']==[]
    assert len(pagador['documentos'])==1
    doc,origin=pagador['documentos'][0]
    assert documento_validado(Documento(**doc))==CPF
    assert origin['pagina']==(2 if continua else 1)
    assert len(original['cabecalhos'])==(2 if continua else 1)
    assert any(c['secao']=='dados pessoais' and c['campo']=='CPF' and
               c['valor_original'].strip()=='CPF:' for c in original['campos'])
    fin=financeiro([('01','000001',NOME,[recibo('11111111',61),recibo('11111112',59)])])
    result=executar(tmp_path,fin,raw)
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['cadastro_parque_santa_monica']['associacoes_retidas']==2
    assert {r['motivo'] for r in result['revisao_cadastral_parque_santa_monica']}=={
        'OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA'}
    w=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    try:
        rows=list(w['Dados'].values)
        assert len(rows)==2 and len(rows[0])==30
        assert rows[1][2] is None and rows[1][12] is None and rows[1][21] is None
        assert rows[1][3]==NOME
    finally:w.close()


def test_documentos_adicionais_continuados_nao_se_perdem_nem_viram_novos_titulares():
    first=ficha(bloco='01',numero='000001',nome=NOME,documento=CPF)
    pages=dividir(first,2)
    # Segundo documento igualmente válido e divergente, ainda no papel titular.
    # Seção documental explícita na página de continuação, sem tomar
    # um documento de outro papel por simples posição ou ordem.
    pages[1] += [(240,725,'Dados pessoais'),(217,713,'CPF: 00000000272')]
    lote=LeitorCadastroOMA().ler(cadastro(pages),contexto=contexto('cadastro'))
    assert len(lote.unidades)==len(lote.pessoas)==1
    resolution=resolver_documento(lote.pessoas[0])
    assert resolution.bloqueante and 'DOCUMENTOS_CONFLITANTES' in resolution.codigos
    assert {documento_validado(e.documento) for e in resolution.evidencias}=={CPF,'00000000272'}
    assert {e.origem.pagina for e in resolution.evidencias}=={1,2}


def test_cpf_titular_na_segunda_pagina_e_preservado_sem_duplicar_registro():
    body=ficha(bloco='01',numero='000001',nome=NOME,documento=CPF)
    label_y=next(y for x,y,text in body if text=='Dados pessoais')
    header=[v for v in body if v[1]==727]
    pages=[header+[v for v in body if v[1]!=727 and v[1]>label_y],
           header+[v for v in body if v[1]<=label_y]]
    lote=LeitorCadastroOMA().ler(cadastro(pages),contexto=contexto('cadastro'))
    assert len(lote.unidades)==len(lote.pessoas)==1
    resolution=resolver_documento(lote.pessoas[0])
    assert not resolution.bloqueante and resolution.valor==CPF
    assert len(resolution.evidencias)==1 and resolution.evidencias[0].origem.pagina==2
    original=json.loads(next(r.valores_originais[0] for r in lote.ressalvas if r.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL'))
    assert len(original['cabecalhos'])==2
