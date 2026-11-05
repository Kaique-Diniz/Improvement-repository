"""Fluxo efêmero real com PDF/XLSX inteiramente sintéticos, sem dados privados."""
import asyncio
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.domain.template import Template
from conversor.web import ephemeral as ep
from conversor.web.demo import documentos_demo
from tests.bbz.test_edificio_win import financeiro
from tests.bbz.test_abrolhos import financeiro as abrolhos, referencia


KEY='chave-inteiramente-sintetica-local'
DATE={'data_ref':'2026-10-21','modo':'A'}


class Clock:
    def __init__(self): self.now=1000
    def __call__(self): return self.now


@pytest.fixture
def app(tmp_path):
    return ep.criar_app_efemero(acesso=KEY,area_temporaria=tmp_path,relogio=Clock())


@pytest.fixture
def client(app):
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert client.post('/api/sessao',json={'chave':KEY}).status_code==200
        yield client


def post(client, files=None, data=None):
    files=files or {'inadimplencia':documentos_demo()['inadimplencia']}
    return client.post('/api/conversoes', data=data or DATE,
        files={role:(role,content) for role,content in files.items()})


def rows(content):
    book=load_workbook(BytesIO(content),data_only=False)
    result=list(book['Dados'].values);book.close();return result


@pytest.mark.parametrize('mode,lines',[('A',2),('B',3)])
def test_upload_pdf_regras_30_colunas_e_download_unico(client,mode,lines):
    response=post(client,documentos_demo(),DATE|{'modo':mode})
    assert response.status_code==200
    r=response.json(); runtime=client.app.state.ciclo
    assert r['perfil']=='plaza' and r['administradora']=='FL'
    assert r['resumo']['unidades']==2 and r['resumo']['boletos']==3
    assert not r['autoriza_cobranca'] and not r['permite_exportacao_operacional']
    assert list(runtime.root.iterdir())==[]
    assert client.get('/api/conversoes/'+r['id']+'/operacional.xlsx').status_code==409
    download=client.get('/api/conversoes/'+r['id']+'/excel')
    assert download.status_code==200 and download.headers['cache-control']=='no-store'
    output=rows(download.content)
    assert output[0]==Template(id='t',nome='t',versao='1.1',espaco_final_coluna_27=False).cabecalhos_fisicos
    assert len(output)==lines+1 and all(len(row)==30 for row in output)
    assert sorted(row[29] for row in output[1:] if row[29] is not None)==[40,85]
    assert {(row[28].date().isoformat(),row[29]) for row in output[1:] if row[29] is not None}=={('2026-09-19',40),('2026-09-20',85)}
    assert client.get('/api/conversoes/'+r['id']+'/excel').status_code==404
    assert not runtime.results and list(runtime.root.iterdir())==[]


def test_upload_xlsx_bbz_sem_persistencia(client):
    raw=financeiro()
    r=post(client,{'inadimplencia':raw},{'data_ref':'2026-10-26','modo':'A'}).json()
    assert r['perfil']=='edificio_win' and r['administradora']=='BBZ'
    output=rows(client.get('/api/conversoes/'+r['id']+'/excel').content)
    assert len(output)==2 and output[1][-1]==100
    assert output[1][-2].date().isoformat()=='2026-08-26'
    assert not list(client.app.state.ciclo.root.iterdir())


def test_sem_reutilizar_vinculo_documental_de_outra_conversao(client):
    raw=abrolhos(); ref=referencia(raw)
    valid=post(client,{'inadimplencia':raw,'referencia':ref},{'data_ref':'2026-10-26','modo':'A'})
    assert valid.status_code==200 and valid.json()['arquivo_teste_disponivel']
    missing=post(client,{'inadimplencia':raw},{'data_ref':'2026-10-26','modo':'A'})
    assert missing.status_code==200 and not missing.json()['arquivo_teste_disponivel']
    assert missing.json()['resumo']['dividas_efetivamente_geradas']==0
    assert client.get('/api/conversoes/'+missing.json()['id']+'/excel').status_code==409
    assert not client.get('/api/config').json()['vinculos_persistentes']
    assert client.get('/api/vinculos').status_code==404


