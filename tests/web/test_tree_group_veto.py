"""Cota TREE = unidade; boletos/componentes e identidades inteiramente fictícios."""
from decimal import Decimal
import json

from openpyxl import load_workbook
import pytest

from conversor.web.service import PedidoDiagnostico, analisar, configurar, PERFIS
from examples.fase3.layouts_sinteticos import pdf_posicionado


def boleto(numero, *, valor='10.00', apontamento=None, vencimento='01/09/26', componentes=None, encargos=False):
    return {'numero':numero,'apontamento':apontamento,'vencimento':vencimento,
        'componentes':componentes or [(valor,'1.00' if encargos else '0.00','0.00','0.00')]}


def pdf_unidades(unidades, *, continuidade=False, subtotal_divergente=False, fechamento_vg=False):
    """Cada unidade em página própria; continuação repete o mesmo boleto na próxima."""
    pages=[];geral=[Decimal('0.00')]*5
    def valores(cs):
        total=[sum((Decimal(c[i]) for c in cs),Decimal('0.00')) for i in range(4)]
        return total+[sum(total)]
    def moeda(v):return format(v,'.2f').replace('.',',')
    def fin(prefixo,vs,y):return (31,y,prefixo+' '+' '.join(map(moeda,vs)))
    for ui,(bloco,numero,books) in enumerate(unidades):
        rows=[];y=715;total_unidade=[Decimal('0.00')]*5
        def cabecalho():
            return [(31,820,'Inadimplência Atualizada'),(31,800,'Condominio: 9999 - TREE MORUMBI'),
                (31,780,f'Bloco: {bloco} • Unidade: {numero} CONTATO SINTETICO CPF: (vazio)'),
                (31,750,'Boleto'),(100,750,'Vencimento'),(150,750,'Emissão'),(560,750,'Valor'),
                (620,750,'Multa'),(665,755,'Atualização'),(669,745,'Monetária'),
                (747,750,'Juros'),(810,750,'Total'),
                (31,40,'A'),(120,40,'AJ'),(190,40,'J')]
        rows=cabecalho()
        for bi,b in enumerate(books):
            vs=valores(b['componentes'])
            total_unidade=[a+c for a,c in zip(total_unidade,vs)]
            for ci,c in enumerate(b['componentes']):
                primeiro=ci==0 or (continuidade and ui==0 and bi==0 and ci==1)
                if primeiro:
                    rows.extend([(31,y,b['numero']),(100,y,b['vencimento']),(150,y,'010926'),
                                 (260,y,'94 COTA DESCRICAO A AJ J')])
                    if b['apontamento']:rows.append((75,y,b['apontamento']))
                else:rows.append((260,y,'1372 COMPONENTE SINTETICO'))
                rows.append((560,y,' '.join(map(moeda,valores([c])))));y-=23
                if continuidade and ui==0 and bi==0 and ci==0:
                    pages.append(rows);rows=cabecalho();y=715
            rows.append(fin('Total do boleto:',vs,y));y-=25
        rows.append(fin('Total da Unidade:',total_unidade,y));y-=25
        geral=[a+c for a,c in zip(geral,total_unidade)]
        if subtotal_divergente:
            errado=total_unidade.copy();errado[0]+=Decimal('1.00');errado[4]+=Decimal('1.00')
            rows.append(fin('Total do Bloco '+bloco+':',errado,y));y-=25
        if ui==len(unidades)-1:
            if fechamento_vg:
                rows.append(fin('Total do Bloco VG:',geral,y));y-=25
            rows.append(fin(f'Quantidade de unidades inadimplentes no condominio: {len(unidades)} Total Geral:',geral,y))
        pages.append(rows)
    return pdf_posicionado([[(x,y,t+' ') for x,y,t in sorted(rows,key=lambda a:(-a[1],a[0]))] for rows in pages])


def executar(tmp_path, blob, modo='B'):
    return analisar(blob,PedidoDiagnostico(data_ref='2026-10-23',modo=modo),
        processamento_id='hierarquia_tree_sintetica',destino=tmp_path)


