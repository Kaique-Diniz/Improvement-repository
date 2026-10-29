"""Histórico privado HMAC, CAS e evidências por conteúdo; sem aprovações implícitas."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from hashlib import sha256
import hmac
import os
from pathlib import Path
import secrets
import re

from filelock import FileLock, Timeout
from pydantic import ValidationError

from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.document_links import (AcervoVinculos, AprovacaoVinculo, EventoVinculo,
    SnapshotVinculos, VinculoDocumental)
from conversor.readers.text_support import ErroLeitura
from .billing_authority import sem_links, ler_protegido
from .json_repository import ler_json_bytes, _gravar, _sincronizar_diretorio
from .private_json import escrever_json
from .private_simulation_json import conferir_local_privado
from .private_permissions import criar_diretorio_privado


def protegido(func):
    @wraps(func)
    def chamar(*a, **kw):
        try:
            return func(*a, **kw)
        except ErroLeitura:
            raise
        except Timeout:
            raise ErroLeitura('CADASTRO_VINCULOS_OCUPADO') from None
        except (OSError, ValueError, ValidationError, ErroAplicacao, TypeError, KeyError):
            raise ErroLeitura('CADASTRO_VINCULOS_INVALIDO_OU_ADULTERADO') from None
    return chamar


class RepositorioVinculosJSON:
    @protegido
    def __init__(self, private_dir):
        self.privado = Path(os.path.abspath(private_dir))
        conferir_local_privado(self.privado)
        self.raiz = self.privado / 'vinculos_documentais'
        self._caminho(self.raiz)
        criar_diretorio_privado(self.raiz)
        conferir_local_privado(self.raiz)
        self.path = self.raiz / 'registro.json'
        self.key = self.raiz / 'chave.bin'
        self.lock = self.raiz / 'escrita.lock'
        self.fontes = self.raiz / 'evidencias'
        self.cabecas = self.raiz / 'cabecas'

    def _caminho(self, path):
        sem_links(path)
        if not path.is_relative_to(self.privado):
            raise ValueError('FORA_DA_AREA_PRIVADA')
        for p in (path, *path.parents):
            # Junction/reparse points Windows também são recusados.
            if p.exists() and getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('CAMINHO_REPARSE')
        if path.exists() and path.is_file() and path.stat().st_nlink != 1:
            raise ValueError('ARQUIVO_COM_LINK_FISICO')
        return path

    @contextmanager
    def _travar(self):
        conferir_local_privado(self.privado); conferir_local_privado(self.raiz)
        self._caminho(self.lock)
        with FileLock(self.lock, timeout=5, mode=0o600):
            for p in (self.path, self.key, self.fontes, self.cabecas): self._caminho(p)
            yield

    def _chave(self, *, criar=False):
        if not self.key.exists() and criar and not self.path.exists():
            _gravar(self.key, secrets.token_bytes(32))
        key = ler_protegido(self.key)
        if len(key) != 32: raise ValueError('CHAVE_INVALIDA')
        return key

    def _assinar(self, dados):
        return hmac.new(self._chave(), b'vinculos-documentais-1.0\0'+bytes_canonicos(dados), 'sha256').hexdigest()

    def _carregar(self):
        if not self.path.exists():
            if self.cabecas.exists() and any(self.cabecas.iterdir()):raise ValueError('HISTORICO_REMOVIDO')
            return self._snapshot(AcervoVinculos())
        if self.path.stat().st_size>32*1024*1024:raise ValueError('ACERVO_FORA_DO_LIMITE')
        envelope = ler_json_bytes(ler_protegido(self.path))
        if set(envelope) != {'acervo', 'assinatura'} or not hmac.compare_digest(self._assinar(envelope['acervo']), envelope['assinatura']):
            raise ValueError('ASSINATURA_INVALIDA')
        acervo = AcervoVinculos.model_validate(envelope['acervo']); anteriores={}; head='0'*64
        for n, evento in enumerate(acervo.eventos, 1):
            dados=evento.model_dump(mode='json', exclude={'assinatura'})
            if evento.sequencia != n or evento.anterior_sha256 != head or not hmac.compare_digest(self._assinar(dados), evento.assinatura):
                raise ValueError('HISTORICO_ADULTERADO')
            r=evento.registro; prev=anteriores.get(r.id)
            if r.versao != (prev.versao+1 if prev else 1): raise ValueError('VERSAO_INCONSISTENTE')
            if evento.acao=='aprovar' and (not prev or prev.estado!='candidato' or not r.aprovacao or
                    r.aprovacao.conteudo_aprovado_sha256!=hash_modelo(prev) or
                    r.aprovacao.responsavel!=evento.responsavel or r.aprovacao.sessao_sha256!=evento.sessao_sha256):
                raise ValueError('APROVACAO_DESVINCULADA_DO_CONTEUDO')
            if evento.acao=='reabrir':
                imutaveis={'versao','estado','aprovacao','atualizado_em','motivo'}
                if (not prev or prev.estado!='revogado' or r.estado!='candidato' or r.aprovacao is not None or
                        r.model_dump(exclude=imutaveis)!=prev.model_dump(exclude=imutaveis)):
                    raise ValueError('REABERTURA_DESVINCULADA_DO_HISTORICO')
            if r.estado=='aprovado' and (evento.acao!='aprovar' and (not prev or prev.estado!='aprovado')):
                raise ValueError('APROVACAO_SEM_ACAO_EXPLICITA')
            anteriores[r.id]=r; head=hash_modelo(evento)
        snapshot=self._snapshot(acervo)
        if not self.cabecas.is_dir():raise ValueError('CABECALHO_IMUTAVEL_AUSENTE')
        heads=sorted(self.cabecas.iterdir())
        if not heads:raise ValueError('CABECALHO_IMUTAVEL_AUSENTE')
        for path in heads:
            self._caminho(path)
            if not path.is_file()or not re.fullmatch('[0-9]{20}\\.json',path.name):raise ValueError('CABECALHO_INVALIDO')
        if heads[-1].name!=f'{snapshot.revisao:020d}.json':raise ValueError('HISTORICO_REVERTIDO_OU_PARCIAL')
        head=ler_json_bytes(ler_protegido(self._caminho(heads[-1])))
        if set(head)!={'revisao','sha256','assinatura'}:raise ValueError('CABECALHO_INVALIDO')
        dados={k:head[k]for k in ('revisao','sha256')}
        if head['revisao']!=snapshot.revisao or head['sha256']!=snapshot.sha256 or not hmac.compare_digest(self._assinar(dados),head['assinatura']):
            raise ValueError('HISTORICO_REVERTIDO_OU_PARCIAL')
        vistos=set()
        for evento in acervo.eventos:self._conferir_fontes(evento.registro,vistos)
        return snapshot

    def _snapshot(self, acervo):
        return SnapshotVinculos(revisao=len(acervo.eventos), sha256=hash_modelo(acervo), acervo=acervo)

    def _conferir_fontes(self, registro, vistos=None):
        if vistos is None:vistos=set()
        for e in (*registro.evidencias, *(e for p in registro.pendencias_documentais for e in p.evidencias)):
            if e.origem.sha256 in vistos:continue
            path=self._caminho(self.fontes / (e.origem.sha256+'.bin'))
            if path.stat().st_size>20*1024*1024:raise ValueError('FONTE_FORA_DO_LIMITE')
            raw=ler_protegido(path)
            if sha256(raw).hexdigest()!=e.origem.sha256: raise ValueError('EVIDENCIA_ADULTERADA')
            vistos.add(e.origem.sha256)

    def _persistir(self, snapshot):
        body=snapshot.acervo.model_dump(mode='json')
        criar_diretorio_privado(self.cabecas)
        path=self._caminho(self.cabecas/f'{snapshot.revisao:020d}.json')
        if path.exists():raise ValueError('REVISAO_IMUTAVEL_JA_EXISTE')
        head={'revisao':snapshot.revisao,'sha256':snapshot.sha256}
        # Em falha entre os dois arquivos, o próximo acesso retém por integridade.
        _gravar(path,bytes_canonicos(head|{'assinatura':self._assinar(head)}))
        escrever_json(self.path,{'acervo':body,'assinatura':self._assinar(body)})
        _sincronizar_diretorio(self.raiz)

    def _gravar_evento(self, s, registro, acao, responsavel, sessao, fundamento, *, persistir=True):
        self._chave(criar=True)
        dados=dict(sequencia=s.revisao+1, acao=acao, registro=registro.model_dump(mode='json'),
            responsavel=responsavel, sessao_sha256=sessao, fundamento=fundamento,
            anterior_sha256=hash_modelo(s.acervo.eventos[-1]) if s.acervo.eventos else '0'*64)
        evento=EventoVinculo.model_validate(dados|{'assinatura':self._assinar(dados)})
        acervo=AcervoVinculos(eventos=(*s.acervo.eventos, evento));snapshot=self._snapshot(acervo)
        if persistir:self._persistir(snapshot)
        return snapshot

    @protegido
    def consultar(self):
        with self._travar():
            return self._carregar()

    @protegido
    def guardar_fonte(self, conteudo):
        if not conteudo or len(conteudo)>20*1024*1024: raise ValueError('FONTE_INVALIDA')
        digest=sha256(conteudo).hexdigest()
        with self._travar():
            self._carregar()  # Nunca substituir acervo inválido.
            self._chave(criar=True)
            criar_diretorio_privado(self.fontes)
            path=self._caminho(self.fontes/(digest+'.bin'))
            if path.exists():
                if sha256(ler_protegido(path)).hexdigest()!=digest: raise ValueError('FONTE_ADULTERADA')
            else: _gravar(path, conteudo)
        return digest

    @protegido
    def ler_fonte(self, digest):
        if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('HASH_DE_FONTE_INVALIDO')
        with self._travar():
            self._carregar()
            raw=ler_protegido(self._caminho(self.fontes/(digest+'.bin')))
            if sha256(raw).hexdigest()!=digest:raise ValueError('FONTE_ADULTERADA')
            return raw

    @protegido
    def impressao(self, valor):
        with self._travar():
            self._chave(criar=True)
            return hmac.new(self._chave(), b'identidade-documental\0'+valor.encode(), 'sha256').hexdigest()

    @protegido
    def candidatar(self, registros, *, revisao_esperada, responsavel, sessao_sha256):
        with self._travar():
            s=self._carregar()
            if type(revisao_esperada)is not int or s.revisao!=revisao_esperada: raise ErroLeitura('VINCULOS_ALTERADOS_RECARREGUE')
            # Validar a importação inteira antes de qualquer gravação.
            if len({r.id for r in registros})!=len(registros):raise ValueError('CANDIDATO_DUPLICADO')
            original=s
            for registro in registros:
                old=s.registros.get(registro.id)
                if old and old.estado not in ('revogado','recusado') and (old.condominio_destino_id,old.codigo_destino)!=(registro.condominio_destino_id,registro.codigo_destino):
                    raise ErroLeitura('UNIDADE_COM_DESTINO_CONFLITANTE')
                if registro.estado!='candidato' or registro.aprovacao:raise ValueError('IMPORTACAO_NAO_APROVA')
                self._conferir_fontes(registro)
            for registro in registros:
                old=s.registros.get(registro.id)
                if old and old.estado=='aprovado':continue
                if old and old.estado in ('revogado','recusado') and old.evidencias==registro.evidencias:continue
                if old:
                    if old.nome_financeiro_hmac==registro.nome_financeiro_hmac and old.evidencias==registro.evidencias and old.perfil_sha256==registro.perfil_sha256 and old.estado=='candidato':continue
                    registro=registro.model_copy(update={'versao':old.versao+1,'registrado_em':old.registrado_em,
                        'pendencias_documentais':tuple({p.id:p for p in (*old.pendencias_documentais,*registro.pendencias_documentais)}.values())})
                if registro.estado!='candidato' or registro.aprovacao: raise ValueError('IMPORTACAO_NAO_APROVA')
                s=self._gravar_evento(s,registro,'candidatar',responsavel,sessao_sha256,
                    'Candidato obtido por confronto documental estrito; aprovação pendente.',persistir=False)
            if s.sha256!=original.sha256:self._persistir(s)
            return s

    @protegido
    def decidir(self, id_, *, acao, revisao_esperada, conteudo_sha256, responsavel, sessao_sha256,
                fundamento, confirmar_evidencias, revalidar_ate=None, comprovacao_reabertura=None):
        with self._travar():
            s=self._carregar();r=s.registros.get(id_)
            if type(revisao_esperada)is not int or s.revisao!=revisao_esperada or not r or hash_modelo(r)!=conteudo_sha256:
                raise ErroLeitura('VINCULOS_ALTERADOS_RECARREGUE')
            if acao not in ('aprovar','recusar','revogar','reabrir') or not responsavel.strip() or not fundamento.strip():raise ValueError('DECISAO_INVALIDA')
            now=datetime.now(timezone.utc);changes={'versao':r.versao+1,'atualizado_em':now,'motivo':fundamento}
            if acao=='aprovar':
                if not confirmar_evidencias or r.estado!='candidato':raise ErroLeitura('CANDIDATO_COMPROVADO_EXIGE_CONFIRMACAO')
                self._conferir_fontes(r)
                changes.update(estado='aprovado',revalidar_ate=revalidar_ate,
                    aprovacao=AprovacaoVinculo(responsavel=responsavel,sessao_sha256=sessao_sha256,
                        aprovado_em=now,fundamento=fundamento,conteudo_aprovado_sha256=hash_modelo(r)))
            elif acao=='reabrir':
                if not confirmar_evidencias or r.estado!='revogado' or revalidar_ate is not None:
                    raise ErroLeitura('REABERTURA_EXIGE_REVOGADO_E_CONFIRMACAO')
                self._validar_reabertura(s,r,comprovacao_reabertura)
                changes.update(estado='candidato',aprovacao=None)
            else:
                if acao=='revogar' and (not confirmar_evidencias or r.estado in ('revogado','recusado')):
                    raise ErroLeitura('REVOGACAO_EXIGE_CONFIRMACAO_EXPLICITA')
                if acao=='recusar' and r.estado!='candidato':raise ErroLeitura('RECUSA_EXIGE_CANDIDATO')
                changes['estado']='revogado'if acao=='revogar'else'recusado'
            novo=VinculoDocumental.model_validate(r.model_dump()|changes)
            return self._gravar_evento(s,novo,acao,responsavel,sessao_sha256,fundamento)

    def _validar_reabertura(self, snapshot, registro, prova):
        # Só a aplicação produz esta comprovação a partir dos bytes armazenados;
        # o cliente HTTP não pode fornecê-la. Revalidar sob a mesma trava do CAS.
        if not isinstance(prova,VinculoDocumental) or prova.estado!='candidato' or prova.aprovacao:
            raise ErroLeitura('REABERTURA_EXIGE_COMPROVACAO_ORIGINAL')
        historico=[e for e in snapshot.acervo.eventos if e.registro.id==registro.id]
        inicio=max(i for i,e in enumerate(historico)if e.acao=='candidatar')
        if any(e.acao=='revisar'for e in historico[inicio:]) or any(e.papel=='confronto'for e in registro.evidencias):
            raise ErroLeitura('REABERTURA_COM_RESTRICAO_EXIGE_NOVA_COMPROVACAO')
        for campo in ('id','identidade','condominio_destino_id','codigo_destino','nome_financeiro_hmac',
                      'perfil_versao','perfil_sha256','recibos_historicos'):
            if getattr(registro,campo)!=getattr(prova,campo):
                raise ErroLeitura('REABERTURA_CONTEXTO_ATUAL_INCOMPATIVEL')
        if registro.evidencias!=prova.evidencias:
            raise ErroLeitura('REABERTURA_EVIDENCIAS_ORIGINAIS_INCOMPATIVEIS')
        self._conferir_fontes(registro)

    @protegido
    def observar(self, id_, *, motivo, pendencia=None, evidencias=()):
        with self._travar():
            s=self._carregar();r=s.registros.get(id_)
            if not r:return s
            changes={}
            adicionais=tuple(e for e in evidencias if e not in r.evidencias)
            if adicionais:changes['evidencias']=(*r.evidencias,*adicionais)
            if pendencia:
                old=next((p for p in r.pendencias_documentais if p.id==pendencia.id),None)
                if old:
                    ev=tuple(dict.fromkeys((*old.evidencias,*pendencia.evidencias)))
                    if ev==old.evidencias:return s
                    pendencia=old.model_copy(update={'evidencias':ev})
                    changes['pendencias_documentais']=tuple(pendencia if p.id==old.id else p for p in r.pendencias_documentais)
                else:changes['pendencias_documentais']=(*r.pendencias_documentais,pendencia)
            else:
                # Revogação/recusa não apagam restrições descobertas depois dela.
                estado=r.estado if r.estado in ('revogado','recusado') else (
                    'conflitante'if motivo in ('DESTINO_PERSISTENTE_CONFLITANTE','REFERENCIA_ATUAL_CONTRADITORIA_OU_NAO_CONCILIADA')else'pendente')
                if r.estado==estado and r.motivo==motivo and not adicionais:return s
                changes['estado']=estado
            changes.update(versao=r.versao+1,atualizado_em=datetime.now(timezone.utc),motivo=motivo)
            novo=VinculoDocumental.model_validate(r.model_dump()|changes)
            return self._gravar_evento(s,novo,'reter_documento'if pendencia else'revisar',
                'verificacao_automatica_sem_aprovacao','0'*64,motivo)

    @contextmanager
    def conferir_snapshot(self, snapshot):
        # Travar até a geração terminar: aprovação/revogação concorrente exige reprocessar.
        try:
            with self._travar():
                s=self._carregar()
                if s.sha256!=snapshot.sha256:raise ErroLeitura('VINCULOS_ALTERADOS_REPROCESSAR')
                yield
        except (OSError, ValueError, ErroAplicacao):
            raise ErroLeitura('CADASTRO_VINCULOS_INVALIDO_OU_ADULTERADO')from None
        except Timeout:
            raise ErroLeitura('CADASTRO_VINCULOS_OCUPADO')from None
