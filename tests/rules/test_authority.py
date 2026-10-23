from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import os

import pytest

from conversor.adapters.billing_authority import AutoridadeHMAC
from conversor.adapters.billing_json import RepositorioPlanosJSON
from conversor.application.billing_ports import CredencialOperador
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos
from tests.rules.test_plan_repository import executar, aprovar, arquivo_atual


def atualizar_manifesto_confiavel(repo):
    """Só em teste: isolar a verificação interna mesmo com manifesto confiável."""
    path=repo.ponteiro;m=json.loads(path.read_text());m['sha256']=sha256(arquivo_atual(repo).read_bytes()).hexdigest()
    m.pop('assinatura');m['assinatura']=repo.autoridade.assinar(m,dominio='manifesto-planos-1.0')
    path.write_bytes(bytes_canonicos(m))


def test_credencial_desconhecida_nao_pode_criar_ou_aprovar(repo,plano,gestor):
    falsa=CredencialOperador('sintetico_sem_autorizacao_'+'x'*32)
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):executar(repo,plano,falsa,'criar')
    assert not repo.raiz.exists() and not repo.ponteiro.exists()
    executar(repo,plano,gestor,'criar');executar(repo,plano,gestor,'submeter')
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):executar(repo,plano,falsa,'aprovar')
    assert repo.carregar().revisao==2
    assert falsa.segredo not in repr(falsa)


def test_papeis_e_responsavel_derivado_do_registro(repo,plano,seguranca):
    _,cs=seguranca
    executar(repo,plano,cs['editor'],'criar');executar(repo,plano,cs['editor'],'submeter')
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):executar(repo,plano,cs['editor'],'aprovar')
    s=executar(repo,plano,cs['aprovador'],'aprovar');assert s.acervo.eventos[-1].responsavel_id=='aprovador'
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):
        executar(repo,plano,cs['aprovador'],'ativar',data_ref=date(2026,1,1))
    executar(repo,plano,cs['ativador'],'ativar',data_ref=date(2026,1,1))


@pytest.mark.parametrize('campo,valor',[('condominio_ids',['cond_outro']),('ambientes',['privado']),('acoes',['criar'])])
def test_autorizacao_limitada_a_condominio_ambiente_e_acao(repo,plano,gestor,campo,valor):
    executar(repo,plano,gestor,'criar')
    path=repo.autoridade.raiz/'operadores.json';d=json.loads(path.read_text());d['concessoes'][0][campo]=valor;path.write_text(json.dumps(d))
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):executar(repo,plano,gestor,'submeter')


@pytest.mark.parametrize('adulteracao',['estado','conteudo','evento','truncar','rollback'])
def test_edicao_manual_do_json_nao_aprova_nem_reescreve_historico(repo,plano,gestor,adulteracao):
    executar(repo,plano,gestor,'criar');antigo=arquivo_atual(repo).read_bytes()
    executar(repo,plano,gestor,'submeter');p=arquivo_atual(repo);d=json.loads(p.read_text())
    if adulteracao=='estado':d['registros'][0]['estado']='aprovado'
    elif adulteracao=='conteudo':d['registros'][0]['conteudo']['regras'][0]['prioridade']=100000
    elif adulteracao=='evento':d['eventos'][-1]['acao']='aprovar'
    elif adulteracao=='truncar':d['eventos']=d['eventos'][:-1]
    else:p.write_bytes(antigo)
    if adulteracao!='rollback':p.write_bytes(bytes_canonicos(d))
    with pytest.raises(ErroAplicacao,match='SNAPSHOT_DE_PLANOS_ADULTERADO'):repo.carregar()
    with pytest.raises(ErroAplicacao,match='SNAPSHOT_DE_PLANOS_ADULTERADO'):executar(repo,plano,gestor,'aprovar',revisao=2)


