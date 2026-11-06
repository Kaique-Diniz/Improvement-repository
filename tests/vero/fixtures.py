"""Fontes inteiramente fictícias, desenhadas do zero para a gramática Lello."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter

from conversor.readers.vero_xlsx import CABECALHO, COMPONENTES, EMPRESA
from conversor.web.demo import pdf

REF = date(2026,11,6)
NOME = 'Pessoa Integralmente Ficticia'
CPF = '11144477735'
OUTRO_CPF = '52998224725'
CNPJ = '11222333000181'


def recibo(codigo=900001,dias=31,componentes=None):
    return {'codigo':codigo,'vencimento':REF-timedelta(days=dias),
        'componentes':componentes if componentes is not None else [(1,'DESPESA FICTICIA','100.10'),(2,'MEMORIA FICTICIA',None)]}


def financeiro(grupos=None,mutar=None):
    grupos = grupos if grupos is not None else [('A00004',NOME,[recibo()])]
    b=Workbook();s=b.active;s.title='Planilha1'
    b.properties.created=b.properties.modified=datetime(2000,1,1)
    s.append(['Cota']);s.append(['* PDF * Email * XLS']);total=[Decimal(0)]*4
    for unit,name,receipts in grupos:
        s.append(['Empresa',EMPRESA])
        s.append(['Referência','10888 - VERO ENCANTO'])
        s.append(['Unidade',unit+' - '+name]);s.append(['Multicontas','NÃO'])
        for r in receipts:
            original=sum(Decimal(v)for _,_,v in r['componentes']if v is not None)
            values=[original,Decimal('1.00'),Decimal('2.00'),original+3]
            s.append(CABECALHO);s.append([r['codigo'],r['vencimento']]+[str(x)for x in values])
            s.append(COMPONENTES)
            for code,history,value in r['componentes']:s.append([None,code,history,None,value,None])
            s.append([]);total=[a+b for a,b in zip(total,values)]
    s.append(['Total de Débitos',None]+[str(x)for x in total])
    if mutar:mutar(b,s)
    out=BytesIO()
    try:b.save(out);return out.getvalue()
    finally:b.close()


def participante(nome=NOME,documento=CPF,tipo='Física',participacao='100,00',segundo_documento=None):
    return dict(nome=nome,documento=documento,tipo=tipo,participacao=participacao,segundo_documento=segundo_documento)


def ficha(codigo='A00004',pessoas=None,*,torre=None):
    pessoas=pessoas if pessoas is not None else [participante()]
    y=720;rows=[(158,y+13,'Bloco'),(422,y+13,'Unidade'),(32,y,'TORRE '+(torre or codigo[0])),(309,y,codigo)]
    y-=13;rows.extend([(32,y,'Tipo Cobrança:'),(143,y,'FICTICIA')])
    for p in pessoas:
        y-=13;rows.append((32,y,'Condômino'))
        y-=13;rows.extend([(32,y,'Nome'),(143,y,p['nome']),(309,y,'Tipo de pessoa:'),(394,y,p['tipo'])])
        y-=13;rows.extend([(32,y,'CPF'),(143,y,p['documento'] if p['tipo']=='Física' else ''),(309,y,'RG')])
        y-=13;rows.extend([(32,y,'CNPJ'),(143,y,p['documento'] if p['tipo']=='Jurídica' else (p['segundo_documento'] or '')),(309,y,'% de participação'),(394,y,p['participacao'])])
        y-=13;rows.extend([(32,y,'Entrega de correspondência'),(143,y,'FICTICIA'),(309,y,'E-mail'),(394,y,'titular@example.invalid')])
        y-=13;rows.extend([(32,y,'Enviar para o Dataflex?'),(143,y,'Sim'),(309,y,'E-mail boleto'),(394,y,'boleto@example.invalid')])
        y-=13;rows.extend([(32,y,'Endereço'),(143,y,'Rua Totalmente Ficticia 42')])
        y-=13;rows.extend([(32,y,'Bairro'),(143,y,'Bairro Ficticio'),(309,y,'Cidade'),(394,y,'Cidade Ficticia')])
        y-=13;rows.extend([(32,y,'Estado'),(143,y,'SP'),(309,y,'País'),(394,y,'Brasil')])
        y-=13;rows.extend([(32,y,'CEP'),(143,y,'00000-001'),(309,y,'Telefone'),(394,y,'90000-0001')])
        y-=13;rows.extend([(32,y,'Aos cuidados de'),(143,y,'Terceiro Integralmente Ficticio')])
        y-=13;rows.extend([(32,y,'Telefone A/C'),(143,y,'(22) 90000-0002'),(309,y,'Celular A/C'),(394,y,'(33) 90000-0003')])
    return rows


def cadastro(paginas=None,referencia='10888-10',nome='PROJETO IMOBILIARIO DI 31 I VERO ENCANTO',mutar=None):
    pages=[]
    for i,body in enumerate(paginas if paginas is not None else [ficha()]):
        rows=([(32,802,'Dados do condomínio'),(32,788,'Referência'),(105,788,referencia),
            (301,788,'Nome'),(373,788,nome),(32,775,'Endereço'),(105,775,'Rua Ficticia 42')]+list(body)) if i==0 else list(body)
        if mutar:rows=mutar(i,rows)
        pages.append(rows)
    reader=PdfReader(BytesIO(pdf(pages)));writer=PdfWriter()
    for page in reader.pages:
        page.mediabox.upper_right=(595,842);writer.add_page(page)
    out=BytesIO();writer.write(out);return out.getvalue()
