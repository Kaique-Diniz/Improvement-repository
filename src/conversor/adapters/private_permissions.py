"""Permissões privadas: POSIX e DACL Windows nativa, sem dependências externas.

Política conservadora: usuário atual, SYSTEM e Administradores locais são a
fronteira de confiança. ACL desconhecida/nula ou ACE não interpretável não prova
privacidade. Não reescreve ACL de arquivos existentes durante uma conferência.
"""
from dataclasses import dataclass
import os
from pathlib import Path

from conversor.application.ports import ErroAplicacao

FULL_CONTROL = 0x1F01FF
TRUSTED_SYSTEM = frozenset(('S-1-5-18', 'S-1-5-32-544'))


@dataclass(frozen=True)
class AcePrivada:
    tipo: int
    flags: int
    mascara: int
    sid: str


@dataclass(frozen=True)
class AclPrivada:
    usuario: str
    proprietario: str
    dacl_presente: bool
    entradas: tuple[AcePrivada, ...]


def validar_acl(acl: AclPrivada):
    permitidos = TRUSTED_SYSTEM | {acl.usuario}
    if not acl.usuario:
        raise ErroAplicacao('ACL_PRIVADA_NAO_COMPROVADA')
    if acl.proprietario not in permitidos or not acl.dacl_presente:
        raise ErroAplicacao('ACL_PRIVADA_INSEGURA')
    if any(e.tipo!=0 for e in acl.entradas):
        raise ErroAplicacao('ACL_PRIVADA_NAO_COMPROVADA')
    direitos_usuario = 0
    for e in acl.entradas:
        # Não tentar resolver ACE condicional/objeto, deny ou participação em grupos.
        if e.mascara and e.sid not in permitidos:
            raise ErroAplicacao('ACL_PRIVADA_INSEGURA')
        if e.sid == acl.usuario and not e.flags & 0x08:  # INHERIT_ONLY não se aplica ao objeto.
            direitos_usuario |= e.mascara
    if direitos_usuario & FULL_CONTROL != FULL_CONTROL and not direitos_usuario & 0x10000000:
        raise ErroAplicacao('ACL_PRIVADA_NAO_COMPROVADA')


