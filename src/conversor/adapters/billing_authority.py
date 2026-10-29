"""Autoridade local, provisionada fora dos planos. Sem credenciais de administradoras."""
from hashlib import sha256
import hmac
import os
from pathlib import Path
from uuid import uuid4
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from conversor.application.billing_ports import CredencialOperador
from conversor.application.ports import ErroAplicacao
from conversor.domain.base import Hash, Id, Modelo
from conversor.domain.billing_rules import AcaoEvento, Ambiente, EventoPlano, bytes_canonicos, hash_modelo
from .json_repository import _gravar, _sincronizar_diretorio, ler_json_bytes
from .private_permissions import conferir_windows, criar_diretorio_privado


def sem_links(path: Path):
    if any(p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400)
           for p in (path, *path.parents)):
        raise ErroAplicacao('CAMINHO_COM_LINK_NAO_PERMITIDO')
    return path


def ler_protegido(path: Path):
    sem_links(path)
    conferir_windows(path)
    if os.name == 'posix' and path.stat().st_mode & 0o077:
        raise ErroAplicacao('PERMISSOES_DE_AUTORIDADE_INSEGURAS')
    return path.read_bytes()


class ConcessaoOperador(Modelo):
    responsavel_id: Id
    credencial_sha256: Hash = Field(repr=False)
    acoes: Annotated[tuple[AcaoEvento, ...], Field(min_length=1)]
    condominio_ids: Annotated[tuple[Id, ...], Field(min_length=1)]
    ambientes: Annotated[tuple[Ambiente, ...], Field(min_length=1)]


