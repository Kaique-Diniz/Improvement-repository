from hashlib import sha256

import pytest
from pydantic import ValidationError

from conversor.application.billing_evaluation import normalizar_entrada
from conversor.application.ports import ErroAplicacao
from conversor.application.simulation_inventory import conferir_pacote, inventariar, consolidar_ocorrencias_externas
from conversor.domain.billing_evaluation import EntradaSimulacao
from conversor.domain.canonical import Apontamento, LoteCanonico, Ocorrencia
from conversor.domain.private_simulation import PacotePrivado


def critico(origem, *, codigo='SUBTOTAL_FONTE_INCONSISTENTE', escopo='arquivo', registro_id=None, id_='critico_sintetico'):
    return Ocorrencia(id=id_, processamento_id='revisao_anterior', codigo=codigo, gravidade='critico',
                     escopo=escopo, registro_id=registro_id, origem=origem)


def test_inventario_completo_com_campos_ausentes_e_origens(laboratorio, unidade, boleto, pessoa, origem):
    boleto = boleto.model_copy(update={'competencia': None, 'apontamentos': (Apontamento(codigo_original='X', namespace_formato='sintetico', origem=origem),)})
    c = laboratorio(lote=LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,)))
    conferir_pacote(c.pacote)
    inventario = c.pacote.inventario
    assert inventario.apontamentos == 1 and inventario.itens_composicao == 2
    assert ('boleto_a', 'competencia') in {(a.registro_id, a.campo) for a in inventario.campos_ausentes}
    assert ('pessoa_sintetica', 'documento') in {(a.registro_id, a.campo) for a in inventario.campos_ausentes}
    assert all(o.leitor_versao and o.identificador and o.sha256 for o in inventario.origens)
    assert c.pacote.entrada.lote.boletos[0].competencia is None


@pytest.mark.parametrize('colecao', ['unidades', 'boletos', 'pessoas'])
def test_omissao_de_entidade_nao_passa_por_inventario(laboratorio, colecao):
    c = laboratorio()
    dados = c.pacote.model_dump(mode='json')
    # Trocar uma identidade conserva a quantidade, mas o inventário ainda detecta a substituição.
    if colecao == 'boletos':
        dados['entrada']['lote'][colecao][0]['id'] = 'boleto_substituido'
    elif colecao == 'pessoas':
        dados['entrada']['lote'][colecao] = []
    else:
        dados['entrada']['lote']['unidades'][0]['unidade_original'] = 'outra_unidade'
    pacote = PacotePrivado.model_validate(dados)
    with pytest.raises(ErroAplicacao, match='INVENTARIO_INCOMPLETO'):
        conferir_pacote(pacote)


@pytest.mark.parametrize('campo', ['fatos', 'ocorrencias_anteriores', 'coberturas_apontamentos'])
def test_colecoes_explicitas_obrigatorias(laboratorio, campo):
    c = laboratorio()
    dados = c.pacote.model_dump(mode='json'); del dados['entrada'][campo]
    with pytest.raises(ValidationError):
        PacotePrivado.model_validate(dados)


@pytest.mark.parametrize('categoria', ['leitura', 'auditoria_lote', 'titularidade', 'documentos'])
def test_catalogo_ausente_nao_vira_lista_vazia(laboratorio, categoria):
    c = laboratorio()
    dados = c.pacote.model_dump(mode='json')
    dados['catalogos'] = [x for x in dados['catalogos'] if x['categoria'] != categoria]
    with pytest.raises(ValidationError):
        PacotePrivado.model_validate(dados)


@pytest.mark.parametrize('lado', ['entrada', 'catalogo'])
def test_carga_parcial_de_bloqueios_recusada_mesmo_com_novo_hash_inventario(laboratorio, origem, lado):
    c = laboratorio(ocorrencias=(critico(origem),))
    entrada = c.pacote.entrada
    catalogos = c.pacote.catalogos
    if lado == 'entrada':
        entrada = entrada.model_copy(update={'ocorrencias_anteriores': ()})
    else:
        catalogos = (catalogos[0].model_copy(update={'ocorrencias': ()}), *catalogos[1:])
    pacote = c.pacote.model_copy(update={'entrada': entrada, 'catalogos': catalogos, 'inventario': inventariar(entrada, catalogos)})
    with pytest.raises(ErroAplicacao, match='OCORRENCIAS_EXTERNAS_AUSENTES_OU_PARCIAIS'):
        c.armazenamento.gravar_pacote(pacote, credencial=c.gestor)


