from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.domain.template import Template
from conversor.export.identifiers import selecionar_perfil
from conversor.readers.passaredo_cadastro import LeitorPassaredoCadastro
from conversor.readers.passaredo_inadimplencia import LeitorPassaredoInadimplencia
from conversor.readers.text_support import ErroLeitura
from conversor.web import ephemeral as ep
from conversor.web.service import analisar, PedidoDiagnostico, reconhecer, ler, PERFIS, PERFIS_SAIDA_PATH
from .fixtures import CPF, OUTRO_CPF, CNPJ, REF, financeiro, cadastro, debito, ficha


def executar(path, raw=None, *, cad=None, modo='A'):
    return analisar(raw if raw is not None else financeiro(),
        PedidoDiagnostico(data_ref=REF, modo=modo, condominio='passaredo'),
        processamento_id='passaredo_sintetico', destino=path, cadastro=cad,
        historico=(), origem='homologacao_sintetica')


def linhas(content):
    book=load_workbook(BytesIO(content)); result=list(book['Dados'].values); book.close(); return result


def saida(path): return linhas((path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes())


def test_layout_nao_prova_condominio_nem_codigo_do_nome_do_arquivo(monkeypatch):
    raw=financeiro()
    with pytest.raises(ErroLeitura, match='PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL'):
        reconhecer(raw)
    perfil,codigo,leitor=reconhecer(raw,perfil_informado='passaredo')
    assert perfil['administradora']=='AUTO GESTÃO' and perfil['dias']==60
    assert codigo=='' and 'codigo_administrativo' not in perfil
    assert perfil['identificacao_diagnostica']=='condominio_informado_pelo_usuario'
    assert leitor=='passaredo_inadimplencia_xlsx_v1'
    monkeypatch.setitem(PERFIS['passaredo']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    with pytest.raises(ErroLeitura, match='PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL'):
        reconhecer(raw)
    assert reconhecer(raw,perfil_informado='passaredo')[0]['identificacao_diagnostica']=='fonte_homologada_por_hash'


def test_selecao_explicita_e_hash_nao_dispensam_validacao_estrutural(monkeypatch):
    raw=financeiro(mutar=lambda w,s:setattr(s.cell(s.max_row-1,1),'value','99 item(ns)'))
    monkeypatch.setitem(PERFIS['passaredo']['fontes_homologacao_sha256'],'inadimplencia',sha256(raw).hexdigest())
    with pytest.raises(ErroLeitura, match='PASSAREDO_FECHAMENTO_AUSENTE_OU_DIVERGENTE'):
        reconhecer(raw,perfil_informado='passaredo')


@pytest.mark.parametrize('dias,elegivel',[(59,False),(60,False),(61,True),(4000,True),(-1,False)])
def test_prazo_estrito_calculado_pelas_datas(tmp_path,dias,elegivel):
    result=executar(tmp_path,financeiro([debito(dias=dias,dias_fonte=999)]))
    assert result['resumo']['dividas_efetivamente_geradas']==int(elegivel)
    assert result['cadastro_passaredo']['dias_informados_divergentes']==1
    assert result['decisoes'][0]['vencimento']==(REF-timedelta(days=dias)).isoformat()


@pytest.mark.parametrize('descricao',[
    'COBRANÇA JUDICIAL FICTÍCIA','ACORDO FICTÍCIO','HONORÁRIOS FICTÍCIOS','CORREÇÃO MONETÁRIA FICTÍCIA'])
def test_encargos_e_rotulos_nao_alteram_original_ou_prazo(tmp_path,descricao):
    raw=financeiro([debito(descricao=descricao,valor='123.45',encargos=('1','2','3','4'))])
    result=executar(tmp_path,raw)
    row=saida(tmp_path)[1]
    assert row[29]==123.45 and row[26]==descricao and row[28].date()==REF-timedelta(days=61)
    assert result['decisoes'][0]['valor']=='123.45' and result['decisoes'][0]['competencia'] is None
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    source=next(r for r in canonical['ressalvas'] if r['codigo']=='PASSAREDO_LANCAMENTO_ORIGINAL')
    fields=json.loads(source['valores_originais'][0])
    assert Decimal(fields['honorarios'])==4 and Decimal(fields['atual'])==Decimal('133.45')
    assert result['fontes'][0]['sha256']==sha256(raw).hexdigest()


def test_30_colunas_codigo_documental_parcelas_e_original(tmp_path):
    raw=financeiro([debito(dias=59,valor='59'),debito(dias=61,valor='61'),
        debito(dias=90,valor='90'),debito(dias=60,valor='60')])
    result=executar(tmp_path,raw)
    rows=saida(tmp_path)
    assert rows[0]==Template(id='t',nome='t',versao='1.1',espaco_final_coluna_27=False).cabecalhos_fisicos
    assert len(rows)==3 and all(len(r)==30 for r in rows)
    assert [r[27] for r in rows[1:]]==[1,2] and [r[29] for r in rows[1:]]==[90,61]
    assert all(r[0]=='AUTO GESTAO' and r[1]=='BL-UNI0007-1030' and r[6]=='BL-UNI0007' for r in rows[1:])
    assert all(r[2] is None for r in rows[1:])  # cadastro opcional, sem inventar CPF
    assert not result['autoriza_cobranca'] and not result['permite_exportacao_operacional']


def test_mesma_unidade_responsaveis_por_lancamento_cadastro_so_com_nome(tmp_path):
    raw=financeiro([debito(nome='Pessoa Fictícia Anterior',dias=90),debito(dias=61)])
    result=executar(tmp_path,raw,cad=cadastro())
    rows=saida(tmp_path)[1:]
    assert rows[0][3]=='Pessoa Fictícia Anterior' and rows[0][2] is None and rows[0][11] is None
    assert rows[1][3]=='Pessoa Fictícia Alfa' and rows[1][2]==CPF and rows[1][11]=='11'
    assert result['resumo']['dividas_efetivamente_geradas']==2
    assert result['cadastro_passaredo']['associacoes_retidas']==1
    review=result['revisao_cadastral_passaredo'][0]
    assert review['responsavel_inadimplencia']=='Pessoa Fictícia Anterior'
    assert review['responsavel_cadastro']=='Pessoa Fictícia Alfa'
    assert review['lancamentos']==1 and 'documento' not in review
    assert any('PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO' in d['alertas_cadastrais'] for d in result['decisoes'])
    original=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    assert any(r['codigo']=='PASSAREDO_CADASTRO_ORIGINAL' for r in original['ressalvas'])


@pytest.mark.parametrize('nome,documento',[( 'Empresa Fictícia Ltda',CNPJ),('Pessoa Fictícia Alfa',CPF)])
def test_documento_so_apos_nome_e_unidade_concordantes(tmp_path,nome,documento):
    executar(tmp_path,financeiro([debito(nome=nome)]),cad=cadastro([ficha(nome=nome,documento=documento)]))
    assert saida(tmp_path)[1][2]==documento


def test_documentos_conflitantes_sao_preservados_sem_atribuicao(tmp_path):
    result=executar(tmp_path,cad=cadastro([ficha(outro_documento=OUTRO_CPF)]))
    assert saida(tmp_path)[1][2] is None and saida(tmp_path)[1][11] is None
    assert result['cadastro_passaredo']['associacoes_retidas']==1
    assert 'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO' in result['decisoes'][0]['alertas_cadastrais']


def test_documento_somente_na_coluna_secundaria_preserva_localizacao(tmp_path):
    raw=cadastro([ficha(documento='',outro_documento=CPF)])
    perfil,codigo,leitor=reconhecer(raw,cadastro=True,perfil_informado='passaredo')
    cad,_=ler(raw,perfil,codigo,leitor,'cadastro')
    assert cad.pessoas[0].evidencias_documentais[0].origem.identificador=='Sheet1_M2'
    executar(tmp_path,cad=raw)
    assert saida(tmp_path)[1][2]==CPF


def test_alias_cpf_continua_suportado_sem_coluna_cpf_cnpj(tmp_path):
    # A coluna CPF secundária, deslocada para L, passa a ser a fonte documental.
    raw=cadastro([ficha(outro_documento=CPF)],mutar=lambda w,s:s.delete_cols(4))
    registros=LeitorPassaredoCadastro().ler(raw)
    assert registros[0].documento.valor==CPF and registros[0].documentos_colunas==('L',)
    executar(tmp_path,cad=raw)
    assert saida(tmp_path)[1][2]==CPF


def test_cadastro_nao_acrescenta_unidade_ou_lancamento(tmp_path):
    result=executar(tmp_path,cad=cadastro([ficha(),ficha(unidade='008',nome='Pessoa Fictícia Beta')]))
    assert result['resumo']['unidades']==1 and result['resumo']['boletos']==1
    assert len(saida(tmp_path))==2


def test_contatos_excedentes_preservados_para_revisao(tmp_path):
    emails='a@example.invalid;b@example.invalid;c@example.invalid;d@example.invalid'
    rows=LeitorPassaredoCadastro().ler(cadastro([ficha(email=emails)]))
    assert len(rows[0].contato.emails)==3 and rows[0].emails_excedentes==('d@example.invalid',)
    result=executar(tmp_path,cad=cadastro([ficha(email=emails)]))
    canonical=json.loads((tmp_path/'canonico.json').read_text(encoding='utf-8'))
    assert any(r['codigo']=='PASSAREDO_CONTATOS_EXCEDENTES_PRESERVADOS' and 'd@example.invalid' in r['valores_originais'][0]
               for r in canonical['ressalvas'])
    assert result['cadastro_passaredo']['associacoes_retidas']==0


@pytest.mark.parametrize('mutar',[
    lambda w,s:s.delete_rows(s.max_row-1,2),
    lambda w,s:setattr(s.cell(s.max_row-1,1),'value','99 item(ns)'),
    lambda w,s:s.append(['CONTEÚDO FICTÍCIO POSTERIOR']),
    lambda w,s:setattr(s['F2'],'value','=1+1'),
    lambda w,s:w.create_sheet('Outra'),
    lambda w,s:setattr(s['D1'],'value','Outra coluna'),
])
def test_estrutura_incompleta_ou_ambigua_nao_e_aceita(mutar):
    with pytest.raises(ErroLeitura):LeitorPassaredoInadimplencia().ler(financeiro(mutar=mutar))


def test_cadastro_duplicado_nao_escolhe_registro_arbitrario():
    with pytest.raises(ErroLeitura,match='PASSAREDO_CADASTRO_UNIDADE_DUPLICADA'):
        LeitorPassaredoCadastro().ler(cadastro([ficha(),ficha(nome='Pessoa Fictícia Outra')]))


@pytest.mark.parametrize('valor',[100.123,'100,123'])
def test_original_nao_e_arredondado_silenciosamente(valor):
    with pytest.raises(ErroLeitura,match='PASSAREDO_ORIGINAL_PRECISAO_INVALIDA'):
        LeitorPassaredoInadimplencia().ler(financeiro(mutar=lambda w,s:setattr(s['F2'],'value',valor)))


def test_campo_dias_decimal_inteiro_nao_e_multiplicado_por_dez():
    raw=financeiro(mutar=lambda w,s:setattr(s['E2'],'value','61.0'))
    assert LeitorPassaredoInadimplencia().ler(raw)[0].dias==61


def test_documento_invalido_continua_em_evidencia_e_nao_vai_para_excel(tmp_path):
    result=executar(tmp_path,cad=cadastro([ficha(documento='11111111111')]))
    assert saida(tmp_path)[1][2] is None
    assert 'PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO' in result['decisoes'][0]['alertas_cadastrais']


def test_modo_b_nao_atribui_cadastro_unico_a_responsaveis_diferentes(tmp_path):
    result=executar(tmp_path,financeiro([debito(nome='Pessoa Fictícia Anterior',dias=59),debito(dias=61)]),modo='B')
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert result['resumo']['cadastros_adicionais']==0
    assert any('PASSAREDO_RESPONSAVEIS_DISTINTOS_LINHA_CADASTRAL_RETIDA' in l['motivos']
        for l in result['previa_template']['linhas'] if l['tipo']=='cadastral')


def test_nome_composto_de_responsaveis_nao_recebe_cpf_individual(tmp_path):
    nome='Pessoa Fictícia Alfa E Pessoa Fictícia Beta'
    result=executar(tmp_path,financeiro([debito(nome=nome)]),cad=cadastro([ficha(nome=nome)]))
    assert saida(tmp_path)[1][2] is None and result['cadastro_passaredo']['associacoes_retidas']==1


def test_unidade_sem_bloco_nao_cria_mapa_para_bloco_informado():
    raw=financeiro();p,c,f=reconhecer(raw,perfil_informado='passaredo');lote,_=ler(raw,p,c,f,'inadimplencia')
    u=lote.unidades[0];assert u.bloco_original=='' and u.unidade_original=='007'
    perfil=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_bytes()),administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
    assert perfil.codificar(u,administradora_id=p['administradora_id'])==('BL-UNI0007-1030','BL-UNI0007')
    with pytest.raises(ErroLeitura,match='TORRE_SEM_MAPEAMENTO_DOCUMENTAL'):
        perfil.codificar(u.model_copy(update={'bloco_original':'A'}),administradora_id=p['administradora_id'])


def test_dois_lancamentos_iguais_preservados_e_determinismo_dos_mesmos_bytes(tmp_path):
    raw=financeiro([debito(),debito()]);cad=cadastro()
    a=executar(tmp_path/'um',raw,cad=cad);b=executar(tmp_path/'dois',raw,cad=cad)
    assert a['resumo']['boletos']==2 and len({d['id'] for d in a['decisoes']})==2
    assert a['decisoes']==b['decisoes']
    assert (tmp_path/'um'/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'dois'/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()
    assert (tmp_path/'um'/'canonico.json').read_bytes()==(tmp_path/'dois'/'canonico.json').read_bytes()


def test_fluxo_efemero_xlsx_cadastro_sessao_download_e_descarte(tmp_path):
    app=ep.criar_app_efemero(acesso='chave-ficticia-passaredo-local',area_temporaria=tmp_path)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert client.post('/api/sessao',json={'chave':'chave-ficticia-passaredo-local'}).status_code==200
        response=client.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A','condominio':'passaredo'},
            files={'inadimplencia':('1028-nao-comprova-identidade.xlsx',financeiro()),'cadastro':('cadastro.xlsx',cadastro([ficha(nome='Pessoa Fictícia Divergente')]))})
        assert response.status_code==200
        result=response.json();id_=result['id'];runtime=app.state.ciclo
        assert result['perfil']=='passaredo' and result['resumo']['boletos']==1
        assert CPF not in response.text and 'example.invalid' not in response.text
        assert result['revisao_cadastral_passaredo'][0]['responsavel_cadastro']=='Pessoa Fictícia Divergente'
        assert not result['permite_exportacao_operacional']
        assert not list(runtime.root.iterdir())
        owner=client.cookies.get('conversor_session');client.cookies.clear()
        assert client.get('/api/conversoes/'+id_+'/excel').status_code==401
        client.post('/api/sessao',json={'chave':'chave-ficticia-passaredo-local'})
        assert client.get('/api/conversoes/'+id_+'/excel').status_code==404
        client.cookies.clear();client.cookies.set('conversor_session',owner)
        assert client.get('/api/conversoes/'+id_+'/operacional.xlsx').status_code==409
        download=client.get('/api/conversoes/'+id_+'/excel')
        assert download.status_code==200 and len(linhas(download.content)[0])==30
        assert client.get('/api/conversoes/'+id_+'/excel').status_code==404
        assert not runtime.results and not list(runtime.root.iterdir())
        root=runtime.root
    assert not root.exists()


def test_api_informa_que_layout_sem_identidade_exige_perfil(tmp_path):
    app=ep.criar_app_efemero(acesso='chave-ficticia-passaredo-local',area_temporaria=tmp_path)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        client.post('/api/sessao',json={'chave':'chave-ficticia-passaredo-local'})
        r=client.post('/api/conversoes',data={'data_ref':str(REF),'modo':'A'},files={'inadimplencia':('1028-passaredo.xlsx',financeiro())})
        assert r.status_code==422 and r.json()['detail']=='PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL'
        assert not list(app.state.ciclo.root.iterdir())
