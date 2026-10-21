"""Gera somente documentos/configuração sintéticos em diretório local ignorado."""
import argparse
import json
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from conversor.domain.catalog import Catalogo
from conversor.domain.recognition import CatalogoAssinaturas


def pdf_sintetico(paginas: list[str]) -> bytes:
    from io import BytesIO
    escritor = PdfWriter()
    for texto in paginas:
        pagina = escritor.add_blank_page(width=595, height=842)
        fonte = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
        pagina[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): fonte})})
        comandos = [b"BT /F1 10 Tf 40 800 Td 14 TL"]
        for linha in texto.splitlines():
            escaped = linha.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
            comandos.append(b"(" + escaped + b") Tj T*")
        stream = DecodedStreamObject()
        stream.set_data(b"\n".join(comandos) + b"\nET")
        pagina[NameObject("/Contents")] = escritor._add_object(stream)
    memoria = BytesIO()
    escritor.write(memoria)
    return memoria.getvalue()


def catalogo_sintetico() -> Catalogo:
    adms = [{"id": f"adm_{a}_sintetica", "nome": f"Administradora {a.upper()} Sintética"} for a in ("habita", "fl")]
    formatos = [{"id": f"fmt_{a}_sintetico_v1", "nome": f"Layout {a.upper()} Sintético", "versao": "1",
        "tipo_arquivo": "pdf_texto", "administradora_ids": [f"adm_{a}_sintetica"],
        "marcadores": [], "leitor_id": f"leitor_{a}_nao_implementado"} for a in ("habita", "fl")]
    condos, perfis, regras = [], [], []
    for nome, adm, codigo in (("tree", "habita", "SYN-TREE"), ("plaza", "fl", "SYN-PLAZA"), ("outro", "habita", "SYN-OUTRO")):
        id_ = f"cond_{nome}_sintetico"
        condos.append({"id": id_, "nome": f"Condomínio {nome.upper()} Sintético", "administradora_id": f"adm_{adm}_sintetica",
            "codigo_na_administradora": codigo, "perfil_version_id": f"perfil_{nome}_v1", "formato_ids": [f"fmt_{adm}_sintetico_v1"],
            "vinculos": [{"administradora_id": f"adm_{adm}_sintetica", "inicio": "2026-01-01"}]})
        perfis.append({"id": f"perfil_{nome}_v1", "condominio_id": id_, "versao": "1", "template_id": "template_universal_v1",
            "regra_id": f"regra_{nome}_v1", "cadastro_antecipado": False, "codificador_cedente": "pendente_homologacao"})
        regras.append({"id": f"regra_{nome}_v1", "condominio_id": id_, "versao": "1", "vigente_de": "2026-01-01"})
    return Catalogo.model_validate({"administradoras": adms, "condominios": condos, "formatos": formatos,
        "perfis_condominio": perfis, "regras_cobranca": regras,
        "templates": [{"id": "template_universal_v1", "nome": "Universal", "versao": "1"}]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path("dados/demo_fase2"))
    args = parser.parse_args()
    fontes = Path(__file__).resolve().parent
    documentos = json.loads((fontes / "documentos.sinteticos.json").read_text(encoding="utf-8"))
    assinaturas = CatalogoAssinaturas.model_validate_json((fontes / "assinaturas.sinteticas.json").read_text(encoding="utf-8"))
    args.saida.mkdir(parents=True, exist_ok=True)
    for nome, paginas in documentos.items():
        with (args.saida / f"{nome}.pdf").open("xb") as arquivo:
            arquivo.write(pdf_sintetico(paginas))
    for nome, modelo in (("catalogo.json", catalogo_sintetico()), ("assinaturas.json", assinaturas)):
        with (args.saida / nome).open("x", encoding="utf-8") as arquivo:
            arquivo.write(modelo.model_dump_json(indent=2))
    print("DEMO_SINTETICA_CRIADA_NAO_HOMOLOGADA")


if __name__ == "__main__":
    main()
