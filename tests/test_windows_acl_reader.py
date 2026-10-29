"""Vectores inteiramente sintéticos. Fakes ctypes não são execução Windows."""
import ctypes as c
from dataclasses import replace
import os
from struct import pack_into
from types import SimpleNamespace

import pytest

from conversor.adapters import private_permissions as p
from conversor.adapters.acl_binary import decodificar_descritor, mesmas_regras, sid_binario
from conversor.application.ports import ErroAplicacao

USER='S-1-5-21-100-200-300-1001'
OTHER='S-1-5-21-100-200-300-1002'
# Vetor fixo de SD relativo: owner em 20, DACL em 48, três ACEs allow.
# SIDs de tamanhos diferentes exercitam o avanço por AceSize, não tamanho fixo.
USER_BYTES=bytes.fromhex('01050000000000051500000064000000c80000002c010000e9030000')
SYSTEM_BYTES=bytes.fromhex('010100000000000512000000')
ADMIN_BYTES=bytes.fromhex('01020000000000052000000020020000')
SD=bytes.fromhex(
    '0100048014000000000000000000000030000000'
    '01050000000000051500000064000000c80000002c010000e9030000'
    '0200580003000000'
    '00131400ff011f00010100000000000512000000'
    '00131800ff011f0001020000000000052000000020020000'
    '00132400ff011f0001050000000000051500000064000000c80000002c010000e9030000')
EXPECTED=p.AclPrivada(USER,USER,True,tuple(p.AcePrivada(0,0x13,p.FULL_CONTROL,s)for s in ('S-1-5-18','S-1-5-32-544',USER)))


def mod(offset,fmt,*values):
    raw=bytearray(SD);pack_into(fmt,raw,offset,*values);return bytes(raw)


def test_vetor_independente_com_tres_sids_e_ace_herdada():
    assert len(SD)==136
    acl=decodificar_descritor(SD,USER)
    assert acl==EXPECTED
    assert acl.entradas[2].sid==USER
    p.validar_acl(acl)


@pytest.mark.parametrize('flags',[0,3,16,19])
def test_ace_explicita_e_herdada_preserva_flags(flags):
    acl=decodificar_descritor(mod(101,'B',flags),USER)
    assert acl.entradas[2].flags==flags
    p.validar_acl(acl)


@pytest.mark.parametrize('raw',[
    b'',SD[:19],mod(0,'B',2),mod(2,'H',4),mod(4,'I',19),mod(4,'I',10000),
    mod(16,'I',49),mod(16,'I',136),mod(48,'B',1),mod(50,'H',7),mod(50,'H',90),
    mod(52,'H',4),mod(58,'H',3),mod(58,'H',18),mod(58,'H',136),
    mod(64,'B',2),mod(65,'B',16),mod(65,'B',3),SD[:-1],
])
def test_descritor_truncado_ou_malformado_nao_e_aceito(raw):
    with pytest.raises(ValueError):decodificar_descritor(raw,USER)


@pytest.mark.parametrize('control,dacl',[(0x8000,0),(0x8004,0)])
def test_dacl_ausente_ou_nula_nao_prova_privacidade(control,dacl):
    raw=bytearray(SD);pack_into('<H',raw,2,control);pack_into('<I',raw,16,dacl)
    acl=decodificar_descritor(bytes(raw),USER)
    assert not acl.dacl_presente and not acl.entradas
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_INSEGURA'):p.validar_acl(acl)


@pytest.mark.parametrize('tipo',[1,5,9,255])
def test_tipo_desconhecido_ou_deny_nunca_vira_allow(tipo):
    acl=decodificar_descritor(mod(56,'B',tipo),USER)
    assert acl.entradas[0].tipo==tipo
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_NAO_COMPROVADA'):p.validar_acl(acl)


def test_sid_diferente_no_terceiro_allow_nao_e_substituido_pelo_usuario():
    acl=decodificar_descritor(mod(132,'I',1002),USER)
    assert acl.entradas[2].sid==OTHER
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_INSEGURA'):p.validar_acl(acl)


def test_sid_endianness_e_limite_da_ace():
    assert sid_binario(USER_BYTES)==(USER,28)
    assert sid_binario(bytes.fromhex('010100010000000078563412'))[0]=='S-1-0x000100000000-305419896'
    with pytest.raises(ValueError):sid_binario(USER_BYTES,fim=27)
    with pytest.raises(ValueError):sid_binario(USER_BYTES,-1)