def test_sessoes_downloads_isolados_e_logout_descarta(client):
    r=post(client).json()
    owner=client.cookies.get('conversor_session')
    client.cookies.clear()
    assert client.get('/api/conversoes/'+r['id']+'/excel').status_code==401
    client.post('/api/sessao',json={'chave':KEY})
    assert client.get('/api/conversoes/'+r['id']+'/excel').status_code==404
    assert client.delete('/api/conversoes/'+r['id']).status_code==404
    client.cookies.set('conversor_session',owner)
    assert client.delete('/api/sessao').status_code==200
    assert not client.app.state.ciclo.results


def test_ttl_independente_de_download_e_descarte_explicito(client):
    r=post(client).json(); runtime=client.app.state.ciclo
    runtime.relogio.now += ep.RETENCAO+1
    runtime.limpar()
    assert not runtime.results
    assert client.get('/api/conversoes/'+r['id']+'/excel').status_code==404
    r=post(client).json()
    assert client.delete('/api/conversoes/'+r['id']).json()=={'descarte_pendente_de_resposta':False}
    assert not runtime.results


@pytest.mark.parametrize('disconnect',[False,True])
def test_resposta_ativa_preserva_bytes_ate_finalizar_ou_falhar(client,disconnect):
    r=post(client).json(); runtime=client.app.state.ciclo; owner=client.cookies.get('conversor_session')
    content=runtime.adquirir_download(r['id'],owner)
    response=ep.DownloadTemporario(runtime,r['id'],content)
    async def send(message):
        if message['type']=='http.response.body':
            assert runtime.apagar(r['id'],owner) is True
            assert r['id'] in runtime.results
            runtime.relogio.now += ep.RETENCAO+1
            runtime.limpar()
            assert r['id'] in runtime.results and runtime.results[r['id']].ativos==1
            assert response.body
            if disconnect: raise OSError('DESCONEXAO_SINTETICA')
    async def receive(): return {'type':'http.request','body':b''}
    async def run():
        await response({'type':'http'},receive,send)
    if disconnect:
        with pytest.raises(OSError): asyncio.run(run())
    else: asyncio.run(run())
    assert not runtime.results and response.body==b''


def test_area_temporaria_removida_no_encerramento(app):
    with TestClient(app,base_url='http://127.0.0.1') as client:
        client.post('/api/sessao',json={'chave':KEY})
        post(client)
        root=app.state.ciclo.root
        assert root.exists() and not list(root.iterdir())
    assert not root.exists() and not app.state.ciclo.results and not app.state.ciclo.sessions


def test_erro_depois_de_gravar_intermediario_remove_tudo(client,monkeypatch,caplog,capsys):
    sentinel='CONTEUDO_DOCUMENTAL_FICTICIO_NAO_LOGAR'
    def fail(*args,destino,**kwargs):
        Path(destino,'canonico.json').write_text(sentinel,encoding='utf-8')
        raise RuntimeError(sentinel)
    monkeypatch.setattr(ep,'analisar',fail)
    r=post(client)
    assert r.status_code==422 and sentinel not in r.text
    assert not list(client.app.state.ciclo.root.iterdir())
    assert sentinel not in caplog.text and sentinel not in capsys.readouterr().out


@pytest.mark.parametrize('raw',[b'outro formato',b'%PDF-1.7 documento quebrado',b'PK\x03\x04lixo'])
def test_invalidos_rejeitados_sem_residuos(client,raw):
    r=post(client,{'inadimplencia':raw})
    assert r.status_code==422 and not list(client.app.state.ciclo.root.iterdir())