def test_recalcular_hash_sem_chave_nao_fabrica_aprovacao(repo,plano,gestor):
    executar(repo,plano,gestor,'criar');p=arquivo_atual(repo);d=json.loads(p.read_text());d['registros'][0]['estado']='ativo';p.write_bytes(bytes_canonicos(d))
    m=json.loads(repo.ponteiro.read_text());m['sha256']=sha256(p.read_bytes()).hexdigest();repo.ponteiro.write_bytes(bytes_canonicos(m))
    with pytest.raises(ErroAplicacao,match='ASSINATURA_DE_AUTORIDADE_INVALIDA'):repo.carregar()


@pytest.mark.parametrize('campo,valor',[('responsavel_id','autoproclamado'),('hash_conteudo','1'*64),('versao','9.0.0'),('assinatura','0'*64)])
def test_cada_aprovacao_exige_recibo_autentico(repo,plano,gestor,campo,valor):
    aprovar(repo,plano,gestor);p=arquivo_atual(repo);d=json.loads(p.read_text());d['eventos'][-1][campo]=valor;p.write_bytes(bytes_canonicos(d))
    atualizar_manifesto_confiavel(repo)
    with pytest.raises(ErroAplicacao,match='ASSINATURA_DE_AUTORIDADE_INVALIDA'):repo.carregar()


def test_estado_nao_pode_divergir_de_eventos_mesmo_em_snapshot_assinado(repo,plano,gestor):
    executar(repo,plano,gestor,'criar');p=arquivo_atual(repo);d=json.loads(p.read_text());d['registros'][0]['estado']='aprovado';p.write_bytes(bytes_canonicos(d))
    atualizar_manifesto_confiavel(repo)
    with pytest.raises(ErroAplicacao,match='ESTADO_SEM_HISTORICO_VALIDO'):repo.carregar()


def test_remocao_do_papel_nao_apaga_aprovacao_historica(repo,plano,gestor):
    aprovar(repo,plano,gestor);antes=repo.carregar();path=repo.autoridade.raiz/'operadores.json';d=json.loads(path.read_text());d['concessoes'][0]['acoes']=['criar'];path.write_text(json.dumps(d))
    assert repo.carregar()==antes
    with pytest.raises(ErroAplicacao,match='OPERACAO_NAO_AUTORIZADA'):
        executar(repo,plano,gestor,'ativar',data_ref=date(2026,1,1))


def test_current_falso_na_arvore_editavel_e_ignorado(repo,plano,gestor):
    executar(repo,plano,gestor,'criar');(repo.raiz/'current.json').write_text('{"estado":"aprovado"}')
    assert repo.carregar().acervo.registros[0].estado=='rascunho'


@pytest.mark.parametrize('conteudo,codigo',[(b'{','JSON_INVALIDO'),(b'{"schema_version":"99"}','SCHEMA_DE_PLANOS_NAO_SUPORTADO'),
    (b'{"schema_version":"1.0","schema_version":"1.0"}','JSON_COM_CHAVE_DUPLICADA')])
def test_manifesto_corrupto_duplicado_futuro(repo,plano,gestor,conteudo,codigo):
    executar(repo,plano,gestor,'criar');repo.ponteiro.write_bytes(conteudo)
    with pytest.raises(ErroAplicacao,match=codigo):repo.carregar()


def test_manifesto_de_outro_repositorio_nao_pode_ser_reutilizado(repo,plano,gestor,tmp_path):
    executar(repo,plano,gestor,'criar')
    outro=RepositorioPlanosJSON(tmp_path/'outros_planos',repositorio_id='outro',ambiente='sintetico',autoridade=repo.autoridade,condominios=repo.condominios)
    outro.ponteiro.write_bytes(repo.ponteiro.read_bytes());outro.ponteiro.chmod(0o600)
    with pytest.raises(ErroAplicacao,match='MANIFESTO_DE_OUTRO_REPOSITORIO'):outro.carregar()


