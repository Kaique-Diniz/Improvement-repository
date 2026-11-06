"""OMA: recibos hierárquicos; nenhum prazo ou associação pessoal neste leitor."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Boleto, Composicao, ItemComposicao, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from .bbz_xlsx import data_fonte, somar, ZERO
from .text_support import ErroLeitura, id_estavel, dinheiro_brl

FORMATO = 'oma_inadimplencia_xlsx_v1'
CABECALHO = ('Recibo', 'Vencimento', 'Emissão', 'Conta', 'Histórico', '', 'Valor Original', 'Valor Principal', 'Multa', 'Atualização Monetária', 'Juros', 'Total')
UNIDADE = re.compile(r'Bloco ([0-9]{2}) - Unidade ([0-9]{6}|[0-9]{5}S) : (.+)')
RECIBO = re.compile(r'[0-9]+(?: [A-Z]+)?')


def falha(codigo, linha=None):
    raise ErroLeitura('OMA_' + codigo, linha=linha)


def texto(v):
    return '' if v is None else str(v).strip()


def moeda(v, linha):
    if isinstance(v, bool) or v is None:
        falha('MOEDA_INVALIDA', linha)
    try:
        n = dinheiro_brl(v.strip()) if isinstance(v, str) and ',' in v else Decimal(str(v))
        if not n.is_finite() or n != n.quantize(Decimal('.01')):
            raise ValueError
        return n.quantize(Decimal('.01'))
    except (InvalidOperation, ValueError, ErroLeitura):
        falha('MOEDA_INVALIDA', linha)


def carregar(conteudo):
    probe = SondadorLocal().sondar(conteudo, arquivo_id='verificacao_oma')
    if probe.tipo != 'xlsx' or probe.bloqueios or not probe.completo:
        falha('XLSX_NAO_EXTRAIVEL')
    book = load_workbook(BytesIO(conteudo), data_only=False, keep_links=False)
    try:
        if book.sheetnames != ['Sheet']:
            falha('ABA_INVALIDA')
        sheet = book['Sheet']
        if sheet.max_column != 12 or any(c.data_type == 'f' for row in sheet for c in row):
            falha('COLUNAS_OU_FORMULAS_INVALIDAS')
        if (texto(sheet['A1'].value) or texto(sheet['C1'].value) or
                any(texto(c.value) for c in sheet[1][3:]) or
                not re.fullmatch(r'Inadimplência\nPosição em: [0-9]{2}/[0-9]{2}/[0-9]{4}', texto(sheet['B1'].value))):
            falha('POSICAO_INVALIDA', 1)
        try:
            posicao = datetime.strptime(texto(sheet['B1'].value).split(': ')[1], '%d/%m/%Y').date()
        except ValueError:
            falha('POSICAO_INVALIDA', 1)
        if not re.fullmatch(r'Condomínio: .+', texto(sheet['A2'].value)):
            falha('IDENTIDADE_AUSENTE', 2)
        if any(texto(c.value) for c in sheet[2][1:]) or any(texto(c.value) for c in sheet[3][1:]):
            falha('CABECALHO_AMBIGUO')
        if not texto(sheet['A3'].value).startswith('Endereço: ') or tuple(texto(c.value) for c in sheet[4]) != CABECALHO:
            falha('CABECALHO_INVALIDO')
        return book, sheet, texto(sheet['A2'].value)[12:].strip(), posicao
    except Exception:
        book.close()
        raise



class LeitorOMAXLSX:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        book, sheet, nome, posicao = carregar(conteudo)
        try:
            if nome != 'PARQUE SANTA MONICA' or (contexto.condominio_id, contexto.administradora_id) != ('condominio_parque_santa_monica', 'oma'):
                falha('IDENTIDADE_DIVERGENTE')
            digest = sha256(conteudo).hexdigest()
            def origem(n, cols='A_L'):
                return Origem(arquivo_id=contexto.arquivo_id, sha256=digest,
                    leitor_versao=contexto.leitor_versao or FORMATO+'@1', linha=n,
                    identificador=f'Sheet_{cols}_{n}', data_fonte=posicao)
            units, persons, bills, notes = [], [], [], []
            current = receipt = None
            unit_closed = True
            closed = False
            resumo_count = 0
            resumo_fechado = False
            keys, seen = set(), set()
            unit_totals, receipt_totals = [], []
            def evidence(code, n, values, rid=None):
                notes.append(RessalvaLeitura(codigo=code, gravidade='informativo', registro_id=rid,
                    origens=(origem(n),), valores_originais=(json.dumps(values, ensure_ascii=False, default=str),)))
            for row in sheet.iter_rows(min_row=5):
                n = row[0].row
                values = tuple(c.value for c in row)
                labels = tuple(texto(v) for v in values)
                if not any(labels):
                    continue
                if closed:
                    # A fonte contém uma cópia sequencial dos totais unitários
                    # após o primeiro acumulado. Conferir integralmente, nunca
                    # materializar novos recibos a partir desse resumo.
                    if any(labels[:5]) or resumo_fechado:
                        falha('CONTEUDO_APOS_FECHAMENTO', n)
                    vetor_resumo = tuple(moeda(v,n) for v in values[6:])
                    if labels[5] == 'Total da unidade:' and resumo_count < len(unit_totals):
                        if vetor_resumo != unit_totals[resumo_count]:
                            falha('RESUMO_UNITARIO_DIVERGENTE', n)
                        resumo_count += 1
                    elif labels[5] == 'Total acumulado:' and resumo_count == len(unit_totals):
                        if vetor_resumo != somar(unit_totals):
                            falha('RESUMO_ACUMULADO_DIVERGENTE', n)
                        resumo_fechado = True
                        evidence('OMA_RESUMO_REPETIDO_RECONCILIADO', n, {'totais_unitarios':resumo_count})
                    else:
                        falha('RESUMO_FINAL_AMBIGUO', n)
                    continue
                if m := UNIDADE.fullmatch(labels[0]):
                    if not unit_closed or receipt or any(labels[1:]):
                        falha('UNIDADE_AMBIGUA_OU_NAO_FECHADA', n)
                    key = chave_unidade(m[1], m[2])
                    if key in keys:
                        falha('UNIDADE_DUPLICADA', n)
                    keys.add(key)
                    current = Unidade(id=id_estavel('uni_real', contexto.condominio_id, key),
                        condominio_id=contexto.condominio_id, administradora_id=contexto.administradora_id,
                        bloco_original=m[1], unidade_original=m[2], chave_normalizada=key,
                        normalizador_versao='oma_identidade_textual@1', origem=origem(n))
                    units.append(current)
                    persons.append(Pessoa(id=id_estavel('pessoa_oma', current.id), unidade_id=current.id,
                        nome=m[3], relacao_unidade='responsavel_da_fonte_financeira', origem=origem(n)))
                    unit_closed = False
                    receipt_totals = []
                    continue
                if labels[5] == 'Total acumulado:':
                    if any(labels[:5]) or not unit_closed or receipt or not units:
                        falha('FECHAMENTO_GERAL_INVALIDO', n)
                    total = tuple(moeda(v,n) for v in values[6:])
                    if total != somar(unit_totals):
                        falha('TOTAL_GERAL_DIVERGENTE', n)
                    evidence('OMA_FECHAMENTO_RECONCILIADO', n, {'totais':total, 'unidades':len(units), 'recibos':len(bills)})
                    closed = True
                    continue
                if labels[4] == 'Total do recibo:':
                    if any(labels[:4]) or labels[5] or not receipt or not receipt['items']:
                        falha('FECHAMENTO_RECIBO_INVALIDO', n)
                    total = tuple(moeda(v,n) for v in values[6:])
                    if total != somar(receipt['vectors']):
                        falha('TOTAL_RECIBO_DIVERGENTE', n)
                    rid = id_estavel('recibo_oma', current.id, receipt['id'])
                    bills.append(Boleto(id=rid, identificador=receipt['id'].replace(' ', '.'), condominio_id=contexto.condominio_id,
                        unidade_id=current.id, vencimento=receipt['due'], emissao_original=receipt['emission'],
                        composicao=Composicao(itens=tuple(receipt['items']), total_original=total[0]),
                        multa=total[2], correcao=total[3], juros=total[4],
                        origens=tuple(receipt['origins'])+(origem(n),)))
                    evidence('OMA_RECIBO_ORIGINAL', n, {'responsavel':persons[-1].nome, 'recibo':receipt['id'],
                        'ordem_origem':len(bills), 'colunas':CABECALHO[6:], 'totais':total,
                        'componentes':receipt['rows']}, rid)
                    receipt_totals.append(total)
                    receipt = None
                    continue
                if labels[5] == 'Total da unidade:':
                    if any(labels[:5]) or current is None or unit_closed or receipt or not receipt_totals:
                        falha('FECHAMENTO_UNIDADE_INVALIDO', n)
                    total = tuple(moeda(v,n) for v in values[6:])
                    if total != somar(receipt_totals):
                        falha('TOTAL_UNIDADE_DIVERGENTE', n)
                    unit_totals.append(total)
                    unit_closed = True
                    continue
                if current is None or unit_closed or labels[5]:
                    falha('COMPONENTE_FORA_DE_CONTEXTO', n)
                if labels[0]:
                    if receipt or not RECIBO.fullmatch(labels[0]) or len(labels[0]) > 127 or not labels[1]:
                        falha('RECIBO_INVALIDO_OU_NAO_FECHADO', n)
                    key = (current.id, labels[0])
                    if key in seen:
                        falha('RECIBO_DUPLICADO', n)
                    seen.add(key)
                    receipt = {'id':labels[0], 'due':data_fonte(values[1],n), 'emission':labels[2] or None,
                        'items':[], 'vectors':[], 'origins':[], 'rows':[]}
                elif receipt is None or any(labels[1:3]):
                    falha('CONTINUACAO_AMBIGUA', n)
                if not labels[3] or not labels[4]:
                    falha('COMPONENTE_INCOMPLETO', n)
                vector = tuple(moeda(v,n) for v in values[6:])
                if sum(vector[1:5], Decimal(0)) != vector[5]:
                    falha('TOTAL_COMPONENTE_DIVERGENTE', n)
                receipt['items'].append(ItemComposicao(codigo=f'componente_{n}', valor=vector[0],
                    descricao_original=labels[4], origem=origem(n,'D_L')))
                receipt['vectors'].append(vector)
                receipt['origins'].append(origem(n))
                receipt['rows'].append({'linha':n,'conta':labels[3],'descricao':labels[4],'valores':vector})
            if not closed or receipt or not unit_closed or (resumo_count and not resumo_fechado):
                falha('RELATORIO_INCOMPLETO')
            evidence('OMA_CABECALHO_ORIGINAL', 3, {'endereco':texto(sheet['A3'].value), 'posicao':posicao})
            return LoteCanonico(unidades=tuple(units), pessoas=tuple(persons), boletos=tuple(bills), ressalvas=tuple(notes))
        finally:
            book.close()


def originais(lote):
    data = {r.registro_id:json.loads(r.valores_originais[0]) for r in lote.ressalvas if r.codigo=='OMA_RECIBO_ORIGINAL'}
    if set(data) != {b.id for b in lote.boletos}:
        falha('PROVENIENCIA_INCOMPLETA')
    return data
