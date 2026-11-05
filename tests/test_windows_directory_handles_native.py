"""Fixtures Windows reais e vazias. Preparação não comprovada é falha, não skip.

Pathnames só preparam/atacam fixtures; o adapter não os recebe. Nenhum privilégio
é habilitado. Symlink indisponível é pendência/falha de validação, nunca aprovação.
"""
import ctypes as ct
from dataclasses import dataclass, field
import json
import struct
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from conversor.adapters import windows_directory_handles as dh
from conversor.adapters import windows_acl_verifier as acl
from conversor.adapters.private_permissions import AclAce
from tests.test_windows_acl_verifier_native import (
    _SECURITY_ATTRIBUTES, _apis_fixture, _bind, _binding_token, _check,
    _observacao_independente,
)


pytestmark = pytest.mark.skipif(sys.platform != "win32",
    reason="Requer abertura relativa/DACL/filesystem Windows real; pendente neste executor")


def _extra():
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    return dict(
        info=_bind(kernel, "GetFileInformationByHandleEx", dh.BOOL,
            [dh.PTR, ct.c_int32, dh.PTR, dh.DWORD]),
        move=_bind(kernel, "MoveFileExW", dh.BOOL, [ct.c_wchar_p, ct.c_wchar_p, dh.DWORD]),
        symlink=_bind(kernel, "CreateSymbolicLinkW", ct.c_ubyte,
            [ct.c_wchar_p, ct.c_wchar_p, dh.DWORD]),
        ioctl=_bind(kernel, "DeviceIoControl", dh.BOOL, [dh.PTR, dh.DWORD, dh.PTR,
            dh.DWORD, dh.PTR, dh.DWORD, ct.POINTER(dh.DWORD), dh.PTR]),
        reopen=_bind(kernel, "ReOpenFile", dh.PTR, [dh.PTR, dh.DWORD, dh.DWORD, dh.DWORD]),
    )


def _sondar_reopen(handle, extra, api, flags):
    """Diagnóstico legado; jamais usa seu resultado para aprovar a cadeia."""
    own = extra["reopen"](handle, dh.ACCESS, dh.SHARE, flags)
    # Nenhuma outra chamada nativa, nem limpeza, antes da captura thread-local.
    error = ct.get_last_error() if own in (None, 0, dh.PTR(-1).value) else 0
    ok = dh._handle(own)
    try:
        return {"reopen_ok": ok, "winerror": error, "flags": flags}
    finally:
        if ok: _check(api.CloseHandle(own), "FIXTURE_SONDA_NAO_FECHADA")


def _registrar(request, stage, **values):
    _check(all(type(v) in (bool, int) for v in values.values()), "DIAGNOSTICO_NAO_SANITIZADO")
    request.node.user_properties.extend((stage+"_"+k, v) for k, v in values.items())
    print(json.dumps({"etapa": stage, **values}, sort_keys=True))


def _etapa(request, stage, operation):
    try:
        result = operation()
    except dh.ErroDiretorioWindows as error:
        _registrar(request, stage, sucesso=False,
            ntstatus=-1 if error.ntstatus is None else error.ntstatus,
            io_status=-1 if error.io_status is None else error.io_status,
            io_information=-1 if error.io_information is None else error.io_information)
        raise
    _registrar(request, stage, sucesso=True)
    return result


def _identidade_observada(handle, extra):
    identity, tag, standard = dh._FILE_ID_INFO(), dh._FILE_ATTRIBUTE_TAG_INFO(), dh._FILE_STANDARD_INFO()
    for kind, result in ((18, identity), (9, tag), (1, standard)):
        _check(extra["info"](handle, kind, ct.byref(result), ct.sizeof(result)),
            "FIXTURE_METADATA_NAO_COMPROVADA")
    _check(tag.FileAttributes & 0x10 and standard.Directory == 1
        and standard.NumberOfLinks == 1 and not standard.DeletePending,
        "FIXTURE_DIRETORIO_NAO_COMPROVADO")
    return dh.IdentidadeDiretorio(identity.VolumeSerialNumber, bytes(identity.FileId)), tag


