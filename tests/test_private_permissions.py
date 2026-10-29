"""Política ACL e proteções reais da plataforma atual; somente fixtures sintéticas."""
from dataclasses import replace
from pathlib import Path

import pytest

from conversor.adapters import private_permissions as p
from conversor.adapters.private_json import escrever_json
from conversor.adapters.private_simulation_json import conferir_local_privado
from conversor.application.ports import ErroAplicacao
from conversor.adapters.billing_authority import ler_protegido
from tests.fs_support import assert_privado, ampliar_acesso_sintetico

USER='S-1-5-21-100-200-300-1001'
OTHER='S-1-5-21-100-200-300-1002'
SAFE=p.AclPrivada(USER,USER,True,(p.AcePrivada(0,0,p.FULL_CONTROL,USER),p.AcePrivada(0,0,p.FULL_CONTROL,'S-1-5-18')))


@pytest.mark.parametrize('acl',[
    replace(SAFE,proprietario=OTHER),replace(SAFE,dacl_presente=False),replace(SAFE,entradas=()),
    replace(SAFE,entradas=SAFE.entradas+(p.AcePrivada(0,0,0x120089,'S-1-1-0'),)),
    replace(SAFE,entradas=SAFE.entradas+(p.AcePrivada(0,0x10,0x120089,OTHER),)),
    replace(SAFE,entradas=SAFE.entradas+(p.AcePrivada(0,0x08,0x120089,OTHER),)),
    replace(SAFE,entradas=SAFE.entradas+(p.AcePrivada(5,0,p.FULL_CONTROL,USER),)),
    replace(SAFE,entradas=SAFE.entradas+(p.AcePrivada(1,0,0x120089,USER),)),
    replace(SAFE,entradas=(p.AcePrivada(0,0x08,p.FULL_CONTROL,USER),)),
    replace(SAFE,entradas=(p.AcePrivada(0,0,0x120089,USER),)),
])
def test_acl_nao_comprovada_e_ampla_nao_sao_aprovadas(acl):
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_(INSEGURA|NAO_COMPROVADA)'):p.validar_acl(acl)


@pytest.mark.parametrize('acl',[SAFE,replace(SAFE,proprietario='S-1-5-32-544'),
    replace(SAFE,entradas=(p.AcePrivada(0,0x10,p.FULL_CONTROL,USER),))])
def test_acl_restrita_explicita_ou_herdada_e_aceita(acl):
    p.validar_acl(acl)


def test_backend_windows_indisponivel_nao_comprova_privacidade(tmp_path,monkeypatch):
    def falhar():raise OSError('SENTINELA_NATIVA_NAO_EXIBIR')
    monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',falhar)
    with pytest.raises(ErroAplicacao,match='^ACL_PRIVADA_NAO_VERIFICAVEL$')as e:p.conferir_windows(tmp_path)
    assert 'SENTINELA'not in str(e.value)


def test_json_recebe_dacl_antes_de_conter_dados(tmp_path,monkeypatch):
    observadas=[]
    class Backend:
        def proteger_novo(self,path,**kw):
            assert path.is_file()and path.stat().st_size==0;observadas.append(path)
        def ler(self,path):return SAFE
    monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',Backend)
    dest=tmp_path/'audit.json';escrever_json(dest,{'fixture':'sem_dados_pessoais'})
    assert len(observadas)==1 and dest.is_file()


def test_conferencia_existente_nao_corrige_acl_silenciosamente(tmp_path,monkeypatch):
    file=tmp_path/'chave_sintetica.bin';file.write_bytes(b'SENTINELA SINTETICA')
    class Backend:
        def proteger_novo(self,*a,**kw):pytest.fail('Não reescrever ACL existente durante conferência.')
        def ler(self,path):return replace(SAFE,dacl_presente=False)
    monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',Backend)
    with pytest.raises(ErroAplicacao):p.conferir_windows(file)
    with pytest.raises(ErroAplicacao):p.criar_diretorio_privado(tmp_path)
    assert file.read_bytes()==b'SENTINELA SINTETICA'


@pytest.mark.parametrize('arquivo',[False,True])
def test_permissoes_reais_da_plataforma_e_rejeicao_de_excesso(tmp_path,arquivo):
    alvo=tmp_path/'privado'
    if arquivo:escrever_json(alvo,{'sintetico':True})
    else:p.criar_diretorio_privado(alvo)
    assert_privado(alvo)
    ampliar_acesso_sintetico(alvo)
    with pytest.raises(ErroAplicacao):conferir_local_privado(alvo,arquivo=arquivo)


def test_chave_de_vinculos_permissiva_nao_pode_ser_usada(tmp_path):
    from tests.bbz.test_persistent_links import repo,iniciar
    from conversor.readers.text_support import ErroLeitura
    r=repo(tmp_path);assert_privado(r.privado);iniciar(tmp_path,r)
    assert_privado(r.key);key=r.key.read_bytes();antes=r.path.read_bytes()
    ampliar_acesso_sintetico(r.key)
    with pytest.raises(ErroLeitura):r.consultar()
    assert r.key.read_bytes()==key and r.path.read_bytes()==antes