def test_comparacao_preserva_multiplicidade_e_independe_da_ordem():
    assert mesmas_regras(EXPECTED,replace(EXPECTED,entradas=EXPECTED.entradas[::-1]))
    assert not mesmas_regras(EXPECTED,replace(EXPECTED,entradas=EXPECTED.entradas+(EXPECTED.entradas[0],)))


class TokenUser(c.Structure):
    _fields_=[('sid',c.c_void_p),('attributes',c.c_uint32)]


class AclHeader(c.LittleEndianStructure):
    _fields_=[('rev',c.c_uint8),('sbz',c.c_uint8),('size',c.c_uint16),('count',c.c_uint16),('sbz2',c.c_uint16)]


class AceHeader(c.LittleEndianStructure):
    _fields_=[('tipo',c.c_uint8),('flags',c.c_uint8),('size',c.c_uint16)]


def put(ptr,ctype,value):c.cast(ptr,c.POINTER(ctype))[0]=value


class MemoriaWindows:
    """Contrato ctypes com memória real local, sem simular autorização do SO."""
    def __init__(self,nome=SD,arquivo=SD):
        self.nome=nome;self.arquivo=arquivo;self.allocs=[];self.liberados=[];self.closed=0
        self.token_invalido=False;self.ace_invalida=False;self.conversao_incorreta=False
        self.sids={USER_BYTES:USER,SYSTEM_BYTES:'S-1-5-18',ADMIN_BYTES:'S-1-5-32-544',USER_BYTES[:-4]+b'\xea\x03\0\0':OTHER}

    def GetCurrentProcess(self):return 123
    def CloseHandle(self,token):self.closed+=1;return 1
    def LocalFree(self,ptr):
        addr=c.cast(ptr,c.c_void_p).value
        for buf in self.allocs:
            if c.addressof(buf)==addr:
                self.liberados.append(addr);c.memset(addr,0xEE,c.sizeof(buf));break
        return None
    def OpenProcessToken(self,process,access,out):
        assert access==8;put(out,c.c_void_p,456);return 1
    def GetTokenInformation(self,token,kind,buf,size,out):
        assert kind==1
        length=c.sizeof(TokenUser)+len(USER_BYTES);put(out,c.c_uint32,length)
        if not buf:return 0
        start=c.addressof(buf);sid=start+c.sizeof(TokenUser)
        TokenUser.from_buffer(buf).sid=start+length+1 if self.token_invalido else sid
        c.memmove(sid,USER_BYTES,len(USER_BYTES));return 1
    def IsValidSid(self,ptr):
        size=8+4*c.string_at(ptr,2)[1]
        return c.string_at(ptr,size)in self.sids
    def GetLengthSid(self,ptr):return 8+4*c.string_at(ptr,2)[1]
    def ConvertSidToStringSidW(self,ptr,out):
        raw=c.string_at(ptr,self.GetLengthSid(ptr));text=self.sids[raw]
        buf=c.create_unicode_buffer(OTHER if self.conversao_incorreta else text);self.allocs.append(buf)
        put(out,c.c_void_p,c.addressof(buf));return 1
    def GetNamedSecurityInfoW(self,path,kind,info,owner,group,dacl,sacl,out):
        assert kind==1 and info==5
        buf=c.create_string_buffer(self.nome);self.allocs.append(buf);start=c.addressof(buf)
        put(out,c.c_void_p,start);put(owner,c.c_void_p,start+20);put(dacl,c.c_void_p,start+48);return 0
    def GetSecurityDescriptorLength(self,sd):return len(self.nome)
    def GetFileSecurityW(self,path,info,buf,size,out):
        assert info==5;put(out,c.c_uint32,len(self.arquivo))
        if not buf:return 0
        c.memmove(buf,self.arquivo,len(self.arquivo));return 1
    def GetSecurityDescriptorDacl(self,buf,present,dacl,default):
        put(present,c.c_int,1);put(default,c.c_int,0)
        offset=c.c_uint32.from_buffer(buf,16).value
        put(dacl,c.c_void_p,c.addressof(buf)+offset);return 1
    def GetAclInformation(self,dacl,out,size,kind):
        assert size==12 and kind==2
        h=AclHeader.from_address(dacl.value)
        arr=c.cast(out,c.POINTER(c.c_uint32));arr[0]=h.count;arr[1]=h.size;arr[2]=0;return 1
    def GetAce(self,dacl,index,out):
        addr=dacl.value+c.sizeof(AclHeader)
        for _ in range(index):addr+=AceHeader.from_address(addr).size
        put(out,c.c_void_p,dacl.value-1 if self.ace_invalida else addr);return 1


