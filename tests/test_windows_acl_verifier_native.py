"""DACLs reais de objetos vazios sintéticos; somente no job Windows.

Não elevar privilégios nem usar a ACL do objeto como binding esperado.
Falha de preparação em Windows é falha/pendência, nunca skip de segurança.
"""
import ctypes as ct
from dataclasses import dataclass, field
import json
import struct
import sys
from types import SimpleNamespace

import pytest

from conversor.adapters import windows_acl_verifier as av
from conversor.adapters.private_permissions import AclAce


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requer DACL nativa Windows real; pendente neste executor")


class _SECURITY_ATTRIBUTES(ct.Structure):
    _fields_ = [("length", av.DWORD), ("descriptor", av.PTR), ("inherit", av.BOOL)]


def _check(condition, code="FIXTURE_NATIVA_NAO_COMPROVADA"):
    if not condition:
        # Sem introspecção do pytest sobre SIDs, caminhos ou descritores reais.
        raise RuntimeError(code)


def _bind(library, name, result, arguments):
    function = getattr(library, name)
    function.restype, function.argtypes = result, arguments
    return function


def _apis_fixture():
    advapi = ct.WinDLL("advapi32", use_last_error=True)
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    return SimpleNamespace(
        OpenProcessToken=_bind(advapi, "OpenProcessToken", av.BOOL,
            [av.PTR, av.DWORD, ct.POINTER(av.PTR)]),
        GetTokenInformation=_bind(advapi, "GetTokenInformation", av.BOOL,
            [av.PTR, ct.c_int32, av.PTR, av.DWORD, ct.POINTER(av.DWORD)]),
        ConvertSidToStringSidW=_bind(advapi, "ConvertSidToStringSidW", av.BOOL,
            [av.PTR, ct.POINTER(av.PTR)]),
        ConvertStringSecurityDescriptorToSecurityDescriptorW=_bind(advapi,
            "ConvertStringSecurityDescriptorToSecurityDescriptorW", av.BOOL,
            [ct.c_wchar_p, av.DWORD, ct.POINTER(av.PTR), ct.POINTER(av.DWORD)]),
        SetSecurityInfo=_bind(advapi, "SetSecurityInfo", av.DWORD,
            [av.PTR, ct.c_int32, av.DWORD, av.PTR, av.PTR, av.PTR, av.PTR]),
        CreateFileW=_bind(kernel, "CreateFileW", av.PTR,
            [ct.c_wchar_p, av.DWORD, av.DWORD, ct.POINTER(_SECURITY_ATTRIBUTES),
             av.DWORD, av.DWORD, av.PTR]),
        CreateDirectoryW=_bind(kernel, "CreateDirectoryW", av.BOOL,
            [ct.c_wchar_p, ct.POINTER(_SECURITY_ATTRIBUTES)]),
        DeleteFileW=_bind(kernel, "DeleteFileW", av.BOOL, [ct.c_wchar_p]),
        RemoveDirectoryW=_bind(kernel, "RemoveDirectoryW", av.BOOL, [ct.c_wchar_p]),
    )


def _texto_sid(fixture_api, api, pointer):
    text = av.PTR()
    try:
        _check(fixture_api.ConvertSidToStringSidW(pointer, ct.byref(text)))
        _check(text.value is not None)
        return ct.wstring_at(text.value)
    finally:
        if text.value:
            _check(api.LocalFree(text) is None)


def _binding_token(fixture_api, api):
    token = av.PTR()
    try:
        _check(fixture_api.OpenProcessToken(api.GetCurrentProcess(), 0x0008, ct.byref(token)))
        needed = av.DWORD()
        result = fixture_api.GetTokenInformation(token, 1, None, 0, ct.byref(needed))
        _check(not result and ct.get_last_error() == 122 and 0 < needed.value <= 65536)
        buffer = ct.create_string_buffer(needed.value)
        _check(fixture_api.GetTokenInformation(token, 1, buffer, len(buffer), ct.byref(needed)))
        sid = ct.cast(buffer, ct.POINTER(av.PTR))[0]  # TOKEN_USER.Sid
        expected = _texto_sid(fixture_api, api, sid)
        elevation = av.DWORD()
        _check(fixture_api.GetTokenInformation(token, 20, ct.byref(elevation),
                                               ct.sizeof(elevation), ct.byref(needed)))
        _check(elevation.value in (0, 1))
        return expected, bool(elevation.value)
    finally:
        if token.value:
            _check(api.CloseHandle(token))


