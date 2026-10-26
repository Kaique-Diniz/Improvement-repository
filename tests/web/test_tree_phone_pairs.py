"""Telefones/endereço criados do zero; nenhuma identidade ou fonte pessoal real."""
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError
import pytest

from conversor.domain.canonical import Telefone, Endereco
from conversor.readers.habita_contacts import extrair_telefones
from conversor.web import service
from conversor.web.app import criar_app
from tests.web.test_mvp import KEY,aguardar
from tests.web.test_tree_group_veto import boleto,pdf_unidades
from tests.web.test_tree_template import endereco
from examples.fase3.layouts_sinteticos import pdf_posicionado


def fonte(contatos):
    # Somente o construtor de PDF é substituído, conservando a geometria financeira.
    import tests.web.test_tree_group_veto as f
    original=f.pdf_posicionado
    def construir(paginas):
        for i,rows in enumerate(paginas):
            for j,t in enumerate(contatos[i]):rows.append((31,650-j*15,t))
        return pdf_posicionado(paginas)
    try:
        f.pdf_posicionado=construir
        return pdf_unidades([('1',f'{i+1:06d}',[boleto(f'990000{i+1:02d}')])for i in range(len(contatos))])
    finally:f.pdf_posicionado=original


def executar(tmp_path,contatos,**kwargs):
    return service.analisar(fonte(contatos),service.PedidoDiagnostico(data_ref='2026-10-23',modo='A'),
        processamento_id='pares_sinteticos',destino=tmp_path,**kwargs)


@pytest.mark.parametrize('texto,esperados',[
    ('Telefone comercial: 00000001 Celular: 11900000001',[('','00000001'),('11','900000001')]),
    ('Telefone residencial: 00000-0001',[('','000000001')]),
    ('Telefone empresarial: (21) 0000-0001',[('21','00000001')]),
    ('Celular: +55 11 90000-0001',[('11','900000001')]),
    ('Celular: 11-90000-0001',[('11','900000001')]),
    ('Telefone comercial: 00000001 / 00000002',[('','00000001'),('','00000002')]),
    ('Telefone: 1100000001 / 2100000001',[('11','00000001'),('21','00000001')]),
    ('E-mail: nome00000001@example.invalid',[]),
    ('Observacao: 00000001',[]),
    ('Telefone: 1234567890123',[]),
])
def test_tokens_telefonicos_independentes_e_sem_inferencia(texto,esperados):
    assert [(t.ddd,t.numero)for t,rotulo,raw in extrair_telefones(texto)]==esperados


@pytest.mark.parametrize('ddd',['1','111',None,11,'XX'])
def test_ddd_informado_invalido_nao_se_transforma_em_vazio(ddd):
    with pytest.raises(ValidationError):Telefone(ddd=ddd,numero='00000001')


def test_comercial_sem_ddd_e_celular_com_ddd_exportados_sem_contaminacao(tmp_path):
    r=executar(tmp_path,[['Telefone comercial: 00000001 Celular: 11900000001']])
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');row=list(wb['Dados'].iter_rows(min_row=2))[0]
    assert [c.value for c in row[11:15]]==['11','900000001',None,'00000001']
    assert row[12].data_type==row[14].data_type=='s'
    infos=[o for o in r['ocorrencias']if o['codigo']=='TELEFONE_SEM_DDD']
    assert len(infos)==1 and infos[0]['gravidade']=='informativo'and infos[0]['origem']['pagina']==1
    assert not r['decisoes'][0]['bloqueios']and r['resumo']['dividas_efetivamente_geradas']==1
    canon=json.loads((tmp_path/'canonico.json').read_text())
    provas=[x for x in canon['ressalvas']if x['codigo']=='TELEFONE_IDENTIFICADO_NA_FONTE']
    assert len(provas)==2 and all(x['origens'][0]['pagina']==1 for x in provas)
    wb.close()


def test_unico_telefone_sem_ddd_nao_e_descartado(tmp_path):
    r=executar(tmp_path,[['Telefone residencial: 0000-0001']])
    assert r['decisoes'][0]['contato']['telefone']
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');s=wb['Dados']
    assert s['L2'].value is None and s['M2'].value=='00000001';wb.close()