def test_configuracao_reutiliza_quantificador_e_exclusao_terminal_do_motor():
    config=configurar(PERFIS['tree'],'habita_composicao_real_v1')
    assert config.versao=='1.1.0'
    exclusoes=[r for r in config.regras if r.acao=='excluir'and r.prioridade==1]
    assert len(exclusoes)==4
    assert all(r.alvo=='unidade'and r.quando.tipo=='existe_boleto'for r in exclusoes)
    assert any(r.alvo=='boleto'and r.quando.tipo=='dias_atraso'and r.quando.operador=='gt'and r.quando.valor==30 for r in config.regras)


@pytest.mark.parametrize('modo',['A','B'])
@pytest.mark.parametrize('codigo',[None,'A','AJ','J'])
def test_um_unico_boleto_veta_todo_grupo_sem_atingir_outra_unidade(tmp_path,modo,codigo):
    books=[boleto('99000001'),boleto('99000002',valor='0.01'if codigo is None else'10.00',
                 apontamento=codigo,vencimento='22/10/26'),boleto('99000003')]
    blob=pdf_unidades([('S1','000001',books),('S2','000001',[boleto('99000004')])])
    r=executar(tmp_path,blob,modo)
    ds=[d for d in r['decisoes']if d['bloco']=='S1'];group=next(c for c in r['cotas']if c['bloco']=='S1')
    assert len(ds)==3 and all(d['situacao_financeira']=='excluido' and d['veto_coletivo']for d in ds)
    assert len(group['causas_veto'])==1 and group['causas_veto'][0]['boleto']=='99000002'
    assert group['causas_veto'][0]['origens'][0]['pagina']==1
    assert group['regras_avaliadas'] and all(d['regras_da_cota']for d in ds)
    assert next(d for d in r['decisoes']if d['bloco']=='S2')['situacao']=='elegivel'
    assert r['resumo']['cotas']==2 and r['resumo']['boletos']==4
    assert r['resumo']['cotas_excluidas_por_veto']==1 and r['resumo']['boletos_excluidos_por_veto']==3
    assert r['resumo']['boletos_nao_selecionados_prazo']==0
    assert r['resumo']['cadastros_adicionais']==(1 if modo=='B'else 0)
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(wb['Dados'].values)[1:]
    assert len([row for row in rows if row[24]])==1
    assert sum(all(v is None for v in row[24:30])for row in rows)==(1 if modo=='B'else 0)
    wb.close()


def test_dez_boletos_centavo_sao_uma_unica_cota_vetada(tmp_path):
    books=[boleto(f'990000{i:02}',valor='0.01',encargos=True)for i in range(1,11)]
    r=executar(tmp_path,pdf_unidades([('S1','000001',books)]))
    assert r['resumo']['cotas_excluidas_centavo']==1 and r['resumo']['boletos']==10
    assert len(r['cotas'][0]['causas_veto'])==10
    assert r['resumo']['dividas_efetivamente_geradas']==0 and r['resumo']['cadastros_adicionais']==1


def test_multiplos_vetos_preservam_todas_as_causas(tmp_path):
    r=executar(tmp_path,pdf_unidades([('S1','000001',[
        boleto('99000001',valor='0.01',apontamento='A'),boleto('99000002',apontamento='AJ'),
        boleto('99000003',apontamento='J'),boleto('99000004')])]))
    c=r['cotas'][0]
    assert len(c['causas_veto'])==4
    assert {x['regra_id']for x in c['causas_veto']}=={'tree_centavo','tree_apontamento_a','tree_apontamento_aj','tree_apontamento_j'}
    assert r['resumo']['cotas_excluidas_centavo']==r['resumo']['cotas_excluidas_apontamentos']==1
    assert r['resumo']['cotas_excluidas_por_veto']==1  # contagens por motivo se sobrepõem