def _observacao_independente(handle, fixture_api, api):
    """Oracle usa conversão SID Win32; não chama o parser do verificador."""
    descriptor, owner, dacl = av.PTR(), av.PTR(), av.PTR()
    try:
        _check(api.GetSecurityInfo(handle, 1, 5, ct.byref(owner), None,
                                   ct.byref(dacl), None, ct.byref(descriptor)) == 0)
        _check(descriptor.value and api.IsValidSecurityDescriptor(descriptor))
        control, revision = av.WORD(), av.DWORD()
        _check(api.GetSecurityDescriptorControl(descriptor, ct.byref(control), ct.byref(revision)))
        _check(revision.value == 1, "FIXTURE_REVISAO_INVALIDA")
        present, defaulted, queried_dacl = av.BOOL(), av.BOOL(), av.PTR()
        _check(api.GetSecurityDescriptorDacl(descriptor, ct.byref(present),
            ct.byref(queried_dacl), ct.byref(defaulted)), "FIXTURE_CONSULTA_DACL_FALHOU")
        _check(present.value and control.value & av.SE_DACL_PRESENT and dacl.value
            and queried_dacl.value == dacl.value, "FIXTURE_DACL_AUSENTE_OU_NULA")
        _check(api.IsValidAcl(dacl), "FIXTURE_DACL_INVALIDA")
        observed_flags = {
            "se_dacl_protected": bool(control.value & av.SE_DACL_PROTECTED),
            "se_dacl_auto_inherited": bool(control.value & 0x0400),
            "se_dacl_auto_inherit_req": bool(control.value & 0x0100),
            "se_dacl_defaulted": bool(control.value & 0x0008),
            "dacl_defaulted_consulta": bool(defaulted.value),
        }
        _check(observed_flags["se_dacl_defaulted"] == observed_flags["dacl_defaulted_consulta"],
               "FIXTURE_DEFAULTED_INCOERENTE")
        info = av._ACL_SIZE_INFORMATION()
        _check(api.GetAclInformation(dacl, ct.byref(info), ct.sizeof(info), 2))
        _check(0 < info.count <= 8)
        aces = []
        for index in range(info.count):
            ace = av.PTR()
            _check(api.GetAce(dacl, index, ct.byref(ace)))
            kind, ace_flags, length, mask = struct.unpack("<BBHI", ct.string_at(ace.value, 8))
            _check(kind in (0, 1), "FIXTURE_TIPO_ACE_NAO_SUPORTADO")
            _check(length >= 16 and length % 4 == 0, "FIXTURE_TAMANHO_ACE_INVALIDO")
            _check(api.IsValidSid(ace.value+8), "FIXTURE_SID_INVALIDO")
            _check(length == 8+api.GetLengthSid(ace.value+8), "FIXTURE_TAMANHO_SID_INVALIDO")
            aces.append((kind, ace_flags, mask, _texto_sid(fixture_api, api, ace.value+8)))
        return _texto_sid(fixture_api, api, owner), aces, observed_flags
    finally:
        if descriptor.value:
            _check(api.LocalFree(descriptor) is None)


def _registrar_booleanos(request, etapa, results):
    _check(all(type(value) is bool for value in results.values()), "FIXTURE_DIAGNOSTICO_NAO_BOOLEANO")
    request.node.user_properties.extend((etapa+"_"+key, value) for key, value in results.items())
    print(json.dumps({"etapa": etapa, **results}, sort_keys=True))