def backend(fake):
    api=p._WindowsACL.__new__(p._WindowsACL);api.c=c;api.a=api.k=fake;return api


def test_binding_copia_descritor_antes_de_localfree_e_interpreta_sid_do_token():
    fake=MemoriaWindows();api=backend(fake)
    assert api.ler('fixture_sintetica')==EXPECTED
    assert fake.closed==1 and fake.liberados
    assert all(c.string_at(addr,1)==b'\xee'for addr in fake.liberados)


def test_binding_rejeita_duas_apis_com_terceiro_sid_distinto():
    api=backend(MemoriaWindows(nome=mod(132,'I',1002)))
    with pytest.raises(OSError,match='LEITURAS_ACL_DIVERGENTES'):api.ler('fixture_sintetica')


def test_binding_nao_libera_terceiro_sid_estranho_mesmo_se_apis_concordam():
    raw=mod(132,'I',1002);api=backend(MemoriaWindows(nome=raw,arquivo=raw))
    acl=api.ler('fixture_sintetica')
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_INSEGURA'):p.validar_acl(acl)


def test_binding_token_com_ponteiro_fora_do_buffer_e_rejeitado_e_handle_fechado():
    fake=MemoriaWindows();fake.token_invalido=True
    with pytest.raises(OSError,match='SID_FORA_DO_TOKEN'):backend(fake).usuario()
    assert fake.closed==1


def test_binding_getace_fora_do_buffer_e_rejeitado_antes_de_dereferenciar():
    fake=MemoriaWindows();fake.ace_invalida=True
    with pytest.raises(OSError,match='ACE_FORA_DO_BUFFER'):backend(fake)._projetar_getace(SD,USER)


def test_binding_conversao_nativa_divergente_nao_substitui_sid():
    fake=MemoriaWindows();fake.conversao_incorreta=True
    with pytest.raises(OSError,match='CONVERSAO_SID_DIVERGENTE'):backend(fake).usuario()
    assert fake.closed==1


@pytest.mark.skipif(os.name!='nt',reason='Exige Windows nativo e PowerShell; fake ctypes/Linux não substitui esta conferência.')
@pytest.mark.parametrize('arquivo',[False,True])
def test_apis_e_getaccessrules_concordam_no_windows_nativo(tmp_path,arquivo):
    from conversor.acl_diagnostics import diagnosticar
    from conversor.adapters.private_json import escrever_json
    alvo=tmp_path/'sintetico'
    if arquivo:escrever_json(alvo,{'sintetico':True})
    else:p.criar_diretorio_privado(alvo)
    antes=alvo.read_bytes()if arquivo else None
    r=diagnosticar(alvo)
    assert r['estado']=='leituras_coerentes',r
    assert r['politica_local']=='confere',r
    assert not r['autoriza_acesso']and r['alteracoes_realizadas']==0
    if arquivo:assert alvo.read_bytes()==antes


def test_assinaturas_usam_dword_de_32_bits_e_ponteiros_nativos(monkeypatch):
    class Funcao:
        argtypes=None;restype=None
    class DLL:
        def __getattr__(self,name):
            fn=Funcao();setattr(self,name,fn);return fn
    dlls={name:DLL()for name in ('advapi32','kernel32')}
    monkeypatch.setattr(c,'WinDLL',lambda name,**kwargs:dlls[name],raising=False)
    api=p._WindowsACL()
    assert api.a.GetNamedSecurityInfoW.restype is c.c_uint32
    assert api.a.GetNamedSecurityInfoW.argtypes[1:3]==[c.c_uint32,c.c_uint32]
    assert api.a.GetAce.argtypes==[c.c_void_p,c.c_uint32,c.POINTER(c.c_void_p)]
    assert api.a.GetTokenInformation.argtypes==[c.c_void_p,c.c_uint32,c.c_void_p,c.c_uint32,c.POINTER(c.c_uint32)]
    assert api.a.ConvertSidToStringSidW.argtypes==[c.c_void_p,c.POINTER(c.c_wchar_p)]
    assert api.k.LocalFree.argtypes==[c.c_void_p]and api.k.LocalFree.restype is c.c_void_p
    assert c.sizeof(c.c_uint32)==4 and c.sizeof(AceHeader)==4 and c.sizeof(AclHeader)==8
