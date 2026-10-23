"""Fontes construídas do zero; dispensa diagnóstica não altera críticas históricas."""
from hashlib import sha256
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from conversor.application.reading import resultado_leitura
from conversor.domain.canonical import Documento, EvidenciaDocumento, Ocorrencia
from conversor.readers.habita_closing import conferir_fechamento_habita
from conversor.web.app import criar_app
from conversor.web.service import analisar, ler, reconhecer, PedidoDiagnostico
from tests.web.test_mvp import KEY, aguardar
from tests.web.test_tree_group_veto import boleto, pdf_unidades


def fonte(*, fechamento=True, continuidade=False):
    return pdf_unidades([
        ('S1','000001',[boleto('99000001',componentes=[('0.01','0.00','0.00','0.00'),('9.99','1.00','2.00','3.00')]),boleto('99000002',valor='15.00')]),
        ('VG','000001',[boleto('99000003',valor='20.00'),boleto('99000004',vencimento='22/10/26')]),
        ('VG','000002',[boleto('99000005',valor='0.01')])],fechamento_vg=fechamento,continuidade=continuidade)


def ler_fonte(blob):
    p,c,l=reconhecer(blob)
    return ler(blob,p,c,l,'inadimplencia')


def executar(tmp_path, *, blob=None, modo='A', historico=None):
    return analisar(blob or fonte(),PedidoDiagnostico(data_ref='2026-10-23',modo=modo),
        processamento_id='fechamento_sintetico',destino=tmp_path,historico=historico)


