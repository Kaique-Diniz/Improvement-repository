"""Testes sintéticos da Central de Validação, sem documentos privados."""
from datetime import date, datetime
from decimal import Decimal

from openpyxl import Workbook, load_workbook

from conversor.application.conversion_validation import validar_conversao
from conversor.domain.template import COLUNAS


import json
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import re

import pytest
from fastapi.testclient import TestClient

from conversor.domain.canonical import LoteCanonico
from conversor.web.app import criar_app
from conversor.web.service import analisar, PedidoDiagnostico
from tests.web.test_mvp import KEY, aguardar
from tests.bbz.test_abrolhos import financeiro, referencia, REF


def _cenario(tmp_path, *, retida=False):
    arq = tmp_path / "saida.xlsx"
    valores = (["Credor", "BLE-UNIA00223-788", "", "Titular fictício"] +
               [""] * 20 + ["Contrato", "Produto", "COTA", 1,
                              date(2026, 7, 5), Decimal("897.88")])
    assert len(valores) == 30
    w = Workbook()
    sh = w.active
    sh.title = "Dados"
    sh.append(COLUNAS)
    sh.append(valores)
    sh["AC2"].number_format = "dd/mm/yyyy"
    w.save(arq)
    w.close()
    infos = [{"tipo": "divida", "boleto_id": "b1", "unidade_id": "u1"}]
    decisoes = [{"id": "b1", "situacao": "elegivel"}]
    return arq, [valores], infos, decisoes


def _validar(arq, registros, infos, decisoes, **extra):
    return validar_conversao(arq, registros=registros, linhas_info=infos,
                            decisoes=decisoes, **extra)


def _symlink_ou_skip_1314(link, destino):
    try:
        link.symlink_to(destino)
    except OSError as erro:
        if getattr(erro, 'winerror', None) == 1314:
            pytest.skip('WinError 1314: Windows impediu criar symlink sem privilégio adicional; somente o cenário de link real foi omitido.')
        raise


def test_xlsx_correto_apresenta_indicadores(tmp_path):
    r = _validar(*_cenario(tmp_path))
    assert r["estado"] == "conforme"
    assert r["indicadores"]["linhas_divida"] == 1
    assert r["indicadores"]["valor_financeiro_xlsx"] == "897.88"
    assert r["autoriza_cobranca"] is False


