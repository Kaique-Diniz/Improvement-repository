"""Diagnóstico somente de leitura; dados e identidades inteiramente sintéticos."""
from contextlib import contextmanager
from copy import deepcopy
import ctypes as c
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from conversor.adapters import private_permissions as p
from conversor.diagnostics import windows_acl as d
from conversor import private_security
from conversor.application.ports import ErroAplicacao
from tests.test_windows_acl_reader import USER,OTHER,SD,EXPECTED,backend,MemoriaWindows

KEY=b'ephemeral test only key 000000000'
OBJ=d.digest(KEY,'objeto','synthetic identity')


def model():
    m=d.projetar(EXPECTED,KEY)
    return m|dict(estado='ok',bytes=136,binario_hmac=d.digest(KEY,'sd',SD),dacl_hmac='d'*64,
        control_flags=0x8004,grupo='e'*64,GetAce=m['regras'])


def probe():
    return dict(caminho_solicitado_hmac='a'*64,caminho_final_hmac='a'*64,objeto_antes_hmac=OBJ,objeto_depois_hmac=OBJ,
        identidade_efetiva_igual_processo=True,diretorio=True,caminho_final_igual_solicitado=True,handle_sem_share_delete=True,
        handle_estavel=True,ponteiro_bits=64,objeto_tipo=1,
        fontes={name:model()|dict(security_information=mask,origem=origin)for name,(mask,origin)in d.FONTES.items()},
        GetAccessRules=model()['regras'])


def test_principais_especiais_sao_identificados_sem_virar_usuario_ou_serem_aprovados():
    for sid,kind in [('S-1-3-0','creator_owner'),('S-1-3-4','owner_rights'),('S-1-1-0','everyone'),(OTHER,'outra')]:
        acl=p.AclPrivada(USER,USER,True,EXPECTED.entradas+(p.AcePrivada(0,3,p.FULL_CONTROL,sid),))
        safe=d.projetar(acl,KEY)
        assert safe['regras'][-1]['classe']==kind
        assert sid not in json.dumps(safe)
        with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_INSEGURA'):p.validar_acl(acl)


def test_flags_3_e_19_so_sao_diferenca_de_heranca_se_sid_mascara_tipo_tambem_coincidem():
    a=model();b=deepcopy(a)
    for r in a['regras']:r['flags']=3
    for r in b['regras']:r['flags']=19
    c=d.comparar(a,b)
    assert c['diferenca_apenas_bit_herdada']and not c['regras_iguais']
    b['regras'][2]['classe']='creator_owner';b['regras'][2]['identidade']='f'*64
    assert not d.comparar(a,b)['diferenca_apenas_bit_herdada']


@pytest.mark.parametrize('field,value',[('tipo',1),('mascara','0x120089'),('flags',11),('identidade','f'*64)])
def test_outros_deltas_nao_sao_normalizados_como_heranca(field,value):
    a=model();b=deepcopy(a);b['regras'][2][field]=value
    assert not d.comparar(a,b)['diferenca_apenas_bit_herdada']


def test_bytes_controle_e_grupo_sao_distintos_da_igualdade_das_aces():
    a=model();b=deepcopy(a);b['binario_hmac']='f'*64;b['grupo']='f'*64;b['control_flags']|=0x400
    c=d.comparar(a,b)
    assert c['regras_iguais']and not c['binario_igual']and not c['grupo_igual']and not c['controle_igual']


def test_ace_duplicada_nunca_desaparece_na_comparacao():
    a=model();b=deepcopy(a);b['regras'].append(b['regras'][0])
    assert not d.comparar(a,b)['regras_iguais']


def test_whitelist_descarta_campos_brutos_injetados():
    raw=probe();raw['SENTINELA_SECRETA']=USER
    raw['fontes']['Named_5']['SDDL']='SENTINELA_SECRETA'
    raw['fontes']['Named_5']['regras'][0]['conta']='SENTINELA_SECRETA'
    safe=d.validar_resposta(raw)
    assert 'SENTINELA'not in json.dumps(safe)and 'S-1-'not in json.dumps(safe)


@pytest.mark.parametrize('alteracao', ['fonte_ausente','sid_bruto','origem','mascara_parametro','tipo','controle','objeto_tipo'])
def test_resposta_parcial_ou_nao_sanitizada_e_rejeitada(alteracao):
    raw=probe()
    if alteracao=='fonte_ausente':del raw['fontes']['File_5']
    if alteracao=='sid_bruto':raw['fontes']['Named_5']['regras'][0]['identidade']=USER
    if alteracao=='origem':raw['fontes']['Named_5']['origem']='Outra API'
    if alteracao=='mascara_parametro':raw['fontes']['Named_5']['security_information']=7
    if alteracao=='tipo':raw['fontes']['Named_5']['regras'][0]['tipo']='allow'
    if alteracao=='controle':raw['fontes']['Named_5']['control_flags']=65536
    if alteracao=='objeto_tipo':raw['objeto_tipo']=2
    with pytest.raises(ValueError):d.validar_resposta(raw)


