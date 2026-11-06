"""Escolha nominal de participante Vero, com as proteções fiscais A1."""
from collections import Counter, defaultdict

from conversor.domain.canonical import EvidenciaDocumento, RessalvaLeitura
from conversor.domain.documents import evidencias_documento, resolver_documento
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.text_support import ErroLeitura
from .passaredo_cadastro import responsabilidade_multipla_sem_vinculo_empresarial

POLITICA = 'vero_participante_nominal_documento_valido_A1@1'


def associar(lote, cadastro=None):
    groups = defaultdict(list)
    if cadastro is not None:
        if cadastro.boletos or any((u.administradora_id,u.condominio_id) != ('lello_2','condominio_vero_encanto') for u in cadastro.unidades):
            raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
        for p in cadastro.pessoas:
            groups[p.unidade_id].append(p)
    units = {u.id:u for u in lote.unidades}
    owners = {p.unidade_id:p for p in lote.pessoas}
    cadastral_units = {u.id:u for u in cadastro.unidades} if cadastro else {}
    invalid = {r.registro_id for r in cadastro.ressalvas if r.codigo == 'VERO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO'} if cadastro else set()
    people, details, notes, stats = {}, {}, list(lote.ressalvas), Counter()
    for bill in lote.boletos:
        unit, original = units[bill.unidade_id], owners[bill.unidade_id]
        person = original
        candidates = groups[unit.id]
        reason = None
        if not candidates:
            stats['lancamentos_sem_cadastro'] += 1
            if cadastro is not None:
                reason = 'VERO_CADASTRO_AUSENTE_ASSOCIACAO_RETIDA'
        else:
            cu = cadastral_units[unit.id]
            if (unit.bloco_original,unit.unidade_original) != (cu.bloco_original,cu.unidade_original):
                raise ErroLeitura('VERO_IDENTIDADE_CADASTRAL_DIVERGENTE')
            matches = [p for p in candidates if normalizar_assinatura(p.nome) == normalizar_assinatura(original.nome)]
            if not matches:
                reason = 'VERO_RESPONSAVEL_DIVERGENTE_CADASTRO'
            elif len(matches) != 1:
                reason = 'VERO_PARTICIPANTES_AMBIGUOS_ASSOCIACAO_RETIDA'
            else:
                selected = matches[0]
                evidence = evidencias_documento(selected)
                document = resolver_documento(selected)
                compartilhado_com_outro_nome = bool(document.valor) and any(
                    other.id != selected.id and normalizar_assinatura(other.nome) != normalizar_assinatura(selected.nome)
                    and resolver_documento(other).valor == document.valor for other in candidates)
                if responsabilidade_multipla_sem_vinculo_empresarial(original.nome,evidence):
                    reason = 'VERO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO'
                elif document.bloqueante or (selected.id in invalid and document.valor) or compartilhado_com_outro_nome:
                    reason = 'VERO_DOCUMENTOS_CONFLITANTES_CADASTRO'
                elif not document.valor:
                    reason = 'VERO_DOCUMENTO_INVALIDO_ASSOCIACAO_RETIDA' if selected.id in invalid else 'VERO_DOCUMENTO_AUSENTE_ASSOCIACAO_RETIDA'
                else:
                    person = original.model_copy(update={'documento':selected.documento,
                        'documento_origem':selected.documento_origem,
                        'evidencias_documentais':tuple(EvidenciaDocumento(documento=e.documento,
                            origem=e.origem,titular_id=original.id) for e in evidence),
                        'contato':selected.contato})
                    stats['associacoes_concordantes'] += 1
                    stats['documentos_validos_vinculados'] += 1
        if reason:
            stats['associacoes_retidas'] += 1
            stats[reason] += 1
            notes.append(RessalvaLeitura(codigo=reason,registro_id=bill.id,
                origens=(original.origem,)+tuple(p.origem for p in candidates)))
            key = (unit.id,original.nome,reason)
            entry = details.setdefault(key,{'unidade':unit.unidade_original,
                'responsavel_inadimplencia':original.nome, 'responsavel_cadastro':' / '.join(p.nome for p in candidates),
                'motivo':reason,'lancamentos':0})
            entry['lancamentos'] += 1
        people[bill.id] = person
    summary = {k:stats[k] for k in ('lancamentos_sem_cadastro','associacoes_concordantes','documentos_validos_vinculados','associacoes_retidas')}
    summary.update(politica=POLITICA,fornecido=cadastro is not None,nomes_financeiros_preservados=True,
        unidades_em_revisao=len({key[0] for key in details}),
        documentos_rejeitados_no_cadastro=sum(len(r.valores_originais) for r in cadastro.ressalvas
            if r.codigo == 'VERO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO') if cadastro else 0,
        retencoes_por_motivo={k:v for k,v in stats.items() if k.startswith('VERO_')},
        participacao_percentual_nao_define_titular=True)
    return lote.model_copy(update={'ressalvas':tuple(notes)}), people, summary, list(details.values())