@dataclass(repr=False)
class _Arvore:
    root: object = field(repr=False)
    child: object = field(repr=False)
    grandchild: object = field(repr=False)
    target: object = field(repr=False)
    handle: int = field(repr=False)
    owner: str = field(repr=False)
    policy: object = field(repr=False)
    identities: tuple = field(repr=False)
    api: object = field(repr=False)
    fa: object = field(repr=False)
    extra: dict = field(repr=False)
    descriptor: object = field(repr=False)
    unicode_identity: object = field(repr=False)
    request: object = field(repr=False)

    def chain(self):
        return _etapa(self.request, "ANCHOR", lambda: dh.CadeiaDiretorios.de_handle_validado(
            self.handle, identidade=self.identities[0], politica=self.policy, owner_esperado=self.owner))

    def open_child(self, chain):
        return _etapa(self.request, "FILHO", lambda: chain.abrir_componente(
            "filho", identidade=self.identities[1], politica=self.policy))

    def comprovar_cadeia(self):
        with self.chain() as chain:
            result = self.open_child(chain)
            _check(result.perfil_confere and not result.autoriza_acesso
                and not result.aplicada_ao_leitor, "PRECONDICAO_POSITIVA_FALHOU")
            _etapa(self.request, "NETO", lambda: chain.abrir_componente(
                "neto", identidade=self.identities[2], politica=self.policy))
        _check(_identidade_observada(self.handle, self.extra)[0] == self.identities[0],
            "ANCHOR_EMPRESTADO_NAO_PRESERVADO")


@pytest.fixture
def arvore(tmp_path, request):
    api, fa, extra = acl._API(), _apis_fixture(), _extra()
    owner, elevated = _binding_token(fa, api)
    request.node.user_properties.append(("fixture_token_elevado", elevated))
    # Só o owner da fixture pode preparar e tentar ataques. O adapter pede ACCESS,
    # nunca esse full-control sintético; isto não define política operacional.
    mask = 0x001F01FF
    policy = acl.PoliticaPerfilE(acl.ClasseObjeto.DIRETORIO, (AclAce(owner, mask),))
    descriptor, size, created, handles = dh.PTR(), dh.DWORD(), [], []
    root, target = tmp_path / "anchor", tmp_path / "alvo"
    child, grandchild = root / "filho", root / "filho" / "neto"
    try:
        _check(fa.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"O:{owner}D:P(A;;0x{mask:08X};;;{owner})", 1, ct.byref(descriptor), ct.byref(size)))
        attributes = _SECURITY_ATTRIBUTES(ct.sizeof(_SECURITY_ATTRIBUTES), descriptor, False)
        unicode_child = root / "ação-😀"
        for path in (root, child, grandchild, target, unicode_child):
            _check(fa.CreateDirectoryW(str(path), ct.byref(attributes)), "FIXTURE_CRIACAO_FALHOU")
            created.append(path)
        # Demonstra rename permitido pela fixture antes do bloqueio de share.
        moved = root / "filho_movido"
        _check(extra["move"](str(child), str(moved), 0), "FIXTURE_RENAME_BASE_FALHOU")
        _check(extra["move"](str(moved), str(child), 0), "FIXTURE_RENAME_RETORNO_FALHOU")
        identities = []
        for path in (root, child, grandchild, unicode_child):
            handle = fa.CreateFileW(str(path), dh.ACCESS, 7, None, 3, 0x02200000, None)
            _check(dh._handle(handle), "FIXTURE_ABERTURA_FALHOU")
            handles.append(handle)
            actual_owner, aces, flags = _observacao_independente(handle, fa, api)
            _check(actual_owner == owner, "FIXTURE_OWNER_DIVERGENTE")
            _check(flags["se_dacl_protected"] and aces == [(0, 0, mask, owner)],
                "FIXTURE_ACL_DIVERGENTE")
            identity, tag = _identidade_observada(handle, extra)
            _check(not tag.FileAttributes & 0x400 and tag.ReparseTag == 0,
                "FIXTURE_REPARSE_INESPERADO")
            identities.append(identity)
        _check(all(i.volume == identities[0].volume for i in identities), "FIXTURE_VOLUME_DIVERGENTE")
        # Só o anchor original permanece emprestado; demais handles de oracle fecham.
        for handle in handles[1:]:
            _check(api.CloseHandle(handle), "FIXTURE_FECHAMENTO_FALHOU")
        handles = handles[:1]
        for flags in (0x02200000, 0x02000000, 0x00200000, 0):
            _registrar(request, "REOPEN_LEGADO", **_sondar_reopen(handles[0], extra, api, flags))
        tree = _Arvore(root, child, grandchild, target, handles[0], owner, policy,
            tuple(identities[:3]), api, fa, extra, descriptor, identities[3], request)
        # Fora do pytest.raises dos casos negativos: uma precondição defeituosa
        # não pode ser confundida com o ataque que o teste pretende demonstrar.
        tree.comprovar_cadeia()
        yield tree
    finally:
        failures = False
        for handle in reversed(handles):
            if not api.CloseHandle(handle): failures = True
        if descriptor.value and api.LocalFree(descriptor) is not None: failures = True
        for path in reversed(created):
            if not fa.RemoveDirectoryW(str(path)): failures = True
        _check(not failures, "FIXTURE_LIMPEZA_FALHOU")


