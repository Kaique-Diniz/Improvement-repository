"""MVP local efêmero: fachada do diagnóstico existente, sem cadastro persistente."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hmac
import json
from pathlib import Path
import secrets
import tempfile
import threading
import time
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.datastructures import Headers, UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from conversor.adapters.document_probe import SondadorLocal
from conversor.readers.text_support import ErroLeitura
from .service import LIMIT, PERFIS, PedidoDiagnostico, analisar
from .local_context import ContextosLocais, ConfiguracaoLocal
from conversor.readers.auto_gestao_identity import IdentidadeTabularNaoComprovada
from conversor.readers.vero_identity import IdentidadeVeroNaoComprovada
from conversor.readers.itajuba_identity import IdentidadeItajubaNaoComprovada
from conversor.readers.beach_parque_identity import IdentidadeBeachParqueNaoComprovada
from conversor.readers.oma_identity import IdentidadeOMANaoComprovada, validar_cadastro_protegido


RETENCAO = 15 * 60
MAX_REQUEST = 3 * LIMIT + 1024 * 1024
MAX_EXCEL = 10 * 1024 * 1024
MAX_CACHE = 32 * 1024 * 1024


class UploadExcedido(Exception):
    pass


class FormularioMemoria(MultiPartParser):
    # O limite é aplicado ANTES de escrever o chunk: nunca rolar para disco.
    spool_max_size = LIMIT + 1

    def on_part_begin(self):
        super().on_part_begin()
        self._bytes_part = 0
        self._bytes_header = 0

    def on_header_field(self, data, start, end):
        self._limitar_header(end-start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data, start, end):
        self._limitar_header(end-start)
        super().on_header_value(data, start, end)

    def _limitar_header(self, count):
        self._bytes_header += count
        if self._bytes_header > 8192:
            raise MultiPartException('CABECALHO_MULTIPART_EXCEDIDO')

    def on_end(self):
        self._terminou = True

    def on_part_data(self, data, start, end):
        self._bytes_part += end - start
        if self._current_part.file is not None and self._bytes_part > LIMIT:
            raise UploadExcedido()
        return super().on_part_data(data, start, end)

    async def parse(self):
        try:
            self._terminou = False
            form = await super().parse()
            if not self._terminou:
                raise MultiPartException('FORMULARIO_INCOMPLETO')
            return form
        except BaseException:
            for file in self._files_to_close_on_error:
                file.close()
            raise


@dataclass(repr=False)
class ResultadoTemporario:
    owner: str = field(repr=False)
    resumo: dict = field(repr=False)
    excel: bytes | None = field(repr=False)
    prazo: float
    detalhes: bytes = field(default=b'', repr=False)
    ativos: int = 0
    remover: bool = False


class CicloEfemero:
    def __init__(self, *, pai=None, relogio=time.monotonic):
        self.pai, self.relogio = pai, relogio
        self.lock = threading.RLock()
        self.sessions, self.attempts, self.results = {}, {}, {}
        self.csrf = {}
        self.sem_login = False
        self.administracao = ContextosLocais(self)
        self.slots = threading.BoundedSemaphore(2)
        self.pendentes = []
        self.root = None
        self.pool = None
        self.encerrando = False

    def iniciar(self):
        self.temp = tempfile.TemporaryDirectory(prefix='conversor-efemero-', dir=self.pai)
        self.root = Path(self.temp.name)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='conversor-efemero')

    def limpar(self):
        with self.lock:
            now = self.relogio()
            self.sessions = {s: t for s, t in self.sessions.items() if t > now}
            self.csrf = {s:t for s,t in self.csrf.items() if s in self.sessions}
            self.administracao.limpar(now)
            self.attempts = {ip: [t for t in ts if now-t < 60] for ip, ts in self.attempts.items() if any(now-t < 60 for t in ts)}
            for id_, result in list(self.results.items()):
                if result.prazo <= now or result.owner not in self.sessions:
                    result.remover = True
                if result.remover and not result.ativos:
                    del self.results[id_]
            for directory in self.pendentes[:]:
                try:
                    directory.cleanup()
                except OSError:
                    continue
                self.pendentes.remove(directory)

    def autenticar(self, token):
        self.limpar()
        with self.lock:
            return self.sessions.get(token, 0) > self.relogio()

    def sair(self, token):
        with self.lock:
            self.sessions.pop(token, None)
        self.limpar()

    def processar(self, files, pedido, owner):
        directory = None
        try:
            if self.encerrando:
                raise HTTPException(503, 'ENCERRANDO')
            for role, content in files.items():
                probe = SondadorLocal().sondar(content, arquivo_id=role)
                if (role == 'cadastro' and content.startswith(b'%PDF-') and
                        tuple(probe.bloqueios) == ('DOCUMENTO_PROTEGIDO',)):
                    validar_cadastro_protegido(content, files['inadimplencia'], escolha=pedido.condominio, perfis=PERFIS)
                    continue
                if probe.tipo not in ('pdf_texto', 'xlsx') or probe.bloqueios or not probe.completo:
                    raise HTTPException(422, 'DOCUMENTO_NAO_EXTRAIVEL_COM_SEGURANCA')
            directory = tempfile.TemporaryDirectory(prefix='conversao-', dir=self.root)
            path = Path(directory.name)
            # Só configuração versionada e evidência desta conversão. Não abrir
            # inventários, vínculos, endereços ou fontes de processamentos anteriores.
            result = analisar(files['inadimplencia'], pedido, processamento_id='diagnostico_efemero',
                destino=path, cadastro=files.get('cadastro'), referencia=files.get('referencia'),
                historico=(), estado_historico='nao_disponivel', origem='upload_efemero',
                repositorio_vinculos=None, buscar_endereco=lambda a,c:self.administracao.buscar_endereco(owner,a,c))
            excel = None
            if result['arquivo_teste_disponivel']:
                output = path / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx'
                if output.stat().st_size > MAX_EXCEL:
                    raise HTTPException(413, 'RESULTADO_EXCEDE_LIMITE')
                excel = output.read_bytes()
            summary = {k: result[k] for k in ('condominio', 'perfil', 'administradora', 'resumo', 'data_ref', 'modo',
                'arquivo_teste_disponivel', 'autoriza_cobranca', 'permite_exportacao_operacional')}
            detalhes = b''
            if self.sem_login:
                canonical = json.loads((path/'canonico.json').read_text(encoding='utf-8'))
                payload = {k:result[k] for k in ('decisoes','previa_template','codificacao_template',
                    'endereco_condominio','comparacao','resumo','data_ref','modo','perfil','condominio')}
                payload['boletos'] = {b['id']:b for b in canonical['boletos']}
                if result['perfil']=='terraco_beach_parque' and result['modo']=='B':
                    payload['modo_b_cadastral_beach_parque'] = result['modo_b_cadastral_beach_parque']
                detalhes = json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                if len(detalhes)>MAX_CACHE:
                    raise HTTPException(413,'LIMITE_DA_PREVIA_EXCEDIDO')
            summary['avisos'] = ['DIAGNOSTICO_NAO_IMPORTAR', 'HISTORICO_ANTERIOR_NAO_DISPONIVEL',
                'VINCULOS_PERSISTENTES_INDISPONIVEIS_EVIDENCIA_SOMENTE_DESTA_CONVERSAO']
            for perfil_tabular in ('passaredo', 'forest_hill', 'parque_santa_monica', 'vero_encanto', 'itajuba', 'terraco_beach_parque'):
                chave_cadastro = 'cadastro_' + perfil_tabular
                if chave_cadastro in result:
                    summary[chave_cadastro] = result[chave_cadastro]
                    chave_revisao = 'revisao_cadastral_' + perfil_tabular
                    summary[chave_revisao] = result[chave_revisao]
                    summary['identificacao_condominio'] = result['identificacao_condominio']
        except HTTPException:
            raise
        except ErroLeitura as error:
            if error.codigo in ('PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL','AUTO_GESTAO_LAYOUT_RECONHECIDO_INFORME_PERFIL','OMA_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL','VERO_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL','ITAJUBA_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL','ITAJUBA_CADASTRO_IDENTIDADE_NAO_COMPROVADA','BPQ_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL','IDENTIDADE_DOCUMENTAL_CONFLITANTE'):
                raise HTTPException(422, error.codigo) from None
            raise HTTPException(422, 'DOCUMENTO_NAO_CONVERTIDO_COM_SEGURANCA') from None
        except Exception:
            raise HTTPException(422, 'DOCUMENTO_NAO_CONVERTIDO_COM_SEGURANCA') from None
        finally:
            try:
                if directory is not None:
                    try:
                        directory.cleanup()
                    except OSError:
                        with self.lock:
                            self.pendentes.append(directory)
                        raise HTTPException(500, 'LIMPEZA_TEMPORARIA_PENDENTE') from None
            finally:
                self.slots.release()
        # Não reter nem devolver o resultado se a limpeza dos arquivos falhou.
        with self.lock:
            self.limpar()
            if self.encerrando or not self.autenticar(owner):
                raise HTTPException(401, 'SESSAO_ENCERRADA')
            if len(self.results) >= 8 or sum(len(r.excel or b'')+len(r.detalhes) for r in self.results.values()) + len(excel or b'')+len(detalhes) > MAX_CACHE:
                raise HTTPException(503, 'LIMITE_DE_RESULTADOS_APAGUE_OU_AGUARDE')
            id_ = secrets.token_urlsafe(24)
            self.results[id_] = ResultadoTemporario(owner, summary, excel, self.relogio()+RETENCAO, detalhes=detalhes)
            return {'id': id_, **summary, 'retencao_segundos': RETENCAO}

    def obter(self, id_, owner):
        self.limpar()
        result = self.results.get(id_)
        if result is None or result.owner != owner or result.remover:
            raise HTTPException(404, 'RESULTADO_INDISPONIVEL')
        return result

    def adquirir_download(self, id_, owner):
        with self.lock:
            result = self.obter(id_, owner)
            if result.excel is None:
                raise HTTPException(409, 'SEM_LINHAS_APTAS_PARA_EXCEL_DIAGNOSTICO')
            result.ativos += 1
            return result.excel

    def liberar_download(self, id_):
        with self.lock:
            result = self.results.get(id_)
            if result is not None:
                result.ativos -= 1
                result.remover = True
            self.limpar()

    def liberar_previa(self, id_):
        with self.lock:
            result = self.results.get(id_)
            if result is not None:result.ativos -= 1
            self.limpar()

    def apagar(self, id_, owner):
        with self.lock:
            result = self.obter(id_, owner)
            result.remover = True
            pending = result.ativos > 0
            self.limpar()
            return pending

    def encerrar(self):
        self.encerrando = True
        self.pool.shutdown(wait=True)
        with self.lock:
            self.sessions.clear()
        self.limpar()
        try:
            self.temp.cleanup()
        except OSError:
            raise RuntimeError('LIMPEZA_TEMPORARIA_PENDENTE') from None


class DownloadTemporario(Response):
    def __init__(self, runtime, id_, content):
        self.runtime, self.id_ = runtime, id_
        super().__init__(content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="DIAGNOSTICO_NAO_IMPORTAR.xlsx"'})

    async def __call__(self, scope, receive, send):
        try:
            with anyio.fail_after(60):
                await super().__call__(scope, receive, send)
        finally:
            self.runtime.liberar_download(self.id_)
            self.body = b''


class PreviaTemporaria(Response):
    def __init__(self,runtime,id_,content):
        self.runtime,self.id_=runtime,id_
        super().__init__(content=content,media_type='application/json')

    async def __call__(self,scope,receive,send):
        try:
            with anyio.fail_after(60):await super().__call__(scope,receive,send)
        finally:
            self.runtime.liberar_previa(self.id_)
            self.body=b''


class ProtecaoLocal:
    def __init__(self, app, runtime):
        self.app, self.runtime = app, runtime

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        started = False
        async def seguro(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                message['headers'] = list(message.get('headers', [])) + [
                    (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
            await send(message)
        async def reject(status, code):
            await JSONResponse({'detail': code}, status_code=status)(scope, receive, seguro)
        try:
            if urlsplit('http://'+headers.get('host', '')).hostname not in ('127.0.0.1', 'localhost', '::1'):
                return await reject(400, 'HOST_NAO_PERMITIDO')
            if self.runtime.sem_login:
                origin = headers.get('origin')
                if headers.get('sec-fetch-site') in ('cross-site','same-site') or (origin and origin != f"{scope.get('scheme','http')}://{headers.get('host','')}"):
                    return await reject(403,'ORIGEM_NAO_PERMITIDA')
            if scope['method'] not in ('GET', 'HEAD'):
                origin = headers.get('origin')
                if (origin and (urlsplit(origin).netloc != headers.get('host') or urlsplit(origin).scheme != scope['scheme'])) or headers.get('sec-fetch-site') == 'cross-site':
                    return await reject(403, 'ORIGEM_NAO_PERMITIDA')
            token = Request(scope).cookies.get('conversor_session', '')
            if scope['path'].startswith('/api/') and scope['path'] != '/api/sessao' and not self.runtime.autenticar(token):
                return await reject(401, 'AUTENTICACAO_NECESSARIA')
            if self.runtime.sem_login and (scope['method'] not in ('GET','HEAD') or scope['path'].endswith('/excel')):
                expected = self.runtime.csrf.get(token,'')
                if not expected or not hmac.compare_digest(expected,headers.get('x-csrf-token','')):
                    return await reject(403,'CSRF_INVALIDO')
                if scope['method'] not in ('GET','HEAD') and headers.get('origin') != f"{scope.get('scheme','http')}://{headers.get('host','')}":
                    return await reject(403,'ORIGEM_NAO_PERMITIDA')
            try:
                length = int(headers.get('content-length', '0'))
            except ValueError:
                return await reject(400, 'REQUISICAO_INVALIDA')
            if length < 0:
                return await reject(400, 'REQUISICAO_INVALIDA')
            if length > MAX_REQUEST:
                return await reject(413, 'LIMITE_UPLOAD_EXCEDIDO')
            total = 0
            async def limitado():
                nonlocal total
                message = await receive()
                total += len(message.get('body', b''))
                if total > MAX_REQUEST:
                    raise UploadExcedido()
                return message
            await self.app(scope, limitado, seguro)
        except UploadExcedido:
            if not started: await reject(413, 'LIMITE_UPLOAD_EXCEDIDO')
        except Exception:
            # Nem parsers nem traceback do ASGI podem imprimir conteúdo enviado.
            if not started: await reject(500, 'FALHA_LOCAL_SEGURA')


def criar_app_efemero(*, acesso=None, area_temporaria=None, relogio=time.monotonic):
    if acesso is not None and (not isinstance(acesso, str) or not 12 <= len(acesso) <= 128):
        raise ValueError('CHAVE_LOCAL_INVALIDA')
    runtime = CicloEfemero(pai=area_temporaria, relogio=relogio)
    runtime.sem_login = acesso is None
    @asynccontextmanager
    async def vida(app):
        runtime.iniciar()
        async def janitor():
            while True:
                await asyncio.sleep(1)
                runtime.limpar()
        cleaner = asyncio.create_task(janitor())
        try:
            yield
        finally:
            cleaner.cancel()
            try: await cleaner
            except asyncio.CancelledError: pass
            await asyncio.to_thread(runtime.encerrar)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=vida)
    app.state.ciclo = runtime
    app.add_middleware(ProtecaoLocal, runtime=runtime)

    @app.exception_handler(RequestValidationError)
    async def parametros_invalidos(request, exc):
        return JSONResponse({'detail':'PARAMETROS_INVALIDOS'},status_code=422)

    class Login(BaseModel):
        model_config = ConfigDict(extra='forbid')
        chave: str = Field(strict=True, max_length=128)

    @app.post('/api/sessao')
    async def login(request: Request):
        if runtime.sem_login:raise HTTPException(405,'SESSAO_AUTOMATICA')
        try:
            data = Login.model_validate(await request.json())
        except Exception:
            raise HTTPException(422, 'PARAMETROS_INVALIDOS') from None
        ip = request.client.host if request.client else 'local'
        with runtime.lock:
            runtime.limpar()
            now = runtime.relogio()
            recent = runtime.attempts.get(ip, [])
            if len(recent) >= 10:
                raise HTTPException(429, 'TENTE_NOVAMENTE_EM_UM_MINUTO')
            if not hmac.compare_digest(data.chave.encode(), acesso.encode()):
                runtime.attempts[ip] = recent+[now]
                raise HTTPException(401, 'CHAVE_INVALIDA')
            if len(runtime.sessions) >= 32:
                raise HTTPException(429, 'LIMITE_DE_SESSOES')
            runtime.attempts.pop(ip, None)
            token = secrets.token_urlsafe(32)
            runtime.sessions[token] = now+8*3600
            runtime.csrf[token] = secrets.token_urlsafe(32)
        response = JSONResponse({'ok': True})
        response.set_cookie('conversor_session', token, httponly=True, samesite='strict', max_age=8*3600,
            secure=request.url.scheme == 'https')
        return response

    @app.get('/api/sessao')
    def sessao(request: Request):
        token=request.cookies.get('conversor_session','')
        if not runtime.autenticar(token):raise HTTPException(401,'SESSAO_ENCERRADA')
        return {'csrf':runtime.csrf[token],'sessao_automatica':runtime.sem_login}

    @app.delete('/api/sessao')
    def logout(request: Request):
        runtime.sair(request.cookies.get('conversor_session', ''))
        response = JSONResponse({'ok': True}); response.delete_cookie('conversor_session')
        return response

    @app.get('/api/config')
    def config():
        return {'perfis': [{'id': p['id'], 'nome': p['nome'], 'administradora': p['administradora']} for p in PERFIS.values()],
            'retencao_segundos': RETENCAO, 'exportacao_operacional': False,
            'vinculos_persistentes': False, 'fontes_anteriores': False}

    async def converter(request, demo=False):
        if runtime.encerrando or not runtime.slots.acquire(blocking=False):
            raise HTTPException(503, 'LIMITE_DE_CONVERSOES_SIMULTANEAS')
        scheduled = False
        form = None
        try:
            parser = FormularioMemoria(request.headers, request.stream(), max_files=3, max_fields=4, max_part_size=256)
            form = await parser.parse()
            names = [k for k, _ in form.multi_items()]
            allowed = {'data_ref', 'modo', 'condominio', 'contexto'} | (set() if demo else {'inadimplencia', 'cadastro', 'referencia'})
            if len(names) != len(set(names)) or not set(names) <= allowed:
                raise HTTPException(422, 'CAMPOS_INVALIDOS')
            pedido = PedidoDiagnostico(data_ref=form.get('data_ref'), modo=form.get('modo'),
                condominio='auto' if demo else form.get('condominio', 'auto'))
            if demo:
                from .demo import documentos_demo
                files = documentos_demo()
            else:
                files = {}
                for role in ('inadimplencia', 'cadastro', 'referencia'):
                    upload = form.get(role)
                    if upload is None and role != 'inadimplencia': continue
                    if not isinstance(upload, UploadFile): raise HTTPException(422, 'ARQUIVO_NECESSARIO')
                    content = await upload.read(LIMIT+1)
                    types = (b'PK',) if role == 'referencia' else (b'PK', b'%PDF-')
                    if not content or len(content)>LIMIT: raise HTTPException(413, 'ARQUIVO_VAZIO_OU_LIMITE_EXCEDIDO')
                    if not content.startswith(types): raise HTTPException(422, 'FORMATO_INVALIDO')
                    files[role] = content
            form_contexto = form.get('contexto')
            await form.close(); form = None
            owner = request.cookies.get('conversor_session', '')
            if form_contexto:
                ctx=runtime.administracao.obter(form_contexto,owner)
                from hashlib import sha256
                if sha256(files['inadimplencia']).hexdigest()!=ctx['sha256'] or pedido.condominio not in ('auto',ctx['perfil']):
                    raise HTTPException(409,'DOCUMENTO_ALTERADO_IDENTIFIQUE_NOVAMENTE')
            future = runtime.pool.submit(runtime.processar, files, pedido, owner)
            scheduled = True
            return await asyncio.shield(asyncio.wrap_future(future))
        except UploadExcedido:
            raise HTTPException(413, 'LIMITE_UPLOAD_EXCEDIDO') from None
        except (MultiPartException, ValidationError, ValueError):
            raise HTTPException(422, 'FORMULARIO_INVALIDO') from None
        finally:
            if form is not None: await form.close()
            if not scheduled: runtime.slots.release()

    @app.post('/api/conversoes')
    async def upload(request: Request):
        return await converter(request)

    @app.post('/api/exemplo')
    async def exemplo(request: Request):
        return await converter(request, demo=True)

    @app.get('/api/conversoes/{id_}/excel')
    def download(id_: str, request: Request):
        content = runtime.adquirir_download(id_, request.cookies.get('conversor_session', ''))
        return DownloadTemporario(runtime, id_, content)

    @app.delete('/api/conversoes/{id_}')
    def apagar(id_: str, request: Request):
        pending = runtime.apagar(id_, request.cookies.get('conversor_session', ''))
        return {'descarte_pendente_de_resposta': pending}

    @app.get('/api/conversoes/{id_}/operacional.xlsx')
    def operacional(id_: str, request: Request):
        with runtime.lock:
            runtime.obter(id_, request.cookies.get('conversor_session', ''))
        raise HTTPException(409, 'EXPORTACAO_OPERACIONAL_NAO_HOMOLOGADA')

    @app.post('/api/identificar')
    async def identificar_documento(request: Request):
        form=None
        if runtime.encerrando or not runtime.slots.acquire(blocking=False):
            raise HTTPException(503,'LIMITE_DE_CONVERSOES_SIMULTANEAS')
        try:
            form=await FormularioMemoria(request.headers,request.stream(),max_files=1,max_fields=1,max_part_size=64).parse()
            names=[k for k,_ in form.multi_items()]
            if len(names)!=len(set(names)) or not set(names)<={'inadimplencia','condominio'}:
                raise HTTPException(422,'CAMPOS_INVALIDOS')
            upload=form.get('inadimplencia')
            if not isinstance(upload,UploadFile):raise HTTPException(422,'ARQUIVO_NECESSARIO')
            raw=await upload.read(LIMIT+1)
            if not raw or len(raw)>LIMIT:raise HTTPException(413,'LIMITE_UPLOAD_EXCEDIDO')
            owner=request.cookies.get('conversor_session','')
            escolha=form.get('condominio','auto')
            return await asyncio.to_thread(runtime.administracao.criar,raw,owner,escolha)
        except ErroLeitura as e:
            if isinstance(e,(IdentidadeTabularNaoComprovada,IdentidadeOMANaoComprovada,IdentidadeVeroNaoComprovada,IdentidadeItajubaNaoComprovada,IdentidadeBeachParqueNaoComprovada)):
                return JSONResponse({'detail':e.codigo,'confirmacao_necessaria':True,
                    'mensagem':('Beach Parque compatível; confirme a identidade interna do documento.' if isinstance(e,IdentidadeBeachParqueNaoComprovada) else 'Identidade documental BN Planner compatível; confirme o condomínio deste documento.' if isinstance(e,IdentidadeItajubaNaoComprovada) else 'Identidade documental Lello Vero compatível; confirme o condomínio deste documento.' if isinstance(e,IdentidadeVeroNaoComprovada) else 'Identidade documental OMA compatível; confirme o condomínio deste documento.' if isinstance(e,IdentidadeOMANaoComprovada) else 'Layout AUTO GESTÃO reconhecido; condomínio ainda não comprovado. Confirme somente se corresponder ao documento.'),
                    'candidatos':[{'id':id_,'nome':PERFIS[id_]['nome']} for id_ in e.candidatos]},status_code=409)
            raise HTTPException(422,'IDENTIDADE_CONFLITANTE' if e.codigo=='IDENTIDADE_DOCUMENTAL_CONFLITANTE' else 'DOCUMENTO_NAO_IDENTIFICADO_COM_SEGURANCA') from None
        except (MultiPartException,ValidationError,ValueError):
            raise HTTPException(422,'FORMULARIO_INVALIDO') from None
        finally:
            try:
                if form is not None:await form.close()
            finally:runtime.slots.release()

    @app.get('/api/contextos/{id_}/configuracao')
    def consultar_configuracao(id_:str,request:Request):
        return runtime.administracao.consultar(id_,request.cookies.get('conversor_session',''))

    @app.put('/api/contextos/{id_}/configuracao')
    def salvar_configuracao(id_:str,dados:ConfiguracaoLocal,request:Request):
        return runtime.administracao.salvar(id_,request.cookies.get('conversor_session',''),dados)

    @app.get('/api/conversoes/{id_}/detalhes')
    def detalhes(id_:str,request:Request):
        with runtime.lock:
            r=runtime.obter(id_,request.cookies.get('conversor_session',''))
            r.ativos += 1
            return PreviaTemporaria(runtime,id_,r.detalhes or b'{}')

    static = Path(__file__).with_name('static')
    @app.get('/')
    def index(request: Request):
        response=FileResponse(static/('classico.html' if runtime.sem_login else 'efemero.html'),media_type='text/html')
        if runtime.sem_login:
            token=request.cookies.get('conversor_session','')
            if not runtime.autenticar(token):
                with runtime.lock:
                    if len(runtime.sessions)>=32:raise HTTPException(429,'LIMITE_DE_SESSOES')
                    token=secrets.token_urlsafe(32);runtime.sessions[token]=runtime.relogio()+8*3600
                    runtime.csrf[token]=secrets.token_urlsafe(32)
                response.set_cookie('conversor_session',token,httponly=True,samesite='strict',max_age=8*3600,secure=request.url.scheme=='https')
        return response
    @app.get('/assets/classico.js')
    def classico_js(): return FileResponse(static/'classico.js',media_type='text/javascript')
    @app.get('/assets/classico.css')
    def classico_css(): return FileResponse(static/'classico.css',media_type='text/css')
    @app.get('/assets/style.css')
    def estilo_classico(): return FileResponse(static/'style.css',media_type='text/css')
    @app.get('/assets/efemero.js')
    def javascript(): return FileResponse(static/'efemero.js', media_type='text/javascript')
    @app.get('/assets/efemero.css')
    def css(): return FileResponse(static/'efemero.css', media_type='text/css')
    return app


def main():
    parser = argparse.ArgumentParser(description='Conversão local efêmera — Excel diagnóstico')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    import uvicorn
    app = criar_app_efemero()
    print(f'Abra http://127.0.0.1:{args.port} — sessão automática; somente neste computador.')
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
