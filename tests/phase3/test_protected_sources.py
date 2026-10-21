from hashlib import sha256

import pytest

from conversor.adapters.protected_sources import FontesLocaisProtegidas
from conversor.readers.contracts import FonteProtegida
from conversor.readers.text_support import ErroLeitura


def test_fonte_por_id_e_hash_sem_caminho_no_contrato(tmp_path):
    conteudo = b"conteudo sintetico"
    (tmp_path / "fonte.pdf").write_bytes(conteudo)
    fonte = FonteProtegida(arquivo_id="fonte", sha256=sha256(conteudo).hexdigest())
    assert FontesLocaisProtegidas(tmp_path, {"fonte": "fonte.pdf"}).ler(fonte) == conteudo
    assert "pdf" not in fonte.model_dump_json()


@pytest.mark.parametrize("falha,codigo", [("ausente", "FONTE_INDISPONIVEL"), ("sem_mapa", "FONTE_NAO_AUTORIZADA"),
    ("hash", "HASH_FONTE_DIVERGENTE"), ("limite", "FONTE_LIMITE_EXCEDIDO"),
    ("escape", "FONTE_FORA_DA_AREA_AUTORIZADA"), ("absoluto", "FONTE_FORA_DA_AREA_AUTORIZADA"),
    ("link", "FONTE_CONTEM_LINK")])
def test_fontes_rejeitam_acesso_invalido_sem_conteudo_no_erro(tmp_path, falha, codigo):
    dados = b"SENTINELA_DE_PRIVACIDADE"
    (tmp_path / "fonte.pdf").write_bytes(dados)
    fonte = FonteProtegida(arquivo_id="fonte", sha256=sha256(dados).hexdigest())
    caminho, limite = "fonte.pdf", 100
    mapa = {"fonte": caminho}
    if falha == "ausente": mapa["fonte"] = "ausente.pdf"
    elif falha == "sem_mapa": mapa = {}
    elif falha == "hash": fonte = FonteProtegida(arquivo_id="fonte", sha256="0" * 64)
    elif falha == "limite": limite = 1
    elif falha == "escape": mapa["fonte"] = "../fora.pdf"
    elif falha == "absoluto": mapa["fonte"] = str(tmp_path / "fonte.pdf")
    elif falha == "link":
        (tmp_path / "link.pdf").symlink_to(tmp_path / "fonte.pdf")
        mapa["fonte"] = "link.pdf"
    with pytest.raises(ErroLeitura, match=codigo) as erro:
        FontesLocaisProtegidas(tmp_path, mapa, limite_bytes=limite).ler(fonte)
    assert str(erro.value) == codigo


def test_mudanca_de_fonte_apos_autorizacao_e_detectada(tmp_path):
    p = tmp_path / "fonte.pdf"
    p.write_bytes(b"antes")
    fonte = FonteProtegida(arquivo_id="fonte", sha256=sha256(p.read_bytes()).hexdigest())
    p.write_bytes(b"depois")
    with pytest.raises(ErroLeitura, match="HASH_FONTE_DIVERGENTE"):
        FontesLocaisProtegidas(tmp_path, {"fonte": "fonte.pdf"}).ler(fonte)
