"""Conversão isolada de BIFF8: planilhas e identidades integralmente fictícias."""
from datetime import datetime
from hashlib import sha256
from io import BytesIO

from openpyxl import load_workbook
import pytest
import xlwt

from conversor.adapters.historical_xls import converter_referencia_xls
from conversor.domain.template import COLUNAS
from conversor.readers.text_support import ErroLeitura
from conversor.web.service import reconhecer


def xls(*,datas_1904=False,header_y=False,formula=False,alterar=None):
    w=xlwt.Workbook();w.set_dates_1904(datas_1904);s=w.add_sheet('Historico ficticio')
    for j,v in enumerate(COLUNAS):s.write(0,j,COLUNAS[26]+' ' if header_y and j==24 else v)
    s.write(1,0,'BBZ');s.write(1,1,'BL0-UNI0001-696');s.write(1,2,191,xlwt.easyxf(num_format_str='00000000000'))
    s.write(1,3,'TITULAR INTEGRALMENTE FICTICIO');s.write(1,6,'BL0-UNI0001')
    s.write(1,7,123,xlwt.easyxf(num_format_str='00000000'))
    s.write(1,12,'900000001');s.write(1,24,'BL0-UNI0001-696');s.write(1,25,'CONDOMINIO FICTICIO')
    s.write(1,26,'=TEXTO LITERAL');s.write(1,27,1)
    s.write(1,28,datetime(2031,8,26),xlwt.easyxf(num_format_str='DD/MM/YYYY'))
    s.write(1,29,xlwt.Formula('1+2') if formula else 123.45,xlwt.easyxf(num_format_str='0.00'))
    if alterar:alterar(w,s)
    buf=BytesIO();w.save(buf);return buf.getvalue()


@pytest.mark.parametrize('datas_1904',[False,True])
def test_conversao_preserva_datas_valores_zeros_e_texto_literal(datas_1904):
    raw=xls(datas_1904=datas_1904);original=sha256(raw).hexdigest()
    data,meta=converter_referencia_xls(raw)
    w=load_workbook(BytesIO(data));s=w.active
    assert tuple(c.value for c in s[1])==COLUNAS and s.max_column==30
    assert s['C2'].value=='00000000191' and s['H2'].value=='00000123'
    assert s['AA2'].value=='=TEXTO LITERAL' and s['AA2'].data_type=='s'
    assert s['AC2'].value==datetime(2031,8,26) and s['AD2'].value==123.45
    assert s['L2'].value is None and s['M2'].value=='900000001'
    assert meta['datemode']==int(datas_1904) and meta['sha256_original']==original
    assert not meta['original_modificado'] and not meta['formulas_macros_links_executados']
    assert sha256(raw).hexdigest()==original and meta['sha256_convertido']==sha256(data).hexdigest()
    assert next(e for e in meta['celulas_conferidas']if e['linha']==2 and e['coluna']==3)['valor_original']==191
    w.close()


def test_cabecalho_y_duplicado_exige_revisao_explicita_auditavel():
    raw=xls(header_y=True)
    with pytest.raises(ErroLeitura,match='CABECALHO_Y_EXIGE_REVISAO'):converter_referencia_xls(raw)
    data,meta=converter_referencia_xls(raw,revisar_cabecalho_y=True)
    assert meta['cabecalho_y_revisado_explicitamente']
    assert meta['cabecalhos_originais'][24]==COLUNAS[26]+' '
    w=load_workbook(BytesIO(data));assert w.active['Y1'].value=='NM_CONTRATO_CEDENTE';w.close()


def test_formula_nao_e_executada_nem_resultado_em_cache_e_aceito():
    with pytest.raises(ErroLeitura,match='FORMULA_OU_PROTECAO'):converter_referencia_xls(xls(formula=True))


@pytest.mark.parametrize('raw',[b'',b'%PDF-1.4',b'PK'+b'0'*20,b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'+b'0'*100])
def test_assinatura_e_estrutura_invalidas_sem_vazamento(raw):
    with pytest.raises(ErroLeitura):converter_referencia_xls(raw)


def test_planilhas_multiplas_sao_ambiguas():
    with pytest.raises(ErroLeitura,match='AMBIGUA_OU_NAO_SUPORTADA'):
        converter_referencia_xls(xls(alterar=lambda w,s:w.add_sheet('Outra ficha ficticia')))


def test_xls_historico_nao_e_aceito_como_relatorio_financeiro():
    with pytest.raises(ErroLeitura):reconhecer(xls())


def test_determinismo_e_manifesto_de_conversao():
    a,ma=converter_referencia_xls(xls());b,mb=converter_referencia_xls(xls())
    assert a==b and ma==mb


def test_numero_sem_formato_nao_ganha_zeros_inventados():
    raw=xls(alterar=lambda w,s:s.write(2,2,191))
    data,meta=converter_referencia_xls(raw)
    w=load_workbook(BytesIO(data));assert w.active['C3'].value==191;w.close()
    assert {'linha':3,'coluna':3,'codigo':'CAMPO_TEXTUAL_HISTORICO_NUMERICO_SEM_ZEROS_COMPROVADOS'} in meta['limitacoes']


def test_celulas_fora_do_template_sao_rejeitadas():
    with pytest.raises(ErroLeitura,match='FORA_DO_TEMPLATE'):
        converter_referencia_xls(xls(alterar=lambda w,s:s.write(2,30,'ANOTACAO FICTICIA')))


def test_coluna_apenas_formatada_exige_vazio_comprovado_em_todas_as_linhas():
    def formatar(w,s):s.write(3,30,None,xlwt.easyxf(num_format_str='0.00'))
    raw=xls(alterar=formatar);data,a=converter_referencia_xls(raw)
    w=load_workbook(BytesIO(data));assert w.active.max_column==30;w.close()
    assert a['versao']=='conversao_referencia_biff8@1.1' and a['colunas_originais']==31
    assert len(a['colunas_extras_integralmente_vazias'])==4
    assert all(e['valor_original']=='' for e in a['colunas_extras_integralmente_vazias'])
    assert a['sha256_original']==sha256(raw).hexdigest()


@pytest.mark.parametrize('valor',[0,' ',False])
def test_extra_com_dado_nunca_e_confundido_com_coluna_vazia(valor):
    with pytest.raises(ErroLeitura,match='FORA_DO_TEMPLATE'):
        converter_referencia_xls(xls(alterar=lambda w,s:s.write(2,30,valor)))
