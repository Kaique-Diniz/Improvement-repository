from hashlib import sha256
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from tests.private_simulation.test_private_inventory import critico
from conversor.adapters.audit_history import reconstruir_reconciliacao, conferir_reconciliacao
from conversor.application.documents import id_documental_legado
from conversor.application.billing_evaluation import normalizar_entrada
from conversor.application.ports import ErroAplicacao
from conversor.application.simulation_inventory import conferir_pacote, inventariar
from conversor.domain.audit_identity import (CandidatoReconciliado, FonteHistorico, PacoteReconciliado,
    PreparacaoTecnica, ReconciliacaoOcorrencias, VinculoOcorrencia)
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.canonical import Documento, EvidenciaDocumento
from conversor.domain.private_simulation import FontePrivada
from conversor.audit_schemas import main


@pytest.fixture
def historico(laboratorio, origem, tmp_path):
    c = laboratorio(ocorrencias=(critico(origem, codigo='BLOQUEIO_OPERACIONAL'),))
    origem = c.pacote.entrada.lote.unidades[0].origem
    ops = c.pacote.entrada.ocorrencias_anteriores
    casos = []
    for i, valor in enumerate(('00000000272', '00000000353')):
        evidencia = (EvidenciaDocumento(documento=Documento(tipo='cpf', valor='00000000191'), origem=origem),
                     EvidenciaDocumento(documento=Documento(tipo='cpf', valor=valor),
                         origem=origem.model_copy(update={'linha': i + 10, 'identificador': f'linha_{i}'})))
        originais = [critico(origem, codigo=codigo, escopo='registro', registro_id='unidade_a',
            id_=id_documental_legado(processamento_id='revisao_anterior', unidade_id='unidade_a', codigo=codigo))
            .model_copy(update={'evidencias_documentais': evidencia})
            for codigo in ('DOCUMENTOS_CONFLITANTES', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO')]
        casos.append({'ocorrencias': [o.model_dump(mode='json') for o in originais]})
    arquivos = []
    for nome, payload, namespace, estrutura in (
            ('ops', [o.model_dump(mode='json') for o in ops], 'operacional', 'lista_ocorrencias'),
            ('docs', {'casos': casos}, 'documental', 'casos_documentais')):
        path = tmp_path / (nome + '.json'); path.write_bytes(bytes_canonicos(payload)); path.chmod(0o600)
        fonte = FonteHistorico(arquivo=FontePrivada(arquivo_id=nome, caminho=str(path), sha256=sha256(path.read_bytes()).hexdigest(),
            tamanho=path.stat().st_size, papel='evidencia'), namespace=namespace, produtor_id=nome,
            produtor_versao='1.0', estrutura=estrutura)
        arquivos.append(fonte)
    rec = reconstruir_reconciliacao(id_='reconciliacao_sintetica', condominio_id=c.pacote.condominio_id,
                                  ambiente='sintetico', fontes=tuple(arquivos))
    entrada = normalizar_entrada(c.pacote.entrada.model_copy(update={'ocorrencias_anteriores': rec.ocorrencias()}))
    catalogos = tuple(cat.model_copy(update={'ocorrencias': tuple(
        r.para_entrada() for r in rec.registros if
        cat.categoria == ('documentos' if r.localizacao.namespace == 'documental' else 'leitura'))}) for cat in c.pacote.catalogos)
    candidato = CandidatoReconciliado(id='candidato_reconciliado', condominio_id=c.pacote.condominio_id, ambiente='sintetico',
        entrada=entrada, catalogos=catalogos, fontes=c.pacote.fontes + tuple(f.arquivo for f in arquivos),
        reconciliacao=rec, inventario=inventariar(entrada, catalogos, rec))
    preparacao = PreparacaoTecnica(id='preparacao_sintetica', condominio_id=candidato.condominio_id,
        ambiente=candidato.ambiente, candidato=candidato)
    pacote = PacoteReconciliado(**candidato.model_dump(), atesto=c.pacote.atesto)
    return SimpleNamespace(c=c, rec=rec, fontes=tuple(arquivos), candidato=candidato, preparacao=preparacao, pacote=pacote)


def test_quatro_registros_documentais_com_dois_ids_legados_preservados(historico):
    h = historico
    conferir_pacote(h.candidato); conferir_reconciliacao(h.rec)
    docs = [r for r in h.rec.registros if r.localizacao.namespace == 'documental']
    assert len(docs) == 4 and len({r.id_legado for r in docs}) == 2
    assert len({r.id_interno for r in docs}) == 4
    assert all(r.original.id == r.id_legado and r.hash_original == hash_modelo(r.original) for r in docs)
    assert all(r.para_entrada().model_dump(exclude={'id'}) == r.original.model_dump(exclude={'id'}) for r in h.rec.registros)
    assert all(r.original.bloqueante for r in h.rec.registros)
    assert len(h.candidato.entrada.ocorrencias_anteriores) == 5


def test_reprocessamento_deterministico_e_fontes_inalteradas(historico):
    h = historico
    hashes = {f.arquivo.caminho: sha256(open(f.arquivo.caminho, 'rb').read()).hexdigest() for f in h.fontes}
    copia = reconstruir_reconciliacao(id_=h.rec.id, condominio_id=h.rec.condominio_id, ambiente=h.rec.ambiente,
                                     fontes=tuple(reversed(h.fontes)))
    assert bytes_canonicos(copia.model_dump(mode='json')) == bytes_canonicos(h.rec.model_dump(mode='json'))
    assert all(sha256(open(p, 'rb').read()).hexdigest() == digest for p, digest in hashes.items())


def test_namespace_operacional_e_documental_separados_mesmo_registro(historico):
    h = historico
    fonte = next(f for f in h.fontes if f.namespace == 'operacional')
    alternativa = fonte.model_copy(update={'namespace': 'documental'})
    a = reconstruir_reconciliacao(id_='a', condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=(fonte,))
    b = reconstruir_reconciliacao(id_='b', condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=(alternativa,))
    assert a.registros[0].original == b.registros[0].original
    assert a.registros[0].id_interno != b.registros[0].id_interno


@pytest.mark.parametrize('campo', ['id_interno', 'id_legado', 'hash_original', 'origem', 'documento'])
def test_mapeamento_alterado_nao_passara_por_validacao(historico, campo):
    r = next(r for r in historico.rec.registros if r.localizacao.namespace == 'documental')
    dados = r.model_dump(mode='json')
    if campo in ('id_interno', 'id_legado'):
        dados[campo] = 'forjado'
    elif campo == 'hash_original':
        dados[campo] = '0' * 64
    elif campo == 'origem':
        dados['original']['origem']['linha'] = 999
    else:
        dados['original']['evidencias_documentais'][0]['documento']['valor'] = '00000000353'
    with pytest.raises(ValidationError):
        VinculoOcorrencia.model_validate(dados)


@pytest.mark.parametrize('ataque', ['omitir', 'duplicar', 'hash_bruto', 'ponteiro', 'versao', 'namespace'])
def test_reconstrucao_nega_historico_incompleto_ou_remapeado(historico, ataque):
    h = historico
    rec = h.rec
    if ataque == 'omitir':
        rec = rec.model_copy(update={'registros': rec.registros[1:]})
    elif ataque == 'duplicar':
        rec = rec.model_copy(update={'registros': (*rec.registros, rec.registros[0])})
    elif ataque == 'hash_bruto':
        r = rec.registros[0].model_copy(update={'hash_registro_bruto': '0' * 64})
        rec = rec.model_copy(update={'registros': (r, *rec.registros[1:])})
    else:
        r = rec.registros[0]
        chave = {'ponteiro': 'ponteiro_json', 'versao': 'produtor_versao', 'namespace': 'namespace'}[ataque]
        valor = {'ponteiro': '/999', 'versao': '99.0', 'namespace': 'outro'}[ataque]
        r = r.model_copy(update={'localizacao': r.localizacao.model_copy(update={chave: valor})})
        rec = rec.model_copy(update={'registros': (r, *rec.registros[1:])})
    with pytest.raises((ErroAplicacao, ValidationError)):
        conferir_reconciliacao(rec)


@pytest.mark.parametrize('ataque', ['arquivo_ausente', 'arquivo_alterado', 'parcial', 'caso_sem_ocorrencias'])
def test_ausencia_e_carga_parcial_nao_viram_vazio(historico, ataque):
    from pathlib import Path
    h = historico
    f = next(f for f in h.fontes if f.namespace == 'documental')
    path = Path(f.arquivo.caminho)
    if ataque == 'arquivo_ausente':
        path.unlink()
    elif ataque == 'arquivo_alterado':
        path.write_bytes(b'{}')
    elif ataque == 'parcial':
        path.write_bytes(path.read_bytes()[:50])
    else:
        dados = json.loads(path.read_bytes()); del dados['casos'][1]['ocorrencias']
        path.write_bytes(bytes_canonicos(dados))
        f = f.model_copy(update={'arquivo': f.arquivo.model_copy(update={'sha256': sha256(path.read_bytes()).hexdigest(), 'tamanho': path.stat().st_size})})
        h.fontes = tuple(f if v.namespace == 'documental' else v for v in h.fontes)
    with pytest.raises(ErroAplicacao):
        reconstruir_reconciliacao(id_=h.rec.id, condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=h.fontes)


def test_conteudo_identico_em_posicoes_distintas_nao_e_deduplicado(historico):
    from pathlib import Path
    h = historico
    fonte = next(f for f in h.fontes if f.namespace == 'operacional')
    path = Path(fonte.arquivo.caminho)
    dados = json.loads(path.read_bytes()); dados.append(dados[0])
    path.write_bytes(bytes_canonicos(dados))
    fonte = fonte.model_copy(update={'arquivo': fonte.arquivo.model_copy(update={'sha256': sha256(path.read_bytes()).hexdigest(), 'tamanho': path.stat().st_size})})
    rec = reconstruir_reconciliacao(id_='duplicata_legitima', condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=(fonte,))
    assert len(rec.registros) == 2 and rec.registros[0].original == rec.registros[1].original
    assert rec.registros[0].id_interno != rec.registros[1].id_interno


def test_registro_assinado_tecnico_nao_e_pacote_aprovado(historico):
    h = historico; repo = h.c.armazenamento
    repo.gravar_reconciliacao(h.rec, credencial=h.c.gestor)
    repo.gravar_preparacao_tecnica(h.preparacao, credencial=h.c.gestor)
    assert repo.carregar_reconciliacao(h.rec.id) == h.rec
    assert repo.carregar_preparacao_tecnica(h.preparacao.id) == h.preparacao
    assert not h.preparacao.autoriza_cobranca and not h.preparacao.permite_exportacao_operacional
    with pytest.raises(ErroAplicacao):
        repo.carregar_pacote(h.preparacao.id)
    with pytest.raises(ErroAplicacao):
        repo.gravar_pacote(h.candidato, credencial=h.c.gestor)


@pytest.mark.parametrize('tipo', ['reconciliacao', 'preparacao_tecnica'])
def test_assinaturas_adulteradas_bloqueiam_leitura(historico, tipo):
    h = historico; repo = h.c.armazenamento
    objeto = h.rec if tipo == 'reconciliacao' else h.preparacao
    getattr(repo, 'gravar_' + tipo)(objeto, credencial=h.c.gestor)
    path, recibo = repo._paths(tipo, objeto.id)
    r = json.loads(recibo.read_bytes()); r['sha256'] = '9' * 64; recibo.write_bytes(bytes_canonicos(r))
    with pytest.raises(ErroAplicacao, match='ASSINATURA_DE_AUTORIDADE_INVALIDA'):
        getattr(repo, 'carregar_' + tipo)(objeto.id)


def test_pacote_11_preserva_bloqueios_e_replay_sem_mudar_financeiro(historico):
    h = historico; c = h.c
    antes = hash_modelo(c.pacote.entrada.lote)
    c.armazenamento.gravar_pacote(h.pacote, credencial=c.gestor)
    assert c.armazenamento.carregar_pacote(h.pacote.id) == h.pacote
    e = c.servico.executar(id_='simulacao_reconciliada', pacote_id=h.pacote.id, solicitacao=c.solicitacao,
        em='2026-10-21T13:00:00Z', fundamento='Apenas sintético', evidencia_id='teste', credencial=c.gestor)
    assert e.relatorio.boletos[0].situacao == 'bloqueado'
    assert {r.id_interno for r in h.rec.registros} <= {o.id for o in e.relatorio.ocorrencias_anteriores}
    assert c.servico.reproduzir(e.id).relatorio == e.relatorio
    assert hash_modelo(h.candidato.entrada.lote) == antes


def test_pacote_10_sem_migracao_automatica_e_sem_regravacao(historico):
    c = historico.c; repo = c.armazenamento
    repo.gravar_pacote(c.pacote, credencial=c.gestor)
    path, recibo = repo._paths('pacote', c.pacote.id)
    originais = (path.read_bytes(), recibo.read_bytes(), hash_modelo(c.pacote))
    copia = repo.carregar_pacote(c.pacote.id)
    assert copia.schema_version == '1.0' and not hasattr(copia, 'reconciliacao')
    assert (path.read_bytes(), recibo.read_bytes(), hash_modelo(copia)) == originais


@pytest.mark.parametrize('alvo', ['mapa', 'entrada', 'inventario', 'fontes'])
def test_pacote_11_com_informacao_omitida_permanece_bloqueado(historico, alvo):
    h = historico; pacote = h.pacote
    if alvo == 'mapa':
        rec = h.rec.model_copy(update={'registros': h.rec.registros[1:]})
        pacote = pacote.model_copy(update={'reconciliacao': rec})
    elif alvo == 'entrada':
        entrada = pacote.entrada.model_copy(update={'ocorrencias_anteriores': pacote.entrada.ocorrencias_anteriores[1:]})
        pacote = pacote.model_copy(update={'entrada': entrada})
    elif alvo == 'inventario':
        pacote = pacote.model_copy(update={'inventario': pacote.inventario.model_copy(update={'reconciliacao_hash': '0' * 64})})
    else:
        pacote = pacote.model_copy(update={'fontes': pacote.fontes[:-1]})
    with pytest.raises(ErroAplicacao):
        h.c.armazenamento.gravar_pacote(pacote, credencial=h.c.gestor)


def test_contratos_11_nao_podem_ser_lidos_como_10(historico):
    from conversor.domain.private_simulation import PacotePrivado
    with pytest.raises(ValidationError):
        PacotePrivado.model_validate(historico.pacote.model_dump())
    assert main(['--check']) == 0


def test_versao_do_produtor_separa_importacoes_sem_modificar_legado(historico):
    h = historico
    f = next(f for f in h.fontes if f.namespace == 'operacional')
    outra = f.model_copy(update={'produtor_versao': '2.0'})
    a = reconstruir_reconciliacao(id_='a', condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=(f,))
    b = reconstruir_reconciliacao(id_='b', condominio_id=h.rec.condominio_id, ambiente='sintetico', fontes=(outra,))
    assert a.registros[0].original == b.registros[0].original
    assert a.registros[0].id_interno != b.registros[0].id_interno


def test_estrutura_historica_nao_suportada_e_recusada(historico):
    fonte = historico.fontes[0].model_copy(update={'estrutura': 'texto_livre'})
    with pytest.raises(ErroAplicacao, match='HISTORICO_DE_OCORRENCIAS_INVALIDO'):
        reconstruir_reconciliacao(id_='invalida', condominio_id=historico.rec.condominio_id, ambiente='sintetico', fontes=(fonte,))


def test_reprocessar_historico_assinado_nao_regrava_ou_migra_arquivo(historico):
    h = historico; repo = h.c.armazenamento
    repo.gravar_reconciliacao(h.rec, credencial=h.c.gestor)
    path, recibo = repo._paths('reconciliacao', h.rec.id)
    antes = path.read_bytes(), recibo.read_bytes()
    repeticao = reconstruir_reconciliacao(id_=h.rec.id, condominio_id=h.rec.condominio_id, ambiente=h.rec.ambiente, fontes=h.fontes)
    assert repeticao == repo.carregar_reconciliacao(h.rec.id)
    assert (path.read_bytes(), recibo.read_bytes()) == antes
