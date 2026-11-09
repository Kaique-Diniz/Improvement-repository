"""Fontes criadas do zero. Pessoas e contatos inteiramente fictícios."""
from datetime import date,timedelta
from decimal import Decimal
from io import BytesIO
from openpyxl import Workbook
from conversor.readers.beach_parque_xlsx import CABECALHO
from tests.bbz.cadastro_fixtures import cadastro as pdf_base, ficha, dividir

REF=date(2026,10,16)
NOME='PESSOA INTEGRALMENTE FICTICIA'
CPF='00000000191'


def recibo(id_='12345678',dias=31,componentes=None):
    return dict(id=id_,vencimento=REF-timedelta(days=dias),componentes=componentes or [('DESPESA FICTICIA','100.10','100.10','1.00','2.00','3.00')])


def financeiro(grupos=None,*,mutar=None):
    grupos=grupos if grupos is not None else [('A','A00001',NOME,[recibo()])]
    w=Workbook();s=w.active;s.title='relatorio (4)'
    s.append(['Período de 01/01/1900 00:00:00 a 16/10/2026 09:11:39'])
    s.append(['Condomínio: 3075 - TERRAÇO BEACH PARQUE'])
    s.append([]);s.append([]);gerais=[]
    def fechar(label,vals):s.append([label,None,None,None,None,'R$']+[str(x)for x in vals])
    for bloco,unidade,nome,recs in grupos:
        s.append([f'Bloco: {bloco} Unidade: {unidade} {nome}']);s.append(CABECALHO)
        uni=[Decimal(0)]*6
        for rec in recs:
            totais=[Decimal(0)]*6
            for i,c in enumerate(rec['componentes']):
                desc,*vals=c;v=[Decimal(x)for x in vals];v.append(sum(v[1:]))
                s.append([rec['id'],rec['vencimento']if i==0 else None,202608 if i==0 else None,'1.01',desc,'R$']+[str(x)for x in v])
                totais=[a+b for a,b in zip(totais,v)]
            fechar('Total do Recibo:',totais);uni=[a+b for a,b in zip(uni,totais)]
        fechar('Total Geral da Unidade:',uni);gerais.append(uni)
    grand=[sum(u[i]for u in gerais)for i in range(6)]
    s.append([f'Quantidade de unidade(s) em aberto: {len(grupos)}',None,None,None,'Total do condomínio :','R$']+[str(x)for x in grand])
    if mutar:mutar(w,s)
    stream=BytesIO()
    try:w.save(stream);return stream.getvalue()
    finally:w.close()


def cadastro(paginas=None,*,total=1,mutar=None,codigo='3075',nome='TERRAÇO BEACH PARQUE'):
    paginas=paginas if paginas is not None else [ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF)]
    def changes(i,rows):
        # Esta família não imprime documento fiscal no cabeçalho.
        rows=[(x,y,t)for x,y,t in rows if not(y==748 and t.startswith('CNPJ:'))]
        rows=[(x,y,'Emitido em 22/01/2025 11:00:00'+t[t.index(' - Página '):])if t.startswith('Emitido em ')else(x,y,t)for x,y,t in rows]
        return mutar(i,rows)if mutar else rows
    return pdf_base(paginas,total=total,codigo=codigo,nome=nome,mutar=changes)