def test_alteracao_de_valor_bloqueia(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["AD2"] = 200
    w.save(arq)
    w.close()
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert {e["codigo"] for e in r["erros"]} >= {"CELULA_DIVERGENTE", "SOMA_FINANCEIRA_DIVERGENTE"}


def test_alteracao_de_cabecalho_bloqueia(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["A1"] = "INDEVIDO"
    w.save(arq)
    w.close()
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "CABECALHO_DIVERGENTE" for x in r["erros"])


def test_boleto_nao_elegivel_nao_pode_ser_exportado(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    decisoes[0]["situacao"] = "revisao"
    decisoes[0]["bloqueios"] = ["DESTINO_NAO_COMPROVADO"]
    r = _validar(arq, registros, infos, decisoes)
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "BOLETOS_DIVERGENTES" for x in r["erros"])


def test_pendencias_documentais_geram_ressalva_sem_expor_dados(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    r = _validar(arq, registros, infos, decisoes, unidades_contato_retido={"u1"})
    assert r["estado"] == "conforme_com_ressalvas"
    assert r["indicadores"]["linhas_divida"] == 1
    assert "Titular fictício" not in str(r)


def test_documento_em_unidade_retida_e_erro_critico(tmp_path):
    arq, registros, infos, decisoes = _cenario(tmp_path)
    w = load_workbook(arq)
    w.active["C2"] = "00000000191"
    w.save(arq)
    w.close()
    registros[0][2] = "00000000191"
    r = _validar(arq, registros, infos, decisoes, unidades_contato_retido={"u1"})
    assert r["estado"] == "erro_critico"
    assert any(x["codigo"] == "CONTATO_RETIDO_EXPOSTO" for x in r["erros"])


def test_sem_linhas_nao_e_sucesso(tmp_path):
    path = tmp_path / "nao-criado.xlsx"
    r = validar_conversao(path, registros=[], linhas_info=[], decisoes=[])
    assert r["estado"] == "sem_arquivo"
    assert r["indicadores"]["linhas_divida"] == 0


# Casos adversos independentes do escritor: as mutações não alteram a fonte.


def _mudar(arq, acao):
    w=load_workbook(arq);acao(w,w['Dados']);w.save(arq);w.close()


@pytest.mark.parametrize('acao,codigo',[
    (lambda w,s:s.delete_cols(30),'QUANTIDADE_COLUNAS_INVALIDA'),
    (lambda w,s:setattr(s['AE1'],'value','EXTRA'),'QUANTIDADE_COLUNAS_INVALIDA'),
    (lambda w,s:w.create_sheet('Extra'),'ABAS_DIVERGENTES'),
    (lambda w,s:s.delete_rows(2),'TOTAL_LINHAS_DIVERGENTE'),
    (lambda w,s:s.append([c.value for c in s[2]]),'LINHA_EXCEDENTE'),
    (lambda w,s:setattr(s['AD2'],'value',Decimal('897.881')),'VALOR_DIVIDA_INVALIDO'),
    (lambda w,s:setattr(s['AD2'],'value',-1),'VALOR_DIVIDA_INVALIDO'),
    (lambda w,s:setattr(s['AD2'],'value',0),'VALOR_DIVIDA_INVALIDO'),
    (lambda w,s:setattr(s['AD2'],'value','=1+1'),'FORMULA_NO_XLSX'),
    (lambda w,s:setattr(s['AC2'],'value',datetime(2026,7,5,12)),'VENCIMENTO_INVALIDO'),
    (lambda w,s:setattr(s['AC2'],'value','05/07/2026'),'VENCIMENTO_INVALIDO'),
    (lambda w,s:setattr(s['AC2'],'value',date(2026,7,6)),'CELULA_DIVERGENTE'),
    (lambda w,s:setattr(s['B2'],'value',123),'IDENTIFICADOR_SEM_TEXTO'),
    (lambda w,s:setattr(s['C2'],'value',191),'DOCUMENTO_SEM_TEXTO'),
    (lambda w,s:setattr(s['AB2'],'value',1.1),'PARCELA_INVALIDA'),
])
def test_adulteracoes_criticas_preservam_arquivo_e_bloqueiam(tmp_path,acao,codigo):
    arq,reg,info,ds=_cenario(tmp_path);_mudar(arq,acao);antes=arq.read_bytes()
    r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and codigo in r['contagem_erros']
    assert arq.read_bytes()==antes


def test_indicadores_observados_nao_repetem_planejamento(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path);_mudar(arq,lambda w,s:s.delete_rows(2))
    r=_validar(arq,reg,info,ds)
    assert r['indicadores']['linhas_divida']==0 and r['indicadores']['linhas_divida_planejadas']==1
    assert r['indicadores']['valor_financeiro_xlsx']=='0.00'
    assert r['indicadores']['valor_financeiro_planejado']=='897.88'


@pytest.mark.parametrize('tipo',['ausente','corrompido','link'])
def test_arquivo_indisponivel_nao_tem_resultado_positivo(tmp_path,tipo):
    arq,reg,info,ds=_cenario(tmp_path)
    if tipo=='ausente':arq.unlink()
    elif tipo=='corrompido':arq.write_bytes(b'ZIP INVALIDO')
    else:
        outro=tmp_path/'fora.xlsx';arq.rename(outro);_symlink_ou_skip_1314(arq,outro)
    r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and not r['arquivo']['conferido_integralmente']


def test_sem_fontes_nao_comprova_extracao_independente(tmp_path):
    r=_validar(*_cenario(tmp_path))
    checks={v['id']:v for v in r['verificacoes']}
    assert checks['fonte_independente']['estado']=='nao_verificavel'
    assert checks['dados_leitor']['estado']=='nao_verificavel'
    assert checks['planejamento']['estado']=='conforme'


def test_cadastro_com_financeiro_e_duplicado_e_modo_A_sao_criticos(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path)
    info[0]['tipo']='cadastral';info[0].pop('boleto_id');ds[0]['situacao']='nao_elegivel'
    r=_validar(arq,reg,info,ds,contexto={'modo':'A'})
    assert {'FINANCEIRO_EM_CADASTRO','CADASTRO_SEM_FUNDAMENTO'} <= r['contagem_erros'].keys()
    _mudar(arq,lambda w,s:s.append([c.value for c in s[2]]))
    r=_validar(arq,reg*2,info*2,ds,contexto={'modo':'B'})
    assert 'CADASTRO_DUPLICADO' in r['contagem_erros']


def test_cadastro_adicional_com_y_ad_vazias_e_sem_divida(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path);reg[0][24:30]=['']*6;info[0]={'tipo':'cadastral','unidade_id':'u1'}
    ds[0].update(unidade_id='u1',situacao='nao_elegivel')
    _mudar(arq,lambda w,s:[setattr(s.cell(2,c),'value',None)for c in range(25,31)])
    r=_validar(arq,reg,info,ds,contexto={'modo':'B'})
    assert r['estado']=='conforme' and r['indicadores']['linhas_cadastrais']==1
    assert r['indicadores']['linhas_divida']==0


@pytest.mark.parametrize('coluna,valor',[(3,'00000000191'),(12,'11'),(13,'999999999'),(22,'ficticio@example.invalid')])
def test_contatos_protegidos_independem_de_plano_e_de_pertencimento(tmp_path,coluna,valor):
    arq,reg,info,ds=_cenario(tmp_path);reg[0][coluna-1]=valor
    _mudar(arq,lambda w,s:setattr(s.cell(2,coluna),'value',valor))
    r=_validar(arq,reg,info,ds,unidades_contato_retido={'u1'})
    assert 'CONTATO_RETIDO_EXPOSTO' in r['contagem_erros']
    if len(valor)>7:assert valor not in json.dumps(r,ensure_ascii=False)


def test_zeros_preservados_documento_textual(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path);reg[0][2]='00000000191'
    def alterar(w,s):s['C2']='00000000191';s['C2'].number_format='@'
    _mudar(arq,alterar)
    assert _validar(arq,reg,info,ds)['estado']=='conforme'


def _canonic_cenario(tmp):
    raw=financeiro();r=analisar(raw,PedidoDiagnostico(data_ref=REF,modo='A'),processamento_id='validacao_sintetica',
        destino=tmp,referencia=referencia(raw))
    arq=tmp/'TESTE_LOCAL_NAO_IMPORTAR.xlsx';w=load_workbook(arq);reg=list(list(v)for v in w['Dados'].values)[1:];w.close()
    for row in reg:row[28]=row[28].date();row[29]=Decimal(str(row[29]))
    lote=LoteCanonico.model_validate_json((tmp/'canonico_extraido.json').read_bytes())
    return arq,reg,r['linhas_teste'],r['decisoes'],lote,r['fontes']


@pytest.mark.parametrize('campo',['valor','vencimento','unidade','decisao','origem','condominio'])
def test_canonico_confere_apesar_de_plano_e_excel_adulterados_juntos(tmp_path,campo):
    arq,reg,info,ds,lote,fontes=_canonic_cenario(tmp_path);extra={}
    if campo=='valor':
        reg[0][29]=Decimal('999.99');_mudar(arq,lambda w,s:setattr(s['AD2'],'value',Decimal('999.99')))
    elif campo=='vencimento':
        reg[0][28]=date(2025,1,1);_mudar(arq,lambda w,s:setattr(s['AC2'],'value',date(2025,1,1)))
    elif campo=='unidade':info[0]['unidade_id']='unidade_inexistente';ds[0]['unidade_id']='unidade_inexistente'
    elif campo=='decisao':ds=[]
    elif campo=='origem':fontes=[{'sha256':'0'*64}]
    else:extra={'contexto':{'condominio_id':'outro_condominio'}}
    r=_validar(arq,reg,info,ds,lote_origem=lote,fontes=fontes,**extra)
    assert r['estado']=='erro_critico'
    if campo!='decisao':assert r['indicadores']['valor_financeiro_canonico']=='100.00'


def test_canonic_conforme_tem_limite_explicito_de_comprovacao(tmp_path):
    arq,reg,info,ds,lote,fontes=_canonic_cenario(tmp_path)
    r=_validar(arq,reg,info,ds,lote_origem=lote,fontes=fontes)
    assert r['estado']=='conforme'
    checks={v['id']:v['estado']for v in r['verificacoes']}
    assert checks['dados_leitor']=='conforme' and checks['fonte_independente']=='nao_verificavel'
    assert r['indicadores']['valor_financeiro_canonico']=='100.00'


def _zip_mudar(arq,transformar):
    raw=BytesIO()
    with ZipFile(arq)as z,ZipFile(raw,'w',ZIP_DEFLATED)as out:
        for name in z.namelist():out.writestr(name,transformar(name,z.read(name)))
    arq.write_bytes(raw.getvalue())


def test_dimensoes_falsas_nao_ocultam_linhas_adicionais(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path)
    _mudar(arq,lambda w,s:s.append([c.value for c in s[2]]))
    _zip_mudar(arq,lambda n,b:re.sub(rb'<dimension ref="[^"]+"',b'<dimension ref="A1:AD1"',b) if n=='xl/worksheets/sheet1.xml'else b)
    r=_validar(arq,reg,info,ds)
    assert 'LINHA_EXCEDENTE'in r['contagem_erros'] and r['indicadores']['linhas_divida']==2


def test_relacionamento_externo_nao_e_conteudo_executavel_permitido(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path)
    _mudar(arq,lambda w,s:setattr(s['A2'],'hyperlink','https://example.invalid'))
    r=_validar(arq,reg,info,ds)
    assert 'VINCULO_EXTERNO'in r['contagem_erros']


def test_texto_literal_parecido_com_formula_nao_e_executado(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path);reg[0][3]='=2+2'
    def mudar(w,s):s['D2']='=2+2';s['D2'].data_type='s'
    _mudar(arq,mudar)
    assert _validar(arq,reg,info,ds)['estado']=='conforme'


def test_erros_limitados_nao_ocultam_contagem_nem_estado_critico(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path)
    _mudar(arq,lambda w,s:[s.append([c.value for c in s[2]])for _ in range(110)])
    r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and r['total_erros']>100 and len(r['erros'])==100 and r['detalhes_limitados']


def _upload_demo(c):
    return aguardar(c,c.post('/api/exemplo',data={'data_ref':'2026-10-23','modo':'B'}))


@pytest.mark.parametrize('tipo',['xlsx_alterado','xlsx_ausente','xlsx_link','laudo_alterado','laudo_ausente'])
def test_download_reconfere_artefatos_e_nao_modifica_originais(tmp_path,tipo):
    root=tmp_path/'mvp'
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});j=_upload_demo(c);path=root/'processamentos'/j['id']
        arq=path/('validacao_conversao.json'if tipo.startswith('laudo')else'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
        if tipo.endswith('ausente'):arq.unlink()
        elif tipo.endswith('link'):
            outro=tmp_path/'copiado.xlsx';arq.rename(outro);_symlink_ou_skip_1314(arq,outro)
        else:arq.write_bytes(b'CONTEUDO ALTERADO SINTETICO')
        endpoint='validacao-conversao.json'if tipo.startswith('laudo')else'arquivo-teste.xlsx'
        resp=c.get('/api/processamentos/'+j['id']+'/'+endpoint)
        assert resp.status_code==409
        if tipo.endswith('alterado'):assert arq.read_bytes()==b'CONTEUDO ALTERADO SINTETICO'


def test_laudo_e_xlsx_com_autenticacao_e_isolamento_de_sessao(tmp_path):
    app=criar_app(tmp_path/'mvp',acesso=KEY)
    with TestClient(app)as c:
        c.post('/api/session',json={'chave':KEY});j=_upload_demo(c);url='/api/processamentos/'+j['id']
        r=c.get(url+'/validacao-conversao.json');assert r.status_code==200
        assert r.json()==j['resultado']['validacao_conversao']
        xlsx=c.get(url+'/arquivo-teste.xlsx');assert xlsx.status_code==200
        assert sha256(xlsx.content).hexdigest()==r.json()['arquivo']['sha256']
        with TestClient(app)as outro:
            assert outro.get(url+'/validacao-conversao.json').status_code==401
            outro.post('/api/session',json={'chave':KEY})
            assert outro.get(url+'/validacao-conversao.json').status_code==404
            assert outro.get(url+'/arquivo-teste.xlsx').status_code==404


def test_erro_critico_da_escrita_bloqueia_download_mas_preserva_laudo(tmp_path,monkeypatch):
    import conversor.web.service as service
    original=service.escrever_xlsx
    def writer(*args,**kwargs):
        ocorrencias=original(*args,**kwargs);_mudar(args[2],lambda w,s:setattr(s['AD2'],'value',999));return ocorrencias
    monkeypatch.setattr(service,'escrever_xlsx',writer)
    with TestClient(criar_app(tmp_path/'mvp',acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});j=_upload_demo(c)
        assert j['estado']=='concluido'and j['resultado']['validacao_conversao']['estado']=='erro_critico'
        assert not j['resultado']['arquivo_teste_disponivel']
        download=c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx')
        assert download.status_code==409 and download.json()['detail']=='VALIDACAO_CRITICA_DOWNLOAD_BLOQUEADO'
        assert c.get('/api/processamentos/'+j['id']+'/validacao-conversao.json').status_code==200


def test_bytes_servidos_nao_sao_reabertos_apos_verificacao(tmp_path,monkeypatch):
    import conversor.web.app as api
    root=tmp_path/'mvp';original=api.ler_protegido
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});j=_upload_demo(c)
        path=root/'processamentos'/j['id']/'TESTE_LOCAL_NAO_IMPORTAR.xlsx';before=path.read_bytes()
        def ler_e_trocar(p):
            raw=original(p)
            if p==path:p.write_bytes(b'ALTERACAO DEPOIS DA LEITURA')
            return raw
        monkeypatch.setattr(api,'ler_protegido',ler_e_trocar)
        response=c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx')
        assert response.status_code==200 and response.content==before
        assert c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').status_code==409