def test_xlsx_malicioso_rejeitado_tambem_na_referencia(client):
    demo=documentos_demo(); out=BytesIO()
    with ZipFile(BytesIO(demo['referencia'])) as source, ZipFile(out,'w') as dest:
        for item in source.infolist(): dest.writestr(item,source.read(item.filename))
        dest.writestr('xl/vbaProject.bin',b'CONTEUDO_SINTETICO')
    demo['referencia']=out.getvalue()
    assert post(client,demo).status_code==422
    assert not list(client.app.state.ciclo.root.iterdir())


def test_upload_nao_rola_para_disco_e_fecha_em_erro(client,monkeypatch):
    import starlette.formparsers as parsers
    original=parsers.SpooledTemporaryFile; opened=[]
    def record(*args,**kwargs):
        file=original(*args,**kwargs);opened.append(file);return file
    monkeypatch.setattr(parsers,'SpooledTemporaryFile',record)
    raw=b'%PDF-'+b'x'*(1024*1024+10)
    assert post(client,{'inadimplencia':raw}).status_code==422
    assert opened and all(file.closed and not file._rolled for file in opened)


def test_limite_por_arquivo_antes_de_spill_e_formulario_incompleto(client,monkeypatch):
    import starlette.formparsers as parsers
    opened=[]; original=parsers.SpooledTemporaryFile
    def record(*args,**kwargs):
        file=original(*args,**kwargs);opened.append(file);return file
    monkeypatch.setattr(parsers,'SpooledTemporaryFile',record)
    monkeypatch.setattr(ep,'LIMIT',1024)
    assert post(client,{'inadimplencia':b'%PDF-'+b'x'*2000}).status_code==413
    body=b'--abc\r\nContent-Disposition: form-data; name="inadimplencia"; filename="x"\r\n\r\n%PDF-1.7'
    assert client.post('/api/conversoes',content=body,headers={'content-type':'multipart/form-data; boundary=abc'}).status_code==422
    assert all(f.closed and not f._rolled for f in opened)


def test_host_origin_limites_e_chave_invalidos(client):
    assert client.get('/',headers={'host':'atacante.invalid'}).status_code==400
    assert client.post('/api/sessao',json={'chave':KEY},headers={'origin':'http://atacante.invalid'}).status_code==403
    assert client.post('/api/sessao',json={'chave':'incorreta'}).status_code==401
    assert client.post('/api/conversoes',headers={'content-length':str(ep.MAX_REQUEST+1)}).status_code==413
    assert client.post('/api/conversoes',headers={'content-length':'invalido'}).status_code==400


def test_orcamento_cache_e_duas_conversoes_no_maximo(client):
    runtime=client.app.state.ciclo
    assert runtime.slots.acquire(False) and runtime.slots.acquire(False)
    try: assert post(client).status_code==503
    finally: runtime.slots.release();runtime.slots.release()
    for _ in range(8): assert post(client).status_code==200
    assert post(client).status_code==503
    assert len(runtime.results)==8 and not list(runtime.root.iterdir())


def test_mesmos_bytes_mesmo_excel_diagnostico(client):
    files=documentos_demo()
    one=post(client,files).json(); two=post(client,files).json()
    a=client.get('/api/conversoes/'+one['id']+'/excel').content
    b=client.get('/api/conversoes/'+two['id']+'/excel').content
    assert a==b and rows(a)==rows(b)


def test_falha_de_limpeza_nao_declara_sucesso_e_pode_ser_retentada(client,monkeypatch):
    original=ep.tempfile.TemporaryDirectory
    deny=[True]
    class Temporario(original):
        def __init__(self,*args,**kwargs):
            self.conversion=kwargs.get('prefix')=='conversao-'
            super().__init__(*args,**kwargs)
        def cleanup(self):
            if self.conversion and deny[0]: raise PermissionError('FALHA_SINTETICA')
            return super().cleanup()
    monkeypatch.setattr(ep.tempfile,'TemporaryDirectory',Temporario)
    r=post(client);runtime=client.app.state.ciclo
    assert r.status_code==500 and r.json()['detail']=='LIMPEZA_TEMPORARIA_PENDENTE'
    assert runtime.pendentes and not runtime.results
    deny[0]=False;runtime.limpar()
    assert not runtime.pendentes and not list(runtime.root.iterdir())


