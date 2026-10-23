"""Regressão do contrato comum com o pacote local sintético, sem aplicar cobrança."""
from decimal import Decimal
from hashlib import sha256
import json

import pytest

from conversor.application.reading import resultado_leitura
from conversor.readers.contracts import FonteProtegida, Leitor
from conversor.readers.operational import RegistroLeitores
from conversor.readers.text_support import ContextoLeitura
from .pacote_suite import pacote, CONFIG


@pytest.fixture(scope="session")
def lotes_comuns(pacote):
    config = json.loads(CONFIG.read_text())
    fontes, contextos = {}, {}
    for caso in config["casos"]:
        id_ = caso["familia"]
        fontes[id_] = (pacote / caso["arquivo"]).read_bytes()
        contextos[id_] = ContextoLeitura(caso["condominio_id"], caso["administradora_id"], caso["formato_id"],
            id_, caso["codigo_condominio_leitor"], leitor_versao=caso["formato_id"] + "@1")
        if caso.get("cadastro"):
            fontes["cadastro"] = (pacote / caso["cadastro"]).read_bytes()
            contextos["cadastro"] = ContextoLeitura(caso["condominio_id"], caso["administradora_id"], "cadastro_fl_sintetico_v1",
                "cadastro", caso["codigo_condominio_leitor"], leitor_versao="cadastro_fl_sintetico_v1@1")
    class Memoria:
        def ler(self, fonte): return fontes[fonte.arquivo_id]
    class Contextos:
        def resolver(self, fonte, **kwargs): return contextos[fonte.arquivo_id]
    registro = RegistroLeitores(Memoria(), Contextos())
    lotes = {}
    for id_, contexto in contextos.items():
        leitor = registro.obter(contexto.formato_id, "1")
        assert isinstance(leitor, Leitor)
        fonte = FonteProtegida(arquivo_id=id_, sha256=sha256(fontes[id_]).hexdigest())
        lotes[id_] = leitor.ler(fonte, formato_id=contexto.formato_id, condominio_id=contexto.condominio_id)
    return lotes


@pytest.mark.parametrize("familia,unidades,boletos", [("habita", 4, 6), ("fl", 4, 5), ("cadastro", 4, 0)])
def test_contrato_comum_dos_tres_documentos(lotes_comuns, familia, unidades, boletos):
    lote = lotes_comuns[familia]
    assert len(lote.unidades) == len(lote.pessoas) == unidades
    assert len(lote.boletos) == boletos


@pytest.mark.parametrize("familia,numero,paginas,total", [("habita", "80000105", {2, 3}, "340.00"),
    ("fl", "900104", {1, 2}, "680.00")])
def test_continuidades_pelo_contrato_comum(lotes_comuns, familia, numero, paginas, total):
    encontrados = [b for b in lotes_comuns[familia].boletos if b.identificador == numero]
    assert len(encontrados) == 1
    assert {o.pagina for o in encontrados[0].origens} == paginas
    assert encontrados[0].composicao.total_original == Decimal(total)


def test_cadastro_e_financeiro_pareaveis_sem_resolver_titular(lotes_comuns):
    ids_financeiro = {u.id for u in lotes_comuns["fl"].unidades}
    assert {u.id for u in lotes_comuns["cadastro"].unidades} == ids_financeiro
    # A divergência intencional de titular não é resolvida pelo adapter de leitura.
    origem = {p.unidade_id: p.nome for p in lotes_comuns["fl"].pessoas}
    cadastro = {p.unidade_id: p.nome for p in lotes_comuns["cadastro"].pessoas}
    assert sum(origem[id_] != cadastro[id_] for id_ in ids_financeiro) == 1


def test_alertas_sem_bloqueio_nem_regua(lotes_comuns):
    resultado = resultado_leitura(lotes_comuns["cadastro"], processamento_id="teste_fase3")
    assert len(resultado.ocorrencias) == 4
    assert all(not o.bloqueante for o in resultado.ocorrencias)
    assert resultado.lote.boletos == ()
