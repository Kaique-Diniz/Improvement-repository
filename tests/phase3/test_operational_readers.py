from datetime import date
from decimal import Decimal
from hashlib import sha256

import pytest

from conversor.application.ports import Estado
from conversor.application.reading import LerDocumento, resultado_leitura
from conversor.adapters.document_probe import SondadorLocal
from conversor.application.recognition import ReconhecerDocumento
from conversor.domain.catalog import Catalogo
from conversor.domain.recognition import CatalogoAssinaturas, ResultadoReconhecimento
from conversor.readers.contracts import FonteProtegida, Leitor
from conversor.readers.operational import ContextosCatalogo, RegistroLeitores, validar_assinatura_para_leitura
from conversor.readers.text_support import ErroLeitura
from examples.fase2.gerar_demo import pdf_sintetico


@pytest.mark.parametrize("familia,leitor,valor", [("habita", "habita_composicao_sintetico_v1", "120.00"),
    ("fl", "fl_composicao_sintetico_v1", "180.00"), ("cadastro", "cadastro_fl_sintetico_v1", None)])
def test_tres_leitores_mesmo_protocolo_e_modelo(registro, fonte, familia, leitor, valor):
    adapter = registro.obter(leitor, "1")
    assert isinstance(adapter, Leitor)
    condominio = "cond_fl" if familia == "cadastro" else "cond_" + familia
    lote = adapter.ler(fonte(familia), formato_id="fmt_" + familia, condominio_id=condominio)
    assert len(lote.unidades) == len(lote.pessoas) == 1
    assert lote.unidades[0].condominio_id == condominio
    assert lote.pessoas[0].unidade_id == lote.unidades[0].id
    assert lote.unidades[0].origem.sha256 == fonte(familia).sha256
    assert lote.unidades[0].origem.leitor_versao == leitor + "@1"
    if valor:
        assert len(lote.boletos) == 1
        b = lote.boletos[0]
        assert b.composicao.total_original == Decimal(valor)
        assert {o.pagina for o in b.origens} == {1, 2}
        assert any(o.continuacao_de for o in b.origens)
    else:
        assert lote.boletos == ()


def test_cadastro_e_financeiro_mesma_chave_de_unidade(registro, fonte):
    financeiro = registro.obter("fl_composicao_sintetico_v1", "1").ler(fonte("fl"), formato_id="fmt_fl", condominio_id="cond_fl")
    cadastro = registro.obter("cadastro_fl_sintetico_v1", "1").ler(fonte("cadastro"), formato_id="fmt_cadastro", condominio_id="cond_fl")
    assert financeiro.unidades[0].id == cadastro.unidades[0].id
    assert financeiro.unidades[0].chave_normalizada == cadastro.unidades[0].chave_normalizada


@pytest.mark.parametrize("leitor,versao", [("nao_registrado", "1"), ("habita_composicao_sintetico_v1", "2")])
def test_sem_import_dinamico_ou_fallback(registro, leitor, versao):
    with pytest.raises(ErroLeitura, match="LEITOR_OU_VERSAO_NAO_REGISTRADO"):
        registro.obter(leitor, versao)


def test_hash_e_verificado_mesmo_se_porta_de_fonte_nao_verificar(registro):
    with pytest.raises(ErroLeitura, match="HASH_FONTE_DIVERGENTE"):
        registro.obter("habita_composicao_sintetico_v1", "1").ler(
            FonteProtegida(arquivo_id="habita", sha256="0" * 64), formato_id="fmt_habita", condominio_id="cond_habita")


@pytest.mark.parametrize("formato,condominio,codigo", [("fmt_fl", "cond_habita", "CONTEXTO_DE_LEITURA_INCOMPATIVEL"),
    ("fmt_inexistente", "cond_fl", "CONTEXTO_DE_LEITURA_INCOMPATIVEL"),
    ("fmt_fl", "cond_fl", "LEITOR_DIVERGENTE_DO_CONTEXTO")])
def test_identidade_e_leitor_incompativeis_bloqueiam(registro, fonte, formato, condominio, codigo):
    with pytest.raises(ErroLeitura, match=codigo):
        registro.obter("habita_composicao_sintetico_v1", "1").ler(fonte("habita"), formato_id=formato, condominio_id=condominio)


@pytest.mark.parametrize("paginas,codigo", [(["texto desconhecido"], "FORMATO_DESCONHECIDO"),
    (["Inadimplencia Atualizada\nBloco: Unidade:\nInadimplencia com composicao Venc. Comp. Saldo"], "FORMATO_AMBIGUO"),
    (["Inadimplencia com composicao Venc. Comp. Saldo"], "FORMATO_DIVERGENTE_DO_LEITOR"),
    (["Inadimplencia AtualizadaX Bloco: Unidade:"], "FORMATO_DESCONHECIDO")])
