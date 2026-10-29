"""Comparação local de ACL, somente leitura; saída sem SIDs, contas ou caminhos."""
from collections import Counter
import base64
import hmac
import json
import os
from pathlib import Path
import secrets
import re
import subprocess

from conversor.adapters.private_permissions import _WindowsACL,validar_acl,_sem_redirecionamento,windows
from conversor.adapters.acl_binary import decodificar_descritor
from conversor.application.ports import ErroAplicacao

# O segredo efêmero só correlaciona identidades nesta execução; não é persistido.
POWERSHELL = r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$h=[Security.Cryptography.HMACSHA256]::new()
$h.Key=[Convert]::FromBase64String($env:CONVERSOR_ACL_DIAG_KEY)
function Id([string]$s){return ([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant()}
function Classe([string]$sid,[string]$u){if($sid -eq $u){return 'usuario'};if($sid -eq 'S-1-5-18'){return 'system'};if($sid -eq 'S-1-5-32-544'){return 'administradores'};return 'outra'}
$a=Get-Acl -LiteralPath $env:CONVERSOR_ACL_DIAG_PATH
$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$o=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value
$raw=[Security.AccessControl.RawSecurityDescriptor]::new($a.GetSecurityDescriptorBinaryForm(),0)
$rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | ForEach-Object {
 $sid=$_.IdentityReference.Value;$f=0
 if(([int]$_.InheritanceFlags -band 1) -ne 0){$f=$f -bor 2}
 if(([int]$_.InheritanceFlags -band 2) -ne 0){$f=$f -bor 1}
 if(([int]$_.PropagationFlags -band 1) -ne 0){$f=$f -bor 4}
 if(([int]$_.PropagationFlags -band 2) -ne 0){$f=$f -bor 8}
 if($_.IsInherited){$f=$f -bor 16}
 @{tipo=[int]$_.AccessControlType;flags=$f;mascara=('0x{0:x}' -f ([uint32]([int64]$_.FileSystemRights -band 4294967295)));identidade=(Id ("sid`0"+$sid));classe=(Classe $sid $u)}
})
@{usuario=(Id ("sid`0"+$u));proprietario=(Id ("sid`0"+$o));dacl_presente=(($null -ne $raw.DiscretionaryAcl) -and (([int]$raw.ControlFlags -band 4) -ne 0));regras=$rules;regras_raw_count=$(if($null -eq $raw.DiscretionaryAcl){0}else{$raw.DiscretionaryAcl.Count})} | ConvertTo-Json -Compress -Depth 6
$h.Dispose()
'''


def _id(key,sid):
    return hmac.new(key,('sid\0'+sid).encode(),'sha256').hexdigest()


def _publico(acl,key):
    def classe(sid):
        return 'usuario'if sid==acl.usuario else'system'if sid=='S-1-5-18'else'administradores'if sid=='S-1-5-32-544'else'outra'
    return dict(usuario=_id(key,acl.usuario),proprietario=_id(key,acl.proprietario),dacl_presente=acl.dacl_presente,
        regras=[dict(tipo=e.tipo,flags=e.flags,mascara=f'0x{e.mascara:x}',identidade=_id(key,e.sid),classe=classe(e.sid))for e in acl.entradas])


def _chaves(fonte):
    return Counter((r['tipo'],r['flags'],r['mascara'],r['identidade'])for r in fonte['regras'])


def comparar_modelos(fontes):
    """Somente identidades efêmeras; preserva duplicatas, distingue ordem/representação."""
    nomes=tuple(fontes);base=fontes[nomes[0]];checks={}
    for nome,f in fontes.items():
        checks[nome]=dict(usuario_igual=f['usuario']==base['usuario'],proprietario_igual=f['proprietario']==base['proprietario'],
            dacl_igual=f['dacl_presente']==base['dacl_presente'],regras_iguais=_chaves(f)==_chaves(base),
            ordem_igual=f['regras']==base['regras'],total_regras=len(f['regras']),
            identidades_adicionais=sum(r['classe']=='outra'for r in f['regras']),
            tipos_nao_suportados=sum(r['tipo']!=0 for r in f['regras']))
    coerente=all(all(c[k]for k in ('usuario_igual','proprietario_igual','dacl_igual','regras_iguais'))for c in checks.values())
    return checks,coerente


def _powershell(path,key):
    executable=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    env=os.environ|{'CONVERSOR_ACL_DIAG_PATH':str(path),'CONVERSOR_ACL_DIAG_KEY':base64.b64encode(key).decode()}
    r=subprocess.run([str(executable),'-NoProfile','-NonInteractive','-Command',POWERSHELL],env=env,
        capture_output=True,timeout=45,check=False)
    if r.returncode or len(r.stdout)>1024*1024:raise ValueError('POWERSHELL_INDISPONIVEL')
    return json.loads(r.stdout.decode('utf-8-sig'))


def _validar_projecao(ps):
    def id_valido(v):return isinstance(v,str)and re.fullmatch('[0-9a-f]{64}',v)
    if not id_valido(ps['usuario'])or not id_valido(ps['proprietario'])or type(ps['dacl_presente'])is not bool:
        raise ValueError('PROJECAO_INVALIDA')
    if not isinstance(ps['regras'],list)or len(ps['regras'])>16000:raise ValueError('PROJECAO_INVALIDA')
    regras=[]
    for r in ps['regras']:
        if (type(r['tipo'])is not int or type(r['flags'])is not int or not 0<=r['flags']<=255 or
            not re.fullmatch('0x[0-9a-f]{1,8}',r['mascara'])or not id_valido(r['identidade'])or
            r['classe']not in ('usuario','system','administradores','outra')):raise ValueError('PROJECAO_INVALIDA')
        regras.append({k:r[k]for k in ('tipo','flags','mascara','identidade','classe')})
    return dict(usuario=ps['usuario'],proprietario=ps['proprietario'],dacl_presente=ps['dacl_presente'],regras=regras)


def diagnosticar(path):
    base=dict(versao='comparacao_acl@1',alteracoes_realizadas=0,autoriza_acesso=False)
    if not windows():return base|dict(estado='indisponivel',codigo='COMPARACAO_NATIVA_EXIGE_WINDOWS')
    etapa='caminho'
    try:
        path=Path(os.path.abspath(path));_sem_redirecionamento(path)
        etapa='identidade_do_processo'
        api=_WindowsACL();key=secrets.token_bytes(32);user=api.usuario()
        etapa='GetNamedSecurityInfo'
        nome=api._snapshot_nome(path)
        etapa='GetFileSecurity'
        arquivo=api._snapshot_arquivo(path)
        etapa='decodificacao_e_GetAce'
        n=decodificar_descritor(nome,user);f=decodificar_descritor(arquivo,user);g=api._projetar_getace(nome,user)
        fontes={'GetNamedSecurityInfo_binario':_publico(n,key),'GetFileSecurity_binario':_publico(f,key),'GetAce_buffer_copiado':_publico(g,key)}
        etapa='PowerShell_GetAccessRules'
        ps=_powershell(path,key)
        # Copiar apenas os campos conhecidos; nenhuma saída bruta de subprocesso é devolvida.
        fontes['PowerShell_GetAccessRules']=_validar_projecao(ps)
        if ps['regras_raw_count']!=len(ps['regras']):raise ValueError('PROJECAO_DOTNET_PARCIAL')
        checks,coerente=comparar_modelos(fontes)
        politica='nao_comprovada'
        try:
            validar_acl(n);politica='confere'
        except ErroAplicacao as e:politica=str(e)
        return base|dict(estado='leituras_coerentes'if coerente else'leituras_divergentes',comparacoes=checks,
            politica_local=politica,modelos=fontes,
            limite='Diagnóstico somente de leitura. Identidades são HMACs efêmeros; não comparar IDs entre execuções. Uma divergência não libera acesso nem altera a ACL.')
    except Exception:
        return base|dict(estado='nao_comprovado',codigo='COMPARACAO_ACL_INDISPONIVEL_OU_DIVERGENTE',etapa=etapa)
