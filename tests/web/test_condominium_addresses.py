"""Cadastro autenticado e persistente; endereços 100% fictícios."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.adapters.condominium_addresses import RepositorioEnderecos
from conversor.domain.canonical import Endereco
from conversor.readers.text_support import ErroLeitura
from conversor.web.app import criar_app
from conversor.web import service
from tests.web.test_mvp import KEY,aguardar
from tests.web.test_tree_group_veto import boleto,pdf_unidades
from tests.web.test_tree_template import endereco as endereco_legacy

TREE='/api/condominios/adm_habita/cond_habita/endereco'
PLAZA='/api/condominios/adm_fl/cond_fl/endereco'
ENDERECO={'logradouro':'Rua do Teste Ficticio','numero':'007','cep':'00000001',
    'bairro':'Bairro Inventado','cidade':'Cidade Ficticia','uf':'SP'}


def cliente(root):
    return TestClient(criar_app(root,acesso=KEY))


def login(c):assert c.post('/api/session',json={'chave':KEY}).status_code==200


def salvar(c,url=TREE,versao=0,endereco=None):
    return c.put(url,json={'endereco':endereco or ENDERECO,'versao_esperada':versao})


def processar_tree(c):
    pdf=pdf_unidades([('1','000001',[boleto('99000001')])])
    return aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-23','modo':'A'},files={'inadimplencia':('SINTETICO.pdf',pdf)}))


def test_consulta_e_gravacao_exigem_autenticacao_e_origem_correta(tmp_path):
    root=tmp_path/'privado'
    with cliente(root)as c:
        assert c.get(TREE).status_code==401 and salvar(c).status_code==401
        login(c)
        assert c.put(TREE,headers={'Origin':'https://example.invalid'},json={'endereco':ENDERECO,'versao_esperada':0}).status_code==403
        assert not(root/'enderecos_condominios.json').exists()
        assert c.get(TREE).json()['origem']=='nao_cadastrado'


def test_persistencia_apos_reabrir_servidor_com_outra_sessao(tmp_path):
    root=tmp_path/'privado'
    with cliente(root)as c:
        login(c);r=salvar(c);assert r.status_code==200
        data=r.json();assert data['endereco']['cep']=='00000001'and data['versao']==1
        assert data['origem']=='configuracao_fornecida_pelo_usuario'and data['atualizado_em']
    raw=(root/'enderecos_condominios.json').read_bytes()
    with cliente(root)as outro:
        assert outro.get(TREE).status_code==401
        login(outro);assert outro.get(TREE).json()==data
        assert(root/'enderecos_condominios.json').read_bytes()==raw
        job=processar_tree(outro);assert job['estado']=='concluido'
        r=job['resultado'];config=r['endereco_condominio']['configuracao']
        assert config['evidencia']['tipo']=='configuracao_fornecida_pelo_usuario'
        assert config['evidencia']['versao']==1 and len(config['evidencia']['sessao_sha256'])==64
        assert 'arquivo'not in config['evidencia'] # não fabrica documento externo
        wb=load_workbook(BytesIO(outro.get('/api/processamentos/'+job['id']+'/arquivo-teste.xlsx').content))
        assert wb['Dados']['E2'].value==ENDERECO['logradouro']and wb['Dados']['G2'].value=='BL01-UNI0001'
        assert wb['Dados']['H2'].value=='00000001';wb.close()
        assert not r['permite_exportacao_operacional']
        assert(root/'enderecos_condominios.json').read_bytes()==raw # analisar não cadastra de novo


def test_versoes_preservam_historico_e_concorrencia_rejeita_edicao_antiga(tmp_path):
    root=tmp_path/'privado'
    with cliente(root)as c:
        login(c);assert salvar(c).status_code==200
        antes=json.loads((root/'enderecos_condominios.json').read_text())['registros'][0]
        assert salvar(c,versao=0,endereco=ENDERECO|{'numero':'008'}).status_code==409
        assert salvar(c,versao=1,endereco=ENDERECO|{'numero':'009'}).json()['versao']==2
        hist=json.loads((root/'enderecos_condominios.json').read_text())['registros']
        assert hist[0]==antes and len(hist)==2
        assert hist[1]['padrao']['endereco']['numero']=='009'


@pytest.mark.parametrize('url',['/api/condominios/adm_fl/cond_habita/endereco',
    '/api/condominios/adm_habita/cond_fl/endereco','/api/condominios/adm_inventada/cond_inventado/endereco'])
def test_ids_cruzados_ou_desconhecidos_nao_sao_aceitos(tmp_path,url):
    with cliente(tmp_path/'privado')as c:
        login(c);assert c.get(url).status_code==404 and salvar(c,url).status_code==404


def test_isolamento_entre_condominios_e_campos_atuais_do_plaza(tmp_path):
    with cliente(tmp_path/'privado')as c:
        login(c);assert salvar(c).status_code==200
        assert not c.get(PLAZA).json()['cadastrado']
        job=aguardar(c,c.post('/api/exemplo',data={'data_ref':'2026-10-23','modo':'B'}))
        assert job['estado']=='concluido'and job['resultado']['resumo']['dividas_efetivamente_geradas']==3
        assert not job['resultado']['endereco_condominio']['cadastrado']
        assert salvar(c,PLAZA,endereco=ENDERECO|{'logradouro':'Outra Rua Ficticia'}).status_code==200
        assert c.get(TREE).json()['endereco']['logradouro']==ENDERECO['logradouro']
        assert c.get(PLAZA).json()['endereco']['logradouro']=='Outra Rua Ficticia'


def test_ausencia_endereco_nao_impede_diagnostico(tmp_path):
    with cliente(tmp_path/'privado')as c:
        login(c);job=processar_tree(c)
        assert job['estado']=='concluido'and job['resultado']['arquivo_teste_disponivel']
        assert not job['resultado']['endereco_condominio']['cadastrado']


def test_perfil_legado_exibido_e_preservado_sem_migracao_silenciosa(tmp_path):
    root=tmp_path/'privado';root.mkdir()
    perfis=json.loads(service.PERFIS_SAIDA_PATH.read_bytes());perfis[1]['endereco_padrao']=endereco_legacy()
    private=root/'perfis_saida.json';private.write_text(json.dumps(perfis));original=private.read_bytes()
    with cliente(root)as c:
        login(c);old=c.get(TREE).json()
        assert old['cadastrado']and old['origem']=='perfil_privado_existente'and old['versao']==0
        assert not(root/'enderecos_condominios.json').exists()
        assert salvar(c).status_code==200 and c.get(TREE).json()['origem']=='configuracao_fornecida_pelo_usuario'
        assert private.read_bytes()==original
        job=processar_tree(c)
        assert job['resultado']['endereco_condominio']['origem']=='cadastro_usuario'


@pytest.mark.parametrize('endereco,versao',[
    (ENDERECO|{'logradouro':''},0),(ENDERECO|{'logradouro':'   '},0),
    (ENDERECO|{'cep':'123'},0),(ENDERECO|{'complemento':'APTO SINTETICO'},0),
    (ENDERECO,True),(ENDERECO,-1),
])
def test_dados_invalidos_nao_sao_persistidos(tmp_path,endereco,versao):
    root=tmp_path/'privado'
    with cliente(root)as c:
        login(c);assert salvar(c,versao=versao,endereco=endereco).status_code==422
        assert not(root/'enderecos_condominios.json').exists()


def test_json_corrompido_nao_e_sobrescrito(tmp_path):
    root=tmp_path/'privado'
    with cliente(root)as c:
        login(c);p=root/'enderecos_condominios.json';p.write_text('{invalido')
        assert c.get(TREE).status_code==409 and salvar(c).status_code==409
        assert p.read_text()=='{invalido'


def test_gravacao_atomica_preserva_arquivo_quando_falha(tmp_path,monkeypatch):
    import conversor.adapters.condominium_addresses as storage
    root=tmp_path/'privado'
    with cliente(root)as c:
        login(c);assert salvar(c).status_code==200
        raw=(root/'enderecos_condominios.json').read_bytes()
        def falha(*args):raise OSError('FALHA_SINTETICA')
        monkeypatch.setattr(storage,'escrever_json',falha)
        assert salvar(c,versao=1).status_code==409
        assert(root/'enderecos_condominios.json').read_bytes()==raw


def test_duas_gravacoes_simultaneas_nao_perdem_atualizacao(tmp_path):
    root=tmp_path/'privado';root.mkdir();r=RepositorioEnderecos(root)
    def gravar(numero):
        try:
            p=r.salvar('adm_habita','cond_habita',Endereco(**(ENDERECO|{'numero':numero})),versao_esperada=0,sessao_sha256='a'*64)
            return p.evidencia.versao
        except ErroLeitura as e:return e.codigo
    with ThreadPoolExecutor(max_workers=2)as pool:resultados=list(pool.map(gravar,['1','2']))
    assert sorted(map(str,resultados))==['1','ENDERECO_ALTERADO_POR_OUTRA_SESSAO']
    assert len(json.loads((root/'enderecos_condominios.json').read_text())['registros'])==1


def test_endereco_divergente_de_fonte_atual_continua_preservado(tmp_path,monkeypatch):
    real=service.ler
    def com_endereco(*args,**kwargs):
        l,ctx=real(*args,**kwargs);p=l.pessoas[0]
        p=p.model_copy(update={'contato':p.contato.model_copy(update={'endereco':Endereco(logradouro='Rua Atual Ficticia')})})
        return l.model_copy(update={'pessoas':(p,)+l.pessoas[1:]}),ctx
    monkeypatch.setattr(service,'ler',com_endereco)
    with cliente(tmp_path/'privado')as c:
        login(c);salvar(c);job=processar_tree(c)
        e=next(iter(job['resultado']['enderecos_template'].values()))
        assert e['estado']=='endereco_atual_preservado'and 'ENDERECO_DIVERGENTE_PRESERVADO'in e['alertas']
        assert e['endereco_origem']['logradouro']=='Rua Atual Ficticia'
        wb=load_workbook(BytesIO(c.get('/api/processamentos/'+job['id']+'/arquivo-teste.xlsx').content))
        assert wb['Dados']['E2'].value=='Rua Atual Ficticia'and wb['Dados']['F2'].value is None;wb.close()


def test_cadastro_sobrevive_a_git_pull_em_copia_temporaria_e_reinicio(tmp_path):
    # Somente repositórios descartáveis, sem push nem acesso ao GitHub do projeto.
    origem=tmp_path/'origem_git';origem.mkdir();codigo=tmp_path/'codigo';root=tmp_path/'privado'
    def git(*args,cwd=origem):
        subprocess.run(['git',*args],cwd=cwd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    git('init','-b','main');(origem/'versao.txt').write_text('1')
    git('add','versao.txt');git('-c','user.name=Teste','-c','user.email=teste@example.invalid','commit','-m','Versao sintetica 1')
    git('clone',str(origem),str(codigo),cwd=tmp_path)
    with cliente(root)as c:login(c);assert salvar(c).status_code==200
    original=(root/'enderecos_condominios.json').read_bytes()
    (origem/'versao.txt').write_text('2');git('add','versao.txt')
    git('-c','user.name=Teste','-c','user.email=teste@example.invalid','commit','-m','Versao sintetica 2')
    git('pull','--ff-only',cwd=codigo)
    assert(codigo/'versao.txt').read_text()=='2'
    assert(root/'enderecos_condominios.json').read_bytes()==original
    with cliente(root)as c:
        login(c);assert c.get(TREE).json()['endereco']['logradouro']==ENDERECO['logradouro']