def test_assinaturas_sem_presuncao(paginas, codigo):
    with pytest.raises(ErroLeitura, match=codigo):
        validar_assinatura_para_leitura(pdf_sintetico(paginas), "habita_composicao_sintetico_v1")


def test_cpf_ausente_alerta_nao_bloqueia_leitura(registro, fonte):
    lote = registro.obter("habita_composicao_sintetico_v1", "1").ler(fonte("habita"), formato_id="fmt_habita", condominio_id="cond_habita")
    r = resultado_leitura(lote, processamento_id="exec_sintetica")
    assert len(r.ocorrencias) == 1
    assert not r.ocorrencias[0].bloqueante
    assert r.ocorrencias[0].codigo == "CPF_AUSENTE_OU_INVALIDO"
    assert len(r.lote.boletos) == 1


def reconhecer_artificial(catalogo, fonte, conteudo):
    # Aprovação artificial de fixture; jamais usada em catálogo operacional real.
    aprovacao = {"responsavel_id": "teste", "evidencia_id": "sintetica", "em": "2026-10-21T00:00:00Z"}
    dados = catalogo.model_dump(mode="json")
    dados["formatos"][0].update(status="validado", aprovacao=aprovacao)
    dados["perfis_condominio"][0].update(status="aprovado", aprovacao=aprovacao)
    dados["regras_cobranca"][0].update(status="aprovada", aprovacao=aprovacao,
        fonte={"arquivo_id": fonte.arquivo_id, "sha256": fonte.sha256, "leitor_versao": "fixture", "pagina": 1, "identificador": "fixture"},
        condicoes=[{"campo": "fixture", "operador": "igual", "valor": "somente_teste", "alcance": "boleto", "acao": "alertar", "prioridade": 0}])
    cat = Catalogo.model_validate(dados)
    estado = Estado(revisao=1, catalogo=cat)
    class Repo:
        def carregar(self): return estado
    assinaturas = CatalogoAssinaturas.model_validate({"versao": "fixture", "status": "homologado", "aprovacao": aprovacao,
        "layouts": [{"id": "sig", "versao": "1", "formato_id": "fmt_habita", "minimo_pontos": 2,
                     "marcadores": [{"id": "m1", "texto": "Inadimplencia Atualizada"}, {"id": "m2", "texto": "Bloco:"}]}],
        "administradoras": [{"administradora_id": "adm", "identificadores": [{"id": "adm", "rotulo": "Administradora", "valor": "ADM-LAB"}]}],
        "condominios": [{"condominio_id": "cond_habita", "identificadores": [{"id": "cond", "rotulo": "Codigo Condominio", "valor": "9999"}]}]})
    class Assinaturas:
        def carregar(self): return assinaturas
    r = ReconhecerDocumento(Repo(), Assinaturas()).executar(SondadorLocal().sondar(conteudo, arquivo_id=fonte.arquivo_id), data_ref=date(2026, 10, 20))
    assert r.pronto_para_proxima_etapa
    return Repo(), Assinaturas(), r


def test_caso_de_uso_com_reconhecimento_e_contrato_comum(catalogo_leitura, memoria_fontes, fonte):
    repo, assinaturas, r = reconhecer_artificial(catalogo_leitura, fonte("habita"), memoria_fontes.ler(fonte("habita")))
    resultado = LerDocumento(repo, memoria_fontes, assinaturas).executar(fonte("habita"), r, processamento_id="exec")
    assert resultado.lote.boletos[0].composicao.total_original == Decimal("120.00")


@pytest.mark.parametrize("falha,codigo", [("bloqueado", "RECONHECIMENTO_BLOQUEIA_LEITURA"),
    ("tipo", "TIPO_NAO_SUPORTADO_PELO_LEITOR"),
    ("arquivo", "FONTE_DIFERE_DO_RECONHECIMENTO"), ("hash", "FONTE_DIFERE_DO_RECONHECIMENTO"),
    ("revisao", "CATALOGO_DIFERE_DO_RECONHECIMENTO"), ("catalogo", "CATALOGO_DIFERE_DO_RECONHECIMENTO"),
    ("assinaturas", "ASSINATURAS_DIFEREM_DO_RECONHECIMENTO"), ("versao_assinaturas", "ASSINATURAS_DIFEREM_DO_RECONHECIMENTO")])
