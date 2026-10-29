"""Investiga descritores/objetos Windows sem mudar a política ou qualquer ACL."""
import base64
from collections import Counter
from contextlib import contextmanager
import ctypes as c
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

from conversor.adapters.private_permissions import _WindowsACL, _sem_redirecionamento, validar_acl, windows
from conversor.adapters.acl_binary import decodificar_descritor
from conversor.application.ports import ErroAplicacao

CLASSES=frozenset(('usuario','system','administradores','creator_owner','creator_group','owner_rights','everyone','authenticated_users','outra'))
ESPECIAIS={'S-1-5-18':'system','S-1-5-32-544':'administradores','S-1-3-0':'creator_owner',
           'S-1-3-1':'creator_group','S-1-3-4':'owner_rights','S-1-1-0':'everyone','S-1-5-11':'authenticated_users'}
FONTES={**{f'{api}_{mask}':(mask,origem) for mask in (5,7) for api,origem in
    (('Named','GetNamedSecurityInfoW'),('File','GetFileSecurityW'),('Handle','GetSecurityInfo'),('DotNet','FileSystemSecurity'))},
    'GetAcl':(None,'Get-Acl'),'GetAcl_depois':(None,'Get-Acl_apos_GetAccessRules'),
    'Python_Named_5':(5,'ctypes_GetNamedSecurityInfoW'),'Python_File_5':(5,'ctypes_GetFileSecurityW'),
    'Roundtrip_Raw_5':(5,'RawSecurityDescriptor_memoria'),'Roundtrip_Common_5':(5,'CommonSecurityDescriptor_memoria'),
    'Handle_5_depois':(5,'GetSecurityInfo'),
    'Named_5_selected':(5,'GetNamedSecurityInfoW_NULL_group_sacl'),
    'Python_Named_5_all':(5,'ctypes_GetNamedSecurityInfoW_all_outputs'),
    'Python_final_Named_5':(5,'GetNamedSecurityInfoW_python_final'),
    'Python_final_File_5':(5,'GetFileSecurityW_python_final'),
    'Python_final_Handle_5':(5,'GetSecurityInfo_python_final')}
CROSS_SOURCES=frozenset(('Python_final_Named_5','Python_final_File_5','Python_final_Handle_5'))
IDENTITY_CHECKS=('hmac_vetor_igual','layout_tamanho_igual','layout_offsets_iguais','volume_igual','indice_alto_igual',
    'indice_baixo_igual','serializacao_igual','identidade_total_igual','arquitetura_igual','usuario_processo_igual',
    'caminho_final_python_igual_csharp','caminho_python_igual_solicitado','caminho_csharp_igual_solicitado_normalizado',
    'pacote_python_verificavel','pacote_csharp_verificavel','pacote_python_presente','pacote_csharp_presente',
    'pacote_presenca_igual','token_appcontainer_verificavel','token_appcontainer_igual',
    'token_elevacao_verificavel','token_elevacao_igual','token_virtualizacao_verificavel','token_virtualizacao_igual',
    'reabertura_final_python_disponivel','reabertura_final_python_mesmo_objeto')


def digest(key,domain,data):
    if isinstance(data,str):data=data.encode('utf-8')
    return hmac.new(key,domain.encode()+b'\0'+data,'sha256').hexdigest()


def projetar(acl,key):
    return dict(usuario=digest(key,'sid',acl.usuario),proprietario=digest(key,'sid',acl.proprietario),
        dacl_presente=acl.dacl_presente,regras=[dict(tipo=e.tipo,flags=e.flags,mascara=f'0x{e.mascara:x}',
            identidade=digest(key,'sid',e.sid),classe='usuario'if e.sid==acl.usuario else ESPECIAIS.get(e.sid,'outra'))for e in acl.entradas])


class FileInfo(c.Structure):
    _fields_=[(name,c.c_uint32)for name in ('attributes','creation_low','creation_high','access_low','access_high',
        'write_low','write_high','volume','size_high','size_low','links','index_high','index_low')]


