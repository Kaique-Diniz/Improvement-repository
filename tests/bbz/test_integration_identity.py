"""Relações e variações sintéticas, sem cadastro financeiro dos próximos condomínios."""
from hashlib import sha256
from pathlib import Path
import json

import pytest
from pydantic import ValidationError

from conversor.domain.integration_identity import CatalogoIdentidadesIntegracao,IdentidadeIntegracao
from conversor.adapters.integration_identity_json import RepositorioIdentidadesIntegracaoJSON
from conversor.readers.text_support import ErroLeitura
from conversor.web.service import reconhecer,IDENTIDADES_PATH,PERFIS


def identidade(**kw):
    return IdentidadeIntegracao(codigo_easycollector='00123',administradora_id='adm_ficticia',condominio_id='cond_ficticio',
        nome_integracao='CONDOMINIO FICTICIO',nomes_documentais=('CONDOMINIO FICTICIO',),codigos_origem=('999',),**kw)


def test_catalogo_persistente_separa_codigo_destino_de_origem(tmp_path):
    cat=CatalogoIdentidadesIntegracao(versao='1',identidades=(identidade(),))
    p=tmp_path/'identidades.json';p.write_text(cat.model_dump_json());raw=p.read_bytes()
    c,digest=RepositorioIdentidadesIntegracaoJSON(p).carregar()
    assert c.identidades[0].codigo_easycollector=='00123'and c.identidades[0].codigos_origem==('999',)
    assert digest==sha256(raw).hexdigest()
    assert RepositorioIdentidadesIntegracaoJSON(p).carregar()==(c,digest)and p.read_bytes()==raw
    assert c.candidatos('CONDOMÍNIO FICTICIO','999')==(c.identidades[0],)
    assert not c.candidatos('OUTRO NOME','999')and not c.candidatos('CONDOMINIO FICTICIO','00123')


@pytest.mark.parametrize('mudanca,codigo',[
    ({'condominio_id':'outro','codigos_origem':('998',)},'CODIGO_EASYCOLLECTOR_DUPLICADO'),
    ({'codigo_easycollector':'00124'},'IDENTIDADE_INTEGRACAO_DUPLICADA'),
])
def test_colisoes_no_catalogo_sao_rejeitadas(mudanca,codigo):
    a=identidade();b=IdentidadeIntegracao.model_validate(a.model_dump()|mudanca)
    with pytest.raises(ValidationError,match=codigo):CatalogoIdentidadesIntegracao(versao='1',identidades=(a,b))


@pytest.mark.parametrize('codigo',[123,1.0,'12A','123.0','-1',''])
def test_codigo_destino_textual_sem_coercao(codigo):
    with pytest.raises(ValidationError):IdentidadeIntegracao.model_validate(identidade().model_dump()|{'codigo_easycollector':codigo})


@pytest.mark.parametrize('raw',['{invalido','{"schema_versao":"2.0"}'])
def test_catalogo_invalido_falha_sem_expor_conteudo(tmp_path,raw):
    p=tmp_path/'identidades.json';p.write_text(raw)
    with pytest.raises(ErroLeitura,match='CATALOGO_IDENTIDADES_INTEGRACAO_INVALIDO')as exc:RepositorioIdentidadesIntegracaoJSON(p).carregar()
    assert raw not in str(exc.value)


def test_cinco_relacoes_cadastradas_respeitam_quatro_pilotos_habilitados():
    c,_=RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH).carregar()
    assert {i.codigo_easycollector for i in c.identidades}=={'363','567','696','788','884'}
    assert[p['id']for p in PERFIS.values()if p['familia']=='bbz']==['nova_york','innova_blue','nova_reboucas','edificio_win']


def test_reconhecimento_por_conteudo_captura_snapshot_sem_usar_filename(xlsx):
    p,codigo,_=reconhecer(xlsx());i=p['identidade_integracao']
    assert i['codigo_easycollector']=='884'and codigo=='287'and i['codigo_origem_observado']=='287'
    assert len(i['catalogo_sha256'])==64 and i['origem_codigo_easycollector']=='decisao_responsavel'
    assert 'identidade_integracao'not in PERFIS['nova_york'] # não altera registro global


