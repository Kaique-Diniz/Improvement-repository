"""Auditoria A1: documentos/telefones e titularidade inteiramente fictícios."""
import json

import pytest
from fastapi.testclient import TestClient

from conversor.application.passaredo_cadastro import associar
from conversor.domain.canonical import Documento, documento_validado
from conversor.readers.passaredo_cadastro import normalizar_documento, extrair_telefones, LeitorPassaredoCadastro
from conversor.web.service import reconhecer, ler
from conversor.web.ephemeral import criar_app_efemero
from .fixtures import CPF, CNPJ, OUTRO_CPF, cadastro, ficha, financeiro, debito
from .test_passaredo import executar, saida


def cnpj_ficticio_com_zero():
    base='001234560001'
    for pesos in ((5,4,3,2,9,8,7,6,5,4,3,2),(6,5,4,3,2,9,8,7,6,5,4,3,2)):
        resto=sum(int(d)*p for d,p in zip(base,pesos))%11
        base+=str(0 if resto<2 else 11-resto)
    return base


@pytest.mark.parametrize('valor',[None,'','   '])
def test_documento_ausente_nao_fabrica_evidencia(valor):
    assert normalizar_documento(valor) is None
    registro=LeitorPassaredoCadastro().ler(cadastro([ficha(documento=valor)]))[0]
    assert registro.documento is None and not registro.documentos and not registro.documentos_rejeitados


@pytest.mark.parametrize('valor',[
    '11111111111', '123', 'texto cadastral fictício', 'abc'+CPF,
    'CPF: '+CPF, CPF+'xyz', '111.444.777-350', '111.444.777/35',
    '11144abc477735', True, 11144477735.25,
])
def test_documento_invalido_ou_malformado_preservado_sem_atribuicao(tmp_path,valor):
    assert normalizar_documento(valor) is None
    raw=cadastro([ficha(documento=valor)])
    registro=LeitorPassaredoCadastro().ler(raw)[0]
    assert registro.documento is None and not registro.documentos
    assert registro.documentos_rejeitados==(str(valor),)
    assert registro.documentos_rejeitados_colunas==('D',)
    assert json.loads(registro.valores_originais)['CPF_CNPJ']==valor
    p,c,f=reconhecer(raw,cadastro=True,perfil_informado='passaredo')
    cad,_=ler(raw,p,c,f,'cadastro')
    assert cad.pessoas[0].documento is None and not cad.pessoas[0].evidencias_documentais
    warning=next(r for r in cad.ressalvas if r.codigo=='PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO')
    assert warning.valores_originais==(str(valor),) and warning.origens[0].identificador=='Sheet1_D2'
    result=executar(tmp_path,cad=raw)
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['cadastro_passaredo']['documentos_rejeitados_no_cadastro']==1
    assert saida(tmp_path)[1][2] is None
    assert 'PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO' in result['decisoes'][0]['alertas_cadastrais']


@pytest.mark.parametrize('valor,esperado',[
    (CPF,CPF),('111.444.777-35',CPF),(CNPJ,CNPJ),('11.222.333/0001-81',CNPJ),
    ('000.000.001-91','00000000191'),(cnpj_ficticio_com_zero(),cnpj_ficticio_com_zero()),
])
def test_documentos_validos_usam_verificadores_e_mantem_zeros(tmp_path,valor,esperado):
    doc=normalizar_documento(valor)
    assert doc is not None and documento_validado(doc)==esperado and doc.valor==esperado
    result=executar(tmp_path,cad=cadastro([ficha(documento=valor)]))
    row=saida(tmp_path)[1]
    assert row[2]==esperado and isinstance(row[2],str)
    assert result['validacao_conversao']['estado']=='conforme'


def test_documento_ruim_isolado_nao_rejeita_outras_pessoas(tmp_path):
    raw=financeiro([debito(unidade='007'),debito(unidade='008',nome='Pessoa Fictícia Beta')])
    cad=cadastro([ficha(documento='malformado '+CPF),ficha(unidade='008',nome='Pessoa Fictícia Beta')])
    result=executar(tmp_path,raw,cad=cad)
    by_unit={r[1]:r for r in saida(tmp_path)[1:]}
    assert result['resumo']['dividas_efetivamente_geradas']==2
    assert by_unit['BL-UNI0007-1030'][2] is None
    assert by_unit['BL-UNI0008-1030'][2]==CPF


