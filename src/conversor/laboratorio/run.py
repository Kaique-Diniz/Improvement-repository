from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from pydantic import ValidationError

from conversor.adapters.document_probe import SondadorLocal
from conversor.application.enrichment import complementar_cadastro
from conversor.application.ports import ErroAplicacao, Estado
from conversor.application.recognition import ReconhecerDocumento
from conversor.export.build_lines import construir_linhas
from conversor.export.xlsx import escrever_xlsx
from conversor.readers.cadastro import LeitorCadastroFLSintetico
from conversor.readers.fl import LeitorFLSintetico
from conversor.readers.habita import LeitorHabitaSintetico
from conversor.readers.text_support import ContextoLeitura, ErroLeitura, id_estavel
from conversor.rules.laboratory import RegraLaboratorio, avaliar
from .comparison import comparar_excel, conferir_financeiro, conferir_resumo_xlsx
from .config import ConfiguracaoLaboratorio, catalogos_de_teste

LEITORES = {l.formato_id: l for l in (LeitorHabitaSintetico, LeitorFLSintetico)}


def caminho_protegido(raiz: Path, relativo: str) -> Path:
    caminho = (raiz / relativo).resolve()
    if not caminho.is_relative_to(raiz.resolve()): raise ErroLeitura("CAMINHO_FORA_DO_PACOTE")
    return caminho


def ler_json_decimal(caminho):
    def pares(itens):
        valor = {}
        for chave, item in itens:
            if chave in valor: raise ErroLeitura("JSON_COM_CHAVE_DUPLICADA")
            valor[chave] = item
        return valor
    def constante(_): raise ErroLeitura("JSON_NAO_FINITO")
    try:
        conteudo = Path(caminho).read_bytes()
        if len(conteudo) > 5 * 1024 * 1024: raise ErroLeitura("JSON_LIMITE_EXCEDIDO")
        return json.loads(conteudo, parse_float=Decimal, object_pairs_hook=pares, parse_constant=constante)
    except (ValueError, UnicodeError):
        raise ErroLeitura("JSON_INVALIDO") from None


