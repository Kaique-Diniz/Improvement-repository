"""Documentos inteiramente fictícios para o contrato BN Planner."""
from datetime import date,datetime,timedelta
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from pypdf import PdfReader,PdfWriter
from conversor.web.demo import pdf
from conversor.readers.itajuba_pdf import CABECALHO
from conversor.readers.itajuba_cadastro import CABECALHO as CAD_HEADER,TITULO

REF=date(2026,10,20)
NOME='Pessoa Integralmente Ficticia'
CPF='11144477735'
OUTRO_CPF='52998224725'


def linha(doc='Tt_T-01_A-01',dias=31,nome=NOME,tx='100.00',outros='5.00',inquilino='',acordo='0',vencimento=None):
    return dict(doc=doc,due=vencimento or REF-timedelta(days=dias),nome=nome,tx=Decimal(tx),outros=Decimal(outros),
        total=Decimal(tx)+Decimal(outros),inquilino=inquilino,acordo=acordo)


def brl(v):return format(v,'.2f').replace('.',',')


def financeiro(grupos=None,quebra=25,mutar=None,emissao=REF):
    grupos=grupos if grupos is not None else [('T-01','A-01',[linha()])]
    records=[];general=Decimal(0)
    for tower,apt,rows in grupos:
        subtotal=Decimal(0)
        for row in rows:
            records.append(('divida',dict(row,torre=tower,ap=apt)));subtotal+=row['total']
        records.append(('Total Unidade',subtotal));general+=subtotal
    records.append(('Total Geral',general))
    chunks=[records[i:i+quebra]for i in range(0,len(records),quebra)];pages=[]
    for pi,chunk in enumerate(chunks,1):
        content=[(165.45,580.35,'CONDOMINIO ITAJUBA'),(742.89,581.1,'Data'),(774.7,580.69,emissao.strftime('%d/%m/%y')),
            (261.21,532.75,'Lista de Ctas a Receber período de 01/12/23 a '+emissao.strftime('%d/%m/%y')),
            (489.45,7.26,'Página'),(525.45,6.85,str(pi)),(555.69,7.26,'de'),(0,0,str(len(chunks)))]
        if pi==1:
            xs=(22.2,88.4,203.7,281.9,373,398.7,535.5,575.1,618.3,773.7)
            content.extend((x,502.6,t)for x,t in zip(xs,CABECALHO));y=479.2
        else:y=513.78
        for kind,value in chunk:
            if kind=='divida':
                content.extend([(25.05,y,value['doc']),(116.08,y,value['due'].strftime('%d/%m/%Y')),
                    (209.4,y+1.44,brl(value['tx'])),(281.4,y+1.44,brl(value['outros'])),(366.36,y,brl(value['total'])),
                    (397.29,y,value['nome']),(535.53,y,value['torre']),(575.13,y,value['ap']),
                    (616.17,y,value['inquilino']),(785.96,y+1.44,value['acordo'])])
            else:
                content.extend([(117.21,y,kind),(364 if kind=='Total Unidade' else 267.8,y,brl(value))])
            y-=18
        if mutar:content=mutar(pi,content)
        pages.append(content)
    reader=PdfReader(BytesIO(pdf(pages)));writer=PdfWriter()
    for page in reader.pages:
        page.mediabox.upper_right=(862.45,616.45);writer.add_page(page)
    out=BytesIO();writer.write(out);return out.getvalue()


def ficha(torre='T-01',ap='A-01',nome=NOME,documento=CPF,telefone='90000-0001',celular='',email='titular@example.invalid',inad='999999.99'):
    return [torre,ap,nome,documento,telefone,celular,email,inad]


def cadastro(registros=None,mutar=None):
    b=Workbook();s=b.active;s.title='Sheet1';b.properties.created=b.properties.modified=datetime(2000,1,1)
    s.append([TITULO]);s.append(CAD_HEADER)
    for row in registros if registros is not None else [ficha()]:s.append(row)
    if mutar:mutar(b,s)
    out=BytesIO()
    try:b.save(out);return out.getvalue()
    finally:b.close()