def test_documento_malformado_nao_apaga_outra_evidencia_valida(tmp_path):
    raw=cadastro([ficha(documento='texto fictício '+CPF,outro_documento=OUTRO_CPF)])
    result=executar(tmp_path,cad=raw)
    assert saida(tmp_path)[1][2]==OUTRO_CPF
    assert 'PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO' in result['decisoes'][0]['alertas_cadastrais']
    p,c,f=reconhecer(raw,cadastro=True,perfil_informado='passaredo');cad,_=ler(raw,p,c,f,'cadastro')
    assert len(cad.pessoas[0].evidencias_documentais)==1
    assert cad.pessoas[0].evidencias_documentais[0].origem.identificador=='Sheet1_M2'


def test_documentos_validos_conflitantes_continuam_retidos(tmp_path):
    result=executar(tmp_path,cad=cadastro([ficha(outro_documento=OUTRO_CPF)]))
    assert result['cadastro_passaredo']['associacoes_retidas']==1
    assert saida(tmp_path)[1][2] is None
    assert 'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO' in result['decisoes'][0]['alertas_cadastrais']


def test_associacao_nao_confia_em_documento_invalido_de_um_canonico():
    raw=financeiro();p,c,f=reconhecer(raw,perfil_informado='passaredo');lote,_=ler(raw,p,c,f,'inadimplencia')
    raw=cadastro();p,c,f=reconhecer(raw,cadastro=True,perfil_informado='passaredo');cad,_=ler(raw,p,c,f,'cadastro')
    original=cad.pessoas[0]
    malformado=Documento(tipo='cpf',valor='texto fictício '+CPF)
    pessoa=original.model_copy(update={'documento':malformado,'evidencias_documentais':()})
    cad=cad.model_copy(update={'pessoas':(pessoa,)})
    _,pessoas,_,_=associar(lote,cad)
    assert pessoas[lote.boletos[0].id].documento is None
    assert not pessoas[lote.boletos[0].id].evidencias_documentais
    assert cad.pessoas[0].documento.valor=='texto fictício '+CPF


@pytest.mark.parametrize('valor,esperados',[
    ('1234-5678',[('', '12345678')]),('91234-5678',[('', '912345678')]),
    ('01234567',[('', '01234567')]),('091234567',[('', '091234567')]),
    ('(11) 91234-5678',[('11','912345678')]),('11 1234-5678',[('11','12345678')]),
    ('+55 (11) 91234-5678',[('11','912345678')]),
    ('(11) 91234-5678 / 91234-5678',[('11','912345678'),('', '912345678')]),
    ('12345678;12345678',[('', '12345678')]),
])
def test_telefones_completos_sem_ddd_nao_herdam_prefixo(valor,esperados):
    assert [(t.ddd,t.numero) for t in extrair_telefones(valor)]==esperados


@pytest.mark.parametrize('valor',[
    '123456789012','001191234567890','99123456789012345678',
    'abc11912345678','11912345678xyz','12345678 912345678',
    '(11) 91234-56789','1(11) 91234-5678','(11) 91234-5678 9',
])
def test_nao_extrai_telefone_parcial_de_uma_sequencia_maior(valor):
    assert extrair_telefones(valor)==()


def test_telefone_sem_ddd_chega_ao_excel_sem_completar(tmp_path):
    executar(tmp_path,cad=cadastro([ficha(fone='0123-4567;91234-5678')]))
    row=saida(tmp_path)[1]
    assert row[11] is None and row[12]=='01234567'
    assert row[13] is None and row[14]=='912345678'


@pytest.mark.parametrize('nome',[
    'Empresa Fictícia Alfa E Beta Ltda','Empresa Fictícia Alfa E Beta S/A',
    'Empresa Fictícia Alfa E Beta S.A.','Empresa Fictícia Alfa E Beta ME',
])
def test_empresa_com_e_e_vinculo_concordante_nao_e_bloqueada(tmp_path,nome):
    result=executar(tmp_path,financeiro([debito(nome=nome)]),cad=cadastro([ficha(nome=nome,documento=CNPJ)]))
    assert saida(tmp_path)[1][2]==CNPJ
    assert result['cadastro_passaredo']['associacoes_retidas']==0


