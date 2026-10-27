from datetime import date
from decimal import Decimal
from hashlib import sha256
import json

import pytest

from conversor.readers.bbz_xlsx import LeitorBBZXLSX,identificar,moeda
from conversor.readers.text_support import ContextoLeitura,ErroLeitura
from conversor.readers.operational import RegistroLeitores
from conversor.readers.contracts import FonteProtegida
from tests.bbz.conftest import recibo,unidade


def contexto(codigo='287',admin='adm_bbz'):
    return ContextoLeitura('cond_sintetico','adm_bbz'if admin is None else admin,LeitorBBZXLSX.formato_id,'sintetico',codigo,LeitorBBZXLSX.formato_id+'@1')


def ler(blob,ctx=None):return LeitorBBZXLSX().ler(blob,contexto=ctx or contexto())


def test_multiplos_componentes_negativos_e_encargos_reconciliados_sem_mudar_original(xlsx):
    raw=xlsx([unidade(recibos=[recibo(componentes=[('COTA FICTICIA','120.00'),('DESCONTO FICTICIO','-20.00')],encargos=('2','1','3'))])])
    lote=ler(raw);b=lote.boletos[0]
    assert b.composicao.total_original==Decimal('100.00')and b.composicao.itens[1].valor==Decimal('-20.00')
    assert(b.multa,b.correcao,b.juros)==(Decimal('2'),Decimal('1'),Decimal('3'))
    proof=next(r for r in lote.ressalvas if r.codigo=='BBZ_RECIBO_RECONCILIADO')
    assert json.loads(proof.valores_originais[0])['totais']==['100.00','100.00','2.00','1.00','3.00','106.00']
    assert b.competencia is None and lote.pessoas[0].documento is None
    assert ler(raw).model_dump_json()==lote.model_dump_json()
    assert all(o.pagina is None and o.linha and o.sha256==sha256(raw).hexdigest()for o in b.origens)


@pytest.mark.parametrize('marcador',[None,'A','AJ','J','AE'])
def test_marcadores_exatos_em_namespace_proprio_sem_regra_financeira(xlsx,marcador):
    lote=ler(xlsx([unidade(recibos=[recibo(marcador=marcador)])]));b=lote.boletos[0]
    assert[b.codigo_original for b in b.apontamentos]==([marcador]if marcador else[])
    assert all(p.namespace_formato==LeitorBBZXLSX.formato_id for p in b.apontamentos)
    assert'/'in lote.pessoas[0].nome


def test_legendas_descricao_e_nome_nao_viram_apontamento(xlsx):
    r=recibo(componentes=[('LEGENDA A AJ J AE E TEXTO JURIDICO','100.00')])
    assert not ler(xlsx([unidade(recibos=[r])])).boletos[0].apontamentos


@pytest.mark.parametrize('valor',['0.00','0.01','-0.01'])
def test_valores_zero_centavos_e_negativos_preservados_no_leitor(xlsx,valor):
    b=ler(xlsx([unidade(recibos=[recibo(componentes=[('FICTICIO',valor)])])])).boletos[0]
    assert b.composicao.total_original==Decimal(valor)


def test_unidade_alfanumerica_e_datas_antigas_sem_inferencia_emissao(xlsx):
    r=recibo(due=date(2016,2,29),emissao=123456)
    lote=ler(xlsx([unidade(numero='SALA-X01',bloco='INAT',recibos=[r])]))
    assert lote.unidades[0].unidade_original=='SALA-X01'and lote.unidades[0].bloco_original=='INAT'
    assert lote.boletos[0].emissao is None and lote.boletos[0].emissao_original=='123456'
    assert any(r.codigo=='BBZ_EMISSAO_BRUTA_NAO_INTERPRETADA'for r in lote.ressalvas)


@pytest.mark.parametrize('id',['00099001','99000001'])
def test_identificador_original_preservado(xlsx,id):assert ler(xlsx([unidade(recibos=[recibo(id=id)])])).boletos[0].identificador==id


