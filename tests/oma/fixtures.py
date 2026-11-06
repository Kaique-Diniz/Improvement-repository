"""Documentos desenhados do zero, sem nomes, valores ou contatos de clientes."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from openpyxl import Workbook
from conversor.readers.oma_xlsx import CABECALHO
from tests.bbz.cadastro_fixtures import cadastro as pdf_base, ficha, dividir

REF = date(2026,10,13)
NOME = 'Pessoa Integralmente Ficticia'
CPF = '00000000191'


def recibo(id_='12345678 A', dias=61, componentes=None):
    return {'id':id_, 'vencimento':REF-timedelta(days=dias), 'componentes':componentes or [('DESPESA FICTICIA', '100.10','100.10','1.00','0.00','2.00')]}


def financeiro(grupos=None, *, resumo=True, mutar=None, nome='PARQUE SANTA MONICA'):
    grupos=grupos if grupos is not None else [('01','000001',NOME,[recibo()])]
    b=Workbook();s=b.active;s.title='Sheet'
    s.append(['','Inadimplência\nPosição em: 13/10/2026','']+[None]*9)
    s.append(['Condomínio: '+nome]);s.append(['Endereço: Rua Inteiramente Ficticia 42'])
    s.append(CABECALHO)
    unit_totals=[]
    def total(label,values):s.append(['']*5+[label]+[str(v) for v in values])
    for bloco,unidade,nome,receipts in grupos:
        s.append([f'Bloco {bloco} - Unidade {unidade} : {nome}'])
        unit=[Decimal(0)]*6
        for rec in receipts:
            subt=[Decimal(0)]*6
            for i,comp in enumerate(rec['componentes']):
                desc,*vals=comp
                v=[Decimal(str(x).replace(',','.')) for x in vals]
                vector=v+[sum(v[1:])]
                s.append([rec['id'] if i==0 else '',rec['vencimento'] if i==0 else '',
                    '202608' if i==0 else '',str(i+1),desc,'']+[str(x).replace('.',',') if x<0 else str(x) for x in vector])
                subt=[a+b for a,b in zip(subt,vector)]
            s.append(['']*4+['Total do recibo:','']+[str(x) for x in subt])
            unit=[a+b for a,b in zip(unit,subt)]
        total('Total da unidade:',unit);unit_totals.append(unit)
    grand=[sum(v[i] for v in unit_totals) for i in range(6)]
    total('Total acumulado:',grand)
    if resumo:
        for v in unit_totals:total('Total da unidade:',v)
        total('Total acumulado:',grand)
    if mutar:mutar(b,s)
    stream=BytesIO()
    try:b.save(stream);return stream.getvalue()
    finally:b.close()


def cadastro(paginas=None, *, total=1, mutar=None, **kw):
    if paginas is None:paginas=[ficha(bloco='01',numero='000001',nome=NOME,documento=CPF)]
    def changes(i,rows):
        rows=[(x,y,'Emitido em 17/09/2025 12:00:00'+t[t.index(' - Página '):]) if t.startswith('Emitido em ') else (x,y,t) for x,y,t in rows]
        return mutar(i,rows) if mutar else rows
    return pdf_base(paginas,total=total,codigo=kw.pop('codigo','0566'),
        nome=kw.pop('nome','COND. EDIF. PQ RESIDENCIAL SANTA MONICA'),mutar=changes,**kw)
