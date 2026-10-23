import pytest

from conversor.application.documents import id_documental_legado, ocorrencias_documentais
from conversor.domain.canonical import Documento, EvidenciaDocumento


def copia_conflitante(pessoa, origem, *, valor='00000000272', linha=2):
    fontes = (EvidenciaDocumento(documento=Documento(tipo='cpf', valor='00000000191'), origem=origem, titular_id=pessoa.id),
              EvidenciaDocumento(documento=Documento(tipo='cpf', valor=valor),
                  origem=origem.model_copy(update={'linha': linha, 'identificador': f'celula_{linha}'}), titular_id=pessoa.id))
    return pessoa.model_copy(update={'evidencias_documentais': fontes})


def test_causa_legada_reproduzida_e_versao_nova_separa_evidencias(pessoa, origem):
    a = copia_conflitante(pessoa, origem, linha=2)
    b = copia_conflitante(pessoa, origem, linha=3)
    oa = ocorrencias_documentais(a, processamento_id='mesmo_processamento')[0]
    ob = ocorrencias_documentais(b, processamento_id='mesmo_processamento')[0]
    assert oa.codigo == ob.codigo == 'DOCUMENTOS_CONFLITANTES'
    assert id_documental_legado(processamento_id=oa.processamento_id, unidade_id=a.unidade_id, codigo=oa.codigo) == id_documental_legado(
        processamento_id=ob.processamento_id, unidade_id=b.unidade_id, codigo=ob.codigo)
    assert oa.id != ob.id and oa.id.startswith('documento:v2:')
    assert oa.evidencias_documentais == a.evidencias_documentais
    assert ob.evidencias_documentais == b.evidencias_documentais
    assert oa.gravidade == ob.gravidade == 'critico'


def test_reprocessamento_documental_identico_e_deterministico(pessoa, origem):
    p = copia_conflitante(pessoa, origem)
    assert ocorrencias_documentais(p, processamento_id='fixo') == ocorrencias_documentais(p, processamento_id='fixo')


@pytest.mark.parametrize('campo', ['pessoa', 'unidade', 'processamento', 'valor', 'fonte_hash', 'versao', 'origem_primaria'])
def test_identidade_v2_sensivel_a_pessoa_conteudo_e_proveniencia(pessoa, origem, campo):
    a = copia_conflitante(pessoa, origem)
    b = a
    processo = 'fixo'
    if campo == 'pessoa':
        b = a.model_copy(update={'id': 'outro_titular'})
    elif campo == 'unidade':
        b = a.model_copy(update={'unidade_id': 'outra_unidade'})
    elif campo == 'processamento':
        processo = 'outro'
    elif campo == 'valor':
        b = copia_conflitante(pessoa, origem, valor='00000000353')
    elif campo == 'origem_primaria':
        b = a.model_copy(update={'origem': origem.model_copy(update={'linha': 20})})
    else:
        evidencia = a.evidencias_documentais[1]
        mod = {'sha256': '9' * 64} if campo == 'fonte_hash' else {'leitor_versao': 'outra_versao'}
        evidencia = evidencia.model_copy(update={'origem': evidencia.origem.model_copy(update=mod)})
        b = a.model_copy(update={'evidencias_documentais': (a.evidencias_documentais[0], evidencia)})
    oa = next(o for o in ocorrencias_documentais(a, processamento_id='fixo') if o.codigo == 'DOCUMENTOS_CONFLITANTES')
    ob = next(o for o in ocorrencias_documentais(b, processamento_id=processo) if o.codigo == 'DOCUMENTOS_CONFLITANTES')
    assert oa.id != ob.id
    assert (oa.codigo, oa.gravidade, oa.escopo) == (ob.codigo, ob.gravidade, ob.escopo)


def test_serializacao_canonica_elimina_ambiguidade_de_separador(pessoa):
    a = pessoa.model_copy(update={'unidade_id': 'b:c'})
    b = pessoa.model_copy(update={'unidade_id': 'c'})
    oa = ocorrencias_documentais(a, processamento_id='a')[0]
    ob = ocorrencias_documentais(b, processamento_id='a:b')[0]
    assert id_documental_legado(processamento_id='a', unidade_id='b:c', codigo=oa.codigo) == id_documental_legado(
        processamento_id='a:b', unidade_id='c', codigo=ob.codigo)
    assert oa.id != ob.id