def escrever_json(caminho, dados):
    conteudo = (json.dumps(dados, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, prefix=".json-", delete=False) as arq:
            temporario = Path(arq.name)
            arq.write(conteudo)
            arq.flush()
            os.fsync(arq.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None: temporario.unlink(missing_ok=True)


def hashes_pacote(pacote):
    arquivos = sorted(p for p in pacote.rglob("*") if p.is_file())
    if len(arquivos) > 100 or sum(p.stat().st_size for p in arquivos) > 100 * 1024 * 1024:
        raise ErroLeitura("PACOTE_LIMITE_EXCEDIDO")
    if any(p.is_symlink() or not p.resolve().is_relative_to(pacote.resolve()) for p in arquivos):
        raise ErroLeitura("PACOTE_CONTEM_LINK")
    return {str(p.relative_to(pacote)): sha256(p.read_bytes()).hexdigest() for p in arquivos}


class _CatalogoEmMemoria:
    def __init__(self, catalogo): self.estado = Estado(revisao=0, catalogo=catalogo)
    def carregar(self): return self.estado
    def salvar(self, *_args, **_kwargs): raise ErroLeitura("CATALOGO_DE_TESTE_SOMENTE_LEITURA")


class _AssinaturasEmMemoria:
    def __init__(self, assinaturas): self.assinaturas = assinaturas
    def carregar(self): return self.assinaturas


def _regra(familia, regras, config):
    if familia == "habita":
        dados = regras["regra_habita_teste"]
        return RegraLaboratorio(id="regra_habita_pacote", dias_exclusivo=dados["dias_minimos_atraso_exclusivo"],
            excluir_unidade_valor=Decimal("0.01") if dados["excluir_unidade_com_boleto_de_001"] else None,
            apontamentos_excluintes=tuple(dados["excluir_unidade_com_apontamento"]),
            namespace_apontamentos=LeitorHabitaSintetico.formato_id)
    dados = regras["regra_fl_teste"]
    return RegraLaboratorio(id="regra_fl_pacote", dias_exclusivo=dados["dias_minimos_atraso_exclusivo"],
        cadastro=config.politica_cadastro_fl_confirmada if dados["cadastro_antecipado"] else "nunca")


def executar_pacote(pacote: Path, saida: Path, configuracao: Path):
    pacote, saida = pacote.resolve(), saida.resolve()
    if saida.is_relative_to(pacote) or pacote.is_relative_to(saida):
        raise ErroLeitura("SAIDA_DEVE_SER_SEPARADA_DAS_FIXTURES")
    if saida.exists() and any(saida.iterdir()): raise ErroLeitura("DESTINO_NAO_VAZIO")
    config = ConfiguracaoLaboratorio.model_validate(ler_json_decimal(configuracao))
    if sorted(c.familia for c in config.casos) != ["fl", "habita"]:
        raise ErroLeitura("CONFIGURACAO_DE_CASOS_INVALIDA")
    esperado = ler_json_decimal(caminho_protegido(pacote, "esperado/resultado_esperado.json"))
    data_ref = date.fromisoformat(esperado["data_referencia"])
    readme = caminho_protegido(pacote, "README.md").read_text(encoding="utf-8")
    if "100% sintetico" not in readme: raise ErroLeitura("PACOTE_SINTETICO_NAO_DECLARADO")
    antes = hashes_pacote(pacote)
    saida.mkdir(parents=True, exist_ok=True, mode=0o700)
    catalogo, assinaturas = catalogos_de_teste(config)
    reconhecimento = ReconhecerDocumento(_CatalogoEmMemoria(catalogo), _AssinaturasEmMemoria(assinaturas))
    relatorio = {"escopo": "somente_testes_sinteticos", "homologado_producao": False,
        "versao_configuracao": config.versao, "data_referencia": data_ref.isoformat(),
        "configuracao_hash": sha256(config.model_dump_json().encode()).hexdigest(),
        "fixture_hashes_antes": antes, "casos": {}, "observacoes": [
            "Cadastros FL com qualquer boleto adiado: política confirmada pelo usuário apenas para este laboratório.",
            "Titular FL divergente: usuário confirmou prioridade do Cadastro Geral somente no laboratório, com alerta e auditoria original preservada.",
            "Perfis de endereço/codificação são didáticos, declarados em configuração e não extraídos de PDFs nem aprovados para produção.",
            "Catálogos e assinaturas continuam rascunhos; layout identificado não promove prontidão operacional.",
            "Habita não fornece administradora documental; FL não fornece código/CNPJ forte de condomínio. Contextos são explícitos do laboratório.",
            "W002A e W045A são códigos de relatórios distintos, não evidências de condomínios diferentes.",
            "Emissao Habita contém YYYYMM: conservado como competência do cenário; emissão diária não é inventada.",
            "Datas nativas e contatos comprovados pela fonte são preservados mesmo quando diferem dos gabaritos didáticos."
        ]}
    for caso in config.casos:
        familia = caso.familia
        try:
            fonte = caminho_protegido(pacote, caso.arquivo).read_bytes()
            sonda = SondadorLocal().sondar(fonte, arquivo_id=f"{familia}_inadimplencia")
            if not any("AMOSTRA" in f.texto.upper() and ("SINTETIC" in f.texto.upper() or "FICTICI" in f.texto.upper()) for f in sonda.fragmentos):
                raise ErroLeitura("FONTE_NAO_DECLARADA_SINTETICA")
            reconhecido = reconhecimento.executar(sonda, data_ref=data_ref)
            candidatos = [p.formato_id for p in reconhecido.pontuacoes if p.elegivel]
            if not candidatos: raise ErroLeitura("LAYOUT_DESCONHECIDO")
            if len(candidatos) > 1: raise ErroLeitura("LAYOUT_AMBIGUO")
            if candidatos[0] != caso.formato_id: raise ErroLeitura("LAYOUT_DIVERGENTE_DO_CONTEXTO")
            contexto = ContextoLeitura(caso.condominio_id, caso.administradora_id, caso.formato_id,
                                       f"{familia}_inadimplencia", caso.codigo_condominio_leitor)
            if caso.formato_id not in LEITORES: raise ErroLeitura("LEITOR_NAO_REGISTRADO")
            lote = LEITORES[caso.formato_id]().ler(fonte, contexto=contexto)
            escrever_json(saida / f"{familia}_extraido_antes_cadastro.json", lote.model_dump(mode="json"))
            cadastro = {}
            fontes_caso = {caso.arquivo: sonda.arquivo_hash}
            if caso.cadastro:
                contexto_cad = ContextoLeitura(caso.condominio_id, caso.administradora_id, "cadastro_fl_sintetico_v1",
                    "fl_cadastro", caso.codigo_condominio_leitor)
                cadastro_bytes = caminho_protegido(pacote, caso.cadastro).read_bytes()
                fontes_caso[caso.cadastro] = sha256(cadastro_bytes).hexdigest()
                cadastro = LeitorCadastroFLSintetico().ler(cadastro_bytes, contexto=contexto_cad)
            regra = _regra(familia, esperado, config)
            pid = id_estavel("exec", json.dumps(fontes_caso, sort_keys=True), data_ref, regra.model_dump_json(), config.model_dump_json())
            alertas_cadastro = []
            lote = complementar_cadastro(lote, cadastro, config.endereco_perfil_didatico,
                politica_titular=config.politica_titular_fl_confirmada if familia == "fl" else "bloquear",
                processamento_id=pid, alertas=alertas_cadastro)
            decisoes = avaliar(lote, regra, data_ref=data_ref, processamento_id=pid)
            linhas, referencias = construir_linhas(lote, decisoes, caso.perfil_saida,
                politica_cadastro=regra.cadastro, processamento_id=pid, ocorrencias_extras=tuple(alertas_cadastro))
            template = catalogo.templates[0]
            excel = saida / f"{familia}_resultado_laboratorio.xlsx"
            ocorrencias = escrever_xlsx(linhas, template, excel, data_ref=data_ref)
            # Resultado do processo, nunca preenchido a partir de saídas esperadas.
            escrever_json(saida / f"{familia}_canonico.json", lote.model_dump(mode="json"))
            escrever_json(saida / f"{familia}_decisoes.json", [d.model_dump(mode="json") for d in decisoes])
            unidades = {u.id: u for u in lote.unidades}
            relatorio["casos"][familia] = {
                "status": "executado_sintetico", "contexto_identidade": "configuracao_explicita_de_laboratorio",
                "fontes_hashes": fontes_caso,
                "reconhecimento_operacional": reconhecido.model_dump(mode="json"),
                "layout_sintetico_identificado": candidatos[0],
                "unidades": len(lote.unidades), "boletos_unicos": len(lote.boletos),
                "boletos": [{"boleto": b.identificador, "unidade": unidades[b.unidade_id].chave_normalizada,
                    "original": str(b.composicao.total_original), "saldo_acumulado_nao_exportado": str(b.saldo_acumulado) if b.saldo_acumulado is not None else None,
                    "paginas": sorted({o.pagina for o in b.origens}), "origens": [{"pagina": o.pagina, "linha": o.linha} for o in b.origens]}
                    for b in lote.boletos],
                "linhas_divida": sum(l.tipo == "divida" for l in linhas), "linhas_cadastrais": sum(l.tipo == "cadastral" for l in linhas),
                "ocorrencias": [o.model_dump(mode="json") for o in ocorrencias],
                "verificacoes_gabarito": conferir_financeiro(lote, decisoes, linhas, ocorrencias, esperado[familia]),
                "comparacao_excel": comparar_excel(excel, caminho_protegido(pacote, caso.referencia_excel), referencias),
                "divergencias_resumo_xlsx": conferir_resumo_xlsx(caminho_protegido(pacote, caso.resumo), lote) if caso.resumo else [],
                "arquivo_excel": excel.name,
            }
        except ErroLeitura as erro:
            relatorio["casos"][familia] = {"status": "bloqueado", "codigo": erro.codigo,
                "pagina": erro.pagina, "linha": erro.linha, "boleto": erro.boleto}
        except (ValidationError, KeyError, ValueError, OSError, ErroAplicacao):
            relatorio["casos"][familia] = {"status": "bloqueado", "codigo": "CONTRATO_OU_FONTE_INVALIDA"}
    depois = hashes_pacote(pacote)
    relatorio["fixture_hashes_depois"] = depois
    relatorio["fixtures_inalteradas"] = antes == depois
    relatorio["todos_financeiros_conferem"] = all(c["status"] == "executado_sintetico"
        and all(v["ok"] for v in c["verificacoes_gabarito"]) and not c["divergencias_resumo_xlsx"]
        for c in relatorio["casos"].values())
    relatorio["divergencias_excel"] = sum(len(c.get("comparacao_excel", {}).get("divergencias_conteudo", []))
                                        for c in relatorio["casos"].values())
    escrever_json(saida / "relatorio_divergencias.json", relatorio)
    escrever_relatorio_md(saida / "RELATORIO.md", relatorio)
    return relatorio


def escrever_relatorio_md(caminho, relatorio):
    linhas = ["# Relatório do pacote sintético", "", "Não homologado para produção.", "",
              f"Data de referência: {relatorio['data_referencia']}.",
              f"Fixtures preservadas por SHA-256: {relatorio['fixtures_inalteradas']}.", "",
              "| Caso | Unidades | Boletos únicos | Dívidas | Cadastrais | Conteúdo divergente |",
              "|---|---:|---:|---:|---:|---:|"]
    for familia, caso in relatorio["casos"].items():
        if caso["status"] == "bloqueado":
            linhas.append(f"| {familia} | bloqueado: {caso['codigo']} | | | | |")
        else:
            linhas.append(f"| {familia} | {caso['unidades']} | {caso['boletos_unicos']} | {caso['linhas_divida']} | {caso['linhas_cadastrais']} | {len(caso['comparacao_excel']['divergencias_conteudo'])} |")
    linhas.extend(["", "## Comparações e divergências", ""])
    for familia, caso in relatorio["casos"].items():
        if caso["status"] != "executado_sintetico": continue
        linhas.extend([f"{familia}: {sum(v['ok'] for v in caso['verificacoes_gabarito'])}/{len(caso['verificacoes_gabarito'])} verificações do JSON conferem.", ""])
        for d in caso["divergencias_resumo_xlsx"]:
            linhas.append(f"- Resumo independente {familia}, linha {d.get('linha', '-')}: {d['codigo']}.")
        for d in caso["comparacao_excel"]["divergencias_conteudo"]:
            linhas.append(f"- {familia}, linha Excel {d.get('linha_excel', '-')}, campo {d['campo']}, boleto {d.get('boleto') or 'cadastral'}, fonte {d.get('fonte_origem', '-')}, página {d.get('pagina', '-')}, linha fonte {d.get('linha_fonte', '-')}: {d['codigo']}.")
        for d in caso["comparacao_excel"]["diferencas_representacao"]:
            linhas.append(f"- {familia}, linha Excel {d['linha_excel']}, campo {d['campo']}: valor equivalente; {d['obtido_tipo']} gerado versus {d['esperado_tipo']} no gabarito.")
        linhas.append("")
    linhas.extend(["", "## Limitações e decisões", ""] + [f"- {o}" for o in relatorio["observacoes"]])
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