def test_duplicados_exatos_unificados_sem_unificar_ddd_ausente_ou_diferente(tmp_path):
    r=executar(tmp_path,[['Telefone comercial: 00000001 Telefone empresarial: 0000-0001',
        'Celular: 1100000001 / 2100000001']])
    canon=json.loads((tmp_path/'canonico.json').read_text());ps=canon['pessoas'][0]['contato']['telefones']
    assert ps==[{'ddd':'11','numero':'00000001'},{'ddd':'21','numero':'00000001'},{'ddd':'','numero':'00000001'}]
    provas=[x for x in canon['ressalvas']if x['codigo']=='TELEFONE_IDENTIFICADO_NA_FONTE']
    assert len(provas)==4 # classificações originais preservadas, apesar de três pares


def test_limite_cinco_pares_e_isolamento_de_unidades(tmp_path):
    r=executar(tmp_path,[['Telefone comercial: '+ ' / '.join(f'000000{i:02d}'for i in range(1,7))],['Celular: 21900000002']])
    canon=json.loads((tmp_path/'canonico.json').read_text());a,b=canon['pessoas']
    assert len(a['contato']['telefones'])==5 and len(b['contato']['telefones'])==1
    assert all(t['ddd']==''for t in a['contato']['telefones'])
    assert b['contato']['telefones'][0]=={'ddd':'21','numero':'900000002'}
    assert any(o['codigo']=='CONTATOS_EXCEDENTES_PRESERVADOS'for o in r['ocorrencias'])


def test_configuracao_privada_automatica_endereco_so_tree_e_sem_sobrescrever(tmp_path):
    root=tmp_path/'privado';root.mkdir()
    perfis=json.loads(service.PERFIS_SAIDA_PATH.read_bytes());perfis[1]['endereco_padrao']=endereco()
    (root/'perfis_saida.json').write_text(json.dumps(perfis))
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        job=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-23','modo':'A'},
            files={'inadimplencia':('SINTETICO.pdf',fonte([['Telefone: 00000001']]))}))
        assert job['estado']=='concluido'
        wb=load_workbook(BytesIO(c.get('/api/processamentos/'+job['id']+'/arquivo-teste.xlsx').content))
        assert wb['Dados']['E2'].value=='Rua Inteiramente Ficticia'and wb['Dados']['G2'].value=='BL01-UNI0001'
        assert job['resultado']['manifesto_diagnostico']['enderecos_template'];wb.close()
        plaza=aguardar(c,c.post('/api/exemplo',data={'data_ref':'2026-10-23','modo':'A'}))
        assert all(e['estado']=='sem_endereco_configurado'for e in plaza['resultado']['enderecos_template'].values())


def test_endereco_configurado_prevalece_com_fonte_parcial_na_auditoria(tmp_path,monkeypatch):
    config=json.loads(service.PERFIS_SAIDA_PATH.read_bytes());config[1]['endereco_padrao']=endereco()
    p=tmp_path/'perfil_privado.json';p.write_text(json.dumps(config))
    old=service.ler
    def com_endereco(*args,**kwargs):
        lote,ctx=old(*args,**kwargs);pessoa=lote.pessoas[0]
        contato=pessoa.contato.model_copy(update={'endereco':Endereco(logradouro='Outra Rua Sintetica')})
        pessoa=pessoa.model_copy(update={'contato':contato})
        return lote.model_copy(update={'pessoas':(pessoa,)+lote.pessoas[1:]}),ctx
    monkeypatch.setattr(service,'ler',com_endereco)
    r=executar(tmp_path/'saida',[['Telefone: 00000001']],perfis_saida=p)
    info=next(iter(r['enderecos_template'].values()))
    assert info['alertas']==['ENDERECO_CADASTRADO_PRIORIZADO']
    assert info['endereco_origem']['logradouro']=='Outra Rua Sintetica'
    assert info['endereco_aplicado']['logradouro']=='Rua Inteiramente Ficticia'
    assert 'ENDERECO_CADASTRADO_PRIORIZADO'in r['decisoes'][0]['alertas_cadastrais']
    wb=load_workbook(tmp_path/'saida/TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert wb['Dados']['E2'].value=='Rua Inteiramente Ficticia'and wb['Dados']['F2'].value=='123'
    wb.close()