def test_consistencia_identidade_parser_e_projecao_dotnet_nao_e_aprovacao():
    safe=d.validar_resposta(probe())
    result=d.avaliar_probe(safe,OBJ,{'Python_Named_5':d.projetar(EXPECTED,KEY)})
    assert result['objeto_e_identidade_comprovados']and result['leituras_completas']and result['descritores_estaveis']
    assert all(result['parsers_csharp_concordam'].values())and all(result['parsers_python_concordam'].values())
    assert result['getaccessrules_igual_raw']
    assert 'autoriza_acesso'not in result


@pytest.mark.parametrize('kind',['objeto','impersonacao','path','alteracao_acl','projecao_parcial','parser'])
def test_mesmo_nome_nao_basta_para_comprovar_objeto_ou_leitura(kind):
    r=probe()
    if kind=='objeto':r['objeto_depois_hmac']='f'*64
    if kind=='impersonacao':r['identidade_efetiva_igual_processo']=False
    if kind=='path':r['caminho_final_igual_solicitado']=False
    if kind=='alteracao_acl':r['fontes']['Handle_5_depois']['binario_hmac']='f'*64
    if kind=='projecao_parcial':r['fontes']['File_5']['estado']='nao_comprovado'
    if kind=='parser':r['fontes']['Named_5']['GetAce']=[]
    result=d.avaliar_probe(d.validar_resposta(r),OBJ,{'Python_Named_5':d.projetar(EXPECTED,KEY)})
    assert (not result['objeto_e_identidade_comprovados']or not result['leituras_completas']or
        not result['descritores_estaveis']or not all(result['parsers_csharp_concordam'].values()))


def preparar(monkeypatch):
    @contextmanager
    def obj(path,key):yield lambda:OBJ
    monkeypatch.setattr(d,'windows',lambda:True);monkeypatch.setattr(d,'objeto_preservado',obj)
    monkeypatch.setattr(d.secrets,'token_bytes',lambda n:KEY)
    monkeypatch.setattr(d,'_WindowsACL',lambda:backend(MemoriaWindows()))
    monkeypatch.setattr(d,'executar_probe',lambda *a:probe())


def test_investigacao_nao_declara_causa_resolvida_nem_muda_arquivos(tmp_path,monkeypatch):
    f=tmp_path/'SENTINELA_PRIVADA';f.write_bytes(b'SENTINELA ORIGINAL')
    preparar(monkeypatch);r=d.investigar(f)
    assert not r['causa_confirmada']and not r['autoriza_acesso']and r['situacao']=='investigacao_pendente'
    assert r['evidencias']['binarios_python_preservados']and r['evidencias']['GetAce_python_igual_binario']
    assert f.read_bytes()==b'SENTINELA ORIGINAL'
    assert 'SENTINELA'not in json.dumps(r)and USER not in json.dumps(r)and str(tmp_path)not in json.dumps(r)


def test_backend_ou_subprocesso_falhando_nunca_vaza_erro_bruto(tmp_path,monkeypatch):
    preparar(monkeypatch)
    def falhar(*a):raise RuntimeError(USER+' SENTINELA_PRIVADA '+str(tmp_path))
    monkeypatch.setattr(d,'executar_probe',falhar)
    r=d.investigar(tmp_path)
    assert r['codigo']=='INVESTIGACAO_NAO_COMPROVADA'
    assert 'SENTINELA'not in str(r)and USER not in str(r)


def test_nao_windows_e_explicito_e_nao_tenta_emular_sucesso(monkeypatch):
    monkeypatch.setattr(d,'windows',lambda:False)
    r=d.investigar('SENTINELA')
    assert r['codigo']=='EXIGE_WINDOWS_NATIVO'and not r['causa_confirmada']


def test_cli_de_investigacao_e_sempre_pendente(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['audit','--private-dir','SENTINELA','--investigar-heranca'])
    monkeypatch.setattr(d,'investigar',lambda _:dict(situacao='investigacao_pendente',autoriza_acesso=False))
    assert private_security.main()==2
    assert 'SENTINELA'not in capsys.readouterr().out


def test_payload_binario_so_transita_em_stdin_e_nao_ha_bypass_da_politica_powershell(monkeypatch):
    monkeypatch.setenv('SystemRoot','C:/Windows')
    def run(args,**kw):
        assert 'SENTINELA'not in ' '.join(args)and '-ExecutionPolicy'not in args
        assert kw['env']['CONVERSOR_ACL_DIAG_PATH']=='SENTINELA'
        assert args[-1]==Path(d.__file__).with_name('acl_probe.ps1').read_text()
        payload=json.loads(kw['input']);assert set(payload)=={'named','file','chave'}
        return SimpleNamespace(returncode=0,stdout=json.dumps(probe()).encode(),stderr=b'')
    monkeypatch.setattr(d.subprocess,'run',run)
    assert d.executar_probe('SENTINELA',KEY,SD,SD)['objeto_tipo']==1


