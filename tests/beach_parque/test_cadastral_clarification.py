"""Lacunas da revisão BPQ: marcador real de cabeçalho e documento de outro papel.

Todos os nomes, documentos e contatos são criados para o teste. Nenhuma ficha
privada ou observação jurídica real participa destas regressões.
"""
import json

import pytest

from conversor.domain.documents import resolver_documento
from conversor.readers.passaredo_cadastro import normalizar_documento
from .fixtures import CPF, NOME, cadastro, ficha, financeiro, recibo
from .test_beach_parque import PROFILE, executar, ler_cad, rows


@pytest.mark.parametrize('modo', ['A', 'B'])
def test_litigio_no_cabecalho_e_restricoes_nao_autorizam_nem_excluem(tmp_path, modo):
    # A fonte sinaliza litígio no cabeçalho; não depende de Classificação.
    nome = NOME + ' (LITÍGIO)'
    raw = financeiro([('A', 'A00001', nome, [recibo('31', 31), recibo('30', 30)])])
    corpo = ficha(bloco='A', numero='A00001', nome=nome, documento=CPF)
    corpo.extend([(24, 110, 'Bloquear reenvio automático de boletos: Sim'),
                  (216, 110, 'Recebe carta de cobrança: Não')])
    antes = executar(tmp_path/'antes', raw, mode=modo)
    depois = executar(tmp_path/'depois', raw, cadastro([corpo]), mode=modo)
    esperados = {'BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO',
                 'BPQ_REVISAO_BLOQUEIO_REENVIO', 'BPQ_REVISAO_NAO_RECEBER_CARTA'}
    assert depois['cadastro_'+PROFILE]['restricoes_por_codigo'] == dict.fromkeys(esperados, 1)
    for resultado in (antes, depois):
        assert resultado['autoriza_cobranca'] is False
        assert resultado['permite_exportacao_operacional'] is False
        assert resultado['resumo']['dividas_efetivamente_geradas'] == 1
        assert resultado['resumo']['cadastros_adicionais'] == int(modo == 'B')
    campos_financeiros = ('id', 'valor', 'vencimento', 'situacao_financeira', 'situacao')
    assert [{k: d[k] for k in campos_financeiros} for d in antes['decisoes']] == [
        {k: d[k] for k in campos_financeiros} for d in depois['decisoes']]
    assert all(esperados <= set(d['alertas_cadastrais']) for d in depois['decisoes'])
    saida = rows(tmp_path/'depois')
    assert len(saida) == 2 + int(modo == 'B')
    assert len(saida[0]) == 30 and saida[0][26] == 'NM_DIVIDA_CEDENTE'
    assert saida[1][29] == 100.1
    canonico = json.loads((tmp_path/'depois'/'canonico.json').read_text(encoding='utf-8'))
    notas = [r for r in canonico['ressalvas'] if r['codigo'] in esperados]
    assert len(notas) == 3
    assert all(r['origens'][0]['sha256'] and not r['valores_originais'] for r in notas)


@pytest.mark.parametrize('papel', ['pagador', 'locatario'])
def test_documento_valido_exclusivo_de_outro_papel_nao_preenche_titular(tmp_path, papel):
    corpo = ficha(bloco='A', numero='A00001', nome=NOME, documento='',
                  pagador=papel == 'pagador', locatario=papel == 'locatario')
    pdf = cadastro([corpo])
    lote = ler_cad(pdf)
    evidencias = json.loads(next(r.valores_originais[0] for r in lote.ressalvas
                                if r.codigo == 'BPQ_CADASTRO_FICHA_ORIGINAL'))
    papeis = {p['papel']: p for p in evidencias['participantes']}
    assert papeis['titular']['documentos'] == []
    docs = [normalizar_documento(d['valor']) for d, origem in papeis[papel]['documentos']]
    assert docs and all(d is not None for d in docs)
    assert not resolver_documento(lote.pessoas[0]).valor
    # Nome e unidade iguais, contatos do cliente presentes, e documento de outro
    # papel válido: ainda assim nada é promovido para o titular sem documento.
    assert lote.pessoas[0].contato.emails == ('titular@example.invalid',)
    resultado = executar(tmp_path, cad=pdf)
    resumo = resultado['cadastro_'+PROFILE]
    assert resumo['associacoes_retidas'] == 1
    assert resumo['retencoes_por_motivo'] == {
        'BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA': 1}
    assert resultado['resumo']['dividas_efetivamente_geradas'] == 1
    assert resultado['autoriza_cobranca'] is False
    assert resultado['permite_exportacao_operacional'] is False
    saida = rows(tmp_path)[1]
    assert saida[2] is None
    assert all(v is None for v in saida[11:24])
    assert saida[29] == 100.1
