"""Metadata/ABI sintéticas: estes testes não certificam DACL no Windows real."""
import ctypes as ct
from dataclasses import fields, replace
import struct
from types import SimpleNamespace

import pytest

from conversor.adapters import windows_acl_verifier as av
from conversor.adapters.private_permissions import AclAce


SID = "S-1-5-21-111-222-333-444"
OUTRO = "S-1-5-21-111-222-333-555"
MASK = 0x00120081


def sid_bytes(text):
    parts = [int(p) for p in text.split("-")[1:]]
    return bytes([parts[0], len(parts)-2]) + parts[1].to_bytes(6, "big") + struct.pack(
        "<" + "I"*(len(parts)-2), *parts[2:])


def ace_bytes(sid=SID, mask=MASK, flags=0, kind=0):
    raw_sid = sid_bytes(sid)
    return struct.pack("<BBHI", kind, flags, 8+len(raw_sid), mask)+raw_sid


def put(pointer, type_, value):
    ct.cast(pointer, ct.POINTER(type_))[0] = value


class API:
    def __init__(self, *, owner=SID, aces=None, protected=True, present=True,
                 null=False, directory=False):
        aces = [ace_bytes()] if aces is None else aces
        self.control = av.SE_SELF_RELATIVE
        self.control |= av.SE_DACL_PRESENT if present else 0
        self.control |= av.SE_DACL_PROTECTED if protected else 0
        self.owner_raw = sid_bytes(owner)
        self.owner_offset = 20
        self.dacl_offset = 20+len(self.owner_raw)
        self.ace_offsets = []
        offset = 8
        for ace in aces:
            self.ace_offsets.append(offset)
            offset += len(ace)
        self.acl_size = offset
        acl = struct.pack("<BBHHH", 2, 0, offset, len(aces), 0)+b"".join(aces)
        self.raw = struct.pack("<BBHIIII", 1, 0, self.control, 20, 0, 0,
                               0 if null or not present else self.dacl_offset)
        self.raw += self.owner_raw+acl
        self.buffer = ct.create_string_buffer(self.raw)
        self.start = ct.addressof(self.buffer)
        self.owner = self.start+20
        self.dacl = None if null or not present else self.start+self.dacl_offset
        self.count = len(aces)
        self.present = present
        self.directory = directory
        self.freed, self.closed = [], []
        self.duplicated = []

    def GetCurrentProcess(self):
        return ct.c_void_p(-1).value

    def DuplicateHandle(self, source_process, source, target_process, output, rights, inherit, options):
        assert source == 500 and rights == av.METADATA_ACCESS
        assert inherit is False and options == 0
        self.duplicated.append(source)
        put(output, av.PTR, 600)
        return 1

    def GetFileInformationByHandle(self, handle, output):
        assert handle.value == 600
        info = av._FILE_INFORMATION()
        info.attributes = 0x10 if self.directory else 0
        put(output, av._FILE_INFORMATION, info)
        return 1

    def GetSecurityInfo(self, handle, kind, flags, owner, group, dacl, sacl, sd):
        assert handle.value == 600 and kind == 1 and flags == 5
        assert group is None and sacl is None
        put(sd, av.PTR, self.start)
        put(owner, av.PTR, self.owner)
        put(dacl, av.PTR, self.dacl)
        return 0

    def IsValidSecurityDescriptor(self, pointer):
        return 1

    def GetSecurityDescriptorControl(self, pointer, control, revision):
        put(control, av.WORD, self.control)
        put(revision, av.DWORD, 1)
        return 1

    def GetSecurityDescriptorLength(self, pointer):
        return len(self.raw)

    def GetSecurityDescriptorDacl(self, pointer, present, dacl, defaulted):
        put(present, av.BOOL, self.present)
        put(dacl, av.PTR, self.dacl)
        put(defaulted, av.BOOL, 0)
        return 1

    def IsValidAcl(self, pointer):
        return 1

    def GetAclInformation(self, pointer, output, size, kind):
        assert size == 12 and kind == 2
        put(output, av._ACL_SIZE_INFORMATION, av._ACL_SIZE_INFORMATION(self.count, self.acl_size, 0))
        return 1

    def GetAce(self, pointer, index, output):
        put(output, av.PTR, self.dacl+self.ace_offsets[index])
        return 1

    def IsValidSid(self, pointer):
        return 1

    def GetLengthSid(self, pointer):
        return 8+4*ct.string_at(pointer, 2)[1]

    def LocalFree(self, pointer):
        self.freed.append(pointer.value)
        return None

    def CloseHandle(self, pointer):
        self.closed.append(pointer.value)
        return 1


