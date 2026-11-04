"""REGRESSÃO DE SEGURANÇA do leitor de produção (private_permissions.mesmas_regras).

Garante que o portão de acesso do leitor de produção CONTINUE exigindo
igualdade exata de ACEs, incluindo o bit INHERITED_ACE (0x10). Se alguém
alterar private_permissions.py para tolerar/normalizar bits de herança (por
exemplo "alinhando" o leitor com a tolerância do módulo de diagnóstico
windows_acl_evidence.py), estes testes DEVEM falhar.

Fixtures 100% sintéticas; nenhum dado real envolvido.
"""
import ast
import inspect

from conversor.adapters.private_permissions import (
    INHERITED_ACE,
    AclAce,
    mesmas_regras,
)


def _ace(sid: str = "S-1-5-21-SINTETICO", mask: int = 0x1F01FF, flags: int = 0):
    return AclAce(sid=sid, access_mask=mask, ace_flags=flags)


def test_bit_inherited_ace_constante():
    assert INHERITED_ACE == 0x10


def test_mesmas_regras_rejeita_diferenca_no_bit_0x10():
    base = _ace(flags=0x00)
    herdado = _ace(flags=INHERITED_ACE)
    assert mesmas_regras([base], [herdado]) is False
    assert mesmas_regras([herdado], [base]) is False


def test_mesmas_regras_rejeita_combinacoes_de_flags_de_heranca():
    # Qualquer diferença em QUALQUER bit de AceFlags (0x04, 0x08, 0x10...)
    # deve ser rejeitada — não apenas o 0x10 isolado.
    for flag in (0x01, 0x02, 0x04, 0x08, 0x10, 0x80):
        assert mesmas_regras([_ace(flags=0x00)], [_ace(flags=flag)]) is False


def test_mesmas_regras_aceita_igualdade_exata():
    a = _ace(flags=INHERITED_ACE)
    b = _ace(flags=INHERITED_ACE)
    assert mesmas_regras([a], [b]) is True
    assert mesmas_regras([], []) is True


def test_mesmas_regras_rejeita_quantidade_ou_sid_ou_mask_diferentes():
    assert mesmas_regras([_ace()], [_ace(), _ace()]) is False
    assert mesmas_regras([_ace(sid="S-A")], [_ace(sid="S-B")]) is False
    assert mesmas_regras([_ace(mask=0x1)], [_ace(mask=0x2)]) is False


def test_leitor_producao_nao_usa_normalizacao_de_diagnostico():
    """Barreira estrutural: private_permissions não pode importar nem delegar
    ao módulo de evidência diagnóstica, nem mascarar bits de herança."""
    from conversor.adapters import private_permissions as pp

    fonte = inspect.getsource(pp)
    arvore = ast.parse(fonte)

    imports = set()
    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any("windows_acl_evidence" in m for m in imports)

    nomes_usados = {node.id for node in ast.walk(arvore) if isinstance(node, ast.Name)}
    assert "mesmas_regras_diagnostico" not in nomes_usados
    assert "VALID_INHERITANCE_FLAGS" not in nomes_usados

    # A comparação de ace_flags deve ser por igualdade direta; nenhuma
    # operação BitXor/Invert (máscara do tipo `flags & ~MASCARA`) é permitida,
    # pois descartaria bits de herança como o INHERITED_ACE (0x10).
    for node in ast.walk(arvore):
        assert not isinstance(node, (ast.BitXor, ast.Invert)), (
            "private_permissions não pode normalizar/mascarar AceFlags"
        )
