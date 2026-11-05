"""Codificação explícita e isolada; todos os contatos e documentos são sintéticos."""
from io import BytesIO
import json

from openpyxl import load_workbook
from pydantic import ValidationError
import pytest

from conversor.domain.canonical import Unidade
from conversor.export.identifiers import PerfilIdentificadores, selecionar_perfil
from conversor.readers.text_support import ErroLeitura
from conversor.web import service
from conversor.web.demo import documentos_demo
from tests.web.test_consolidated_corrections import executar, financeiro, SPECS
from tests.web.test_unit_contacts import documentos


def perfil(**overrides):
    return PerfilIdentificadores.model_validate(dict(id='perfil_inventado',versao='1',
        uso='diagnostico_nao_operacional',administradora_id='adm_inventada',condominio_id='cond_inventado',
        nome_cedente='ADMINISTRADORA SINTETICA',produto='PRODUTO SINTETICO',largura_unidade=4,
        torres={'A':'8','Q':'02'},evidencia={'arquivo':'referencia_sintetica.xlsx','sha256':'a'*64,
            'aba':'Dados','celulas':{'torre_A':'G2'}})|overrides)


def unidade(bloco='A', numero='0007', condominio='cond_inventado',admin='adm_inventada'):
    return Unidade(id='unidade_inventada',condominio_id=condominio,administradora_id=admin,
        normalizador_versao='sintetico@1',bloco_original=bloco,
        unidade_original=numero,chave_normalizada=f'{bloco}/{int(numero)}' if numero.isascii()and numero.isdigit()else f'{bloco}/{numero}',
        origem={'arquivo_id':'pdf_sintetico','sha256':'b'*64,'leitor_versao':'sintetico@1','identificador':'linha_inventada'})


def test_mapa_explicito_nao_depende_da_ordem_alfabetica_e_preserva_identidade():
    p=perfil();u=unidade();antes=u.model_dump()
    assert p.codificar(u,administradora_id='adm_inventada')==('80007','UNI0007-BL8')
    assert p.codificar(unidade('Q'),administradora_id='adm_inventada')==('020007','UNI0007-BL02')
    assert u.model_dump()==antes


@pytest.mark.parametrize('overrides',[{'torres':{'A':'1','B':'1'}},{'torres':{}},
    {'torres':{' A':'1'}},{'torres':{'A':'um'}},{'torres':{'A':1}},
    {'largura_unidade':True},{'largura_unidade':0},{'uso':'producao'}])
def test_configuracao_ambigua_invalida_ou_operacional_rejeitada(overrides):
    with pytest.raises(ValidationError):perfil(**overrides)


@pytest.mark.parametrize('bloco,numero,codigo',[
    ('B','0007','TORRE_SEM_MAPEAMENTO_DOCUMENTAL'),
    ('A','ABC','UNIDADE_SEM_CODIFICACAO_DOCUMENTAL'),
    ('A','０００７','UNIDADE_SEM_CODIFICACAO_DOCUMENTAL'),
    ('A','10007','UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')])
def test_nao_inventa_codigos_sem_correspondencia(bloco,numero,codigo):
    with pytest.raises(ErroLeitura,match=codigo):perfil().codificar(unidade(bloco,numero),administradora_id='adm_inventada')


@pytest.mark.parametrize('admin,cond',[('outra_adm','cond_inventado'),('adm_inventada','outro_cond')])
def test_nao_aplica_perfil_entre_administradoras_ou_condominios(admin,cond):
    with pytest.raises(ErroLeitura,match='PERFIL_IDENTIFICADORES_DE_OUTRO_CONDOMINIO'):
        perfil().codificar(unidade(condominio=cond),administradora_id=admin)
    assert selecionar_perfil([perfil().model_dump()],administradora_id=admin,condominio_id=cond)is None


def test_configuracoes_repetidas_do_mesmo_condominio_nao_sao_escolhidas_automaticamente():
    with pytest.raises(ErroLeitura,match='PERFIL_IDENTIFICADORES_AMBIGUO'):
        selecionar_perfil([perfil().model_dump()]*2,administradora_id='adm_inventada',condominio_id='cond_inventado')


def test_administradora_da_unidade_e_conferida_mesmo_com_contexto_correto():
    with pytest.raises(ErroLeitura,match='PERFIL_IDENTIFICADORES_DE_OUTRO_CONDOMINIO'):
        perfil().codificar(unidade(admin='outra_adm'),administradora_id='adm_inventada')


