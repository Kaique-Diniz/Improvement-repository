"""Fixtures criadas do zero para os layouts reais; nenhuma identidade ou fonte real."""
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def pdf_posicionado(paginas):
    writer=PdfWriter()
    for registros in paginas:
        page=writer.add_blank_page(width=1200,height=842)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),
            NameObject('/BaseFont'):NameObject('/Courier'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        commands=[]
        for x,y,text in registros:
            escaped=text.encode('cp1252').replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
            commands.append(f'BT /F1 7 Tf 1 0 0 1 {x} {y} Tm '.encode()+b'('+escaped+b') Tj ET')
        stream=DecodedStreamObject();stream.set_data(b'\n'.join(commands))
        page[NameObject('/Contents')]=writer._add_object(stream)
    writer.add_metadata({'/Title':'SINTETICO - NAO HOMOLOGADO PARA PRODUCAO'})
    out=BytesIO();writer.write(out);return out.getvalue()


def linhas(textos,*,inicio=800):
    return [(31, inicio-i*14, t)for i,t in enumerate(textos)]


def habita_paginas():
    cab=['Inadimplência Atualizada','Condominio: 9999 - CONDOMINIO SINTETICO',
         'Administradora: ADM-LAB','Codigo Condominio: 9999',
         'Bloco: DEP • Unidade: 000001 TITULAR SINTETICO CPF: 000.000.001-91',
         'Celular: (11) 90000-0001 E-mail: sintetico@example.invalid',
         'Boleto Vencimento Emissão Conta Histórico Valor Multa Atualização Monetária Juros Total']
    return [linhas(cab+['90000001 17/09/26 090926 94 COTA 100,00 2,00 3,00 4,00 109,00']),
            linhas(cab+['90000001 17/09/26 090926 1372 FUNDO 20,00 0,00 0,00 0,00 20,00',
                        'Total do boleto: 120,00 2,00 3,00 4,00 129,00',
                        'Total da Unidade: 120,00 2,00 3,00 4,00 129,00',
                        'Quantidade de unidades inadimplentes no condominio: 1 Total Geral: 120,00 2,00 3,00 4,00 129,00'])]


def rodape(numero,total):
    return [(31,58,'ADMINISTRADORA SINTETICA'),(31,50,'Rua Ficticia - endereco da administradora'),
            (31,41,'https://example.invalid'),(31,24,f'{numero} de {total}')]


def fl_paginas():
    return [linhas(['Emitido em 21/10/2026 10:00:00','W002A CONDOMINIO EDIFICIO SINTETICO (9999)',
        'Inadimplência com composição','Posição em 21/10/2026', 'Venc. Comp. Cod. Descrição Valor Saldo',
        '0001 TORRE A - TITULAR SINTETICO','17/09/26 09/2026 900001 COTA 100,00 100,00',
        '   DESCONTO (20,00) 80,00'])+rodape(1,2),
        linhas(['Emitido em 21/10/2026 10:00:00','   FUNDO 5,00 85,00',
        '18/09/26 09/2026 900002 COTA (DESCRICAO','EM OUTRA LINHA)', '10,00 95,00',
        'Data Motivo Detalhamento','21/10/2026 10:00 NOTA ADMINISTRATIVA',
        'Observacao do acordo R$ 123,00 sem lancamento.',
        '0002 TORRE B - EMPRESA SINTETICA','19/09/26 09/2026 900003 COTA 40,00 40,00',
        '2 unidades inadimplentes (1,00%) 135,00'])+rodape(2,2)]


def cadastro_paginas():
    return [[(31,810,'W045A CONDOMINIO EDIFICIO SINTETICO (9999)'),
        (31,790,'Cadastro de unidades'),(31,770,'Unidade'),(91,770,'Nome/Telefone/Celular'),
        (241,770,'Tipo'),(346,770,'Endereço'),(534,770,'CPF/CNPJ'),(609,770,'E-mail'),
        (31,740,'0001 TORRE'),(31,730,'A'),(91,740,'TITULAR SINTETICO'),(241,740,'Proprietario'),
        (346,740,'Rua Ficticia, 1'),(534,740,'00000000191'),(609,740,'sintetico@example.invalid')]
        +[(101.5 if y>24 else x,y,t)for x,y,t in rodape(1,2)],
        [(31,810,'Emitido em 21/10/2026 10:00:00'),(91,780,'+55 11 90000-0001'),
        (346,780,'BAIRRO FICTICIO - CIDADE FICTICIA - SP - 00000-000'),
        (31,750,'0002 TORRE'),(31,740,'B'),(91,750,'EMPRESA SINTETICA'),(241,750,'Proprietario'),
        (346,750,'Rua Ficticia, 2'),(534,750,'00000000000191'),(609,750,'empresa@example.invalid')]
        +[(101.5 if y>24 else x,y,t)for x,y,t in rodape(2,2)]]