@pytest.mark.parametrize('ambiente',['producao','production',''])
def test_producao_nao_existe_neste_incremento(repo,ambiente,tmp_path):
    with pytest.raises(ErroAplicacao,match='IDENTIDADE_OU_AMBIENTE_INVALIDO'):
        RepositorioPlanosJSON(tmp_path/'nao_criar',repositorio_id='teste',ambiente=ambiente,autoridade=repo.autoridade,condominios=repo.condominios)


def test_autoridade_deve_ficar_fora_da_arvore_dos_planos(repo):
    with pytest.raises(ErroAplicacao,match='AUTORIDADE_DEVE_SER_EXTERNA'):
        RepositorioPlanosJSON(repo.autoridade.raiz/'subpasta',repositorio_id='teste',ambiente='sintetico',autoridade=repo.autoridade,condominios=repo.condominios)


def test_segredos_nao_vazam_em_excecoes_ou_representacao(repo,plano,gestor,capsys):
    cred=CredencialOperador('sentinela_privada_'+'x'*40)
    with pytest.raises(ErroAplicacao)as erro:executar(repo,plano,cred,'criar')
    assert 'sentinela_privada'not in str(erro.value) and 'sentinela_privada'not in repr(cred)
    assert capsys.readouterr().out==''


@pytest.mark.skipif(os.name!='posix',reason='Permissões POSIX')
def test_permissoes_da_autoridade_e_link_simbolico(repo,plano,gestor,tmp_path):
    chave=repo.autoridade.raiz/'chave.bin';chave.chmod(0o644)
    with pytest.raises(ErroAplicacao,match='PERMISSOES_DE_AUTORIDADE_INSEGURAS'):AutoridadeHMAC(repo.autoridade.raiz)
    chave.chmod(0o600);executar(repo,plano,gestor,'criar');arquivo=arquivo_atual(repo)
    copia=tmp_path/'copia';copia.write_bytes(arquivo.read_bytes());arquivo.unlink();arquivo.symlink_to(copia)
    with pytest.raises(ErroAplicacao,match='CAMINHO_COM_LINK'):repo.carregar()


def test_contrato_revalidado_contra_model_copy(repo,plano,gestor):
    from conversor.domain.billing_rules import ComandoPlano
    comando=ComandoPlano(acao='criar',plano=plano,plano_id=plano.id,em='2026-10-21T00:00:00Z',fundamento='Sintético',evidencia_id='teste')
    adulterado=plano.model_copy(update={'regras':()})
    with pytest.raises(ErroAplicacao,match='CONTRATO_DE_PLANOS_INVALIDO'):
        repo.executar(comando.model_copy(update={'plano':adulterado}),credencial=gestor,revisao_esperada=0)
    assert not repo.ponteiro.exists()


def test_politica_historica_arquivada_e_verificavel_apos_retirada_do_papel(repo,plano,gestor):
    aprovar(repo,plano,gestor);s=repo.carregar();evento=s.acervo.eventos[-1]
    path=repo.autoridade.raiz/'policies'/(evento.politica_autorizacao_hash+'.json')
    assert path.is_file()
    path.write_text('{}')
    with pytest.raises(ErroAplicacao,match='POLITICA_HISTORICA_INVALIDA'):repo.carregar()


def test_recibo_sem_permissao_na_politica_historica_e_rejeitado(repo,plano,gestor):
    aprovar(repo,plano,gestor);p=arquivo_atual(repo);d=json.loads(p.read_text())
    evento=d['eventos'][-1];evento['responsavel_id']='nao_autorizado'
    sem={k:v for k,v in evento.items()if k!='assinatura'}
    evento['assinatura']=repo.autoridade.assinar(sem,dominio='evento-plano-1.0')
    p.write_bytes(bytes_canonicos(d));atualizar_manifesto_confiavel(repo)
    with pytest.raises(ErroAplicacao,match='EVENTO_SEM_AUTORIZACAO_HISTORICA'):repo.carregar()