def test_bloqueio_externo_sem_evidencia_nao_e_atestavel(laboratorio, origem):
    c = laboratorio(ocorrencias=(critico(origem).model_copy(update={'origem': None}),))
    with pytest.raises(ErroAplicacao, match='BLOQUEIO_EXTERNO_SEM_FONTE'):
        c.armazenamento.gravar_pacote(c.pacote, credencial=c.gestor)


def test_catalogo_de_outro_condominio_ou_duplicado_recusado(laboratorio):
    c = laboratorio()
    dados = c.pacote.model_dump(mode='json')
    dados['catalogos'][0]['condominio_id'] = 'outro'
    with pytest.raises(ValidationError):
        PacotePrivado.model_validate(dados)
    dados = c.pacote.model_dump(mode='json'); dados['catalogos'][0]['categoria'] = 'documentos'
    with pytest.raises(ValidationError):
        PacotePrivado.model_validate(dados)


@pytest.mark.parametrize('alteracao', ['fonte_ausente', 'hash_divergente', 'arquivo_modificado', 'arquivo_parcial'])
def test_origens_e_fontes_sempre_conferidas(laboratorio, alteracao):
    c = laboratorio()
    pacote = c.pacote
    if alteracao == 'fonte_ausente':
        pacote = pacote.model_copy(update={'fontes': pacote.fontes[1:]})
    elif alteracao == 'hash_divergente':
        pacote = pacote.model_copy(update={'fontes': (pacote.fontes[0].model_copy(update={'sha256': '9' * 64}), *pacote.fontes[1:])})
    elif alteracao == 'arquivo_modificado':
        c.primaria.write_bytes(b'Outra fonte com conteudo diferente')
    else:
        c.primaria.write_bytes(c.primaria.read_bytes()[:10])
    with pytest.raises(ErroAplicacao, match='ORIGEM_SEM_FONTE|FONTE_PRIVADA_ALTERADA'):
        c.armazenamento.gravar_pacote(pacote, credencial=c.gestor)


def test_nem_ausencias_nem_criticidade_podem_ser_editadas_no_inventario(laboratorio, origem):
    c = laboratorio(ocorrencias=(critico(origem),))
    adulterado = c.pacote.model_copy(update={'inventario': c.pacote.inventario.model_copy(update={'campos_ausentes': ()})})
    with pytest.raises(ErroAplicacao, match='INVENTARIO_INCOMPLETO'):
        conferir_pacote(adulterado)


def test_mesmo_id_com_evidencias_documentais_distintas_recusa_preparacao(origem):
    from conversor.domain.canonical import Documento, EvidenciaDocumento
    a = critico(origem, codigo='DOCUMENTOS_CONFLITANTES')
    evidencia = EvidenciaDocumento(documento=Documento(tipo='cpf', valor='00000000191'), origem=origem, titular_id='pessoa_sintetica')
    b = a.model_copy(update={'evidencias_documentais': (evidencia,)})
    with pytest.raises(ErroAplicacao, match='IDENTIDADE_DE_OCORRENCIA_EXTERNA_CONFLITANTE'):
        consolidar_ocorrencias_externas(((a,), (b,)))
    assert a.evidencias_documentais == () and b.evidencias_documentais == (evidencia,)


def test_repeticao_externa_exatamente_igual_e_idempotente(origem):
    o = critico(origem)
    assert consolidar_ocorrencias_externas(((o,), (o,))) == (o,)


@pytest.mark.parametrize('caso', ['fato_condominio', 'fato_unidade', 'fato_boleto', 'cobertura'])
def test_completude_rejeita_referencias_externas_na_preparacao(laboratorio, caso):
    from tests.evaluation.conftest import fato
    from conversor.domain.billing_evaluation import CoberturaApontamentos
    c = laboratorio()
    entrada = c.pacote.entrada
    if caso == 'cobertura':
        entrada = entrada.model_copy(update={'coberturas_apontamentos': (
            CoberturaApontamentos(boleto_id='inexistente', namespace='sintetico', origens=(entrada.lote.unidades[0].origem,)),)})
    else:
        campo = {'fato_condominio': 'condominio_id', 'fato_unidade': 'unidade_id', 'fato_boleto': 'boleto_id'}[caso]
        entrada = entrada.model_copy(update={'fatos': (fato().model_copy(update={campo: 'inexistente'}),)})
    entrada = normalizar_entrada(entrada)
    pacote = c.pacote.model_copy(update={'entrada': entrada, 'inventario': inventariar(entrada, c.pacote.catalogos)})
    with pytest.raises(ErroAplicacao, match='FATO_FORA_|COBERTURA_FORA_'):
        conferir_pacote(pacote)