@pytest.mark.parametrize('estado',['aprovado','candidato','revogado','recusado','reaberto'])
def test_central_sem_template_respeita_estado_persistente(tmp_path,estado):
    from tests.bbz.test_persistent_links import repo, iniciar, decidir, executar
    from tests.bbz.test_link_reopening import prova_original
    r=repo(tmp_path);iniciar(tmp_path,r)
    if estado in ('aprovado','revogado','reaberto'):decidir(r)
    if estado in ('revogado','reaberto'):decidir(r,'revogar')
    if estado=='recusado':decidir(r,'recusar')
    if estado=='reaberto':decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
    antes=r.consultar();out=executar(tmp_path/'sem_template',r,modo='B');v=out['validacao_conversao']
    assert v['estado']!='erro_critico'
    assert v['indicadores']['linhas_divida']==(1 if estado=='aprovado'else 0)
    assert v['indicadores']['unidades_vinculo_persistente']==(1 if estado=='aprovado'else 0)
    assert r.consultar()==antes
    assert not out['permite_exportacao_operacional']and not out['autoriza_cobranca']


def test_central_verifica_retencao_cadastral_sem_repositorio_persistente(tmp_path):
    from tests.bbz.test_abrolhos import cadastral
    raw=financeiro();ref=referencia(raw,mutar=lambda w,s:setattr(s['C2'],'value','00000000272'))
    r=analisar(raw,PedidoDiagnostico(data_ref=REF,modo='A'),processamento_id='retencao_sintetica',
        destino=tmp_path,referencia=ref,cadastro=cadastral())
    v=r['validacao_conversao']
    assert v['estado']=='conforme_com_ressalvas'
    assert v['indicadores']['unidades_contato_retido']==v['indicadores']['linhas_com_contato_retido']==1
    assert not v['erros']
    assert all(x not in json.dumps(v,ensure_ascii=False)for x in ['00000000272','00000000191','CONTATO INTEGRALMENTE FICTICIO'])