def test_reparse_sinalizado_nao_chega_ao_backend_acl(tmp_path,monkeypatch):
    alvo=tmp_path/'arquivo_sintetico';alvo.write_bytes(b'SINTETICO')
    cls=type(alvo);original=cls.lstat
    def lstat(path,*args,**kw):
        st=original(path,*args,**kw)
        if path!=alvo:return st
        class Reparse:
            st_file_attributes=0x400
            def __getattr__(self,name):return getattr(st,name)
        return Reparse()
    def backend():pytest.fail('Reparse point não pode chegar ao backend de ACL.')
    monkeypatch.setattr(cls,'lstat',lstat);monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',backend)
    with pytest.raises(ErroAplicacao,match='CAMINHO_COM_LINK'):p.conferir_windows(alvo)


@pytest.mark.parametrize('ponto',['arquivo','raiz'])
def test_fonte_sinalizada_como_symlink_nao_e_lida(tmp_path,monkeypatch,ponto):
    from hashlib import sha256
    from conversor.adapters.protected_sources import FontesLocaisProtegidas
    from conversor.readers.contracts import FonteProtegida
    from conversor.readers.text_support import ErroLeitura
    alvo=tmp_path/'fonte_sintetica.pdf';raw=b'SINTETICO';alvo.write_bytes(raw)
    cls=type(alvo);is_link=cls.is_symlink;abrir=cls.open
    sinalizado=alvo if ponto=='arquivo'else tmp_path
    def link(p):return p==sinalizado or is_link(p)
    def nao_ler(p,*a,**kw):
        if p==alvo:pytest.fail('Tentativa de ler alvo sinalizado como link.')
        return abrir(p,*a,**kw)
    monkeypatch.setattr(cls,'is_symlink',link);monkeypatch.setattr(cls,'open',nao_ler)
    with pytest.raises(ErroLeitura,match='FONTE_CONTEM_LINK'):
        FontesLocaisProtegidas(tmp_path,{'f':'fonte_sintetica.pdf'}).ler(FonteProtegida(arquivo_id='f',sha256=sha256(raw).hexdigest()))


def test_ancestral_sinalizado_nao_pode_redirecionar_gravacao(tmp_path,monkeypatch):
    from conversor.adapters.document_links_json import RepositorioVinculosJSON
    from conversor.readers.text_support import ErroLeitura
    link=tmp_path/'atalho_sintetico';root=link/'interno';cls=type(root);original=cls.is_symlink;mkdir=cls.mkdir
    def is_link(p):return p==link or original(p)
    def nao_criar(p,*a,**kw):
        if p==root or p==link:pytest.fail('Tentativa de criar diretório sob ancestral sinalizado.')
        return mkdir(p,*a,**kw)
    monkeypatch.setattr(cls,'is_symlink',is_link);monkeypatch.setattr(cls,'mkdir',nao_criar)
    with pytest.raises(ErroLeitura):RepositorioVinculosJSON(root)
    assert not root.exists()


def test_auditoria_de_permissoes_nao_altera_arquivos_nem_expoe_nomes(tmp_path):
    from conversor.private_security import auditar
    root=p.criar_diretorio_privado(tmp_path/'area');file=root/'arquivo_sintetico.json';escrever_json(file,{'valor':'SENTINELA_NAO_EXIBIR'})
    antes=file.read_bytes();r=auditar(root)
    assert r['estado']=='politica_local_confere'and r['alteracoes_realizadas']==0
    ampliar_acesso_sintetico(file);r=auditar(root)
    assert r['estado']=='nao_comprovado'and r['falhas']
    assert file.read_bytes()==antes and 'SENTINELA'not in str(r)and file.name not in str(r)


def test_corrida_de_criacao_nao_reescreve_dacl_de_diretorio_existente(tmp_path,monkeypatch):
    alvo=tmp_path/'corrida_sintetica';cls=type(alvo);mkdir=cls.mkdir
    class Backend:
        def proteger_novo(self,*args,**kwargs):pytest.fail('Não aplicar DACL em diretório criado por outro processo.')
        def ler(self,path):return SAFE
    def concorrente(path,*args,**kwargs):
        if path==alvo:
            mkdir(path,mode=0o700)
            raise FileExistsError('Criado simultaneamente na fixture.')
        return mkdir(path,*args,**kwargs)
    monkeypatch.setattr(cls,'mkdir',concorrente);monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',Backend)
    assert p.criar_diretorio_privado(alvo)==alvo and alvo.is_dir()


def test_fixture_de_vinculos_cria_raiz_segura_e_nao_repara_raiz_existente(tmp_path):
    from tests.bbz.test_persistent_links import repo
    from conversor.readers.text_support import ErroLeitura
    r=repo(tmp_path);assert_privado(r.privado)
    sentinel=r.privado/'sentinela_sintetica';sentinel.write_bytes(b'SINTETICO ORIGINAL')
    ampliar_acesso_sintetico(r.privado)
    with pytest.raises((ErroAplicacao,ErroLeitura)):repo(tmp_path)
    assert sentinel.read_bytes()==b'SINTETICO ORIGINAL'
