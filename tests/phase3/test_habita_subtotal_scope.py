"""Totais inteiramente fictícios: coincidência com o geral não comprova escopo."""
from decimal import Decimal

import pytest

from conversor.application.reading import resultado_leitura
from conversor.readers.text_support import ErroLeitura
from examples.fase3.layouts_sinteticos import habita_paginas
from tests.phase3.test_real_layouts import ler, trocar


def paginas_com_subtotal(*, subtotal_geral=False, geral_incorreto=False):
    primeiro=habita_paginas()
    primeiro[-1]=[r for r in primeiro[-1]if 'Total Geral:'not in r[2]]
    segundo=trocar(habita_paginas(),'DEP','VG')
    segundo=trocar(segundo,'90000001','90000002')
    geral=('250,00 4,00 6,00 8,00 268,00'if geral_incorreto
           else'240,00 4,00 6,00 8,00 258,00')
    segundo[-1]=[(x,y,'Quantidade de unidades inadimplentes no condominio: 2 Total Geral: '+geral)
                 if 'Total Geral:'in t else(x,y,t)for x,y,t in segundo[-1]]
    subtotal=geral if subtotal_geral else'120,00 2,00 3,00 4,00 129,00'
    segundo[-1].insert(-1,(31,666,'Total do Bloco VG: '+subtotal))
    return primeiro+segundo


def assinatura_financeira(lote):
    return [(b.id,b.unidade_id,b.vencimento,b.competencia,b.composicao.total_original,
             tuple(i.valor for i in b.composicao.itens),b.multa,b.correcao,b.juros)
            for b in lote.boletos]


def test_subtotal_exclusivo_vg_reconciliado_nao_bloqueia_outro_bloco():
    lote=ler('habita',paginas_com_subtotal())
    assert len(lote.unidades)==len(lote.boletos)==2
    assert {u.bloco_original for u in lote.unidades}=={'DEP','VG'}
    assert sum(b.composicao.total_original for b in lote.boletos)==Decimal('240.00')
    assert not resultado_leitura(lote,processamento_id='sintetico').bloqueante


def test_subtotal_vg_igual_ao_geral_nao_e_reinterpretado_silenciosamente():
    correto=ler('habita',paginas_com_subtotal())
    ambiguo=ler('habita',paginas_com_subtotal(subtotal_geral=True))
    assert assinatura_financeira(ambiguo)==assinatura_financeira(correto)
    pendencias=[r for r in ambiguo.ressalvas if r.codigo=='SUBTOTAL_BLOCO_DIVERGENTE']
    assert len(pendencias)==1 and pendencias[0].gravidade=='critico'
    assert pendencias[0].origens[0].pagina==4
    assert pendencias[0].valores_originais[0]=='Total do Bloco VG:'
    assert pendencias[0].valores_originais[1:6]!=pendencias[0].valores_originais[6:11]
    assert resultado_leitura(ambiguo,processamento_id='sintetico').bloqueante


def test_subtotal_igual_ao_geral_incorreto_nao_mascara_erro_aritmetico():
    with pytest.raises(ErroLeitura,match='SOMA_GERAL_INCONSISTENTE'):
        ler('habita',paginas_com_subtotal(subtotal_geral=True,geral_incorreto=True))
