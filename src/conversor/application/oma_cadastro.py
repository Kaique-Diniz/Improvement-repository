"""PSM: reutiliza A1 e exige documento válido antes de transferir contatos."""
import json
from conversor.application.passaredo_cadastro import associar as associar_a1
from conversor.domain.canonical import Contato, RessalvaLeitura
from conversor.domain.documents import resolver_documento
from conversor.domain.oma import unidades_equivalentes
from conversor.readers.oma_xlsx import originais


def associar(lote, cadastro=None):
    lote, pessoas, resumo, revisao = associar_a1(lote, cadastro,
        obter_originais=originais, unidades_equivalentes=unidades_equivalentes)
    resumo['politica'] = 'oma_identidade_nominal_documento_valido_A1@1'
    if cadastro is None:
        return lote, pessoas, resumo, revisao
    temporais = tuple(r for r in cadastro.ressalvas if r.codigo == 'OMA_CADASTRO_TEMPORALIDADE')
    lote = lote.model_copy(update={'ressalvas':lote.ressalvas + temporais})
    datas = {d for r in temporais for d in json.loads(r.valores_originais[0])['datas_emissao']}
    resumo['datas_emissao_cadastro'] = sorted(datas)
    cad = {p.unidade_id:p for p in cadastro.pessoas}
    units = {u.id:u for u in lote.unidades}
    notas = list(lote.ressalvas)
    bloqueados = {r.registro_id for r in notas if r.codigo in (
        'PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO','PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO',
        'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO')}
    for b in lote.boletos:
        p = pessoas[b.id]
        if b.unidade_id not in cad or b.id in bloqueados or resolver_documento(p).valor:
            continue
        # Nome e unidade, isoladamente, não bastam para transferir contatos do
        # cadastro antigo. Retém a associação e conserva a dívida/nome financeiro.
        pessoas[b.id] = p.model_copy(update={'contato':Contato(), 'documento':None,
            'documento_origem':None, 'evidencias_documentais':()})
        codigo = 'OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA'
        c = cad[b.unidade_id]
        notas.append(RessalvaLeitura(codigo=codigo, registro_id=b.id, origens=(p.origem,c.origem)))
        resumo['associacoes_concordantes'] -= 1
        resumo['associacoes_retidas'] += 1
    # No OMA o mesmo número ocorre em blocos distintos. Não reutilizar a chave
    # de apresentação sem bloco do Passaredo, que não possui blocos na fonte.
    motivos = {r.registro_id:r.codigo for r in notas if r.codigo in (
        'PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO','PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO',
        'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO','OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA')}
    detalhes = {}
    for b in lote.boletos:
        if b.id not in motivos:
            continue
        u, p, c = units[b.unidade_id], pessoas[b.id], cad[b.unidade_id]
        codigo = motivos[b.id]
        chave = (u.id,p.nome,c.nome,codigo)
        detalhe = detalhes.setdefault(chave,{'unidade':u.bloco_original+'/'+u.unidade_original,
            'responsavel_inadimplencia':p.nome,'responsavel_cadastro':c.nome,'motivo':codigo,'lancamentos':0})
        detalhe['lancamentos'] += 1
    revisao = list(detalhes.values())
    resumo['unidades_em_revisao'] = len({b.unidade_id for b in lote.boletos if b.id in motivos})
    return lote.model_copy(update={'ressalvas':tuple(notas)}), pessoas, resumo, revisao
