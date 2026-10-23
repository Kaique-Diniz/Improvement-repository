from datetime import date
from hashlib import sha256
from types import SimpleNamespace
import json
import secrets

import pytest

from conversor.adapters.integrated_processing_json import RepositorioProcessamentosSinteticosJSON
from conversor.application.billing_ports import CredencialOperador
from conversor.application.integrated_processing import ProcessarEnsaioSintetico
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.canonical import Ocorrencia
from tests.rules.test_plan_repository import arquivo_atual, executar


@pytest.mark.parametrize('estado', ['rascunho', 'aguardando_aprovacao', 'aprovado', 'revogado'])
def test_acumulo_de_papeis_nao_aprova_ou_ativa_automaticamente(integrado, estado):
    c = integrado(estado=estado)
    antes = c.repo.carregar()
    with pytest.raises(ErroAplicacao, match='PLANO_NAO_ATIVO_OU_REVOGADO'):
        c.executar()
    assert c.repo.carregar() == antes
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


@pytest.mark.parametrize('campo,valor', [('data_ref', None), ('data_ref', ''), ('data_ref', '21/10/2026'),
    ('data_ref', '2026-02-30'), ('data_ref', 123), ('data_ref', True), ('modo_cadastro', None),
    ('modo_cadastro', 'C'), ('ambiente', 'privado'), ('em', '2026-10-21T13:00:00'), ('fundamento', ' ')])
def test_parametros_invalidos_rejeitados_antes_de_io(integrado, campo, valor, monkeypatch):
    c = integrado()
    def proibido(*args, **kwargs):pytest.fail('Nao deveria carregar fonte nem autenticar')
    monkeypatch.setattr(c.servico.autenticador, 'autenticar', proibido)
    monkeypatch.setattr(c.armazenamento, 'carregar_preparacao_tecnica', proibido)
    with pytest.raises(ErroAplicacao, match='PEDIDO_INTEGRADO_INVALIDO'):
        c.servico.executar(c.pedido.model_copy(update={campo: valor}), credencial=c.gestor)


@pytest.mark.parametrize('referencia', [date(2027, 1, 1), date(2027, 5, 1)])
def test_vigencia_do_plano_nao_se_confunde_com_referencia(integrado, referencia):
    c = integrado()
    with pytest.raises(ErroAplicacao, match='DATA_REF_FORA_DA_VIGENCIA_DO_PLANO'):
        c.servico.executar(c.pedido.model_copy(update={'data_ref': referencia}), credencial=c.gestor)


@pytest.mark.parametrize('campo,valor', [('plano_id', 'nao_existe'), ('plano_versao', '99.0.0'),
    ('plano_hash', 'f' * 64), ('preparacao_hash', 'f' * 64), ('administradora_id', 'outra'),
    ('condominio_id', 'cond_outro')])
def test_vinculos_e_hashes_incorretos_impedem_processamento(integrado, campo, valor):
    c = integrado()
    with pytest.raises(ErroAplicacao):
        c.servico.executar(c.pedido.model_copy(update={campo: valor}), credencial=c.gestor)
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


@pytest.mark.parametrize('campo,valor', [('versao', '9.0.0'), ('sha256', 'f' * 64), ('arquivo_id', 'outra_regua')])
def test_regua_deve_ter_versao_e_hash_comprovados_na_fonte(integrado, campo, valor):
    c = integrado()
    regua = c.pedido.regua.model_copy(update={campo: valor})
    with pytest.raises(ErroAplicacao):
        c.servico.executar(c.pedido.model_copy(update={'regua': regua}), credencial=c.gestor)


@pytest.mark.parametrize('alvo', ['manifesto_assinatura', 'snapshot', 'snapshot_e_hash'])
def test_configuracao_ativa_adulterada_nao_e_aprovacao_valida(integrado, alvo):
    c = integrado()
    if alvo == 'manifesto_assinatura':
        m = json.loads(c.repo.ponteiro.read_text()); m['assinatura'] = '0' * 64
        c.repo.ponteiro.write_bytes(bytes_canonicos(m))
    else:
        path = arquivo_atual(c.repo)
        dados = json.loads(path.read_text())
        dados['registros'][0]['conteudo']['regras'][0]['prioridade'] = 9
        if alvo == 'snapshot_e_hash':
            dados['registros'][0]['hash_conteudo'] = sha256(bytes_canonicos(dados['registros'][0]['conteudo'])).hexdigest()
        path.write_bytes(bytes_canonicos(dados))
    with pytest.raises(ErroAplicacao):c.executar()


@pytest.mark.parametrize('caso', ['credencial_invalida', 'sem_permissao_operador', 'ator_forjado'])
def test_ato_operador_exige_autenticacao_e_autorizacao(integrado, caso):
    c = integrado()
    cred = (CredencialOperador(secrets.token_hex(32)) if caso == 'credencial_invalida'
            else c.seguranca[1]['aprovador'] if caso == 'sem_permissao_operador' else c.gestor)
    pedido = c.pedido.model_copy(update={'operador_id': 'outra_identidade'}) if caso == 'ator_forjado' else c.pedido
    with pytest.raises(ErroAplicacao):c.servico.executar(pedido, credencial=cred)
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