class _WindowsACL:
    def __init__(self):
        import ctypes as c
        self.c = c
        self.a = c.WinDLL('advapi32', use_last_error=True)
        self.k = c.WinDLL('kernel32', use_last_error=True)
        p = c.c_void_p; pp = c.POINTER(p); d = c.c_uint32; b = c.c_int
        def api(dll, name, args, result):
            f = getattr(dll, name); f.argtypes = args; f.restype = result
        api(self.k,'GetCurrentProcess',[],p)
        api(self.k,'CloseHandle',[p],b)
        api(self.k,'LocalFree',[p],p)
        api(self.a,'OpenProcessToken',[p,d,pp],b)
        api(self.a,'GetTokenInformation',[p,d,p,d,c.POINTER(d)],b)
        api(self.a,'ConvertSidToStringSidW',[p,c.POINTER(c.c_wchar_p)],b)
        api(self.a,'IsValidSid',[p],b)
        api(self.a,'GetLengthSid',[p],d)
        api(self.a,'GetFileSecurityW',[c.c_wchar_p,d,p,d,c.POINTER(d)],b)
        api(self.a,'GetSecurityDescriptorLength',[p],d)
        api(self.a,'GetNamedSecurityInfoW',[c.c_wchar_p,d,d,pp,pp,pp,pp,pp],d)
        api(self.a,'GetSecurityDescriptorDacl',[p,c.POINTER(b),pp,c.POINTER(b)],b)
        api(self.a,'GetAclInformation',[p,p,d,d],b)
        api(self.a,'GetAce',[p,d,pp],b)
        api(self.a,'ConvertStringSecurityDescriptorToSecurityDescriptorW',[c.c_wchar_p,d,pp,c.POINTER(d)],b)
        api(self.a,'SetNamedSecurityInfoW',[c.c_wchar_p,d,d,p,p,p,p],d)

    def sid(self, ptr, *, disponivel=68):
        from .acl_binary import sid_binario
        c=self.c
        if not ptr or disponivel<8:raise OSError('SID_INVALIDO')
        header=c.string_at(ptr,8);length=8+4*header[1]
        if length>disponivel or length>68:raise OSError('SID_FORA_DO_LIMITE')
        raw=c.string_at(ptr,length);esperado,end=sid_binario(raw)
        buf=c.create_string_buffer(raw)
        if not self.a.IsValidSid(buf) or self.a.GetLengthSid(buf)!=length:raise OSError('SID_INVALIDO')
        text=c.c_wchar_p()
        if not self.a.ConvertSidToStringSidW(buf,c.byref(text)):raise OSError('SID_INDISPONIVEL')
        try:
            if text.value!=esperado:raise OSError('CONVERSAO_SID_DIVERGENTE')
            return esperado
        finally:self.k.LocalFree(c.cast(text,c.c_void_p))

    def usuario(self):
        c=self.c;token=c.c_void_p();size=c.c_uint32()
        if not self.a.OpenProcessToken(self.k.GetCurrentProcess(),0x8,c.byref(token)):raise OSError('TOKEN_INDISPONIVEL')
        try:
            self.a.GetTokenInformation(token,1,None,0,c.byref(size))
            if not 8<=size.value<=1024*1024:raise OSError('TOKEN_INVALIDO')
            capacidade=size.value;buf=c.create_string_buffer(capacidade)
            if not self.a.GetTokenInformation(token,1,buf,capacidade,c.byref(size)):raise OSError('TOKEN_INVALIDO')
            class SidAttributes(c.Structure):
                _fields_=[('sid',c.c_void_p),('attributes',c.c_uint32)]
            if size.value>capacidade or size.value<c.sizeof(SidAttributes):raise OSError('TOKEN_INVALIDO')
            ptr=SidAttributes.from_buffer(buf).sid;inicio=c.addressof(buf);fim=inicio+size.value
            if not ptr or not inicio<=ptr<fim:raise OSError('SID_FORA_DO_TOKEN')
            return self.sid(ptr,disponivel=fim-ptr)
        finally:self.k.CloseHandle(token)

    def _snapshot_nome(self,path):
        c=self.c;owner=c.c_void_p();acl=c.c_void_p();sd=c.c_void_p()
        if self.a.GetNamedSecurityInfoW(str(path),1,5,c.byref(owner),None,c.byref(acl),None,c.byref(sd)):
            if sd.value:self.k.LocalFree(sd)
            raise OSError('ACL_INDISPONIVEL')
        try:
            if not sd.value:raise OSError('DESCRITOR_INVALIDO')
            length=self.a.GetSecurityDescriptorLength(sd)
            if not 20<=length<=1024*1024:raise OSError('DESCRITOR_INVALIDO')
            return c.string_at(sd,length)  # Copiar enquanto o bloco LocalAlloc está vivo.
        finally:self.k.LocalFree(sd)

    def _snapshot_arquivo(self,path):
        c=self.c;size=c.c_uint32()
        self.a.GetFileSecurityW(str(path),5,None,0,c.byref(size))
        if not 20<=size.value<=1024*1024:raise OSError('DESCRITOR_INVALIDO')
        capacidade=size.value;buf=c.create_string_buffer(capacidade)
        if not self.a.GetFileSecurityW(str(path),5,buf,capacidade,c.byref(size)) or size.value>capacidade:
            raise OSError('ACL_INDISPONIVEL')
        return bytes(buf.raw[:size.value])

    def ler(self,path):
        from .acl_binary import decodificar_descritor,mesmas_regras
        usuario=self.usuario()
        snapshot=self._snapshot_nome(path)
        nome=decodificar_descritor(snapshot,usuario)
        arquivo=decodificar_descritor(self._snapshot_arquivo(path),usuario)
        ponteiros=self._projetar_getace(snapshot,usuario)
        if not mesmas_regras(nome,arquivo) or not mesmas_regras(nome,ponteiros):
            raise OSError('LEITURAS_ACL_DIVERGENTES')
        return arquivo

    def _projetar_getace(self,data,usuario):
        from .acl_binary import decodificar_descritor
        esperado=decodificar_descritor(data,usuario)  # Validar limites antes de chamar APIs de ponteiros.
        c=self.c;buf=c.create_string_buffer(data);base=c.addressof(buf);fim=base+len(data)
        presente=c.c_int();default=c.c_int();dacl=c.c_void_p()
        if not self.a.GetSecurityDescriptorDacl(buf,c.byref(presente),c.byref(dacl),c.byref(default)):
            raise OSError('DACL_INDISPONIVEL')
        if bool(presente.value and dacl.value)!=esperado.dacl_presente:raise OSError('DACL_DIVERGENTE')
        entradas=[]
        if esperado.dacl_presente:
            if not base<=dacl.value<=fim-8:raise OSError('DACL_FORA_DO_BUFFER')
            dacl_fim=dacl.value+int.from_bytes(c.string_at(dacl.value+2,2),'little')
            if dacl_fim>fim:raise OSError('DACL_FORA_DO_BUFFER')
            class Size(c.Structure):
                _fields_=[('count',c.c_uint32),('used',c.c_uint32),('free',c.c_uint32)]
            info=Size()
            if not self.a.GetAclInformation(dacl,c.byref(info),c.sizeof(info),2) or info.count!=len(esperado.entradas):
                raise OSError('DACL_DIVERGENTE')
            for i in range(info.count):
                ace=c.c_void_p()
                if not self.a.GetAce(dacl,i,c.byref(ace)) or not ace.value or not dacl.value+8<=ace.value<=dacl_fim-4:
                    raise OSError('ACE_FORA_DO_BUFFER')
                header=c.string_at(ace.value,4);tipo,flags=header[:2];size=int.from_bytes(header[2:],'little')
                if size<4 or size%4 or ace.value+size>dacl_fim:raise OSError('ACE_FORA_DO_BUFFER')
                if tipo in (0,1):
                    if size<16:raise OSError('ACE_ALLOW_INVALIDA')
                    mask=c.c_uint32.from_address(ace.value+4).value
                    entradas.append(AcePrivada(tipo,flags,mask,self.sid(ace.value+8,disponivel=size-8)))
                else:entradas.append(AcePrivada(tipo,flags,0,''))
        return AclPrivada(usuario,esperado.proprietario,esperado.dacl_presente,tuple(entradas))

    def proteger_novo(self, path, *, diretorio=False):
        flags = 'OICI' if diretorio else ''
        sddl = 'D:P' + ''.join(f'(A;{flags};FA;;;{sid})' for sid in (self.usuario(),'S-1-5-18','S-1-5-32-544'))
        self._aplicar_dacl(path,sddl)

    def _aplicar_dacl(self, path, sddl):
        c = self.c; sd = c.c_void_p(); acl = c.c_void_p(); present = c.c_int(); default = c.c_int()
        if not self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(sd),None):raise OSError('DACL_INVALIDA')
        try:
            if not self.a.GetSecurityDescriptorDacl(sd,c.byref(present),c.byref(acl),c.byref(default)):raise OSError('DACL_INVALIDA')
            if self.a.SetNamedSecurityInfoW(str(path),1,0x80000004,None,None,acl,None):raise OSError('ACL_NAO_APLICADA')
        finally:self.k.LocalFree(sd)


