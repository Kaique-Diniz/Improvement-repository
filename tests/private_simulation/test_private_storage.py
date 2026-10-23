from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os

from filelock import FileLock
import pytest

from conversor.adapters.private_simulation_json import RepositorioSimulacoesJSON
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos


def test_pacote_persistido_assinado_0600_e_imutavel(laboratorio):
    c = laboratorio()
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    assert c.armazenamento.carregar_pacote(c.pacote.id) == c.pacote
    path, recibo = c.armazenamento._paths('pacote', c.pacote.id)
    if os.name == 'posix':
        assert path.stat().st_mode & 0o777 == recibo.stat().st_mode & 0o777 == 0o600
        assert c.armazenamento.raiz.stat().st_mode & 0o777 == 0o700
    assert c.gestor.segredo not in path.read_text() + recibo.read_text()
    assert json.loads(recibo.read_text())['responsavel_id'] == 'gestor'
    with pytest.raises(ErroAplicacao, match='IMUTAVEL_JA_EXISTE'):
        c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)


@pytest.mark.parametrize('ataque', ['conteudo', 'hash_recalculado', 'recibo_apagado', 'recibo_falso', 'troca_identidade', 'politica_adulterada'])
def test_adulteracao_e_omissao_nao_podem_reassinar_pacote(laboratorio, ataque):
    c = laboratorio()
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    path, recibo = c.armazenamento._paths('pacote', c.pacote.id)
    if ataque in ('conteudo', 'hash_recalculado'):
        dados = json.loads(path.read_text()); dados['entrada']['lote']['pessoas'] = []
        path.write_bytes(bytes_canonicos(dados))
        if ataque == 'hash_recalculado':
            r = json.loads(recibo.read_text()); r['sha256'] = sha256(path.read_bytes()).hexdigest()
            recibo.write_text(json.dumps(r))
    elif ataque == 'recibo_apagado':
        recibo.unlink()
    elif ataque == 'recibo_falso':
        r = json.loads(recibo.read_text()); r['assinatura'] = '0' * 64; recibo.write_text(json.dumps(r))
    elif ataque == 'troca_identidade':
        r = json.loads(recibo.read_text()); r['id'] = 'outro'; recibo.write_text(json.dumps(r))
    else:
        path_politica = next((c.autoridade.raiz / 'policies').glob('*.json'))
        path_politica.write_text('{}')
    with pytest.raises(ErroAplicacao):
        c.armazenamento.carregar_pacote(c.pacote.id)


def test_credencial_sem_permissao_tecnica_nao_pode_atestar(laboratorio):
    c = laboratorio()
    with pytest.raises(ErroAplicacao, match='OPERACAO_NAO_AUTORIZADA'):
        c.armazenamento.gravar_pacote(c.pacote, credencial=c.credenciais['ativador'])
    assert not list(c.armazenamento.raiz.glob('*.json'))


@pytest.mark.parametrize('recurso', ['repositorio_git', 'fonte_git', 'symlink', 'permissao_fonte', 'permissao_raiz', 'mesma_autoridade'])
def test_isolamento_git_links_e_permissoes(laboratorio, tmp_path, recurso):
    c = laboratorio()
    git = tmp_path / 'checkout'; git.mkdir(mode=0o700)
    (git / '.git').mkdir(); (git / '.git' / 'HEAD').write_text('ref: refs/heads/main\n')
    if recurso == 'repositorio_git':
        with pytest.raises(ErroAplicacao, match='NAO_PODE_FICAR_NO_GIT'):
            RepositorioSimulacoesJSON(git / 'privado', repositorio_id='outro', ambiente='sintetico', autoridade=c.autoridade)
        assert not (git / 'privado').exists()
        return
    if recurso == 'mesma_autoridade':
        with pytest.raises(ErroAplicacao, match='AUTORIDADE_DEVE_SER_EXTERNA'):
            RepositorioSimulacoesJSON(c.autoridade.raiz / 'simulacao', repositorio_id='outro', ambiente='sintetico', autoridade=c.autoridade)
        return
    if recurso == 'fonte_git':
        path = git / 'fonte.txt'; path.write_bytes(c.primaria.read_bytes()); path.chmod(0o600)
        fonte = c.pacote.fontes[0].model_copy(update={'caminho': str(path)})
        c.pacote = c.pacote.model_copy(update={'fontes': (fonte, *c.pacote.fontes[1:])})
    elif recurso == 'symlink':
        link = tmp_path / 'link'; link.symlink_to(c.primaria)
        fonte = c.pacote.fontes[0].model_copy(update={'caminho': str(link)})
        c.pacote = c.pacote.model_copy(update={'fontes': (fonte, *c.pacote.fontes[1:])})
    elif recurso == 'permissao_fonte':
        c.primaria.chmod(0o644)
    else:
        c.armazenamento.raiz.chmod(0o755)
    with pytest.raises(ErroAplicacao):
        c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)


def test_duas_gravacoes_concorrentes_so_uma_conclui(laboratorio):
    c = laboratorio()
    def gravar(_):
        try:
            c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
            return 'ok'
        except ErroAplicacao as e:
            return str(e)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(gravar, range(2)))
    assert resultados.count('ok') == 1
    assert all(r == 'ok' or r in ('ARTEFATO_PRIVADO_IMUTAVEL_JA_EXISTE', 'REPOSITORIO_PRIVADO_OCUPADO') for r in resultados)
    assert c.armazenamento.carregar_pacote(c.pacote.id) == c.pacote


def test_timeout_de_concorrencia_nao_deixa_recibo(laboratorio):
    c = laboratorio()
    with FileLock(c.armazenamento.lock, mode=0o600):
        with pytest.raises(ErroAplicacao, match='REPOSITORIO_PRIVADO_OCUPADO'):
            c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    assert not list(c.armazenamento.raiz.glob('*.json'))


def test_falha_antes_do_commit_deixa_apenas_orfao_nao_legivel(laboratorio, monkeypatch):
    c = laboratorio()
    from conversor.adapters import private_simulation_json as modulo
    original = modulo.os.replace
    def falhar(origem, destino):
        if destino.parent == c.armazenamento.ancoras:
            raise OSError('falha sintética de commit')
        return original(origem, destino)
    with monkeypatch.context() as patch:
        patch.setattr(modulo.os, 'replace', falhar)
        with pytest.raises(ErroAplicacao, match='ARTEFATO_PRIVADO_INDISPONIVEL'):
            c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    with pytest.raises(ErroAplicacao):
        c.armazenamento.carregar_pacote(c.pacote.id)
    assert not list(c.armazenamento.raiz.glob('*.tmp'))
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    assert c.armazenamento.carregar_pacote(c.pacote.id) == c.pacote


@pytest.mark.parametrize('id_', ['../fuga', 'a/b', '', '/tmp/fuga'])
def test_ids_nao_escapam_do_repositorio(laboratorio, id_):
    c = laboratorio()
    with pytest.raises(ErroAplicacao, match='CONTRATO_PRIVADO_INVALIDO'):
        c.armazenamento.carregar_pacote(id_)


def test_erros_e_stdout_nao_expoem_dados(laboratorio, capsys):
    c = laboratorio()
    c.primaria.unlink()
    with pytest.raises(ErroAplicacao) as e:
        c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    assert c.pacote.entrada.lote.pessoas[0].nome not in str(e.value)
    assert str(c.primaria) not in str(e.value)
    assert capsys.readouterr().out == ''