@pytest.mark.parametrize('valor',[True,False,None,float('inf'),float('nan'),'nao monetario','0.001',.1+.2])
def test_valor_invalido_ou_precisao_nao_sao_corrigidos(valor):
    with pytest.raises(ErroLeitura,match='BBZ_VALOR_MONETARIO_INVALIDO'):moeda(valor,7)


@pytest.mark.parametrize('admin',['adm_sintetica_1','adm_sintetica_2'])
def test_leitor_de_familia_nao_fixa_id_administradora(xlsx,admin):
    # Associação é responsabilidade do catálogo/reconhecedor, não do layout.
    lote=ler(xlsx(),contexto(admin=admin))
    assert lote.unidades[0].administradora_id==admin


def test_codigo_administrativo_nao_e_codigo_do_arquivo(xlsx):
    assert identificar(xlsx())[0]=='287'
    with pytest.raises(ErroLeitura,match='IDENTIDADE_BBZ_DIVERGENTE'):ler(xlsx(),contexto(codigo='884'))


@pytest.mark.parametrize('mutacao,codigo',[
    (lambda w,s:setattr(s['L7'],'value',101),'BBZ_TOTAL_COMPONENTE_DIVERGENTE'),
    (lambda w,s:setattr(s['G8'],'value',101),'BBZ_TOTAL_RECIBO_DIVERGENTE'),
    (lambda w,s:setattr(s['G9'],'value',101),'BBZ_TOTAL_UNIDADE_DIVERGENTE'),
    (lambda w,s:setattr(s['G10'],'value',101),'BBZ_TOTAL_CONDOMINIO_DIVERGENTE'),
    (lambda w,s:setattr(s['A10'],'value','Quantidade de unidade(s) em aberto: 2'),'BBZ_CONTAGEM_OU_FECHAMENTO_INVALIDO'),
    (lambda w,s:s.delete_rows(10),'FORMATO_DESCONHECIDO'),
    (lambda w,s:s.append(['TEXTO EXTRA FICTICIO']),'BBZ_CONTEUDO_APOS_FECHAMENTO'),
    (lambda w,s:setattr(s['B7'],'value','31/02/2026'),'BBZ_DATA_INVALIDA'),
    (lambda w,s:setattr(s['B7'],'value',None),'BBZ_CONTINUACAO_DE_RECIBO_AMBIGUA'),
    (lambda w,s:setattr(s['A7'],'value','AJX 99000001'),'BBZ_RECIBO_OU_MARCADOR_INVALIDO'),
    (lambda w,s:setattr(s['G7'],'value','=1+1'),'BBZ_FORMULA_SEM_VALIDACAO'),
    (lambda w,s:setattr(s['M7'],'value',1),'BBZ_COLUNAS_NAO_RECONHECIDAS'),
    (lambda w,s:setattr(s['H6'],'value','Principal diferente'),'FORMATO_DESCONHECIDO'),
    (lambda w,s:w.copy_worksheet(s),'FORMATO_AMBIGUO'),
])
def test_adulteracao_e_layout_incompleto_bloqueiam_com_localizador(xlsx,mutacao,codigo):
    with pytest.raises(ErroLeitura,match=codigo):ler(xlsx(mutar=mutacao))


def test_recibo_repetido_nao_e_fundido(xlsx):
    with pytest.raises(ErroLeitura,match='BBZ_RECIBO_DUPLICADO'):
        ler(xlsx([unidade(recibos=[recibo(),recibo()])]))


def test_unidade_repetida_nao_e_fundida(xlsx):
    with pytest.raises(ErroLeitura,match='BBZ_UNIDADE_DUPLICADA'):ler(xlsx([unidade(),unidade()]))


def test_continuacao_exige_mesmo_recibo_e_marcador(xlsx):
    def mutar(w,s):s['A8']='J 99000002'
    with pytest.raises(ErroLeitura,match='BBZ_CONTINUACAO_DE_RECIBO_AMBIGUA'):
        ler(xlsx([unidade(recibos=[recibo(componentes=[('COTA','50'),('FUNDO','50')])])],mutar=mutar))