@pytest.mark.parametrize('codigo,escopo', [('SUBTOTAL_BLOCO_DIVERGENTE', 'arquivo'),
    ('TITULARIDADE_FL_NAO_CONFIRMADA', 'registro'), ('DOCUMENTOS_CONFLITANTES', 'registro')])
def test_bloqueios_criticos_preservados_em_historico_reconciliado(integrado, origem, unidade, codigo, escopo):
    o = Ocorrencia(id='critico_inventado', processamento_id='anterior', codigo=codigo, gravidade='critico',
        escopo=escopo, registro_id=unidade.id if escopo == 'registro' else None, origem=origem)
    c = integrado(specs=[{'dias': 31}, {'dias': 30}], modo='B', ocorrencias=(o,))
    r = c.executar()
    assert all(d.situacao == 'bloqueado' for d in r.projecao.relatorio_motor.boletos)
    assert not r.projecao.boletos_divida and not r.projecao.candidatos_cadastrais
    vinculo = c.preparacao.candidato.reconciliacao.registros[0]
    assert vinculo.id_legado == o.id and vinculo.id_interno.startswith('auditoria:v1:')
    assert any(x.id == vinculo.id_interno for x in r.projecao.relatorio_motor.ocorrencias_anteriores)
    assert c.servico.reproduzir(r.id).projecao == r.projecao


def test_documento_v2_legado_preservado_sem_fusao_de_evidencias(integrado, origem, unidade):
    o = Ocorrencia(id='documento:v2:' + 'b' * 64, processamento_id='anterior', codigo='DOCUMENTOS_CONFLITANTES',
        gravidade='critico', escopo='registro', registro_id=unidade.id, origem=origem)
    c = integrado(documentais=(o,))
    r = c.executar()
    mapa = c.preparacao.candidato.reconciliacao.registros
    assert len(mapa) == 1 and mapa[0].id_legado == o.id and mapa[0].original.id == o.id
    assert mapa[0].id_interno.startswith('auditoria:v1:')
    assert c.armazenamento.carregar_processamento(r.id) == r
    assert c.armazenamento.carregar_preparacao_tecnica(c.preparacao.id) == c.preparacao


@pytest.mark.parametrize('documento,situacao', [(None, 'elegivel_na_simulacao'),
    ({'tipo': 'cpf', 'valor': '123'}, 'elegivel_na_simulacao')])
def test_ausencia_e_invalidade_de_documento_preservam_politica(integrado, documento, situacao):
    def editar(e):e['lote']['pessoas'][0]['documento'] = documento
    c = integrado(editar_entrada=editar)
    r = c.executar()
    assert r.projecao.relatorio_motor.boletos[0].situacao == situacao
    assert c.servico.reproduzir(r.id).projecao == r.projecao


def test_revogacao_posterior_nao_impede_reproducao_historica_sem_autorizacao(integrado):
    c = integrado()
    r = c.executar()
    executar(c.repo, c.plano, c.gestor, 'revogar')
    with pytest.raises(ErroAplicacao, match='PLANO_NAO_ATIVO_OU_REVOGADO'):c.executar()
    copia = c.servico.reproduzir(r.id)
    assert copia.identico and not copia.autoriza_cobranca and not copia.permite_exportacao_operacional


@pytest.mark.parametrize('caso', ['adapter', 'orquestrador'])
def test_ambiente_real_recusado_sem_acesso_a_fontes(integrado, tmp_path, caso):
    c = integrado()
    if caso == 'adapter':
        destino = tmp_path / 'nao_criar'
        with pytest.raises(ErroAplicacao, match='SOMENTE_SINTETICO'):
            RepositorioProcessamentosSinteticosJSON(destino, repositorio_id='proibido',
                autoridade=c.seguranca[0], ambiente='privado')
        assert not destino.exists()
    else:
        with pytest.raises(ErroAplicacao, match='SOMENTE_SINTETICO'):
            ProcessarEnsaioSintetico(SimpleNamespace(ambiente='privado'), None, None, None, None, None, None)


def test_administradora_canonica_deve_corresponder_ao_contexto(integrado):
    def editar(e):e['lote']['unidades'][0]['administradora_id'] = 'administradora_divergente'
    c = integrado(editar_entrada=editar)
    with pytest.raises(ErroAplicacao, match='UNIDADE_DE_OUTRA_ADMINISTRADORA'):c.executar()


def test_json_marcado_ativo_sem_eventos_de_aprovacao_e_ativacao_e_recusado(integrado):
    c = integrado(estado='rascunho')
    path = arquivo_atual(c.repo)
    dados = json.loads(path.read_text()); dados['registros'][0]['estado'] = 'ativo'
    path.write_bytes(bytes_canonicos(dados))
    manifesto = json.loads(c.repo.ponteiro.read_text())
    manifesto['sha256'] = sha256(path.read_bytes()).hexdigest()
    # Mesmo um manifesto sintético válido não cria os eventos ausentes no acervo.
    manifesto['assinatura'] = c.seguranca[0].assinar(
        {k: v for k, v in manifesto.items() if k != 'assinatura'}, dominio='manifesto-planos-1.0')
    c.repo.ponteiro.write_bytes(bytes_canonicos(manifesto))
    with pytest.raises(ErroAplicacao):c.executar()
