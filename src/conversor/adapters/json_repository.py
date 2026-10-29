"""Snapshots multiarquivo imutáveis + commit por troca atômica de current.json."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Annotated, Literal
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import Field, ValidationError

from conversor.application.configuration import COLECOES
from conversor.application.ports import ErroAplicacao, Estado
from conversor.domain.base import Hash, Modelo
from conversor.domain.catalog import Catalogo


class Manifesto(Modelo):
    schema_version: Literal["1.0"] = "1.0"
    geracao: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    revisao: Annotated[int, Field(strict=True, ge=1)]
    arquivos: dict[str, Hash]


def _sem_chaves_duplicadas(pares):
    saida = {}
    for chave, valor in pares:
        if chave in saida:
            raise ErroAplicacao("JSON_COM_CHAVE_DUPLICADA")
        saida[chave] = valor
    return saida


def ler_json_bytes(conteudo: bytes):
    try:
        return json.loads(conteudo, object_pairs_hook=_sem_chaves_duplicadas,
                          parse_constant=lambda _: (_ for _ in ()).throw(ErroAplicacao("JSON_NAO_FINITO")))
    except (ValueError, UnicodeError):
        raise ErroAplicacao("JSON_INVALIDO") from None


def _bytes(dados) -> bytes:
    return (json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _gravar(path: Path, conteudo: bytes):
    with path.open("xb") as arquivo:
        os.chmod(path, 0o600)
        from .private_permissions import proteger_novo_windows
        proteger_novo_windows(path)
        arquivo.write(conteudo)
        arquivo.flush()
        os.fsync(arquivo.fileno())


def _sincronizar_diretorio(path: Path):
    # fsync de diretório é suportado em POSIX; Windows mantém os.replace + flush dos arquivos.
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class RepositorioJSON:
    def __init__(self, diretorio: str | Path, *, timeout: float = 5):
        self.raiz = Path(diretorio).resolve()
        self.timeout = timeout

    def _arquivo(self, path):
        if not path.resolve().is_relative_to(self.raiz):
            raise ErroAplicacao("CAMINHO_FORA_DO_REPOSITORIO")
        return path

    def carregar(self) -> Estado:
        try:
            ponteiro = self._arquivo(self.raiz / "current.json")
            if not ponteiro.exists():
                raise ErroAplicacao("REPOSITORIO_NAO_INICIALIZADO")
            conteudo_ponteiro = ponteiro.read_bytes()
            bruto = ler_json_bytes(conteudo_ponteiro)
            if not isinstance(bruto, dict) or bruto.get("schema_version") != "1.0":
                raise ErroAplicacao("SCHEMA_NAO_SUPORTADO")
            manifesto = Manifesto.model_validate(bruto)
            if set(manifesto.arquivos) != {f"{c}.json" for c in COLECOES}:
                raise ErroAplicacao("MANIFESTO_INCOMPLETO")
            geracao = self._arquivo(self.raiz / "generations" / manifesto.geracao)
            if self._arquivo(geracao / "manifest.json").read_bytes() != conteudo_ponteiro:
                raise ErroAplicacao("MANIFESTO_DIVERGENTE")
            dados = {"schema_version": "1.0"}
            for colecao in COLECOES:
                nome = f"{colecao}.json"
                conteudo = self._arquivo(geracao / nome).read_bytes()
                if sha256(conteudo).hexdigest() != manifesto.arquivos[nome]:
                    raise ErroAplicacao("INTEGRIDADE_DO_ARQUIVO_VIOLADA")
                envelope = ler_json_bytes(conteudo)
                if not isinstance(envelope, dict) or envelope.get("schema_version") != "1.0":
                    raise ErroAplicacao("SCHEMA_NAO_SUPORTADO")
                if set(envelope) != {"schema_version", colecao}:
                    raise ErroAplicacao("ENVELOPE_INVALIDO")
                dados[colecao] = envelope[colecao]
            return Estado(revisao=manifesto.revisao, catalogo=Catalogo.model_validate(dados))
        except ErroAplicacao:
            raise
        except ValidationError:
            raise ErroAplicacao("CONTRATO_OU_REFERENCIA_INVALIDA") from None
        except OSError:
            raise ErroAplicacao("FALHA_LEITURA_REPOSITORIO") from None

    @staticmethod
    def _preservar_historico(anterior: Catalogo, novo: Catalogo):
        for colecao in ("formatos", "perfis_condominio", "regras_cobranca", "templates", "processamentos", "ocorrencias"):
            novos = {i.id: i for i in getattr(novo, colecao)}
            for item in getattr(anterior, colecao):
                imutavel = (colecao in ("templates", "processamentos", "ocorrencias")
                            or getattr(item, "status", None) in ("validado", "aprovado", "aprovada"))
                if imutavel and novos.get(item.id) != item:
                    raise ErroAplicacao("HISTORICO_OU_VERSAO_IMUTAVEL")
        for condo in anterior.condominios:
            atual = next((c for c in novo.condominios if c.id == condo.id), None)
            if atual is None:
                continue  # exclusão ainda depende das chaves estrangeiras do catálogo
            # Relações fechadas não mudam; a aberta só pode receber fim, seguido de novo vínculo.
            for indice, vinculo in enumerate(condo.vinculos):
                if indice >= len(atual.vinculos):
                    raise ErroAplicacao("VINCULO_HISTORICO_IMUTAVEL")
                outro = atual.vinculos[indice]
                if vinculo.fim is not None and outro != vinculo:
                    raise ErroAplicacao("VINCULO_HISTORICO_IMUTAVEL")
                if vinculo.fim is None and (outro.inicio != vinculo.inicio or outro.administradora_id != vinculo.administradora_id):
                    raise ErroAplicacao("VINCULO_HISTORICO_IMUTAVEL")

    def salvar(self, catalogo: Catalogo, *, revisao_esperada: int) -> Estado:
        temporario = None
        ponteiro_tmp = None
        try:
            catalogo = Catalogo.model_validate(catalogo.model_dump())
            self.raiz.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock_path = self._arquivo(self.raiz / ".write.lock")
            with FileLock(lock_path, timeout=self.timeout):
                if (self.raiz / "current.json").exists():
                    estado = self.carregar()
                else:
                    estado = Estado(revisao=0, catalogo=Catalogo())
                if estado.revisao != revisao_esperada:
                    raise ErroAplicacao("CONFLITO_DE_REVISAO")
                self._preservar_historico(estado.catalogo, catalogo)
                geracao_id = uuid4().hex
                geracoes = self._arquivo(self.raiz / "generations")
                geracoes.mkdir(mode=0o700, exist_ok=True)
                temporario = geracoes / f".tmp-{geracao_id}"
                temporario.mkdir(mode=0o700)
                dados = catalogo.model_dump(mode="json")
                hashes = {}
                for colecao in COLECOES:
                    conteudo = _bytes({"schema_version": "1.0", colecao: dados[colecao]})
                    nome = f"{colecao}.json"
                    _gravar(temporario / nome, conteudo)
                    hashes[nome] = sha256(conteudo).hexdigest()
                manifesto = Manifesto(geracao=geracao_id, revisao=estado.revisao + 1, arquivos=hashes)
                conteudo_manifesto = _bytes(manifesto.model_dump(mode="json"))
                _gravar(temporario / "manifest.json", conteudo_manifesto)
                _sincronizar_diretorio(temporario)
                os.replace(temporario, geracoes / geracao_id)
                temporario = None
                _sincronizar_diretorio(geracoes)
                ponteiro_tmp = self.raiz / f".current-{geracao_id}.tmp"
                _gravar(ponteiro_tmp, conteudo_manifesto)
                os.replace(ponteiro_tmp, self.raiz / "current.json")
                ponteiro_tmp = None
                _sincronizar_diretorio(self.raiz)
                return Estado(revisao=manifesto.revisao, catalogo=catalogo)
        except ErroAplicacao:
            raise
        except Timeout:
            raise ErroAplicacao("REPOSITORIO_OCUPADO") from None
        except ValidationError:
            raise ErroAplicacao("CONTRATO_OU_REFERENCIA_INVALIDA") from None
        except OSError:
            raise ErroAplicacao("FALHA_GRAVACAO_REPOSITORIO") from None
        finally:
            if temporario is not None:
                shutil.rmtree(temporario, ignore_errors=True)
            if ponteiro_tmp is not None:
                ponteiro_tmp.unlink(missing_ok=True)
