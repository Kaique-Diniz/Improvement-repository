"""Presença, vazio comprovado e inconclusão; PDFs criados do zero, sem fontes reais."""
from hashlib import sha256

import pytest
from pydantic import ValidationError

from conversor.domain.canonical import LoteCanonico, ResultadoCobranca
from conversor.readers.habita_point_coverage import (
    CampoApontamentoConferido, conferir_apontamentos_habita, conferir_posicao,
)
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from examples.fase3.layouts_sinteticos import pdf_posicionado
from tests.phase3.test_habita_rule_mapping import FORMATO, VERSAO, ler


def fragmentos(codigo=None):
    f = [('Boleto', 31, 750), ('Vencimento', 100, 750), ('Emissão', 150, 750), ('Valor', 560, 750),
         ('Multa', 620, 750), ('Juros', 747, 750), ('Total', 810, 750),
         ('91000001', 31, 715), ('01/10/26', 100, 715),
         ('DESCRICAO A AJ J', 260, 715), ('A', 31, 40), ('AJ', 120, 40), ('J', 190, 40)]
    if codigo is not None:
        f.append((codigo, 75, 715))
    return f


def pdf_campo(codigo=None, *, continuar=False, codigo_segunda=None, sem_ancora=False):
    paginas = []
    for i in range(2 if continuar else 1):
        f = [('Inadimplência Atualizada', 31, 820), ('Condominio: 9999 - SINTETICO', 31, 800),
             ('Bloco: SINT • Unidade: 000001 TITULAR SINTETICO CPF: (vazio)', 31, 780)]
        f += fragmentos(codigo if i == 0 or codigo_segunda is None else codigo_segunda)
        f += [('Atualização', 665, 755), ('Monetária', 669, 745),
              ('010926', 150, 715), ('94', 210, 715),
              ('10,00 0,00 0,00 0,00 10,00', 560, 715)]
        if sem_ancora:
            f = [t for t in f if t[0] != 'Boleto']
        if not continuar or i == 1:
            total = '20,00' if continuar else '10,00'
            if continuar:
                f.append((f'Total do boleto: {total} 0,00 0,00 0,00 {total}', 31, 680))
            f.extend([(f'Total da Unidade: {total} 0,00 0,00 0,00 {total}', 31, 660),
                      (f'Quantidade de unidades inadimplentes no condominio: 1 Total Geral: {total} 0,00 0,00 0,00 {total}', 31, 640)])
        paginas.append([(x, y, text + ' ') for text, x, y in sorted(f, key=lambda t: (-t[2], t[1]))])
    return pdf_posicionado(paginas)


def contexto():
    return ContextoLeitura('cond_sintetico_mapeamento', 'adm_sintetica', FORMATO,
                          'pdf_inventado_mapeamento', '9999', leitor_versao=VERSAO)


def conferir(blob, lote=None):
    return conferir_apontamentos_habita(blob, contexto=contexto(), lote=lote or ler(blob))


@pytest.mark.parametrize('codigo,estado', [(None, 'vazio_validado'), ('A', 'preenchido_validado'),
                                         ('AJ', 'preenchido_validado'), ('J', 'preenchido_validado')])
def test_posicao_comprovada_ignora_codigos_da_legenda_e_descricao(codigo, estado):
    r = conferir_posicao(fragmentos(codigo), numero='91000001', vencimento='01/10/26')
    assert r[:2] == (estado, codigo)


@pytest.mark.parametrize('caso', ['codigo_desconhecido', 'codigo_parcial', 'dois_codigos', 'sem_rotulo',
                                 'sem_total', 'sem_data', 'duas_linhas', 'duas_ancoras'])
def test_falta_ou_ambiguidade_nao_comprova_ausencia(caso):
    f = fragmentos()
    if caso == 'codigo_desconhecido':f.append(('X', 75, 715))
    if caso == 'codigo_parcial':f.append(('A?', 75, 715))
    if caso == 'dois_codigos':f.extend([('A', 70, 715), ('J', 80, 715)])
    if caso == 'sem_rotulo':f = [r for r in f if r[0] != 'Boleto']
    if caso == 'sem_total':f = [r for r in f if r[0] != 'Total']
    if caso == 'sem_data':f = [r for r in f if r[0] != '01/10/26']
    if caso == 'duas_linhas':f.extend([('91000001', 31, 700), ('01/10/26', 100, 700)])
    if caso == 'duas_ancoras':f.extend([(t, x, y-10) for t, x, y in f if y == 750])
    assert conferir_posicao(f, numero='91000001', vencimento='01/10/26')[:2] == ('inconclusivo', None)