def test_identidade_conhecida_sem_perfil_financeiro_nao_processa(xlsx):
    cat,_=RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH).carregar();i=next(i for i in cat.identidades if i.codigo_easycollector=='788')
    raw=xlsx(codigo=i.codigos_origem[0],nome=i.nomes_documentais[0])
    with pytest.raises(ErroLeitura,match='CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO'):reconhecer(raw)


def test_mistura_nome_nova_york_com_codigo_de_outro_condominio_bloqueia(xlsx):
    cat,_=RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH).carregar();i=next(i for i in cat.identidades if i.codigo_easycollector=='363')
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):reconhecer(xlsx(codigo=i.codigos_origem[0]))


def test_porta_permite_outro_repositorio_sem_mudar_reconhecedor(xlsx):
    cat,digest=RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH).carregar()
    class Memoria:
        def carregar(self):return cat,digest
    p,_,_=reconhecer(xlsx(),repositorio_identidades=Memoria())
    assert p['identidade_integracao']['codigo_easycollector']=='884'


def test_filename_de_outro_condominio_nao_muda_identidade_do_conteudo(xlsx,tmp_path):
    from fastapi.testclient import TestClient
    from conversor.web.app import criar_app
    from tests.web.test_mvp import KEY,aguardar
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        job=aguardar(c,c.post('/api/processamentos',data={'data_ref':'2026-10-26','modo':'A'},
            files={'inadimplencia':('363 - INNOVA BLUE.xlsx',xlsx())}))
        assert job['estado']=='concluido'
        r=job['resultado'];assert r['identidade_integracao']['codigo_easycollector']=='884'
        assert r['identidade_integracao']['codigo_origem_observado']=='287'
        assert all(v['cedente'].endswith('-884')and v['cedente']!='287'for v in r['codificacao_template']['unidades'].values())
        manifest=c.get('/api/processamentos/'+job['id']+'/manifesto-diagnostico.json').json()
        assert manifest['identidade_integracao']['codigo_easycollector']=='884'


def test_codigo_auxiliar_pode_repetir_sem_ser_chave_prioritaria():
    a=identidade();b=IdentidadeIntegracao.model_validate(a.model_dump()|{'codigo_easycollector':'00124','condominio_id':'outro',
        'nomes_documentais':('OUTRO CONDOMINIO FICTICIO',),'nome_integracao':'OUTRO CONDOMINIO FICTICIO'})
    cat=CatalogoIdentidadesIntegracao(versao='1',identidades=(a,b))
    assert cat.candidatos('CONDOMINIO FICTICIO','999')==(a,)
    assert cat.candidatos('OUTRO CONDOMINIO FICTICIO','999')==(b,)
    assert not cat.candidatos('NOME NAO CADASTRADO','999')


def test_nome_e_codigo_auxiliar_ambiguos_exigem_revisao(xlsx):
    cat,_=RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH).carregar();ny=next(i for i in cat.identidades if i.codigo_easycollector=='884')
    outra=IdentidadeIntegracao.model_validate(ny.model_dump()|{'codigo_easycollector':'999','condominio_id':'outro_ficticio'})
    ambiguo=CatalogoIdentidadesIntegracao(versao='1',identidades=(ny,outra))
    class Memoria:
        def carregar(self):return ambiguo,'a'*64
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DESCONHECIDO_OU_AMBIGUO'):reconhecer(xlsx(),repositorio_identidades=Memoria())


def test_json_com_chaves_duplicadas_nao_escolhe_codigo_silenciosamente(tmp_path):
    cat=CatalogoIdentidadesIntegracao(versao='1',identidades=(identidade(),))
    raw=cat.model_dump_json().replace('"codigo_easycollector":"00123"','"codigo_easycollector":"999","codigo_easycollector":"00123"')
    p=tmp_path/'identidades.json';p.write_text(raw)
    with pytest.raises(ErroLeitura,match='CATALOGO_IDENTIDADES_INTEGRACAO_INVALIDO'):RepositorioIdentidadesIntegracaoJSON(p).carregar()


def test_codigo_destino_divergente_entre_perfil_e_catalogo_bloqueia(xlsx,monkeypatch):
    from conversor.web import service
    monkeypatch.setitem(service.PERFIS,'nova_york',dict(service.PERFIS['nova_york'],codigo_easycollector='999'))
    with pytest.raises(ErroLeitura,match='CODIGO_DESTINO_DIVERGENTE_DO_PERFIL'):reconhecer(xlsx())