@contextmanager
def objeto_preservado(path,key):
    """Handle somente leitura, sem share-delete, durante toda a investigação."""
    k=c.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[c.c_wchar_p,c.c_uint32,c.c_uint32,c.c_void_p,c.c_uint32,c.c_uint32,c.c_void_p]
    k.CreateFileW.restype=c.c_void_p
    k.GetFileInformationByHandle.argtypes=[c.c_void_p,c.POINTER(FileInfo)];k.GetFileInformationByHandle.restype=c.c_int
    k.CloseHandle.argtypes=[c.c_void_p];k.CloseHandle.restype=c.c_int
    k.GetFinalPathNameByHandleW.argtypes=[c.c_void_p,c.c_wchar_p,c.c_uint32,c.c_uint32]
    k.GetFinalPathNameByHandleW.restype=c.c_uint32
    handle=k.CreateFileW(str(path),0x20080,3,None,3,0x02200000,None)
    if handle in (None,c.c_void_p(-1).value):raise ValueError('OBJETO_NAO_COMPROVADO')
    try:
        def conferir():
            info=FileInfo()
            if not k.GetFileInformationByHandle(handle,c.byref(info))or info.attributes&0x400:
                raise ValueError('OBJETO_NAO_COMPROVADO')
            final=c.create_unicode_buffer(32768);length=k.GetFinalPathNameByHandleW(handle,final,len(final),0)
            if not 0<length<len(final):raise ValueError('CAMINHO_FINAL_NAO_COMPROVADO')
            formatted=f'{info.volume:08x}:{info.index_high:08x}:{info.index_low:08x}'
            offsets=','.join(str(getattr(FileInfo,n).offset)for n,_ in FileInfo._fields_)
            return dict(identidade=digest(key,'objeto',formatted),serializacao=digest(key,'objeto_formatacao',formatted),
                volume=digest(key,'objeto_volume',f'{info.volume:08x}'),
                indice_alto=digest(key,'objeto_indice_alto',f'{info.index_high:08x}'),
                indice_baixo=digest(key,'objeto_indice_baixo',f'{info.index_low:08x}'),
                layout_tamanho=str(c.sizeof(FileInfo)),layout_offsets=digest(key,'layout_offsets',offsets),
                caminho_final=final.value,ponteiro_bits=str(c.sizeof(c.c_void_p)*8))
        yield conferir
    finally:k.CloseHandle(handle)


def named_todas_saidas(api,path):
    """Varia somente ponteiros opcionais; o leitor normal não é alterado."""
    pointers=[c.c_void_p()for _ in range(5)]
    code=api.a.GetNamedSecurityInfoW(str(path),1,5,*(c.byref(p)for p in pointers))
    sd=pointers[-1]
    try:
        if code or not sd.value:raise ValueError('DESCRITOR_NAO_COMPROVADO')
        size=api.a.GetSecurityDescriptorLength(sd)
        if not 20<=size<=1048576:raise ValueError('DESCRITOR_NAO_COMPROVADO')
        return c.string_at(sd,size)
    finally:
        if sd.value:api.k.LocalFree(sd)


def contexto_processo(api):
    """Metadados locais; nenhum nome de pacote, SID ou token é devolvido."""
    result={}
    try:
        fn=api.k.GetCurrentPackageFullName
        fn.argtypes=[c.POINTER(c.c_uint32),c.c_wchar_p];fn.restype=c.c_int32
        size=c.c_uint32();code=fn(c.byref(size),None)
        result.update(pacote_verificavel='1'if code in (122,15700)else'0',pacote_presente='1'if code==122 and size.value>0 else'0')
    except (AttributeError,OSError):result.update(pacote_verificavel='0',pacote_presente='0')
    token=c.c_void_p()
    if api.a.OpenProcessToken(api.k.GetCurrentProcess(),8,c.byref(token)):
        try:
            for label,kind in (('appcontainer',29),('elevacao',20),('virtualizacao',24)):
                value=c.c_uint32();size=c.c_uint32()
                ok=api.a.GetTokenInformation(token,kind,c.byref(value),4,c.byref(size))and size.value==4 and value.value in (0,1)
                result['token_'+label+'_verificavel']='1'if ok else'0'
                result['token_'+label]='1'if ok and value.value else'0'
        finally:api.k.CloseHandle(token)
    return result