@pytest.fixture
def policy():
    return av.PoliticaPerfilE(av.ClasseObjeto.ARQUIVO, (AclAce(SID, MASK),))


def verificar(monkeypatch, policy, api, **kwargs):
    monkeypatch.setattr(av, "_API", lambda: api)
    return av.verificar_acl_handle(500, classe=policy.classe, politica=policy,
                                   owner_esperado=kwargs.get("owner", SID))


def test_conformidade_nao_e_capacidade_e_libera_recursos(monkeypatch, policy):
    api = API()
    r = verificar(monkeypatch, policy, api)
    assert r.perfil_confere and not r.autoriza_acesso and not r.aplicada_ao_leitor
    assert {f.name for f in fields(r)} == {"classe", "perfil_confere", "autoriza_acesso", "aplicada_ao_leitor"}
    assert api.freed == [api.start] and api.closed == [600]
    assert SID not in repr(policy) and SID not in repr(r)


@pytest.mark.parametrize("params,code", [
    ({"owner": OUTRO}, "OWNER_DIVERGENTE"),
    ({"protected": False}, "DACL_NAO_PROTEGIDA"),
    ({"present": False}, "DACL_AUSENTE"),
    ({"null": True}, "DACL_NULA"),
    ({"aces": []}, "DACL_VAZIA"),
    ({"aces": [ace_bytes(), ace_bytes()]}, "ACES_DIVERGENTES"),
    ({"aces": [ace_bytes(mask=MASK+1)]}, "ACES_DIVERGENTES"),
    ({"aces": [ace_bytes(sid=OUTRO)]}, "ACES_DIVERGENTES"),
    ({"aces": [ace_bytes(flags=0x10)]}, "ACES_DIVERGENTES"),
    ({"aces": [ace_bytes(flags=0x01)]}, "ACES_DIVERGENTES"),
    ({"aces": [ace_bytes(kind=1)]}, "TIPO_ACE_NAO_SUPORTADO"),
    ({"aces": [ace_bytes(kind=5)]}, "TIPO_ACE_NAO_SUPORTADO"),
    ({"directory": True}, "CLASSE_DIVERGENTE"),
])
def test_divergencias_fechadas(monkeypatch, policy, params, code):
    api = API(**params)
    with pytest.raises(av.ErroVerificacaoACL, match="^"+code+"$") as error:
        verificar(monkeypatch, policy, api)
    assert SID not in str(error.value) and OUTRO not in str(error.value)
    assert api.closed == [600]
    assert api.freed == ([] if params.get("directory") else [api.start])


def test_classe_diretorio_usa_o_mesmo_handle(monkeypatch, policy):
    assert verificar(monkeypatch, replace(policy, classe=av.ClasseObjeto.DIRETORIO),
                     API(directory=True)).perfil_confere


@pytest.mark.parametrize("function", [
    "IsValidSecurityDescriptor", "GetSecurityDescriptorControl", "GetSecurityDescriptorDacl",
    "IsValidAcl", "GetAclInformation", "GetAce", "IsValidSid", "GetLengthSid",
])
def test_falha_auxiliar_libera_buffer_e_handle(monkeypatch, policy, function):
    api = API()
    setattr(api, function, lambda *args: 0)
    with pytest.raises(av.ErroVerificacaoACL):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


def test_erro_getsecurityinfo_com_buffer_ainda_libera(monkeypatch, policy):
    api = API()
    original = api.GetSecurityInfo
    def falhar(*args):
        original(*args)
        return 5
    api.GetSecurityInfo = falhar
    with pytest.raises(av.ErroVerificacaoACL, match="CONSULTA_SEGURANCA_FALHOU"):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


@pytest.mark.parametrize("function,expected_closed", [
    ("DuplicateHandle", []), ("GetFileInformationByHandle", [600]),
    ("GetSecurityInfo", [600]),
])
def test_falha_antes_de_alocar_descritor(monkeypatch, policy, function, expected_closed):
    api = API()
    setattr(api, function, lambda *args: 5 if function == "GetSecurityInfo" else 0)
    with pytest.raises(av.ErroVerificacaoACL):
        verificar(monkeypatch, policy, api)
    assert api.freed == [] and api.closed == expected_closed


def test_reparse_point_nao_atesta_classe_regular(monkeypatch, policy):
    api = API()
    def reparse(handle, output):
        info = av._FILE_INFORMATION(); info.attributes = 0x400
        put(output, av._FILE_INFORMATION, info)
        return 1
    api.GetFileInformationByHandle = reparse
    with pytest.raises(av.ErroVerificacaoACL, match="OBJETO_REPARSE"):
        verificar(monkeypatch, policy, api)
    assert api.freed == [] and api.closed == [600]