def test_alteracao_vinculos_apos_geracao_invalida_download_e_preserva_laudo(tmp_path):
    from conversor.adapters.document_links_json import RepositorioVinculosJSON
    from tests.bbz.test_persistent_links import decidir
    from tests.bbz.test_link_reopening import prova_original
    root=tmp_path/'mvp';raw=financeiro()
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        def upload(ref=None):
            files={'inadimplencia':('f.xlsx',raw)}
            if ref:files['referencia']=('r.xlsx',ref)
            return aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},files=files))
        j=upload(referencia(raw));r=RepositorioVinculosJSON(root)
        assert c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').status_code==200
        decidir(r)
        assert c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').status_code==409
        j=upload();assert j['resultado']['validacao_conversao']['indicadores']['unidades_vinculo_persistente']==1
        url='/api/processamentos/'+j['id']
        assert c.get(url+'/arquivo-teste.xlsx').status_code==200
        decidir(r,'revogar');assert c.get(url+'/arquivo-teste.xlsx').status_code==409
        decidir(r,'reabrir',comprovacao_reabertura=prova_original(r))
        assert c.get(url+'/arquivo-teste.xlsx').status_code==409
        laudo=c.get(url+'/validacao-conversao.json');assert laudo.status_code==200
        assert laudo.json()==j['resultado']['validacao_conversao']  # Fotografia histórica, não aprovação atual.
        assert upload()['resultado']['validacao_conversao']['estado']=='sem_arquivo'