@pytest.mark.parametrize('nome',[
    'Pessoa Fictícia Alfa E Pessoa Fictícia Beta',
    'Pessoa Fictícia Alfa / Pessoa Fictícia Beta',
    'Pessoa Fictícia Alfa; Pessoa Fictícia Beta',
    'Pessoa Fictícia Alfa\nPessoa Fictícia Beta',
    'Empresa Fictícia S/A\nPessoa Fictícia Beta',
    'Pessoa Fictícia Alfa / Empresa Fictícia Beta Ltda',
])
def test_cnpj_valido_nao_prova_titularidade_de_lista_de_responsaveis(tmp_path,nome):
    result=executar(tmp_path,financeiro([debito(nome=nome)]),cad=cadastro([ficha(nome=nome,documento=CNPJ)]))
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['cadastro_passaredo']['associacoes_retidas']==1
    assert saida(tmp_path)[1][2] is None and saida(tmp_path)[1][11] is None


def test_indicador_empresarial_nao_supera_nome_divergente(tmp_path):
    result=executar(tmp_path,financeiro([debito(nome='Empresa Fictícia Alfa E Beta Ltda')]),
        cad=cadastro([ficha(nome='Empresa Fictícia Gama Ltda',documento=CNPJ)]))
    assert result['cadastro_passaredo']['associacoes_retidas']==1 and saida(tmp_path)[1][2] is None


def test_cpf_individual_nao_e_liberado_por_indicador_empresarial(tmp_path):
    nome='Empresa Fictícia Alfa E Beta Ltda'
    result=executar(tmp_path,financeiro([debito(nome=nome)]),cad=cadastro([ficha(nome=nome,documento=CPF)]))
    assert result['cadastro_passaredo']['associacoes_retidas']==1 and saida(tmp_path)[1][2] is None


def test_cnpj_conflitante_nao_e_liberado_por_indicador_empresarial(tmp_path):
    nome='Empresa Fictícia Alfa E Beta Ltda'
    result=executar(tmp_path,financeiro([debito(nome=nome)]),
        cad=cadastro([ficha(nome=nome,documento=CNPJ,outro_documento=cnpj_ficticio_com_zero())]))
    assert result['cadastro_passaredo']['associacoes_retidas']==1 and saida(tmp_path)[1][2] is None


def test_cnpj_invalido_nao_comprova_o_vinculo_empresarial(tmp_path):
    nome='Empresa Fictícia Alfa E Beta Ltda'
    result=executar(tmp_path,financeiro([debito(nome=nome)]),
        cad=cadastro([ficha(nome=nome,documento='texto fictício '+CNPJ)]))
    assert result['cadastro_passaredo']['associacoes_retidas']==1 and saida(tmp_path)[1][2] is None


def test_ddd_do_fone_nao_e_herdado_pelo_celular(tmp_path):
    raw=cadastro([ficha(fone='(11) 91234-5678')],mutar=lambda w,s:setattr(s['G2'],'value','0123-4567'))
    executar(tmp_path,cad=raw)
    row=saida(tmp_path)[1]
    assert (row[11],row[12])==('11','912345678')
    assert (row[13],row[14])==(None,'01234567')


def test_cadastro_malformado_nao_vaza_no_resumo_ou_em_logs(tmp_path,caplog):
    key='chave-ficticia-a1-conversao'
    sentinel='EVIDENCIA_FICTICIA_NAO_LOGAR_'+CPF
    app=criar_app_efemero(acesso=key,area_temporaria=tmp_path)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        client.post('/api/sessao',json={'chave':key})
        r=client.post('/api/conversoes',data={'data_ref':'2026-10-07','modo':'A','condominio':'passaredo'},
            files={'inadimplencia':('ficticio.xlsx',financeiro()),'cadastro':('cadastro.xlsx',cadastro([ficha(documento=sentinel)]))})
        assert r.status_code==200 and sentinel not in r.text and sentinel not in caplog.text
        assert r.json()['cadastro_passaredo']['documentos_rejeitados_no_cadastro']==1
        assert not list(app.state.ciclo.root.iterdir())
