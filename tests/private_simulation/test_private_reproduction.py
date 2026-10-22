from datetime import date
from decimal import Decimal

import pytest

from tests.private_simulation.test_private_inventory import critico
from tests.rules.test_plan_repository import executar
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.canonical import Documento, EvidenciaDocumento, LoteCanonico


def salvar(c):
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    return c.executar()


def test_simulacao_privada_reproduz_bytes_e_preserva_financeiro(laboratorio):
    c = laboratorio()
    antes = hash_modelo(c.pacote)
    execucao = salvar(c)
    assert c.armazenamento.carregar_execucao(execucao.id) == execucao
    repeticao = c.servico.reproduzir(execucao.id)
    assert bytes_canonicos(repeticao.relatorio.model_dump(mode='json')) == bytes_canonicos(execucao.relatorio.model_dump(mode='json'))
    assert repeticao.hash_relatorio_original == hash_modelo(execucao.relatorio)
    assert hash_modelo(c.pacote) == antes
    b = c.pacote.entrada.lote.boletos[0]
    assert b.composicao.total_original == Decimal('100.00') and b.saldo_acumulado == Decimal('300.00')
    assert execucao.relatorio.boletos[0].situacao == 'elegivel_na_simulacao'
    assert not execucao.autoriza_cobranca and not execucao.permite_exportacao_operacional
    assert not repeticao.autoriza_cobranca and not repeticao.permite_exportacao_operacional


@pytest.mark.parametrize('escopo,registro_id,codigo', [
    ('arquivo', None, 'SUBTOTAL_FONTE_INCONSISTENTE'),
    ('registro', 'unidade_a', 'TITULARIDADE_NAO_CONFIRMADA'),
    ('registro', 'pessoa_sintetica', 'DOCUMENTOS_CONFLITANTES'),
    ('registro', 'boleto_a', 'BLOQUEIO_FINANCEIRO'),
    ('registro', 'registro_desconhecido', 'ESCOPO_NAO_RESOLVIDO'),
])
def test_bloqueios_externos_prevalecem_em_execucao_e_replay(laboratorio, origem, escopo, registro_id, codigo):
    o = critico(origem, codigo=codigo, escopo=escopo, registro_id=registro_id)
    c = laboratorio(ocorrencias=(o,))
    execucao = salvar(c)
    d = execucao.relatorio.boletos[0]
    assert d.situacao == 'bloqueado' and d.motivo_codigo == 'BLOQUEIO_CRITICO_PRESERVADO'
    assert next(x for x in d.ocorrencias_preservadas if x.id == o.id).codigo == codigo
    assert c.servico.reproduzir(execucao.id).relatorio == execucao.relatorio


def test_dois_documentos_validos_conflitantes_continuam_na_auditoria(laboratorio, pessoa, origem, unidade, boleto):
    evidencias = tuple(EvidenciaDocumento(documento=Documento(tipo='cpf', valor=v), origem=origem, titular_id=pessoa.id)
                       for v in ('00000000191', '00000000272'))
    pessoa = pessoa.model_copy(update={'evidencias_documentais': evidencias})
    c = laboratorio(lote=LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,)))
    execucao = salvar(c)
    assert execucao.relatorio.boletos[0].situacao == 'bloqueado'
    o = next(o for o in execucao.relatorio.ocorrencias_anteriores if o.codigo == 'DOCUMENTOS_CONFLITANTES')
    assert len(o.evidencias_documentais) == 2
    assert c.servico.reproduzir(execucao.id).relatorio == execucao.relatorio


@pytest.mark.parametrize('estado', ['rascunho', 'aguardando_aprovacao', 'aprovado'])
def test_sem_ativacao_e_aprovacao_atual_nao_simula(laboratorio, estado):
    c = laboratorio(estado=estado)
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    with pytest.raises(ErroAplicacao, match='PLANO_NAO_ATIVO_OU_REVOGADO'):
        c.executar()
    with pytest.raises(ErroAplicacao):
        c.armazenamento.carregar_execucao('execucao_sintetica')


def test_revogacao_impede_execucao_nova_mas_preserva_replay_historico(laboratorio):
    c = laboratorio()
    execucao = salvar(c)
    executar(c.repo, c.plano, c.gestor, 'revogar')
    with pytest.raises(ErroAplicacao, match='PLANO_NAO_ATIVO_OU_REVOGADO'):
        c.executar('nova')
    historico = c.servico.reproduzir(execucao.id)
    assert historico.relatorio == execucao.relatorio
    assert historico.modo == 'reproducao_historica_sem_autorizacao_atual'
    assert not historico.autoriza_cobranca


