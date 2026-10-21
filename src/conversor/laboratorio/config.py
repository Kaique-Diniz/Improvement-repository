from typing import Literal

from pydantic import Field

from conversor.domain.base import Id, Modelo, Texto
from conversor.domain.canonical import Endereco
from conversor.domain.catalog import Catalogo
from conversor.domain.recognition import CatalogoAssinaturas
from conversor.export.build_lines import PerfilSaidaLaboratorio


class CasoLaboratorio(Modelo):
    familia: Literal["habita", "fl"]
    formato_id: Id
    arquivo: str
    cadastro: str | None = None
    resumo: str | None = None
    referencia_excel: str
    condominio_id: Id
    administradora_id: Id
    codigo_condominio_leitor: Texto
    marcadores: tuple[Texto, ...] = Field(min_length=2)
    perfil_saida: PerfilSaidaLaboratorio


class ConfiguracaoLaboratorio(Modelo):
    escopo: Literal["somente_testes_sinteticos"]
    versao: str
    politica_cadastro_fl_confirmada: Literal["unidades_com_boleto_adiado"]
    politica_titular_fl_confirmada: Literal["cadastro_confirmado_no_laboratorio"]
    endereco_perfil_didatico: Endereco
    casos: tuple[CasoLaboratorio, ...]


def catalogos_de_teste(config: ConfiguracaoLaboratorio):
    """Catálogos em memória, todos rascunhos. Reconhecimento não é promovido."""
    dados = {c: [] for c in ("administradoras", "formatos", "condominios", "perfis_condominio", "regras_cobranca", "templates")}
    layouts = []
    for caso in config.casos:
        dados["administradoras"].append({"id": caso.administradora_id, "nome": caso.familia + " laboratorio"})
        dados["formatos"].append({"id": caso.formato_id, "nome": caso.familia + " sintético do pacote", "versao": "1",
            "tipo_arquivo": "pdf_texto", "administradora_ids": [caso.administradora_id],
            "marcadores": caso.marcadores, "leitor_id": caso.formato_id})
        dados["condominios"].append({"id": caso.condominio_id, "nome": caso.familia + " laboratorio",
            "administradora_id": caso.administradora_id, "codigo_na_administradora": caso.codigo_condominio_leitor,
            "perfil_version_id": f"perfil_{caso.familia}_lab", "formato_ids": [caso.formato_id],
            "vinculos": [{"administradora_id": caso.administradora_id, "inicio": "2026-01-01"}]})
        dados["perfis_condominio"].append({"id": f"perfil_{caso.familia}_lab", "condominio_id": caso.condominio_id,
            "versao": "1", "template_id": "template_lab", "regra_id": f"regra_{caso.familia}_lab",
            "cadastro_antecipado": caso.familia == "fl", "codificador_cedente": caso.perfil_saida.codificador})
        dados["regras_cobranca"].append({"id": f"regra_{caso.familia}_lab", "condominio_id": caso.condominio_id,
            "versao": "1", "vigente_de": "2026-01-01"})
        layouts.append({"id": f"assinatura_{caso.familia}_pacote", "versao": config.versao, "formato_id": caso.formato_id,
            "minimo_pontos": len(caso.marcadores), "marcadores": [{"id": f"m{i}", "texto": texto}
                for i, texto in enumerate(caso.marcadores, 1)]})
    dados["templates"] = [{"id": "template_lab", "nome": "Universal Laboratorio", "versao": "1", "espaco_final_coluna_27": False}]
    return Catalogo.model_validate(dados), CatalogoAssinaturas.model_validate({"versao": config.versao,
        "layouts": layouts, "administradoras": [], "condominios": []})