@pytest.mark.parametrize('modo,dividas,cadastros',[('A',3,0),('B',3,2)])
def test_fechamento_reconciliado_disponibiliza_so_diagnostico_preservando_evidencia(tmp_path,modo,dividas,cadastros):
    blob=fonte(continuidade=True)
    original,ctx=ler_fonte(blob)
    r=executar(tmp_path,blob=blob,modo=modo)
    assert r['resumo']['cotas']==3 and r['resumo']['boletos']==5
    assert r['resumo']['dividas_efetivamente_geradas']==dividas
    assert r['resumo']['cadastros_adicionais']==cadastros and not r['resumo'].get('revisao',0)
    assert not r['permite_exportacao_operacional']and not r['autoriza_cobranca']
    assert r['fechamento_habita']['estado']=='reconciliado_somente_diagnostico'
    assert all(r['fechamento_habita']['verificacoes'].values())
    assert r['fechamento_habita']['quantidades']['boletos']==5
    assert resultado_leitura(original,processamento_id='sintetico').bloqueante
    assert json.loads((tmp_path/'canonico.json').read_text())==original.model_dump(mode='json')
    crit=[o for o in r['ocorrencias']if o['codigo']=='SUBTOTAL_BLOCO_DIVERGENTE']
    assert len(crit)==1 and crit[0]['gravidade']=='critico'and crit[0]['escopo']=='arquivo'
    assert all('SUBTOTAL_BLOCO_DIVERGENTE'in d['impedimentos_exportacao_operacional']for d in r['decisoes'])
    assert all(not d['bloqueios']and d['anomalia_global_reconciliada']for d in r['decisoes'])
    manifesto=json.loads((tmp_path/'manifesto_diagnostico.json').read_text())
    assert manifesto==r['manifesto_diagnostico']
    assert manifesto['arquivo']['sha256']==sha256((tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()).hexdigest()
    assert manifesto['ocorrencias_criticas_preservadas']==crit
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    assert wb.sheetnames==['Dados']and wb['Dados'].max_column==30
    rows=list(wb['Dados'].values)[1:]
    assert len(rows)==dividas+cadastros
    assert sum(all(v is None for v in row[24:30])for row in rows)==cadastros
    assert [row[27]for row in rows if row[24]is not None]==[1,2,1]
    assert {row[26]for row in rows if row[24]is not None}=={'99000001','99000002','99000003'}
    wb.close()


def test_mesmo_xlsx_com_e_sem_anomalia_quando_financas_sao_iguais(tmp_path):
    executar(tmp_path/'com',modo='B')
    executar(tmp_path/'sem',blob=fonte(fechamento=False),modo='B')
    assert (tmp_path/'com/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()==(tmp_path/'sem/TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()


@pytest.mark.parametrize('escopo',['arquivo','processamento','registro'])
def test_outra_critica_nao_e_dispensada(tmp_path,escopo):
    blob=fonte();lote,ctx=ler_fonte(blob)
    crit=Ocorrencia(id='critica_legada',processamento_id='historico',codigo='DOCUMENTOS_CONFLITANTES',
        gravidade='critico',escopo=escopo,registro_id=lote.unidades[0].id if escopo=='registro'else None,
        origem=lote.unidades[0].origem)
    r=executar(tmp_path,blob=blob,modo='B',historico=(crit,))
    assert crit.model_dump(mode='json')in r['ocorrencias']
    if escopo=='registro':
        assert r['resumo']['dividas_efetivamente_geradas']==1
        assert all(not l['unidade_id']==lote.unidades[0].id for l in r['linhas_teste'])
    else:
        assert not r['arquivo_teste_disponivel']
        assert all('DOCUMENTOS_CONFLITANTES'in d['bloqueios']for d in r['decisoes'])


def test_documentos_validos_conflitantes_nao_entram_no_xlsx_diagnostico(tmp_path,monkeypatch):
    import conversor.web.service as service
    leitor=service.ler
    def com_conflito(*args,**kwargs):
        lote,ctx=leitor(*args,**kwargs)
        p=lote.pessoas[0]
        evidencias=tuple(EvidenciaDocumento(documento=d,origem=p.origem)for d in (
            Documento(tipo='cpf',valor='00000000191'),Documento(tipo='cnpj',valor='00000000000191')))
        p=p.model_copy(update={'evidencias_documentais':evidencias})
        return lote.model_copy(update={'pessoas':(p,)+lote.pessoas[1:]}),ctx
    monkeypatch.setattr(service,'ler',com_conflito)
    r=executar(tmp_path,modo='B')
    assert r['fechamento_habita']['estado']=='reconciliado_somente_diagnostico'
    assert r['resumo']['dividas_efetivamente_geradas']==1
    afetados=[d for d in r['decisoes']if d['bloco']=='S1']
    assert all('DOCUMENTOS_CONFLITANTES'in d['bloqueios']and d['situacao']=='revisao'for d in afetados)
    assert all(l['unidade_id']!=afetados[0]['unidade_id']for l in r['linhas_teste'])


@pytest.mark.parametrize('alteracao',['hash','pagina','linha','versao','escopo'])
def test_ocorrencia_historica_so_e_vinculada_a_evidencia_exata(tmp_path,alteracao):
    blob=fonte();lote,ctx=ler_fonte(blob)
    original=next(o for o in resultado_leitura(lote,processamento_id='hist').ocorrencias if o.codigo=='SUBTOTAL_BLOCO_DIVERGENTE')
    values={'sha256':'0'*64}if alteracao=='hash'else{'pagina':1}if alteracao=='pagina'else{'linha':1}if alteracao=='linha'else{'leitor_versao':'outro@1'}if alteracao=='versao'else{}
    hist=original.model_copy(update={'id':'legado','origem':original.origem.model_copy(update=values),
        **({'escopo':'processamento'}if alteracao=='escopo'else{})})
    r=executar(tmp_path,historico=(hist,))
    assert not r['arquivo_teste_disponivel']and r['resumo']['boletos_retidos']==5
    assert 'legado'not in r['fechamento_habita']['ocorrencias_preservadas']


def test_historico_vinculado_preservado_sem_modificar_id_ou_gravidade(tmp_path):
    blob=fonte();lote,ctx=ler_fonte(blob)
    hist=next(o for o in resultado_leitura(lote,processamento_id='hist').ocorrencias if o.codigo=='SUBTOTAL_BLOCO_DIVERGENTE')
    hist=hist.model_copy(update={'id':'auditoria_legada_preservada'})
    r=executar(tmp_path,historico=(hist,))
    assert hist.model_dump(mode='json')in r['ocorrencias']
    assert hist.id in r['fechamento_habita']['ocorrencias_preservadas']
    assert r['resumo']['dividas_efetivamente_geradas']==3


@pytest.mark.parametrize('alteracao',['boleto_omitido','componente_omitido','origem_adulterada','vencimento_adulterado'])
def test_inventario_ou_canonico_parcial_nao_comprova_reconciliacao(alteracao):
    blob=fonte();lote,ctx=ler_fonte(blob)
    if alteracao=='boleto_omitido':lote=lote.model_copy(update={'boletos':lote.boletos[1:]})
    else:
        b=lote.boletos[0]
        if alteracao=='componente_omitido':b=b.model_copy(update={'composicao':b.composicao.model_copy(update={'itens':b.composicao.itens[:1]})})
        elif alteracao=='origem_adulterada':b=b.model_copy(update={'origens':(b.origens[0].model_copy(update={'sha256':'0'*64}),)})
        else:b=b.model_copy(update={'vencimento':b.vencimento.replace(day=2)})
        lote=lote.model_copy(update={'boletos':(b,)+lote.boletos[1:]})
    conf=conferir_fechamento_habita(blob,contexto=ctx,lote=lote,ocorrencias=resultado_leitura(lote,processamento_id='s').ocorrencias)
    assert conf['estado']=='nao_reconciliado'and conf['ocorrencias_preservadas']==[]


def test_divergencia_generica_continua_retida(tmp_path):
    blob=pdf_unidades([('S1','000001',[boleto('99000001')]),('VG','000001',[boleto('99000002')])],subtotal_divergente=True)
    r=executar(tmp_path,blob=blob)
    assert r['fechamento_habita']['estado']=='nao_reconciliado'
    assert r['resumo']['boletos_retidos']==2 and not r['arquivo_teste_disponivel']


@pytest.mark.parametrize('alteracao',['outro_rotulo','vg_inexistente','encargo_divergente'])
def test_padroes_parecidos_nao_recebem_dispensa(tmp_path,monkeypatch,alteracao):
    import tests.web.test_tree_group_veto as fixtures
    writer=fixtures.pdf_posicionado
    def modificar(paginas):
        novas=[]
        for pagina in paginas:
            rows=[]
            for x,y,t in pagina:
                if alteracao=='outro_rotulo':t=t.replace('Total do Bloco VG:','Total do Bloco S1:')
                elif alteracao=='vg_inexistente':t=t.replace('Bloco: VG','Bloco: S2')
                elif t.startswith('Total do Bloco VG:'):
                    partes=t.split();partes[-4]='2,00';partes[-1]='62,01';t=' '.join(partes)
                rows.append((x,y,t))
            novas.append(rows)
        return writer(novas)
    monkeypatch.setattr(fixtures,'pdf_posicionado',modificar)
    r=executar(tmp_path)
    assert r['fechamento_habita']['estado']=='nao_reconciliado'
    assert not r['arquivo_teste_disponivel']and r['resumo']['boletos_retidos']==5


def test_reprocessamento_deterministico_do_xlsx_e_manifesto(tmp_path):
    for nome in ('primeiro','segundo'):executar(tmp_path/nome,modo='B')
    for nome in ('TESTE_LOCAL_NAO_IMPORTAR.xlsx','manifesto_diagnostico.json','canonico.json'):
        assert (tmp_path/'primeiro'/nome).read_bytes()==(tmp_path/'segundo'/nome).read_bytes()


def test_colisao_de_identidade_nao_dispensa_outra_ocorrencia(tmp_path):
    blob=fonte();lote,ctx=ler_fonte(blob)
    atual=next(o for o in resultado_leitura(lote,processamento_id='fechamento_sintetico').ocorrencias if o.codigo=='SUBTOTAL_BLOCO_DIVERGENTE')
    outro=atual.model_copy(update={'codigo':'OUTRA_CRITICA_NAO_RECONCILIADA'})
    r=executar(tmp_path,historico=(outro,))
    assert not r['arquivo_teste_disponivel']
    assert r['fechamento_habita']['estado']=='nao_reconciliado'


def test_manifesto_http_autenticado_vinculado_ao_xlsx_e_relatorio(tmp_path):
    with TestClient(criar_app(tmp_path/'privado',acesso=KEY))as client:
        client.post('/api/session',json={'chave':KEY})
        job=aguardar(client,client.post('/api/processamentos',data={'data_ref':'2026-10-23','modo':'B'},
            files={'inadimplencia':('SINTETICO.pdf',fonte())}))
        assert job['estado']=='concluido'
        base='/api/processamentos/'+job['id']
        wb=client.get(base+'/arquivo-teste.xlsx');assert wb.status_code==200
        m=client.get(base+'/manifesto-diagnostico.json');assert m.status_code==200
        assert m.json()['arquivo']['sha256']==sha256(wb.content).hexdigest()
        r=client.get(base+'/inconsistencias.json').json()
        assert r['manifesto_diagnostico']==m.json()and r['fechamento_habita']['estado']=='reconciliado_somente_diagnostico'
        assert client.get(base+'/operacional.xlsx').status_code==409
        client.delete('/api/session')
        assert client.get(base+'/manifesto-diagnostico.json').status_code==401
        client.post('/api/session',json={'chave':KEY})
        assert client.get(base+'/manifesto-diagnostico.json').status_code==404
