"""Verificador isolado do Perfil E; não abre conteúdo nem autoriza acesso.

O chamador fornece um handle de disco vivo e um binding de teste confiável.
Esta prova de owner/DACL não verifica token/elevação, ancestrais, volume ou
TOCTOU de caminhos e não substitui os contratos de autorização da aplicação.
Nenhum consumidor de produção está integrado a este módulo.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass, field
from enum import Enum
import re
import struct
import sys

from .private_permissions import AclAce, mesmas_regras


DWORD = ct.c_uint32
WORD = ct.c_uint16
BOOL = ct.c_int32
PTR = ct.c_void_p
METADATA_ACCESS = 0x00020080  # READ_CONTROL | FILE_READ_ATTRIBUTES
SE_DACL_PRESENT = 0x0004
SE_DACL_PROTECTED = 0x1000
SE_SELF_RELATIVE = 0x8000


class _FILETIME(ct.Structure):
    _fields_ = [("low", DWORD), ("high", DWORD)]


class _FILE_INFORMATION(ct.Structure):
    _fields_ = [("attributes", DWORD), ("creation", _FILETIME),
                ("access", _FILETIME), ("write", _FILETIME),
                ("volume", DWORD), ("size_high", DWORD), ("size_low", DWORD),
                ("links", DWORD), ("index_high", DWORD), ("index_low", DWORD)]


class _ACL_SIZE_INFORMATION(ct.Structure):
    _fields_ = [("count", DWORD), ("used", DWORD), ("free", DWORD)]


class ClasseObjeto(str, Enum):
    ARQUIVO = "arquivo"
    DIRETORIO = "diretorio"


@dataclass(frozen=True)
class PoliticaPerfilE:
    """Binding sintético explícito: uma ACE ALLOW, SID do owner, flags zero."""
    classe: ClasseObjeto
    aces: tuple[AclAce, ...] = field(repr=False)


@dataclass(frozen=True)
class ConformidadeACL:
    """Somente conformidade de metadata; não é capacidade de conteúdo."""
    classe: ClasseObjeto
    perfil_confere: bool = field(default=True, init=False)
    autoriza_acesso: bool = field(default=False, init=False)
    aplicada_ao_leitor: bool = field(default=False, init=False)


class ErroVerificacaoACL(ValueError):
    """Código seguro, sem SID, handle, caminho ou mensagem nativa."""


def _erro(codigo):
    raise ErroVerificacaoACL(codigo)


class _API:
    def __init__(self):
        if sys.platform != "win32":
            _erro("API_WINDOWS_INDISPONIVEL")
        try:
            advapi = ct.WinDLL("advapi32", use_last_error=True)
            kernel = ct.WinDLL("kernel32", use_last_error=True)
            signatures = {
                "GetSecurityInfo": (advapi, DWORD, [PTR, ct.c_int32, DWORD,
                    ct.POINTER(PTR), ct.POINTER(PTR), ct.POINTER(PTR),
                    ct.POINTER(PTR), ct.POINTER(PTR)]),
                "IsValidSecurityDescriptor": (advapi, BOOL, [PTR]),
                "GetSecurityDescriptorLength": (advapi, DWORD, [PTR]),
                "GetSecurityDescriptorControl": (advapi, BOOL,
                    [PTR, ct.POINTER(WORD), ct.POINTER(DWORD)]),
                "GetSecurityDescriptorDacl": (advapi, BOOL,
                    [PTR, ct.POINTER(BOOL), ct.POINTER(PTR), ct.POINTER(BOOL)]),
                "IsValidAcl": (advapi, BOOL, [PTR]),
                "GetAclInformation": (advapi, BOOL, [PTR, PTR, DWORD, ct.c_int32]),
                "GetAce": (advapi, BOOL, [PTR, DWORD, ct.POINTER(PTR)]),
                "IsValidSid": (advapi, BOOL, [PTR]),
                "GetLengthSid": (advapi, DWORD, [PTR]),
                "GetCurrentProcess": (kernel, PTR, []),
                "DuplicateHandle": (kernel, BOOL, [PTR, PTR, PTR,
                    ct.POINTER(PTR), DWORD, BOOL, DWORD]),
                "GetFileInformationByHandle": (kernel, BOOL,
                    [PTR, ct.POINTER(_FILE_INFORMATION)]),
                "LocalFree": (kernel, PTR, [PTR]),
                "CloseHandle": (kernel, BOOL, [PTR]),
            }
            for name, (library, result, args) in signatures.items():
                function = getattr(library, name)
                function.restype, function.argtypes = result, args
                setattr(self, name, function)
        except (AttributeError, OSError):
            raise ErroVerificacaoACL("API_WINDOWS_INDISPONIVEL") from None


def _chamar(api, nome, *args):
    try:
        return getattr(api, nome)(*args)
    except (AttributeError, OSError, ValueError, TypeError, ct.ArgumentError):
        raise ErroVerificacaoACL("API_WINDOWS_FALHOU") from None


def _exigir(valor, codigo):
    if not valor:
        _erro(codigo)


def _sid_configurado(sid):
    # Representação numérica sem aliases, espaços, zeros redundantes ou logs.
    if not isinstance(sid, str) or len(sid) > 200:
        return False
    if not re.fullmatch(r"S-1-(?:0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*)){0,15}", sid):
        return False
    parts = sid.split("-")
    return int(parts[2]) < 2**48 and all(int(p) < 2**32 for p in parts[3:])


def _validar_entrada(handle, classe, politica, owner):
    _exigir(type(handle) is int and 0 < handle < 2**(ct.sizeof(PTR)*8)-1,
            "HANDLE_INVALIDO")
    _exigir(isinstance(classe, ClasseObjeto) and type(politica) is PoliticaPerfilE,
            "POLITICA_INVALIDA")
    _exigir(isinstance(politica.classe, ClasseObjeto) and
            politica.classe == classe and type(politica.aces) is tuple and
            len(politica.aces) == 1 and _sid_configurado(owner), "POLITICA_INVALIDA")
    ace = politica.aces[0]
    _exigir(type(ace) is AclAce and type(ace.sid) is str and ace.sid == owner and
            type(ace.access_mask) is int and 0 < ace.access_mask <= 0xFFFFFFFF and
            type(ace.ace_flags) is int and ace.ace_flags == 0, "POLITICA_INVALIDA")


def _bytes_na_faixa(pointer, tamanho, inicio, fim):
    _exigir(type(pointer) is int and inicio <= pointer <= fim and
            0 <= tamanho <= fim-pointer, "ESTRUTURA_NATIVA_INVALIDA")
    return ct.string_at(pointer, tamanho)


def _sid(api, pointer, inicio, fim):
    header = _bytes_na_faixa(pointer, 8, inicio, fim)
    _exigir(header[0] == 1 and header[1] <= 15, "SID_NATIVO_INVALIDO")
    size = 8 + 4*header[1]
    raw = _bytes_na_faixa(pointer, size, inicio, fim)
    _exigir(_chamar(api, "IsValidSid", pointer), "SID_NATIVO_INVALIDO")
    _exigir(_chamar(api, "GetLengthSid", pointer) == size, "SID_NATIVO_INVALIDO")
    authority = int.from_bytes(raw[2:8], "big")
    sub = struct.unpack_from("<" + "I"*header[1], raw, 8)
    return "S-1-" + str(authority) + "".join("-"+str(p) for p in sub), size


def _ler_aces(api, pointer, inicio, fim):
    header = _bytes_na_faixa(pointer, 8, inicio, fim)
    revision, _, size, count, _ = struct.unpack("<BBHHH", header)
    _exigir(revision in (2, 4) and size >= 8, "DACL_INVALIDA")
    _bytes_na_faixa(pointer, size, inicio, fim)
    _exigir(_chamar(api, "IsValidAcl", pointer), "DACL_INVALIDA")
    info = _ACL_SIZE_INFORMATION()
    _exigir(_chamar(api, "GetAclInformation", pointer, ct.byref(info),
                    ct.sizeof(info), 2), "CONSULTA_DACL_FALHOU")
    _exigir(info.count == count and 8 <= info.used <= size and
            info.used + info.free == size, "DACL_INVALIDA")
    _exigir(count > 0, "DACL_VAZIA")
    cursor, aces = pointer + 8, []
    for index in range(count):
        ace = PTR()
        _exigir(_chamar(api, "GetAce", pointer, index, ct.byref(ace)),
                "CONSULTA_ACE_FALHOU")
        _exigir(ace.value == cursor, "ESTRUTURA_NATIVA_INVALIDA")
        raw = _bytes_na_faixa(cursor, 4, pointer+8, pointer+info.used)
        kind, flags, ace_size = struct.unpack("<BBH", raw)
        # Validar tipo ANTES de interpretar máscara/SID e de comparar ACEs.
        _exigir(kind == 0, "TIPO_ACE_NAO_SUPORTADO")  # ACCESS_ALLOWED_ACE_TYPE
        _exigir(ace_size >= 16 and ace_size % 4 == 0, "ACE_INVALIDA")
        raw = _bytes_na_faixa(cursor, ace_size, pointer+8, pointer+info.used)
        sid, sid_size = _sid(api, cursor+8, cursor+8, cursor+ace_size)
        _exigir(ace_size == 8+sid_size, "ACE_INVALIDA")
        aces.append(AclAce(sid, struct.unpack_from("<I", raw, 4)[0], flags))
        cursor += ace_size
    _exigir(cursor == pointer+info.used, "DACL_INVALIDA")
    return aces


def _conferir(api, handle, classe, politica, owner_esperado):
    duplicate, descriptor = PTR(), PTR()
    try:
        process = _chamar(api, "GetCurrentProcess")
        _exigir(_chamar(api, "DuplicateHandle", process, handle, process,
            ct.byref(duplicate), METADATA_ACCESS, False, 0), "HANDLE_NAO_DUPLICADO")
        _exigir(duplicate.value not in (None, 0, PTR(-1).value), "HANDLE_INVALIDO")
        info = _FILE_INFORMATION()
        _exigir(_chamar(api, "GetFileInformationByHandle", duplicate,
                        ct.byref(info)), "TIPO_OBJETO_INDISPONIVEL")
        _exigir(not info.attributes & 0x400, "OBJETO_REPARSE")
        directory = bool(info.attributes & 0x10)
        _exigir(directory == (classe == ClasseObjeto.DIRETORIO), "CLASSE_DIVERGENTE")
        owner, dacl = PTR(), PTR()
        status = _chamar(api, "GetSecurityInfo", duplicate, 1, 0x00000005,
                        ct.byref(owner), None, ct.byref(dacl), None, ct.byref(descriptor))
        _exigir(status == 0 and descriptor.value, "CONSULTA_SEGURANCA_FALHOU")
        _exigir(_chamar(api, "IsValidSecurityDescriptor", descriptor), "DESCRITOR_INVALIDO")
        control, revision = WORD(), DWORD()
        _exigir(_chamar(api, "GetSecurityDescriptorControl", descriptor,
                        ct.byref(control), ct.byref(revision)), "DESCRITOR_INVALIDO")
        _exigir(revision.value == 1 and control.value & SE_SELF_RELATIVE,
                "FORMATO_DESCRITOR_NAO_SUPORTADO")
        _exigir(control.value & SE_DACL_PROTECTED, "DACL_NAO_PROTEGIDA")
        size = _chamar(api, "GetSecurityDescriptorLength", descriptor)
        _exigir(20 <= size <= 1024*1024, "DESCRITOR_INVALIDO")
        start, end = descriptor.value, descriptor.value+size
        sd = _bytes_na_faixa(start, 20, start, end)
        sd_revision, _, sd_control, owner_offset, _, _, dacl_offset = struct.unpack("<BBHIIII", sd)
        _exigir(sd_revision == 1 and sd_control == control.value and
                owner_offset >= 20 and owner_offset % 4 == 0 and
                owner.value == start+owner_offset, "DESCRITOR_INVALIDO")
        sid, _ = _sid(api, owner.value, start+20, end)
        _exigir(sid == owner_esperado, "OWNER_DIVERGENTE")
        present, defaulted, queried_dacl = BOOL(), BOOL(), PTR()
        _exigir(_chamar(api, "GetSecurityDescriptorDacl", descriptor,
                        ct.byref(present), ct.byref(queried_dacl), ct.byref(defaulted)),
                "CONSULTA_DACL_FALHOU")
        _exigir(present.value and control.value & SE_DACL_PRESENT, "DACL_AUSENTE")
        _exigir(dacl.value and queried_dacl.value, "DACL_NULA")
        _exigir(dacl_offset >= 20 and dacl_offset % 4 == 0 and
                dacl.value == queried_dacl.value == start+dacl_offset,
                "DESCRITOR_INVALIDO")
        aces = _ler_aces(api, dacl.value, start+20, end)
        _exigir(mesmas_regras(list(politica.aces), aces), "ACES_DIVERGENTES")
    finally:
        # Tentar ambas as liberações mesmo se a primeira falhar.
        failed = False
        if descriptor.value:
            try:
                failed = bool(_chamar(api, "LocalFree", descriptor))
            except ErroVerificacaoACL:
                failed = True
        if duplicate.value:
            try:
                failed = not bool(_chamar(api, "CloseHandle", duplicate)) or failed
            except ErroVerificacaoACL:
                failed = True
        _exigir(not failed, "LIBERACAO_RECURSOS_FALHOU")


def verificar_acl_handle(handle: int, *, classe: ClasseObjeto,
                        politica: PoliticaPerfilE, owner_esperado: str) -> ConformidadeACL:
    """Consulta somente metadata do objeto aberto; falha por código seguro.

    O handle original é emprestado e não é fechado; o verificador duplica
    somente READ_CONTROL/READ_ATTRIBUTES. Binding/elevação e a segurança
    da cadeia de caminhos não são certificados por este resultado isolado.
    """
    _validar_entrada(handle, classe, politica, owner_esperado)
    api = _API()
    _conferir(api, handle, classe, politica, owner_esperado)
    return ConformidadeACL(classe)
