from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import logging
from zipfile import ZipFile
import re

from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
import pytest

from conversor.adapters.document_probe import LimitesSondagem, SondadorLocal
from conversor.application.ports import ErroAplicacao
from conversor.domain.recognition import Motivo, TipoDocumento
from examples.fase2.gerar_demo import pdf_sintetico


def xlsx_sintetico(linhas=None):
    livro = Workbook()
    livro.active.title = "Aba Sintética"
    for linha in linhas or [["Código", "Valor"], ["SYN-001", "SINTÉTICO"]]:
        livro.active.append(linha)
    destino = BytesIO()
    livro.save(destino)
    livro.close()
    return destino.getvalue()


def pdf_imagem_sintetico():
    escritor = PdfWriter()
    pagina = escritor.add_blank_page(width=100, height=100)
    imagem = DecodedStreamObject()
    imagem.set_data(b"\xff\xff\xff")
    imagem.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
        NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
    pagina[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): escritor._add_object(imagem)})})
    stream = DecodedStreamObject()
    stream.set_data(b"q 100 0 0 100 0 0 cm /Im1 Do Q")
    pagina[NameObject("/Contents")] = escritor._add_object(stream)
    destino = BytesIO()
    escritor.write(destino)
    return destino.getvalue()


def test_pdf_texto_localizado_sem_serializar_conteudo(textos_sinteticos):
    conteudo = pdf_sintetico(textos_sinteticos["habita_tree"])
    resultado = SondadorLocal().sondar(conteudo, arquivo_id="sintetico")
    assert resultado.tipo == TipoDocumento.PDF_TEXTO
    assert resultado.completo
    assert resultado.arquivo_hash == sha256(conteudo).hexdigest()
    assert resultado.fragmentos[0].localizador == "pagina_1"
    assert "Inadimplência Atualizada" in resultado.fragmentos[0].texto
    assert "Inadimplência" not in resultado.model_dump_json()
    assert "Inadimplência" not in repr(resultado)


def test_pdf_rasterizado_sem_ocr_nao_e_conhecido(reconhecer):
    sonda = SondadorLocal().sondar(pdf_imagem_sintetico(), arquivo_id="sintetico")
    assert sonda.tipo == TipoDocumento.PDF_IMAGEM
    assert sonda.bloqueios == (Motivo.PDF_SEM_TEXTO,)
    assert reconhecer(pdf_imagem_sintetico()).estado == "desconhecido"


def test_pdf_vazio_nao_e_presumido_escaneado():
    sonda = SondadorLocal().sondar(pdf_sintetico([""]), arquivo_id="sintetico")
    assert sonda.tipo == TipoDocumento.DESCONHECIDO
    assert sonda.bloqueios == (Motivo.PDF_SEM_TEXTO,)


def test_pdf_misto_nao_aceita_somente_primeira_pagina(reconhecer, textos_sinteticos):
    conteudo = pdf_sintetico(textos_sinteticos["habita_tree"] + [""])
    resultado = reconhecer(conteudo)
    assert resultado.tipo == TipoDocumento.PDF_MISTO
    assert resultado.bloqueios == (Motivo.PDF_MISTO,)
    assert resultado.selecao is None


def test_pdf_protegido_nao_tenta_senha(textos_sinteticos):
    escritor = PdfWriter()
    escritor.append(PdfReader(BytesIO(pdf_sintetico(textos_sinteticos["habita_tree"]))))
    escritor.encrypt("SENHA_SINTETICA_NAO_LOGAR")
    destino = BytesIO()
    escritor.write(destino)
    sonda = SondadorLocal().sondar(destino.getvalue(), arquivo_id="sintetico")
    assert sonda.bloqueios == (Motivo.DOCUMENTO_PROTEGIDO,)
    assert not sonda.fragmentos


def test_excecao_na_segunda_pagina_descarta_evidencia_parcial(monkeypatch, textos_sinteticos):
    from pypdf._page import PageObject
    original = PageObject.extract_text
    chamadas = 0
    def extrair(pagina, *args, **kwargs):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 2:
            raise ValueError("SENTINELA_PRIVADA")
        return original(pagina, *args, **kwargs)
    monkeypatch.setattr(PageObject, "extract_text", extrair)
    sonda = SondadorLocal().sondar(pdf_sintetico(textos_sinteticos["habita_tree"] * 2), arquivo_id="sintetico")
    assert not sonda.completo
    assert not sonda.fragmentos
    assert sonda.bloqueios == (Motivo.DOCUMENTO_INVALIDO,)


@pytest.mark.parametrize("conteudo", [b"%PDF-1.7\ninvalido", b"PK\x03\x04invalido", b"\x00\x01binario", b""])
def test_documentos_invalidos_ou_desconhecidos_sao_bloqueados(conteudo):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id="sintetico")
    assert sonda.bloqueios
    assert not sonda.fragmentos


def test_xlsx_leitura_de_celulas_sem_formula_ou_nome_da_aba():
    conteudo = xlsx_sintetico([["Código Condomínio", "SYN-001"], ["Sentinela", '=HYPERLINK("https://example.invalid")']])
    sonda = SondadorLocal().sondar(conteudo, arquivo_id="sintetico")
    assert sonda.tipo == TipoDocumento.XLSX
    assert sonda.fragmentos[0].localizador == "aba_1"
    assert "Código Condomínio\tSYN-001" in sonda.fragmentos[0].texto
    assert "HYPERLINK" not in sonda.fragmentos[0].texto
    assert "Aba Sintética" not in sonda.model_dump_json()