def test_download_e_revogacao_concorrentes_usam_snapshot_coerente(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from conversor.adapters.document_links_json import RepositorioVinculosJSON
    from tests.bbz.test_persistent_links import iniciar, decidir
    import conversor.web.app as api
    root=tmp_path/'mvp';root.mkdir(mode=0o700);r=RepositorioVinculosJSON(root);iniciar(tmp_path,r);decidir(r)
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY})
        j=aguardar(c,c.post('/api/processamentos',data={'data_ref':REF.isoformat(),'modo':'A'},files={'inadimplencia':('f.xlsx',financeiro())}))
        path=root/'processamentos'/j['id']/'TESTE_LOCAL_NAO_IMPORTAR.xlsx'
        entrou=Event();liberar=Event();original=api.ler_protegido
        def ler(p):
            raw=original(p)
            if p==path:entrou.set();assert liberar.wait(3)
            return raw
        monkeypatch.setattr(api,'ler_protegido',ler)
        with ThreadPoolExecutor(max_workers=2)as pool:
            download=pool.submit(c.get,'/api/processamentos/'+j['id']+'/arquivo-teste.xlsx')
            assert entrou.wait(3)
            revogar=pool.submit(decidir,r,'revogar');assert not revogar.done()
            liberar.set();assert download.result(timeout=5).status_code==200
            assert next(iter(revogar.result(timeout=5).registros.values())).estado=='revogado'
        assert c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx').status_code==409


