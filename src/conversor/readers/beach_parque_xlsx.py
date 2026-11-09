"""Beach Parque / HABITACIONAL: XLSX estrutural, componentes assinados e fechamento em seis colunas.

Valida identidade documental; não contém prazo de cobrança ou regra por marcador.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import (
    Apontamento, Boleto, Composicao, ItemComposicao, LoteCanonico, Origem,
    Pessoa, RessalvaLeitura, Unidade,
)
from conversor.domain.identity import chave_unidade
from .text_support import ErroLeitura, id_estavel

CABECALHO = ('Recibo','Vencimento','Emissão','Conta','Histórico','Moeda',
             'Valor Original','Valor Principal','Multa','Correção','Juros','Total')
IDENTIDADE = re.compile(r'^Condom[ií]nio:\s*([0-9]+)\s*-\s*(.+)$', re.I)
UNIDADE = re.compile(r'^Bloco:\s*(\S+)\s+Unidade:\s*(\S+)\s+(.+)$', re.I)
PERIODO = re.compile(r'^Per[ií]odo de (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}) a (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})$',re.I)
CONTAGEM = re.compile(r'^Quantidade de unidade\(s\) em aberto:\s*([0-9]+)$', re.I)
RECIBO = re.compile(r'^(?:(A|J) )?([0-9]+)$')
ZERO = (Decimal('0.00'),) * 6


def falha(codigo, linha=None):
    raise ErroLeitura(codigo, linha=linha)


def texto(valor):
    return str(valor).strip() if valor is not None else ''


def carregar(conteudo):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id='verificacao_xlsx')
    if sonda.tipo != 'xlsx' or sonda.bloqueios or not sonda.completo:
        falha('XLSX_NAO_EXTRAIVEL_COM_SEGURANCA')
    try:
        livro = load_workbook(BytesIO(conteudo), data_only=False, keep_links=False)
    except Exception:
        falha('XLSX_INVALIDO')
    try:
        if livro.sheetnames != ['relatorio (4)']:
            falha('FORMATO_AMBIGUO')
        aba = livro.worksheets[0]
        if any(c.data_type == 'f' for row in aba for c in row):
            falha('BPQ_FORMULA_SEM_VALIDACAO')
        if any(c.value is not None for row in aba for c in row[12:]):
            falha('BPQ_COLUNAS_NAO_RECONHECIDAS')
        for n in (1,2):
            if any(c.value is not None for c in aba[n][1:]):falha('BPQ_CABECALHO_AMBIGUO',n)
        identidade = IDENTIDADE.fullmatch(texto(aba['A2'].value))
        periodo = PERIODO.fullmatch(texto(aba['A1'].value))
        if not identidade or not periodo:
            falha('FORMATO_DESCONHECIDO')
        try:
            inicio,fim = [datetime.strptime(v,'%d/%m/%Y %H:%M:%S') for v in periodo.groups()]
            if inicio > fim:raise ValueError
        except ValueError:
            falha('BPQ_PERIODO_INVALIDO',1)
        headers = [row[0].row for row in aba if tuple(texto(c.value) for c in row[:12]) == CABECALHO]
        if not headers or not any(texto(row[4].value) == 'Total do condomínio :' for row in aba):
            falha('FORMATO_DESCONHECIDO')
        return livro,aba,identidade
    except Exception:
        livro.close()
        raise


def identificar(conteudo):
    livro,aba,identidade = carregar(conteudo)
    try:
        return identidade[1],identidade[2]
    finally:
        livro.close()


def moeda(valor, linha):
    # Excel armazena números binários; converter representação antes de calcular.
    # Nunca fazer contas/igualdade monetária com float ou arredondar divergências.
    if isinstance(valor,bool) or not isinstance(valor,(int,float,Decimal,str)):
        falha('BPQ_VALOR_MONETARIO_INVALIDO',linha)
    try:
        v = Decimal(str(valor))
        if not v.is_finite() or v != v.quantize(Decimal('.01')):
            raise InvalidOperation
        return v.quantize(Decimal('.01'))
    except (InvalidOperation,ValueError):
        falha('BPQ_VALOR_MONETARIO_INVALIDO',linha)


def data_fonte(valor, linha):
    if isinstance(valor,datetime):
        if valor.time().isoformat() != '00:00:00':falha('BPQ_DATA_COM_HORA',linha)
        return valor.date()
    if type(valor) is date:return valor
    if isinstance(valor,str):
        for fmt in ('%d/%m/%Y','%Y-%m-%d'):
            try:return datetime.strptime(valor,fmt).date()
            except ValueError:pass
    falha('BPQ_DATA_INVALIDA',linha)


def somar(vetores):
    resultado = ZERO
    for vetor in vetores:
        resultado = tuple(a+b for a,b in zip(resultado,vetor,strict=True))
    return resultado


class LeitorBeachParqueXLSX:
    formato_id = 'beach_parque_inadimplencia_xlsx_v1'

    def ler(self, conteudo, *, contexto):
        livro,aba,identidade = carregar(conteudo)
        try:
            if (identidade[1], identidade[2], contexto.administradora_id, contexto.condominio_id) != ('3075', 'TERRAÇO BEACH PARQUE', 'habitacional', 'condominio_terraco_beach_parque'):
                falha('IDENTIDADE_BPQ_DIVERGENTE')
            digest = sha256(conteudo).hexdigest()
            def origem(linha, intervalo='A:L'):
                return Origem(arquivo_id=contexto.arquivo_id,sha256=digest,
                    leitor_versao=contexto.leitor_versao or self.formato_id+'@1',linha=linha,
                    identificador=f'xlsx_aba1_r{linha}_'+intervalo.replace(':','_'))
            unidades=[];pessoas=[];boletos=[];ressalvas=[];vistos=set();unit_keys=set()
            unidade=None;recibo=None;cabecalho=False;unidade_fechada=True;fechado=False
            totais_recibos=[];totais_unidade=[];fechamentos=[];linha_fechamento=None
            def evidenciar(codigo,linha,dados,registro_id=None):
                ressalvas.append(RessalvaLeitura(codigo=codigo,gravidade='informativo',registro_id=registro_id,
                    origens=(origem(linha),),valores_originais=(json.dumps(dados,ensure_ascii=False,default=str,sort_keys=True),)))
            for row in aba:
                n=row[0].row
                if not any(c.value is not None for c in row):continue
                valores=tuple(c.value for c in row[:12]);a=texto(valores[0])
                if fechado:falha('BPQ_CONTEUDO_APOS_FECHAMENTO',n)
                if n in (1,2):continue
                if m:=UNIDADE.fullmatch(a):
                    if not unidade_fechada or recibo:falha('BPQ_UNIDADE_NAO_FECHADA',n)
                    if any(v is not None for v in valores[1:]):falha('BPQ_CABECALHO_UNIDADE_AMBIGUO',n)
                    chave=chave_unidade(m[1],m[2])
                    if chave in unit_keys:falha('BPQ_UNIDADE_DUPLICADA',n)
                    unit_keys.add(chave)
                    unidade=Unidade(id=id_estavel('uni_real',contexto.condominio_id,chave),
                        condominio_id=contexto.condominio_id,administradora_id=contexto.administradora_id,
                        bloco_original=m[1],unidade_original=m[2],chave_normalizada=chave,
                        normalizador_versao='identidade_real_v1',origem=origem(n,'A'))
                    from conversor.domain.beach_parque import complemento_unidade
                    try: complemento_unidade(m[1], m[2])
                    except ValueError: falha('BPQ_UNIDADE_INVALIDA', n)
                    unidades.append(unidade)
                    pessoas.append(Pessoa(id=id_estavel('pessoa_bpq',unidade.id),unidade_id=unidade.id,
                        nome=m[3],relacao_unidade='nome_no_cabecalho_financeiro',origem=origem(n,'A')))
                    unidade_fechada=False;cabecalho=False;totais_recibos=[]
                    evidenciar('BPQ_CABECALHO_UNIDADE_ORIGINAL',n,{'aba':aba.title,'celula':f'A{n}','texto':a},unidade.id)
                    continue
                if tuple(texto(v)for v in valores)==CABECALHO:
                    if unidade is None or unidade_fechada or cabecalho:falha('BPQ_CABECALHO_AMBIGUO',n)
                    cabecalho=True;continue
                if texto(valores[4])=='Total do condomínio :':
                    m=CONTAGEM.fullmatch(a)
                    if (not m or not unidade_fechada or recibo or int(m[1])!=len(unidades)
                            or texto(valores[5])!='R$'or any(v is not None for v in valores[1:4])):
                        falha('BPQ_CONTAGEM_OU_FECHAMENTO_INVALIDO',n)
                    total=tuple(moeda(v,n)for v in valores[6:12])
                    if total!=somar(totais_unidade):falha('BPQ_TOTAL_CONDOMINIO_DIVERGENTE',n)
                    fechado=True;linha_fechamento=n;fechamentos.append({'nivel':'condominio','linha':n,'totais':total})
                    continue
                if a in ('Total do Recibo:','Total Geral da Unidade:'):
                    if unidade is None or unidade_fechada or not cabecalho or texto(valores[5])!='R$':
                        falha('BPQ_SUBTOTAL_FORA_DE_CONTEXTO',n)
                    if any(v is not None for v in valores[1:5]):falha('BPQ_SUBTOTAL_AMBIGUO',n)
                    total=tuple(moeda(v,n)for v in valores[6:12])
                    if a=='Total do Recibo:':
                        if recibo is None or not recibo['itens']:falha('BPQ_RECIBO_SEM_COMPONENTES',n)
                        if total!=somar(recibo['vetores']):falha('BPQ_TOTAL_RECIBO_DIVERGENTE',n)
                        rid=id_estavel('boleto_bpq',unidade.id,recibo['token'],recibo['inicio'])
                        boletos.append(Boleto(id=rid,condominio_id=contexto.condominio_id,unidade_id=unidade.id,
                            identificador=f"bpq_{recibo['inicio']:06d}:{recibo['token'].replace(' ','.')}",vencimento=recibo['vencimento'],
                            emissao=recibo['emissao'],emissao_original=recibo['emissao_original'],
                            composicao=Composicao(itens=tuple(recibo['itens']),total_original=total[0]),
                            multa=total[2],correcao=total[3],juros=total[4],
                            apontamentos=tuple(recibo['apontamentos']),origens=tuple(recibo['origens'])+(origem(n),)))
                        evidenciar('BPQ_RECIBO_RECONCILIADO',n,{'aba':aba.title,'celulas':f'G{n}:L{n}',
                            'recibo_original':recibo['token'],'colunas':CABECALHO[6:],'totais':total,
                            'componentes':recibo['linhas'], 'responsavel':pessoas[-1].nome,
                            'emissao_original':recibo['emissao_original'], 'ordem':len(boletos)},rid)
                        totais_recibos.append(total);recibo=None
                    else:
                        if recibo or not totais_recibos:falha('BPQ_RECIBO_NAO_FECHADO',n)
                        if total!=somar(totais_recibos):falha('BPQ_TOTAL_UNIDADE_DIVERGENTE',n)
                        unidade_fechada=True;totais_unidade.append(total)
                        fechamentos.append({'nivel':'unidade','unidade_id':unidade.id,'linha':n,'totais':total})
                    continue
                if unidade is None or unidade_fechada or not cabecalho:
                    falha('BPQ_LINHA_FORA_DE_CONTEXTO',n)
                if any(c.value is not None for c in row[12:]):falha('BPQ_COLUNAS_NAO_RECONHECIDAS',n)
                if isinstance(valores[0],bool) or not (m:=RECIBO.fullmatch(a)):
                    falha('BPQ_RECIBO_OU_MARCADOR_INVALIDO',n)
                if valores[1] is not None:
                    if recibo:falha('BPQ_RECIBO_NAO_FECHADO',n)
                    # Ocorrências documentais são independentes, inclusive código repetido.
                    # Linha de abertura integra o ID estável; nunca deduplicar dívidas.
                    chave=(unidade.id,a)
                    if chave in vistos:
                        evidenciar('BPQ_CODIGO_REPETIDO_OCORRENCIA_PRESERVADA',n,{'recibo_original':a},unidade.id)
                    vistos.add(chave)
                    emissao=None;raw_emissao=texto(valores[2])
                    if isinstance(valores[2],(date,datetime)):
                        emissao=data_fonte(valores[2],n)
                    elif valores[2] is not None:
                        evidenciar('BPQ_EMISSAO_BRUTA_NAO_INTERPRETADA',n,{'celula':f'C{n}','valor':raw_emissao},unidade.id)
                    recibo={'inicio':n,'id':m[2],'token':a,'vencimento':data_fonte(valores[1],n),'emissao':emissao,
                        'emissao_original':raw_emissao or None,'apontamentos':[],
                        'itens':[],'vetores':[],'origens':[],'linhas':[]}
                    if m[1]:recibo['apontamentos'].append(Apontamento(codigo_original=m[1],
                        namespace_formato=self.formato_id,origem=origem(n,'A')))
                elif recibo is None or recibo['token']!=a or valores[2] is not None:
                    falha('BPQ_CONTINUACAO_DE_RECIBO_AMBIGUA',n)
                vetor=tuple(moeda(v,n)for v in valores[6:12])
                if (texto(valores[5])!='R$' or not texto(valores[3]) or
                        not isinstance(valores[4],str) or not valores[4].strip()):
                    falha('BPQ_COMPONENTE_INCOMPLETO',n)
                if sum(vetor[1:5],Decimal(0))!=vetor[5]:falha('BPQ_TOTAL_COMPONENTE_DIVERGENTE',n)
                recibo['itens'].append(ItemComposicao(codigo=f'componente_{n}',valor=vetor[0],
                    descricao_original=valores[4] if valores[4] is not None else '',origem=origem(n,'G')))
                recibo['vetores'].append(vetor);recibo['origens'].append(origem(n))
                recibo['linhas'].append({'linha':n,'moeda':texto(valores[5]),'emissao_original':valores[2],'celulas':f'A{n}:L{n}',
                    'recibo':a,'conta':texto(valores[3]),'historico':valores[4],
                    'valores':vetor,'formatos':[c.number_format for c in row[6:12]]})
            if not fechado or recibo or not unidades or not unidade_fechada:
                falha('BPQ_RELATORIO_INCOMPLETO')
            evidenciar('BPQ_FECHAMENTO_RECONCILIADO',linha_fechamento,{'aba':aba.title,
                'identidade_original':texto(aba['A2'].value),'periodo_original':texto(aba['A1'].value),
                'colunas_monetarias':CABECALHO[6:],'fechamentos':fechamentos,
                'unidades':len(unidades),'recibos':len(boletos)})
            return LoteCanonico(unidades=tuple(unidades),pessoas=tuple(pessoas),boletos=tuple(boletos),ressalvas=tuple(ressalvas))
        finally:
            livro.close()


def originais(lote):
    return {r.registro_id:json.loads(r.valores_originais[0]) for r in lote.ressalvas
            if r.codigo == 'BPQ_RECIBO_RECONCILIADO'}