def _registrar_observacao(request, etapa, observed, owner, expected):
    actual_owner, actual_aces, flags = observed
    # Somente booleanos e código de etapa; nunca owner, ACEs ou SD brutos.
    diagnostic = {"owner_confere": actual_owner == owner,
        "estrutura_acl_valida": True, "aces_esperadas_conferem": actual_aces == expected,
        "ace_explicita_esperada_presente": expected[0] in actual_aces, **flags}
    _registrar_booleanos(request, etapa, diagnostic)


def _desproteger_fixture_propria(handle, descriptor, fixture_api, api):
    """Só o handle do arquivo vazio recém-criado pelo caso negativo."""
    present, defaulted, dacl = av.BOOL(), av.BOOL(), av.PTR()
    _check(api.GetSecurityDescriptorDacl(descriptor, ct.byref(present),
        ct.byref(dacl), ct.byref(defaulted)), "FIXTURE_DACL_ORIGEM_INDISPONIVEL")
    _check(present.value and dacl.value and api.IsValidAcl(dacl), "FIXTURE_DACL_ORIGEM_INVALIDA")
    # SE_FILE_OBJECT; DACL_SECURITY_INFORMATION | UNPROTECTED_DACL_SECURITY_INFORMATION.
    # Nem owner/group/SACL são alterados. Status DWORD: apenas zero é sucesso.
    _check(fixture_api.SetSecurityInfo(handle, 1, 0x20000004, None, None, dacl, None) == 0,
           "FIXTURE_DESPROTECAO_FALHOU")


@dataclass(repr=False)
class _Caso:
    handle: int
    owner: str = field(repr=False)
    classe: av.ClasseObjeto
    politica: av.PoliticaPerfilE = field(repr=False)
    variante: str


@pytest.fixture
def caso_nativo(tmp_path, request):
    variante = request.param
    api, fa = av._API(), _apis_fixture()
    owner, elevado = _binding_token(fa, api)  # ANTES de criar/ler a ACL da fixture.
    request.node.user_properties.append(("contexto_token", "elevado" if elevado else "nao_elevado"))
    directory = variante == "diretorio"
    classe = av.ClasseObjeto.DIRETORIO if directory else av.ClasseObjeto.ARQUIVO
    mask = 0x001200A7 if directory else 0x00120081
    aces = f"(A;;0x{mask:08X};;;{owner})"
    if variante == "ace_extra": aces += f"(A;;0x00020080;;;{owner})"
    if variante == "herdada": aces = f"(A;ID;0x{mask:08X};;;{owner})"
    # Base explícita comprovável; o caso negativo é desprotegido depois, por handle.
    protected = "P"
    descriptor, size = av.PTR(), av.DWORD()
    handle, created = None, False
    path = tmp_path / "objeto_sintetico"
    try:
        _check(fa.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"O:{owner}D:{protected}{aces}", 1, ct.byref(descriptor), ct.byref(size)))
        input_control, input_revision = av.WORD(), av.DWORD()
        _check(api.GetSecurityDescriptorControl(descriptor, ct.byref(input_control),
            ct.byref(input_revision)), "FIXTURE_FLAGS_ENTRADA_INDISPONIVEIS")
        _check(input_revision.value == 1, "FIXTURE_REVISAO_ENTRADA_INVALIDA")
        _registrar_booleanos(request, "DESCRITOR_ENTRADA", {
            "se_dacl_protected": bool(input_control.value & av.SE_DACL_PROTECTED),
            "se_dacl_auto_inherited": bool(input_control.value & 0x0400),
            "se_dacl_auto_inherit_req": bool(input_control.value & 0x0100),
            "se_dacl_defaulted": bool(input_control.value & 0x0008),
        })
        attributes = _SECURITY_ATTRIBUTES(ct.sizeof(_SECURITY_ATTRIBUTES), descriptor, False)
        if directory:
            _check(fa.CreateDirectoryW(str(path), ct.byref(attributes)))
            created = True
        # WRITE_DAC é pedido somente para desproteger o objeto próprio do teste negativo.
        access = av.METADATA_ACCESS | (0x00040000 if variante == "nao_protegida" else 0)
        handle = fa.CreateFileW(str(path), access, 7,
            None if directory else ct.byref(attributes),
            3 if directory else 1, 0x02200000 if directory else 0x80, None)
        _check(handle not in (None, 0, av.PTR(-1).value))
        created = True
        expected = [(0, 0x10 if variante == "herdada" else 0, mask, owner)]
        if variante == "ace_extra": expected.append((0, 0, 0x00020080, owner))
        observed = _observacao_independente(handle, fa, api)
        _registrar_observacao(request, "APOS_CRIACAO", observed, owner, expected)
        _check(observed[0] == owner, "FIXTURE_OWNER_DIVERGENTE")
        if variante == "nao_protegida":
            # Omitir P na entrada SDDL não comprova o control efetivo do objeto.
            _check(observed[2]["se_dacl_protected"], "FIXTURE_BASE_NAO_PROTEGIDA")
            _check(observed[1] == expected, "FIXTURE_ACES_BASE_DIVERGENTES")
            _desproteger_fixture_propria(handle, descriptor, fa, api)
            observed = _observacao_independente(handle, fa, api)
            _registrar_observacao(request, "APOS_DESPROTECAO", observed, owner, expected)
            _check(observed[0] == owner, "FIXTURE_OWNER_DIVERGENTE")
            _check(not observed[2]["se_dacl_protected"], "FIXTURE_DACL_AINDA_PROTEGIDA")
            # A desproteção pode acrescentar ACEs herdadas do pai. Não removê-las.
            _check(expected[0] in observed[1], "FIXTURE_ACE_EXPLICITA_AUSENTE")
        else:
            _check(observed[2]["se_dacl_protected"], "FIXTURE_PROTECAO_DIVERGENTE")
            _check(observed[1] == expected, "FIXTURE_ACES_DIVERGENTES")
        yield _Caso(handle, owner, classe, av.PoliticaPerfilE(classe, (AclAce(owner, mask),)), variante)
    finally:
        # Só o objeto próprio do caso negativo é desprotegido; nunca alterar owner.
        if handle not in (None, 0, av.PTR(-1).value):
            _check(api.CloseHandle(handle))
        if descriptor.value:
            _check(api.LocalFree(descriptor) is None)
        if created:
            _check((fa.RemoveDirectoryW if directory else fa.DeleteFileW)(str(path)))