class RegistroAutoridade(Modelo):
    schema_version: Literal['1.0'] = '1.0'
    concessoes: Annotated[tuple[ConcessaoOperador, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def credenciais_unicas(self):
        if len({c.credencial_sha256 for c in self.concessoes}) != len(self.concessoes):
            raise ValueError('CREDENCIAL_DUPLICADA')
        return self


class AutoridadeHMAC:
    """Chave, concessões e ponteiro confiável fora da árvore editável dos planos.

    A conta do serviço deve proteger essa raiz por ACL. Quem controla a chave e o
    processo tem a autoridade local; este adapter não implementa IAM de produção.
    """
    def __init__(self, diretorio: str | Path):
        self.raiz = Path(os.path.abspath(diretorio))
        self._chave_path = self.raiz / 'chave.bin'
        self._registro_path = self.raiz / 'operadores.json'
        try:
            sem_links(self.raiz)
            # O ambiente pode ter diretórios .git vazios de proteção. Só um
            # gitdir de worktree (arquivo) ou diretório com HEAD indica checkout.
            if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file()
                   for p in (self.raiz, *self.raiz.parents)):
                raise ErroAplicacao('AUTORIDADE_NAO_PODE_FICAR_NO_GIT')
            if not self.raiz.is_dir():
                raise ErroAplicacao('AUTORIDADE_INDISPONIVEL')
            # Só consultar ACL após validar o destino; nenhum segredo foi lido/provisionado.
            conferir_windows(self.raiz)
            if os.name == 'posix' and self.raiz.stat().st_mode & 0o077:
                raise ErroAplicacao('PERMISSOES_DE_AUTORIDADE_INSEGURAS')
            self._chave = ler_protegido(self._chave_path)
            if len(self._chave) < 32:
                raise ErroAplicacao('CHAVE_DE_AUTORIDADE_INVALIDA')
            self._registro()
        except OSError:
            raise ErroAplicacao('AUTORIDADE_INDISPONIVEL') from None

    def _registro(self):
        try:
            return RegistroAutoridade.model_validate(ler_json_bytes(ler_protegido(self._registro_path)))
        except ValidationError:
            raise ErroAplicacao('REGISTRO_DE_AUTORIDADE_INVALIDO') from None
        except OSError:
            raise ErroAplicacao('AUTORIDADE_INDISPONIVEL') from None

    def conferir_protecao(self):
        for path in (self.raiz, self._chave_path, self._registro_path):
            sem_links(path)
            conferir_windows(path)
            if os.name == 'posix' and path.stat().st_mode & 0o077:
                raise ErroAplicacao('PERMISSOES_DE_AUTORIDADE_INSEGURAS')
        if not hmac.compare_digest(ler_protegido(self._chave_path), self._chave):
            raise ErroAplicacao('CHAVE_DE_AUTORIDADE_ALTERADA')

    def conferir_isolamento(self, raiz: Path):
        sem_links(raiz)
        if self.raiz.is_relative_to(raiz) or raiz.is_relative_to(self.raiz):
            raise ErroAplicacao('AUTORIDADE_DEVE_SER_EXTERNA_AOS_PLANOS')

    def autorizar(self, credencial: CredencialOperador, acao, plano, ambiente):
        if not isinstance(credencial, CredencialOperador):
            raise ErroAplicacao('CREDENCIAL_INVALIDA')
        registro = self._registro()
        digest = sha256(credencial.segredo.encode()).hexdigest()
        concessao = next((c for c in registro.concessoes if hmac.compare_digest(c.credencial_sha256, digest)), None)
        if concessao is None or acao not in concessao.acoes or plano.condominio_id not in concessao.condominio_ids or ambiente not in concessao.ambientes:
            raise ErroAplicacao('OPERACAO_NAO_AUTORIZADA')
        digest_registro = hash_modelo(registro)
        # Arquivar a política efetivamente consultada, para verificar a permissão
        # histórica sem depender da lista atual (que pode revogar um operador).
        pasta = sem_links(self.raiz / 'policies')
        criar_diretorio_privado(pasta)
        destino = sem_links(pasta / (digest_registro + '.json'))
        if not destino.exists():
            temporario = pasta / ('.' + uuid4().hex + '.tmp')
            try:
                _gravar(temporario, bytes_canonicos(registro.model_dump(mode='json')))
                os.replace(temporario, destino)
                _sincronizar_diretorio(pasta)
                _sincronizar_diretorio(self.raiz)
            finally:
                temporario.unlink(missing_ok=True)
        # Também detectar arquivo existente adulterado, antes de emitir recibo.
        self._politica_historica(digest_registro)
        return concessao.responsavel_id, digest_registro

    def _politica_historica(self, digest):
        try:
            path = self.raiz / 'policies' / (digest + '.json')
            registro = RegistroAutoridade.model_validate(ler_json_bytes(ler_protegido(path)))
            if hash_modelo(registro) != digest:
                raise ErroAplicacao('POLITICA_HISTORICA_ADULTERADA')
            return registro
        except ValidationError:
            raise ErroAplicacao('POLITICA_HISTORICA_INVALIDA') from None
        except OSError:
            raise ErroAplicacao('POLITICA_HISTORICA_INDISPONIVEL') from None

    def assinar(self, dados, *, dominio):
        return hmac.new(self._chave, dominio.encode() + b'\0' + bytes_canonicos(dados), 'sha256').hexdigest()

    def verificar(self, dados, assinatura, *, dominio):
        if not hmac.compare_digest(self.assinar(dados, dominio=dominio), assinatura):
            raise ErroAplicacao('ASSINATURA_DE_AUTORIDADE_INVALIDA')

    def conferir_evento(self, evento: EventoPlano):
        dados = evento.model_dump(mode='json', exclude={'assinatura'})
        self.verificar(dados, evento.assinatura, dominio='evento-plano-1.0')
        self.conferir_autorizacao_historica(evento.responsavel_id, evento.politica_autorizacao_hash,
            acao=evento.acao, condominio_id=evento.condominio_id, ambiente=evento.ambiente)

    def conferir_autorizacao_historica(self, responsavel_id, politica_hash, *, acao, condominio_id, ambiente):
        """Verifica recibos históricos sem conceder novas permissões administrativas."""
        registro = self._politica_historica(politica_hash)
        if not any(c.responsavel_id == responsavel_id and acao in c.acoes
                   and condominio_id in c.condominio_ids and ambiente in c.ambientes
                   for c in registro.concessoes):
            raise ErroAplicacao('EVENTO_SEM_AUTORIZACAO_HISTORICA')