@pytest.mark.parametrize('campo,valor', [('condominio_id', 'cond_outro'), ('ambiente', 'privado'), ('plano_hash', '8' * 64),
                                        ('plano_versao', '9.0.0'), ('data_ref', date(2028, 1, 1)), ('data_ref', date(2026, 10, 20))])
def test_isolamento_de_condominio_versao_ambiente_e_data(laboratorio, campo, valor):
    c = laboratorio()
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    c.solicitacao = c.solicitacao.model_copy(update={campo: valor})
    # O closure da fixture referencia a solicitação original; chamar o caso de uso diretamente.
    with pytest.raises(ErroAplicacao):
        c.servico.executar(id_='outra', pacote_id=c.pacote.id, solicitacao=c.solicitacao, em='2026-10-21T13:00:00Z',
            fundamento='Teste', evidencia_id='evidencia', credencial=c.gestor)


@pytest.mark.parametrize('alvo', ['pacote', 'execucao', 'fonte', 'implementacao', 'assinatura_historica'])
def test_replay_recusa_conteudo_ou_contexto_alterado(laboratorio, monkeypatch, alvo):
    c = laboratorio()
    execucao = salvar(c)
    if alvo in ('pacote', 'execucao'):
        path, _ = c.armazenamento._paths(alvo, c.pacote.id if alvo == 'pacote' else execucao.id)
        path.write_bytes(path.read_bytes() + b' ')
    elif alvo == 'fonte':
        c.primaria.write_bytes(b'Mudanca sintetica')
    elif alvo == 'implementacao':
        monkeypatch.setattr('conversor.application.private_simulation.hash_implementacao', lambda: '0' * 64)
    else:
        monkeypatch.setattr(c.autoridade, 'conferir_evento', lambda evento: (_ for _ in ()).throw(ErroAplicacao('ASSINATURA_INVALIDA')))
    with pytest.raises(ErroAplicacao):
        c.servico.reproduzir(execucao.id)


def test_mudanca_administrativa_entre_simulacao_e_persistencia_recusa(laboratorio, monkeypatch):
    c = laboratorio()
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    original = c.servico.atual.conferir
    chamadas = 0
    def conferir(estado):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 4:
            executar(c.repo, c.plano, c.gestor, 'revogar')
        original(estado)
    monkeypatch.setattr(c.servico.atual, 'conferir', conferir)
    with pytest.raises(ErroAplicacao):
        c.executar()
    with pytest.raises(ErroAplicacao):
        c.armazenamento.carregar_execucao('execucao_sintetica')


@pytest.mark.parametrize('ataque', ['omitir_boleto', 'omitir_ocorrencia', 'liberar_critico', 'alterar_entrada'])
def test_armazenamento_recusa_relatorio_que_omita_cobertura_ou_bloqueio(laboratorio, origem, ataque):
    c = laboratorio(ocorrencias=(critico(origem),))
    execucao = salvar(c)
    relatorio = execucao.relatorio
    if ataque == 'omitir_boleto':
        relatorio = relatorio.model_copy(update={'boletos': ()})
    elif ataque == 'omitir_ocorrencia':
        relatorio = relatorio.model_copy(update={'ocorrencias_anteriores': ()})
    elif ataque == 'liberar_critico':
        d = relatorio.boletos[0].model_copy(update={'situacao': 'elegivel_na_simulacao'})
        relatorio = relatorio.model_copy(update={'boletos': (d,)})
    else:
        relatorio = relatorio.model_copy(update={'hash_entrada': '1' * 64})
    execucao = execucao.model_copy(update={'id': 'forjada', 'relatorio': relatorio})
    with pytest.raises(ErroAplicacao, match='RELATORIO_'):
        c.armazenamento.gravar_execucao(execucao, credencial=c.gestor)


def test_revogacao_durante_commit_nao_devolve_execucao_como_atual(laboratorio, monkeypatch):
    c = laboratorio()
    c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)
    original = c.armazenamento.gravar_execucao
    def gravar(execucao, *, credencial):
        original(execucao, credencial=credencial)
        executar(c.repo, c.plano, c.gestor, 'revogar')
    monkeypatch.setattr(c.armazenamento, 'gravar_execucao', gravar)
    with pytest.raises(ErroAplicacao):
        c.executar()
    # O commit não é desfeito: conserva evidência histórica explícita, jamais autorização atual.
    historico = c.servico.reproduzir('execucao_sintetica')
    assert historico.identico and not historico.autoriza_cobranca
