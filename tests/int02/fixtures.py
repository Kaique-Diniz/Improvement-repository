"""Composição de fontes fictícias aprovadas; nenhuma fonte privada é usada."""
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from tests.passaredo import fixtures as tab
from tests.oma import fixtures as oma
from tests.vero import fixtures as vero
from tests.itajuba import fixtures as itj
from tests.beach_parque import fixtures as bpq

PERFIS=('passaredo','forest_hill','parque_santa_monica','vero_encanto','itajuba','terraco_beach_parque')
NOME='Pessoa Integralmente Ficticia'
CPF='00000000191'

@dataclass(frozen=True)
class Caso:
    perfil: str
    financeiro: bytes
    cadastro: bytes
    ref: date
    prazo: int
    valor: str
    ext: str
    ext_cad: str


def caso(perfil, *, dias=None, nome=NOME, nome_cad=NOME, documento=CPF):
    prazo=60 if perfil in('passaredo','parque_santa_monica')else 30
    dias=dias if dias is not None else(prazo+1,prazo,prazo-1)
    if perfil in('passaredo','forest_hill'):
        unidade='007'if perfil=='passaredo'else'AV.P02 231'
        raw=tab.financeiro([tab.debito(unidade=unidade,nome=nome,dias=d)for d in dias])
        cad=tab.cadastro([tab.ficha(unidade=unidade,nome=nome_cad,documento=documento)])
        return Caso(perfil,raw,cad,tab.REF,prazo,'100.10','xlsx','xlsx')
    if perfil=='parque_santa_monica':
        raw=oma.financeiro([('01','000001',nome,[oma.recibo(str(900000+i),d)for i,d in enumerate(dias)])])
        cad=oma.cadastro([oma.ficha(bloco='01',numero='000001',nome=nome_cad,documento=documento)])
        return Caso(perfil,raw,cad,oma.REF,prazo,'100.10','xlsx','pdf')
    if perfil=='vero_encanto':
        raw=vero.financeiro([('A00004',nome,[vero.recibo(900000+i,d)for i,d in enumerate(dias)])])
        cad=vero.cadastro([vero.ficha(pessoas=[vero.participante(nome=nome_cad,documento=documento)])])
        return Caso(perfil,raw,cad,vero.REF,prazo,'100.10','xlsx','pdf')
    if perfil=='itajuba':
        raw=itj.financeiro([('T-01','A-01',[itj.linha(doc=f'Tt_ficticio_{i}',dias=d,nome=nome)for i,d in enumerate(dias)])],quebra=2)
        cad=itj.cadastro([itj.ficha(nome=nome_cad,documento=documento)])
        return Caso(perfil,raw,cad,itj.REF,prazo,'105.00','pdf','xlsx')
    if perfil=='terraco_beach_parque':
        raw=bpq.financeiro([('A','A00001',nome,[bpq.recibo(str(900000+i),d)for i,d in enumerate(dias)])])
        cad=bpq.cadastro([bpq.ficha(bloco='A',numero='A00001',nome=nome_cad,documento=documento)])
        return Caso(perfil,raw,cad,bpq.REF,prazo,'100.10','xlsx','pdf')
    raise ValueError('PERFIL_DE_TESTE_DESCONHECIDO')


def homologar(monkeypatch, casos):
    from conversor.web.service import PERFIS as CONFIG
    for c in casos:
        for role,raw in(('inadimplencia',c.financeiro),('cadastro',c.cadastro)):
            monkeypatch.setitem(CONFIG[c.perfil]['fontes_homologacao_sha256'],role,sha256(raw).hexdigest())
