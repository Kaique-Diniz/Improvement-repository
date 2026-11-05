"""Falhas/ABI sintéticas; não certificam filesystem ou compartilhamento Windows."""
import ctypes as ct
from dataclasses import fields
from types import SimpleNamespace

import pytest

from conversor.adapters import windows_directory_handles as dh
from conversor.adapters import windows_acl_verifier as acl
from conversor.adapters.private_permissions import AclAce


SID = "S-1-5-21-111-222-333-444"
POLICY = acl.PoliticaPerfilE(acl.ClasseObjeto.DIRETORIO, (AclAce(SID, dh.ACCESS),))
ROOT = dh.IdentidadeDiretorio(7, b"r"*16)
CHILD = dh.IdentidadeDiretorio(7, b"c"*16)


def put(pointer, type_, value):
    ct.cast(pointer, ct.POINTER(type_))[0] = value


class API:
    def __init__(self):
        self.identities = {100: ROOT, 200: ROOT, 300: CHILD, 400: CHILD}
        self.closed, self.opens, self.reopens, self.queries = [], [], [], []
        self.next_handle = 300
        self.attributes, self.tag, self.links, self.pending = 0x10, 0, 1, 0
        self.device, self.characteristics, self.fs, self.flags = 7, 0, "NTFS", 8
        self.acls = []

    def GetFileType(self, handle):
        return 1

    def GetFileInformationByHandleEx(self, handle, kind, output, size):
        self.queries.append((handle, kind))
        if kind == 9:
            result = dh._FILE_ATTRIBUTE_TAG_INFO(self.attributes, self.tag)
        elif kind == 1:
            result = dh._FILE_STANDARD_INFO(0, 0, self.links, self.pending, 1)
        else:
            assert kind == 18
            identity = self.identities[handle]
            result = dh._FILE_ID_INFO(identity.volume, (ct.c_ubyte*16)(*identity.file_id))
        assert size == ct.sizeof(result)
        put(output, type(result), result)
        return 1

    def NtQueryVolumeInformationFile(self, handle, ios, output, size, kind):
        assert handle != 100  # consultas NT somente nos handles síncronos próprios
        assert kind == 4 and size == 8
        put(output, dh._FILE_FS_DEVICE_INFORMATION,
            dh._FILE_FS_DEVICE_INFORMATION(self.device, self.characteristics))
        value = dh._IO_STATUS_BLOCK(); value.Status = 0; value.Information = 8
        put(ios, dh._IO_STATUS_BLOCK, value)
        return 0

    def GetVolumeInformationByHandleW(self, handle, name, length, serial, maximum, flags, fs, fs_length):
        assert name is None and length == 0 and fs_length == 32
        put(serial, dh.DWORD, 7); put(maximum, dh.DWORD, 255); put(flags, dh.DWORD, self.flags)
        fs.value = self.fs
        return 1

    def NtOpenFile(self, output, rights, attributes, ios, share, options):
        attrs = ct.cast(attributes, ct.POINTER(dh._OBJECT_ATTRIBUTES)).contents
        name = attrs.ObjectName.contents
        raw = ct.string_at(name.Buffer, name.Length)
        if raw:
            self.opens.append((attrs.RootDirectory, raw.decode("utf-16-le")))
            returned = self.next_handle
            self.next_handle += 100
        else:
            assert attrs.RootDirectory == 100
            self.reopens.append(attrs.RootDirectory)
            returned = 200
        assert attrs.Length == ct.sizeof(attrs) and name.MaximumLength == name.Length+2
        assert attrs.Attributes == 0x1040 and attrs.SecurityDescriptor is None
        assert attrs.SecurityQualityOfService is None
        assert ct.string_at(name.Buffer+name.Length, 2) == b"\0\0"
        assert rights == dh.ACCESS and share == 1 and options == 0x00200021
        assert ct.cast(ios, ct.POINTER(dh._IO_STATUS_BLOCK)).contents.Status == 0x103
        put(output, dh.PTR, returned)
        result = dh._IO_STATUS_BLOCK(); result.Status = 0; result.Information = 1
        put(ios, dh._IO_STATUS_BLOCK, result)
        return 0

    def CloseHandle(self, handle):
        self.closed.append(handle)
        assert handle != 100
        return 1

    def verificar(self, handle, *, classe, politica, owner_esperado):
        assert classe == acl.ClasseObjeto.DIRETORIO and politica == POLICY and owner_esperado == SID
        self.acls.append(handle)
        return acl.ConformidadeACL(classe)