@pytest.mark.parametrize("caso_nativo", ["arquivo", "diretorio"], indirect=True)
def test_nativo_perfil_e_de_objeto_vazio(caso_nativo):
    c = caso_nativo
    result = av.verificar_acl_handle(c.handle, classe=c.classe, politica=c.politica, owner_esperado=c.owner)
    assert result.perfil_confere and not result.autoriza_acesso and not result.aplicada_ao_leitor


@pytest.mark.parametrize("caso_nativo,code", [
    ("nao_protegida", "DACL_NAO_PROTEGIDA"),
    ("ace_extra", "ACES_DIVERGENTES"),
    ("herdada", "ACES_DIVERGENTES"),
], indirect=["caso_nativo"])
def test_nativo_rejeita_divergencia_efetivamente_observada(caso_nativo, code):
    c = caso_nativo
    with pytest.raises(av.ErroVerificacaoACL, match="^"+code+"$"):
        av.verificar_acl_handle(c.handle, classe=c.classe, politica=c.politica, owner_esperado=c.owner)


@pytest.mark.parametrize("caso_nativo", ["arquivo"], indirect=True)
def test_nativo_owner_diverge_do_binding_explicito(caso_nativo):
    c = caso_nativo
    wrong = "S-1-5-21-101-202-303-404"
    _check(c.owner != wrong)
    policy = av.PoliticaPerfilE(c.classe, (AclAce(wrong, c.politica.aces[0].access_mask),))
    with pytest.raises(av.ErroVerificacaoACL, match="^OWNER_DIVERGENTE$"):
        av.verificar_acl_handle(c.handle, classe=c.classe, politica=policy, owner_esperado=wrong)