def test_inicializador_padrao_e_efemero_e_legado_explicito(monkeypatch):
    from conversor.web import __main__ as launcher
    calls=[]
    monkeypatch.setattr(ep,'main',lambda:calls.append('efemero'))
    monkeypatch.setattr(launcher,'main_legado',lambda args:calls.append(('legado',args)))
    monkeypatch.setattr(launcher.sys,'argv',['conversor-web'])
    launcher.main()
    assert calls==['efemero']
    monkeypatch.setattr(launcher.sys,'argv',['conversor-web','--legado-persistente','--private-dir','sintetico'])
    launcher.main()
    assert calls[1]==('legado',['--private-dir','sintetico'])


def test_nome_de_arquivo_nao_vira_path(client):
    raw=documentos_demo()['inadimplencia']
    r=client.post('/api/conversoes',data=DATE,files={'inadimplencia':('../../nao_gravar.pdf',raw)})
    assert r.status_code==200 and not list(client.app.state.ciclo.root.iterdir())


def test_limite_de_tentativas_de_login(client):
    for _ in range(10):
        assert client.post('/api/sessao',json={'chave':'invalida'}).status_code==401
    assert client.post('/api/sessao',json={'chave':KEY}).status_code==429


def aguardar(condicao, prazo=4):
    import time
    fim=time.monotonic()+prazo
    while time.monotonic()<fim:
        if condicao(): return
        time.sleep(.02)
    assert condicao()


def test_expiracao_sem_requisicoes_e_sem_limpeza_manual(client):
    assert post(client).status_code==200
    runtime=client.app.state.ciclo
    runtime.relogio.now += ep.RETENCAO+1
    # Somente observa: nenhuma requisição ou chamada a limpar dispara o descarte.
    aguardar(lambda:not runtime.results)
    assert not list(runtime.root.iterdir())


def test_downloads_simultaneos_e_cancelamento_liberam_ultima_referencia(client):
    result=post(client).json(); runtime=client.app.state.ciclo
    owner=client.cookies.get('conversor_session')
    responses=[ep.DownloadTemporario(runtime,result['id'],runtime.adquirir_download(result['id'],owner)) for _ in range(2)]
    assert runtime.results[result['id']].ativos==2
    async def run():
        started=asyncio.Event(); release=asyncio.Event()
        async def receive(): return {'type':'http.request','body':b''}
        async def send_first(message): pass
        async def send_second(message):
            if message['type']=='http.response.body':
                started.set()
                await release.wait()
        pending=asyncio.create_task(responses[1]({'type':'http'},receive,send_second))
        await started.wait()
        try:
            await responses[0]({'type':'http'},receive,send_first)
            assert responses[0].body==b'' and responses[1].body
            assert runtime.results[result['id']].ativos==1
            assert runtime.results[result['id']].remover
            pending.cancel()
            with pytest.raises(asyncio.CancelledError): await pending
        finally:
            pending.cancel()
    asyncio.run(run())
    assert not runtime.results and responses[1].body==b''


def test_cancelamento_multipart_fecha_spool_sem_disco(monkeypatch):
    import starlette.formparsers as parsers
    from starlette.datastructures import Headers
    opened=[]; original=parsers.SpooledTemporaryFile
    def record(*args,**kwargs):
        file=original(*args,**kwargs);opened.append(file);return file
    monkeypatch.setattr(parsers,'SpooledTemporaryFile',record)
    async def chunks():
        yield b'--abc\r\nContent-Disposition: form-data; name="inadimplencia"; filename="sintetico.pdf"\r\n\r\n%PDF-1.7'
        raise asyncio.CancelledError()
    parser=ep.FormularioMemoria(Headers({'content-type':'multipart/form-data; boundary=abc'}),chunks())
    with pytest.raises(asyncio.CancelledError): asyncio.run(parser.parse())
    assert opened and all(file.closed and not file._rolled for file in opened)


