"""Lista de Ctas a Receber BN Planner: linhas, subtotais e paginação."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import re

from pypdf import PdfReader

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Boleto, Composicao, ItemComposicao, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from conversor.domain.itajuba import complemento_unidade
from .text_support import ErroLeitura, id_estavel, dinheiro_brl

FORMATO = 'itajuba_inadimplencia_pdf_v1'
TIPOS = {'Tt':'COTA CONDOMINIAL','Mlt':'MULTA','Ext':'COTA EXTRA','AcT':'ACORDO'}
COLUNAS = ((0,85),(85,150),(150,270),(270,340),(340,397),(397,533),(533,574),(574,610),(610,773),(773,863))
CABECALHO = ('Doc.','Dt Vcto','Tx Cond','Outros','Total','Condômino','Torre','Bloco/Ap','Inquilino','Acordo')


def falha(codigo,pagina=None,linha=None):
    raise ErroLeitura('ITAJUBA_'+codigo,pagina=pagina,linha=linha)


@dataclass(frozen=True)
class Linha:
    pagina: int
    numero: int
    partes: tuple

    def texto(self,inicio=0,fim=863):
        return ' '.join(t for x,y,t in self.partes if inicio<=x<fim).strip()


def unidade(torre,apartamento,contexto,origem):
    try:complemento_unidade(torre,apartamento)
    except ValueError:falha('UNIDADE_INVALIDA',origem.pagina,origem.linha)
    key=chave_unidade(torre,apartamento)
    return Unidade(id=id_estavel('uni_real',contexto.condominio_id,key),condominio_id=contexto.condominio_id,
        administradora_id=contexto.administradora_id,bloco_original=torre,unidade_original=apartamento,
        chave_normalizada=key,normalizador_versao='itajuba_identidade_textual@1',origem=origem)


def paginas(conteudo):
    probe=SondadorLocal().sondar(conteudo,arquivo_id='verificacao_itajuba')
    if probe.tipo!='pdf_texto' or probe.bloqueios or not probe.completo:
        falha('PDF_NAO_EXTRAIVEL')
    result=[]
    try:
        with BytesIO(conteudo) as stream:
            pdf=PdfReader(stream,strict=True)
            for pi,page in enumerate(pdf.pages,1):
                if not 861<=float(page.mediabox.width)<=864 or not 615<=float(page.mediabox.height)<=618:
                    falha('GEOMETRIA_INCOMPATIVEL',pi)
                parts=[]
                def visitor(text,cm,tm,font,size):
                    value=text.replace('\r','').replace('\n','').strip()
                    if value:
                        x=tm[4]*cm[0]+tm[5]*cm[2]+cm[4];y=tm[4]*cm[1]+tm[5]*cm[3]+cm[5]
                        if not 0<=x<864 or not 0<=y<=618:falha('GEOMETRIA_INCOMPATIVEL',pi)
                        parts.append((x,y,value))
                page.extract_text(visitor_text=visitor)
                identity=[t for x,y,t in parts if 160<x<170 and 578<y<583]
                if identity!=['CONDOMINIO ITAJUBA']:falha('IDENTIDADE_DIVERGENTE',pi)
                dates=[t for x,y,t in parts if 770<x<820 and 578<y<583]
                if len(dates)!=1:falha('EMISSAO_INVALIDA',pi)
                try:emissao=datetime.strptime(dates[0],'%d/%m/%y').date()
                except ValueError:falha('EMISSAO_INVALIDA',pi)
                number=[t for x,y,t in parts if 520<x<550 and y<15]
                total=[t for x,y,t in parts if (x<1 and y<1) or (575<x<620 and y<15)]
                if number!=[str(pi)] or total!=[str(len(pdf.pages))]:falha('PAGINACAO_INCOMPLETA',pi)
                if not any(t=='Página'and y<15 for x,y,t in parts) or not any(t=='de'and y<15 for x,y,t in parts):
                    falha('RODAPE_INVALIDO',pi)
                if not any(t.startswith('Lista de Ctas a Receber período de ')and 525<y<540 for x,y,t in parts):
                    falha('TITULO_INVALIDO',pi)
                groups=[]
                for part in sorted((p for p in parts if 15<p[1]<525),key=lambda p:(-p[1],p[0])):
                    if groups and abs(groups[-1][0]-part[1])<2:
                        groups[-1][1].append(part)
                    else:groups.append((part[1],[part]))
                rows=[Linha(pi,n,tuple(sorted(items)))for n,(_,items)in enumerate(groups,1)]
                header=bool(rows)and tuple(rows[0].texto(a,b)for a,b in COLUNAS)==CABECALHO
                if not rows or(pi==1 and not header):
                    falha('CABECALHO_INVALIDO',pi)
                # A fonte imprime colunas só na primeira página. Páginas de
                # continuação mantêm identidade, emissão e paginação conferidas.
                result.append((emissao,rows[1:]if header else rows))
    except ErroLeitura:raise
    except Exception:falha('PDF_INVALIDO')
    if len({emissao for emissao,_ in result})!=1:falha('EMISSAO_DIVERGENTE')
    return result


class LeitorItajubaPDF:
    formato_id=FORMATO

    def ler(self,conteudo,*,contexto):
        if(contexto.administradora_id,contexto.condominio_id)!=('bn_planner','condominio_itajuba'):
            falha('CONTEXTO_DIVERGENTE')
        digest=sha256(conteudo).hexdigest()
        units,owners,bills,notes={}, {}, [], []
        names=defaultdict(set);repetitions=Counter();subtotal=Decimal(0);general=Decimal(0)
        current=None;closed=True;finished=False
        for emissao,rows in paginas(conteudo):
            for line in rows:
                if finished:falha('CONTEUDO_APOS_FECHAMENTO',line.pagina,line.numero)
                values=tuple(line.texto(a,b)for a,b in COLUNAS)
                origin=Origem(arquivo_id=contexto.arquivo_id,sha256=digest,leitor_versao=contexto.leitor_versao or FORMATO+'@1',
                    pagina=line.pagina,linha=line.numero,identificador=f'p{line.pagina}_l{line.numero}',data_fonte=emissao)
                if values[1]in('Total Unidade','Total Geral'):
                    amounts=[t for x,y,t in line.partes if t not in('Total Unidade','Total Geral')]
                    if len(amounts)!=1:falha('FECHAMENTO_INVALIDO',line.pagina,line.numero)
                    amount=dinheiro_brl(amounts[0])
                    if values[1]=='Total Unidade':
                        if current is None or closed or amount!=subtotal:falha('SUBTOTAL_DIVERGENTE',line.pagina,line.numero)
                        closed=True
                    else:
                        if not bills or not closed or amount!=general:falha('TOTAL_GERAL_DIVERGENTE',line.pagina,line.numero)
                        finished=True
                    notes.append(RessalvaLeitura(codigo='ITAJUBA_FECHAMENTO_RECONCILIADO',gravidade='informativo',
                        registro_id=current.id if values[1]=='Total Unidade'else None,origens=(origin,),
                        valores_originais=(values[1],str(amount))))
                    continue
                match=re.fullmatch(r'(Tt|Mlt|Ext|AcT)(?:[_-][A-Za-z0-9_-]+|[0-9]+)',values[0])
                if not match or not values[5]:falha('LINHA_FINANCEIRA_INVALIDA',line.pagina,line.numero)
                try:due=datetime.strptime(values[1],'%d/%m/%Y').date()
                except ValueError:falha('VENCIMENTO_INVALIDO',line.pagina,line.numero)
                tx,out,total=(dinheiro_brl(v)for v in values[2:5])
                if tx+out!=total:falha('SOMA_LINHA_DIVERGENTE',line.pagina,line.numero)
                u=unidade(values[6],values[7],contexto,origin)
                if current is None or u.id!=current.id:
                    if u.id in units:falha('UNIDADE_REPETIDA_FORA_DE_SEQUENCIA',line.pagina,line.numero)
                    if current is not None and not closed:
                        # Algumas unidades da fonte não têm subtotal impresso.
                        # Não inventar uma conferência local: todas as linhas
                        # continuam obrigatoriamente incluídas no total geral.
                        notes.append(RessalvaLeitura(codigo='ITAJUBA_SUBTOTAL_NAO_IMPRESSO',registro_id=current.id,
                            origens=(current.origem,),valores_originais=(str(subtotal),)))
                    current=u;units[u.id]=u;subtotal=Decimal(0);closed=False
                elif closed:falha('LINHA_APOS_SUBTOTAL',line.pagina,line.numero)
                names[u.id].add(values[5])
                owners.setdefault(u.id,Pessoa(id=id_estavel('representante_itajuba',u.id,values[5]),unidade_id=u.id,
                    nome=values[5],origem=origin,relacao_unidade='representante_estrutural_da_fonte'))
                key=(u.id,*values)
                repetitions[key]+=1
                rid=id_estavel('lancamento_itajuba',*key,repetitions[key])
                # Identificador técnico da ocorrência, ordenável e estável para
                # a mesma entrada. Doc. bruto continua integral na evidência.
                occurrence_id=f'itj_{len(bills)+1:06d}:{rid.split(":",1)[1]}'
                bills.append(Boleto(id=rid,identificador=occurrence_id,condominio_id=u.condominio_id,unidade_id=u.id,vencimento=due,
                    composicao=Composicao(total_original=total,itens=(
                        ItemComposicao(codigo='taxa_condominial',valor=tx,origem=origin,descricao_original='Tx Cond'),
                        ItemComposicao(codigo='outros',valor=out,origem=origin,descricao_original='Outros'))),origens=(origin,)))
                original=dict(documento=values[0],vencimento=values[1],taxa_condominial=str(tx),outros=str(out),
                    total=str(total),responsavel=values[5],torre=values[6],apartamento=values[7],
                    inquilino=values[8],papel_inquilino='inquilino_nao_titular',acordo=values[9],
                    tipo=match[1],ordem=len(bills),ocorrencia=repetitions[key])
                notes.append(RessalvaLeitura(codigo='ITAJUBA_LANCAMENTO_ORIGINAL',gravidade='informativo',registro_id=rid,
                    origens=(origin,),valores_originais=(json.dumps(original,ensure_ascii=False),)))
                subtotal+=total;general+=total
        if not finished:falha('FECHAMENTO_GERAL_AUSENTE')
        for uid,nomes in names.items():
            if len(nomes)>1:
                notes.append(RessalvaLeitura(codigo='ITAJUBA_RESPONSAVEIS_DISTINTOS_NA_UNIDADE',registro_id=uid,
                    origens=(owners[uid].origem,),valores_originais=tuple(sorted(nomes))))
        return LoteCanonico(unidades=tuple(units.values()),pessoas=tuple(owners.values()),boletos=tuple(bills),ressalvas=tuple(notes))


def originais(lote):
    result={r.registro_id:json.loads(r.valores_originais[0])for r in lote.ressalvas if r.codigo=='ITAJUBA_LANCAMENTO_ORIGINAL'}
    if set(result)!={b.id for b in lote.boletos}:falha('PROVENIENCIA_INCOMPLETA')
    return result