def test_nativo_abertura_relativa_unicode_e_cadeia(arvore):
    a = arvore
    a.comprovar_cadeia()
    with a.chain() as chain:
        result = a.open_child(chain)
        _check(result.perfil_confere and not result.autoriza_acesso
            and not result.aplicada_ao_leitor, "RESULTADO_NAO_DIAGNOSTICO")
        result = chain.abrir_componente("neto", identidade=a.identities[2], politica=a.policy)
        _check(result.perfil_confere, "CADEIA_NAO_COMPROVADA")
    # O anchor emprestado continua válido depois do fechamento da cadeia.
    _check(_identidade_observada(a.handle, a.extra)[0] == a.identities[0])


def test_nativo_componente_unicode_contado_em_utf16(arvore):
    a = arvore
    with a.chain() as chain:
        result = chain.abrir_componente("ação-😀", identidade=a.unicode_identity, politica=a.policy)
        _check(result.perfil_confere, "UNICODE_RELATIVO_NAO_COMPROVADO")


@pytest.mark.parametrize("target", ["root", "child", "grandchild"])
def test_nativo_share_impede_rename_de_todos_os_nos_vivos(arvore, target):
    a = arvore
    path = getattr(a, target)
    moved = path.with_name(path.name+"_trocado")
    _check(a.extra["move"](str(path), str(moved), 0), "FIXTURE_RENAME_ANTES_DO_LEASE_FALHOU")
    _check(a.extra["move"](str(moved), str(path), 0), "FIXTURE_RENAME_RETORNO_FALHOU")
    a.comprovar_cadeia()
    with a.chain() as chain:
        a.open_child(chain)
        chain.abrir_componente("neto", identidade=a.identities[2], politica=a.policy)
        def tentar_trocar():
            ok = a.extra["move"](str(path), str(moved), 0)
            return bool(ok), ct.get_last_error()
        with ThreadPoolExecutor(max_workers=1) as executor:
            ok, error = executor.submit(tentar_trocar).result(timeout=15)
        _check(not ok and error == 32, "FIXTURE_RENAME_NAO_BLOQUEADO_POR_SHARE")
    _check(a.extra["move"](str(path), str(moved), 0), "FIXTURE_RENAME_APOS_FECHAR_FALHOU")
    _check(a.extra["move"](str(moved), str(path), 0), "FIXTURE_RENAME_RETORNO_FALHOU")


@pytest.mark.parametrize("target", ["root", "child"])
def test_nativo_handle_de_escrita_preexistente_causa_recusa(arvore, target):
    a = arvore
    a.comprovar_cadeia()
    writer = a.fa.CreateFileW(str(getattr(a, target)), 2, 7, None, 3, 0x02200000, None)
    _check(dh._handle(writer), "FIXTURE_WRITER_NAO_COMPROVADO")
    try:
        with pytest.raises(dh.ErroDiretorioWindows,
                match="^ANCHOR_NAO_REABERTO$" if target == "root" else "^ABERTURA_RELATIVA_FALHOU$") as error:
            if target == "root":
                with a.chain():
                    _check(False, "ANCHOR_COM_CONFLITO_ACEITO")
            else:
                with a.chain() as chain:
                    a.open_child(chain)
        _check(error.value.ntstatus == 0xC0000043, "CONFLITO_DE_SHARE_NAO_COMPROVADO")
    finally:
        _check(a.api.CloseHandle(writer), "FIXTURE_WRITER_NAO_FECHADO")
    a.comprovar_cadeia()


