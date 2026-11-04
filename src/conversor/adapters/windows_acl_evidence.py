"""MÓDULO DE DIAGNÓSTICO ACL. NÃO USAR PARA CONTROLE DE ACESSO EM PRODUÇÃO. autoriza_acesso=False."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import stat
import sys
from typing import Any

# --------------------------------------------------------------------------
# Linhas vermelhas deste módulo (consolidado na fase de diagnóstico):
#
# 1. FERRAMENTA EXCLUSIVA DE DIAGNÓSTICO. Este módulo NUNCA autoriza acesso:
#    os campos `autoriza_acesso` e `aplicada_ao_leitor` são hardcoded False
#    em toda evidência gerada, independentemente do resultado da análise.
#    O portão real do leitor de produção é `private_permissions.mesmas_regras`,
#    que continua exigindo igualdade exata de ACEs, INCLUINDO o bit
#    INHERITED_ACE (0x10). Qualquer tolerância aqui existente (flags de
#    herança e caminhos 8.3) serve APENAS para reduzir falsos positivos na
#    EVIDÊNCIA diagnóstica e jamais se propaga para decisões de acesso.
#
# 2. Sem dados reais: todas as fixtures de teste usam diretórios temporários
#    sintéticos; nenhum caminho da pasta privada original é gravado na
#    evidência além do canonical_path resolvido localmente.
# --------------------------------------------------------------------------

INHERITED_ACE = 0x10            # ACE_HEADER.AceFlags: ACE herdado por propagação.
FLAG_INHERIT_ONLY = 0x08        # AceFlags: ACE aplicável apenas a filhos.
FLAG_NO_PROPAGATE = 0x04        # AceFlags: não se propaga além do filho imediato.
VALID_INHERITANCE_FLAGS = FLAG_INHERIT_ONLY | FLAG_NO_PROPAGATE | INHERITED_ACE

# Máscaras de SecurityInformation usadas nas leituras comparativas.
MASK_OWNER_DAACL = 0x05         # OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION
MASK_OWNER_GROUP_DAACL = 0x07   # + GROUP_SECURITY_INFORMATION

# Flags de reparse point relevantes para rejeição de atalhos/links.
_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
_IO_REPARSE_TAG_SYMLINK = 0xA000000C
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FSCTL_GET_REPARSE_POINT = 0x000900A8

_EVIDENCIA_VERSAO = "evidencia-acl-2"


# ==========================================================================
# Normalização de caminhos 8.3 (nomes curtos) via GetLongPathNameW
# ==========================================================================

def _normalizar_caminho_8_3_win(path: str) -> str:
    """Expande componentes em formato 8.3 (ex.: PROJET~1) com GetLongPathNameW.

    GetLongPathNameW preserva a grafia (casing) original dos componentes que
    já estão em forma longa — comportamento desejado, pois a comparação de
    identidade de caminho é feita separadamente de forma case-insensitive.
    Lança OSError se o caminho não puder ser expandido (inexistente/sem
    permissão): nesse caso a evidência deve REGISTRAR falha, nunca assumir
    equivalência.
    """
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    buf = ctypes.create_unicode_buffer(32768)
    n = kernel32.GetLongPathNameW(str(path), buf, len(buf))
    if n == 0 or n >= len(buf):
        raise OSError(ctypes.get_last_error(), "GetLongPathNameW falhou", str(path))
    return buf[:n]


def _normalizar_caminho_8_3_posix(path: str) -> str:
    """Equivalente fora do Windows para testes determinísticos.

    Resolve um caminho canônico sem seguir links simbólicos, de modo que
    dois nomes diferentes apontando para entradas distintas (hardlink/symlink)
    permaneçam distintos após a normalização.
    """
    return os.path.realpath(str(path))


if sys.platform == "win32":
    _normalizar_caminho_8_3 = _normalizar_caminho_8_3_win
else:  # pragma: no cover - plataforma de desenvolvimento/teste
    _normalizar_caminho_8_3 = _normalizar_caminho_8_3_posix


def _norm_key(caminho: str) -> str:
    """Chave de comparação: case-insensitive e sem separador final."""
    return str(caminho).rstrip("\\/").casefold()


def _compare_string_ordinal_ignore_case(a: str, b: str) -> int:
    """Comparação ordinal binária case-insensitive (espelho de CompareStringOrdinal).

    Retorna 0 quando iguais, -1 quando a < b, 1 quando a > b — mesma
    semântica de retorno da API Win32 (LESS/EQUAL/GREATER ajustado).
    """
    if sys.platform == "win32":  # pragma: no cover - caminho Windows real
        CSTR_LESS_THAN, CSTR_EQUAL, CSTR_GREATER_THAN = 1, 2, 3
        resultado = ctypes.windll.oleaut32.CompareStringOrdinal(  # type: ignore[attr-defined]
            0x400,  # LOCALE_USER_DEFAULT
            1,      # NORM_IGNORECASE (flags)
            str(a), len(a),
            str(b), len(b),
            True,   # bIgnoreCase
        )
        return {CSTR_EQUAL: 0, CSTR_LESS_THAN: -1, CSTR_GREATER_THAN: 1}.get(resultado, 1)
    x, y = a.casefold(), b.casefold()
    return (x > y) - (x < y)


def _mesmo_path_normalizado(handle_path: str, esperado: str) -> bool:
    """Compara o caminho do handle aberto com o caminho esperado.

    Pipeline anti-hardlink/anti-8.3:
      1. Normaliza AMBOS os lados com GetLongPathNameW (expansão de nomes
         curtos 8.3). Falha de normalização => caminhos NÃO coincidem.
      2. Compara com CompareStringOrdinal (ordinal, case-insensitive).
    Um hardlink possui nome próprio apontando para o MESMO conteúdo, mas
    seu caminho normalizado permanece diferente do caminho esperado — a
    comparação ordinal o rejeita. Reparse points (symlinks/junções) são
    rejeitados antes desta etapa por `_detectar_reparse_point`.
    """
    try:
        norm_handle = _normalizar_caminho_8_3(handle_path)
        norm_esperado = _normalizar_caminho_8_3(esperado)
    except OSError:
        return False
    if _compare_string_ordinal_ignore_case(norm_handle, norm_esperado) != 0:
        return False
    return True


# ==========================================================================
# Comparação de máscaras 5 (OWNER+DACL) vs 7 (OWNER+GROUP+DACL)
# ==========================================================================

def _ignorar_group(rec: dict[str, Any]) -> dict[str, Any]:
    """Projeta um registro de leitura descartando explicitamente o campo GROUP.

    A divergência entre as leituras com máscara 5 e máscara 7 é, por
    definição, apenas a presença do GROUP_SID lido na máscara 7. Se a
    comparação binária incluísse esse campo, toda evidência reportaria
    DIVERGENTE mesmo com OWNER e DACL idênticos (falso positivo clássico).
    Portanto a comparação binária ignora explicitamente GROUP e compara
    somente owner_sid, dacl_hash e flags_dacl.
    """
    return {
        "owner_sid": rec.get("owner_sid"),
        "dacl_hash": rec.get("dacl_hash"),
        "flags_dacl": rec.get("flags_dacl"),
    }


def comparar_mascaras_5_e_7(leitura_5: dict[str, Any],
                            leitura_7: dict[str, Any]) -> dict[str, Any]:
    """Retorna o resultado binário da comparação 5x7 sem contagem de GROUP."""
    projetada_5 = _ignorar_group(leitura_5)
    projetada_7 = _ignorar_group(leitura_7)
    identicas = projetada_5 == projetada_7
    return {
        "identicas": identicas,
        "campo_excluido_da_comparacao": "group_sid",
        "motivo_exclusao": (
            "A máscara 7 acrescenta GROUP ao resultado; incluir GROUP na "
            "comparação binária contra a máscara 5 geraria falso positivo "
            "permanente de divergência."
        ),
        "owner_coincide": projetada_5["owner_sid"] == projetada_7["owner_sid"],
        "dacl_coincide": projetada_5["dacl_hash"] == projetada_7["dacl_hash"],
    }


# ==========================================================================
# Comparação diagnóstica de ACEs (IGNORA artefatos de herança — só diagnóstico)
# ==========================================================================

def _flags_sem_heranca(ace_flags: int) -> int:
    """Remove bits de herança (INHERITED_ACE e flags de propagação) do AceFlags.

    ATENÇÃO: esta normalização existe SOMENTE para a evidência diagnóstica,
    que precisa distinguir "ACE efetivamente diferente" de "ACE idêntico que
    o Windows marcou como herdado". O leitor de produção (private_permissions)
    aplica exatamente a regra inversa e NUNCA chama esta função.
    """
    return ace_flags & ~VALID_INHERITANCE_FLAGS


def mesmas_regras_diagnostico(aces_a: list[dict[str, Any]],
                              aces_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Compara ACEs em modo diagnóstico, ignorando bits de herança.

    Retorna dicionário com o veredito e o detalhamento da divergência,
    incluindo uma marca explícita de que a diferença era puramente de
    herança (diagnóstico) — o que NUNCA autoriza acesso.
    """
    divergencias: list[dict[str, Any]] = []
    so_heranca = True
    if len(aces_a) != len(aces_b):
        return {
            "divergente": True,
            "somente_heranca": False,
            "divergencias": [{"tipo": "quantidade",
                              "a": len(aces_a), "b": len(aces_b)}],
        }
    for i, (a, b) in enumerate(zip(aces_a, aces_b)):
        if a.get("sid") != b.get("sid") or a.get("access_mask") != b.get("access_mask"):
            so_heranca = False
            divergencias.append({"indice": i, "tipo": "sid_ou_mask",
                                 "a": a, "b": b})
        elif _flags_sem_heranca(int(a.get("ace_flags", 0))) != \
                _flags_sem_heranca(int(b.get("ace_flags", 0))):
            so_heranca = False
            divergencias.append({"indice": i, "tipo": "flags_nao_heranca",
                                 "a": a, "b": b})
        elif int(a.get("ace_flags", 0)) != int(b.get("ace_flags", 0)):
            divergencias.append({"indice": i, "tipo": "heranca_invertida",
                                 "a": a, "b": b})
    return {
        "divergente": bool(divergencias),
        "somente_heranca": bool(divergencias) and so_heranca,
        "divergencias": divergencias,
    }


