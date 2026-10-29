"""Decodificação limitada de descritores Windows self-relative; nenhum ponteiro."""
from collections import Counter
from struct import unpack_from


def sid_binario(data, offset=0, *, fim=None):
    fim=len(data)if fim is None else fim
    if offset<0 or fim>len(data) or offset+8>fim:raise ValueError('SID_TRUNCADO')
    rev,n=data[offset:offset+2]
    if rev!=1 or n>15:raise ValueError('SID_INVALIDO')
    end=offset+8+4*n
    if end>fim:raise ValueError('SID_FORA_DO_LIMITE')
    autoridade=int.from_bytes(data[offset+2:offset+8],'big')
    autoridade=str(autoridade)if autoridade<2**32 else f'0x{autoridade:012x}'
    sub=unpack_from('<'+'I'*n,data,offset+8)if n else ()
    return 'S-1-'+autoridade+''.join('-'+str(x)for x in sub),end


def decodificar_descritor(data, usuario):
    from .private_permissions import AclPrivada,AcePrivada
    if len(data)<20:raise ValueError('DESCRITOR_TRUNCADO')
    rev,_,control,owner,group,sacl,dacl=unpack_from('<BBHIIII',data)
    if rev!=1 or not control&0x8000:raise ValueError('DESCRITOR_NAO_RELATIVO')
    if owner<20 or owner%4:raise ValueError('OWNER_INVALIDO')
    proprietario,_=sid_binario(data,owner)
    presente=bool(control&4 and dacl)
    entradas=[]
    if presente:
        if dacl<20 or dacl%4 or dacl+8>len(data):raise ValueError('DACL_FORA_DO_LIMITE')
        aclrev,_,size,count,_=unpack_from('<BBHHH',data,dacl)
        fim=dacl+size
        if aclrev not in (2,4) or size<8 or fim>len(data):raise ValueError('DACL_INVALIDA')
        pos=dacl+8
        for _ in range(count):
            if pos+4>fim:raise ValueError('ACE_TRUNCADA')
            tipo,flags,tamanho=unpack_from('<BBH',data,pos)
            if tamanho<4 or tamanho%4 or pos+tamanho>fim:raise ValueError('ACE_FORA_DO_LIMITE')
            if tipo in (0,1):
                if tamanho<16:raise ValueError('ACE_ALLOW_INVALIDA')
                mask=unpack_from('<I',data,pos+4)[0]
                sid,end=sid_binario(data,pos+8,fim=pos+tamanho)
                if end!=pos+tamanho:raise ValueError('ACE_SID_TAMANHO_DIVERGENTE')
                entradas.append(AcePrivada(tipo,flags,mask,sid))
            else:
                entradas.append(AcePrivada(tipo,flags,0,''))  # Não aprovar ACE desconhecida.
            pos+=tamanho
    return AclPrivada(usuario,proprietario,presente,tuple(entradas))


def mesmas_regras(a,b):
    return (a.usuario,a.proprietario,a.dacl_presente,Counter(a.entradas))==(b.usuario,b.proprietario,b.dacl_presente,Counter(b.entradas))
