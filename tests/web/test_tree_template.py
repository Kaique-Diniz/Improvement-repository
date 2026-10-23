"""Dados inventados; nenhum endereço ou contato real nas configurações de teste."""
import json
from pathlib import Path
from io import BytesIO

from openpyxl import load_workbook
import pytest
from pydantic import ValidationError

from conversor.domain.canonical import Endereco
from conversor.export.identifiers import selecionar_perfil, EnderecoPadrao
from conversor.readers.text_support import ErroLeitura
from conversor.web import service
from conversor.web.app import criar_app
from fastapi.testclient import TestClient
from tests.web.test_template_identifiers import unidade
from tests.web.test_tree_group_veto import boleto,pdf_unidades
from tests.web.test_mvp import KEY,aguardar


def perfil_tree():
    return selecionar_perfil(json.loads(service.PERFIS_SAIDA_PATH.read_bytes()),administradora_id='adm_habita',condominio_id='cond_habita')


def endereco():
    return {'endereco':{'logradouro':'Rua Inteiramente Ficticia','numero':'123','cep':'00000000','bairro':'Bairro Inventado','cidade':'Cidade Inventada','uf':'SP'},
        'evidencia':{'arquivo':'endereco_sintetico.json','sha256':'a'*64,'aba':'declaracao','celulas':{'endereco':'registro_sintetico'}}}


@pytest.mark.parametrize('bloco,codigo',[('1','01'),('2','02'),('DEP','DEP')])
def test_codificacao_tree_explicita_preserva_identidade(bloco,codigo):
    u=unidade(bloco,'0007',condominio='cond_habita',admin='adm_habita');original=u.model_dump()
    assert perfil_tree().codificar(u,administradora_id='adm_habita')==(f'BL{codigo}-UNI0007-TREE MORUMBI',f'BL{codigo}-UNI0007')
    assert u.model_dump()==original


def test_vg_sem_evidencia_nao_recebe_codigo_inventado():
    with pytest.raises(ErroLeitura,match='TORRE_SEM_MAPEAMENTO_DOCUMENTAL'):
        perfil_tree().codificar(unidade('VG',condominio='cond_habita',admin='adm_habita'),administradora_id='adm_habita')


@pytest.mark.parametrize('atual',[Endereco(logradouro='Rua Atual Sintetica'),Endereco(cidade='Cidade Atual'),Endereco(numero='9')])
def test_endereco_atual_inclusive_parcial_nunca_e_substituido(atual):
    perfil=perfil_tree().model_copy(update={'endereco_padrao':EnderecoPadrao.model_validate(endereco())})
    saida,status=perfil.preencher_endereco(atual)
    assert saida==atual and status=='endereco_atual_preservado'


def test_endereco_padrao_so_preenche_ausencia_integral():
    p=perfil_tree().model_copy(update={'endereco_padrao':EnderecoPadrao.model_validate(endereco())})
    saida,status=p.preencher_endereco(Endereco(complemento='CODIGO-UNIDADE'))
    assert saida.logradouro=='Rua Inteiramente Ficticia'and saida.complemento=='CODIGO-UNIDADE'
    assert status=='endereco_explicito_configurado'
    original=Endereco();assert perfil_tree().preencher_endereco(original)==(original,'sem_endereco_configurado')


@pytest.mark.parametrize('campo,valor',[('logradouro',''),('complemento','APTO INVENTADO')])
def test_endereco_ambiguo_ou_complemento_de_unidade_nao_e_padrao(campo,valor):
    data=endereco();data['endereco'][campo]=valor
    with pytest.raises(ValidationError):EnderecoPadrao.model_validate(data)


def test_upload_com_configuracao_privada_endereco_e_rotulo_nao_muda_canonico(tmp_path):
    dados=json.loads(service.PERFIS_SAIDA_PATH.read_bytes());dados[1]['endereco_padrao']=endereco()
    config=tmp_path/'perfis_saida_privados.json';config.write_text(json.dumps(dados))
    pdf=pdf_unidades([('1','000007',[boleto('99000001',vencimento='17/08/26')])])
    original=service.analisar(pdf,service.PedidoDiagnostico(data_ref='2026-10-23',modo='A'),
        processamento_id='sintetico',destino=tmp_path/'original')
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY,perfis_saida=config))as c:
        c.post('/api/session',json={'chave':KEY})
        r=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-23','modo':'A'},files={'inadimplencia':('SINTETICO.pdf',pdf)}))
        assert r['estado']=='concluido';data=r['resultado']
        blob=c.get('/api/processamentos/'+r['id']+'/arquivo-teste.xlsx').content
        wb=load_workbook(BytesIO(blob));s=wb['Dados']
        assert s['AA1'].value=='NM_DIVIDA_CEDENTE'and s.max_column==30
        assert s['E2'].value=='Rua Inteiramente Ficticia'and s['G2'].value=='BL01-UNI0007'
        assert s['AA2'].value=='COTA 08/2026 - 1'
        assert data['decisoes'][0]['competencia']is None
        assert data['decisoes'][0]['boleto']=='99000001'
        assert data['resumo']['dividas_efetivamente_geradas']==original['resumo']['dividas_efetivamente_geradas']==1
        assert (tmp_path/'privado/processamentos'/r['id']/'canonico.json').read_bytes()==(tmp_path/'original/canonico.json').read_bytes()
        assert c.get('/api/processamentos/'+r['id']+'/operacional.xlsx').status_code==409
        wb.close()