def executar_probe(path,key,nome,arquivo,*,named_all=None,meta=None):
    script=Path(__file__).with_name('acl_probe.ps1')
    env=os.environ|{'CONVERSOR_ACL_DIAG_PATH':str(path),'CONVERSOR_ACL_PROBE_CS':str(script.with_suffix('.cs'))}
    exe=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    # Descritores e chave só em stdin; não são argumentos, variáveis persistentes ou arquivos.
    payload={k:base64.b64encode(v).decode('ascii')for k,v in dict(chave=key,named=nome,file=arquivo,named_all=nome if named_all is None else named_all).items()}
    payload['meta']=meta or {}
    r=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-Command',script.read_text(encoding='utf-8')],
        input=json.dumps(payload).encode('ascii'),env=env,capture_output=True,timeout=90,check=False)
    if len(r.stdout)>1024*1024:raise ValueError('PROBE_WINDOWS_NAO_COMPROVADO')
    data=json.loads(r.stdout.decode('utf-8-sig'))
    if r.returncode or 'erro'in data:
        # Nada do stderr/erro bruto é devolvido. Etapas são enums próprios.
        stages=('entrada','compilacao','leitura')
        stage=data.get('etapa')if data.get('etapa')in stages else'indisponivel'
        raise FalhaProbe(stage)
    return data


class FalhaProbe(ValueError):
    def __init__(self,etapa):self.etapa=etapa


def _id(v):return isinstance(v,str)and re.fullmatch('[0-9a-f]{64}',v)is not None


def saidas_opcionais(name):
    if 'Named'in name or name.startswith('Roundtrip_'):
        selected=name in ('Named_5_selected','Python_Named_5')
        return dict(owner=True,group=not selected,dacl=True,sacl=not selected)
    return None


def regras_validas(rules):
    if not isinstance(rules,list)or len(rules)>4096:raise ValueError('PROJECAO_INVALIDA')
    out=[]
    for r in rules:
        if not isinstance(r,dict):raise ValueError('PROJECAO_INVALIDA')
        if (type(r.get('tipo'))is not int or not 0<=r['tipo']<=255 or type(r.get('flags'))is not int or
            not 0<=r['flags']<=255 or not isinstance(r.get('mascara'),str)or
            not re.fullmatch('0x[0-9a-f]{1,8}',r['mascara'])or not _id(r.get('identidade'))or r.get('classe')not in CLASSES):
            raise ValueError('PROJECAO_INVALIDA')
        out.append({k:r[k]for k in ('tipo','flags','mascara','identidade','classe')})
    return out


def validar_resposta(raw):
    if not isinstance(raw,dict):raise ValueError('PROJECAO_INVALIDA')
    out={}
    for k in ('caminho_solicitado_hmac','caminho_final_hmac','objeto_antes_hmac','objeto_depois_hmac'):
        if not _id(raw.get(k)):raise ValueError('PROJECAO_INVALIDA')
        out[k]=raw[k]
    for k in ('identidade_efetiva_igual_processo','diretorio','caminho_final_igual_solicitado','handle_sem_share_delete','handle_estavel'):
        if type(raw.get(k))is not bool:raise ValueError('PROJECAO_INVALIDA')
        out[k]=raw[k]
    if (type(raw.get('ponteiro_bits'))is not int or raw['ponteiro_bits']not in (32,64)or
        type(raw.get('objeto_tipo'))is not int or raw['objeto_tipo']!=1):raise ValueError('PROJECAO_INVALIDA')
    out['ponteiro_bits']=raw['ponteiro_bits'];out['objeto_tipo']=1;out['fontes']={}
    if set(raw['fontes'])!=set(FONTES):raise ValueError('PROJECAO_PARCIAL')
    for name,(mask,origin)in FONTES.items():
        f=raw['fontes'][name]
        parametro=f.get('security_information')
        if ((mask is None and parametro is not None)or(mask is not None and (type(parametro)is not int or parametro!=mask))or
            f.get('origem')!=origin):raise ValueError('PARAMETROS_DIVERGENTES')
        item=dict(security_information=mask,origem=origin)
        outputs=f.get('saidas_opcionais');expected=saidas_opcionais(name)
        if outputs!=expected or (outputs is not None and any(type(v)is not bool for v in outputs.values())):
            raise ValueError('PONTEIROS_DIVERGENTES')
        item['saidas_opcionais']=expected
        if f.get('estado')=='nao_comprovado':item['estado']='nao_comprovado'
        elif f.get('estado')=='ok':
            item['estado']='ok'
            for k in ('binario_hmac','dacl_hmac','usuario','proprietario','grupo'):
                if not _id(f.get(k)):raise ValueError('PROJECAO_INVALIDA')
                item[k]=f[k]
            if (type(f.get('control_flags'))is not int or not 0<=f['control_flags']<=65535 or
                type(f.get('bytes'))is not int or not 20<=f['bytes']<=1048576 or type(f.get('dacl_presente'))is not bool):
                raise ValueError('PROJECAO_INVALIDA')
            for k in ('control_flags','bytes','dacl_presente'):item[k]=f[k]
            item['controle_decodificado']=dict(dacl_protegida=bool(f['control_flags']&0x1000),
                dacl_auto_herdada=bool(f['control_flags']&0x400),
                heranca_automatica_solicitada=bool(f['control_flags']&0x100),
                self_relative=bool(f['control_flags']&0x8000))
            item['regras']=regras_validas(f['regras']);item['GetAce']=regras_validas(f['GetAce'])
        else:raise ValueError('PROJECAO_INVALIDA')
        out['fontes'][name]=item
    checks=raw['comparacao_identidade']
    if set(checks)!=set(IDENTITY_CHECKS)or any(type(v)is not bool for v in checks.values()):raise ValueError('IDENTIDADE_PARCIAL')
    out['comparacao_identidade']={k:checks[k]for k in IDENTITY_CHECKS}
    out['GetAccessRules']=regras_validas(raw['GetAccessRules'])
    return out


