"""Objetos imutáveis privados; recibo externo assinado é o único ponto de commit."""
from functools import wraps
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import TypeAdapter, ValidationError

from conversor.application.ports import ErroAplicacao
from conversor.application.simulation_inventory import conferir_pacote, conferir_resultado_preservado
from conversor.domain.base import Id
from conversor.domain.billing_rules import Ambiente, ErroPlano, bytes_canonicos, hash_modelo
from conversor.domain.private_simulation import ExecucaoPrivada, PacotePrivado, ReciboPrivado
from conversor.domain.simulation_comparison import ComparacaoPrivada
from conversor.domain.audit_identity import (PacoteReconciliado, ReconciliacaoOcorrencias, ReciboReconciliacao,
    PreparacaoTecnica, ReciboPreparacaoTecnica)
from .billing_authority import ler_protegido, sem_links
from .json_repository import _gravar, _sincronizar_diretorio, ler_json_bytes
from .private_permissions import conferir_windows, criar_diretorio_privado


def seguro(funcao):
    @wraps(funcao)
    def executar(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except ErroAplicacao:
            raise
        except (ValidationError, UnicodeError, ValueError, ErroPlano):
            raise ErroAplicacao('CONTRATO_PRIVADO_INVALIDO') from None
        except Timeout:
            raise ErroAplicacao('REPOSITORIO_PRIVADO_OCUPADO') from None
        except OSError:
            raise ErroAplicacao('ARTEFATO_PRIVADO_INDISPONIVEL') from None
    return executar


def conferir_local_privado(caminho, *, arquivo=False):
    path = sem_links(Path(os.path.abspath(caminho)))
    if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file()
           for p in ((path.parent if arquivo else path), *path.parents)):
        raise ErroAplicacao('ARTEFATO_PRIVADO_NAO_PODE_FICAR_NO_GIT')
    if arquivo and not path.is_file():
        raise ErroAplicacao('FONTE_PRIVADA_INDISPONIVEL')
    if not arquivo and not path.is_dir():
        raise ErroAplicacao('DIRETORIO_PRIVADO_INDISPONIVEL')
    conferir_windows(path)
    if os.name == 'posix' and path.stat().st_mode & 0o077:
        raise ErroAplicacao('PERMISSOES_PRIVADAS_INSEGURAS')
    return path


def conferir_fontes(pacote):
    for fonte in pacote.fontes:
        path = conferir_local_privado(fonte.caminho, arquivo=True)
        conteudo = ler_protegido(path)
        if len(conteudo) != fonte.tamanho or sha256(conteudo).hexdigest() != fonte.sha256:
            raise ErroAplicacao('FONTE_PRIVADA_ALTERADA_OU_PARCIAL')


class VerificadorHistoricoHMAC:
    """Só recibos 4.1 autênticos. Não atesta vigência administrativa ATUAL."""
    def __init__(self, autoridade):
        self.autoridade = autoridade

    @seguro
    def conferir(self, estado):
        from conversor.domain.billing_rules import EstadoPlanos
        from conversor.domain.billing_lifecycle import conferir_acervo
        self.autoridade.conferir_protecao()
        estado = EstadoPlanos.model_validate(estado.model_dump(warnings=False))
        if estado.revisao != len(estado.acervo.eventos):
            raise ErroAplicacao('REVISAO_HISTORICA_INCONSISTENTE')
        for evento in estado.acervo.eventos:
            self.autoridade.conferir_evento(evento)
        conferir_acervo(estado.acervo)


