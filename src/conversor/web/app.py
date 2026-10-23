"""Servidor local autenticado, arquivos privados e trabalhos isolados por sessão."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from conversor.adapters.private_json import escrever_json
from conversor.domain.audit_identity import ReconciliacaoOcorrencias
from conversor.domain.canonical import Ocorrencia
from conversor.readers.text_support import ErroLeitura
from conversor.validacao_leitores import _area_fora_do_git
from .service import LIMIT, PERFIS, PedidoDiagnostico, analisar

MAX_REQUEST = 3 * LIMIT + 1024 * 1024


class LimitarCorpo:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        if int(headers.get(b'content-length', b'0')) > MAX_REQUEST:
            return await JSONResponse({'detail': 'LIMITE_UPLOAD_EXCEDIDO'}, status_code=413)(scope, receive, send)
        total = 0
        async def limitado():
            nonlocal total
            message = await receive()
            total += len(message.get('body', b''))
            if total > MAX_REQUEST:
                raise HTTPException(413, 'LIMITE_UPLOAD_EXCEDIDO')
            return message
        await self.app(scope, limitado, send)


def gravar_privado(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(content)


class RegistroPrivado:
    def __init__(self, raiz, arquivo=None):
        self.raiz = raiz.resolve()
        self.arquivo = Path(arquivo) if arquivo else raiz / 'fontes_autorizadas.json'

    def listar(self):
        if not self.arquivo.exists():
            return []
        dados = json.loads(self.arquivo.read_text())
        return dados['casos']

    def ler_arquivo(self, spec):
        path = Path(spec['path'])
        if path.is_symlink() or not path.resolve().is_relative_to(self.raiz.parent):
            raise ErroLeitura('FONTE_FORA_DA_AREA_PRIVADA')
        with path.open('rb') as f:
            b = f.read(max(LIMIT, 32 * 1024 * 1024) + 1)
        if len(b) != spec['bytes'] or sha256(b).hexdigest() != spec['sha256']:
            raise ErroLeitura('INTEGRIDADE_DA_FONTE_PRIVADA_DIVERGENTE')
        return b

    def carregar(self, caso):
        arquivos = {role: self.ler_arquivo(spec) for role, spec in caso['arquivos'].items()}
        historico = self.historico(caso)
        return arquivos, historico

    def historico(self, caso):
        # Histórico vazio somente quando explicitamente inventariado como vazio.
        spec = caso['historico']
        if spec.get('vazio_inventariado') is True and spec['registros'] == 0:
            return ()
        content = self.ler_arquivo(spec)
        r = ReconciliacaoOcorrencias.model_validate_json(content)
        perfil = PERFIS[caso['perfil']]
        if r.condominio_id != perfil['condominio_id'] or len(r.registros) != spec['registros']:
            raise ErroLeitura('INVENTARIO_EXTERNO_INCOMPLETO')
        return r.ocorrencias()

    def encontrar_upload(self, content):
        hash_ = sha256(content).hexdigest()
        return next((c for c in self.listar() if c['arquivos']['inadimplencia']['sha256'] == hash_), None)

    def mapeamento(self, caso, arquivos):
        if 'mapeamento_referencia' not in caso or 'referencia' not in arquivos:
            return None
        if sha256(arquivos['referencia']).hexdigest() != caso['arquivos']['referencia']['sha256']:
            return None
        return json.loads(self.ler_arquivo(caso['mapeamento_referencia']))


def criar_app(raiz: Path, *, acesso=None, catalogo=None):
    raiz = Path(raiz)
    raiz.mkdir(mode=0o700, parents=True, exist_ok=True)
    if raiz.is_symlink():
        raise RuntimeError('AREA_PRIVADA_NAO_PODE_SER_LINK')
    _area_fora_do_git(raiz)
    os.chmod(raiz, 0o700)
    (raiz / 'processamentos').mkdir(mode=0o700, exist_ok=True)
    os.chmod(raiz / 'processamentos', 0o700)
    key_file = raiz / 'acesso-local.txt'
    if key_file.is_symlink():
        raise RuntimeError('CHAVE_PRIVADA_NAO_PODE_SER_LINK')
    if acesso is None:
        if not key_file.exists():
            gravar_privado(key_file, secrets.token_urlsafe(32).encode())
        os.chmod(key_file, 0o600)
        acesso = key_file.read_text().strip()
    if not acesso or len(acesso) < 12:
        raise RuntimeError('CHAVE_DE_ACESSO_INSUFICIENTE')
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='conversor-privado')
    @asynccontextmanager
    async def vida(app):
        yield
        pool.shutdown(wait=True)
    app = FastAPI(title='Conversor Inteligente de Inadimplência', docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=vida)
    app.add_middleware(LimitarCorpo)
    jobs, sessions, attempts = {}, {}, {}
    lock = threading.Lock()
    registry = RegistroPrivado(raiz, catalogo)
    app.state.raiz = raiz

    @app.middleware('http')
    async def protecao(request, call_next):
        if request.method not in ('GET', 'HEAD'):
            origin = request.headers.get('origin')
            if origin and urlsplit(origin).netloc != request.headers.get('host'):
                return JSONResponse({'detail': 'ORIGEM_NAO_PERMITIDA'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'ORIGEM_NAO_PERMITIDA'}, status_code=403)
        if request.url.path.startswith('/api/') and request.url.path != '/api/session':
            token = request.cookies.get('conversor_session', '')
            if sessions.get(token, 0) < time.monotonic():
                return JSONResponse({'detail': 'AUTENTICACAO_NECESSARIA'}, status_code=401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.exception_handler(RequestValidationError)
    async def validacao(request, exc):
        return JSONResponse({'detail': 'PARAMETROS_INVALIDOS'}, status_code=422)

    class Acesso(BaseModel):
        model_config = ConfigDict(extra='forbid')
        chave: str

    @app.post('/api/session')
    def login(dados: Acesso, request: Request):
        ip = request.client.host if request.client else 'local'
        now = time.monotonic()
        with lock:
            recent = [t for t in attempts.get(ip, []) if now - t < 60]
            if len(recent) >= 10:
                raise HTTPException(429, 'TENTE_NOVAMENTE_EM_UM_MINUTO')
            if not hmac.compare_digest(dados.chave.encode(), acesso.encode()):
                attempts[ip] = recent + [now]
                raise HTTPException(401, 'CHAVE_INVALIDA')
            attempts.pop(ip, None)
            token = secrets.token_urlsafe(32)
            sessions[token] = now + 8 * 3600
        response = JSONResponse({'ok': True})
        response.set_cookie('conversor_session', token, httponly=True, samesite='strict', max_age=8 * 3600,
                            secure=request.url.scheme == 'https')
        return response

    @app.delete('/api/session')
    def logout(request: Request):
        sessions.pop(request.cookies.get('conversor_session', ''), None)
        response = JSONResponse({'ok': True})
        response.delete_cookie('conversor_session')
        return response

    @app.get('/api/config')
    def config():
        try:
            privados = [{'id': c['id'], 'nome': PERFIS[c['perfil']]['nome']} for c in registry.listar()]
        except Exception:
            privados = []
        return {'condominios': [{'id': p['id'], 'nome': p['nome'], 'administradora': p['administradora']} for p in PERFIS.values()],
                'fontes_privadas': privados, 'exportacao_operacional': False}

    def job_do_usuario(id_, request):
        if not re.fullmatch(r'[0-9a-f]{32}', id_):
            raise HTTPException(404, 'ANALISE_NAO_ENCONTRADA')
        job = jobs.get(id_)
        if not job or job['owner'] != request.cookies.get('conversor_session'):
            raise HTTPException(404, 'ANALISE_NAO_ENCONTRADA')
        return job

    def iniciar(request, pedido, arquivos, *, historico=None, origem='upload', mapeamento=None, contexto=None):
        with lock:
            if sum(j['estado'] == 'processando' for j in jobs.values()) >= 4:
                raise HTTPException(429, 'AGUARDE_OS_PROCESSAMENTOS_EM_CURSO')
            id_ = uuid4().hex
            path = raiz / 'processamentos' / id_
            path.mkdir(mode=0o700, parents=True)
            for role, content in arquivos.items():
                gravar_privado(path / (role + ('.xlsx' if role == 'referencia' else '.pdf')), content)
            escrever_json(path / 'contexto.json', {
                'finalidade': 'diagnostico_local_sem_aprovacao_ou_exportacao_operacional',
                'processamento_id': id_, 'data_ref': pedido.data_ref.isoformat(), 'modo': pedido.modo,
                'sessao_hash': sha256(request.cookies.get('conversor_session', '').encode()).hexdigest(),
                'origem': origem, 'vinculos_fontes_historico_referencia': contexto,
                'registros_historicos_recebidos': len(historico or ())})
            job = {'id': id_, 'owner': request.cookies.get('conversor_session'), 'estado': 'processando', 'path': path}
            jobs[id_] = job
        def work():
            try:
                result = analisar(arquivos['inadimplencia'], pedido, processamento_id=id_, destino=path,
                    cadastro=arquivos.get('cadastro'), referencia=arquivos.get('referencia'),
                    historico=historico, origem=origem,
                    mapeamento_referencia=mapeamento,
                    progresso=lambda etapa: job.update(etapa=etapa))
                with lock:
                    job.update(estado='concluido', resultado=result)
            except (ErroLeitura, ValidationError) as exc:
                code = exc.codigo if isinstance(exc, ErroLeitura) else 'CONTRATO_DO_DOCUMENTO_INVALIDO'
                with lock:
                    job.update(estado='erro', codigo=code)
                escrever_json(path / 'erro.json', {'codigo': code})
            except Exception:
                with lock:
                    job.update(estado='erro', codigo='FALHA_NO_PROCESSAMENTO_PRIVADO')
                escrever_json(path / 'erro.json', {'codigo': 'FALHA_NO_PROCESSAMENTO_PRIVADO'})
        pool.submit(work)
        return JSONResponse({'id': id_, 'estado': 'processando'}, status_code=202)

    def pedido(data_ref, modo, condominio):
        try:
            return PedidoDiagnostico(data_ref=data_ref, modo=modo, condominio=condominio)
        except ValidationError:
            raise HTTPException(422, 'DATA_REFERENCIA_MODO_OU_CONDOMINIO_INVALIDO') from None

    def bloqueio_historico():
        return (Ocorrencia(id='historico_ausente', processamento_id='diagnostico',
            codigo='INVENTARIO_EXTERNO_AUSENTE_OU_DIVERGENTE', gravidade='critico', escopo='processamento'),)

    @app.post('/api/processamentos')
    async def upload(request: Request, data_ref: str = Form(...), modo: str = Form(...),
                     condominio: str = Form('auto'), inadimplencia: UploadFile = File(...),
                     cadastro: UploadFile | None = File(None), referencia: UploadFile | None = File(None)):
        p = pedido(data_ref, modo, condominio)
        files = {}
        for role, f in [('inadimplencia', inadimplencia), ('cadastro', cadastro), ('referencia', referencia)]:
            if f is not None:
                try:
                    content = await f.read(LIMIT + 1)
                finally:
                    await f.close()
                if not content or len(content) > LIMIT:
                    raise HTTPException(413, 'ARQUIVO_VAZIO_OU_LIMITE_EXCEDIDO')
                if not content.startswith(b'PK' if role == 'referencia' else b'%PDF-'):
                    raise HTTPException(422, 'TIPO_DE_ARQUIVO_INVALIDO')
                files[role] = content
        history = bloqueio_historico()
        mapping = None
        case = None
        try:
            case = registry.encontrar_upload(files['inadimplencia'])
            if case:
                # Histórico crítico sempre carregado, mesmo sem Cadastro enviado.
                history = registry.historico(case)
                mapping = registry.mapeamento(case, files)
                for role in ('cadastro',):
                    if role in files and (role not in case['arquivos'] or
                            sha256(files[role]).hexdigest() != case['arquivos'][role]['sha256']):
                        history = bloqueio_historico()
        except Exception:
            history = bloqueio_historico()
        return iniciar(request, p, files, historico=history, mapeamento=mapping, contexto=case)

    @app.post('/api/fontes-privadas/{caso_id}/processar')
    def processar_privado(caso_id: str, request: Request, data_ref: str = Form(...), modo: str = Form(...)):
        p = pedido(data_ref, modo, 'auto')
        try:
            case = next(c for c in registry.listar() if c['id'] == caso_id)
            files, history = registry.carregar(case)
            mapping = registry.mapeamento(case, files)
        except Exception:
            raise HTTPException(409, 'FONTES_OU_HISTORICO_PRIVADOS_INDISPONIVEIS_OU_DIVERGENTES') from None
        return iniciar(request, p, files, historico=history, origem='fonte_privada_autorizada', mapeamento=mapping, contexto=case)

    @app.post('/api/exemplo')
    def exemplo(request: Request, data_ref: str = Form(...), modo: str = Form(...)):
        from .demo import documentos_demo
        p = pedido(data_ref, modo, 'plaza')
        return iniciar(request, p, documentos_demo(), historico=(), origem='exemplo_sintetico')

    @app.get('/api/processamentos/{id_}')
    def status(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        return {k: v for k, v in job.items() if k not in ('owner', 'path')}

    @app.get('/api/processamentos/{id_}/arquivo-teste.xlsx')
    def excel(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        if job['estado'] != 'concluido' or not job['resultado']['arquivo_teste_disponivel']:
            raise HTTPException(409, 'SEM_REGISTROS_APTOS_PARA_ARQUIVO_DE_TESTE')
        return FileResponse(job['path'] / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx',
            filename=f'TESTE_LOCAL_NAO_IMPORTAR_{id_[:8]}.xlsx',
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.get('/api/processamentos/{id_}/inconsistencias.json')
    def inconsistencias(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        if job['estado'] != 'concluido':
            raise HTTPException(409, 'PROCESSAMENTO_NAO_CONCLUIDO')
        r = job['resultado']
        return JSONResponse({'resumo': r['resumo'], 'avisos': r['avisos'], 'comparacao': r['comparacao'],
            'ocorrencias': r['ocorrencias'], 'decisoes': r['decisoes'], 'autoriza_cobranca': False},
            headers={'Content-Disposition': f'attachment; filename="inconsistencias_{id_[:8]}.json"'})

    @app.get('/api/processamentos/{id_}/operacional.xlsx')
    def operacional(id_: str, request: Request):
        job_do_usuario(id_, request)
        raise HTTPException(409, 'EXPORTACAO_OPERACIONAL_NAO_HOMOLOGADA')

    app.mount('/', StaticFiles(directory=Path(__file__).with_name('static'), html=True), name='interface')
    return app
