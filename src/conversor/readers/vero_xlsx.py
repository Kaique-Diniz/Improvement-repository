"""LELLO Vero: um recibo por dívida, componentes e fechamento conferidos."""
from hashlib import sha256
from io import BytesIO
import json
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Boleto, Composicao, ItemComposicao, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from conversor.domain.vero_encanto import torre_unidade
from .bbz_xlsx import data_fonte
from .oma_xlsx import moeda as moeda_base, texto
from .text_support import ErroLeitura, id_estavel

FORMATO = 'vero_inadimplencia_xlsx_v1'
CABECALHO = ('Código', 'Vencimento', 'Valor Original', 'Valor Multa', 'Correção/Juros', 'Total')
COMPONENTES = ('', 'Conta', 'Histórico', '', 'Valor', '')
REFERENCIA = '10888 - VERO ENCANTO'
EMPRESA = 'LELLO CONDOMINIOS LTDA'


def falha(codigo, linha=None):
    raise ErroLeitura('VERO_' + codigo, linha=linha)


def moeda(valor, linha):
    try:
        return moeda_base(valor, linha)
    except ErroLeitura:
        falha('VALOR_MONETARIO_INVALIDO', linha)


def inteiro(valor, linha):
    if isinstance(valor, bool) or not re.fullmatch(r'[0-9]{1,40}', str(valor)):
        falha('CODIGO_INVALIDO', linha)
    return str(valor)


