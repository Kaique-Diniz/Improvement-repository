"""Proposta restrita de comparação; não habilita exceção no leitor de produção."""
from copy import deepcopy
from dataclasses import replace
import json
import os

import pytest

from conversor.adapters import private_permissions as p
from conversor.adapters.acl_binary import decodificar_descritor, mesmas_regras
from conversor.application.ports import ErroAplicacao
from conversor.diagnostics import windows_acl as d
from tests.test_windows_acl_reader import SD, USER, EXPECTED, MemoriaWindows, backend, mod
from tests.test_windows_acl_investigation import OBJ, preparar, probe


def arquivo_sem_bit_herdado():
    raw=bytearray(SD)
    for offset in (57,77,101):raw[offset]&=~0x10
    return bytes(raw)


def cenario():
    raw=probe()
    for nome in ('File_5','Python_File_5','Python_final_File_5'):
        fonte=raw['fontes'][nome]
        for regra in fonte['regras']:regra['flags']&=~0x10
        fonte['GetAce']=deepcopy(fonte['regras'])
        fonte['binario_hmac']='b'*64;fonte['dacl_hmac']='c'*64
    return raw


def propor(raw, alterar_evidencias=None):
    safe=d.validar_resposta(raw)
    modelos={nome:{k:safe['fontes'][nome][k]for k in ('usuario','proprietario','dacl_presente','regras')}
        for nome in ('Python_Named_5','Python_File_5','Python_Named_5_all')}
    evidencias=d.avaliar_probe(safe,OBJ,modelos)
    evidencias.update(GetAce_python_igual_binario=True,GetAce_file_python_igual_binario=True,
        binarios_python_preservados=True,politicas_python=dict.fromkeys(
            ('Named','File','GetAce_Named','GetAce_File'),'confere'))
    if alterar_evidencias:alterar_evidencias(evidencias)
    return d.propor_comparacao_heranca(safe,evidencias)


def test_delta_0x10_isolado_e_somente_candidato_sem_autorizacao():
    r=propor(cenario())
    assert r['situacao']=='candidato_a_excecao_nao_implementada'
    assert all(r['condicoes'].values())
    assert not r['autoriza_acesso']and not r['aplicada_ao_leitor']
    assert all(type(v)is bool for v in r['condicoes'].values())
    assert USER not in json.dumps(r)and 'S-1-'not in json.dumps(r)


def test_ausencia_de_delta_nao_propoe_excecao():
    assert propor(probe())['situacao']=='condicoes_nao_comprovadas'


@pytest.mark.parametrize('campo,valor',[
    ('proprietario','f'*64),('usuario','f'*64),('grupo','f'*64),
    ('control_flags',0x9004),('dacl_presente',False),
])
def test_metadado_distinto_impede_proposta(campo,valor):
    raw=cenario();raw['fontes']['File_5'][campo]=valor
    r=propor(raw)
    assert r['situacao']=='condicoes_nao_comprovadas'
    assert not r['condicoes']['metadados_exatos']


@pytest.mark.parametrize('campo,valor',[
    ('identidade','f'*64),('mascara','0x120089'),('tipo',1),('tipo',5),
    ('flags',3|8),('flags',3|4),('flags',3&~1),('flags',3&~2),('flags',3|0x20),
    ('classe','owner_rights'),('classe','creator_owner'),('classe','everyone'),
    ('classe','authenticated_users'),('classe','outra'),
])
def test_outros_deltas_nao_sao_ignorados(campo,valor):
    raw=cenario();raw['fontes']['File_5']['regras'][0][campo]=valor
    assert propor(raw)['situacao']=='condicoes_nao_comprovadas'


@pytest.mark.parametrize('mudanca',['adicional','duplicada','ausente','ordem'])
def test_multiplicidade_e_ordem_nao_sao_reconstruidas(mudanca):
    raw=cenario();regras=raw['fontes']['File_5']['regras']
    if mudanca=='adicional':regras.append(regras[0]|dict(identidade='f'*64,classe='outra'))
    elif mudanca=='duplicada':regras.append(deepcopy(regras[0]))
    elif mudanca=='ausente':regras.pop()
    else:regras.reverse()
    assert propor(raw)['situacao']=='condicoes_nao_comprovadas'


@pytest.mark.parametrize('campo',[
    'objeto_e_identidade_comprovados','leituras_completas','leituras_caminho_fisico_completas',
    'descritores_estaveis','binarios_python_preservados','GetAce_python_igual_binario',
    'GetAce_file_python_igual_binario','getaccessrules_igual_raw',
])
def test_evidencia_incompleta_ou_instavel_impede_proposta(campo):
    assert propor(cenario(),lambda e:e.update({campo:False}))['situacao']=='condicoes_nao_comprovadas'


