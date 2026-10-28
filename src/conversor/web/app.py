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
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from filelock import Timeout

from conversor.adapters.private_json import escrever_json
from conversor.adapters.condominium_addresses import RepositorioEnderecos
from conversor.adapters.document_links_json import RepositorioVinculosJSON
from conversor.adapters.billing_authority import ler_protegido, sem_links
from conversor.application.ports import ErroAplicacao
from conversor.application.document_links import candidatos_documentais, comprovar_reabertura
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.base import Data, Hash, Texto
from conversor.domain.base import Modelo
from conversor.domain.audit_identity import ReconciliacaoOcorrencias
from conversor.domain.canonical import Endereco, Ocorrencia
from conversor.export.identifiers import OrigemEnderecoUsuario, selecionar_perfil
from conversor.readers.text_support import ErroLeitura
from conversor.validacao_leitores import _area_fora_do_git
from .service import LIMIT, PERFIS, PERFIS_SAIDA_PATH, PedidoDiagnostico, analisar, reconhecer, ler
from typing import Literal

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


def criar_app(raiz: Path, *, acesso=None, catalogo=None, perfis_saida=None):
    raiz = Path(os.path.abspath(raiz))
    try:
        sem_links(raiz)
        if any(p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in (raiz,*raiz.parents)):
            raise ErroAplicacao('CAMINHO_REPARSE')
    except ErroAplicacao:
        raise RuntimeError('AREA_PRIVADA_NAO_PODE_SER_LINK')from None
    raiz.mkdir(mode=0o700, parents=True, exist_ok=True)
    if raiz.is_symlink():
        raise RuntimeError('AREA_PRIVADA_NAO_PODE_SER_LINK')
    _area_fora_do_git(raiz)
    if perfis_saida is None and (raiz / 'perfis_saida.json').exists():
        perfis_saida = raiz / 'perfis_saida.json'
    if perfis_saida is not None:
        perfis_saida = Path(perfis_saida)
        if perfis_saida.is_symlink():
            raise RuntimeError('PERFIL_PRIVADO_NAO_PODE_SER_LINK')
        _area_fora_do_git(perfis_saida.parent)
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
    enderecos = RepositorioEnderecos(raiz)
    vinculos = RepositorioVinculosJSON(raiz)
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
        return {'condominios': [{'id': p['id'], 'nome': p['nome'], 'administradora': p['administradora'],
                                'administradora_id': p['administradora_id'], 'condominio_id': p['condominio_id']} for p in PERFIS.values()],
                'fontes_privadas': privados, 'exportacao_operacional': False}

    class SalvarEndereco(Modelo):
        endereco: Endereco
        versao_esperada: int = Field(strict=True, ge=0)

    def perfil_condominio(administradora_id, condominio_id):
        p = next((p for p in PERFIS.values() if (p['administradora_id'], p['condominio_id']) ==
                  (administradora_id, condominio_id)), None)
        if p is None:
            raise HTTPException(404, 'CONDOMINIO_NAO_RECONHECIDO')
        return p

    def dados_endereco(perfil, padrao, *, privado=False):
        origem = padrao.evidencia if padrao else None
        manual = isinstance(origem, OrigemEnderecoUsuario)
        return {'administradora_id': perfil['administradora_id'], 'condominio_id': perfil['condominio_id'],
            'administradora': perfil['administradora'], 'condominio': perfil['nome'],
            'cadastrado': padrao is not None, 'endereco': padrao.endereco.model_dump(mode='json') if padrao else Endereco().model_dump(),
            'versao': origem.versao if manual and not privado else 0, 'atualizado_em': origem.registrado_em.isoformat() if manual else None,
            'origem': 'perfil_privado_existente' if privado and padrao else 'configuracao_fornecida_pelo_usuario' if manual else 'nao_cadastrado'}

    @app.get('/api/condominios/{administradora_id}/{condominio_id}/endereco')
    def consultar_endereco(administradora_id: str, condominio_id: str):
        p = perfil_condominio(administradora_id, condominio_id)
        try:
            padrao = enderecos.obter(administradora_id, condominio_id)
            privado = padrao is None
            if privado:
                dados = json.loads(Path(perfis_saida or PERFIS_SAIDA_PATH).read_bytes())
                saida = selecionar_perfil(dados, administradora_id=administradora_id, condominio_id=condominio_id)
                padrao = saida.endereco_padrao if saida else None
            return dados_endereco(p, padrao, privado=privado)
        except (ErroLeitura, ValidationError, OSError, ValueError, Timeout):
            raise HTTPException(409, 'CADASTRO_ENDERECOS_INDISPONIVEL') from None

    @app.put('/api/condominios/{administradora_id}/{condominio_id}/endereco')
    def salvar_endereco(administradora_id: str, condominio_id: str, dados: SalvarEndereco, request: Request):
        p = perfil_condominio(administradora_id, condominio_id)
        try:
            padrao = enderecos.salvar(administradora_id, condominio_id, dados.endereco,
                versao_esperada=dados.versao_esperada,
                sessao_sha256=sha256(request.cookies['conversor_session'].encode()).hexdigest())
            return dados_endereco(p, padrao)
        except ErroLeitura as exc:
            raise HTTPException(409, exc.codigo) from None
        except ValidationError:
            raise HTTPException(422, 'ENDERECO_DO_CONDOMINIO_INVALIDO') from None
        except (OSError, Timeout):
            raise HTTPException(409, 'CADASTRO_ENDERECOS_INDISPONIVEL') from None

    def job_do_usuario(id_, request):
        if not re.fullmatch(r'[0-9a-f]{32}', id_):
            raise HTTPException(404, 'ANALISE_NAO_ENCONTRADA')
        job = jobs.get(id_)
        if not job or job['owner'] != request.cookies.get('conversor_session'):
            raise HTTPException(404, 'ANALISE_NAO_ENCONTRADA')
        return job

    class PrepararVinculos(Modelo):
        revisao_esperada: int = Field(strict=True, ge=0)
        responsavel: Texto

    class DecidirVinculo(PrepararVinculos):
        acao: Literal['aprovar','recusar','revogar','reabrir']
        conteudo_sha256: Hash
        fundamento: Texto
        confirmar_evidencias: bool = Field(default=False, strict=True)
        revalidar_ate: Data | None = None

    def resposta_vinculos(snapshot, administradora_id=None, condominio_id=None):
        registros=[r for r in snapshot.registros.values() if
            (not administradora_id or r.identidade.administradora_id==administradora_id)and
            (not condominio_id or r.condominio_destino_id==condominio_id)]
        ids={r.id for r in registros}
        return {'versao_contrato':'1.0','revisao':snapshot.revisao,'sha256':snapshot.sha256,
            'registros':[r.model_dump(mode='json')|{'conteudo_sha256':hash_modelo(r)}for r in registros],
            'historico':[e.model_dump(mode='json',exclude={'assinatura'})for e in snapshot.acervo.eventos if e.registro.id in ids],
            'limite':'Aprovar pertencimento não aprova CPF, contatos, regras financeiras ou exportação operacional.'}

    @app.get('/api/vinculos')
    def consultar_vinculos(administradora_id: str | None=None, condominio_id: str | None=None):
        if bool(administradora_id)!=bool(condominio_id):raise HTTPException(422,'INFORME_ADMINISTRADORA_E_CONDOMINIO')
        if administradora_id:perfil_condominio(administradora_id,condominio_id)
        try:return resposta_vinculos(vinculos.consultar(),administradora_id,condominio_id)
        except ErroLeitura as e:raise HTTPException(409,e.codigo)from None

    @app.post('/api/vinculos/candidatos/{id_}')
    def preparar_vinculos(id_: str, dados: PrepararVinculos, request: Request):
        job=job_do_usuario(id_,request)
        if job['estado']!='concluido':raise HTTPException(409,'ANALISE_AINDA_NAO_CONCLUIDA')
        try:
            raw=ler_protegido(job['path']/'inadimplencia.xlsx');ref=ler_protegido(job['path']/'referencia.xlsx')
            fontes={f['papel']:f for f in job['resultado']['fontes']}
            if sha256(raw).hexdigest()!=fontes['inadimplencia']['sha256'] or sha256(ref).hexdigest()!=fontes['referencia']['sha256']:
                raise ErroLeitura('FONTES_DA_ANALISE_ALTERADAS')
            p,code,reader=reconhecer(raw)
            if not p.get('exigir_escopo_documental_destino'):raise ErroLeitura('PERFIL_NAO_EXIGE_VINCULO_DE_DESTINO')
            lote,_=ler(raw,p,code,reader,'inadimplencia')
            saida=selecionar_perfil(json.loads(Path(perfis_saida or PERFIS_SAIDA_PATH).read_bytes()),
                administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
            if saida is None:saida=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_bytes()),
                administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
            s=candidatos_documentais(vinculos,lote,referencia=ref,financeiro=raw,perfil=p,perfil_saida=saida,codigo=code,
                revisao_esperada=dados.revisao_esperada,responsavel=dados.responsavel,
                sessao_sha256=sha256(request.cookies['conversor_session'].encode()).hexdigest())
            return resposta_vinculos(s,p['administradora_id'],p['condominio_id'])
        except ErroLeitura as e:raise HTTPException(409,e.codigo)from None
        except (OSError,KeyError,ValueError,ErroAplicacao):raise HTTPException(409,'REFERENCIA_ORIGINAL_VERIFICAVEL_NECESSARIA')from None

    @app.post('/api/vinculos/{vinculo_id}/decisao')
    def decidir_vinculo(vinculo_id: str, dados: DecidirVinculo, request: Request):
        if not re.fullmatch('[a-f0-9]{64}',vinculo_id):raise HTTPException(404,'VINCULO_NAO_ENCONTRADO')
        try:
            prova=None
            if dados.acao=='reabrir':
                snapshot=vinculos.consultar();registro=snapshot.registros.get(vinculo_id)
                if (not registro or snapshot.revisao!=dados.revisao_esperada or
                        hash_modelo(registro)!=dados.conteudo_sha256):
                    raise ErroLeitura('VINCULOS_ALTERADOS_RECARREGUE')
                if registro.estado!='revogado' or not dados.confirmar_evidencias or not dados.fundamento.strip():
                    raise ErroLeitura('REABERTURA_EXIGE_REVOGADO_E_CONFIRMACAO')
                original={papel:next(e.origem.sha256 for e in registro.evidencias if e.papel==papel)
                    for papel in ('financeiro','referencia')}
                raw=vinculos.ler_fonte(original['financeiro']);ref=vinculos.ler_fonte(original['referencia'])
                p,code,reader=reconhecer(raw)
                lote,_=ler(raw,p,code,reader,'inadimplencia')
                saida=selecionar_perfil(json.loads(Path(perfis_saida or PERFIS_SAIDA_PATH).read_bytes()),
                    administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
                if saida is None:saida=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_bytes()),
                    administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
                prova=comprovar_reabertura(vinculos,registro,lote,financeiro=raw,referencia=ref,
                    perfil=p,perfil_saida=saida,codigo=code)
            s=vinculos.decidir(vinculo_id,**dados.model_dump(exclude={'responsavel'}),responsavel=dados.responsavel,
                sessao_sha256=sha256(request.cookies['conversor_session'].encode()).hexdigest(),
                comprovacao_reabertura=prova)
            r=s.registros[vinculo_id]
            return resposta_vinculos(s,r.identidade.administradora_id,r.condominio_destino_id)
        except ErroLeitura as e:raise HTTPException(409,e.codigo)from None
        except (OSError,KeyError,ValueError,StopIteration,ErroAplicacao):
            raise HTTPException(409,'REABERTURA_COMPROVACAO_ORIGINAL_INDISPONIVEL')from None

    def iniciar(request, pedido, arquivos, *, historico=None, origem='upload', mapeamento=None, contexto=None,
                estado_historico='nao_disponivel'):
        with lock:
            if sum(j['estado'] == 'processando' for j in jobs.values()) >= 4:
                raise HTTPException(429, 'AGUARDE_OS_PROCESSAMENTOS_EM_CURSO')
            id_ = uuid4().hex
            path = raiz / 'processamentos' / id_
            path.mkdir(mode=0o700, parents=True)
            for role, content in arquivos.items():
                gravar_privado(path / (role + ('.xlsx' if content.startswith(b'PK') else '.pdf')), content)
            escrever_json(path / 'contexto.json', {
                'finalidade': 'diagnostico_local_sem_aprovacao_ou_exportacao_operacional',
                'processamento_id': id_, 'data_ref': pedido.data_ref.isoformat(), 'modo': pedido.modo,
                'sessao_hash': sha256(request.cookies.get('conversor_session', '').encode()).hexdigest(),
                'origem': origem, 'vinculos_fontes_historico_referencia': contexto,
                'estado_historico': estado_historico,
                'registros_historicos_recebidos': len(historico or ())})
            job = {'id': id_, 'owner': request.cookies.get('conversor_session'), 'estado': 'processando', 'path': path}
            jobs[id_] = job
        def work():
            try:
                result = analisar(arquivos['inadimplencia'], pedido, processamento_id=id_, destino=path,
                    cadastro=arquivos.get('cadastro'), referencia=arquivos.get('referencia'),
                    historico=historico, origem=origem,
                    estado_historico=estado_historico,
                    mapeamento_referencia=mapeamento,
                    perfis_saida=perfis_saida,
                    buscar_endereco=enderecos.obter,
                    repositorio_vinculos=vinculos,
                    progresso=lambda etapa: job.update(etapa=etapa))
                with lock:
                    job.update(estado='concluido', resultado=result)
            except (ErroLeitura, ValidationError) as exc:
                code = exc.codigo if isinstance(exc, ErroLeitura) else 'CONTRATO_DO_DOCUMENTO_INVALIDO'
                local = {k:getattr(exc,k) for k in ('pagina','linha') if getattr(exc,k,None) is not None}
                with lock:
                    job.update(estado='erro', codigo=code, **local)
                escrever_json(path / 'erro.json', {'codigo': code, **local})
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
                tipos = (b'PK',) if role=='referencia' else (b'%PDF-',) if role=='cadastro' else (b'%PDF-',b'PK')
                if not content.startswith(tipos):
                    raise HTTPException(422, 'TIPO_DE_ARQUIVO_INVALIDO')
                files[role] = content
        history = ()
        estado_historico = 'nao_disponivel'
        mapping = None
        case = None
        try:
            case = registry.encontrar_upload(files['inadimplencia'])
            if case:
                # Histórico crítico sempre carregado, mesmo sem Cadastro enviado.
                history = registry.historico(case)
                estado_historico = 'carregado' if history else 'vazio_inventariado'
                mapping = registry.mapeamento(case, files)
                for role in ('cadastro',):
                    if role in files and (role not in case['arquivos'] or
                            sha256(files[role]).hexdigest() != case['arquivos'][role]['sha256']):
                        history = tuple(history) + bloqueio_historico()
                        estado_historico = 'divergente'
        except Exception:
            history = tuple(history) + bloqueio_historico()
            estado_historico = 'divergente'
        return iniciar(request, p, files, historico=history, mapeamento=mapping, contexto=case,
                       estado_historico=estado_historico)

    @app.post('/api/fontes-privadas/{caso_id}/processar')
    def processar_privado(caso_id: str, request: Request, data_ref: str = Form(...), modo: str = Form(...)):
        p = pedido(data_ref, modo, 'auto')
        try:
            case = next(c for c in registry.listar() if c['id'] == caso_id)
            files, history = registry.carregar(case)
            mapping = registry.mapeamento(case, files)
        except Exception:
            raise HTTPException(409, 'FONTES_OU_HISTORICO_PRIVADOS_INDISPONIVEIS_OU_DIVERGENTES') from None
        return iniciar(request, p, files, historico=history, origem='fonte_privada_autorizada', mapeamento=mapping, contexto=case,
                       estado_historico='carregado' if history else 'vazio_inventariado')

    @app.post('/api/exemplo')
    def exemplo(request: Request, data_ref: str = Form(...), modo: str = Form(...)):
        from .demo import documentos_demo
        p = pedido(data_ref, modo, 'plaza')
        return iniciar(request, p, documentos_demo(), historico=(), origem='exemplo_sintetico', estado_historico='exemplo_sintetico')

    @app.get('/api/processamentos/{id_}')
    def status(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        return {k: v for k, v in job.items() if k not in ('owner', 'path')}

    @app.get('/api/processamentos/{id_}/arquivo-teste.xlsx')
    def excel(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        if job['estado'] != 'concluido' or not job['resultado']['arquivo_teste_disponivel']:
            raise HTTPException(409, 'SEM_REGISTROS_APTOS_PARA_ARQUIVO_DE_TESTE')
        digest=job['resultado'].get('escopo_destino',{}).get('cadastro_sha256')
        if digest:
            try:
                if vinculos.consultar().sha256!=digest:raise ErroLeitura('VINCULOS_ALTERADOS_REPROCESSAR')
            except ErroLeitura as e:raise HTTPException(409,e.codigo)from None
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
            'ocorrencias': r['ocorrencias'], 'decisoes': r['decisoes'], 'cotas': r['cotas'], 'hierarquia': r['hierarquia'],
            'politica_cadastral': r['politica_cadastral'], 'reavaliacoes_historicas': r['reavaliacoes_historicas'],
            'historico_tecnico': r['historico_tecnico'], 'previa_template': r['previa_template'],
            'codificacao_template': r['codificacao_template'],
            'fechamento_habita': r['fechamento_habita'], 'manifesto_diagnostico': r['manifesto_diagnostico'],
            'rotulos_template': r['rotulos_template'], 'enderecos_template': r['enderecos_template'],
            'endereco_condominio': r['endereco_condominio'],
            'autoriza_cobranca': False, 'permite_exportacao_operacional': False},
            headers={'Content-Disposition': f'attachment; filename="inconsistencias_{id_[:8]}.json"'})

    @app.get('/api/processamentos/{id_}/manifesto-diagnostico.json')
    def manifesto(id_: str, request: Request):
        job = job_do_usuario(id_, request)
        if job['estado'] != 'concluido':
            raise HTTPException(409, 'PROCESSAMENTO_NAO_CONCLUIDO')
        return FileResponse(job['path'] / 'manifesto_diagnostico.json',
            filename=f'MANIFESTO_DIAGNOSTICO_NAO_IMPORTAR_{id_[:8]}.json', media_type='application/json')

    @app.get('/api/processamentos/{id_}/operacional.xlsx')
    def operacional(id_: str, request: Request):
        job_do_usuario(id_, request)
        raise HTTPException(409, 'EXPORTACAO_OPERACIONAL_NAO_HOMOLOGADA')

    app.mount('/', StaticFiles(directory=Path(__file__).with_name('static'), html=True), name='interface')
    return app