def test_repositorio_operacional_confere_hash_e_proveniencia(xlsx):
    raw=xlsx();fonte=FonteProtegida(arquivo_id='sintetico',sha256=sha256(raw).hexdigest())
    class Fontes:
        def ler(self,f):return raw
    class Contextos:
        def resolver(self,f,**kw):return contexto()
    adapter=RegistroLeitores(Fontes(),Contextos()).obter(LeitorBBZXLSX.formato_id,'1')
    assert len(adapter.ler(fonte,formato_id=LeitorBBZXLSX.formato_id,condominio_id='cond_sintetico').boletos)==1
    with pytest.raises(ErroLeitura,match='HASH_FONTE_DIVERGENTE'):
        adapter.ler(fonte.model_copy(update={'sha256':'a'*64}),formato_id=LeitorBBZXLSX.formato_id,condominio_id='cond_sintetico')


def test_mesmo_numero_recibo_em_unidades_distintas_nao_mistura(xlsx):
    lote=ler(xlsx([unidade(),unidade(numero='000002')]))
    assert len(lote.boletos)==2 and len({b.id for b in lote.boletos})==2
    assert len({b.unidade_id for b in lote.boletos})==2


def test_data_de_emissao_comprovada_nao_vem_do_vencimento(xlsx):
    b=ler(xlsx([unidade(recibos=[recibo(emissao=date(2025,1,1),due=date(2026,1,1))])])).boletos[0]
    assert b.emissao==date(2025,1,1)and b.vencimento==date(2026,1,1)and b.competencia is None


def test_adaptador_xlsx_usa_contexto_de_catalogo_e_protocolo_existentes(xlsx):
    from conversor.domain.catalog import Catalogo
    from conversor.readers.contracts import Leitor
    from conversor.readers.operational import ContextosCatalogo
    from tests.phase3.conftest import catalogo_leitura
    dados=catalogo_leitura.__wrapped__().model_dump(mode='json')
    # Catálogo estritamente sintético; não gera plano/aprovação de produção.
    dados=json.loads(json.dumps(dados).replace('"adm"','"adm_bbz"'))
    dados['formatos'][0].update(tipo_arquivo='xlsx',leitor_id=LeitorBBZXLSX.formato_id)
    dados['condominios'][0]['codigo_na_administradora']='287'
    catalogo=Catalogo.model_validate(dados)
    raw=xlsx();fonte=FonteProtegida(arquivo_id='fixture_xlsx',sha256=sha256(raw).hexdigest())
    class Fontes:
        def ler(self,f):return raw
    registro=RegistroLeitores(Fontes(),ContextosCatalogo(catalogo,date(2026,10,26)))
    adapter=registro.obter(LeitorBBZXLSX.formato_id,'1');assert isinstance(adapter,Leitor)
    lote=adapter.ler(fonte,formato_id='fmt_habita',condominio_id='cond_habita')
    assert len(lote.boletos)==1 and lote.unidades[0].administradora_id=='adm_bbz'


def test_catalogo_impede_associacao_de_formato_a_administradora_nao_autorizada():
    from pydantic import ValidationError
    from conversor.domain.catalog import Catalogo
    from tests.phase3.conftest import catalogo_leitura
    dados=catalogo_leitura.__wrapped__().model_dump(mode='json')
    dados['administradoras'].append({'id':'adm_outro_sintetico','nome':'OUTRA ADMINISTRADORA FICTICIA'})
    dados['formatos'][0].update(tipo_arquivo='xlsx',leitor_id=LeitorBBZXLSX.formato_id)
    dados['condominios'][0]['administradora_id']='adm_outro_sintetico'
    dados['condominios'][0]['vinculos'][0]['administradora_id']='adm_outro_sintetico'
    with pytest.raises(ValidationError,match='FORMATO_INCOMPATIVEL_COM_ADMINISTRADORA'):Catalogo.model_validate(dados)
