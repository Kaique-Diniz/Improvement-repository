"""Pequeno cenário criado do zero; não contém dados de clientes."""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from conversor.domain.template import Template


def pdf(paginas):
    writer = PdfWriter()
    for registros in paginas:
        page = writer.add_blank_page(width=1200, height=842)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),
            NameObject('/BaseFont'):NameObject('/Courier'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        commands = []
        for x,y,text in registros:
            escaped = text.encode('cp1252').replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
            commands.append(f'BT /F1 7 Tf 1 0 0 1 {x} {y} Tm '.encode()+b'('+escaped+b') Tj ET')
        stream=DecodedStreamObject();stream.set_data(b'\n'.join(commands))
        page[NameObject('/Contents')]=writer._add_object(stream)
    writer.add_metadata({'/Title':'EXEMPLO INTEGRALMENTE SINTETICO'})
    out=BytesIO();writer.write(out);return out.getvalue()


def documentos_demo():
    def lines(texts):return [(31,800-i*14,t) for i,t in enumerate(texts)]
    def footer(n,total):return [(31,58,'ADMINISTRADORA SINTETICA'),(31,24,f'{n} de {total}')]
    financeiro=pdf([
        lines(['W002A CONDOMINIO EDIFICIO PLAZA MAYOR IPIRANGA (9999)',
            'Inadimplência com composição','Posição em 21/10/2026','Venc. Comp. Cod. Descrição Valor Saldo',
            '0001 TORRE A - TITULAR SINTETICO','20/09/26 09/2026 900001 COTA 100,00 100,00',
            'DESCONTO (20,00) 80,00'])+footer(1,2),
        lines(['Emitido em 21/10/2026','FUNDO 5,00 85,00',
            '21/09/26 09/2026 900002 COTA 10,00 95,00',
            '0002 TORRE B - EMPRESA SINTETICA','19/09/26 09/2026 900003 COTA 40,00 40,00',
            '2 unidades inadimplentes (1,00%) 135,00'])+footer(2,2)])
    cadastro=pdf([[(31,810,'W045A CONDOMINIO EDIFICIO PLAZA MAYOR IPIRANGA (9999)'),
        (31,790,'Cadastro de unidades'),(31,770,'Unidade'),(91,770,'Nome/Telefone/Celular'),
        (241,770,'Tipo'),(346,770,'Endereço'),(534,770,'CPF/CNPJ'),(609,770,'E-mail'),
        (31,740,'0001 TORRE'),(31,730,'A'),(91,740,'TITULAR SINTETICO'),(241,740,'Proprietario'),
        (346,740,'Rua Ficticia, 1'),(534,740,'00000000191'),(609,740,'sintetico@example.invalid'),
        (31,690,'0002 TORRE'),(31,680,'B'),(91,690,'EMPRESA SINTETICA'),(241,690,'Proprietario'),
        (346,690,'Rua Ficticia, 2'),(534,690,'00000000000191'),(609,690,'empresa@example.invalid')]+footer(1,1)])
    book=Workbook();s=book.active;s.title='Dados'
    s.append(Template(id='demo',nome='demo',versao='1').cabecalhos_fisicos)
    for key,due,value in [('A/0001',date(2026,9,20),85),('B/0002',date(2026,9,19),40)]:
        row=['']*30;row[1]=key;row[28]=due;row[29]=value;s.append(row)
    row=['']*30;row[1]='A/0001';s.append(row)
    out=BytesIO();book.save(out);book.close()
    return {'inadimplencia':financeiro,'cadastro':cadastro,'referencia':out.getvalue()}
