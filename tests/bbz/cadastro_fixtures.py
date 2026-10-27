"""PDFs desenhados do zero: nenhuma identidade ou contato de cliente."""
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from conversor.web.demo import pdf

NOME = 'CONTATO INTEGRALMENTE FICTICIO / OUTRO CONTATO'
CPF = '00000000191'
CNPJ = '00000000000191'
FISCAL = '00123456000149'
ENDERECO = 'Rua Inteiramente Ficticia 10 - Bairro Ficticio - Cidade Ficticia - SP - CEP: 00000-001'


def ficha(numero='000001',bloco='0',nome=NOME,documento=CPF,cliente='000099',contatos=None,
          locatario=False,pagador=False,observacao=None,segundo_documento=None):
    y=727;out=[(20,y,f'Bloco: {bloco}'),(161,y,f'Unidade: {numero} - {nome}'),(481,y,f'Código do cliente: {cliente}')]
    def row(*campos):
        nonlocal y
        y-=12;out.extend((x,y,s)for x,s in campos)
    def secao(s):row((240,s))
    secao('Endereço de cobrança');row((24,'A/C: DESTINATARIO FICTICIO'))
    row((24,'Endereço: Rua de Correspondencia 99 - Outro Bairro - Outra Cidade - RJ - CEP: 00000-002'))
    secao('Dados pessoais');row((24,'Tipo de pessoa: Física'),(217,('CNPJ'if len(documento)==14 else'CPF')+': '+documento))
    if segundo_documento:row((217,'CPF: '+segundo_documento))
    secao('Telefone/e-mail do cliente')
    for c in contatos or ['Celular - (11) 90000-0001','E-mail - titular@example.invalid']:row((24,c))
    if locatario:
        secao('Unidade alugada');row((24,'Locatário: 000088 - LOCATARIO TOTALMENTE FICTICIO'))
        row((398,'CPF: 00000000272'))
        secao('Telefone/e-mail de locatário');row((24,'Celular - 90000-0002'));row((24,'E-mail - locatario@example.invalid'))
    secao('Dados gerais')
    if pagador:
        secao('Dados do pagador');row((24,'Nome: PAGADOR TOTALMENTE FICTICIO'));row((398,'CPF: 00000000272'))
    else:
        row((24,'Dados do pagador'),(217,'Tipo de pessoa: Física'),(398,('CNPJ'if len(documento)==14 else'CPF')+': '+documento))
    row((24,'Observações: '+(observacao or 'TEXTO LIVRE FICTICIO SEM ATRIBUICAO DE IDENTIDADE')))
    return out


def dividir(rows,partes=2):
    header=[r for r in rows if r[1]==727];body=[r for r in rows if r[1]!=727]
    ys=sorted({y for x,y,s in body},reverse=True)
    chunks=[ys[i*len(ys)//partes:(i+1)*len(ys)//partes]for i in range(partes)]
    return [header+[r for r in body if r[1]in section]for section in chunks]


def cadastro(paginas=None,*,total=1,codigo='000287',nome='CONDOMINIO NOVA YORK PENTHOUSES',
             fiscal=FISCAL,mutar=None,protecao=None):
    paginas=paginas or [ficha()];pages=[]
    for i,body in enumerate(paginas,1):
        rows=[(190,800,'Relatório de Unidades - Completo'),(20,748,f'Condomínio: {codigo} - {nome}'),
              (468,748,'CNPJ: '+fiscal),(20,739,'Endereço: '+ENDERECO)]+list(body)
        if i==len(paginas):rows += [(20,96,'Quantidade de Unidade por tipo de endereçamento'),(20,70,f'Total de Unidade {total}')]
        rows.append((400,22,f'Emitido em 26/10/2026 12:00:00 - Página {i} de {len(paginas)}'))
        if mutar:rows=mutar(i,rows)
        pages.append(rows)
    reader=PdfReader(BytesIO(pdf(pages)));writer=PdfWriter()
    for page in reader.pages:
        page.mediabox.upper_right=(595.28,842);writer.add_page(page)
    if protecao:
        writer.encrypt(''if protecao!='senha'else'abertura_apenas_sintetica',
            permissions_flag=UserAccessPermissions.EXTRACT if protecao=='permitida'else UserAccessPermissions.PRINT)
    out=BytesIO();writer.write(out);return out.getvalue()
