"""Revisão independente das células divergentes dos dois cenários já existentes.

Lê novamente o texto PDF, sem chamar leitores ou normalizadores do conversor.
Não altera fontes, gabaritos, regras ou Excel. Evidência insuficiente bloqueia
o diagnóstico, em vez de atribuir automaticamente o problema ao gabarito.
"""
import argparse
from collections import Counter
from datetime import date, datetime, time
from hashlib import sha256
import json
from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from pypdf import PdfReader

from conversor.domain.canonical import LoteCanonico
from conversor.domain.template import COLUNAS
from conversor.readers.text_support import ErroLeitura
from .run import caminho_protegido, escrever_json, hashes_pacote, ler_json_decimal


def exigir(condicao, codigo):
    if not condicao:
        raise ErroLeitura(codigo)


def valor_documental(campo, fragmento):
    """Somente campos discutidos neste laboratório; sem inferir dados ausentes."""
    if campo == "EMAIL1":
        encontrados = re.findall(r"[^\s<>]+@[^\s<>]+", fragmento)
        exigir(len(encontrados) <= 1, "EVIDENCIA_EMAIL_AMBIGUA")
        return encontrados[0] if encontrados else ""
    if campo in ("DDD1", "FONE1"):
        encontrados = re.findall(r"(?:\+55\s*)?(?:\(\d{2}\)|\d{2})\s*\d{4,5}-\d{4}", fragmento)
        exigir(len(encontrados) == 1, "EVIDENCIA_TELEFONE_AUSENTE_OU_AMBIGUA")
        digitos = "".join(c for c in encontrados[0] if c.isdigit())
        if len(digitos) in (12, 13) and digitos.startswith("55"):
            digitos = digitos[2:]
        exigir(len(digitos) in (10, 11), "EVIDENCIA_TELEFONE_INVALIDA")
        return digitos[:2] if campo == "DDD1" else digitos[2:]
    exigir(campo == "VENCIMENTO", "CAMPO_FORA_DO_ESCOPO_DA_REVISAO")
    encontrados = re.findall(r"\b(\d{2})/(\d{2})/(\d{2})\b", fragmento)
    exigir(len(encontrados) == 1, "EVIDENCIA_VENCIMENTO_AMBIGUA")
    dia, mes, ano = map(int, encontrados[0])
    return date(2000 + ano, mes, dia)  # convenção explícita dos sintéticos de 2026


def bloco_documental(paginas, familia, pessoa):
    origem = pessoa.origem
    inicio = (origem.pagina, origem.linha)
    marcador = r"^Bloco:" if familia == "habita" else r"^\w+\s+TORRE\s+\w+\s{2,}"
    resultado = []
    for pagina, linhas in enumerate(paginas, 1):
        for linha, texto in enumerate(linhas, 1):
            if (pagina, linha) < inicio:
                continue
            if (pagina, linha) == inicio:
                exigir(bool(re.match(marcador, texto)), "ORIGEM_CADASTRAL_NAO_CONFIRMADA")
            elif re.match(marcador, texto):
                return "\n".join(resultado)
            resultado.append(texto)
    exigir(bool(resultado), "ORIGEM_CADASTRAL_NAO_CONFIRMADA")
    return "\n".join(resultado)