def test_nativo_identidade_inesperada_e_substituicao_antes_de_abrir(arvore):
    a = arvore
    a.comprovar_cadeia()
    old = a.root / "filho_anterior"
    _check(a.extra["move"](str(a.child), str(old), 0), "FIXTURE_TROCA_NAO_COMPROVADA")
    attributes = _SECURITY_ATTRIBUTES(ct.sizeof(_SECURITY_ATTRIBUTES), a.descriptor, False)
    replacement = False
    try:
        _check(a.fa.CreateDirectoryW(str(a.child), ct.byref(attributes)), "FIXTURE_SUBSTITUTO_FALHOU")
        replacement = True
        handle = a.fa.CreateFileW(str(a.child), dh.ACCESS, 7, None, 3, 0x02200000, None)
        _check(dh._handle(handle))
        try:
            _check(_identidade_observada(handle, a.extra)[0] != a.identities[1],
                "FIXTURE_IDENTIDADE_NAO_MUDOU")
        finally:
            _check(a.api.CloseHandle(handle))
        with a.chain() as chain:
            with pytest.raises(dh.ErroDiretorioWindows, match="^IDENTIDADE_DIVERGENTE$"):
                a.open_child(chain)
    finally:
        if replacement: _check(a.fa.RemoveDirectoryW(str(a.child)))
        _check(a.extra["move"](str(old), str(a.child), 0))


@pytest.mark.parametrize("component", ["..", "a/b", "a\\b", "a:b", "a\0b", "\\??\\x", "NUL"])
def test_nativo_componentes_invalidos(arvore, component):
    a = arvore
    with a.chain() as chain:
        with pytest.raises(dh.ErroDiretorioWindows, match="COMPONENTE_INVALIDO"):
            chain.abrir_componente(component, identidade=a.identities[1], politica=a.policy)


@pytest.mark.parametrize("kind", ["junction", "symlink"])
@pytest.mark.parametrize("scope", ["anchor", "filho"])
def test_nativo_rejeita_reparse_confirmado_sem_seguir_alvo(arvore, kind, scope):
    a = arvore
    a.comprovar_cadeia()
    link = a.root / "desvio"
    created = False
    try:
        if kind == "symlink":
            _check(a.extra["symlink"](str(link), str(a.target), 3),
                "FIXTURE_SYMLINK_INDISPONIVEL_SEM_PRIVILEGIO")
            created = True
            expected_tag = 0xA000000C
        else:
            attributes = _SECURITY_ATTRIBUTES(ct.sizeof(_SECURITY_ATTRIBUTES), a.descriptor, False)
            _check(a.fa.CreateDirectoryW(str(link), ct.byref(attributes)))
            created = True
            handle = a.fa.CreateFileW(str(link), 0x40000000, 7, None, 3, 0x02200000, None)
            _check(dh._handle(handle))
            try:
                substitute = ("\\??\\"+str(a.target)).encode("utf-16-le")
                display = str(a.target).encode("utf-16-le")
                paths = substitute+b"\0\0"+display+b"\0\0"
                raw = struct.pack("<IHHHHHH", 0xA0000003, 8+len(paths), 0,
                    0, len(substitute), len(substitute)+2, len(display))+paths
                buffer, count = ct.create_string_buffer(raw), dh.DWORD()
                _check(a.extra["ioctl"](handle, 0x000900A4, buffer, len(raw), None, 0,
                    ct.byref(count), None), "FIXTURE_JUNCTION_NAO_CRIADA")
            finally:
                _check(a.api.CloseHandle(handle))
            expected_tag = 0xA0000003
        oracle = a.fa.CreateFileW(str(link), dh.ACCESS, 7, None, 3, 0x02200000, None)
        _check(dh._handle(oracle))
        try:
            identity, tag = _identidade_observada(oracle, a.extra)
            _check(tag.FileAttributes & 0x400 and tag.ReparseTag == expected_tag,
                "FIXTURE_REPARSE_NAO_COMPROVADO")
            if scope == "anchor":
                with pytest.raises(dh.ErroDiretorioWindows, match="^OBJETO_REPARSE$"):
                    with dh.CadeiaDiretorios.de_handle_validado(oracle, identidade=identity,
                            politica=a.policy, owner_esperado=a.owner):
                        _check(False, "REPARSE_ACEITO")
            else:
                with a.chain() as chain:
                    with pytest.raises(dh.ErroDiretorioWindows,
                            match="^ABERTURA_RELATIVA_FALHOU$|^OBJETO_REPARSE$") as error:
                        _etapa(a.request, "REPARSE", lambda: chain.abrir_componente(
                            "desvio", identidade=identity, politica=a.policy))
                    if str(error.value) == "ABERTURA_RELATIVA_FALHOU":
                        _check(error.value.ntstatus == 0xC000050B,
                            "ERRO_NAO_COMPROVA_REPARSE")  # STATUS_REPARSE_POINT_ENCOUNTERED
        finally:
            _check(a.api.CloseHandle(oracle))
    finally:
        if created: _check(a.fa.RemoveDirectoryW(str(link)), "FIXTURE_REPARSE_NAO_REMOVIDO")