@pytest.fixture
def api(monkeypatch):
    fake = API()
    monkeypatch.setattr(dh, "_API", lambda: fake)
    monkeypatch.setattr(acl, "verificar_acl_handle", fake.verificar)
    return fake


def chain():
    return dh.CadeiaDiretorios.de_handle_validado(100, identidade=ROOT,
        politica=POLICY, owner_esperado=SID)


def open_child(c, nome="filho", identity=CHILD):
    return c.abrir_componente(nome, identidade=identity, politica=POLICY)


def test_cadeia_viva_relativa_sem_conteudo_e_sem_expor_handle(api):
    with chain() as c:
        result = open_child(c, "ação-😀")
        assert result.perfil_confere and not result.autoriza_acesso and not result.aplicada_ao_leitor
        assert {f.name for f in fields(result)} == {"perfil_confere", "autoriza_acesso", "aplicada_ao_leitor"}
        assert not hasattr(c, "handle") and not hasattr(c, "read") and not hasattr(c, "write")
        assert api.closed == []
        open_child(c, "neto")
        assert api.opens == [(200, "ação-😀"), (300, "neto")]
        assert {200, 300, 400} <= set(api.acls)
        assert SID not in repr(c) and "ação" not in repr(c)
        assert SID not in repr(ROOT) and "rrrr" not in repr(ROOT)
    assert api.closed == [400, 300, 200]
    c.fechar()
    assert api.closed == [400, 300, 200]


@pytest.mark.parametrize("name", ["", ".", "..", "../a", "a/b", "a\\b", "\\??\\a",
    "\\\\?\\C:\\a", "x:y", "a\0b", "a.", "a ", "a\n", 'a"', "a*", "a?", "a<", "a>", "a|",
    "NUL", "nul.txt", "CON", "AUX.x", "PRN", "CLOCK$", "CONIN$", "CONOUT$", "COM1",
    "LPT9.txt", "COM¹", "LPT²", "COM³", "CON .txt", "x"*256, "😀"*128, "\ud800", None, 7])
def test_componentes_invalidos_nao_chegam_a_api(api, name):
    c = chain()
    with pytest.raises(dh.ErroDiretorioWindows, match="^COMPONENTE_INVALIDO$"):
        open_child(c, name)
    assert not api.opens and api.closed == [200]


@pytest.mark.parametrize("name", [".fixture", "com10", "auxiliar", "a b", "é", "😀", "x"*255, "😀"*127+"x"])
def test_componente_utf16_contado_em_bytes(api, name):
    with chain() as c:
        open_child(c, name)
    assert api.opens == [(200, name)]


@pytest.mark.parametrize("identity", [None, dh.IdentidadeDiretorio(0, b"a"*16),
    dh.IdentidadeDiretorio(True, b"a"*16), dh.IdentidadeDiretorio(7, b"a"),
    dh.IdentidadeDiretorio(7, bytes(16)), dh.IdentidadeDiretorio(7, bytearray(b"a"*16))])
def test_binding_identidade_invalido_antes_de_reabrir(api, identity):
    with pytest.raises(dh.ErroDiretorioWindows, match="IDENTIDADE_INVALIDA"):
        dh.CadeiaDiretorios.de_handle_validado(100, identidade=identity, politica=POLICY, owner_esperado=SID)
    assert not api.reopens and not api.closed


def test_politica_nao_e_inferida_do_objeto(api):
    with pytest.raises(dh.ErroDiretorioWindows, match="BINDING_INVALIDO"):
        dh.CadeiaDiretorios.de_handle_validado(100, identidade=ROOT, politica=POLICY, owner_esperado="S-1-5-18")
    assert not api.queries


