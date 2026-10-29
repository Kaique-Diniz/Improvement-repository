"""Comparação independente e saída local pseudonimizada, sem tocar fontes reais."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conversor import acl_diagnostics as d
from conversor import private_security
from conversor.adapters import private_permissions as p
from tests.test_windows_acl_reader import USER,OTHER,SD,EXPECTED,mod,backend,MemoriaWindows

KEY=b'chave efemera somente de teste!!'


def publico(acl=EXPECTED):return d._publico(acl,KEY)


def test_saida_usa_hmac_efemero_nao_sid_e_nao_correlaciona_execucoes():
    a=publico();b=d._publico(EXPECTED,b'outra chave sintetica')
    raw=json.dumps(a)
    assert 'S-1-'not in raw and USER not in raw
    assert a['regras'][2]['identidade']==a['usuario']==a['proprietario']
    assert a['usuario']!=b['usuario']
    assert [r['classe']for r in a['regras']]==['system','administradores','usuario']


def test_multiconjunto_aceita_ordem_diferente_mas_nao_perde_duplicatas():
    a=publico();b=deepcopy(a);b['regras'].reverse()
    checks,ok=d.comparar_modelos({'binario':a,'powershell':b})
    assert ok and checks['powershell']['regras_iguais']and not checks['powershell']['ordem_igual']
    b['regras'].append(b['regras'][0]);assert not d.comparar_modelos({'a':a,'b':b})[1]


@pytest.mark.parametrize('campo,valor',[
    ('identidade','f'*64),('mascara','0x120089'),('tipo',1),('flags',0),
])
def test_diferenca_real_nao_e_tratada_como_representacao(campo,valor):
    a=publico();b=deepcopy(a);b['regras'][2][campo]=valor
    checks,ok=d.comparar_modelos({'binario':a,'powershell':b})
    assert not ok and not checks['powershell']['regras_iguais']


@pytest.mark.parametrize('campo,valor',[('usuario','f'*64),('proprietario','f'*64),('dacl_presente',False)])
def test_identidade_owner_e_dacl_tambem_sao_comparados(campo,valor):
    a=publico();b=deepcopy(a);b[campo]=valor
    assert not d.comparar_modelos({'a':a,'b':b})[1]


def test_projecao_do_powershell_descarta_todos_os_campos_nao_permitidos():
    r=publico();r['SENTINELA_SECRETA']='caminho confidencial'
    r['regras'][0]['conta']='SENTINELA_SECRETA'
    r['regras_raw_count']=3
    assert 'SENTINELA'not in str(d._validar_projecao(r))


@pytest.mark.parametrize('campo,valor',[
    ('usuario',USER),('proprietario',OTHER),('dacl_presente','True'),('regras',{}),
])
def test_projecao_nao_expoe_identidades_brutas_inesperadas(campo,valor):
    r=publico();r[campo]=valor
    with pytest.raises(ValueError):d._validar_projecao(r)


def simular(monkeypatch,*,raw=SD,powershell=None):
    fake=MemoriaWindows(nome=raw,arquivo=raw)
    monkeypatch.setattr(d,'windows',lambda:True)
    monkeypatch.setattr(d,'_WindowsACL',lambda:backend(fake))
    # Chave depende de cada chamada; simulação precisa usar exatamente a recebida.
    def ps(path,key):
        acl=d.decodificar_descritor(raw,USER)
        r=d._publico(acl,key)|{'regras_raw_count':len(acl.entradas)}
        return powershell(r)if powershell else r
    monkeypatch.setattr(d,'_powershell',ps)
    return fake


def test_diagnostico_concordante_e_somente_leitura(tmp_path,monkeypatch):
    f=tmp_path/'SENTINELA_CAMINHO_PRIVADO';f.write_bytes(b'SENTINELA CONTEUDO')
    antes=f.read_bytes();fake=simular(monkeypatch)
    r=d.diagnosticar(f)
    assert r['estado']=='leituras_coerentes'and r['politica_local']=='confere'
    assert not r['autoriza_acesso']and r['alteracoes_realizadas']==0
    assert f.read_bytes()==antes and not hasattr(fake,'SetNamedSecurityInfoW')
    assert 'SENTINELA'not in json.dumps(r)and 'S-1-'not in json.dumps(r)
    assert len(r['comparacoes'])==4


def test_diagnostico_terceiro_sid_divergente_nao_aprova_pasta(tmp_path,monkeypatch):
    def mudar(r):r['regras'][2]['identidade']='f'*64;r['regras'][2]['classe']='outra';return r
    simular(monkeypatch,powershell=mudar)
    r=d.diagnosticar(tmp_path)
    assert r['estado']=='leituras_divergentes'and not r['autoriza_acesso']
    assert r['comparacoes']['PowerShell_GetAccessRules']['identidades_adicionais']==1


def test_acl_efetivamente_ampla_continua_insegura_mesmo_com_quatro_leituras_iguais(tmp_path,monkeypatch):
    simular(monkeypatch,raw=mod(132,'I',1002))
    r=d.diagnosticar(tmp_path)
    assert r['estado']=='leituras_coerentes'and r['politica_local']=='ACL_PRIVADA_INSEGURA'
    assert not r['autoriza_acesso']


def test_projecao_parcial_nao_prova_concordancia(tmp_path,monkeypatch):
    def parcial(r):r['regras_raw_count']=4;return r
    simular(monkeypatch,powershell=parcial)
    r=d.diagnosticar(tmp_path)
    assert r['estado']=='nao_comprovado'and r['etapa']=='PowerShell_GetAccessRules'


def test_excecao_nunca_imprime_stderr_sid_ou_caminho(tmp_path,monkeypatch):
    simular(monkeypatch)
    def falhar(*a):raise RuntimeError('SENTINELA_SECRETA '+USER+' '+str(tmp_path))
    monkeypatch.setattr(d,'_powershell',falhar)
    r=d.diagnosticar(tmp_path)
    assert r['estado']=='nao_comprovado'and r['etapa']=='PowerShell_GetAccessRules'
    assert 'SENTINELA'not in json.dumps(r)and USER not in json.dumps(r)and str(tmp_path)not in json.dumps(r)


def test_caminho_redirecionado_nao_e_passado_a_api(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'windows',lambda:True)
    monkeypatch.setattr(type(tmp_path),'is_symlink',lambda _:True)
    def nunca():pytest.fail('Não acessar APIs em caminho redirecionado.')
    monkeypatch.setattr(d,'_WindowsACL',nunca)
    r=d.diagnosticar(tmp_path)
    assert r['estado']=='nao_comprovado'and r['etapa']=='caminho'


def test_sem_windows_nao_chama_apis_nativas(monkeypatch):
    monkeypatch.setattr(d,'windows',lambda:False)
    r=d.diagnosticar(Path('sintetico'))
    assert r['codigo']=='COMPARACAO_NATIVA_EXIGE_WINDOWS'and not r['autoriza_acesso']


def test_subprocesso_tem_script_fixo_path_somente_no_ambiente_e_nao_expoe_stderr(monkeypatch):
    monkeypatch.setenv('SystemRoot','C:/Windows')
    def run(args,**kw):
        assert 'SENTINELA_CAMINHO'not in ' '.join(args)
        assert kw['env']['CONVERSOR_ACL_DIAG_PATH']=='SENTINELA_CAMINHO'
        assert args[-1]==d.POWERSHELL and kw['timeout']==45 and kw['capture_output']
        return SimpleNamespace(returncode=1,stdout=b'',stderr=b'SENTINELA_SECRETA')
    monkeypatch.setattr(d.subprocess,'run',run)
    with pytest.raises(ValueError,match='^POWERSHELL_INDISPONIVEL$'):d._powershell('SENTINELA_CAMINHO',KEY)


@pytest.mark.parametrize('estado,politica,exitcode',[
    ('leituras_coerentes','confere',0),('leituras_divergentes','confere',2),
    ('leituras_coerentes','ACL_PRIVADA_INSEGURA',2),('nao_comprovado',None,2),
])
def test_cli_nao_trata_divergencia_ou_acl_insegura_como_sucesso(monkeypatch,capsys,estado,politica,exitcode):
    monkeypatch.setattr('sys.argv',['audit','--private-dir','SENTINELA_CAMINHO','--comparar-leituras'])
    monkeypatch.setattr(d,'diagnosticar',lambda path:dict(estado=estado,politica_local=politica))
    assert private_security.main()==exitcode
    assert 'SENTINELA'not in capsys.readouterr().out