def test_erro_de_compilacao_revela_somente_etapa_enumerada(monkeypatch):
    monkeypatch.setenv('SystemRoot','C:/Windows')
    monkeypatch.setattr(d.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=2,
        stdout=b'{"erro":"SENTINELA_PRIVADA","etapa":"compilacao","conta":"SENTINELA"}',stderr=b'SENTINELA'))
    with pytest.raises(d.FalhaProbe)as e:d.executar_probe('sintetico',KEY,SD,SD)
    assert e.value.etapa=='compilacao'and 'SENTINELA'not in str(e.value)


def test_handle_de_leitura_fecha_e_identidade_nao_expoe_fileid(monkeypatch):
    class Fn:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*a):return self.fn(*a)
    closed=[]
    def abrir(path,access,share,attrs,disposition,flags,template):
        assert access==0x20080 and share==3 and disposition==3 and flags==0x02200000
        return 123
    def info(handle,out):
        f=c.cast(out,c.POINTER(d.FileInfo))[0];f.volume=1;f.index_high=2;f.index_low=3;f.attributes=16
        return 1
    dll=SimpleNamespace(CreateFileW=Fn(abrir),GetFileInformationByHandle=Fn(info),CloseHandle=Fn(lambda h:closed.append(h)))
    monkeypatch.setattr(c,'WinDLL',lambda *a,**kw:dll,raising=False)
    with pytest.raises(RuntimeError):
        with d.objeto_preservado('sintetico',KEY)as identity:
            assert identity()==d.digest(KEY,'objeto','00000001:00000002:00000003')
            raise RuntimeError('sintetico')
    assert closed==[123]and c.sizeof(d.FileInfo)==52


NATIVE=pytest.mark.skipif(os.name!='nt',reason='Exige Win32/.NET/PowerShell nativos. Linux não comprova transformações de herança.')


@NATIVE
@pytest.mark.parametrize('scenario',['explicita','herdada','creator_owner','owner_rights','everyone'])
def test_native_mesmo_objeto_com_acl_sintetica(tmp_path,scenario):
    """Únicas ACLs modificadas são de novos diretórios temporários sintéticos."""
    api=p._WindowsACL();u=api.usuario();parent=tmp_path/'sintetico';parent.mkdir(mode=0o700)
    if scenario=='herdada':
        api.proteger_novo(parent,diretorio=True);target=parent/'child';target.mkdir()
    elif scenario=='creator_owner':
        api._aplicar_dacl(parent,'D:P'+f'(A;;FA;;;{u})'+'(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICIIO;FA;;;CO)')
        target=parent
    else:
        api.proteger_novo(parent,diretorio=True);target=parent
        if scenario in ('owner_rights','everyone'):
            sid='S-1-3-4'if scenario=='owner_rights'else'S-1-1-0'
            sddl='D:P'+''.join(f'(A;OICI;FA;;;{s})'for s in (u,'S-1-5-18','S-1-5-32-544'))+f'(A;;FR;;;{sid})'
            api._aplicar_dacl(target,sddl)
    before=api._snapshot_nome(target);r=d.investigar(target);after=api._snapshot_nome(target)
    assert before==after  # Investigação jamais persiste herança, normalize ou qualquer ACL.
    assert r.get('evidencias',{}).get('objeto_e_identidade_comprovados'),r
    assert r['evidencias']['leituras_completas']and r['evidencias']['descritores_estaveis'],r
    assert all(r['evidencias']['parsers_csharp_concordam'].values()),r
    assert all(r['evidencias']['parsers_python_concordam'].values()),r
    assert r['evidencias']['binarios_python_preservados']and r['evidencias']['getaccessrules_igual_raw'],r
    assert not r['autoriza_acesso']and not r['causa_confirmada']
    rules=r['probe']['fontes']['Handle_7']['regras']
    if scenario=='herdada':assert any(x['flags']&16 for x in rules),r
    if scenario in ('creator_owner','owner_rights','everyone'):
        assert scenario in {x['classe']for x in rules},r
        with pytest.raises(ErroAplicacao):p.conferir_windows(target)


@NATIVE
def test_native_substituicao_creator_owner_na_heranca_e_observada_sem_whitelist(tmp_path):
    api=p._WindowsACL();u=api.usuario();parent=tmp_path/'sintetico';parent.mkdir(mode=0o700)
    api._aplicar_dacl(parent,'D:P'+f'(A;;FA;;;{u})'+'(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICIIO;FA;;;CO)')
    child=parent/'child';child.mkdir()
    r=d.investigar(child)
    assert r.get('evidencias',{}).get('leituras_completas'),r
    assert r['evidencias']['objeto_e_identidade_comprovados']and not r['autoriza_acesso'],r
    rules=r['probe']['fontes']['Handle_7']['regras']
    assert any(x['classe']=='usuario'and not x['flags']&8 for x in rules),r
    assert any(x['flags']&16 for x in rules),r