def test_reconhecimento_obsoleto_ou_bloqueado_nao_avanca(catalogo_leitura, memoria_fontes, fonte, falha, codigo):
    repo, assinaturas, r = reconhecer_artificial(catalogo_leitura, fonte("habita"), memoria_fontes.ler(fonte("habita")))
    mudanca = {"bloqueado": {"bloqueios": ["REGRA_NAO_APROVADA"], "bloqueante": True, "pronto_para_proxima_etapa": False},
        "tipo": {"tipo": "xlsx"},
        "arquivo": {"arquivo_id": "outra_fonte"}, "hash": {"arquivo_hash": "1" * 64},
        "revisao": {"catalogo_revisao": 2}, "catalogo": {"catalogo_hash": "2" * 64},
        "assinaturas": {"assinaturas_hash": "3" * 64}, "versao_assinaturas": {"assinaturas_versao": "outra"}}[falha]
    r = ResultadoReconhecimento.model_validate(r.model_dump() | mudanca)
    with pytest.raises(ErroLeitura, match=codigo):
        LerDocumento(repo, memoria_fontes, assinaturas).executar(fonte("habita"), r, processamento_id="exec")


def test_contexto_preserva_administradora_historica(catalogo_leitura, fonte):
    dados = catalogo_leitura.model_dump(mode="json")
    dados["administradoras"].append({"id": "adm_nova", "nome": "SINTETICA NOVA"})
    dados["formatos"][0]["administradora_ids"].append("adm_nova")
    dados["condominios"][0].update(administradora_id="adm_nova", vinculos=[
        {"administradora_id": "adm", "inicio": "2026-01-01", "fim": "2026-10-01"},
        {"administradora_id": "adm_nova", "inicio": "2026-10-01"}])
    catalogo = Catalogo.model_validate(dados)
    ctx = ContextosCatalogo(catalogo, date(2026, 9, 20)).resolver(fonte("habita"), formato_id="fmt_habita", condominio_id="cond_habita")
    assert ctx.administradora_id == "adm"


def test_mesmo_adapter_atende_outro_condominio_sem_duplicar_leitor(catalogo_leitura, fontes_sinteticas):
    dados = catalogo_leitura.model_dump(mode="json")
    condo = dict(dados["condominios"][0]) | {"id": "cond_habita_2", "codigo_na_administradora": "8888", "perfil_version_id": "perfil_2"}
    dados["condominios"].append(condo)
    dados["perfis_condominio"].append(dict(dados["perfis_condominio"][0]) | {"id": "perfil_2", "condominio_id": "cond_habita_2", "regra_id": "regra_2"})
    dados["regras_cobranca"].append(dict(dados["regras_cobranca"][0]) | {"id": "regra_2", "condominio_id": "cond_habita_2"})
    cat = Catalogo.model_validate(dados)
    original = fontes_sinteticas["habita"]
    outro = original.replace(b"9999", b"8888")  # PDF sintético sem compressão, comprimentos idênticos.
    class Fontes:
        def ler(self, fonte): return original if fonte.arquivo_id == "primeiro" else outro
    reg = RegistroLeitores(Fontes(), ContextosCatalogo(cat, date(2026, 10, 20)))
    leitor = reg.obter("habita_composicao_sintetico_v1", "1")
    lotes = [leitor.ler(FonteProtegida(arquivo_id=id_, sha256=sha256(b).hexdigest()), formato_id="fmt_habita", condominio_id=c)
        for id_, b, c in (("primeiro", original, "cond_habita"), ("segundo", outro, "cond_habita_2"))]
    assert lotes[0].unidades[0].id != lotes[1].unidades[0].id
    assert lote_valores(lotes[0]) == lote_valores(lotes[1])
    assert reg.obter("habita_composicao_sintetico_v1", "1") is leitor


def lote_valores(lote):
    return tuple(b.composicao.total_original for b in lote.boletos)


def test_proveniencia_corrompida_no_adapter_bloqueia(registro, fonte, monkeypatch):
    from conversor.readers.habita import LeitorHabitaSintetico
    from conversor.domain.canonical import LoteCanonico
    original = LeitorHabitaSintetico.ler
    def corromper(self, *args, **kwargs):
        dados = original(self, *args, **kwargs).model_dump()
        dados["boletos"][0]["composicao"]["itens"][0]["origem"]["sha256"] = "0" * 64
        return LoteCanonico.model_validate(dados)
    monkeypatch.setattr(LeitorHabitaSintetico, "ler", corromper)
    with pytest.raises(ErroLeitura, match="PROVENIENCIA_DE_LEITURA_INCONSISTENTE"):
        registro.obter("habita_composicao_sintetico_v1", "1").ler(fonte("habita"), formato_id="fmt_habita", condominio_id="cond_habita")
