from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from filelock import FileLock
import pytest

from conversor.adapters.billing_authority import AutoridadeHMAC
from conversor.adapters.billing_json import RepositorioPlanosJSON
from conversor.application.billing_plans import consultar_plano_ativo
from conversor.application.billing_ports import CredencialOperador
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import ComandoPlano, PlanoCobranca, hash_modelo


def executar(repo,plano,gestor,acao,*,revisao=None,em=None,data_ref=None):
    if revisao is None:
        try:revisao=repo.carregar().revisao
        except ErroAplicacao as erro:
            if str(erro)!='REPOSITORIO_DE_PLANOS_NAO_INICIALIZADO':raise
            revisao=0
    return repo.executar(ComandoPlano(acao=acao,plano=plano if acao=='criar'else None,
        plano_id=plano.id,em=em or datetime(2026,10,21,tzinfo=timezone.utc)+timedelta(seconds=revisao if type(revisao)is int else 0),
        fundamento='Fundamento inteiramente sintético',evidencia_id='evidencia_sintetica',data_ref=data_ref),
        credencial=gestor,revisao_esperada=revisao)


def aprovar(repo,plano,gestor):
    for acao in ('criar','submeter','aprovar'):executar(repo,plano,gestor,acao)


def arquivo_atual(repo):
    return repo.raiz/'generations'/(json.loads(repo.ponteiro.read_text())['geracao']+'.json')


def test_estados_assinatura_hash_e_historico(repo,plano,gestor):
    for acao,estado in [('criar','rascunho'),('submeter','aguardando_aprovacao'),('aprovar','aprovado'),
                        ('ativar','ativo'),('revogar','revogado')]:
        anterior=repo.carregar().acervo.eventos if acao!='criar'else()
        novo=executar(repo,plano,gestor,acao,data_ref=date(2026,10,21)if acao=='ativar'else None)
        assert novo.acervo.registros[0].estado==estado
        assert novo.acervo.eventos[:-1]==anterior
        assert repo.carregar()==novo
        evento=novo.acervo.eventos[-1]
        assert evento.responsavel_id=='gestor' and evento.hash_conteudo==hash_modelo(plano)
        assert evento.versao==plano.versao and evento.fundamento and evento.evidencia_id
        repo.autoridade.conferir_evento(evento)
        if os.name=='posix':assert arquivo_atual(repo).stat().st_mode&0o777==0o600
    assert len(list((repo.raiz/'generations').glob('*.json')))==5
    with pytest.raises(ErroAplicacao,match='PLANO_ATIVO_UNICO_INDISPONIVEL'):
        consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=date(2026,10,21))


def test_rejeitar_nao_aprova_nem_apaga_historico(repo,plano,gestor):
    for acao in ('criar','submeter','rejeitar','submeter','aprovar'):executar(repo,plano,gestor,acao)
    s=repo.carregar()
    assert s.acervo.registros[0].estado=='aprovado'
    assert [e.acao for e in s.acervo.eventos]==['criar','submeter','rejeitar','submeter','aprovar']


@pytest.mark.parametrize('fase,acao', [('criar','ativar'),('criar','aprovar'),('criar','revogar'),
    ('submeter','ativar'),('aprovar','aprovar'),('aprovar','submeter'),('ativar','ativar'),('revogar','ativar')])
def test_transicoes_ilegais_preservam_revisao(repo,plano,gestor,fase,acao):
    for passo in ('criar','submeter','aprovar','ativar','revogar'):
        executar(repo,plano,gestor,passo,data_ref=date(2026,10,21)if passo=='ativar'else None)
        if passo==fase:break
    antes=repo.carregar()
    with pytest.raises(ErroAplicacao,match='TRANSICAO_DE_PLANO_INVALIDA'):
        executar(repo,plano,gestor,acao,data_ref=date(2026,10,21)if acao=='ativar'else None)
    assert repo.carregar()==antes


@pytest.mark.parametrize('data_ref', [date(2025,12,31), date(2027,1,1), date(2027,2,1)])
def test_ativacao_requer_data_ref_dentro_intervalo(repo,plano,gestor,data_ref):
    aprovar(repo,plano,gestor)
    with pytest.raises(ErroAplicacao,match='ATIVACAO_FORA_DA_VIGENCIA'):
        executar(repo,plano,gestor,'ativar',data_ref=data_ref)
    assert repo.carregar().revisao==3


def test_ativo_exige_aprovacao_e_consulta_nao_usa_hoje(repo,plano,gestor):
    aprovar(repo,plano,gestor)
    with pytest.raises(ErroAplicacao,match='PLANO_ATIVO_UNICO_INDISPONIVEL'):
        consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=date(2026,10,21))
    executar(repo,plano,gestor,'ativar',data_ref=date(2026,1,1))
    assert consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=date(2026,1,1))==plano
    with pytest.raises(ErroAplicacao):consultar_plano_ativo(repo,condominio_id='outro',data_ref=date(2026,1,1))
    for ambiguo in (None,'2026-10-21',datetime(2026,10,21,tzinfo=timezone.utc)):
        with pytest.raises(ErroAplicacao,match='DATA_REF_EXPLICITA_OBRIGATORIA'):
            consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=ambiguo)