class LeitorVeroXLSX:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        if (contexto.administradora_id, contexto.condominio_id) != ('lello_2', 'condominio_vero_encanto'):
            falha('CONTEXTO_DIVERGENTE')
        probe = SondadorLocal().sondar(conteudo, arquivo_id='verificacao_vero')
        if probe.tipo != 'xlsx' or probe.bloqueios or not probe.completo:
            falha('XLSX_NAO_EXTRAIVEL')
        book = load_workbook(BytesIO(conteudo), data_only=False, keep_links=False)
        try:
            if book.sheetnames != ['Planilha1'] or book.active.max_column != 6:
                falha('ABA_OU_COLUNAS_INVALIDAS')
            sheet = book.active
            if any(c.data_type == 'f' for row in sheet for c in row):
                falha('FORMULA_NAO_PERMITIDA')
            if tuple(texto(sheet.cell(i, 1).value) for i in (1, 2)) != ('Cota', '* PDF * Email * XLS'):
                falha('TITULO_INVALIDO')
            if any(texto(c.value) for row in list(sheet)[:2] for c in row[1:]):
                falha('TITULO_AMBIGUO')
            digest = sha256(conteudo).hexdigest()

            def origem(n):
                return Origem(arquivo_id=contexto.arquivo_id, sha256=digest,
                    leitor_versao=contexto.leitor_versao or FORMATO+'@1', linha=n,
                    identificador=f'Planilha1_A_F_{n}')

            units, people, bills, notes, totals = [], [], [], [], []
            current = receipt = None
            seen_units, seen_receipts = set(), set()
            state, closed, company = 'empresa', False, None

            def concluir():
                nonlocal receipt
                if receipt is None:
                    return
                items = receipt['items']
                if not items or sum(i.valor for i in items) != receipt['values'][0]:
                    falha('SOMA_COMPONENTES_DIVERGENTE', receipt['line'])
                rid = id_estavel('recibo_vero', current.id, receipt['id'])
                bills.append(Boleto(id=rid, identificador=receipt['id'], unidade_id=current.id,
                    condominio_id=current.condominio_id, vencimento=receipt['due'],
                    composicao=Composicao(itens=tuple(items), total_original=receipt['values'][0]),
                    multa=receipt['values'][1],
                    origens=tuple(receipt['origins'])))
                notes.append(RessalvaLeitura(codigo='VERO_RECIBO_ORIGINAL', gravidade='informativo',
                    registro_id=rid, origens=(origem(receipt['line']),), valores_originais=(json.dumps({
                        'responsavel': people[-1].nome, 'recibo':receipt['id'],
                        'colunas':CABECALHO, 'valores':receipt['values'],
                        'correcao_juros_indissociados':True, 'componentes':receipt['rows']},
                        ensure_ascii=False, default=str),)))
                totals.append(receipt['values'])
                receipt = None

            for row in sheet.iter_rows(min_row=3):
                n = row[0].row
                values = tuple(c.value for c in row)
                labels = tuple(texto(v) for v in values)
                if not any(labels):
                    continue
                if closed:
                    falha('CONTEUDO_APOS_FECHAMENTO', n)
                if labels[0] == 'Total de Débitos':
                    if state != 'componentes' or any(labels[1:2]):
                        falha('FECHAMENTO_INVALIDO', n)
                    concluir()
                    final = tuple(moeda(v, n) for v in values[2:])
                    if not bills or final != tuple(sum(v[i] for v in totals) for i in range(4)):
                        falha('TOTAL_GERAL_DIVERGENTE', n)
                    notes.append(RessalvaLeitura(codigo='VERO_FECHAMENTO_RECONCILIADO',
                        gravidade='informativo', origens=(origem(n),),
                        valores_originais=(json.dumps({'totais':final, 'recibos':len(bills),
                            'unidades':len(units)}, default=str),)))
                    closed = True
                elif labels[0] == 'Empresa':
                    if state not in ('empresa', 'componentes') or any(labels[2:]) or labels[1] != EMPRESA:
                        falha('EMPRESA_INVALIDA', n)
                    concluir()
                    if company is not None and company != labels[1]:
                        falha('EMPRESA_DIVERGENTE', n)
                    company, state = labels[1], 'referencia'
                elif state == 'referencia':
                    if labels[:2] != ('Referência', REFERENCIA) or any(labels[2:]):
                        falha('IDENTIDADE_DIVERGENTE', n)
                    state = 'unidade'
                elif state == 'unidade':
                    m = re.fullmatch(r'([AB]0[0-9]{4}) - (.+)', labels[1])
                    if labels[0] != 'Unidade' or not m or any(labels[2:]) or m[1] in seen_units:
                        falha('UNIDADE_INVALIDA_OU_DUPLICADA', n)
                    seen_units.add(m[1])
                    torre, _ = torre_unidade(m[1])
                    current = Unidade(id=id_estavel('uni_real', contexto.condominio_id, chave_unidade(torre, m[1])),
                        condominio_id=contexto.condominio_id, administradora_id=contexto.administradora_id,
                        bloco_original=torre, unidade_original=m[1], chave_normalizada=chave_unidade(torre,m[1]),
                        normalizador_versao='vero_identidade_textual@1', origem=origem(n))
                    units.append(current)
                    people.append(Pessoa(id=id_estavel('pessoa_vero', current.id), unidade_id=current.id,
                        nome=m[2], relacao_unidade='responsavel_da_fonte_financeira', origem=origem(n)))
                    state = 'multicontas'
                elif state == 'multicontas':
                    if labels != ('Multicontas','NÃO','','','',''):
                        falha('MULTICONTAS_NAO_SUPORTADO', n)
                    state = 'cabecalho'
                elif labels == CABECALHO and state in ('cabecalho','componentes'):
                    concluir()
                    state = 'recibo'
                elif state == 'recibo':
                    code = inteiro(values[0], n)
                    if code in seen_receipts:
                        falha('RECIBO_DUPLICADO', n)
                    seen_receipts.add(code)
                    vector = tuple(moeda(v,n) for v in values[2:])
                    if sum(vector[:3]) != vector[3]:
                        falha('TOTAL_RECIBO_DIVERGENTE', n)
                    receipt = {'id':code, 'line':n, 'due':data_fonte(values[1],n),
                        'values':vector,'items':[], 'origins':[origem(n)],'rows':[]}
                    state = 'cabecalho_componentes'
                elif state == 'cabecalho_componentes':
                    if labels != COMPONENTES:
                        falha('CABECALHO_COMPONENTES_INVALIDO', n)
                    state = 'componentes'
                elif state == 'componentes' and receipt is not None:
                    if any(labels[i] for i in (0,3,5)) or not labels[2]:
                        falha('COMPONENTE_INVALIDO', n)
                    code = inteiro(values[1], n)
                    value = moeda(values[4], n) if labels[4] else None
                    receipt['origins'].append(origem(n))
                    receipt['rows'].append({'conta':code, 'historico':labels[2], 'valor':value, 'linha':n})
                    if value is not None:
                        receipt['items'].append(ItemComposicao(codigo=f'conta_{code}_ordem_{len(receipt["rows"])}',
                            valor=value, descricao_original=labels[2], origem=origem(n)))
                else:
                    falha('ESTRUTURA_INESPERADA', n)
            if not closed:
                falha('FECHAMENTO_AUSENTE')
            return LoteCanonico(unidades=tuple(units), pessoas=tuple(people), boletos=tuple(bills), ressalvas=tuple(notes))
        finally:
            book.close()


def originais(lote):
    return {r.registro_id:json.loads(r.valores_originais[0]) for r in lote.ressalvas if r.codigo == 'VERO_RECIBO_ORIGINAL'}