@pytest.mark.parametrize('modo,cadastros',[('A',0),('B',1)])
def test_projecao_altera_somente_cinco_campos_e_preserva_financeiro_AB(tmp_path,monkeypatch,modo,cadastros):
    data=documentos_demo()
    def rodar(destino):
        return service.analisar(data['inadimplencia'],service.PedidoDiagnostico(data_ref='2026-10-21',modo=modo),
            processamento_id='projecao_sintetica',destino=destino,cadastro=data['cadastro'])
    configurado=rodar(tmp_path/'configurado')
    empty=tmp_path/'perfis_vazios.json';empty.write_text('[]')
    monkeypatch.setattr(service,'PERFIS_SAIDA_PATH',empty)
    anterior=rodar(tmp_path/'anterior')
    assert configurado['decisoes']==anterior['decisoes']
    assert configurado['resumo']==anterior['resumo']
    assert (tmp_path/'configurado'/'canonico.json').read_bytes()==(tmp_path/'anterior'/'canonico.json').read_bytes()
    assert configurado['configuracao_hash']==anterior['configuracao_hash']
    assert configurado['codificacao_template']['pendentes']==0
    assert anterior['codificacao_template']['pendentes']==2
    with_books=[]
    for folder in ('configurado','anterior'):
        b=load_workbook(tmp_path/folder/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');with_books.append(b)
    a,b=with_books
    try:
        assert a['Dados'].max_column==30
        for nova,velha in zip(a['Dados'].iter_rows(min_row=2),b['Dados'].iter_rows(min_row=2),strict=True):
            for i in range(30):
                if i not in (0,1,6,24,25):assert nova[i].value==velha[i].value
            assert nova[0].value=='FL'
            assert nova[1].value in ('10001','20002') and nova[1].data_type=='s'
            assert nova[6].value in ('UNI0001-BL1','UNI0002-BL2')
            if nova[24].value:
                assert nova[24].value==nova[1].value and nova[24].data_type=='s'
                assert nova[25].value=='PLAZA MAYOR'
        assert sum(all(c.value is None for c in row[24:30])for row in a['Dados'].iter_rows(min_row=2))==cadastros
    finally:
        for book in with_books:book.close()
    assert not configurado['permite_exportacao_operacional'] and not configurado['autoriza_cobranca']


def test_torre_nova_conserva_identidade_provisoria_sem_alterar_financeiro(tmp_path,monkeypatch):
    specs={'A':SPECS['A'],'B':SPECS['B']};data=financeiro(specs)
    cfg=json.loads(service.PERFIS_SAIDA_PATH.read_text(encoding='utf-8'));cfg[0]['torres']={'B':'2'}
    path=tmp_path/'mapa_parcial.json';path.write_text(json.dumps(cfg))
    monkeypatch.setattr(service,'PERFIS_SAIDA_PATH',path)
    r=executar(tmp_path/'saida',data,modo='A')
    a=next(v for v in r['codificacao_template']['unidades'].values()if v['bloco_original']=='A')
    assert a['cedente']=='A/1' and a['complemento']=='A/1'
    assert a['motivo']=='TORRE_SEM_MAPEAMENTO_DOCUMENTAL' and r['codificacao_template']['pendentes']==1
    assert r['resumo']['elegivel']==5 and not r['resumo'].get('revisao')


@pytest.mark.parametrize('formato',[None,'%d/%m/%Y','%Y-%m-%d'])
def test_comparacao_com_codigos_explicitos_nao_precisa_de_catalogo_historico(tmp_path,formato):
    demo=documentos_demo();wb=load_workbook(BytesIO(demo['referencia']))
    for row in wb['Dados'].iter_rows(min_row=2):
        key=row[1].value;bloco,num=key.split('/');code={'A':'1','B':'2'}[bloco]
        row[1].value=code+num;row[6].value=f'UNI{num}-BL{code}'
        if formato and row[28].value:
            row[28].value=row[28].value.strftime(formato)
    out=BytesIO();wb.save(out);wb.close()
    r=service.analisar(demo['inadimplencia'],service.PedidoDiagnostico(data_ref='2026-10-23',modo='B'),
        processamento_id='comparacao_sintetica',destino=tmp_path,cadastro=demo['cadastro'],referencia=out.getvalue())
    assert r['comparacao']['resumo']['valores_coincidentes']==2
    assert not r['comparacao']['resumo'].get('nao_avaliavel')
    assert not r['comparacao']['vinculo_tecnico_historico_utilizado']


def test_documentos_conflitantes_continuam_retidos_apos_codificacao(tmp_path):
    docs=documentos(docs=('00000000191','00000000272'))
    r=executar(tmp_path,docs['inadimplencia'],cadastro=docs['cadastro'],modo='B')
    assert all(d['situacao']=='revisao' and 'DOCUMENTOS_CONFLITANTES'in d['bloqueios']for d in r['decisoes']if d['bloco']=='A')
    bloqueadas={d['unidade_id']for d in r['decisoes']if d['bloco']=='A'}
    assert not any(l['unidade_id']in bloqueadas for l in r['linhas_teste'])
    assert all(l['valores']is None for l in r['previa_template']['linhas']if l['bloco']=='A')
    assert not r['permite_exportacao_operacional']