@pytest.mark.parametrize('fonte',['Named','File','GetAce_Named','GetAce_File'])
def test_cada_politica_individual_e_obrigatoria(fonte):
    def alterar(e):e['politicas_python'][fonte]='ACL_PRIVADA_INSEGURA'
    assert propor(cenario(),alterar)['situacao']=='condicoes_nao_comprovadas'


@pytest.mark.parametrize('fonte',['Handle_5','Python_Named_5','Python_File_5'])
def test_binarios_nao_confirmados_impedem_proposta(fonte):
    raw=cenario();raw['fontes'][fonte]['binario_hmac']='f'*64
    assert propor(raw)['situacao']=='condicoes_nao_comprovadas'


def test_getace_e_descritor_inconsistentes_impedem_proposta():
    raw=cenario();raw['fontes']['File_5']['GetAce']=[]
    assert propor(raw)['situacao']=='condicoes_nao_comprovadas'


def test_copia_binaria_identica_com_projecao_distinta_nao_e_comprovacao():
    raw=cenario();raw['fontes']['File_5']['binario_hmac']=raw['fontes']['Named_5']['binario_hmac']
    assert propor(raw)['situacao']=='condicoes_nao_comprovadas'


def test_politica_individual_nao_confunde_0x10_com_inherit_only():
    arquivo=decodificar_descritor(arquivo_sem_bit_herdado(),USER)
    p.validar_acl(EXPECTED);p.validar_acl(arquivo)
    assert not mesmas_regras(EXPECTED,arquivo)  # Comparador global permanece estrito.
    somente_heranca=replace(arquivo,entradas=tuple(replace(e,flags=e.flags|8)for e in arquivo.entradas))
    with pytest.raises(ErroAplicacao,match='ACL_PRIVADA_NAO_COMPROVADA'):
        p.validar_acl(somente_heranca)


def test_leitor_e_conferencia_continuam_fail_closed_no_delta_exclusivo(tmp_path,monkeypatch):
    api=backend(MemoriaWindows(nome=SD,arquivo=arquivo_sem_bit_herdado()))
    with pytest.raises(OSError,match='^LEITURAS_ACL_DIVERGENTES$'):api.ler('sintetico')
    monkeypatch.setattr(p,'windows',lambda:True);monkeypatch.setattr(p,'_WindowsACL',lambda:api)
    with pytest.raises(ErroAplicacao,match='^ACL_PRIVADA_NAO_VERIFICAVEL$'):p.conferir_windows(tmp_path)


@pytest.mark.parametrize('raw',[
    mod(44,'I',1002),mod(132,'I',1002),mod(60,'I',0x120089),mod(56,'B',1),
    mod(57,'B',3|8),mod(2,'H',0x9004),SD[:-1],
])
def test_leitor_nao_libera_outras_divergencias_ou_descritores_incompletos(raw):
    api=backend(MemoriaWindows(nome=raw,arquivo=arquivo_sem_bit_herdado()))
    with pytest.raises((OSError,ValueError)):api.ler('sintetico')


def test_investigacao_valida_cada_acl_realmente_decodificada(tmp_path,monkeypatch):
    preparar(monkeypatch)
    raw=mod(132,'I',1002)  # Terceiro SID distinto: nunca converter em usuário.
    monkeypatch.setattr(d,'_WindowsACL',lambda:backend(MemoriaWindows(nome=raw,arquivo=raw)))
    r=d.investigar(tmp_path)
    assert r['evidencias']['politicas_python']==dict.fromkeys(
        ('Named','File','GetAce_Named','GetAce_File'),'ACL_PRIVADA_INSEGURA')
    assert r['proposta_comparacao_heranca']['situacao']=='condicoes_nao_comprovadas'
    assert not r['autoriza_acesso']and not r['causa_confirmada']


@pytest.mark.skipif(os.name!='nt',reason='Exige Win32/.NET/PowerShell nativos; somente objetos temporários sintéticos.')
@pytest.mark.parametrize('arquivo',[False,True])
def test_native_diagnostico_de_objeto_herdado_nao_persiste_acl(tmp_path,arquivo):
    pai=p.criar_diretorio_privado(tmp_path/'pai_sintetico')
    alvo=pai/'herdado'
    if arquivo:alvo.touch()
    else:alvo.mkdir()
    api=p._WindowsACL();antes=(api._snapshot_nome(alvo),api._snapshot_arquivo(alvo))
    r=d.investigar(alvo)
    assert r.get('evidencias',{}).get('objeto_e_identidade_comprovados'),r
    assert r['evidencias']['leituras_completas']and r['evidencias']['descritores_estaveis'],r
    assert set(r['evidencias']['politicas_python'].values())=={'confere'},r
    assert r['evidencias']['GetAce_file_python_igual_binario'],r
    assert 'proposta_comparacao_heranca'in r
    assert not r['autoriza_acesso']and not r['causa_confirmada']
    assert not r['proposta_comparacao_heranca']['autoriza_acesso']
    assert (api._snapshot_nome(alvo),api._snapshot_arquivo(alvo))==antes