@pytest.mark.parametrize('estado', ['rascunho','aprovado','ativo','revogado'])
def test_nenhuma_versao_e_sobrescrita_nem_mesmo_rascunho(repo,plano,gestor,estado):
    for acao,alvo in [('criar','rascunho'),('submeter','aguardando_aprovacao'),('aprovar','aprovado'),('ativar','ativo'),('revogar','revogado')]:
        executar(repo,plano,gestor,acao,data_ref=date(2026,1,1)if acao=='ativar'else None)
        if alvo==estado:break
    antes=repo.carregar();p=PlanoCobranca.model_validate(plano.model_dump()|{'vigente_ate':'2028-01-01'})
    with pytest.raises(ErroAplicacao,match='VERSAO_OU_CONTEUDO_IMUTAVEL'):executar(repo,p,gestor,'criar')
    assert repo.carregar()==antes


def test_versao_repetida_id_novo_rejeitada_e_versao_nova_exige_aprovacao(repo,plano,gestor):
    aprovar(repo,plano,gestor)
    mesma=PlanoCobranca.model_validate(plano.model_dump()|{'id':'outro_id'})
    with pytest.raises(ErroAplicacao,match='VERSAO_DE_PLANO_DUPLICADA'):executar(repo,mesma,gestor,'criar')
    nova=PlanoCobranca.model_validate(plano.model_dump()|{'id':'plano_v2','versao':'2.0.0'})
    executar(repo,nova,gestor,'criar')
    with pytest.raises(ErroAplicacao,match='TRANSICAO_DE_PLANO_INVALIDA'):
        executar(repo,nova,gestor,'ativar',data_ref=date(2026,1,1))
    assert repo.carregar().acervo.registros[-1].estado=='rascunho'


def test_sobreposicao_ativa_bloqueada_revogacao_preserva_versao_antiga(repo,plano,gestor):
    aprovar(repo,plano,gestor);executar(repo,plano,gestor,'ativar',data_ref=date(2026,1,1))
    nova=PlanoCobranca.model_validate(plano.model_dump()|{'id':'plano_v2','versao':'2.0.0'})
    aprovar(repo,nova,gestor)
    with pytest.raises(ErroAplicacao,match='PLANOS_ATIVOS_SOBREPOSTOS'):
        executar(repo,nova,gestor,'ativar',data_ref=date(2026,1,1))
    executar(repo,plano,gestor,'revogar')
    executar(repo,nova,gestor,'ativar',data_ref=date(2026,1,1))
    assert consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=date(2026,1,1))==nova
    assert repo.carregar().acervo.registros[0].conteudo==plano


def test_duas_vigencias_adjacentes_ativas_sem_ambiguidade(repo,plano,gestor):
    nova=PlanoCobranca.model_validate(plano.model_dump()|{'id':'plano_v2','versao':'2.0.0','vigente_de':'2027-01-01','vigente_ate':None})
    for p,d in [(plano,date(2026,1,1)),(nova,date(2027,1,1))]:
        aprovar(repo,p,gestor);executar(repo,p,gestor,'ativar',data_ref=d)
    assert consultar_plano_ativo(repo,condominio_id=plano.condominio_id,data_ref=date(2027,1,1))==nova


@pytest.mark.parametrize('campo,valor,codigo', [('condominio_id','inexistente','REFERENCIA_DE_CONDOMINIO_INVALIDA'),
    ('natureza','operacional','NATUREZA_INCOMPATIVEL_COM_AMBIENTE')])
def test_referencias_e_isolamento_ambiental(repo,plano,gestor,campo,valor,codigo,seguranca):
    if campo=='condominio_id':
        # conceder explicitamente permissão à identidade de teste não cria condomínio.
        path=repo.autoridade.raiz/'operadores.json';d=json.loads(path.read_text());d['concessoes'][0]['condominio_ids'].append(valor);path.write_text(json.dumps(d))
    p=PlanoCobranca.model_validate(plano.model_dump()|{campo:valor})
    with pytest.raises(ErroAplicacao,match=codigo):executar(repo,p,gestor,'criar')
    assert not repo.ponteiro.exists()


def test_concorrencia_um_vencedor_e_uma_revisao_obsoleta(repo,plano,gestor):
    # Aguardar o commit concorrente (incluindo I/O e ACL no Windows) antes de
    # conferir a revisão; o teste de lock ocupado mantém o timeout curto da fixture.
    repo.timeout = 10
    executar(repo,plano,gestor,'criar')
    def submeter(_):
        try:executar(repo,plano,gestor,'submeter',revisao=1);return 'ok'
        except ErroAplicacao as e:return str(e)
    with ThreadPoolExecutor(max_workers=2)as pool:resultados=list(pool.map(submeter,range(2)))
    assert sorted(resultados)==['CONFLITO_DE_REVISAO','ok']
    assert repo.carregar().revisao==2 and len(repo.carregar().acervo.eventos)==2


