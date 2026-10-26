"""Nomes/boletos/posições sintéticos; classificação administrativa sem regra financeira."""
import json
from types import SimpleNamespace

from openpyxl import load_workbook
import pytest

from conversor.web.service import reconhecer,ler,analisar,PedidoDiagnostico
from conversor.web.demo import documentos_demo
from conversor.readers.fl_real import UNIDADE,nome_do_cabecalho
from conversor.readers.text_support import LinhaFonte
from tests.web.test_consolidated_corrections import financeiro

SPECS={'A':[('990001','10/09/26','09/2026')],'B':[('990002','10/09/26','09/2026')]}


def leitura(blob):
    p,c,l=reconhecer(blob)
    return ler(blob,p,c,l,'inadimplencia')[0]


@pytest.mark.parametrize('codigo',['Jurídico','JURÍDICO','juridico'])
@pytest.mark.parametrize('nome',['TITULAR SINTETICO','TITULAR SINTETICO / OUTRO CONTATO','ESCRITORIO JURÍDICO SINTETICO LTDA','EMPRESA JURÍDICO'])
def test_marcador_em_coluna_administrativa_separado_do_nome(codigo,nome):
    blob=financeiro(SPECS,nome=nome,marcador=codigo,separado=True,descricao='SERVICO JURÍDICO DESCRITIVO')
    antes=leitura(financeiro(SPECS,nome=nome,descricao='SERVICO JURÍDICO DESCRITIVO'))
    depois=leitura(blob)
    assert depois.pessoas[0].nome==nome
    ficha=lambda bs:[b.model_dump(exclude={'origens':True,'composicao':{'itens':{'__all__':{'origem'}}}})for b in bs]
    assert ficha(depois.boletos)==ficha(antes.boletos)
    assert all('JURÍDICO'in b.composicao.itens[0].descricao_original for b in depois.boletos)
    rs=[r for r in depois.ressalvas if r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO']
    assert len(rs)==1 and rs[0].gravidade=='informativo'
    assert rs[0].valores_originais[1]==codigo
    geometria=json.loads(rs[0].valores_originais[2]);assert geometria['x']==471.12 and geometria['namespace']=='fragmentos_pdf'
    assert all(o.pagina==1 and o.sha256 for o in rs[0].origens)


@pytest.mark.parametrize('nome',['EMPRESA JURÍDICO','INSTITUTO JURÍDICO SINTETICO','CONTATO SINTETICO / ESCRITORIO JURÍDICO'])
def test_palavra_no_nome_inclusive_final_sem_geometria_administrativa_nao_e_removida(nome):
    lote=leitura(financeiro(SPECS,nome=nome))
    assert lote.pessoas[0].nome==nome
    assert not any(r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO'for r in lote.ressalvas)


def test_texto_incorporado_ao_fragmento_sem_prova_de_coluna_nao_sofre_substituicao():
    lote=leitura(financeiro(SPECS,marcador='Jurídico',separado=False))
    assert lote.pessoas[0].nome=='TITULAR SINTETICO Jurídico'
    assert not any(r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO'for r in lote.ressalvas)


@pytest.mark.parametrize('x,y',[(350,744),(650,744),(471.12,742)])
def test_fragmento_fora_da_coluna_ou_linha_nao_e_classificacao_do_titular(x,y,monkeypatch):
    import tests.web.test_consolidated_corrections as f
    original=f.pdf
    def posicoes(pages):
        return original([[(x,y,t)if t=='Jurídico'else(xx,yy,t)for xx,yy,t in page]for page in pages])
    monkeypatch.setattr(f,'pdf',posicoes)
    lote=leitura(financeiro(SPECS,marcador='Jurídico',separado=True))
    assert not any(r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO'for r in lote.ressalvas)


@pytest.mark.parametrize('incorporado_na_linha',[False,True])
def test_linha_fundida_ou_separada_so_remove_marcador_confirmado_por_fragmento(incorporado_na_linha):
    original='0001 TORRE A - TITULAR SINTETICO / OUTRO CONTATO'
    fonte=SimpleNamespace(fragmentos=[((LinhaFonte(1,1,original),31,744),(LinhaFonte(1,2,'Jurídico'),471.12,744))])
    unidade=UNIDADE.fullmatch(original+(' Jurídico'if incorporado_na_linha else''))
    nome,marcadores=nome_do_cabecalho(fonte,1,unidade)
    assert nome=='TITULAR SINTETICO / OUTRO CONTATO'and marcadores[0][0].texto=='Jurídico'


@pytest.mark.parametrize('modo,cad',[('A',False),('B',False),('A',True),('B',True)])
def test_extracao_ate_excel_sem_filtro_juridico_e_com_cadastro_opcional(tmp_path,modo,cad):
    blob=financeiro(SPECS,nome='TITULAR SINTETICO / OUTRO CONTATO',marcador='Jurídico',separado=True)
    extra={'cadastro':documentos_demo()['cadastro']}if cad else{}
    r=analisar(blob,PedidoDiagnostico(data_ref='2026-10-23',modo=modo),processamento_id='juridico_sintetico',destino=tmp_path,**extra)
    assert r['resumo']['dividas_efetivamente_geradas']==2 and r['resumo']['boletos_selecionados_pela_regua']==2
    assert not r['permite_exportacao_operacional']and not any(d['bloqueios']for d in r['decisoes'])
    assert any(o['codigo']=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO'and o['gravidade']=='informativo'for o in r['ocorrencias'])
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(wb['Dados'].values)[1:]
    assert not any(row[3].endswith('Jurídico')for row in rows)
    if not cad:assert rows[0][3]=='TITULAR SINTETICO / OUTRO CONTATO'
    assert wb['Dados'].max_column==30
    wb.close()