def chave_regra(r,*,sem_herdada=False):
    return (r['tipo'],r['flags']&~16 if sem_herdada else r['flags'],r['mascara'],r['identidade'])


def comparar(a,b):
    if a.get('estado')!='ok'or b.get('estado')!='ok':return dict(estado='nao_comprovado')
    exact=Counter(map(chave_regra,a['regras']))==Counter(map(chave_regra,b['regras']))
    no_inherit=Counter(chave_regra(r,sem_herdada=True)for r in a['regras'])==Counter(chave_regra(r,sem_herdada=True)for r in b['regras'])
    return dict(estado='comparado',binario_igual=a['binario_hmac']==b['binario_hmac'],
        dacl_binaria_igual=a['dacl_hmac']==b['dacl_hmac'],owner_igual=a['proprietario']==b['proprietario'],
        grupo_igual=a['grupo']==b['grupo'],controle_igual=a['control_flags']==b['control_flags'],
        usuario_igual=a['usuario']==b['usuario'],dacl_presente_igual=a['dacl_presente']==b['dacl_presente'],
        regras_iguais=exact,diferenca_apenas_bit_herdada=not exact and no_inherit,
        classes_a=sorted(Counter(r['classe']for r in a['regras']).items()),
        classes_b=sorted(Counter(r['classe']for r in b['regras']).items()))


def avaliar_probe(probe,objeto,python_models):
    sources=probe['fontes']
    pairs=[('Named_5',name)for name in sources if name!='Named_5']+[
        ('Named_7','DotNet_7'),('Handle_7','GetAcl'),('GetAcl','GetAcl_depois'),('Handle_5','Handle_5_depois'),
        ('Python_Named_5','Python_Named_5_all'),('Python_Named_5','Python_final_Named_5'),
        ('Python_File_5','Python_final_File_5')]
    comparisons={a+'__'+b:comparar(sources[a],sources[b])for a,b in pairs}
    identity=probe['comparacao_identidade']
    object_checks=dict(csharp_aberturas_iguais=probe['objeto_antes_hmac']==probe['objeto_depois_hmac'],
        python_igual_csharp_antes=probe['objeto_antes_hmac']==objeto,python_igual_csharp_depois=probe['objeto_depois_hmac']==objeto,
        csharp_handle_estavel=probe['handle_estavel'],csharp_caminho_final_literal_igual=probe['caminho_final_igual_solicitado'],
        handle_sem_share_delete=probe['handle_sem_share_delete'],identidade_efetiva_igual_processo=probe['identidade_efetiva_igual_processo'])
    required=('hmac_vetor_igual','layout_tamanho_igual','layout_offsets_iguais','volume_igual','indice_alto_igual',
        'indice_baixo_igual','serializacao_igual','identidade_total_igual','usuario_processo_igual','caminho_final_python_igual_csharp')
    object_ok=(all(object_checks[k]for k in object_checks if k!='csharp_caminho_final_literal_igual')and
        identity['caminho_csharp_igual_solicitado_normalizado']and all(identity[k]for k in required))
    csharp_parsers={name:Counter(map(chave_regra,f['regras']))==Counter(map(chave_regra,f['GetAce']))for name,f in sources.items()if f['estado']=='ok'}
    python_parsers={}
    for name,model in python_models.items():
        f=sources[name];python_parsers[name]=(f['estado']=='ok'and all(model[k]==f[k]for k in ('usuario','proprietario','dacl_presente'))and
            Counter(map(chave_regra,model['regras']))==Counter(map(chave_regra,f['regras'])))
    ps=sources['GetAcl']
    dotnet_projection=(ps['estado']=='ok'and Counter(map(chave_regra,ps['regras']))==Counter(map(chave_regra,probe['GetAccessRules'])))
    # A igualdade sem o bit de herança é somente diagnóstica. Nunca concede acesso.
    complete=all(f['estado']=='ok'for name,f in sources.items()if name not in CROSS_SOURCES)
    stable=comparisons['Handle_5__Handle_5_depois'].get('binario_igual',False)and comparisons['GetAcl__GetAcl_depois'].get('binario_igual',False)
    return dict(objeto_e_identidade_comprovados=object_ok,leituras_completas=complete,descritores_estaveis=stable,
        comparacao_objeto=object_checks|identity,leituras_caminho_fisico_completas=all(sources[n]['estado']=='ok'for n in CROSS_SOURCES),
        comparacoes=comparisons,parsers_csharp_concordam=csharp_parsers,parsers_python_concordam=python_parsers,
        getaccessrules_igual_raw=dotnet_projection)