@pytest.mark.parametrize('codigo', [None, 'A', 'AJ', 'J'])
@pytest.mark.parametrize('continuar', [False, True])
def test_pdf_completo_confere_todos_cabecalhos_sem_criar_atesto(codigo, continuar):
    blob = pdf_campo(codigo, continuar=continuar)
    lote = ler(blob)
    r = conferir(blob, lote)
    assert len(r.campos) == len(lote.boletos) == 1
    campo = r.campos[0]
    assert campo.estado == ('preenchido_validado' if codigo else 'vazio_validado')
    assert campo.codigo == codigo and campo.namespace == FORMATO
    assert len(campo.origens) == (2 if continuar else 1)
    assert {o.pagina for o in campo.origens} == ({1, 2} if continuar else {1})
    assert all(o.sha256 == sha256(blob).hexdigest() for o in campo.origens)
    assert not r.atesto_humano and not r.autoriza_exportacao_divida
    assert not r.ocorrencias_revisao(processamento_id='conferencia_sintetica')
    assert conferir(blob, lote) == r


def test_geometria_ausente_nao_valida_vazio_e_gera_critico_por_boleto():
    blob = pdf_campo(sem_ancora=True)
    lote = ler(blob)
    r = conferir(blob, lote)
    assert r.campos[0].estado == 'inconclusivo' and r.campos[0].codigo is None
    ocorrencias = r.ocorrencias_revisao(processamento_id='conferencia_sintetica')
    assert len(ocorrencias) == 1 and ocorrencias[0].bloqueante
    assert ocorrencias[0].registro_id == lote.boletos[0].id
    assert ocorrencias[0].escopo == 'registro'
    with pytest.raises(ValidationError, match='RESULTADO_COM_BLOQUEIO_NAO_PODE_INCLUIR'):
        ResultadoCobranca(processamento_id='conferencia_sintetica', unidade_id=lote.unidades[0].id,
                         boleto_id=lote.boletos[0].id, acao='incluir', regra_id='sintetica',
                         regra_versao='teste', motivo_codigo='NAO_AUTORIZADO',
                         origens=lote.boletos[0].origens, ocorrencias=ocorrencias)


def test_continuacao_divergente_evidencias_preservadas_sem_escolha():
    baseline = ler(pdf_campo('A', continuar=True))
    blob = pdf_campo('A', continuar=True, codigo_segunda='J')
    # Entrada sintética adulterada que tenta preservar o canônico anterior.
    # Mesmo que o atacante atualize os hashes declarados, as linhas discordam.
    dados = baseline.model_dump(mode='json')
    def atualizar_hash(valor):
        if isinstance(valor, dict):
            if 'sha256' in valor:valor['sha256'] = sha256(blob).hexdigest()
            for filho in valor.values():atualizar_hash(filho)
        elif isinstance(valor, list):
            for filho in valor:atualizar_hash(filho)
    atualizar_hash(dados)
    lote = LoteCanonico.model_validate(dados)
    r = conferir(blob, lote)
    assert r.campos[0].estado == 'inconclusivo'
    assert len(r.campos[0].origens) == 2
    assert r.ocorrencias_revisao(processamento_id='divergencia_sintetica')[0].bloqueante


def test_hash_arquivo_divergente_nao_e_cobertura():
    lote = ler(pdf_campo())
    with pytest.raises(ErroLeitura, match='FONTE_COBERTURA_DIVERGENTE'):
        conferir(pdf_campo('A'), lote)


def test_namespace_canonico_divergente_exige_revisao():
    blob = pdf_campo('A')
    dados = ler(blob).model_dump(mode='json')
    dados['boletos'][0]['apontamentos'][0]['namespace_formato'] = 'outro_namespace'
    r = conferir(blob, LoteCanonico.model_validate(dados))
    assert r.campos[0].estado == 'inconclusivo'


def test_modelo_nao_aceita_preenchido_sem_codigo_ou_codigo_em_vazio():
    c = conferir(pdf_campo()).campos[0].model_dump()
    with pytest.raises(ValidationError, match='ESTADO_CAMPO_INCOERENTE'):
        CampoApontamentoConferido.model_validate(c | {'estado': 'preenchido_validado'})
    with pytest.raises(ValidationError, match='ESTADO_CAMPO_INCOERENTE'):
        CampoApontamentoConferido.model_validate(c | {'codigo': 'A'})


def test_data_pode_estar_recuada_dentro_da_coluna_sem_perder_cobertura():
    f = [(t, 108.28 if t == '01/10/26' else x, y) for t, x, y in fragmentos()]
    assert conferir_posicao(f, numero='91000001', vencimento='01/10/26')[:2] == ('vazio_validado', None)


def test_lote_sem_boleto_nao_oculta_cabecalho_existente_na_fonte():
    blob = pdf_campo()
    lote = ler(blob)
    incompleto = LoteCanonico.model_validate(lote.model_dump() | {'boletos': ()})
    with pytest.raises(ErroLeitura, match='INVENTARIO_COBERTURA_DIVERGENTE'):
        conferir(blob, incompleto)


def test_campo_preenchido_nao_pode_ser_apagado_silenciosamente_do_canonico():
    blob = pdf_campo('AJ')
    dados = ler(blob).model_dump(mode='json')
    dados['boletos'][0]['apontamentos'] = []
    r = conferir(blob, LoteCanonico.model_validate(dados))
    assert r.campos[0].estado == 'inconclusivo'
    assert r.ocorrencias_revisao(processamento_id='omissao_sintetica')[0].bloqueante