@pytest.mark.parametrize("field,value,code", [
    ("attributes", 0x410, "OBJETO_REPARSE"), ("tag", 0xA000000C, "OBJETO_REPARSE"),
    ("attributes", 0, "NAO_DIRETORIO"), ("links", 2, "OBJETO_INSTAVEL"),
    ("pending", 1, "OBJETO_INSTAVEL"), ("device", 8, "VOLUME_NAO_SUPORTADO"),
    ("characteristics", 0x10, "VOLUME_NAO_SUPORTADO"),
    ("characteristics", 1, "VOLUME_NAO_SUPORTADO"), ("fs", "ReFS", "FILESYSTEM_NAO_SUPORTADO"),
    ("fs", "FAT32", "FILESYSTEM_NAO_SUPORTADO"), ("flags", 0, "FILESYSTEM_NAO_SUPORTADO"),
])
def test_tipo_reparse_hardlink_volume_e_fs_falham_fechados(api, field, value, code):
    c = chain()
    setattr(api, field, value)
    with pytest.raises(dh.ErroDiretorioWindows, match="^"+code+"$"):
        open_child(c)
    assert api.closed == [200] and not api.opens


@pytest.mark.parametrize("where", [100, 200, 300])
def test_identidade_divergente_nao_e_aceita(api, where):
    api.identities[where] = dh.IdentidadeDiretorio(7, b"x"*16)
    with pytest.raises(dh.ErroDiretorioWindows, match="IDENTIDADE_DIVERGENTE"):
        with chain() as c:
            open_child(c)
    assert api.closed == ([] if where == 100 else [200] if where == 200 else [300, 200])


def test_volume_divergente_antes_da_abertura(api):
    c = chain()
    with pytest.raises(dh.ErroDiretorioWindows, match="VOLUME_DIVERGENTE"):
        open_child(c, identity=dh.IdentidadeDiretorio(8, CHILD.file_id))
    assert api.closed == [200] and not api.opens


def test_alteracao_de_ancestral_durante_abertura_fecha_tudo(api):
    c = chain()
    original = api.NtOpenFile
    def race(*args):
        status = original(*args)
        api.identities[200] = CHILD
        return status
    api.NtOpenFile = race
    with pytest.raises(dh.ErroDiretorioWindows, match="IDENTIDADE_DIVERGENTE"):
        open_child(c)
    assert api.closed == [300, 200]


def test_identidade_muda_entre_consulta_e_acl(api):
    c = chain()
    original = api.verificar
    def race(*args, **kwargs):
        result = original(*args, **kwargs)
        api.identities[200] = CHILD
        return result
    dh.acl.verificar_acl_handle = race  # restaurado pela fixture monkeypatch
    with pytest.raises(dh.ErroDiretorioWindows, match="IDENTIDADE_DIVERGENTE"):
        open_child(c)
    assert api.closed == [200]


@pytest.mark.parametrize("status,io_status,info", [(0x103, 0, 1), (-1073741757, 0, 1),
    (0, -1, 1), (0, 0, 0), (0, 0, 2)])
def test_status_pendente_erro_share_ou_ios_incoerente_fecha_saida(api, status, io_status, info):
    c = chain()
    original = api.NtOpenFile
    def fail(*args):
        original(*args)
        result = dh._IO_STATUS_BLOCK(); result.Status = io_status; result.Information = info
        put(args[3], dh._IO_STATUS_BLOCK, result)
        return status
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="ABERTURA_RELATIVA_FALHOU"):
        open_child(c)
    assert api.closed == [300, 200]


@pytest.mark.parametrize("where", ["NtOpenFile", "NtAnchor", "GetFileInformationByHandleEx",
    "NtQueryVolumeInformationFile", "GetVolumeInformationByHandleW", "GetFileType"])
