"""Projeção de cotas/unidades e causas: não interpreta regras nem altera boletos."""
from conversor.domain.billing_evaluation import AvaliacaoRegra


def causas_veto(avaliacoes: tuple[AvaliacaoRegra, ...], boletos):
    causas = []
    for regra in avaliacoes:
        if regra.alvo != 'unidade' or regra.acao != 'excluir' or regra.passo.resultado != 'verdadeiro':
            continue
        # As condições estruturadas usam existe_boleto; cada filho conserva
        # o ID e as fontes do boleto que comprovou a condição.
        for filho in regra.passo.filhos:
            if filho.resultado == 'verdadeiro' and filho.boleto_id:
                boleto = boletos[filho.boleto_id]
                causas.append({'regra_id': regra.regra_id, 'versao': regra.plano_versao,
                    'boleto_id': boleto.id, 'boleto': boleto.identificador,
                    'fonte_regra': regra.fonte_regra.model_dump(mode='json'),
                    'origens': [o.model_dump(mode='json') for o in filho.origens]})
    return causas


def projetar_cotas(lote, decisoes, avaliacoes_unidade):
    boletos = {b.id: b for b in lote.boletos}
    cotas = []
    for unidade in lote.unidades:
        ds = [d for d in decisoes if d['unidade_id'] == unidade.id]
        causas = causas_veto(avaliacoes_unidade[unidade.id], boletos)
        selecionados = [d['id'] for d in ds if d['situacao_financeira'] == 'elegivel_na_simulacao']
        prazo = [d['id'] for d in ds if d['motivo_selecao'] == 'prazo_nao_atingido']
        indeterminados = [d['id'] for d in ds if d['situacao_financeira'] not in ('excluido', 'elegivel_na_simulacao')]
        retidos = [d['id'] for d in ds if d['situacao'] == 'revisao']
        estado = ('excluida_por_veto' if causas else 'pendente_revisao' if indeterminados else
                  'elegivel' if selecionados else 'sem_boleto_no_prazo')
        cotas.append({'id': unidade.id, 'condominio_id': unidade.condominio_id,
            'administradora_id': unidade.administradora_id, 'bloco': unidade.bloco_original,
            'unidade': unidade.unidade_original, 'chave_normalizada': unidade.chave_normalizada,
            'boletos_ids': [d['id'] for d in ds], 'situacao_financeira': estado,
            'boletos_selecionados': selecionados, 'boletos_fora_prazo': prazo,
            'boletos_retidos': retidos, 'retida_tecnicamente': bool(retidos),
            'impedimentos_tecnicos': sorted({m for d in ds if d['situacao'] == 'revisao'
                for m in (d['bloqueios'] or ['CONDICAO_INDETERMINADA'])}),
            'causas_veto': causas,
            'regras_avaliadas': [r.model_dump(mode='json') for r in avaliacoes_unidade[unidade.id]],
            'origem_unidade': unidade.origem.model_dump(mode='json')})
    return cotas
