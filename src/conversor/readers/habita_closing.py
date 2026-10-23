"""Reconciliação técnica adicional para XLSX local; nunca altera o lote ou libera operação."""
from collections import defaultdict
from hashlib import sha256
import re

from .habita_real import CAUDA, INICIO, UNIDADE
from .real_support import PDFReal, ZERO, data_real
from .text_support import ErroLeitura, dinheiro_brl

VERSAO = 'habita_vg_diagnostico@1'
COLUNAS = ('original', 'multa', 'atualizacao_monetaria', 'juros', 'total_atualizado')


def conferir_fechamento_habita(conteudo, *, contexto, lote, ocorrencias):
    """Somente o fechamento terminal VG duplicando um geral integralmente conferido.

    A ocorrência crítica e o canônico não são modificados. IDs históricos só são
    vinculados quando hash, versão, página, linha e localização coincidem com a
    evidência atual. Outra origem, outro subtotal ou integridade parcial retêm.
    """
    candidatos = [r for r in lote.ressalvas if r.codigo == 'SUBTOTAL_BLOCO_DIVERGENTE']
    resultado = {'versao': VERSAO, 'estado': 'nao_aplicavel',
        'codigo': 'ANOMALIA_FECHAMENTO_HABITA_VG_RECONCILIADA',
        'somente_diagnostico_local': True, 'permite_exportacao_operacional': False,
        'ocorrencias_preservadas': [], 'verificacoes': {}}
    if not candidatos:
        return resultado
    resultado['estado'] = 'nao_reconciliado'
    checks = resultado['verificacoes']
    def exigir(nome, ok):
        checks[nome] = bool(ok)
        if not ok:
            raise ErroLeitura('FECHAMENTO_DIAGNOSTICO_NAO_RECONCILIADO')
    try:
        exigir('leitor_validado', contexto.leitor_versao == 'habita_composicao_real_v1@1')
        exigir('anomalia_unica', len(candidatos) == 1)
        ressalva = candidatos[0]
        exigir('ressalva_global_critica', ressalva.gravidade == 'critico' and ressalva.registro_id is None
               and len(ressalva.origens) == 1)
        fonte = PDFReal(conteudo, contexto, layout=True)
        fonte.validar_condominio('habita')
        unidades = {u.id: u for u in lote.unidades}
        por_chave = {(u.bloco_original, u.unidade_original): u for u in lote.unidades}
        exigir('identidades_completas', bool(unidades) and len(por_chave) == len(unidades))
        origens = [u.origem for u in lote.unidades] + [o for b in lote.boletos for o in b.origens]
        origens += [i.origem for b in lote.boletos for i in b.composicao.itens]
        origens += list(ressalva.origens)
        exigir('fontes_canonicas_vinculadas', all((o.arquivo_id, o.sha256, o.leitor_versao) ==
            (contexto.arquivo_id, fonte.hash, contexto.leitor_versao) for o in origens))
        somas = defaultdict(lambda: [ZERO] * 5)
        itens = defaultdict(list)
        datas = {}
        observadas = set()
        atual = ativo = None
        subtotais, gerais = [], []
        ultima_financeira = None
        fechamentos = {'fechamentos_boletos': 0, 'fechamentos_unidades': 0}
        for pagina in fonte.paginas:
            for linha in pagina:
                text = linha.texto.strip()
                if m := UNIDADE.fullmatch(text):
                    exigir('sem_unidade_apos_geral', not gerais)
                    atual = (m[1], m[2]); observadas.add(atual)
                cauda = CAUDA.search(linha.texto)
                if not cauda:
                    continue  # Demais linhas já passaram pelo leitor operacional estrito.
                valores = list(map(dinheiro_brl, cauda.groups()))
                exigir('soma_componentes_cinco_colunas', sum(valores[:4], ZERO) == valores[4])
                prefixo = ' '.join(linha.texto[:cauda.start()].split())
                exigir('sem_linha_financeira_apos_geral', not gerais)
                if subtotais:
                    exigir('geral_sucede_subtotal', re.search(r'\bTotal Geral:$', prefixo) is not None)
                if prefixo == 'Total do boleto:':
                    exigir('fechamentos_boletos', ativo is not None and somas[ativo] == valores)
                    fechamentos['fechamentos_boletos'] += 1; ativo = None
                elif prefixo == 'Total da Unidade:':
                    exigir('fechamentos_unidades', atual is not None and
                        [sum((v[i] for (u, n), v in somas.items() if u == atual), ZERO) for i in range(5)] == valores)
                    fechamentos['fechamentos_unidades'] += 1; ativo = None
                elif prefixo.startswith('Total do Bloco '):
                    subtotais.append((prefixo, valores, linha)); ativo = None
                elif re.search(r'\bTotal Geral:$', prefixo):
                    quantidade = re.fullmatch(r'Quantidade\b[^0-9:]*:\s*(\d+)\s+Total Geral:', prefixo, re.I)
                    exigir('contagem_documental_unidades', quantidade is not None and int(quantidade[1]) == len(unidades))
                    gerais.append((valores, linha)); ativo = None
                else:
                    exigir('lancamentos_antes_fechamento', not gerais and not subtotais)
                    if m := INICIO.fullmatch(prefixo):
                        ativo = (atual, m[1])
                        vencimento = data_real(m[3], linha)
                        exigir('vencimento_continuacao', ativo not in datas or datas[ativo] == vencimento)
                        datas[ativo] = vencimento
                    exigir('componente_vinculado', ativo is not None and atual in por_chave)
                    somas[ativo] = [a + b for a, b in zip(somas[ativo], valores)]
                    itens[ativo].append((linha.pagina, linha.numero, valores[0]))
                    ultima_financeira = (linha.pagina, linha.numero)
        esperados = {(unidades[b.unidade_id].bloco_original, unidades[b.unidade_id].unidade_original, b.identificador)
                     for b in lote.boletos}
        exigir('inventario_integral', bool(esperados) and observadas == set(por_chave)
            and {(*u, n) for u, n in somas} == esperados)
        for b in lote.boletos:
            u = unidades[b.unidade_id]; chave = ((u.bloco_original, u.unidade_original), b.identificador)
            valores = [b.composicao.total_original, b.multa, b.correcao, b.juros]
            exigir('valores_canonicos_completos', all(v is not None for v in valores))
            exigir('boletos_e_vencimentos_conferidos', somas[chave] == valores + [sum(valores, ZERO)]
                and datas[chave] == b.vencimento)
            exigir('componentes_e_localizacoes_conferidos', itens[chave] ==
                [(i.origem.pagina, i.origem.linha, i.valor) for i in b.composicao.itens])
        exigir('fechamento_terminal_unico', len(subtotais) == len(gerais) == 1)
        rotulo, impresso, sub = subtotais[0]; geral, fim = gerais[0]
        exigir('rotulo_vg_e_ordem_terminal', rotulo == 'Total do Bloco VG:' and sub.pagina == fim.pagina == len(fonte.paginas)
            and ultima_financeira < (sub.pagina, sub.numero) < (fim.pagina, fim.numero))
        exigir('origem_anomalia_exata', ressalva.origens[0] == fonte.origem(sub))
        todos = [sum((v[i] for v in somas.values()), ZERO) for i in range(5)]
        vg = [sum((v[i] for (u, n), v in somas.items() if u[0] == 'VG'), ZERO) for i in range(5)]
        outros = [sum((v[i] for (u, n), v in somas.items() if u[0] != 'VG'), ZERO) for i in range(5)]
        exigir('vg_e_outros_blocos_presentes', any(u[0] == 'VG' for u, n in somas) and any(u[0] != 'VG' for u, n in somas))
        exigir('total_geral_integral_reconciliado', todos == geral)
        exigir('vg_repete_geral_e_difere_do_bloco', impresso == geral and impresso != vg)
        exigir('diferenca_exatamente_demais_blocos', [a - b for a, b in zip(impresso, vg)] == outros)
        exigir('evidencia_original_preservada', ressalva.valores_originais == (rotulo, *map(str, impresso), *map(str, vg)))
        # Um histórico de outra fonte ou outra localização nunca é dispensado.
        origem = fonte.origem(sub)
        vinculadas = [o for o in ocorrencias if o.codigo == 'SUBTOTAL_BLOCO_DIVERGENTE'
            and o.gravidade == 'critico' and o.escopo == 'arquivo' and o.registro_id is None
            and o.origem is not None and (o.origem.sha256, o.origem.leitor_versao,
                o.origem.pagina, o.origem.linha, o.origem.identificador) ==
                (origem.sha256, origem.leitor_versao, origem.pagina, origem.linha, origem.identificador)]
        exigir('identidades_auditoria_sem_colisao', all(sum(o.id == v.id for o in ocorrencias) == 1 for v in vinculadas))
        exigir('ocorrencia_atual_rastreavel', any(o.origem == origem for o in vinculadas))
        resultado.update(estado='reconciliado_somente_diagnostico', fonte_sha256=sha256(conteudo).hexdigest(),
            origem_subtotal=origem.model_dump(mode='json'), origem_total_geral=fonte.origem(fim).model_dump(mode='json'),
            ocorrencias_preservadas=[o.id for o in vinculadas], quantidades={'unidades': len(unidades),
                'boletos': len(somas), 'componentes': sum(map(len, itens.values())),
                'unidades_vg': sum(u.bloco_original == 'VG' for u in lote.unidades),
                'boletos_vg': sum(u[0] == 'VG' for u, n in somas),
                'boletos_outros_blocos': sum(u[0] != 'VG' for u, n in somas), **fechamentos},
            valores={'colunas': list(COLUNAS), 'vg_impresso': list(map(str, impresso)),
                'vg_calculado': list(map(str, vg)), 'geral_impresso': list(map(str, geral)),
                'geral_calculado': list(map(str, todos)), 'demais_blocos': list(map(str, outros))})
    except ErroLeitura:
        resultado['motivo'] = next((k for k, v in checks.items() if not v), 'LEITURA_ADICIONAL_NAO_COMPROVADA')
    return resultado
