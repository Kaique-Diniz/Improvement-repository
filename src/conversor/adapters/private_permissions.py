"""Leitor de produção: verificação EXATA de permissões/ACEs da pasta privada.

LINHA VERMELHA DE SEGURANÇA:
    Este módulo é o portão de acesso do leitor de produção à pasta privada.
    A função mesmas_regras() exige IGUALDADE BINÁRIA EXATA entre as máscaras
    de ACEs, INCLUINDO o bit INHERITED_ACE (0x10). Ela NUNCA normaliza,
    tolera ou ignora qualquer bit de AceFlags — nem hoje, nem quando o módulo
    de diagnóstico (windows_acl_evidence.py) passou a ignorar artefatos de
    herança e caminhos 8.3 APENAS para reduzir falsos positivos em evidência
    diagnóstica. Qualquer tentativa de "alinhar" este leitor com a tolerância
    do diagnóstico deve ser recusada; há teste de regressão de segurança em
    tests/test_private_permissions_regression.py que falha se o comportamento
    exato for alterado.
"""
from dataclasses import dataclass


# Bit de flag do Windows que marca um ACE herdado (ACE_HEADER.AceFlags).
INHERITED_ACE = 0x10


@dataclass(frozen=True)
class AclAce:
    """Representação mínima e sintética de um ACE para comparação binária."""
    sid: str
    access_mask: int
    ace_flags: int = 0


def mesmas_regras(aces_esperados: list[AclAce], aces_lidos: list[AclAce]) -> bool:
    """Compara listas de ACEs com IGUALDADE EXATA (sid, access_mask, ace_flags).

    NÃO tolera divergências em nenhum bit de AceFlags — em particular o bit
    INHERITED_ACE (0x10). Um ACE herdado nunca equivale ao mesmo ACE não
    herdado. Esta é uma exigência absoluta do leitor de produção.
    """
    if len(aces_esperados) != len(aces_lidos):
        return False
    for esperado, lido in zip(aces_esperados, aces_lidos):
        if esperado.sid != lido.sid:
            return False
        if esperado.access_mask != lido.access_mask:
            return False
        if esperado.ace_flags != lido.ace_flags:
            return False
    return True