def test_api_falha_sem_vazar_mensagem_nativa(api, where):
    def fail(*args):
        raise OSError(SID+" SENTINELA_PRIVADA")
    c = chain() if where == "NtOpenFile" else None
    setattr(api, "NtOpenFile" if where == "NtAnchor" else where, fail)
    with pytest.raises(dh.ErroDiretorioWindows, match="^API_WINDOWS_FALHOU$") as error:
        open_child(c) if c else chain()
    assert "SENTINELA" not in str(error.value) and SID not in str(error.value)
    assert api.closed == ([200] if c or where in (
        "NtQueryVolumeInformationFile", "GetVolumeInformationByHandleW") else [])


def test_acl_erro_preserva_comparador_e_falha_fechada(api, monkeypatch):
    def fail(*args, **kwargs):
        raise acl.ErroVerificacaoACL("ACES_DIVERGENTES")
    monkeypatch.setattr(acl, "verificar_acl_handle", fail)
    with pytest.raises(dh.ErroDiretorioWindows, match="ACL_NAO_COMPROVADA"):
        chain()
    assert api.closed == [200]


@pytest.mark.parametrize("field", ["perfil_confere", "autoriza_acesso", "aplicada_ao_leitor"])
def test_resultado_acl_inesperado_nao_concede_capacidade(api, monkeypatch, field):
    values = dict(perfil_confere=True, autoriza_acesso=False, aplicada_ao_leitor=False)
    values[field] = not values[field]
    monkeypatch.setattr(acl, "verificar_acl_handle", lambda *a, **k: SimpleNamespace(**values))
    with pytest.raises(dh.ErroDiretorioWindows, match="ACL_NAO_COMPROVADA"):
        chain()
    assert api.closed == [200]


def test_erro_nativo_apos_preencher_handle_ainda_fecha(api):
    c = chain()
    original = api.NtOpenFile
    def fail(*args):
        original(*args)
        raise OSError("sem detalhes")
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="API_WINDOWS_FALHOU"):
        open_child(c)
    assert api.closed == [300, 200]


def test_falha_de_fechamento_tenta_todos_e_permite_repetir(api):
    c = chain(); open_child(c)
    original = api.CloseHandle
    def fail(handle):
        original(handle)
        if handle == 300:
            raise OSError("erro")
        return 1
    api.CloseHandle = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="FECHAMENTO_FALHOU"):
        c.fechar()
    assert api.closed == [300, 200]
    api.CloseHandle = original
    c.fechar()
    assert api.closed == [300, 200, 300]


def test_erro_no_corpo_e_objeto_fechado_nao_podem_reabrir(api):
    with pytest.raises(RuntimeError, match="SINTETICO"):
        with chain() as c:
            open_child(c)
            raise RuntimeError("SINTETICO")
    assert api.closed == [300, 200]
    with pytest.raises(dh.ErroDiretorioWindows, match="CADEIA_FECHADA"):
        open_child(c)
    assert len(api.opens) == 1


@pytest.mark.parametrize("value", [None, 0, dh.PTR(-1).value])
def test_reopen_handle_invalido_nunca_fecha_anchor(api, value):
    def invalid(output, *args):
        put(output, dh.PTR, value)
        return 0
    api.NtOpenFile = invalid
    with pytest.raises(dh.ErroDiretorioWindows, match="ANCHOR_NAO_REABERTO"):
        chain()
    assert not api.closed


@pytest.mark.parametrize("value", [None, 0, dh.PTR(-1).value])
def test_saida_ntopen_handle_invalido_fecha_apenas_cadeia(api, value):
    c = chain()
    def fail(output, *args):
        put(output, dh.PTR, value)
        return 0
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="ABERTURA_RELATIVA_FALHOU"):
        open_child(c)
    assert api.closed == [200]


@pytest.mark.parametrize("status,ios_status,size", [(-1, 0, 8), (0x103, 0, 8), (0, -1, 8), (0, 0, 0), (0, 0, 9)])
def test_volume_nt_status_e_tamanho_sao_verificados(api, status, ios_status, size):
    def fail(handle, ios, *args):
        value = dh._IO_STATUS_BLOCK(); value.Status = ios_status; value.Information = size
        put(ios, dh._IO_STATUS_BLOCK, value)
        return status
    api.NtQueryVolumeInformationFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="VOLUME_NAO_COMPROVADO"):
        chain()
    assert api.closed == [200]