@pytest.mark.parametrize('tipo',['divida','cadastral'])
def test_unidade_nao_comprovada_nao_pode_entrar_em_nenhum_tipo_de_linha(tmp_path,tipo):
    from conversor.domain.document_scope import EscopoDestinoDiagnostico
    arq,reg,info,ds,lote,fontes=_canonic_cenario(tmp_path)
    dados=json.loads((tmp_path/'escopo_destino.json').read_bytes());dados.pop('sha256_conteudo')
    escopo=EscopoDestinoDiagnostico.model_validate(dados)
    escopo=escopo.model_copy(update={'unidades':tuple(m.model_copy(update={'estado':'nao_comprovado'})for m in escopo.unidades)})
    if tipo=='cadastral':
        reg[0][24:30]=['']*6;info[0]['tipo']='cadastral';info[0].pop('boleto_id');ds[0]['situacao']='nao_elegivel'
        _mudar(arq,lambda w,s:[setattr(s.cell(2,c),'value',None)for c in range(25,31)])
    r=_validar(arq,reg,info,ds,lote_origem=lote,fontes=fontes,escopo_destino=escopo)
    assert r['estado']=='erro_critico'and 'UNIDADE_FORA_DO_ESCOPO'in r['contagem_erros']


def test_rastreio_sem_unidade_nao_pode_ser_considerado_conforme(tmp_path):
    arq,reg,info,ds=_cenario(tmp_path);info[0].pop('unidade_id')
    r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and 'UNIDADE_DE_RASTREIO_AUSENTE'in r['contagem_erros']


