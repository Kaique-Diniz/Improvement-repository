"""Gerações imutáveis; commit atômico no manifesto da autoridade externa."""
from hashlib import sha256
import os
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import Field, TypeAdapter, ValidationError

from conversor.application.billing_ports import CredencialOperador
from conversor.application.ports import ErroAplicacao, RepositorioCondominios
from conversor.domain.base import Hash, Id, Modelo
from conversor.domain.billing_rules import (AcervoPlanos, Ambiente, ComandoPlano, ErroPlano, EstadoPlanos,
                                           EventoPlano, bytes_canonicos, hash_modelo)
from conversor.domain.billing_lifecycle import acrescentar_evento, conferir_acervo
from .billing_authority import AutoridadeHMAC, ler_protegido, sem_links
from .json_repository import _gravar, _sincronizar_diretorio, ler_json_bytes


class ManifestoPlanos(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    repositorio_id: Id
    raiz_hash: Hash
    ambiente: Ambiente
    revisao: int = Field(strict=True, ge=1)
    geracao: Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')]
    sha256: Hash
    assinatura: Hash = Field(repr=False)


class RepositorioPlanosJSON:
    def __init__(self, diretorio: str | Path, *, repositorio_id: str, ambiente: Ambiente,
                 autoridade: AutoridadeHMAC, condominios: RepositorioCondominios, timeout=5):
        try:
            self.id = TypeAdapter(Id).validate_python(repositorio_id)
            self.ambiente = TypeAdapter(Ambiente).validate_python(ambiente)
        except ValidationError:
            raise ErroAplicacao('IDENTIDADE_OU_AMBIENTE_INVALIDO') from None
        self.raiz = Path(os.path.abspath(diretorio))
        self.autoridade = autoridade
        autoridade.conferir_isolamento(self.raiz)
        self.condominios = condominios
        self.timeout = timeout
        self.ponteiro = autoridade.raiz / (self.id + '.current.json')
        self.lock = autoridade.raiz / (self.id + '.lock')
        self.raiz_hash = sha256(str(self.raiz).encode()).hexdigest()

    def _conferir_condominios(self, acervo):
        for cid in {r.conteudo.condominio_id for r in acervo.registros}:
            condominio = self.condominios.get_condominio(cid)
            if condominio.id != cid:
                raise ErroAplicacao('REFERENCIA_DE_CONDOMINIO_INVALIDA')

    def carregar(self) -> EstadoPlanos:
        try:
            self.autoridade.conferir_protecao()
            sem_links(self.raiz)
            if not self.ponteiro.exists():
                raise ErroAplicacao('REPOSITORIO_DE_PLANOS_NAO_INICIALIZADO')
            bruto = ler_json_bytes(ler_protegido(self.ponteiro))
            if not isinstance(bruto, dict) or bruto.get('schema_version') != '1.0':
                raise ErroAplicacao('SCHEMA_DE_PLANOS_NAO_SUPORTADO')
            manifesto = ManifestoPlanos.model_validate(bruto)
            self.autoridade.verificar(manifesto.model_dump(mode='json', exclude={'assinatura'}),
                                     manifesto.assinatura, dominio='manifesto-planos-1.0')
            if (manifesto.repositorio_id, manifesto.raiz_hash, manifesto.ambiente) != (self.id, self.raiz_hash, self.ambiente):
                raise ErroAplicacao('MANIFESTO_DE_OUTRO_REPOSITORIO')
            arquivo = sem_links(self.raiz / 'generations' / (manifesto.geracao + '.json'))
            conteudo = arquivo.read_bytes()
            if sha256(conteudo).hexdigest() != manifesto.sha256:
                raise ErroAplicacao('SNAPSHOT_DE_PLANOS_ADULTERADO')
            dados = ler_json_bytes(conteudo)
            if not isinstance(dados, dict) or dados.get('schema_version') != '1.0':
                raise ErroAplicacao('SCHEMA_DE_PLANOS_NAO_SUPORTADO')
            acervo = AcervoPlanos.model_validate(dados)
            if len(acervo.eventos) != manifesto.revisao or acervo.ambiente != self.ambiente:
                raise ErroAplicacao('REVISAO_OU_AMBIENTE_DIVERGENTE')
            for evento in acervo.eventos:
                self.autoridade.conferir_evento(evento)
            conferir_acervo(acervo)
            self._conferir_condominios(acervo)
            return EstadoPlanos(revisao=manifesto.revisao, acervo=acervo)
        except ErroAplicacao:
            raise
        except ErroPlano as erro:
            raise ErroAplicacao(str(erro)) from None
        except ValidationError:
            raise ErroAplicacao('CONTRATO_DE_PLANOS_INVALIDO') from None
        except OSError:
            raise ErroAplicacao('FALHA_LEITURA_PLANOS') from None

    def executar(self, comando: ComandoPlano, *, credencial: CredencialOperador,
                 revisao_esperada: int) -> EstadoPlanos:
        temporario = None
        try:
            self.autoridade.conferir_protecao()
            # Revalidar objetos construídos por model_copy/model_construct também.
            comando = ComandoPlano.model_validate(comando.model_dump(warnings=False))
            if type(revisao_esperada) is not int or revisao_esperada < 0:
                raise ErroAplicacao('REVISAO_ESPERADA_INVALIDA')
            sem_links(self.lock)
            with FileLock(self.lock, timeout=self.timeout, mode=0o600):
                if self.ponteiro.exists():
                    anterior = self.carregar()
                else:
                    anterior = EstadoPlanos(revisao=0, acervo=AcervoPlanos(ambiente=self.ambiente))
                if anterior.revisao != revisao_esperada:
                    raise ErroAplicacao('CONFLITO_DE_REVISAO')
                if comando.plano is not None:
                    plano = comando.plano
                else:
                    registro = next((r for r in anterior.acervo.registros if r.conteudo.id == comando.plano_id), None)
                    if registro is None:
                        raise ErroAplicacao('PLANO_INEXISTENTE')
                    plano = registro.conteudo
                responsavel, politica_hash = self.autoridade.autorizar(credencial, comando.acao, plano, self.ambiente)
                dados_evento = {
                    'schema_version': '1.0', 'sequencia': anterior.revisao + 1, 'ambiente': self.ambiente, 'plano_id': plano.id,
                    'condominio_id': plano.condominio_id, 'versao': plano.versao,
                    'hash_conteudo': hash_modelo(plano), 'acao': comando.acao, 'responsavel_id': responsavel,
                    'em': comando.em.isoformat(), 'fundamento': comando.fundamento, 'evidencia_id': comando.evidencia_id,
                    'data_ref': comando.data_ref.isoformat() if comando.data_ref else None,
                    'hash_anterior': hash_modelo(anterior.acervo.eventos[-1]) if anterior.acervo.eventos else '0' * 64,
                    'politica_autorizacao_hash': politica_hash,
                }
                normalizado = EventoPlano.model_validate(dados_evento | {'assinatura': '0' * 64})
                dados_evento = normalizado.model_dump(mode='json', exclude={'assinatura'})
                assinatura = self.autoridade.assinar(dados_evento, dominio='evento-plano-1.0')
                evento = EventoPlano.model_validate(dados_evento | {'assinatura': assinatura})
                novo = acrescentar_evento(anterior.acervo, evento, comando.plano)
                self._conferir_condominios(novo)
                # Uma geração nova não sobrescreve conteúdo de nenhuma versão anterior.
                geracoes = sem_links(self.raiz / 'generations')
                geracoes.mkdir(parents=True, mode=0o700, exist_ok=True)
                if os.name == 'posix':
                    os.chmod(self.raiz, 0o700)
                geracao = uuid4().hex
                conteudo = bytes_canonicos(novo.model_dump(mode='json'))
                _gravar(geracoes / (geracao + '.json'), conteudo)
                _sincronizar_diretorio(geracoes)
                _sincronizar_diretorio(self.raiz)
                dados_manifesto = {'schema_version': '1.0', 'repositorio_id': self.id, 'raiz_hash': self.raiz_hash,
                    'ambiente': self.ambiente, 'revisao': anterior.revisao + 1, 'geracao': geracao,
                    'sha256': sha256(conteudo).hexdigest()}
                manifesto = ManifestoPlanos.model_validate(dados_manifesto | {
                    'assinatura': self.autoridade.assinar(dados_manifesto, dominio='manifesto-planos-1.0')})
                temporario = self.autoridade.raiz / ('.' + self.id + '-' + geracao + '.tmp')
                _gravar(temporario, bytes_canonicos(manifesto.model_dump(mode='json')))
                # Ponto único de commit, protegido pela autoridade externa e pelo lock.
                os.replace(temporario, self.ponteiro)
                temporario = None
                _sincronizar_diretorio(self.autoridade.raiz)
                return EstadoPlanos(revisao=anterior.revisao + 1, acervo=novo)
        except ErroAplicacao:
            raise
        except ErroPlano as erro:
            raise ErroAplicacao(str(erro)) from None
        except Timeout:
            raise ErroAplicacao('REPOSITORIO_DE_PLANOS_OCUPADO') from None
        except ValidationError:
            raise ErroAplicacao('CONTRATO_DE_PLANOS_INVALIDO') from None
        except UnicodeError:
            raise ErroAplicacao('TEXTO_DE_PLANOS_INVALIDO') from None
        except OSError:
            raise ErroAplicacao('FALHA_GRAVACAO_PLANOS') from None
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    pass  # Não mascarar a falha original nem publicar o temporário.