@pytest.mark.parametrize("kind", [1, 9, 18])
def test_getinfo_retorno_zero_nao_interpreta_buffer(api, kind):
    original = api.GetFileInformationByHandleEx
    def fail(handle, query, *args):
        return 0 if query == kind else original(handle, query, *args)
    api.GetFileInformationByHandleEx = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="METADATA_INDISPONIVEL"):
        chain()
    assert not api.reopens and not api.closed


def test_objeto_filho_reparse_depois_da_abertura_nao_passa_por_acl(api):
    c = chain()
    original = api.NtOpenFile
    def reparse(*args):
        result = original(*args)
        api.attributes = 0x410
        return result
    api.NtOpenFile = reparse
    with pytest.raises(dh.ErroDiretorioWindows, match="OBJETO_REPARSE"):
        open_child(c)
    assert api.closed == [300, 200] and 300 not in api.acls


def test_acl_de_ancestral_alterada_impede_continuacao(api, monkeypatch):
    c = chain(); open_child(c)
    def invalid(*args, **kwargs):
        raise acl.ErroVerificacaoACL("ACES_DIVERGENTES")
    monkeypatch.setattr(acl, "verificar_acl_handle", invalid)
    with pytest.raises(dh.ErroDiretorioWindows, match="ACL_NAO_COMPROVADA"):
        open_child(c, "neto")
    assert api.closed == [300, 200] and len(api.opens) == 1


def test_excecao_intermediaria_fecha_filho_e_todos_os_ancestrais(api):
    c = chain(); open_child(c)
    original = api.NtOpenFile
    def invalid(*args):
        original(*args)
        raise OSError("SENTINELA_PRIVADA")
    api.NtOpenFile = invalid
    with pytest.raises(dh.ErroDiretorioWindows, match="API_WINDOWS_FALHOU"):
        open_child(c, "neto")
    assert api.closed == [400, 300, 200]


def test_assinaturas_e_layout_windows(monkeypatch):
    functions = {}
    def dll(name, **kwargs):
        assert name in ("ntdll", "kernel32") and kwargs == {"use_last_error": True}
        class Library:
            def __getattr__(self, key):
                return functions.setdefault(key, SimpleNamespace())
        return Library()
    monkeypatch.setattr(dh, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(ct, "WinDLL", dll, raising=False)
    native = dh._API()
    assert ct.sizeof(dh.NTSTATUS) == ct.sizeof(dh.DWORD) == 4
    assert ct.sizeof(dh._FILE_ID_INFO) == 24 and dh._FILE_ID_INFO.FileId.offset == 8
    assert ct.sizeof(dh._FILE_ATTRIBUTE_TAG_INFO) == 8
    assert ct.sizeof(dh._FILE_STANDARD_INFO) == 24
    assert dh._FILE_STANDARD_INFO.DeletePending.offset == 20
    assert ct.sizeof(dh._IO_STATUS_BLOCK) == 2*ct.sizeof(dh.PTR)
    assert ct.sizeof(dh._UNICODE_STRING) == (16 if ct.sizeof(dh.PTR) == 8 else 8)
    assert ct.sizeof(dh._OBJECT_ATTRIBUTES) == (48 if ct.sizeof(dh.PTR) == 8 else 24)
    assert native.NtOpenFile.restype is dh.NTSTATUS
    assert native.NtOpenFile.argtypes == [ct.POINTER(dh.PTR), dh.DWORD,
        ct.POINTER(dh._OBJECT_ATTRIBUTES), ct.POINTER(dh._IO_STATUS_BLOCK), dh.DWORD, dh.DWORD]
    assert not hasattr(native, "ReOpenFile")
    assert not dh.ACCESS & (1 | 2 | 4 | 0x10000 | 0x40000 | 0x80000)
    assert not dh.OPTIONS & (0x1000 | 0x4000)  # sem DELETE_ON_CLOSE/backup intent


@pytest.mark.parametrize("failure", ["platform", "dll", "symbol"])
def test_api_indisponivel_sem_fallback(monkeypatch, failure):
    monkeypatch.setattr(dh, "sys", SimpleNamespace(platform="linux" if failure == "platform" else "win32"))
    def dll(*args, **kwargs):
        if failure == "dll": raise OSError("erro")
        return SimpleNamespace()
    monkeypatch.setattr(ct, "WinDLL", dll, raising=False)
    with pytest.raises(dh.ErroDiretorioWindows, match="API_WINDOWS_INDISPONIVEL"):
        dh._API()


@pytest.mark.parametrize("status,io_status,info", [(-1073741757, -1073741757, 0),
    (-1073741790, -1073741790, 0), (0x103, 0x103, 0), (0, -1, 1), (0, 0, 2)])
def test_anchor_status_nao_e_confundido_com_filhos_e_libera_saida(api, status, io_status, info):
    def fail(output, rights, attrs, ios, share, options):
        assert ct.cast(attrs, ct.POINTER(dh._OBJECT_ATTRIBUTES)).contents.ObjectName.contents.Length == 0
        put(output, dh.PTR, 200)
        result = dh._IO_STATUS_BLOCK(); result.Status = io_status; result.Information = info
        put(ios, dh._IO_STATUS_BLOCK, result)
        return status
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="^ANCHOR_NAO_REABERTO$") as error:
        chain()
    assert error.value.ntstatus == status & 0xFFFFFFFF
    assert error.value.io_status == io_status & 0xFFFFFFFF
    assert error.value.io_information == info
    assert api.closed == [200] and not api.opens