def test_zip_generico_nao_e_xlsx():
    destino = BytesIO()
    with ZipFile(destino, "w") as arquivo:
        arquivo.writestr("sintetico.txt", "Exemplo Sintético")
    sonda = SondadorLocal().sondar(destino.getvalue(), arquivo_id="sintetico")
    assert sonda.tipo == TipoDocumento.DESCONHECIDO
    assert Motivo.TIPO_NAO_SUPORTADO in sonda.bloqueios


def test_entidades_xml_externas_nao_sao_lidas():
    destino = BytesIO()
    with ZipFile(destino, "w") as arquivo:
        arquivo.writestr("[Content_Types].xml", '<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///sentinela">]><x>&leak;</x>')
        arquivo.writestr("xl/workbook.xml", "<x/>")
    sonda = SondadorLocal().sondar(destino.getvalue(), arquivo_id="sintetico")
    assert sonda.bloqueios == (Motivo.DOCUMENTO_INVALIDO,)


@pytest.mark.parametrize("separador", [";", ",", "\t"])
def test_csv_utf8_com_estrutura_consistente(separador):
    conteudo = f'Código{separador}Descrição\nSYN-001{separador}Sintético\n'.encode("utf-8")
    sonda = SondadorLocal().sondar(conteudo, arquivo_id="sintetico")
    assert sonda.tipo == TipoDocumento.CSV
    assert not sonda.bloqueios
    assert "SYN-001\tSintético" in sonda.fragmentos[0].texto


@pytest.mark.parametrize("conteudo", [b"a;b,c\nx;y,z", b"a;b\nc;d;e", b"apenas texto", b"a;b\nc;\x00"])
def test_csv_ambiguo_inconsistente_ou_nao_suportado(conteudo):
    assert SondadorLocal().sondar(conteudo, arquivo_id="sintetico").bloqueios


@pytest.mark.parametrize("tipo_limite", ["bytes_arquivo", "paginas", "caracteres", "bytes_stream_pdf"])
def test_limites_pdf_sem_truncar_e_aceitar_parcialmente(textos_sinteticos, tipo_limite):
    limites = replace(LimitesSondagem(), **{tipo_limite: 1 if tipo_limite != "paginas" else 0})
    conteudo = pdf_sintetico(textos_sinteticos["habita_tree"])
    sonda = SondadorLocal(limites).sondar(conteudo, arquivo_id="sintetico")
    assert sonda.bloqueios == (Motivo.LIMITE_EXCEDIDO,)
    assert not sonda.completo
    assert not sonda.fragmentos


def test_limites_zip_e_celulas():
    conteudo = xlsx_sintetico()
    for limite in (replace(LimitesSondagem(), bytes_descompactados=1), replace(LimitesSondagem(), celulas=1)):
        sonda = SondadorLocal(limite).sondar(conteudo, arquivo_id="sintetico")
        assert sonda.bloqueios == (Motivo.LIMITE_EXCEDIDO,)


def test_limite_de_arquivo_nao_fornece_hash_parcial(tmp_path):
    arquivo = tmp_path / "sintetico.pdf"
    arquivo.write_bytes(b"conteudo sintetico")
    with pytest.raises(ErroAplicacao, match="LIMITE_ARQUIVO_EXCEDIDO"):
        SondadorLocal(replace(LimitesSondagem(), bytes_arquivo=1)).sondar_arquivo(arquivo, arquivo_id="sintetico")


def test_nome_do_arquivo_nao_seleciona_tipo(tmp_path):
    arquivo = tmp_path / "habita_tree.pdf"
    arquivo.write_bytes(xlsx_sintetico())
    assert SondadorLocal().sondar_arquivo(arquivo, arquivo_id="sintetico").tipo == TipoDocumento.XLSX


def test_logs_do_parser_nao_vazam_para_aplicacao(caplog):
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("pypdf._reader").warning("SENTINELA_PRIVADA")
    assert "SENTINELA_PRIVADA" not in caplog.text


def test_dimensao_xlsx_incorreta_nao_oculta_outra_identidade(reconhecer, textos_sinteticos, dados_reconhecimento):
    dados_reconhecimento["formatos"][0]["tipo_arquivo"] = "xlsx"
    linhas = [[linha, ""] for linha in textos_sinteticos["habita_tree"][0].splitlines()]
    linhas.append(["Código Condomínio", "SYN-OUTRO"])
    entrada = xlsx_sintetico(linhas)
    memoria = BytesIO()
    with ZipFile(BytesIO(entrada)) as original, ZipFile(memoria, "w") as novo:
        for info in original.infolist():
            conteudo = original.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                conteudo = re.sub(rb'<dimension ref="[^"]+"', b'<dimension ref="A1"', conteudo)
            novo.writestr(info.filename, conteudo)
    resultado = reconhecer(memoria.getvalue())
    assert resultado.estado == "ambiguo"
    assert Motivo.CONDOMINIO_AMBIGUO in resultado.bloqueios
