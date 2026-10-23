"""Validação privada da Fase 3: compara leitura canônica, sem régua ou Excel."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from conversor.adapters.json_repository import ler_json_bytes
from conversor.adapters.protected_sources import FontesLocaisProtegidas
from conversor.adapters.private_json import escrever_json
from conversor.application.ports import ErroAplicacao
from conversor.application.reading import resultado_leitura
from conversor.domain.base import Data, Hash, Id, Modelo, Texto
from conversor.domain.canonical import LoteCanonico
from conversor.readers.contracts import FonteProtegida
from conversor.readers.operational import RegistroLeitores
from conversor.readers.text_support import ContextoLeitura, ErroLeitura, id_estavel


class CasoValidacao(Modelo):
    id: Id
    fonte: FonteProtegida
    arquivo: str = Field(repr=False)
    gabarito: str = Field(repr=False)
    gabarito_sha256: Hash
    leitor_id: Literal["habita_composicao_sintetico_v1", "fl_composicao_sintetico_v1", "cadastro_fl_sintetico_v1",
                       "habita_composicao_real_v1", "fl_composicao_real_v1", "cadastro_fl_real_v1"]
    leitor_versao: Literal["1"] = "1"
    formato_id: Id
    condominio_id: Id
    administradora_id: Id
    codigo_condominio: Texto = Field(repr=False)
    data_ref: Data


class ManifestoValidacao(Modelo):
    schema_version: Literal["1.0"] = "1.0"
    finalidade: Literal["validacao_privada_fase3"]
    natureza: Literal["sintetica", "real_autorizada"]
    autorizacao_id: Id
    casos: tuple[CasoValidacao, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def sem_duplicatas(self):
        for valores in ([c.id for c in self.casos], [c.fonte.arquivo_id for c in self.casos]):
            if len(set(valores)) != len(valores):
                raise ValueError("CASO_OU_FONTE_DUPLICADA")
        return self


class _ContextosDeclarados:
    """Identidade esperada pelo revisor, sem promovê-la a reconhecimento homologado."""
    def __init__(self, casos):
        self.casos = {c.fonte.arquivo_id: c for c in casos}

    def resolver(self, fonte, *, formato_id, condominio_id):
        caso = self.casos.get(fonte.arquivo_id)
        if caso is None or (caso.formato_id, caso.condominio_id, caso.fonte) != (formato_id, condominio_id, fonte):
            raise ErroLeitura("CONTEXTO_DE_LEITURA_INCOMPATIVEL")
        return ContextoLeitura(caso.condominio_id, caso.administradora_id, caso.formato_id,
            fonte.arquivo_id, caso.codigo_condominio, leitor_versao=f"{caso.leitor_id}@{caso.leitor_versao}")


def _area_fora_do_git(caminho: Path):
    """O processo privado não aceita fontes/resultados dentro de checkout Git."""
    caminho = caminho.resolve()
    if not caminho.is_dir():
        raise ErroLeitura("AREA_PRIVADA_INDISPONIVEL")
    try:
        ambiente = {k: v for k, v in os.environ.items() if k not in (
            "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")}
        teste = subprocess.run(["git", "-C", str(caminho), "rev-parse", "--git-dir"], capture_output=True, env=ambiente)
    except OSError:
        raise ErroLeitura("NAO_FOI_POSSIVEL_VERIFICAR_AREA_PRIVADA") from None
    # Este ambiente contém âncoras .git vazias em /tmp e /workspace, que não são checkouts.
    if teste.returncode == 0 or any((p / ".git").is_file() or (p / ".git" / "HEAD").is_file()
                                  for p in (caminho, *caminho.parents)):
        raise ErroLeitura("AREA_PRIVADA_DEVE_FICAR_FORA_DO_GIT")


def _diferencas(atual, esperado, caminho="$", local=None):
    """Descritores sem valores, nomes, CPFs, contatos ou números de boleto."""
    if isinstance(atual, dict):
        origem = atual.get("origem") or (atual.get("origens") or [None])[0]
        if isinstance(origem, dict):
            local = {k: origem.get(k) for k in ("pagina", "linha")}
        if not isinstance(esperado, dict):
            return [{"campo": caminho, **(local or {})}]
        encontrados = []
        for chave in sorted(set(atual) | set(esperado)):
            encontrados.extend(_diferencas(atual.get(chave), esperado.get(chave), caminho + "." + chave, local))
        return encontrados
    if isinstance(atual, list) and isinstance(esperado, list):
        encontrados = []
        for i in range(max(len(atual), len(esperado))):
            encontrados.extend(_diferencas(atual[i] if i < len(atual) else None,
                esperado[i] if i < len(esperado) else None, f"{caminho}[{i}]", local))
        return encontrados
    return [] if atual == esperado else [{"campo": caminho, **(local or {})}]


def executar_validacao(raiz: Path, manifesto: Path, saida: Path, *, salvar_canonicos=False):
    raiz, manifesto, saida = raiz.resolve(), manifesto.resolve(), saida.resolve()
    _area_fora_do_git(raiz)
    if not manifesto.is_relative_to(raiz) or manifesto.is_symlink():
        raise ErroLeitura("MANIFESTO_FORA_DA_AREA_PRIVADA")
    _area_fora_do_git(manifesto.parent)
    if not saida.is_relative_to(raiz) or saida == raiz or saida.exists():
        raise ErroLeitura("SAIDA_PRIVADA_DEVE_SER_NOVA_E_INTERNA")
    _area_fora_do_git(next(p for p in saida.parents if p.is_dir()))
    # O manifesto também tem leitura limitada; nenhuma entrada bruta é logada.
    with manifesto.open("rb") as arq:
        manifesto_bytes = arq.read(1024 * 1024 + 1)
    if len(manifesto_bytes) > 1024 * 1024:
        raise ErroLeitura("MANIFESTO_LIMITE_EXCEDIDO")
    config = ManifestoValidacao.model_validate(ler_json_bytes(manifesto_bytes))
    fontes = FontesLocaisProtegidas(raiz, {c.fonte.arquivo_id: c.arquivo for c in config.casos})
    registro = RegistroLeitores(fontes, _ContextosDeclarados(config.casos))
    saida.mkdir(parents=True, mode=0o700)
    relatorio = {"finalidade": config.finalidade, "natureza": config.natureza, "autorizacao_id": config.autorizacao_id,
        "manifesto_sha256": sha256(manifesto_bytes).hexdigest(), "homologado_producao": False,
        "contexto": "declarado_no_manifesto_nao_aprova_reconhecimento", "casos": []}
    for caso in config.casos:
        try:
            for relativo in (caso.arquivo, caso.gabarito):
                pasta = (raiz / relativo).resolve().parent
                if pasta.is_relative_to(raiz) and pasta.is_dir():
                    _area_fora_do_git(pasta)
            leitor = registro.obter(caso.leitor_id, caso.leitor_versao)
            lote = leitor.ler(caso.fonte, formato_id=caso.formato_id, condominio_id=caso.condominio_id)
            pid = id_estavel("validacao", caso.fonte.sha256, caso.gabarito_sha256, caso.leitor_id, caso.leitor_versao, caso.data_ref)
            resultado = resultado_leitura(lote, processamento_id=pid)
            id_gabarito = id_estavel("gabarito", caso.id)
            gabaritos = FontesLocaisProtegidas(raiz, {id_gabarito: caso.gabarito})
            bruto = gabaritos.ler(FonteProtegida(arquivo_id=id_gabarito, sha256=caso.gabarito_sha256))
            esperado = LoteCanonico.model_validate(ler_json_bytes(bruto))
            diferencas = _diferencas(lote.model_dump(mode="json"), esperado.model_dump(mode="json"))
            item = {"caso_id": caso.id, "status": "divergente" if diferencas else "comparacao_confere",
                "fonte_sha256": caso.fonte.sha256, "gabarito_sha256": caso.gabarito_sha256,
                "data_ref": caso.data_ref.isoformat(),
                "leitor_id": caso.leitor_id, "leitor_versao": caso.leitor_versao,
                "unidades": len(lote.unidades), "boletos": len(lote.boletos), "pessoas": len(lote.pessoas),
                "alertas": dict(Counter(o.codigo for o in resultado.ocorrencias)),
                "campos_divergentes": diferencas[:100], "total_campos_divergentes": len(diferencas)}
            if resultado.bloqueante:
                item["status"] = "revisao_humana"
                item["registros_em_revisao"] = sorted({o.registro_id for o in resultado.ocorrencias
                    if o.bloqueante and o.registro_id is not None})
                item["auditoria_revisao"] = f"{caso.id}.revisao_documental.json"
            # Detecta alteração de fontes e gabaritos durante a execução.
            fontes.ler(caso.fonte)
            gabaritos.ler(FonteProtegida(arquivo_id=id_gabarito, sha256=caso.gabarito_sha256))
            if resultado.bloqueante:
                escrever_json(saida / item["auditoria_revisao"], {
                    "ocorrencias": [o.model_dump(mode="json") for o in resultado.ocorrencias if o.bloqueante],
                    "ressalvas": [r.model_dump(mode="json") for r in resultado.lote.ressalvas if r.gravidade=='critico'],
                    "homologado_producao": False,
                })
            if salvar_canonicos:
                escrever_json(saida / f"{caso.id}.canonico.json", lote.model_dump(mode="json"))
        except ErroLeitura as erro:
            item = {"caso_id": caso.id, "status": "bloqueado", "codigo": erro.codigo,
                    "pagina": erro.pagina, "linha": erro.linha}
        except (ValidationError, ValueError, OSError, ErroAplicacao):
            item = {"caso_id": caso.id, "status": "bloqueado", "codigo": "FONTE_OU_GABARITO_INVALIDO"}
        relatorio["casos"].append(item)
    escrever_json(saida / "relatorio_leitores.json", relatorio)
    return relatorio


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, required=True)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--salvar-canonicos", action="store_true", help="Salvar dados extraídos somente na saída privada")
    args = parser.parse_args(argv)
    try:
        relatorio = executar_validacao(args.raiz, args.manifesto, args.saida, salvar_canonicos=args.salvar_canonicos)
        estados = Counter(c["status"] for c in relatorio["casos"])
        print(json.dumps({"casos": len(relatorio["casos"]), "estados": dict(estados), "homologado_producao": False}))
        return 2 if estados["bloqueado"] or estados["revisao_humana"] else (1 if estados["divergente"] else 0)
    except ErroLeitura as erro:
        print(json.dumps({"erro": erro.codigo}))
    except (ValidationError, ValueError, OSError, ErroAplicacao):
        print('{"erro":"VALIDACAO_PRIVADA_INVALIDA"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