def test_anchor_excecao_apos_alocacao_fecha_saida(api):
    original = api.NtOpenFile
    def fail(*args):
        original(*args)
        raise OSError(SID)
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="^API_WINDOWS_FALHOU$"):
        chain()
    assert api.closed == [200] and not api.opens


def test_anchor_identidade_e_acl_sao_revalidados_apos_nova_abertura(api):
    original = api.NtOpenFile
    def fail(*args):
        status = original(*args)
        api.identities[200] = CHILD
        return status
    api.NtOpenFile = fail
    with pytest.raises(dh.ErroDiretorioWindows, match="IDENTIDADE_DIVERGENTE"):
        chain()
    assert api.closed == [200] and not api.acls


@pytest.mark.parametrize("flags", [0x02200000, 0x02000000, 0x00200000, 0])
@pytest.mark.parametrize("valid", [False, True])
def test_sonda_legada_captura_last_error_antes_de_qualquer_limpeza(monkeypatch, flags, valid):
    from tests.test_windows_directory_handles_native import _sondar_reopen
    events = []
    def reopen(handle, rights, share, actual_flags):
        assert handle == 100 and rights == dh.ACCESS and share == 1 and actual_flags == flags
        events.append("reopen")
        return 200 if valid else dh.PTR(-1).value
    def last_error():
        events.append("last_error")
        return 5
    def close(handle):
        assert handle == 200
        events.append("close")
        return 1
    monkeypatch.setattr(ct, "get_last_error", last_error, raising=False)
    result = _sondar_reopen(100, {"reopen": reopen}, SimpleNamespace(CloseHandle=close), flags)
    assert result == {"reopen_ok": valid, "winerror": 0 if valid else 5, "flags": flags}
    assert events == (["reopen", "close"] if valid else ["reopen", "last_error"])


def test_diagnostico_nt_registra_apenas_codigos_numericos(monkeypatch, capsys):
    from tests.test_windows_directory_handles_native import _etapa
    request = SimpleNamespace(node=SimpleNamespace(user_properties=[]))
    def fail():
        raise dh.ErroDiretorioWindows("ANCHOR_NAO_REABERTO", ntstatus=-1073741757,
            io_status=-1073741757, io_information=0)
    with pytest.raises(dh.ErroDiretorioWindows):
        _etapa(request, "ANCHOR", fail)
    text = capsys.readouterr().out
    assert SID not in text and "ntstatus" in text and "3221225539" in text
    assert all(type(value) in (bool, int) for _, value in request.node.user_properties)