def test_lock_e_revisao_invalida(repo,plano,gestor):
    with FileLock(repo.lock):
        with pytest.raises(ErroAplicacao,match='REPOSITORIO_DE_PLANOS_OCUPADO'):
            executar(repo,plano,gestor,'criar',revisao=0)
    for rev in (True,-1,'0'):
        with pytest.raises(ErroAplicacao,match='REVISAO_ESPERADA_INVALIDA'):
            executar(repo,plano,gestor,'criar',revisao=rev)


@pytest.mark.parametrize('ponto',['geracao','manifesto','commit'])
def test_falha_antes_commit_nao_publica_estado_parcial(repo,plano,gestor,monkeypatch,ponto):
    import conversor.adapters.billing_json as modulo
    executar(repo,plano,gestor,'criar');antes=repo.carregar();gravar=modulo._gravar;replace=os.replace
    def falhar_gravacao(path,b):
        if (ponto=='geracao'and path.suffix=='.json')or(ponto=='manifesto'and path.suffix=='.tmp'):raise OSError('sentinela_privada')
        return gravar(path,b)
    def falhar_replace(a,b):
        if ponto=='commit':raise OSError('sentinela_privada')
        return replace(a,b)
    monkeypatch.setattr(modulo,'_gravar',falhar_gravacao);monkeypatch.setattr(os,'replace',falhar_replace)
    with pytest.raises(ErroAplicacao,match='FALHA_GRAVACAO_PLANOS')as erro:executar(repo,plano,gestor,'submeter')
    assert 'sentinela_privada'not in str(erro.value)
    assert repo.carregar()==antes and not list(repo.autoridade.raiz.glob('*.tmp'))


def test_leitura_concorrente_consistente(repo,plano,gestor,monkeypatch):
    import conversor.adapters.billing_json as modulo
    executar(repo,plano,gestor,'criar');ler=modulo.ler_protegido;intercalou=False
    def interceptar(path):
        nonlocal intercalou
        dados=ler(path)
        if path==repo.ponteiro and not intercalou:
            intercalou=True;executar(repo,plano,gestor,'submeter',revisao=1)
        return dados
    monkeypatch.setattr(modulo,'ler_protegido',interceptar)
    assert repo.carregar().revisao==1 and repo.carregar().revisao==2


def test_erro_ausente_e_snapshot_ausente_explicitos(repo,plano,gestor):
    with pytest.raises(ErroAplicacao,match='NAO_INICIALIZADO'):repo.carregar()
    executar(repo,plano,gestor,'criar');arquivo_atual(repo).unlink()
    with pytest.raises(ErroAplicacao,match='FALHA_LEITURA_PLANOS'):repo.carregar()


def test_evento_com_instante_regressivo_rejeitado(repo,plano,gestor):
    executar(repo,plano,gestor,'criar')
    with pytest.raises(ErroAplicacao,match='EVENTO_FORA_DE_ORDEM_TEMPORAL'):
        executar(repo,plano,gestor,'submeter',em=datetime(2025,1,1,tzinfo=timezone.utc))


def test_consulta_com_backend_diferente_sem_reescrever_caso_de_uso(repo,plano,gestor):
    aprovar(repo,plano,gestor);executar(repo,plano,gestor,'ativar',data_ref=date(2026,1,1));estado=repo.carregar()
    class Memoria:
        def carregar(self):return estado
    assert consultar_plano_ativo(Memoria(),condominio_id=plano.condominio_id,data_ref=date(2026,2,1))==plano


def test_consulta_rejeita_backend_que_declara_ativo_sem_historico(plano):
    from conversor.domain.billing_rules import AcervoPlanos, EstadoPlanos, RegistroPlano
    falso=EstadoPlanos(revisao=1,acervo=AcervoPlanos(ambiente='sintetico',registros=(
        RegistroPlano(conteudo=plano,hash_conteudo=hash_modelo(plano),estado='ativo'),)))
    class BackendInconsistente:
        def carregar(self):return falso
    with pytest.raises(ErroAplicacao,match='ESTADO_SEM_HISTORICO_VALIDO'):
        consultar_plano_ativo(BackendInconsistente(),condominio_id=plano.condominio_id,data_ref=date(2026,1,1))


def test_novo_condominio_configuravel_e_versoes_isoladas(repo,plano,gestor):
    outro=PlanoCobranca.model_validate(plano.model_dump()|{'id':'plano_outro_condominio','condominio_id':'cond_outro'})
    for p in (plano,outro):
        aprovar(repo,p,gestor);executar(repo,p,gestor,'ativar',data_ref=date(2026,1,1))
    for p in (plano,outro):
        assert consultar_plano_ativo(repo,condominio_id=p.condominio_id,data_ref=date(2026,10,21))==p
