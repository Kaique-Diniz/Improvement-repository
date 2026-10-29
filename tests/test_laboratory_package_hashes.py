"""Identificadores portáveis; os bytes das fontes sintéticas não são normalizados."""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from conversor.laboratorio.run import caminho_protegido, hashes_pacote
from conversor.readers.text_support import ErroLeitura
from tests.fs_support import symlink_ou_skip_1314


def test_hashes_resolvem_identificadores_da_configuracao_sem_alterar_bytes(tmp_path):
    config = json.loads((Path(__file__).resolve().parents[1] /
                         'config_exemplos/laboratorio_pacote.json').read_text(encoding='utf-8'))
    conteudos = {}
    for caso in config['casos']:
        for campo in ('arquivo', 'cadastro', 'referencia_excel', 'resumo'):
            if relativo := caso.get(campo):
                # Inclui CRLF e bytes não textuais para detectar normalização indevida.
                conteudo = b'fonte sintetica\r\n\x00\xff' + relativo.encode('utf-8')
                arquivo = tmp_path / relativo
                arquivo.parent.mkdir(parents=True, exist_ok=True)
                arquivo.write_bytes(conteudo)
                conteudos[relativo] = conteudo
    inventario = hashes_pacote(tmp_path)
    assert inventario == {nome: sha256(valor).hexdigest() for nome, valor in conteudos.items()}
    assert all((tmp_path / nome).read_bytes() == valor for nome, valor in conteudos.items())
    assert inventario == hashes_pacote(tmp_path)


@pytest.mark.parametrize('formato_relativo', [PurePosixPath, PureWindowsPath])
def test_chave_posix_independe_da_representacao_nativa(tmp_path, monkeypatch, formato_relativo):
    arquivo = tmp_path / 'habita' / 'habita_tree_sintetico.pdf'
    arquivo.parent.mkdir()
    conteudo = b'apenas bytes sinteticos para hashing\r\n'
    arquivo.write_bytes(conteudo)
    relative_to = type(tmp_path).relative_to

    def relativo_nativo(self, *args, **kwargs):
        return formato_relativo(relative_to(self, *args, **kwargs))

    # Emula somente a representação do caminho relativo; leitura/segurança são reais.
    with monkeypatch.context() as patch:
        patch.setattr(type(tmp_path), 'relative_to', relativo_nativo)
        inventario = hashes_pacote(tmp_path)
    assert inventario == {'habita/habita_tree_sintetico.pdf': sha256(conteudo).hexdigest()}
    assert arquivo.read_bytes() == conteudo


def test_hashes_rejeitam_symlink(tmp_path):
    pacote = tmp_path / 'pacote'
    pacote.mkdir()
    fonte = tmp_path / 'fora.bin'
    fonte.write_bytes(b'sintetico')
    symlink_ou_skip_1314(pacote / 'link.bin', fonte)
    with pytest.raises(ErroLeitura, match='^PACOTE_CONTEM_LINK$'):
        hashes_pacote(pacote)


def test_caminho_fora_do_pacote_continua_rejeitado(tmp_path):
    with pytest.raises(ErroLeitura, match='^CAMINHO_FORA_DO_PACOTE$'):
        caminho_protegido(tmp_path, '../fora.bin')


def test_hashes_preservam_limite_de_quantidade(tmp_path):
    for numero in range(101):
        (tmp_path / f'{numero}.bin').write_bytes(b'')
    with pytest.raises(ErroLeitura, match='^PACOTE_LIMITE_EXCEDIDO$'):
        hashes_pacote(tmp_path)


def test_hashes_preservam_limite_de_tamanho(tmp_path):
    # Arquivo sintético esparso: excede o limite sem gravar 100 MiB de conteúdo.
    with (tmp_path / 'grande.bin').open('wb') as arquivo:
        arquivo.truncate(100 * 1024 * 1024 + 1)
    with pytest.raises(ErroLeitura, match='^PACOTE_LIMITE_EXCEDIDO$'):
        hashes_pacote(tmp_path)
