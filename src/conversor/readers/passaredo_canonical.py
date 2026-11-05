"""Adaptação Passaredo ao canônico; sem seleção, atualização ou cobrança."""
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
import json

from conversor.domain.canonical import (
    Boleto, Composicao, EvidenciaDocumento, ItemComposicao, LoteCanonico,
    Origem, Pessoa, RessalvaLeitura, Unidade,
)
from .passaredo_cadastro import LeitorPassaredoCadastro
from .passaredo_inadimplencia import LeitorPassaredoInadimplencia
from .text_support import ErroLeitura, id_estavel


def origem(digest, contexto, linha, coluna='A'):
    return Origem(arquivo_id=contexto.arquivo_id, sha256=digest,
        leitor_versao=contexto.leitor_versao, linha=linha,
        identificador=f'Sheet1_{coluna}{linha}')


def unidade(numero, contexto, fonte):
    # Não há bloco na fonte. Não presumir bloco 0 nem remover zeros da unidade.
    return Unidade(id=id_estavel('unidade_passaredo', contexto.condominio_id, numero),
        condominio_id=contexto.condominio_id, administradora_id=contexto.administradora_id,
        bloco_original='', unidade_original=numero, chave_normalizada=numero,
        normalizador_versao='unidade_textual_passaredo@1', origem=fonte)


def ler_financeiro(conteudo, *, contexto):
    registros = LeitorPassaredoInadimplencia().ler(conteudo)
    digest = sha256(conteudo).hexdigest()
    unidades, representantes, boletos, ressalvas = {}, {}, [], []
    nomes = defaultdict(set)
    repeticoes = Counter()
    for registro in registros:
        fonte = origem(digest, contexto, registro.linha)
        u = unidades.setdefault(registro.unidade, unidade(registro.unidade, contexto, fonte))
        nomes[u.id].add(registro.responsavel)
        # O representante estrutural não é atribuído a todos os lançamentos.
        # Cada lançamento conserva abaixo seu próprio responsável da fonte.
        representantes.setdefault(u.id, Pessoa(id=id_estavel('pessoa_passaredo', u.id, registro.responsavel),
            unidade_id=u.id, nome=registro.responsavel,
            relacao_unidade='responsavel_representativo_da_fonte', origem=fonte))
        chave = (u.id, registro.responsavel, registro.descricao, registro.vencimento, registro.valor)
        repeticoes[chave] += 1
        identificador = id_estavel('lancamento_passaredo', *chave, repeticoes[chave])
        b = Boleto(id=identificador, identificador=identificador,
            condominio_id=contexto.condominio_id, unidade_id=u.id,
            vencimento=registro.vencimento,
            composicao=Composicao(total_original=registro.valor, itens=(ItemComposicao(
                codigo='original', valor=registro.valor, descricao_original=registro.descricao,
                origem=origem(digest, contexto, registro.linha, 'F')),)),
            juros=registro.juros, multa=registro.multa, correcao=registro.correcao,
            origens=(fonte,))
        boletos.append(b)
        ressalvas.append(RessalvaLeitura(codigo='PASSAREDO_LANCAMENTO_ORIGINAL',
            gravidade='informativo', registro_id=b.id, origens=(fonte,),
            valores_originais=(json.dumps(asdict(registro), ensure_ascii=False, default=str),)))
    for uid, valores in nomes.items():
        if len(valores) > 1:
            ressalvas.append(RessalvaLeitura(codigo='PASSAREDO_RESPONSAVEIS_DISTINTOS_NA_UNIDADE',
                registro_id=uid, origens=(representantes[uid].origem,),
                valores_originais=tuple(sorted(valores))))
    return LoteCanonico(unidades=tuple(unidades.values()), pessoas=tuple(representantes.values()),
        boletos=tuple(boletos), ressalvas=tuple(ressalvas))


def ler_cadastro(conteudo, *, contexto):
    registros = LeitorPassaredoCadastro().ler(conteudo)
    digest = sha256(conteudo).hexdigest()
    unidades, pessoas, ressalvas = [], [], []
    for registro in registros:
        fonte = origem(digest, contexto, registro.linha)
        u = unidade(registro.unidade, contexto, fonte)
        uid = id_estavel('pessoa_cadastro_passaredo', u.id, registro.responsavel)
        evidencias = tuple(EvidenciaDocumento(documento=doc, titular_id=uid,
            origem=origem(digest, contexto, registro.linha, coluna))
            for doc, coluna in zip(registro.documentos, registro.documentos_colunas))
        pessoas.append(Pessoa(id=uid, unidade_id=u.id, nome=registro.responsavel,
            documento=registro.documento, documento_origem=evidencias[0].origem if evidencias else None,
            evidencias_documentais=evidencias, contato=registro.contato,
            relacao_unidade='responsavel_informado_no_cadastro', origem=fonte))
        unidades.append(u)
        ressalvas.append(RessalvaLeitura(codigo='PASSAREDO_CADASTRO_ORIGINAL',
            gravidade='informativo', registro_id=u.id, origens=(fonte,),
            valores_originais=(registro.valores_originais,)))
        if registro.telefones_excedentes or registro.emails_excedentes:
            ressalvas.append(RessalvaLeitura(codigo='PASSAREDO_CONTATOS_EXCEDENTES_PRESERVADOS',
                registro_id=u.id, origens=(fonte,), valores_originais=(registro.valores_originais,)))
    return LoteCanonico(unidades=tuple(unidades), pessoas=tuple(pessoas), boletos=(),
        ressalvas=tuple(ressalvas))


def lancamentos_originais(lote):
    registros = {r.registro_id: json.loads(r.valores_originais[0]) for r in lote.ressalvas
                 if r.codigo == 'PASSAREDO_LANCAMENTO_ORIGINAL'}
    if set(registros) != {b.id for b in lote.boletos}:
        raise ErroLeitura('PASSAREDO_PROVENIENCIA_INCOMPLETA')
    return registros