def windows():
    return os.name == 'nt'


def _sem_redirecionamento(path):
    if any(p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400)
           for p in (path,*path.parents)):
        raise ErroAplicacao('CAMINHO_COM_LINK_NAO_PERMITIDO')
    if path.is_file() and path.stat().st_nlink != 1:raise ErroAplicacao('ARQUIVO_COM_LINK_FISICO')


def conferir_windows(path):
    if windows():
        try:
            path = Path(path); _sem_redirecionamento(path)
            validar_acl(_WindowsACL().ler(path))
        except ErroAplicacao:raise
        except Exception:
            raise ErroAplicacao('ACL_PRIVADA_NAO_VERIFICAVEL')from None


def proteger_novo_windows(path, *, diretorio=False):
    """Somente no momento de criação, antes de gravar bytes privados."""
    if windows():
        try:
            path = Path(path);_sem_redirecionamento(path)
            _WindowsACL().proteger_novo(path,diretorio=diretorio)
            conferir_windows(path)
        except ErroAplicacao:raise
        except Exception:
            raise ErroAplicacao('ACL_PRIVADA_NAO_APLICADA')from None


def criar_diretorio_privado(path, *, parents=False):
    path = Path(path);_sem_redirecionamento(path)
    try:
        path.mkdir(mode=0o700,parents=parents)
        novo = True
    except FileExistsError:
        if not path.is_dir():raise
        novo = False
    if novo:proteger_novo_windows(path,diretorio=True)
    conferir_windows(path)
    return path