def test_excecao_na_primeira_liberacao_ainda_fecha_handle(monkeypatch, policy):
    api = API()
    def erro(pointer):
        api.freed.append(pointer.value)
        raise OSError("sentinela_de_erro")
    api.LocalFree = erro
    with pytest.raises(av.ErroVerificacaoACL, match="LIBERACAO_RECURSOS_FALHOU"):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


def test_descriptor_absoluto_nao_previsto_falha_fechada(monkeypatch, policy):
    api = API(); api.control &= ~av.SE_SELF_RELATIVE
    with pytest.raises(av.ErroVerificacaoACL, match="FORMATO_DESCRITOR_NAO_SUPORTADO"):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


@pytest.mark.parametrize("function", ["GetAclInformation", "GetAce"])
def test_api_nao_pode_entregar_faixa_ou_contagem_incoerente(monkeypatch, policy, function):
    api = API()
    def info(pointer, output, size, kind):
        put(output, av._ACL_SIZE_INFORMATION, av._ACL_SIZE_INFORMATION(api.count, api.acl_size+1, 0))
        return 1
    def ace(pointer, index, output):
        put(output, av.PTR, api.start+len(api.raw)+4)
        return 1
    setattr(api, function, info if function == "GetAclInformation" else ace)
    with pytest.raises(av.ErroVerificacaoACL):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


def test_excecao_nativa_nao_expoe_mensagem(monkeypatch, policy):
    api = API()
    def falhar(*args):
        raise OSError(SID+" SENTINELA_PRIVADA")
    api.GetSecurityInfo = falhar
    with pytest.raises(av.ErroVerificacaoACL, match="^API_WINDOWS_FALHOU$") as error:
        verificar(monkeypatch, policy, api)
    assert "SENTINELA" not in str(error.value) and api.closed == [600]


@pytest.mark.parametrize("free_error,close_error", [(True, False), (False, True), (True, True)])
def test_falha_de_limpeza_nao_retorna_conformidade(monkeypatch, policy, free_error, close_error):
    api = API()
    original_free, original_close = api.LocalFree, api.CloseHandle
    def liberar(pointer):
        original_free(pointer)
        return 123 if free_error else None
    def fechar(pointer):
        original_close(pointer)
        return 0 if close_error else 1
    api.LocalFree, api.CloseHandle = liberar, fechar
    with pytest.raises(av.ErroVerificacaoACL, match="LIBERACAO_RECURSOS_FALHOU"):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


@pytest.mark.parametrize("where,value", [(0, 9), (2, 3), (4, 0xFFFFFFFF), (16, 0xFFFFFFFC)])
def test_cabecalho_descritor_corrompido(monkeypatch, policy, where, value):
    api = API()
    raw = bytearray(api.raw)
    struct.pack_into("<B" if where == 0 else "<H" if where == 2 else "<I", raw, where, value)
    ct.memmove(api.start, bytes(raw), len(raw))
    with pytest.raises(av.ErroVerificacaoACL):
        verificar(monkeypatch, policy, api)
    assert api.freed == [api.start] and api.closed == [600]


@pytest.mark.parametrize("size", [0, 19, 1024*1024+1])
def test_comprimento_descritor_invalido(monkeypatch, policy, size):
    api = API(); api.GetSecurityDescriptorLength = lambda *args: size
    with pytest.raises(av.ErroVerificacaoACL, match="DESCRITOR_INVALIDO"):
        verificar(monkeypatch, policy, api)


@pytest.mark.parametrize("mutate", [
    lambda a: ct.memset(a.dacl+2, 0, 2),  # AclSize zero
    lambda a: ct.memset(a.dacl+8+2, 0, 2),  # AceSize zero
    lambda a: ct.memset(a.dacl+8+8+1, 255, 1),  # SID fora dos limites
])
def test_tamanhos_acl_ace_sid_nao_permitem_leitura_fora_da_faixa(monkeypatch, policy, mutate):
    api = API(); mutate(api)
    with pytest.raises(av.ErroVerificacaoACL):
        verificar(monkeypatch, policy, api)


def test_tipo_ace_validado_antes_do_comparador(monkeypatch, policy):
    def nao_comparar(*args):
        pytest.fail("Comparador não deve receber tipo ACE não suportado")
    monkeypatch.setattr(av, "mesmas_regras", nao_comparar)
    with pytest.raises(av.ErroVerificacaoACL, match="TIPO_ACE_NAO_SUPORTADO"):
        verificar(monkeypatch, policy, API(aces=[ace_bytes(kind=1)]))


