"""Planilhas integralmente sintéticas; estrutura comprovada, sem valores de clientes."""
from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
import pytest

from conversor.readers.bbz_xlsx import CABECALHO


def recibo(id='99000001',due=date(2026,8,26),componentes=None,marcador=None,encargos=('0','0','0'),emissao=date(2026,8,1)):
    return dict(id=id,due=due,componentes=componentes or [('COTA FICTICIA','100.00')],
                marcador=marcador,encargos=encargos,emissao=emissao)


def unidade(numero='000001',recibos=None,bloco='0'):
    return dict(numero=numero,bloco=bloco,nome='CONTATO INTEGRALMENTE FICTICIO / OUTRO CONTATO',recibos=recibos or [recibo()])


def planilha(unidades=None,codigo='287',nome='CONDOMINIO NOVA YORK PENTHOUSES',mutar=None):
    w=Workbook();s=w.active;s.title='RELATORIO SINTETICO'
    s.append(['Período de 01/01/2016 00:00:00 a 26/10/2026 23:59:59'])
    s.append([f'Condomínio: {codigo} - {nome}']);s.append([]);s.append([])
    totais=[];units=unidades or [unidade()]
    for u in units:
        s.append([f"Bloco: {u['bloco']} Unidade: {u['numero']} {u['nome']}"]);s.append(CABECALHO)
        subtotal=[Decimal(0)]*6
        for r in u['recibos']:
            soma=[Decimal(0)]*6
            for i,(desc,valor)in enumerate(r['componentes']):
                g=Decimal(valor);m,c,j=map(Decimal,r['encargos']if i==0 else('0','0','0'))
                vetor=[g,g,m,c,j,g+m+c+j]
                token=(r['marcador']+' 'if r['marcador']else'')+r['id']
                s.append([token,r['due']if i==0 else None,r['emissao']if i==0 else None,100+i,desc,'R$']+[float(v)for v in vetor])
                soma=[a+b for a,b in zip(soma,vetor)]
            s.append(['Total do Recibo:',None,None,None,None,'R$']+[float(v)for v in soma])
            subtotal=[a+b for a,b in zip(subtotal,soma)]
        s.append(['Total Geral da Unidade:',None,None,None,None,'R$']+[float(v)for v in subtotal]);totais.append(subtotal)
    total=[sum(v[i]for v in totais)for i in range(6)]
    s.append([f'Quantidade de unidade(s) em aberto: {len(units)}',None,None,None,'Total do condomínio :','R$']+[float(v)for v in total])
    if mutar:mutar(w,s)
    out=BytesIO();w.save(out);w.close();return out.getvalue()


@pytest.fixture
def xlsx():return planilha
