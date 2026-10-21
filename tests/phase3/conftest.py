from datetime import date
from hashlib import sha256

import pytest

from conversor.domain.catalog import Catalogo
from conversor.readers.contracts import FonteProtegida
from conversor.readers.operational import ContextosCatalogo, RegistroLeitores
from examples.fase2.gerar_demo import pdf_sintetico


@pytest.fixture
def fontes_sinteticas():
    habita = "Inadimplencia Atualizada\nCondominio: 9999 - LAB\nAdministradora: ADM-LAB\nCodigo Condominio: 9999\n"
    fl = "FL CONDOMINIOS - Relatorio W002A\nW002A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\nInadimplencia com composicao\n"
    textos = {
        "habita": [habita + "Bloco: DEP  Unidade: 000001  TITULAR SINTETICO  CPF: (ausente)\n"
            "10000001  17/09/26  202609  94  COTA 100,00 2,00 1,00 103,00\n--- CONTINUA NA PAGINA SEGUINTE ---",
            habita + "CONTINUACAO DO BOLETO 10000001 DA UNIDADE DEP-000001\n"
            "1372 FUNDO 20,00 0,00 0,00 20,00\nTotal do boleto: 120,00 2,00 1,00 123,00\nTotal da Unidade: 120,00 2,00 1,00 123,00"],
        "fl": [fl + "0001 TORRE A - TITULAR SINTETICO\nVenc. Comp. Cod. Descricao Valor Saldo\n"
            "17/09/26 09/2026 900001 COTA 200,00 200,00\n--- CONTINUA NA PAGINA 2 ---",
            fl + "CONTINUACAO DO BOLETO 900001 - 0001 TORRE A\nDESCONTO (20,00) 180,00\nFIM DO RELATORIO: 1 UNIDADES E 1 BOLETOS"],
        "cadastro": ["W045A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\n"
            "0001 TORRE A  TITULAR SINTETICO  Proprietario  Rua Exemplo, 1  (vazio)  fase3@example.invalid\n+55 11 90000-0001"],
    }
    return {k: pdf_sintetico(v) for k, v in textos.items()}


@pytest.fixture
def catalogo_leitura():
    dados = {k: [] for k in ("administradoras", "condominios", "formatos", "perfis_condominio", "regras_cobranca", "templates")}
    dados["administradoras"] = [{"id": "adm", "nome": "ADM SINTETICA"}]
    dados["templates"] = [{"id": "tpl", "nome": "Universal", "versao": "1"}]
    for familia, leitor, codigo in (("habita", "habita_composicao_sintetico_v1", "9999"),
        ("fl", "fl_composicao_sintetico_v1", "LAB"), ("cadastro", "cadastro_fl_sintetico_v1", "LAB_CAD")):
        dados["formatos"].append({"id": "fmt_" + familia, "nome": familia, "versao": "1", "tipo_arquivo": "pdf_texto",
            "leitor_id": leitor, "administradora_ids": ["adm"], "marcadores": ["sintetico", "teste"]})
        dados["condominios"].append({"id": "cond_" + familia, "nome": "CONDOMINIO SINTETICO", "administradora_id": "adm",
            "codigo_na_administradora": codigo, "perfil_version_id": "perfil_" + familia,
            "formato_ids": ["fmt_" + familia], "vinculos": [{"administradora_id": "adm", "inicio": "2026-01-01"}]})
        dados["perfis_condominio"].append({"id": "perfil_" + familia, "versao": "1", "condominio_id": "cond_" + familia,
            "template_id": "tpl", "regra_id": "regra_" + familia, "cadastro_antecipado": False, "codificador_cedente": "pendente"})
        dados["regras_cobranca"].append({"id": "regra_" + familia, "condominio_id": "cond_" + familia, "versao": "1", "vigente_de": "2026-01-01"})
    # Cadastro e inadimplência compartilham o condomínio/chave real do teste.
    dados["condominios"][1]["formato_ids"].append("fmt_cadastro")
    return Catalogo.model_validate(dados)


@pytest.fixture
def memoria_fontes(fontes_sinteticas):
    class Memoria:
        def ler(self, fonte):
            return fontes_sinteticas[fonte.arquivo_id]
    return Memoria()


@pytest.fixture
def registro(catalogo_leitura, memoria_fontes):
    return RegistroLeitores(memoria_fontes, ContextosCatalogo(catalogo_leitura, date(2026, 10, 20)))


@pytest.fixture
def fonte(fontes_sinteticas):
    def criar(id_):
        return FonteProtegida(arquivo_id=id_, sha256=sha256(fontes_sinteticas[id_]).hexdigest())
    return criar
