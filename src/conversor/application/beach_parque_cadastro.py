"""Beach Parque: A1 por lançamento; somente titular válido transfere contatos."""
from collections import Counter
import json
from conversor.application.passaredo_cadastro import associar as associar_a1
from conversor.domain.canonical import Contato, RessalvaLeitura
from conversor.domain.documents import resolver_documento
from conversor.readers.beach_parque_xlsx import originais

POLITICA = 'beach_parque_titular_nominal_documento_valido_A1@1'
RETIDO_SEM_DOCUMENTO = 'BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA'
MOTIVOS = ('PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO',
    'PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO',
    'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO', RETIDO_SEM_DOCUMENTO)


def associar(lote, cadastro=None):
    lote, pessoas, resumo, _ = associar_a1(lote,cadastro,obter_originais=originais)
    resumo['politica'] = POLITICA
    resumo['historico_nao_comprova_titularidade_atual'] = True
    if cadastro is None:
        return lote,pessoas,resumo,[]
    cad={p.unidade_id:p for p in cadastro.pessoas}
    unidades={u.id:u for u in lote.unidades}
    notas=list(lote.ressalvas)
    retidos={r.registro_id for r in notas if r.codigo in MOTIVOS}
    for b in lote.boletos:
        p=pessoas[b.id]
        if b.unidade_id not in cad or b.id in retidos or resolver_documento(p).valor:
            continue
        pessoas[b.id]=p.model_copy(update={'contato':Contato(),'documento':None,
            'documento_origem':None,'evidencias_documentais':()})
        notas.append(RessalvaLeitura(codigo=RETIDO_SEM_DOCUMENTO,registro_id=b.id,
            origens=(p.origem,cad[b.unidade_id].origem)))
        resumo['associacoes_concordantes']-=1
        resumo['associacoes_retidas']+=1
    temporais=[r for r in cadastro.ressalvas if r.codigo=='BPQ_CADASTRO_TEMPORALIDADE']
    completude=[r for r in cadastro.ressalvas if r.codigo=='BPQ_CADASTRO_IDENTIDADE_E_COMPLETUDE']
    notas.extend(temporais+completude)
    if len(completude)!=1:
        from conversor.readers.text_support import ErroLeitura
        raise ErroLeitura('BPQ_CADASTRO_COMPLETUDE_AUSENTE_OU_AMBIGUA')
    meta=json.loads(completude[0].valores_originais[0])
    resumo.update(registros_cadastro=meta['unidades_resumo'],paginas_cadastro=meta['paginas'],
        continuidades_cadastro=meta['continuidades'])
    resumo['datas_emissao_cadastro']=sorted({d for r in temporais for d in json.loads(r.valores_originais[0])['datas_emissao']})
    motivos={r.registro_id:r.codigo for r in notas if r.codigo in MOTIVOS}
    resumo['retencoes_por_motivo']=dict(Counter(motivos.values()))
    resumo['unidades_em_revisao']=len({b.unidade_id for b in lote.boletos if b.id in motivos})
    resumo['restricoes_por_codigo']=dict(Counter(r.codigo for r in cadastro.ressalvas if r.codigo.startswith('BPQ_REVISAO_')))
    detalhes={}
    for b in lote.boletos:
        if b.id not in motivos:continue
        u=unidades[b.unidade_id];codigo=motivos[b.id]
        key=(u.id,codigo)
        # Relatório temporário por unidade, sem repetir nomes/documentos.
        d=detalhes.setdefault(key,{'unidade':u.bloco_original+'/'+u.unidade_original,
            'motivo':codigo,'lancamentos':0})
        d['lancamentos']+=1
    return lote.model_copy(update={'ressalvas':tuple(notas)}),pessoas,resumo,list(detalhes.values())
