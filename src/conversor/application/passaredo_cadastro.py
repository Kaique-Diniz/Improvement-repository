"""Passaredo: associação por lançamento, unidade textual e nome concordante."""
from collections import Counter
import re

from conversor.domain.canonical import Pessoa, RessalvaLeitura
from conversor.domain.documents import evidencias_documento, resolver_documento
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.passaredo_canonical import lancamentos_originais
from conversor.readers.text_support import ErroLeitura, id_estavel

POLITICA = 'passaredo_nome_e_unidade_por_lancamento@1'


def associar(lote, cadastro=None):
    dados = lancamentos_originais(lote)
    unidades = {u.id: u for u in lote.unidades}
    pessoas_cad, unidades_cad = {}, {}
    ressalvas = list(lote.ressalvas)
    stats = Counter()
    revisao, detalhes = set(), {}
    if cadastro is not None:
        if cadastro.boletos:
            raise ErroLeitura('CADASTRO_NAO_PODE_CRIAR_BOLETOS')
        esperadas = {(u.administradora_id, u.condominio_id) for u in lote.unidades}
        if any((u.administradora_id, u.condominio_id) not in esperadas for u in cadastro.unidades):
            raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
        unidades_cad = {u.id: u for u in cadastro.unidades}
        pessoas_cad = {p.unidade_id: p for p in cadastro.pessoas}
        if len(pessoas_cad) != len(cadastro.pessoas):
            raise ErroLeitura('PASSAREDO_CADASTRO_AMBIGUO')
        ressalvas.extend(r for r in cadastro.ressalvas if r.registro_id in unidades)
    pessoas = {}
    for b in lote.boletos:
        u, original = unidades[b.unidade_id], dados[b.id]
        p = Pessoa(id=id_estavel('responsavel_lancamento_passaredo', u.id, original['responsavel']),
            unidade_id=u.id, nome=original['responsavel'], origem=b.origens[0],
            relacao_unidade='responsavel_informado_na_inadimplencia')
        c = pessoas_cad.get(u.id)
        codigo = None
        if c is None:
            stats['lancamentos_sem_cadastro'] += 1
        else:
            cu = unidades_cad[u.id]
            if (cu.bloco_original, cu.unidade_original) != (u.bloco_original, u.unidade_original):
                raise ErroLeitura('PASSAREDO_IDENTIDADE_CADASTRAL_DIVERGENTE')
            if not p.nome.strip() or normalizar_assinatura(p.nome) != normalizar_assinatura(c.nome):
                codigo = 'PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO'
            elif re.search(r'\s+[eE]\s+|[/;\n]', p.nome) and any(
                    e.documento.tipo == 'cpf' for e in evidencias_documento(c)):
                codigo = 'PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO'
            elif resolver_documento(c).bloqueante:
                codigo = 'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO'
            else:
                evidencias = tuple(e.model_copy(update={'titular_id': p.id}) for e in evidencias_documento(c))
                p = p.model_copy(update={'documento': c.documento, 'documento_origem': c.documento_origem,
                    'evidencias_documentais': evidencias, 'contato': c.contato})
                stats['associacoes_concordantes'] += 1
                stats['documentos_validos_vinculados'] += bool(resolver_documento(p).valor)
            if codigo:
                revisao.add(u.id)
                stats['associacoes_retidas'] += 1
                ressalvas.append(RessalvaLeitura(codigo=codigo, registro_id=b.id,
                    origens=(p.origem, c.origem), valores_originais=(p.nome, c.nome)))
                chave = (u.unidade_original, p.nome, c.nome, codigo)
                detalhe = detalhes.setdefault(chave, {'unidade': u.unidade_original,
                    'responsavel_inadimplencia': p.nome, 'responsavel_cadastro': c.nome,
                    'motivo': codigo, 'lancamentos': 0})
                detalhe['lancamentos'] += 1
        pessoas[b.id] = p
    resumo = {key: stats[key] for key in ('lancamentos_sem_cadastro', 'associacoes_concordantes',
        'documentos_validos_vinculados', 'associacoes_retidas')}
    resumo.update(politica=POLITICA, unidades_em_revisao=len(revisao),
        fornecido=cadastro is not None, nomes_financeiros_preservados=True)
    return lote.model_copy(update={'ressalvas': tuple(ressalvas)}), pessoas, resumo, list(detalhes.values())