# ==========================================================================
# Coleta de evidência (isolada do leitor de produção)
# ==========================================================================

def _detectar_reparse_point(caminho: str) -> tuple[bool, str]:
    """Verifica se o caminho é um reparse point (symlink, junção, mount point)."""
    try:
        st = os.lstat(str(caminho))
    except OSError:
        return True, "lstat_indisponivel"
    is_link = stat.S_ISLNK(st.st_mode)
    attr = getattr(st, "st_file_attributes", 0)
    reparse_attr = bool(attr & _FILE_ATTRIBUTE_REPARSE_POINT)
    if is_link or reparse_attr:
        return True, "reparse_point_detectado"
    return False, "sem_reparse"


def _contar_hardlinks(caminho: str) -> int:
    try:
        return int(os.lstat(str(caminho)).st_nlink)
    except OSError:
        return 0


def _hash_dacl_sintetico(aces: list[dict[str, Any]]) -> str:
    payload = json.dumps(aces, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def coletar_evidencia_acl(caminho_esperado: str,
                          handle_path: str,
                          *,
                          owner_sid: str,
                          group_sid: str | None,
                          aces: list[dict[str, Any]],
                          flags_dacl: int = 0,
                          baseline_owner_sid: str | None = None,
                          baseline_group_sid: str | None = None,
                          baseline_aces: list[dict[str, Any]] | None = None,
                          ) -> dict[str, Any]:
    """Monta o registro de evidência diagnóstica para um handle aberto.

    `handle_path` é o caminho obtido por QueryInformationWFile /
    GetFinalPathNameByHandle do handle realmente aberto; `caminho_esperado`
    é o caminho declarado pela configuração. A concordância é decidida por
    normalização 8.3 + CompareStringOrdinal, e hardlinks/reparse points são
    rejeitados. Em QUALQUER resultado, autoriza_acesso e aplicada_ao_leitor
    permanecem False (hardcoded).
    """
    reparse, motivo_reparse = _detectar_reparse_point(handle_path)
    caminho_ok = (not reparse) and _mesmo_path_normalizado(handle_path,
                                                           caminho_esperado)
    nlink = _contar_hardlinks(handle_path)

    leitura_5 = {
        "mascara": MASK_OWNER_DAACL,
        "owner_sid": owner_sid,
        "group_sid": None,  # não lido nesta máscara
        "dacl_hash": _hash_dacl_sintetico(aces),
        "flags_dacl": flags_dacl,
    }
    leitura_7 = {
        "mascara": MASK_OWNER_GROUP_DAACL,
        "owner_sid": owner_sid,
        "group_sid": group_sid,
        "dacl_hash": _hash_dacl_sintetico(aces),
        "flags_dacl": flags_dacl,
    }
    comparacao_5x7 = comparar_mascaras_5_e_7(leitura_5, leitura_7)

    analise_baseline: dict[str, Any] | None = None
    if baseline_aces is not None:
        diagnostico = mesmas_regras_diagnostico(aces, baseline_aces)
        analise_baseline = {
            **diagnostico,
            "baseline_owner_sid": baseline_owner_sid,
            "owner_atual_coincide": owner_sid == baseline_owner_sid,
            "nota": (
                "Diferenças restritas ao bit INHERITED_ACE (0x10) ou flags de "
                "propagação são registradas como artefato de herança para a "
                "evidência; o leitor de produção continua exigindo igualdade "
                "exata e estas informações não autorizam nada."
            ),
        }

    evidencia = {
        "versao": _EVIDENCIA_VERSAO,
        "papel": "diagnostico",
        "canonical_path": _normalizar_caminho_8_3(caminho_esperado),
        "handle_path_normalizado": (
            _normalizar_caminho_8_3(handle_path) if not reparse else None
        ),
        "caminho_coincide": caminho_ok,
        "reparse_point_detectado": reparse,
        "motivo_reparse": motivo_reparse,
        "nlink": nlink,
        "leitura_mascara_5": leitura_5,
        "leitura_mascara_7": leitura_7,
        "comparacao_5x7": comparacao_5x7,
        "analise_baseline": analise_baseline,
        # ==== LINHAS VERMELHAS: hardcoded False, SEMPRE. ====
        "autoriza_acesso": False,
        "aplicada_ao_leitor": False,
    }
    return evidencia


__all__ = [
    "INHERITED_ACE",
    "MASK_OWNER_DAACL",
    "MASK_OWNER_GROUP_DAACL",
    "coletar_evidencia_acl",
    "comparar_mascaras_5_e_7",
    "mesmas_regras_diagnostico",
]