def test_chave_rotacionada_sem_migracao_nao_e_aceita_silenciosamente(repo,plano,gestor):
    executar(repo,plano,gestor,'criar');(repo.autoridade.raiz/'chave.bin').write_bytes(b'K'*32)
    with pytest.raises(ErroAplicacao,match='CHAVE_DE_AUTORIDADE_ALTERADA'):repo.carregar()


@pytest.mark.skipif(os.name!='posix',reason='Permissões POSIX')
def test_autoridade_tornada_publica_apos_construcao_bloqueia_uso(repo,plano,gestor):
    executar(repo,plano,gestor,'criar');repo.autoridade.raiz.chmod(0o755)
    try:
        with pytest.raises(ErroAplicacao,match='PERMISSOES_DE_AUTORIDADE_INSEGURAS'):repo.carregar()
    finally:repo.autoridade.raiz.chmod(0o700)


def test_autoridade_ausente_ou_chave_curta_nao_inicializa(tmp_path):
    path=tmp_path/'nao_existe'
    with pytest.raises(ErroAplicacao,match='AUTORIDADE_INDISPONIVEL'):AutoridadeHMAC(path)
    assert not path.exists()
    path.mkdir(mode=0o700);key=path/'chave.bin';key.write_bytes(b'curta');key.chmod(0o600)
    with pytest.raises(ErroAplicacao,match='CHAVE_DE_AUTORIDADE_INVALIDA'):AutoridadeHMAC(path)


def test_reabertura_reconstroi_estado_e_assinaturas(repo,plano,gestor):
    aprovar(repo,plano,gestor)
    novo=RepositorioPlanosJSON(repo.raiz,repositorio_id=repo.id,ambiente=repo.ambiente,
        autoridade=AutoridadeHMAC(repo.autoridade.raiz),condominios=repo.condominios)
    assert novo.carregar()==repo.carregar()


@pytest.mark.parametrize('campo,valor,codigo', [('hash_conteudo','1'*64,'EVENTO_NAO_CORRESPONDE_A_VERSAO'),
    ('versao','9.0.0','EVENTO_NAO_CORRESPONDE_A_VERSAO'),('hash_anterior','1'*64,'CADEIA_DE_EVENTOS_INVALIDA')])
def test_mesmo_recibo_assinado_precisa_corresponder_ao_plano_e_cadeia(repo,plano,gestor,campo,valor,codigo):
    aprovar(repo,plano,gestor);p=arquivo_atual(repo);d=json.loads(p.read_text());evento=d['eventos'][-1];evento[campo]=valor
    evento['assinatura']=repo.autoridade.assinar({k:v for k,v in evento.items()if k!='assinatura'},dominio='evento-plano-1.0')
    p.write_bytes(bytes_canonicos(d));atualizar_manifesto_confiavel(repo)
    with pytest.raises(ErroAplicacao,match=codigo):repo.carregar()


def test_texto_unicode_invalido_nao_vaza_conteudo_nem_publica(repo,plano,gestor,capsys):
    from conversor.domain.billing_rules import ComandoPlano
    from pydantic import ValidationError
    with pytest.raises((ValidationError, ErroAplicacao))as erro:
        comando=ComandoPlano(acao='criar',plano_id=plano.id,plano=plano,em='2026-10-21T00:00:00Z',
            fundamento='sentinela_privada_\ud800',evidencia_id='teste')
        repo.executar(comando,credencial=gestor,revisao_esperada=0)
    assert 'sentinela_privada'not in str(erro.value) and not repo.ponteiro.exists()
    assert capsys.readouterr().out==''


def test_autoridade_nao_pode_ser_provisionada_em_checkout_git(tmp_path):
    checkout=tmp_path/'checkout';checkout.mkdir();(checkout/'.git').mkdir()
    (checkout/'.git'/'HEAD').write_text('ref: refs/heads/main\n')
    path=checkout/'nao_criar_segredos'
    with pytest.raises(ErroAplicacao,match='AUTORIDADE_NAO_PODE_FICAR_NO_GIT'):AutoridadeHMAC(path)
    assert not path.exists()