def test_comparador_recebe_ordem_e_flags_sem_normalizacao(monkeypatch, policy):
    from conversor.adapters.private_permissions import mesmas_regras
    seen = []
    def comparar(expected, actual):
        seen.extend(actual)
        return mesmas_regras(expected, actual)
    monkeypatch.setattr(av, "mesmas_regras", comparar)
    with pytest.raises(av.ErroVerificacaoACL, match="ACES_DIVERGENTES"):
        verificar(monkeypatch, policy, API(aces=[ace_bytes(mask=1, flags=0x10), ace_bytes(mask=2)]))
    assert seen == [AclAce(SID, 1, 0x10), AclAce(SID, 2, 0)]


@pytest.mark.parametrize("handle", [None, 0, -1, True, ct.c_void_p(500), 2**(ct.sizeof(av.PTR)*8)-1])
def test_handle_invalido_nao_consulta_api(monkeypatch, policy, handle):
    monkeypatch.setattr(av, "_API", lambda: pytest.fail("API não deve ser carregada"))
    with pytest.raises(av.ErroVerificacaoACL, match="HANDLE_INVALIDO"):
        av.verificar_acl_handle(handle, classe=policy.classe, politica=policy, owner_esperado=SID)


@pytest.mark.parametrize("aces", [(), (AclAce(SID, MASK, 0x10),), (AclAce(OUTRO, MASK),),
    (AclAce(SID, 0),), (AclAce(SID, True),), (AclAce(SID, MASK), AclAce(SID, MASK))])
def test_politica_e_nao_inclui_ace_principal_ou_heranca_automaticamente(monkeypatch, policy, aces):
    monkeypatch.setattr(av, "_API", lambda: pytest.fail("API não deve ser carregada"))
    with pytest.raises(av.ErroVerificacaoACL, match="POLITICA_INVALIDA"):
        av.verificar_acl_handle(500, classe=policy.classe,
            politica=replace(policy, aces=aces), owner_esperado=SID)


def test_apis_indisponiveis_sem_fallback(monkeypatch, policy):
    monkeypatch.setattr(av, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(av.ErroVerificacaoACL, match="API_WINDOWS_INDISPONIVEL"):
        av.verificar_acl_handle(500, classe=policy.classe, politica=policy, owner_esperado=SID)


def test_assinaturas_abi_sem_long_do_host(monkeypatch):
    functions = {}
    def dll(name, **kwargs):
        assert name in {"advapi32", "kernel32"} and kwargs == {"use_last_error": True}
        class Library:
            def __getattr__(self, key):
                functions.setdefault(key, SimpleNamespace())
                return functions[key]
        return Library()
    monkeypatch.setattr(av, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(av.ct, "WinDLL", dll, raising=False)
    api = av._API()
    assert ct.sizeof(av.DWORD) == ct.sizeof(av.BOOL) == 4
    assert ct.sizeof(av.WORD) == 2
    assert ct.sizeof(av._FILE_INFORMATION) == 52
    assert av._FILE_INFORMATION.links.offset == 40
    assert ct.sizeof(av._ACL_SIZE_INFORMATION) == 12
    assert api.GetSecurityInfo.restype is av.DWORD and len(api.GetSecurityInfo.argtypes) == 8
    assert api.GetSecurityInfo.argtypes == [av.PTR, ct.c_int32, av.DWORD,
        ct.POINTER(av.PTR), ct.POINTER(av.PTR), ct.POINTER(av.PTR),
        ct.POINTER(av.PTR), ct.POINTER(av.PTR)]
    assert api.LocalFree.argtypes == [av.PTR] and api.LocalFree.restype is av.PTR
    assert api.DuplicateHandle.argtypes == [av.PTR, av.PTR, av.PTR,
        ct.POINTER(av.PTR), av.DWORD, av.BOOL, av.DWORD]


@pytest.mark.parametrize("failure", ["library", "symbol"])
def test_dll_ou_simbolo_ausente_falha_fechada(monkeypatch, failure):
    def dll(*args, **kwargs):
        if failure == "library": raise OSError("sem DLL")
        return SimpleNamespace()
    monkeypatch.setattr(av, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(av.ct, "WinDLL", dll, raising=False)
    with pytest.raises(av.ErroVerificacaoACL, match="API_WINDOWS_INDISPONIVEL"):
        av._API()
