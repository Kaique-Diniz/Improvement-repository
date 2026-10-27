from datetime import datetime
from io import BytesIO

from openpyxl import load_workbook
import pytest
from pydantic import ValidationError

from conversor.export.historical_comparison import DivergenciaTemplate
from conversor.web.service import analisar,PedidoDiagnostico


def comparar(xlsx,tmp_path,mutar):
    raw=xlsx();base=tmp_path/'base';args=PedidoDiagnostico(data_ref='2026-10-26',modo='A')
    analisar(raw,args,processamento_id='sintetico',destino=base)
    w=load_workbook(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');mutar(w,w.active);out=BytesIO();w.save(out);w.close()
    after=tmp_path/'depois';r=analisar(raw,args,processamento_id='sintetico',destino=after,referencia=out.getvalue())
    assert(after/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(base/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    assert(after/'canonico.json').read_bytes()==(base/'canonico.json').read_bytes()
    assert r['resumo']['dividas_efetivamente_geradas']==1 and not r['autoriza_cobranca']
    return r['comparacao']['contrato_atual']


@pytest.mark.parametrize('categoria,mutar',[
    ('formato_resolvido',lambda w,s:setattr(s,'title','HISTORICO FICTICIO')),
    ('cadastral',lambda w,s:setattr(s['D2'],'value','OUTRO CONTATO INTEGRALMENTE FICTICIO')),
    ('identificador',lambda w,s:setattr(s['B2'],'value','CODIGO_DIFERENTE_FICTICIO')),
    ('financeira',lambda w,s:setattr(s['AD2'],'value',101)),
    ('sem_explicacao',lambda w,s:(setattr(s['AA2'],'value','SEM VINCULO FICTICIO'),setattr(s['AC2'],'value',datetime(2026,1,1)))),
])
def test_cinco_categorias_sem_mudar_saida_financeira(xlsx,tmp_path,categoria,mutar):
    result=comparar(xlsx,tmp_path,mutar)
    assert result['resumo_por_categoria'].get(categoria,0)>=1
    assert result['nenhum_dado_ou_decisao_alterado']and result['historico_nao_e_contrato_definitivo']


def test_cabecalho_espacos_rotulo_parcela_e_coluna_extra_sao_formato_resolvido(xlsx,tmp_path):
    def mutar(w,s):s['AA1']='NM_DIVIDA_CEDENTE ';s['AA2']='COTA 08/2026';s['AB2']=99;s['AE2']='NOTA APENAS FICTICIA'
    r=comparar(xlsx,tmp_path,mutar);codes={d['codigo']for d in r['divergencias']}
    assert {'CABECALHOS_ATUAIS_LITERAIS','ROTULO_ATUAL_NAO_INFERE_COMPETENCIA','PARCELAS_SEQUENCIAIS_POR_CONTRATO','ANOTACOES_FORA_DAS_30_COLUNAS'}<=codes
    assert all(d['categoria']=='formato_resolvido'for d in r['divergencias'])


def test_documento_numerico_historico_nao_e_copiado(xlsx,tmp_path):
    r=comparar(xlsx,tmp_path,lambda w,s:setattr(s['C2'],'value',11111111111))
    assert {'formato_resolvido','cadastral'}<=set(r['resumo_por_categoria'])


def test_cadastros_duplicados_nao_sao_reproduzidos(xlsx,tmp_path):
    def mutar(w,s):
        for _ in range(2):
            row=[None]*30;row[1]=s['B2'].value;row[6]=s['G2'].value;s.append(row)
    r=comparar(xlsx,tmp_path,mutar);codes={d['codigo']for d in r['divergencias']}
    assert 'CADASTRO_HISTORICO_DUPLICADO'in codes and'MODO_A_SOMENTE_FINANCEIRO'in codes


def test_divergencia_financeira_exige_revisao_sem_copiar_valor(xlsx,tmp_path):
    r=comparar(xlsx,tmp_path,lambda w,s:setattr(s['AD2'],'value',999))
    d=next(d for d in r['divergencias']if d['categoria']=='financeira')
    assert d['revisao_humana']and d['campos']==['VL_PARCELA']


def test_identificador_divergente_exige_revisao_sem_equivalencia_automatica(xlsx,tmp_path):
    r=comparar(xlsx,tmp_path,lambda w,s:setattr(s['B2'],'value','Bloc0-UniLOJA_FICTICIA'))
    assert any(d['categoria']=='identificador'and d['revisao_humana']for d in r['divergencias'])


def test_categoria_desconhecida_nao_e_aceita():
    with pytest.raises(ValidationError):DivergenciaTemplate(categoria='aprovado',codigo='INVALIDO',linha_excel=1)


def test_referencia_sem_assinatura_fica_sem_explicacao_sem_afetar_debito(xlsx,tmp_path):
    r=comparar(xlsx,tmp_path,lambda w,s:setattr(s['A1'],'value','CABECALHO INVALIDO'))
    assert r['resumo_por_categoria']=={'sem_explicacao':1}
