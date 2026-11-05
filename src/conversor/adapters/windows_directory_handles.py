"""Cadeia isolada de diretórios sintéticos: metadata, nunca conteúdo/autorização.

O anchor emprestado e as identidades esperadas vêm de binding confiável externo.
Não comprova ancestrais anteriores ao anchor, SID operacional ou token/elevação.
Somente NTFS local não removível segundo as APIs; nenhuma abertura por pathname.
Use como context manager ou chame fechar(). Não expõe os handles próprios.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass, field
import re
import sys
import threading

from . import windows_acl_verifier as acl


DWORD, BOOL, PTR = acl.DWORD, acl.BOOL, acl.PTR
NTSTATUS = ct.c_int32
ACCESS = acl.METADATA_ACCESS | 0x20 | 0x100000  # TRAVERSE | SYNCHRONIZE
SHARE = 1  # FILE_SHARE_READ; nem WRITE nem DELETE
OPTIONS = 0x00000001 | 0x00000020 | 0x00200000
OBJECT_FLAGS = 0x40 | 0x1000  # CASE_INSENSITIVE | DONT_REPARSE; não INHERIT


class _UNICODE_STRING(ct.Structure):
    _fields_ = [("Length", ct.c_uint16), ("MaximumLength", ct.c_uint16), ("Buffer", PTR)]


class _OBJECT_ATTRIBUTES(ct.Structure):
    _fields_ = [("Length", DWORD), ("RootDirectory", PTR),
                ("ObjectName", ct.POINTER(_UNICODE_STRING)), ("Attributes", DWORD),
                ("SecurityDescriptor", PTR), ("SecurityQualityOfService", PTR)]


class _STATUS(ct.Union):
    _fields_ = [("Status", NTSTATUS), ("Pointer", PTR)]


class _IO_STATUS_BLOCK(ct.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("u", _STATUS), ("Information", ct.c_size_t)]


class _FILE_ID_INFO(ct.Structure):
    _fields_ = [("VolumeSerialNumber", ct.c_uint64), ("FileId", ct.c_ubyte * 16)]


class _FILE_ATTRIBUTE_TAG_INFO(ct.Structure):
    _fields_ = [("FileAttributes", DWORD), ("ReparseTag", DWORD)]


class _FILE_STANDARD_INFO(ct.Structure):
    _fields_ = [("AllocationSize", ct.c_int64), ("EndOfFile", ct.c_int64),
                ("NumberOfLinks", DWORD), ("DeletePending", ct.c_ubyte),
                ("Directory", ct.c_ubyte)]


class _FILE_FS_DEVICE_INFORMATION(ct.Structure):
    _fields_ = [("DeviceType", DWORD), ("Characteristics", DWORD)]


class ErroDiretorioWindows(ValueError):
    """Apenas códigos fixos; sem nome, SID, identidade ou mensagem nativa."""


def _exigir(value, code):
    if not value:
        raise ErroDiretorioWindows(code)


class _API:
    def __init__(self):
        _exigir(sys.platform == "win32", "API_WINDOWS_INDISPONIVEL")
        try:
            kernel = ct.WinDLL("kernel32", use_last_error=True)
            native = ct.WinDLL("ntdll", use_last_error=True)
            signatures = {
                "ReOpenFile": (kernel, PTR, [PTR, DWORD, DWORD, DWORD]),
                "NtOpenFile": (native, NTSTATUS, [ct.POINTER(PTR), DWORD,
                    ct.POINTER(_OBJECT_ATTRIBUTES), ct.POINTER(_IO_STATUS_BLOCK), DWORD, DWORD]),
                "NtQueryVolumeInformationFile": (native, NTSTATUS, [PTR,
                    ct.POINTER(_IO_STATUS_BLOCK), PTR, DWORD, ct.c_int32]),
                "GetFileType": (kernel, DWORD, [PTR]),
                "GetFileInformationByHandleEx": (kernel, BOOL, [PTR, ct.c_int32, PTR, DWORD]),
                "GetVolumeInformationByHandleW": (kernel, BOOL, [PTR, PTR, DWORD,
                    ct.POINTER(DWORD), ct.POINTER(DWORD), ct.POINTER(DWORD), PTR, DWORD]),
                "CloseHandle": (kernel, BOOL, [PTR]),
            }
            for name, (dll, result, args) in signatures.items():
                function = getattr(dll, name)
                function.restype, function.argtypes = result, args
                setattr(self, name, function)
        except (AttributeError, OSError):
            raise ErroDiretorioWindows("API_WINDOWS_INDISPONIVEL") from None


def _call(api, name, *args):
    try:
        return getattr(api, name)(*args)
    except (AttributeError, OSError, ValueError, TypeError, ct.ArgumentError):
        raise ErroDiretorioWindows("API_WINDOWS_FALHOU") from None


def _handle(value):
    return type(value) is int and 0 < value < 2**(8*ct.sizeof(PTR))-1


@dataclass(frozen=True)
class IdentidadeDiretorio:
    """Binding esperado explícito, não inferido do objeto a ser aceito."""
    volume: int = field(repr=False)
    file_id: bytes = field(repr=False)


def _identidade_valida(identity):
    _exigir(type(identity) is IdentidadeDiretorio and type(identity.volume) is int
        and 0 < identity.volume < 2**64 and type(identity.file_id) is bytes
        and len(identity.file_id) == 16 and any(identity.file_id), "IDENTIDADE_INVALIDA")


def _componente(nome):
    _exigir(type(nome) is str and nome and nome not in (".", ".."), "COMPONENTE_INVALIDO")
    _exigir(not any(ord(c) < 32 or c in '\\/:<>"|?*' for c in nome)
        and nome[-1] not in " .", "COMPONENTE_INVALIDO")
    # Aliases DOS, inclusive os dígitos sobrescritos reconhecidos pelo Windows.
    stem = nome.split(".", 1)[0].rstrip(" ").upper()
    _exigir(not re.fullmatch(r"CON|PRN|AUX|NUL|CLOCK\$|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³]", stem),
        "COMPONENTE_INVALIDO")
    try:
        raw = nome.encode("utf-16-le", errors="strict")
    except UnicodeError:
        raise ErroDiretorioWindows("COMPONENTE_INVALIDO") from None
    _exigir(0 < len(raw) <= 510, "COMPONENTE_INVALIDO")
    return raw


def _binding(handle, identity, policy, owner):
    _identidade_valida(identity)
    # Reutiliza a validação de contrato; nenhuma alteração na semântica ACL.
    try:
        acl._validar_entrada(handle, acl.ClasseObjeto.DIRETORIO, policy, owner)
    except acl.ErroVerificacaoACL:
        raise ErroDiretorioWindows("BINDING_INVALIDO") from None


def _verificar_acl(handle, policy, owner):
    try:
        result = acl.verificar_acl_handle(handle, classe=acl.ClasseObjeto.DIRETORIO,
            politica=policy, owner_esperado=owner)
    except acl.ErroVerificacaoACL:
        raise ErroDiretorioWindows("ACL_NAO_COMPROVADA") from None
    _exigir(result.perfil_confere and not result.autoriza_acesso
        and not result.aplicada_ao_leitor, "ACL_NAO_COMPROVADA")


def _info(api, handle, kind, type_):
    result = type_()
    _exigir(_call(api, "GetFileInformationByHandleEx", handle, kind,
        ct.byref(result), ct.sizeof(result)), "METADATA_INDISPONIVEL")
    return result


def _estado(api, handle, *, consultar_volume=True):
    _exigir(_call(api, "GetFileType", handle) == 1, "TIPO_NAO_SUPORTADO")
    tag = _info(api, handle, 9, _FILE_ATTRIBUTE_TAG_INFO)
    standard = _info(api, handle, 1, _FILE_STANDARD_INFO)
    _exigir(not tag.FileAttributes & 0x400 and tag.ReparseTag == 0, "OBJETO_REPARSE")
    _exigir(tag.FileAttributes & 0x10 and standard.Directory == 1, "NAO_DIRETORIO")
    _exigir(not standard.DeletePending and standard.NumberOfLinks == 1,
        "OBJETO_INSTAVEL")
    identity = _info(api, handle, 18, _FILE_ID_INFO)
    identity = IdentidadeDiretorio(identity.VolumeSerialNumber, bytes(identity.FileId))
    _identidade_valida(identity)
    if not consultar_volume:
        # O handle emprestado pode ser overlapped: não submeter uma consulta NT
        # potencialmente assíncrona com buffers locais a esse handle arbitrário.
        return identity
    device, ios = _FILE_FS_DEVICE_INFORMATION(), _IO_STATUS_BLOCK()
    status = _call(api, "NtQueryVolumeInformationFile", handle, ct.byref(ios),
        ct.byref(device), ct.sizeof(device), 4)  # FileFsDeviceInformation
    _exigir(status == 0 and ios.Status == 0 and ios.Information == ct.sizeof(device),
        "VOLUME_NAO_COMPROVADO")
    _exigir(device.DeviceType == 7 and not device.Characteristics & (0x1 | 0x10),
        "VOLUME_NAO_SUPORTADO")  # DISK; não REMOVABLE_MEDIA/REMOTE_DEVICE
    serial, maximum, flags = DWORD(), DWORD(), DWORD()
    filesystem = ct.create_unicode_buffer(32)
    _exigir(_call(api, "GetVolumeInformationByHandleW", handle, None, 0,
        ct.byref(serial), ct.byref(maximum), ct.byref(flags), filesystem, len(filesystem)),
        "VOLUME_NAO_COMPROVADO")
    _exigir(filesystem.value == "NTFS" and flags.value & 8 and maximum.value >= 1,
        "FILESYSTEM_NAO_SUPORTADO")  # FILE_PERSISTENT_ACLS
    return identity


@dataclass(frozen=True)
class ConformidadeDiretorio:
    """Resultado sem handle, caminho ou capacidade de conteúdo."""
    perfil_confere: bool = field(default=True, init=False)
    autoriza_acesso: bool = field(default=False, init=False)
    aplicada_ao_leitor: bool = field(default=False, init=False)


@dataclass(repr=False)
class _No:
    handle: int
    identidade: IdentidadeDiretorio
    politica: acl.PoliticaPerfilE
    owner: str


class CadeiaDiretorios:
    """Dona dos handles restritos; o anchor original continua sendo do chamador.

    Sem listagem, leitura, escrita, criação ou exportação pública de handles.
    A cadeia comprovada começa no anchor, nunca nos seus ancestrais externos.
    Compartilhamento bloqueia aberturas incompatíveis, não mudanças de DACL por
    owner/admin nem adversário da mesma identidade. Reconsultas não eliminam ABA.
    """
    def __init__(self):
        self._api = None
        self._nos = []
        self._fechada = True
        self._lock = threading.RLock()

    def __repr__(self):
        return "<CadeiaDiretorios metadata isolada>"

    @classmethod
    def de_handle_validado(cls, handle, *, identidade, politica, owner_esperado):
        _binding(handle, identidade, politica, owner_esperado)
        chain = cls()
        chain._api = _API()
        try:
            _exigir(_estado(chain._api, handle, consultar_volume=False) == identidade,
                "IDENTIDADE_DIVERGENTE")
            # ReOpenFile adquire OUTRO file object com share restrito; DuplicateHandle
            # sozinho conservaria o compartilhamento permissivo do anchor original.
            own = _call(chain._api, "ReOpenFile", handle, ACCESS, SHARE, 0x02200000)
            _exigir(_handle(own), "ANCHOR_NAO_REABERTO")
            chain._nos.append(_No(own, identidade, politica, owner_esperado))
            chain._conferir()
            _exigir(_estado(chain._api, handle, consultar_volume=False) == identidade,
                "IDENTIDADE_DIVERGENTE")
            chain._fechada = False
            return chain
        except BaseException:
            chain.fechar()
            raise

    def _conferir(self):
        for node in self._nos:
            _exigir(_estado(self._api, node.handle) == node.identidade, "IDENTIDADE_DIVERGENTE")
            _verificar_acl(node.handle, node.politica, node.owner)
            _exigir(_estado(self._api, node.handle) == node.identidade, "IDENTIDADE_DIVERGENTE")

    def abrir_componente(self, nome, *, identidade, politica):
        with self._lock:
            try:
                _exigir(not self._fechada and self._nos, "CADEIA_FECHADA")
                raw = _componente(nome)
                parent = self._nos[-1]
                _binding(parent.handle, identidade, politica, parent.owner)
                _exigir(identidade.volume == parent.identidade.volume, "VOLUME_DIVERGENTE")
                self._conferir()
                # Buffer UTF-16 contado em BYTES, independente do wchar_t do host.
                buffer = ct.create_string_buffer(raw+b"\0\0")
                name = _UNICODE_STRING(len(raw), len(raw)+2, ct.addressof(buffer))
                attrs = _OBJECT_ATTRIBUTES(ct.sizeof(_OBJECT_ATTRIBUTES), parent.handle,
                    ct.pointer(name), OBJECT_FLAGS, None, None)
                ios, child = _IO_STATUS_BLOCK(), PTR()
                try:
                    status = _call(self._api, "NtOpenFile", ct.byref(child), ACCESS,
                        ct.byref(attrs), ct.byref(ios), SHARE, OPTIONS)
                finally:
                    # Mesmo retorno de erro com handle preenchido precisa ser fechado.
                    if _handle(child.value):
                        self._nos.append(_No(child.value, identidade, politica, parent.owner))
                _exigir(status == 0 and ios.Status == 0 and ios.Information == 1
                    and _handle(child.value), "ABERTURA_RELATIVA_FALHOU")  # FILE_OPENED
                self._conferir()
                return ConformidadeDiretorio()
            except BaseException:
                self.fechar()
                raise

    def fechar(self):
        with self._lock:
            self._fechada = True
            remaining = []
            for node in reversed(self._nos):
                try:
                    ok = bool(_call(self._api, "CloseHandle", node.handle))
                except ErroDiretorioWindows:
                    ok = False
                if not ok:
                    remaining.append(node)
            self._nos = list(reversed(remaining))
            _exigir(not remaining, "FECHAMENTO_FALHOU")

    def __enter__(self):
        with self._lock:
            _exigir(not self._fechada, "CADEIA_FECHADA")
            return self

    def __exit__(self, *exc):
        self.fechar()