class RepositorioSimulacoesJSON:
    @seguro
    def __init__(self, diretorio, *, repositorio_id, ambiente, autoridade, timeout=5):
        self.id = TypeAdapter(Id).validate_python(repositorio_id)
        self.ambiente = TypeAdapter(Ambiente).validate_python(ambiente)
        self.raiz = Path(os.path.abspath(diretorio))
        sem_links(self.raiz)
        # Validar Git ANTES de criar diretório/artefato.
        if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file()
               for p in (self.raiz, *self.raiz.parents)):
            raise ErroAplicacao('ARTEFATO_PRIVADO_NAO_PODE_FICAR_NO_GIT')
        autoridade.conferir_protecao()
        autoridade.conferir_isolamento(self.raiz)
        criar_diretorio_privado(self.raiz,parents=True)
        conferir_local_privado(self.raiz)
        self.autoridade = autoridade
        self.raiz_hash = sha256(str(self.raiz).encode()).hexdigest()
        self.ancoras = autoridade.raiz / ('simulacoes-' + self.id)
        criar_diretorio_privado(sem_links(self.ancoras))
        conferir_local_privado(self.ancoras)
        _sincronizar_diretorio(autoridade.raiz)
        self.timeout = timeout
        self.lock = self.ancoras / 'escrita.lock'

    def _paths(self, tipo, id_):
        id_ = TypeAdapter(Id).validate_python(id_)
        # Id admite dois-pontos, mas nunca barras/ponto-ponto como componente.
        nome = tipo + '-' + id_ + '.json'
        return sem_links(self.raiz / nome), sem_links(self.ancoras / nome)

    def _guardar(self, tipo, objeto, credencial, modelo_recibo=ReciboPrivado):
        self.autoridade.conferir_protecao()
        conferir_local_privado(self.raiz)
        conferir_local_privado(self.ancoras)
        if objeto.ambiente != self.ambiente:
            raise ErroAplicacao('ARTEFATO_DE_OUTRO_AMBIENTE')
        # Submeter autoriza o registro técnico de um pacote/simulação, não aprovar/ativar regras.
        ator, politica = self.autoridade.autorizar(credencial, 'submeter', objeto, self.ambiente)
        destino, ancora = self._paths(tipo, objeto.id)
        sem_links(self.lock)
        with FileLock(self.lock, timeout=self.timeout, mode=0o600):
            if ancora.exists():
                raise ErroAplicacao('ARTEFATO_PRIVADO_IMUTAVEL_JA_EXISTE')
            conteudo = bytes_canonicos(objeto.model_dump(mode='json'))
            dados = dict(schema_version='1.0', repositorio_id=self.id, raiz_hash=self.raiz_hash, tipo=tipo,
                id=objeto.id, condominio_id=objeto.condominio_id, ambiente=self.ambiente,
                sha256=sha256(conteudo).hexdigest(), responsavel_id=ator, politica_autorizacao_hash=politica)
            recibo = modelo_recibo(**dados, assinatura=self.autoridade.assinar(dados, dominio='artefato-privado-1.0'))
            # Um órfão sem recibo nunca pode ser lido. Repetição explícita após falha pode substituí-lo.
            temporario = self.raiz / ('.' + uuid4().hex + '.tmp')
            temp_recibo = self.ancoras / ('.' + uuid4().hex + '.tmp')
            try:
                _gravar(temporario, conteudo)
                os.replace(temporario, destino)
                _sincronizar_diretorio(self.raiz)
                _gravar(temp_recibo, bytes_canonicos(recibo.model_dump(mode='json')))
                os.replace(temp_recibo, ancora)
                _sincronizar_diretorio(self.ancoras)
            finally:
                temporario.unlink(missing_ok=True)
                temp_recibo.unlink(missing_ok=True)

    def _ler(self, tipo, id_, modelo, modelo_recibo=ReciboPrivado):
        self.autoridade.conferir_protecao()
        conferir_local_privado(self.raiz)
        conferir_local_privado(self.ancoras)
        destino, ancora = self._paths(tipo, id_)
        recibo = modelo_recibo.model_validate(ler_json_bytes(ler_protegido(ancora)))
        self.autoridade.verificar(recibo.model_dump(mode='json', exclude={'assinatura'}), recibo.assinatura,
                                  dominio='artefato-privado-1.0')
        if (recibo.repositorio_id, recibo.raiz_hash, recibo.tipo, recibo.id, recibo.ambiente) != (
                self.id, self.raiz_hash, tipo, id_, self.ambiente):
            raise ErroAplicacao('RECIBO_DE_OUTRO_ARTEFATO_PRIVADO')
        self.autoridade.conferir_autorizacao_historica(recibo.responsavel_id, recibo.politica_autorizacao_hash,
            acao='submeter', condominio_id=recibo.condominio_id, ambiente=recibo.ambiente)
        conteudo = ler_protegido(destino)
        if sha256(conteudo).hexdigest() != recibo.sha256:
            raise ErroAplicacao('ARTEFATO_PRIVADO_ADULTERADO')
        dados = ler_json_bytes(conteudo)
        if tipo == 'pacote':
            modelo = _modelo_pacote(dados)
        objeto = modelo.model_validate(dados)
        if (objeto.id, objeto.condominio_id, objeto.ambiente) != (id_, recibo.condominio_id, self.ambiente):
            raise ErroAplicacao('IDENTIDADE_PRIVADA_DIVERGENTE')
        return objeto

    @seguro
    def gravar_pacote(self, pacote, *, credencial):
        dados = pacote.model_dump(warnings=False)
        pacote = _modelo_pacote(dados).model_validate(dados)
        conferir_pacote(pacote)
        conferir_fontes(pacote)
        _conferir_historico_pacote(pacote)
        self._guardar('pacote', pacote, credencial)

    @seguro
    def carregar_pacote(self, id_):
        pacote = self._ler('pacote', id_, PacotePrivado)
        conferir_pacote(pacote)
        conferir_fontes(pacote)
        _conferir_historico_pacote(pacote)
        return pacote

    @seguro
    def gravar_execucao(self, execucao, *, credencial):
        execucao = ExecucaoPrivada.model_validate(execucao.model_dump(warnings=False))
        pacote = self.carregar_pacote(execucao.pacote_id)
        if (hash_modelo(pacote), pacote.condominio_id, pacote.ambiente) != (
                execucao.pacote_hash, execucao.condominio_id, execucao.ambiente):
            raise ErroAplicacao('EXECUCAO_DE_OUTRO_PACOTE')
        conferir_resultado_preservado(execucao, pacote)
        self._guardar('execucao', execucao, credencial)

    @seguro
    def carregar_execucao(self, id_):
        return self._ler('execucao', id_, ExecucaoPrivada)

    @seguro
    def gravar_comparacao(self, comparacao, *, credencial):
        comparacao = ComparacaoPrivada.model_validate(comparacao.model_dump(warnings=False))
        execucao = self.carregar_execucao(comparacao.execucao_id)
        if (hash_modelo(execucao), execucao.condominio_id, execucao.ambiente) != (
                comparacao.execucao_hash, comparacao.condominio_id, comparacao.ambiente):
            raise ErroAplicacao('COMPARACAO_DE_OUTRA_EXECUCAO')
        self._guardar('comparacao', comparacao, credencial)

    @seguro
    def carregar_comparacao(self, id_):
        return self._ler('comparacao', id_, ComparacaoPrivada)

    @seguro
    def gravar_reconciliacao(self, reconciliacao, *, credencial):
        from .audit_history import conferir_reconciliacao
        reconciliacao = ReconciliacaoOcorrencias.model_validate(reconciliacao.model_dump(warnings=False))
        conferir_reconciliacao(reconciliacao)
        self._guardar('reconciliacao', reconciliacao, credencial, ReciboReconciliacao)

    @seguro
    def carregar_reconciliacao(self, id_):
        from .audit_history import conferir_reconciliacao
        reconciliacao = self._ler('reconciliacao', id_, ReconciliacaoOcorrencias, ReciboReconciliacao)
        conferir_reconciliacao(reconciliacao)
        return reconciliacao

    @seguro
    def gravar_preparacao_tecnica(self, preparacao, *, credencial):
        preparacao = PreparacaoTecnica.model_validate(preparacao.model_dump(warnings=False))
        _conferir_preparacao_tecnica(preparacao)
        self._guardar('preparacao_tecnica', preparacao, credencial, ReciboPreparacaoTecnica)

    @seguro
    def carregar_preparacao_tecnica(self, id_):
        preparacao = self._ler('preparacao_tecnica', id_, PreparacaoTecnica, ReciboPreparacaoTecnica)
        _conferir_preparacao_tecnica(preparacao)
        return preparacao


def _modelo_pacote(dados):
    versao = dados.get('schema_version')
    if versao == '1.0':
        return PacotePrivado
    if versao == '1.1':
        return PacoteReconciliado
    raise ErroAplicacao('SCHEMA_DE_PACOTE_PRIVADO_NAO_SUPORTADO')


def _conferir_historico_pacote(pacote):
    if isinstance(pacote, PacoteReconciliado):
        from .audit_history import conferir_reconciliacao
        conferir_reconciliacao(pacote.reconciliacao)


def _conferir_preparacao_tecnica(preparacao):
    from .audit_history import conferir_reconciliacao
    conferir_pacote(preparacao.candidato)
    conferir_fontes(preparacao.candidato)
    conferir_reconciliacao(preparacao.candidato.reconciliacao)