@pytest.mark.parametrize('membro',['xl/vbaProject.bin','xl/macrosheets/sheet1.xml','xl/connections.xml'])
def test_partes_ativas_nao_podem_ser_ocultadas_em_xlsx_com_celulas_corretas(tmp_path,membro):
    arq,reg,info,ds=_cenario(tmp_path)
    with ZipFile(arq,'a',ZIP_DEFLATED)as z:z.writestr(membro,b'<conteudo_sintetico/>'if membro.endswith('.xml')else b'BINARIO SINTETICO')
    r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and 'CONTEUDO_EXECUTAVEL'in r['contagem_erros']


def test_symlink_sem_privilegio_1314_omite_somente_o_cenario(tmp_path,monkeypatch):
    link=tmp_path/'link_sintetico';erro=OSError(13,'Restricao sintetica de criacao de link');erro.winerror=1314
    def impedir(*args,**kwargs):raise erro
    monkeypatch.setattr(type(link),'symlink_to',impedir)
    with pytest.raises(pytest.skip.Exception,match='WinError 1314'):
        _symlink_ou_skip_1314(link,tmp_path/'destino_sintetico')
    assert not link.exists()


@pytest.mark.parametrize('winerror',[None,5,87,1315])
def test_outros_erros_de_symlink_nao_sao_ignorados(tmp_path,monkeypatch,winerror):
    link=tmp_path/'link_sintetico';erro=OSError(13,'Falha sintetica que deve ser propagada')
    if winerror is not None:erro.winerror=winerror
    def impedir(*args,**kwargs):raise erro
    monkeypatch.setattr(type(link),'symlink_to',impedir)
    with pytest.raises(OSError)as captura:
        _symlink_ou_skip_1314(link,tmp_path/'destino_sintetico')
    assert captura.value is erro


def test_rejeita_caminho_simbolico_sem_criar_link_real(tmp_path,monkeypatch):
    arq,reg,info,ds=_cenario(tmp_path);antes=arq.read_bytes()
    classe=type(arq);is_symlink=classe.is_symlink;abrir=classe.open
    def simbolico(p):return p==arq or is_symlink(p)
    def nao_ler_alvo(p,*args,**kwargs):
        if p==arq:pytest.fail('O validador tentou ler um caminho identificado como simbolico.')
        return abrir(p,*args,**kwargs)
    with monkeypatch.context()as m:
        m.setattr(classe,'is_symlink',simbolico);m.setattr(classe,'open',nao_ler_alvo)
        r=_validar(arq,reg,info,ds)
    assert r['estado']=='erro_critico'and not r['arquivo']['conferido_integralmente']
    assert r['arquivo']['sha256']is None and arq.read_bytes()==antes


def test_download_rejeita_caminho_simbolico_sem_criar_link_real(tmp_path,monkeypatch):
    root=tmp_path/'mvp'
    with TestClient(criar_app(root,acesso=KEY))as c:
        c.post('/api/session',json={'chave':KEY});j=_upload_demo(c)
        arq=root/'processamentos'/j['id']/'TESTE_LOCAL_NAO_IMPORTAR.xlsx';antes=arq.read_bytes()
        classe=type(arq);is_symlink=classe.is_symlink;abrir=classe.open
        def simbolico(p):return p==arq or is_symlink(p)
        def nao_ler_alvo(p,*args,**kwargs):
            if p==arq:pytest.fail('O endpoint tentou ler um caminho identificado como simbolico.')
            return abrir(p,*args,**kwargs)
        with monkeypatch.context()as m:
            m.setattr(classe,'is_symlink',simbolico);m.setattr(classe,'open',nao_ler_alvo)
            response=c.get('/api/processamentos/'+j['id']+'/arquivo-teste.xlsx')
        assert response.status_code==409
        assert response.json()['detail']=='ARQUIVO_PRIVADO_INDISPONIVEL_REPROCESSAR'
        assert arq.read_bytes()==antes