def revisar(pacote: Path, execucao: Path, config: Path):
    pacote, execucao = pacote.resolve(), execucao.resolve()
    relatorio_bytes = (execucao / "relatorio_divergencias.json").read_bytes()
    relatorio = json.loads(relatorio_bytes)
    configuracao = ler_json_decimal(config)
    antes = hashes_pacote(pacote)
    exigir(relatorio["fixture_hashes_depois"] == antes, "PACOTE_DIFERE_DA_EXECUCAO_REVISADA")
    exigir(relatorio["homologado_producao"] is False, "REVISAO_RESTRITA_A_LABORATORIO")
    itens = []
    for caso in configuracao["casos"]:
        familia = caso["familia"]
        executado = relatorio["casos"][familia]
        exigir(executado["status"] == "executado_sintetico", "EXECUCAO_BLOQUEADA_NAO_REVISAVEL")
        lote = LoteCanonico.model_validate_json((execucao / f"{familia}_canonico.json").read_bytes())
        pessoas = {p.unidade_id: p for p in lote.pessoas}
        fontes = {f"{familia}_inadimplencia": caso["arquivo"]}
        if caso.get("cadastro"):
            fontes["fl_cadastro"] = caso["cadastro"]
        textos = {chave: [p.extract_text().splitlines() for p in PdfReader(caminho_protegido(pacote, nome)).pages]
                  for chave, nome in fontes.items()}
        gerado = load_workbook(execucao / executado["arquivo_excel"], read_only=True)
        gabarito = load_workbook(caminho_protegido(pacote, caso["referencia_excel"]), read_only=True)
        try:
            exigir(tuple(c.value for c in gerado["Dados"][1]) == COLUNAS, "TEMPLATE_DIVERGENTE")
            comparacao = executado["comparacao_excel"]
            diferencas = comparacao["divergencias_conteudo"] + comparacao["diferencas_representacao"]
            for indice, diferenca in enumerate(diferencas, 1):
                campo, linha = diferenca["campo"], diferenca["linha_excel"]
                coluna = COLUNAS.index(campo) + 1
                atual, esperado = gerado["Dados"].cell(linha, coluna), gabarito["Dados"].cell(linha, coluna)
                pessoa = pessoas[diferenca["unidade_id"]]
                fonte = diferenca.get("fonte_origem", f"{familia}_inadimplencia")
                paginas = textos[fonte]
                if campo == "VENCIMENTO":
                    fragmento = paginas[diferenca["pagina"]-1][diferenca["linha_fonte"]-1]
                    boleto = next(b for b in lote.boletos if b.identificador == diferenca["boleto"] and b.unidade_id == pessoa.unidade_id)
                    canonico = boleto.vencimento
                    exigir(isinstance(atual.value, datetime) and atual.value.time() == time(), "EXCEL_NAO_CONTEM_DATA_NATIVA_INTEGRA")
                    exigir(atual.is_date and atual.number_format == "dd/mm/yyyy", "EXCEL_FORMATO_DE_DATA_INCORRETO")
                    exigir(isinstance(esperado.value, str), "GABARITO_NAO_CONTEM_TEXTO_ISO")
                    exigir(date.fromisoformat(esperado.value) == atual.value.date(), "DATAS_NAO_EQUIVALENTES")
                    valor_excel = atual.value.date()
                    classificacao = "problema_de_representacao_no_excel"
                    status = "esclarecida_sem_correcao"
                    motivo = "GABARITO_TEXTO_ISO_SAIDA_DATA_NATIVA_CONFORME_CONTRATO"
                else:
                    fragmento = bloco_documental(paginas, familia, pessoa)
                    if campo == "EMAIL1":
                        canonico = pessoa.contato.emails[0] if pessoa.contato.emails else ""
                    else:
                        exigir(bool(pessoa.contato.telefones), "CANONICO_SEM_TELEFONE_DOCUMENTADO")
                        telefone = pessoa.contato.telefones[0]
                        canonico = telefone.ddd if campo == "DDD1" else telefone.numero
                    valor_excel = atual.value or ""
                    exigir(valor_excel != (esperado.value or ""), "DIVERGENCIA_DE_CONTATO_NAO_REPRODUZIDA")
                    classificacao = "inconsistencia_do_gabarito"
                    status = "pendente_revisao_gabarito"
                    motivo = "GABARITO_OMITE_CONTATO_DOCUMENTADO" if not esperado.value else (
                        "GABARITO_CONTEM_EMAIL_AUSENTE_DA_FONTE" if not valor_excel else "GABARITO_EMAIL_DIFERE_DA_FONTE")
                documental = valor_documental(campo, fragmento)
                exigir(documental == canonico, "FONTE_E_CANONICO_DIVERGEM_NAO_CLASSIFICAR_GABARITO")
                exigir(canonico == valor_excel, "CANONICO_E_EXCEL_DIVERGEM_NAO_CLASSIFICAR_GABARITO")
                itens.append({"id": familia[0].upper() + f"{indice:02}", "caso": familia,
                    "celula": f"{get_column_letter(coluna)}{linha}", "campo": campo, "boleto": diferenca["boleto"],
                    "fonte": fonte, "pagina": diferenca["pagina"], "linha_fonte": diferenca["linha_fonte"],
                    "classificacao": classificacao, "status": status, "motivo": motivo,
                    "fonte_confere_com_canonico": True, "canonico_confere_com_excel": True,
                    "fonte_tem_valor": bool(documental), "gabarito_vazio": not bool(esperado.value),
                    "fonte_sha256": antes[fontes[fonte]]})
        finally:
            gerado.close()
            gabarito.close()
    exigir(antes == hashes_pacote(pacote), "FIXTURES_ALTERADAS_DURANTE_REVISAO")
    contagens = Counter(i["classificacao"] for i in itens)
    return {"escopo": "somente_testes_sinteticos", "homologado_producao": False,
        "relatorio_revisado_sha256": sha256(relatorio_bytes).hexdigest(), "fixtures_inalteradas": True,
        "total": len(itens), "classificacoes": {classe: contagens[classe] for classe in (
            "erro_de_extracao", "erro_de_normalizacao", "problema_de_representacao_no_excel", "inconsistencia_do_gabarito")},
        "estados": dict(Counter(i["status"] for i in itens)), "correcoes_em_leitores_ou_regras": 0,
        "itens": itens}


def main():
    parser = argparse.ArgumentParser(description="Revisar contatos e datas dos dois casos sintéticos existentes")
    parser.add_argument("--pacote", type=Path, required=True)
    parser.add_argument("--execucao", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config_exemplos/laboratorio_pacote.json"))
    args = parser.parse_args()
    try:
        saida = args.saida.resolve()
        exigir(not saida.exists(), "DESTINO_DA_REVISAO_JA_EXISTE")
        exigir(not saida.is_relative_to(args.pacote.resolve()) and not saida.is_relative_to(args.execucao.resolve()),
               "REVISAO_DEVE_SER_SEPARADA_DAS_FONTES_E_EXECUCAO")
        resultado = revisar(args.pacote, args.execucao, args.config)
        saida.mkdir(parents=True, mode=0o700)
        escrever_json(saida / "revisao_individual.json", resultado)
        print(json.dumps({k: resultado[k] for k in ("total", "classificacoes", "estados", "homologado_producao")}))
        return 0  # diagnóstico concluído, não equivalência integral nem aprovação
    except ErroLeitura as erro:
        print(json.dumps({"erro": erro.codigo}))
    except (OSError, ValueError, KeyError, IndexError, StopIteration):
        print('{"erro":"REVISAO_COM_EVIDENCIA_INVALIDA"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