def investigar(path):
    base=dict(versao='investigacao_acl@3',alteracoes_realizadas=0,autoriza_acesso=False,causa_confirmada=False,
        situacao='investigacao_pendente',limite='Somente evidências de leitura; padrões de herança não aprovam ACLs ou vínculos.')
    if not windows():return base|dict(codigo='EXIGE_WINDOWS_NATIVO')
    etapa='caminho'
    try:
        path=Path(os.path.abspath(path));_sem_redirecionamento(path);key=secrets.token_bytes(32)
        etapa='identidade_objeto'
        with objeto_preservado(path,key)as identity:
            snapshot=identity();before=snapshot['identidade'];etapa='leituras_python';api=_WindowsACL();user=api.usuario()
            named=api._snapshot_nome(path);file=api._snapshot_arquivo(path)
            n=decodificar_descritor(named,user);f=decodificar_descritor(file,user);g=api._projetar_getace(named,user)
            all_outputs=named_todas_saidas(api,path);a=decodificar_descritor(all_outputs,user)
            models={'Python_Named_5':projetar(n,key),'Python_File_5':projetar(f,key),'Python_Named_5_all':projetar(a,key)}
            meta=snapshot|contexto_processo(api)|dict(usuario=digest(key,'sid',user),hmac_vetor=digest(key,'instrumentacao',bytes((0,1,127,128,255))))
            etapa='probe_mesmo_processo_windows';probe=validar_resposta(executar_probe(path,key,named,file,named_all=all_outputs,meta=meta))
            checks=avaliar_probe(probe,before,models)
            checks['comparacao_objeto']['python_handle_estavel']=identity()['identidade']==before
            checks['objeto_e_identidade_comprovados'] &= checks['comparacao_objeto']['python_handle_estavel']
            checks['GetAce_python_igual_binario']=projetar(n,key)==projetar(g,key)
            checks['binarios_python_preservados']=(digest(key,'sd',named)==probe['fontes']['Python_Named_5'].get('binario_hmac')and
                digest(key,'sd',file)==probe['fontes']['Python_File_5'].get('binario_hmac')and
                digest(key,'sd',all_outputs)==probe['fontes']['Python_Named_5_all'].get('binario_hmac'))
            checks['python_named_estavel']=api._snapshot_nome(path)==named
            checks['python_file_estavel']=api._snapshot_arquivo(path)==file
            checks['descritores_estaveis'] &= checks['python_named_estavel']and checks['python_file_estavel']
            _sem_redirecionamento(path)
        policy='confere'
        try:validar_acl(n)
        except ErroAplicacao as e:policy=str(e)
        return base|dict(politica_python=policy,evidencias=checks,probe=probe)
    except FalhaProbe as e:return base|dict(codigo='PROBE_WINDOWS_NAO_COMPROVADO',etapa=e.etapa)
    except Exception:return base|dict(codigo='INVESTIGACAO_NAO_COMPROVADA',etapa=etapa)
