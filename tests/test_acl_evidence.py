"""Testes do módulo de EVIDÊNCIA DIAGNÓSTICA ACL (isolado do leitor de produção).

Todos os fixtures usam diretórios temporários sintéticos. Nenhum dado real,
PDF, credencial ou caminho da pasta privada original aparece aqui.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from conversor.adapters import windows_acl_evidence as wae


ACE_SINTETICO_A = {"sid": "S-1-5-21-SINTETICO-A", "access_mask": 0x1F01FF, "ace_flags": 0x00}
ACE_SINTETICO_B = {"sid": "S-1-5-21-SINTETICO-B", "access_mask": 0x110085, "ace_flags": 0x00}


def _arquivo_sintetico(tmp_path: Path, nome: str = "evidencia_sintetica.txt") -> Path:
    p = tmp_path / nome
    p.write_bytes(b"conteudo-sintetico-de-teste")
    return p


# --------------------------------------------------------------------------
# Cabeçalho e linhas vermelhas do módulo
# --------------------------------------------------------------------------

def test_modulo_declar_diagnostico_no_cabecalho():
    doc = (Path(wae.__file__).read_text(encoding="utf-8").splitlines()[0])
    assert "MÓDULO DE DIAGNÓSTICO ACL" in doc
    assert "NÃO USAR PARA CONTROLE DE ACESSO EM PRODUÇÃO" in doc
    assert "autoriza_acesso=False" in doc


def test_evidencia_sempre_hardcoded_false(tmp_path):
    alvo = _arquivo_sintetico(tmp_path)
    ev = wae.coletar_evidencia_acl(
        str(alvo), str(alvo),
        owner_sid="S-1-5-21-OWNER-SINTETICO",
        group_sid="S-1-5-21-GROUP-SINTETICO",
        aces=[ACE_SINTETICO_A, ACE_SINTETICO_B],
    )
    # Mesmo no cenário "ideal" (caminho coincide, máscaras idênticas),
    # o módulo NUNCA autoriza acesso nem se aplica ao leitor.
    assert ev["caminho_coincide"] is True
    assert ev["comparacao_5x7"]["identicas"] is True
    assert ev["autoriza_acesso"] is False
    assert ev["aplicada_ao_leitor"] is False
    # Serializável e estável (determinismo).
    json.dumps(ev, ensure_ascii=False)


# --------------------------------------------------------------------------
# Comparação de máscaras 5 x 7 — GROUP deve ser ignorado explicitamente
# --------------------------------------------------------------------------

def test_comparacao_5x7_ignora_group_conforme_owner_dacl_identicos():
    leitura_5 = {"mascara": 5, "owner_sid": "S-OWN", "group_sid": None,
                 "dacl_hash": "abc", "flags_dacl": 0}
    leitura_7 = {"mascara": 7, "owner_sid": "S-OWN", "group_sid": "S-GRP",
                 "dacl_hash": "abc", "flags_dacl": 0}
    resultado = wae.comparar_mascaras_5_e_7(leitura_5, leitura_7)
    assert resultado["identicas"] is True          # sem falso positivo
    assert resultado["campo_excluido_da_comparacao"] == "group_sid"
    assert resultado["owner_coincide"] is True
    assert resultado["dacl_coincide"] is True


def test_comparacao_5x7_detecta_divergencia_real_de_owner():
    leitura_5 = {"mascara": 5, "owner_sid": "S-OWN-1", "group_sid": None,
                 "dacl_hash": "abc", "flags_dacl": 0}
    leitura_7 = {"mascara": 7, "owner_sid": "S-OWN-2", "group_sid": "S-GRP",
                 "dacl_hash": "abc", "flags_dacl": 0}
    resultado = wae.comparar_mascaras_5_e_7(leitura_5, leitura_7)
    assert resultado["identicas"] is False
    assert resultado["owner_coincide"] is False


def test_comparacao_5x7_detecta_divergencia_real_de_dacl():
    leitura_5 = {"mascara": 5, "owner_sid": "S-OWN", "group_sid": None,
                 "dacl_hash": "abc", "flags_dacl": 0}
    leitura_7 = {"mascara": 7, "owner_sid": "S-OWN", "group_sid": "S-GRP",
                 "dacl_hash": "def", "flags_dacl": 0}
    resultado = wae.comparar_mascaras_5_e_7(leitura_5, leitura_7)
    assert resultado["identicas"] is False
    assert resultado["dacl_coincide"] is False


# --------------------------------------------------------------------------
# Normalização 8.3 + CompareStringOrdinal
# --------------------------------------------------------------------------

def test_normalizacao_8_3_expande_nome_curto(monkeypatch, tmp_path):
    longo = tmp_path / "Pasta_De_Projeto_Com_Nome_Longo"
    longo.mkdir()
    arquivo = _arquivo_sintetico(longo)
    curto = tmp_path / "PASTA_~1" / arquivo.name
    # Alias fictício: sua expansão pertence ao mock, não ao filesystem real.
    monkeypatch.setattr(
        wae, "_normalizar_caminho_8_3",
        lambda p: str(p).replace("PASTA_~1", longo.name),
    )
    assert wae._mesmo_path_normalizado(str(curto), str(arquivo)) is True


def test_comparacao_de_caminho_e_case_insensitive_ordinal(monkeypatch):
    monkeypatch.setattr(wae, "_normalizar_caminho_8_3", lambda p: str(p))
    assert wae._compare_string_ordinal_ignore_case(
        "C:\\Privado\\Arquivo.TXT", "c:\\privado\\arquivo.txt") == 0
    assert wae._compare_string_ordinal_ignore_case("a", "b") == -1


@pytest.fixture
def api_ordinal_sintetica(monkeypatch):
    class Comparar:
        resultado = 2
        chamadas = []

        def __call__(self, a, tamanho_a, b, tamanho_b, ignorar_case):
            assert self.argtypes == [wae.ctypes.c_wchar_p, wae.ctypes.c_int,
                                     wae.ctypes.c_wchar_p, wae.ctypes.c_int,
                                     wae.ctypes.c_int]
            assert self.restype is wae.ctypes.c_int
            self.chamadas.append((a, tamanho_a, b, tamanho_b, ignorar_case))
            return self.resultado

    comparar = Comparar()

    def carregar(nome, *, use_last_error):
        assert nome == "kernel32" and use_last_error is True
        return SimpleNamespace(CompareStringOrdinal=comparar)

    # Trocar apenas a referência do módulo; não simular Windows no pytest todo.
    monkeypatch.setattr(wae, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(wae.ctypes, "WinDLL", carregar, raising=False)
    monkeypatch.setattr(wae.ctypes, "get_last_error", lambda: 87, raising=False)
    monkeypatch.setattr(wae, "_normalizar_caminho_8_3", lambda p: str(p))
    return comparar


@pytest.mark.parametrize("nativo,esperado", [(1, -1), (2, 0), (3, 1)])
def test_assinatura_nativa_e_retorno_ordinal(api_ordinal_sintetica, nativo, esperado):
    api_ordinal_sintetica.resultado = nativo
    assert wae._compare_string_ordinal_ignore_case("a", "b") == esperado
    assert api_ordinal_sintetica.chamadas == [("a", 1, "b", 1, 1)]


@pytest.mark.parametrize("texto,unidades", [
    ("", 0), ("ação", 4), ("漢字", 2), ("a\U0001f600x", 4),
    ("\ud83d\ude00", 2), ("\ud800", 1),
])
def test_comprimento_nativo_em_unidades_utf16(api_ordinal_sintetica, texto, unidades):
    assert wae._compare_string_ordinal_ignore_case(texto, "z") == 0
    assert api_ordinal_sintetica.chamadas == [(texto, unidades, "z", 1, 1)]


@pytest.mark.parametrize("a,b,iguais", [
    ("ação.txt", "AÇÃO.TXT", True),
    ("a\U0001f600x", "a\U0001f600y", False),
    ("a\U0001f600x", "a\U0001f600x", True),
    ("", "", True),
])
def test_comparacao_unicode_sem_truncar_sufixo(a, b, iguais):
    # No Windows exercita a API real, além do teste sintético de assinatura.
    assert (wae._compare_string_ordinal_ignore_case(a, b) == 0) is iguais


@pytest.mark.parametrize("a,b", [("a\0x", "a"), ("a", "a\0x"), ("a\0x", "a\0x")])
def test_nul_nao_pode_ser_truncado_ou_considerado_igual(monkeypatch, a, b):
    def nao_normalizar(_):
        pytest.fail("NUL deve ser rejeitado antes da API de normalização")

    monkeypatch.setattr(wae, "_normalizar_caminho_8_3", nao_normalizar)
    assert wae._mesmo_path_normalizado(a, b) is False
    with pytest.raises(OSError, match="NUL"):
        wae._compare_string_ordinal_ignore_case(a, b)


@pytest.mark.parametrize("resultado", [0, -1, 4])
def test_erro_nativo_nunca_indica_igualdade(api_ordinal_sintetica, resultado, tmp_path):
    api_ordinal_sintetica.resultado = resultado
    with pytest.raises(OSError, match="CompareStringOrdinal falhou"):
        wae._compare_string_ordinal_ignore_case("a", "a")
    assert wae._mesmo_path_normalizado("a", "a") is False
    alvo = _arquivo_sintetico(tmp_path)
    ev = wae.coletar_evidencia_acl(str(alvo), str(alvo), owner_sid="S-OWN",
                                  group_sid=None, aces=[ACE_SINTETICO_A])
    assert ev["caminho_coincide"] is False
    assert ev["autoriza_acesso"] is False
    assert ev["aplicada_ao_leitor"] is False


@pytest.mark.parametrize("falha", ["dll", "simbolo", "chamada"])
def test_api_indisponivel_nao_usa_casefold(api_ordinal_sintetica, monkeypatch, falha):
    def indisponivel(*args, **kwargs):
        if falha == "dll":
            raise OSError("DLL indisponível")
        if falha == "simbolo":
            return SimpleNamespace()
        return SimpleNamespace(CompareStringOrdinal=chamada_indisponivel)

    def chamada_indisponivel(*args):
        raise OSError("Chamada indisponível")

    monkeypatch.setattr(wae.ctypes, "WinDLL", indisponivel)
    with pytest.raises(OSError):
        wae._compare_string_ordinal_ignore_case("a", "A")
    assert wae._mesmo_path_normalizado("a", "A") is False


def test_hardlink_e_rejeitado_na_comparacao_de_caminho(tmp_path):
    origem = _arquivo_sintetico(tmp_path, "origem.txt")
    link = tmp_path / "hardlink.txt"
    try:
        os.link(origem, link)
    except (OSError, NotImplementedError):
        pytest.skip("hardlink indisponível nesta plataforma")
    # O hardlink tem o MESMO conteúdo/inodo, mas caminho normalizado
    # diferente — a evidência diagnóstica deve rejeitá-lo como coincidência.
    assert wae._mesmo_path_normalizado(str(link), str(origem)) is False
    ev = wae.coletar_evidencia_acl(
        str(origem), str(link),
        owner_sid="S-OWN", group_sid=None, aces=[ACE_SINTETICO_A],
    )
    assert ev["caminho_coincide"] is False
    assert ev["nlink"] >= 2
    assert ev["autoriza_acesso"] is False


def test_symlink_reparse_point_e_rejeitado(tmp_path):
    origem = _arquivo_sintetico(tmp_path, "origem.txt")
    link = tmp_path / "symlink.txt"
    try:
        os.symlink(origem, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponível nesta plataforma")
    ev = wae.coletar_evidencia_acl(
        str(origem), str(link),
        owner_sid="S-OWN", group_sid=None, aces=[ACE_SINTETICO_A],
    )
    assert ev["reparse_point_detectado"] is True
    assert ev["caminho_coincide"] is False
    assert ev["handle_path_normalizado"] is None
    assert ev["autoriza_acesso"] is False


# --------------------------------------------------------------------------
# Diagnóstico de herança (INHERITED_ACE) — apenas evidência, nunca acesso
# --------------------------------------------------------------------------

def test_diagnostico_marca_artefato_de_heranca_sem_autorizar():
    ace_base = dict(ACE_SINTETICO_A)
    ace_herdado = {**ACE_SINTETICO_A, "ace_flags": wae.INHERITED_ACE}
    resultado = wae.mesmas_regras_diagnostico([ace_base], [ace_herdado])
    assert resultado["divergente"] is True
    assert resultado["somente_heranca"] is True
    assert resultado["divergencias"][0]["tipo"] == "heranca_invertida"


def test_diagnostico_aponta_divergencia_real_de_sid():
    outro = {**ACE_SINTETICO_A, "sid": "S-1-5-21-OUTRO"}
    resultado = wae.mesmas_regras_diagnostico([ACE_SINTETICO_A], [outro])
    assert resultado["divergente"] is True
    assert resultado["somente_heranca"] is False


def test_evidencia_com_baseline_registra_artefato_mas_nao_autoriza(tmp_path):
    alvo = _arquivo_sintetico(tmp_path)
    ace_base = dict(ACE_SINTETICO_A)
    ace_herdado = {**ACE_SINTETICO_A, "ace_flags": wae.INHERITED_ACE}
    ev = wae.coletar_evidencia_acl(
        str(alvo), str(alvo),
        owner_sid="S-OWN", group_sid="S-GRP", aces=[ace_base],
        baseline_owner_sid="S-OWN", baseline_aces=[ace_herdado],
    )
    analise = ev["analise_baseline"]
    assert analise["somente_heranca"] is True
    # Ainda assim, nada é autorizado nem aplicado ao leitor:
    assert ev["autoriza_acesso"] is False
    assert ev["aplicada_ao_leitor"] is False
