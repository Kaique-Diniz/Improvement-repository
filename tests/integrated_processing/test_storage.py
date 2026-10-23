from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path

from filelock import FileLock
import pytest
from pydantic import ValidationError

from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.integrated_processing import ExecucaoIntegradaSintetica
from conversor.integrated_processing_schemas import documentos, main


@pytest.mark.parametrize('fase', ['payload', 'recibo_escrita', 'recibo_commit'])
def test_interrupcao_nao_expoe_resultado_sem_commit_e_permite_recuperacao(integrado, monkeypatch, fase):
    c = integrado(modo='B')
    from conversor.adapters import private_simulation_json as modulo
    original_replace, original_gravar = modulo.os.replace, modulo._gravar
    destino, recibo = c.armazenamento._paths('processamento_sintetico', c.pedido.processamento_id)
    def replace(origem, alvo):
        if (fase == 'payload' and alvo == destino) or (fase == 'recibo_commit' and alvo == recibo):
            raise OSError('Interrupcao sintetica')
        return original_replace(origem, alvo)
    def gravar(path, conteudo):
        if fase == 'recibo_escrita' and path.parent == c.armazenamento.ancoras:
            raise OSError('Interrupcao sintetica')
        return original_gravar(path, conteudo)
    with monkeypatch.context() as m:
        m.setattr(modulo.os, 'replace', replace)
        m.setattr(modulo, '_gravar', gravar)
        with pytest.raises(ErroAplicacao, match='ARTEFATO_PRIVADO_INDISPONIVEL'):c.executar()
    assert not recibo.exists()
    with pytest.raises(ErroAplicacao):c.armazenamento.carregar_processamento(c.pedido.processamento_id)
    assert not list(c.armazenamento.raiz.glob('*.tmp'))
    assert not list(c.armazenamento.ancoras.glob('*.tmp'))
    r = c.executar()
    assert c.servico.reproduzir(r.id).projecao == r.projecao


@pytest.mark.parametrize('ataque', ['payload', 'hash_recibo', 'assinatura', 'recibo_ausente', 'identidade'])
def test_historico_adulterado_nao_e_reproduzido_nem_sobrescrito(integrado, ataque):
    c = integrado()
    r = c.executar()
    path, recibo = c.armazenamento._paths('processamento_sintetico', r.id)
    if ataque in ('payload', 'hash_recibo'):
        dados = json.loads(path.read_text()); dados['pedido']['fundamento'] = 'Alteracao inventada'
        path.write_bytes(bytes_canonicos(dados))
        if ataque == 'hash_recibo':
            d = json.loads(recibo.read_text()); d['sha256'] = sha256(path.read_bytes()).hexdigest()
            recibo.write_bytes(bytes_canonicos(d))
    elif ataque == 'recibo_ausente':
        recibo.unlink()
    else:
        d = json.loads(recibo.read_text())
        d['assinatura' if ataque == 'assinatura' else 'id'] = '0' * 64
        recibo.write_bytes(bytes_canonicos(d))
    with pytest.raises(ErroAplicacao):c.servico.reproduzir(r.id)
    if ataque != 'recibo_ausente':
        with pytest.raises(ErroAplicacao):c.executar()


def test_orfao_com_conteudo_diferente_nunca_e_sobrescrito(integrado):
    c = integrado()
    r = c.executar()
    path, recibo = c.armazenamento._paths('processamento_sintetico', r.id)
    recibo.unlink()
    original = path.read_bytes()
    with pytest.raises(ErroAplicacao, match='PROCESSAMENTO_ORFAO_DIVERGENTE_REQUER_REVISAO'):
        c.servico.executar(c.pedido.model_copy(update={'modo_cadastro': 'B'}), credencial=c.gestor)
    assert path.read_bytes() == original and not recibo.exists()


def test_concorrencia_identica_realiza_um_unico_commit(integrado, monkeypatch):
    c = integrado()
    c.armazenamento.timeout = 5
    chamadas = []
    original = c.armazenamento._guardar
    def gravar(*args, **kwargs):
        chamadas.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(c.armazenamento, '_guardar', gravar)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: c.executar(), range(2)))
    assert resultados[0] == resultados[1] and len(chamadas) == 1


def test_lock_ocupado_nao_publica_resultado(integrado):
    c = integrado()
    with FileLock(c.armazenamento.ancoras / 'processamentos.lock', mode=0o600):
        with pytest.raises(ErroAplicacao, match='REPOSITORIO_PRIVADO_OCUPADO'):c.executar()
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


@pytest.mark.parametrize('alvo', ['fonte', 'regua', 'preparacao', 'historico'])
def test_fontes_e_inventarios_ausentes_ou_adulterados_impedem_processamento(integrado, alvo):
    c = integrado()
    if alvo == 'fonte':c.primaria.unlink()
    elif alvo == 'regua':c.regua_path.write_bytes(b'{}')
    elif alvo == 'historico':
        Path(c.preparacao.candidato.reconciliacao.fontes[0].arquivo.caminho).write_bytes(b'[]\n')
    else:
        path, _ = c.armazenamento._paths('preparacao_tecnica', c.preparacao.id)
        dados = json.loads(path.read_text()); dados['candidato']['catalogos'] = []
        path.write_bytes(bytes_canonicos(dados))
    with pytest.raises(ErroAplicacao):c.executar()
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