@pytest.mark.parametrize('modo',['A','B'])
def test_prazo_individual_componentes_legendas_e_parcelas_sem_veto(tmp_path,modo):
    blob=pdf_unidades([('S1','000001',[
        boleto('99000003',vencimento='22/09/26'), # 31 dias
        boleto('99000001',vencimento='23/09/26'), # 30 dias
        boleto('99000002',vencimento='10/08/26',componentes=[('0.01','0.00','0.00','0.00'),('10.00','0.00','0.00','0.00')])])])
    r=executar(tmp_path,blob,modo)
    assert r['resumo']['cotas_excluidas_por_veto']==0 and r['resumo']['cotas_elegiveis_pela_regua']==1
    assert r['resumo']['boletos_selecionados_pela_regua']==2 and r['resumo']['boletos_nao_selecionados_prazo']==1
    assert r['resumo']['cadastros_adicionais']==(1 if modo=='B'else 0)
    rows=[l for l in r['previa_template']['linhas']if l['tipo']=='divida']
    assert [l['cota']for l in rows]==['99000002','99000003']
    assert [l['valores'][27]for l in rows]==[1,2]
    assert [l['valores'][26]for l in rows]==['99000002','99000003'] # competência ausente
    assert next(d for d in r['decisoes']if d['boleto']=='99000002')['valor']=='10.01'


def test_continuidade_preserva_boleto_componentes_e_veto_da_unidade(tmp_path):
    blob=pdf_unidades([('S1','000001',[
        boleto('99000001',componentes=[('0.01','0.00','0.00','0.00'),('10.00','0.00','0.00','0.00')]),
        boleto('99000002',apontamento='AJ')])],continuidade=True)
    r=executar(tmp_path,blob)
    assert r['resumo']['cotas']==1 and r['resumo']['boletos']==2
    assert len(next(d for d in r['decisoes']if d['boleto']=='99000001')['componentes'])==2
    assert {o['pagina']for o in r['decisoes'][0]['origens']}=={1,2}
    assert all(d['veto_coletivo']for d in r['decisoes'])
    assert len(r['cotas'][0]['causas_veto'])==1


def test_retencao_tecnica_nao_oculta_selecao_financeira_nem_remove_veto(tmp_path):
    blob=pdf_unidades([('S1','000001',[boleto('99000001')]),
                      ('S2','000001',[boleto('99000002',valor='0.01')])],subtotal_divergente=True)
    r=executar(tmp_path,blob)
    assert r['resumo']['cotas_elegiveis_pela_regua']==r['resumo']['cotas_excluidas_por_veto']==1
    assert r['resumo']['boletos_selecionados_pela_regua']==1
    assert r['resumo']['cotas_retidas']==r['resumo']['boletos_retidos']==2
    assert r['resumo']['dividas_efetivamente_geradas']==0
    assert all('SUBTOTAL_BLOCO_DIVERGENTE'in c['impedimentos_tecnicos']for c in r['cotas'])
    assert r['previa_template']['linhas'] and all(l['bloqueada']for l in r['previa_template']['linhas'])
    assert not r['permite_exportacao_operacional'] and not (tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx').exists()


def test_campo_inconclusivo_na_unidade_nunca_autoriza_boleto_irmao(tmp_path,monkeypatch):
    import conversor.web.service as service
    real=service.conferir_apontamentos_habita
    def parcial(*args,**kwargs):
        completo=real(*args,**kwargs)
        campo=completo.campos[0].model_copy(update={'estado':'inconclusivo'})
        return completo.model_copy(update={'campos':(campo,)+completo.campos[1:]})
    monkeypatch.setattr(service,'conferir_apontamentos_habita',parcial)
    r=executar(tmp_path,pdf_unidades([('S1','000001',[boleto('99000001'),boleto('99000002')])]))
    assert r['resumo']['cotas_indeterminadas']==1 and r['resumo']['boletos_selecionados_pela_regua']==0
    assert all(d['situacao']=='revisao'for d in r['decisoes'])