def test_cancelamento_de_requisicao_aguarda_worker_e_cache_expira(client,monkeypatch):
    import threading
    import httpx
    started=threading.Event(); release=threading.Event(); original=ep.analisar
    runtime=client.app.state.ciclo
    def blocking(*args,destino,**kwargs):
        Path(destino,'intermediario_sintetico.json').write_text('{}',encoding='utf-8')
        started.set()
        assert release.wait(5)
        return original(*args,destino=destino,**kwargs)
    monkeypatch.setattr(ep,'analisar',blocking)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app),base_url='http://127.0.0.1',cookies=dict(client.cookies)) as remote:
            pending=asyncio.create_task(remote.post('/api/conversoes',data=DATE,files={'inadimplencia':('sintetico.pdf',documentos_demo()['inadimplencia'])}))
            try:
                assert await asyncio.to_thread(started.wait,3)
                pending.cancel()
                with pytest.raises(asyncio.CancelledError): await pending
                assert list(runtime.root.iterdir())  # worker ainda utiliza seu temporário
            finally:
                release.set()
                if not pending.done():
                    pending.cancel()
                    with pytest.raises(asyncio.CancelledError): await pending
    asyncio.run(run())
    aguardar(lambda:bool(runtime.results))
    assert not list(runtime.root.iterdir())
    # O worker não é abortado: seu resultado sem resposta permanece até o TTL.
    runtime.relogio.now += ep.RETENCAO+1
    aguardar(lambda:not runtime.results)
    assert runtime.slots.acquire(False) and runtime.slots.acquire(False)
    runtime.slots.release();runtime.slots.release()


def test_reinicio_normal_nao_reutiliza_sessao_resultados_ou_area(tmp_path):
    first=ep.criar_app_efemero(acesso=KEY,area_temporaria=tmp_path)
    with TestClient(first,base_url='http://127.0.0.1') as one:
        one.post('/api/sessao',json={'chave':KEY})
        result=post(one).json(); old_cookie=one.cookies.get('conversor_session')
        old_root=first.state.ciclo.root
    assert not old_root.exists()
    second=ep.criar_app_efemero(acesso=KEY,area_temporaria=tmp_path)
    with TestClient(second,base_url='http://127.0.0.1') as two:
        two.cookies.set('conversor_session',old_cookie)
        assert two.get('/api/config').status_code==401
        two.cookies.clear();two.post('/api/sessao',json={'chave':KEY})
        assert two.get('/api/conversoes/'+result['id']+'/excel').status_code==404
        assert second.state.ciclo.root!=old_root and not second.state.ciclo.results
    assert not second.state.ciclo.root.exists()


def test_inicializacao_nao_identifica_nem_recolhe_residuo_de_outra_execucao(tmp_path):
    orphan=tmp_path/'conversor-efemero-residuo-sintetico'; orphan.mkdir()
    marker=orphan/'sintetico.json';marker.write_text('{}',encoding='utf-8')
    app=ep.criar_app_efemero(acesso=KEY,area_temporaria=tmp_path)
    with TestClient(app,base_url='http://127.0.0.1'):
        assert app.state.ciclo.root!=orphan and marker.read_text(encoding='utf-8')=='{}'
    # Limitação registrada, sem apagar por prefixo diretórios de origem não comprovada.
    assert marker.exists()


def test_limite_global_do_cache_nao_e_limite_de_rss(client,monkeypatch):
    runtime=client.app.state.ciclo
    assert post(client).status_code==200
    total=sum(len(result.excel or b'') for result in runtime.results.values())
    assert total>0
    monkeypatch.setattr(ep,'MAX_CACHE',total)
    assert post(client).status_code==503
    assert len(runtime.results)==1 and not list(runtime.root.iterdir())