def test_preparacao_parcial_nao_pode_ser_registrada(integrado):
    c = integrado()
    candidato = c.preparacao.candidato.model_copy(update={'catalogos': c.preparacao.candidato.catalogos[:3]})
    prep = c.preparacao.model_copy(update={'id': 'parcial', 'candidato': candidato})
    with pytest.raises(ErroAplicacao, match='CONTRATO_PRIVADO_INVALIDO'):
        c.armazenamento.gravar_preparacao_tecnica(prep, credencial=c.gestor)


def test_persistencia_nao_remove_evidencias_nem_altera_fontes(integrado, capsys):
    c = integrado(specs=[{'ap': 'AJ'}, {'dias': 31}, {'dias': 30}], modo='B')
    fontes = {f.caminho: Path(f.caminho).read_bytes() for f in c.preparacao.candidato.fontes}
    r = c.executar()
    assert all(Path(p).read_bytes() == conteudo for p, conteudo in fontes.items())
    assert c.servico.reproduzir(r.id).projecao == r.projecao
    path, recibo = c.armazenamento._paths('processamento_sintetico', r.id)
    assert c.gestor.segredo not in path.read_text() + recibo.read_text()
    if os.name == 'posix':
        assert path.stat().st_mode & 0o777 == recibo.stat().st_mode & 0o777 == 0o600
    assert not list(c.armazenamento.raiz.rglob('*.xlsx'))
    assert not capsys.readouterr().out


def test_contrato_nao_aceita_autorizacao_operacional_ou_atesto(integrado):
    r = integrado().executar()
    for campo in ('autoriza_cobranca', 'permite_exportacao_operacional', 'atesto_humano_emitido'):
        with pytest.raises(ValidationError):
            ExecucaoIntegradaSintetica.model_validate(r.model_dump() | {campo: True})


@pytest.mark.parametrize('alvo', ['aprovacao_hash', 'ativacao_hash', 'plano_hash'])
def test_adapter_tambem_recusa_prova_ou_hash_nao_associados_ao_plano(integrado, alvo):
    c = integrado()
    original = c.executar()
    d = original.model_dump()
    rel = d['projecao']['relatorio_motor']
    if alvo == 'plano_hash':
        d['pedido']['plano_hash'] = rel['solicitacao']['plano_hash'] = 'f' * 64
    else:
        rel['prova_plano'][alvo] = 'f' * 64
    # Recalcular hash público não substitui aprovação/ativação assinadas.
    d['projecao']['hash_relatorio_motor'] = sha256(bytes_canonicos(
        original.projecao.relatorio_motor.model_validate(rel).model_dump(mode='json'))).hexdigest()
    adulterado = ExecucaoIntegradaSintetica.model_validate(d)
    with pytest.raises(ErroAplicacao):
        c.armazenamento.salvar_processamento(adulterado, credencial=c.gestor)
    assert c.armazenamento.carregar_processamento(original.id) == original


@pytest.mark.parametrize('alvo', ['plano', 'catalogo'])
def test_mudanca_durante_avaliacao_nao_devolve_execucao_atual(integrado, monkeypatch, alvo):
    c = integrado()
    from conversor.application import integrated_processing as modulo
    from tests.rules.test_plan_repository import executar
    original = modulo.SimularProcessamentoSintetico.executar
    def avaliar(self, *args, **kwargs):
        r = original(self, *args, **kwargs)
        if alvo == 'plano':executar(c.repo, c.plano, c.gestor, 'revogar')
        else:c.catalogo.condominio = c.catalogo.condominio.model_copy(update={'nome': 'Nome inventado posterior'})
        return r
    monkeypatch.setattr(modulo.SimularProcessamentoSintetico, 'executar', avaliar)
    with pytest.raises(ErroAplicacao):c.executar()
    assert not list(c.armazenamento.raiz.glob('processamento_sintetico-*.json'))


def test_mudanca_apos_commit_conserva_apenas_historico_sem_resultado_atual(integrado, monkeypatch):
    c = integrado()
    from tests.rules.test_plan_repository import executar
    original = c.armazenamento.salvar_processamento
    def salvar(*args, **kwargs):
        r = original(*args, **kwargs)
        executar(c.repo, c.plano, c.gestor, 'revogar')
        return r
    monkeypatch.setattr(c.armazenamento, 'salvar_processamento', salvar)
    with pytest.raises(ErroAplicacao):c.executar()
    copia = c.servico.reproduzir(c.pedido.processamento_id)
    assert copia.identico and not copia.autoriza_cobranca


def test_pin_de_implementacao_divergente_impede_reproducao(integrado, monkeypatch):
    c = integrado()
    r = c.executar()
    from conversor.application import integrated_processing as modulo
    monkeypatch.setattr(modulo, 'hash_implementacao_integrada', lambda: '0' * 64)
    with pytest.raises(ErroAplicacao, match='IMPLEMENTACAO_INTEGRADA_HISTORICA_INDISPONIVEL'):
        c.servico.reproduzir(r.id)


def test_schemas_aditivos_publicados_e_reproduziveis(tmp_path):
    assert main(['--check']) == 0
    assert main(['--saida', str(tmp_path)]) == 0
    for nome, conteudo in documentos():
        assert (tmp_path / nome).read_text() == conteudo
        s = json.loads(conteudo)
        assert s['additionalProperties'] is False and s['$schema'].endswith('2020-12/schema')
    (tmp_path / 'pedido.schema.json').write_text('{}')
    assert main(['--check', '--saida', str(tmp_path)]) == 1
