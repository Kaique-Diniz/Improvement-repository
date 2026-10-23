"""Regressões do incremento consolidado; nenhum conteúdo de clientes."""
from datetime import date
from io import BytesIO

from openpyxl import load_workbook
import pytest

from conversor.application.cadastro import cruzar_cadastro, reavaliar_pendencias_cadastrais
from conversor.domain.canonical import LoteCanonico, Ocorrencia, Pessoa
from conversor.web.demo import documentos_demo, pdf
from conversor.web.service import PedidoDiagnostico, analisar, ler, reconhecer
from examples.fase3.layouts_sinteticos import pdf_posicionado
from tests.web.test_unit_contacts import documentos, legado, lotes


def financeiro(specs, *, nome='TITULAR SINTETICO', marcador=None, separado=True, descricao='COTA'):
    textos=['W002A CONDOMINIO EDIFICIO PLAZA MAYOR IPIRANGA (9999)',
            'Inadimplência com composição','Posição em 23/10/2026','Venc. Comp. Cod. Descrição Valor Saldo']
    rows=[(31,800-i*14,t)for i,t in enumerate(textos)]
    y=744;total=0
    for bloco,numero,nome_unidade in [('A','0001',nome),('B','0002','EMPRESA SINTETICA')]:
        rows.append((31,y,f'{numero} TORRE {bloco} - '+nome_unidade+(' '+marcador if marcador and not separado and bloco=='A' else '')))
        if marcador and separado and bloco=='A':rows.append((471.12,y,marcador))
        y-=14;saldo=0
        for id_,vencimento,competencia in specs[bloco]:
            saldo+=10;total+=10
            rows.append((31,y,f'{vencimento} {competencia} {id_} {descricao} 10,00 {saldo},00'));y-=14
    rows.extend([(31,y,f'2 unidades inadimplentes (1,00%) {total},00'),
                 (31,58,'ADMINISTRADORA SINTETICA'),(31,24,'1 de 1')])
    return pdf([rows])


SPECS={'A':[('900300','10/01/26','01/2026'),('900100','10/12/25','12/2025'),
            ('900250','05/01/26','01/2026'),('900200','10/01/26','01/2026'),('900400','01/10/26','10/2026')],
       'B':[('900010','10/06/26','06/2026')]}


def executar(tmp_path, data, *, cadastro=None, modo='B', historico=()):
    return analisar(data,PedidoDiagnostico(data_ref='2026-10-23',modo=modo),
        processamento_id='incremento_consolidado_sintetico',destino=tmp_path,cadastro=cadastro,historico=historico)


@pytest.mark.parametrize('modo',['A','B'])
@pytest.mark.parametrize('retida',[False,True])
def test_parcelas_por_contrato_vencimento_desempate_ano_sem_consumir_retidas(tmp_path, modo, retida):
    data=financeiro(SPECS)
    perfil,codigo,formato=reconhecer(data);lote,_=ler(data,perfil,codigo,formato,'inadimplencia')
    bloqueado=next(b for b in lote.boletos if b.identificador=='900250')
    hist=(Ocorrencia(id='bloqueio_boleto_sintetico',processamento_id='anterior',codigo='COMPOSICAO_SOB_REVISAO',
        gravidade='critico',escopo='registro',registro_id=bloqueado.id,origem=bloqueado.origens[0]),)if retida else ()
    r=executar(tmp_path,data,modo=modo,historico=hist)
    wb=load_workbook(tmp_path/'TESTE_LOCAL_NAO_IMPORTAR.xlsx');rows=list(wb['Dados'].iter_rows(min_row=2,values_only=True))
    dividas=[row for row in rows if row[27]is not None]
    a=[row for row in dividas if row[1]=='10001'];b=[row for row in dividas if row[1]=='20002']
    assert [row[27]for row in a]==list(range(1,len(a)+1))
    assert [row[27]for row in b]==[1]
    esperado=['900100','900200','900300']if retida else ['900100','900250','900200','900300']
    ids={b.id:b.identificador for b in lote.boletos}
    assert [ids[l['boleto_id']]for l in r['linhas_teste']if l['tipo']=='divida'and l['unidade_id']==lote.unidades[0].id]==esperado
    assert [row[28].date()for row in a]==sorted(row[28].date()for row in a)
    for row in dividas:
        assert row[26]==f'COTA {row[28].month:02d}/{row[28].year} - {row[27]}'
        assert row[29]==10
    assert len({l['boleto_id']for l in r['linhas_teste']if l['tipo']=='divida'})==len(dividas)
    prevista=r['previa_template']['linhas']
    for l in prevista:
        if l['tipo']=='divida'and not l['bloqueada']:
            codigo=r['codificacao_template']['unidades'][l['unidade_id']]['cedente']
            row=next(row for row in dividas if row[1]==codigo and row[27]==l['parcela_final'])
            assert l['valores'][26]==row[26] and l['valores'][27]==row[27]
        elif l['tipo']=='divida':
            assert l['parcela_final']is None and l['numeracao_pendente'] and l['valores'][27]==''
    assert sum(all(v is None for v in row[24:30])for row in rows)==(1 if modo=='B'and not retida else 0)
    assert not r['permite_exportacao_operacional'];wb.close()


def test_ordem_de_leitura_nao_altera_sequencia_final(tmp_path):
    a=executar(tmp_path/'a',financeiro(SPECS),modo='A')
    inversas={k:list(reversed(v))for k,v in SPECS.items()}
    b=executar(tmp_path/'b',financeiro(inversas),modo='A')
    def proj(r):return [(l['cota'],l['valores'][26:30])for l in r['previa_template']['linhas']]
    assert proj(a)==proj(b)


def habita(codigo=None, centavo=False):
    from pypdf import PdfReader
    from tests.phase3.test_habita_point_coverage import pdf_campo
    pages=[]
    for page in PdfReader(BytesIO(pdf_campo(codigo))).pages:
        rows=[]
        def visitar(text,cm,tm,font,size):
            if not text.strip():return
            text=text.strip().replace('9999 - SINTETICO','9999 - TREE MORUMBI').replace('01/10/26','01/09/26')
            if centavo:text=text.replace('10,00','0,01')
            rows.append((tm[4],tm[5],text+' '))
        page.extract_text(visitor_text=visitar);pages.append(rows)
    return pdf_posicionado(pages)


def test_rotulo_tree_por_vencimento_preserva_identificador_e_competencia_ausente(tmp_path):
    r=executar(tmp_path,habita(),modo='A')
    assert len(r['linhas_teste'])==1 and r['decisoes'][0]['competencia']is None
    l=r['previa_template']['linhas'][0]
    assert l['valores'][26]=='COTA 09/2026 - 1' and l['valores'][27]==1
    assert r['rotulos_template'][r['decisoes'][0]['id']]['identificador_origem']==r['decisoes'][0]['cota']


@pytest.mark.parametrize('codigo,centavo', [('A',False),('AJ',False),('J',False),(None,True)])
@pytest.mark.parametrize('modo',['A','B'])
def test_mvp_preserva_exclusoes_tree_por_cota(tmp_path,codigo,centavo,modo):
    r=executar(tmp_path,habita(codigo,centavo),modo=modo)
    assert r['resumo']['nao_elegiveis_pela_regua']==1
    assert not any(l['tipo']=='divida'for l in r['linhas_teste'])
    assert r['resumo']['cadastros_adicionais']==(1 if modo=='B'else 0)
    assert all(l['valores'][24:30]==['']*6 for l in r['previa_template']['linhas'])


@pytest.mark.parametrize('marcador',['1º Notificação','2ª NOTIFICAÇÃO','3° Notificacao','4o Notificacao'])
@pytest.mark.parametrize('separado',[True,False])
def test_notificacao_apenas_no_cabecalho_preservada_na_auditoria(marcador,separado):
    specs={'A':[('900001','10/09/26','09/2026')],'B':[('900002','10/09/26','09/2026')]}
    data=financeiro(specs,marcador=marcador,separado=separado)
    perfil,codigo,formato=reconhecer(data);lote,_=ler(data,perfil,codigo,formato,'inadimplencia')
    original,_=ler(financeiro(specs),perfil,codigo,formato,'inadimplencia')
    assert lote.pessoas[0].nome=='TITULAR SINTETICO'
    assert [b.composicao.total_original for b in lote.boletos]==[b.composicao.total_original for b in original.boletos]
    assert [(b.id,b.identificador,b.vencimento,b.competencia,b.saldo_acumulado)for b in lote.boletos]==[(b.id,b.identificador,b.vencimento,b.competencia,b.saldo_acumulado)for b in original.boletos]
    aud=[r for r in lote.ressalvas if r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO']
    assert len(aud)==1 and aud[0].gravidade=='informativo' and marcador in aud[0].valores_originais
    assert aud[0].origens[1].identificador.startswith('fl_cabecalho_fragmento_')
    cad_data=documentos_demo()['cadastro'];pc,cc,lc=reconhecer(cad_data,cadastro=True)
    cad,_=ler(cad_data,pc,cc,lc,'cadastro')
    unido=cruzar_cadastro(lote,cad)
    assert not any(r.codigo=='DIVERGENCIA_NOME_ENTRE_FONTES'for r in unido.ressalvas)


@pytest.mark.parametrize('nome',['ASSOCIACAO NOTIFICACAO / OUTRO CONTATO','EMPRESA 1º NOTIFICAÇÃO LTDA'])
def test_nomes_legitimos_e_descricao_financeira_nao_sofrem_substituicao(nome):
    specs={'A':[('900001','10/09/26','09/2026')],'B':[('900002','10/09/26','09/2026')]}
    data=financeiro(specs,nome=nome,descricao='SERVICO 1º Notificação')
    perfil,codigo,formato=reconhecer(data);lote,_=ler(data,perfil,codigo,formato,'inadimplencia')
    assert lote.pessoas[0].nome==nome
    assert all('1º Notificação'in b.composicao.itens[0].descricao_original for b in lote.boletos)
    assert not any(r.codigo=='MARCADOR_ADMINISTRATIVO_NO_CABECALHO'for r in lote.ressalvas)


def test_historico_nome_reavaliado_sem_remover_conflito_documental(tmp_path):
    dados=documentos('OUTRO CONTATO SINTETICO',docs=('00000000191','00000000272'))
    financeiro,cad=lotes(dados)
    nome=legado(cad,'TITULAR_DIVERGENTE',origem=financeiro.pessoas[0].origem,id_='legado_nome')
    conflito=legado(cad,'DOCUMENTOS_CONFLITANTES',id_='legado_documentos')
    r=executar(tmp_path,dados['inadimplencia'],cadastro=dados['cadastro'],historico=(nome,conflito))
    assert [o['ocorrencia_id']for o in r['reavaliacoes_historicas']]==[nome.id]
    assert nome.model_dump(mode='json')in r['ocorrencias'] and conflito.model_dump(mode='json')in r['ocorrencias']
    assert all(d['situacao']=='revisao'and'DOCUMENTOS_CONFLITANTES'in d['bloqueios']and'TITULAR_DIVERGENTE'not in d['bloqueios']
               for d in r['decisoes']if d['bloco']=='A')


def test_cadastro_ausente_ou_unidade_ausente_preserva_fonte_financeira(tmp_path):
    dados=documentos_demo();fin,cad=lotes(dados)
    somente_b=LoteCanonico(unidades=(cad.unidades[1],),boletos=(),pessoas=(cad.pessoas[1],),
                          ressalvas=tuple(r for r in cad.ressalvas if r.registro_id==cad.unidades[1].id))
    unido=cruzar_cadastro(fin,somente_b)
    assert unido.pessoas[0]==fin.pessoas[0] and unido.boletos==fin.boletos
    r=executar(tmp_path,dados['inadimplencia'],modo='A')
    assert not r['resumo'].get('revisao',0)
    assert all(l['valores'][2]==''for l in r['previa_template']['linhas'])


@pytest.mark.parametrize('alteracao',['administradora','condominio','torre'])
def test_identidade_estrutural_impede_mistura_entre_cadastros(alteracao):
    from conversor.readers.text_support import ErroLeitura
    fin,cad=lotes(documentos())
    if alteracao=='torre':
        from conversor.domain.identity import chave_unidade
        u=cad.unidades[0].model_copy(update={'bloco_original':'C','chave_normalizada':chave_unidade('C','0001')})
        cad=cad.model_copy(update={'unidades':(u,cad.unidades[1])})
        r=cruzar_cadastro(fin,cad)
        assert r.pessoas[0]==fin.pessoas[0]
    else:
        field='administradora_id'if alteracao=='administradora'else'condominio_id'
        cad=cad.model_copy(update={'unidades':tuple(u.model_copy(update={field:'outra_identidade'})for u in cad.unidades)})
        with pytest.raises(ErroLeitura):cruzar_cadastro(fin,cad)


def test_contato_cadastral_preferencial_e_fallback_sem_endereco_hibrido():
    from conversor.domain.canonical import Contato, Endereco, Telefone
    fin,cad=lotes(documentos('CONTATO CADASTRAL SINTETICO'))
    p=fin.pessoas[0].model_copy(update={'contato':Contato(telefones=(Telefone(ddd='11',numero='900000001'),),
        emails=('origem@example.invalid',),endereco=Endereco(logradouro='Rua Financeira',numero='10',cidade='Cidade Sintetica'),
        origem=fin.pessoas[0].origem)})
    cp=cad.pessoas[0].model_copy(update={'contato':Contato(emails=('cadastro@example.invalid',),
        endereco=Endereco(logradouro='Rua Cadastral'),origem=cad.pessoas[0].origem)})
    fin=fin.model_copy(update={'pessoas':(p,fin.pessoas[1])});cad=cad.model_copy(update={'pessoas':(cp,cad.pessoas[1])})
    unido=cruzar_cadastro(fin,cad);contato=unido.pessoas[0].contato
    assert unido.pessoas[0].nome==cp.nome and contato.emails==cp.contato.emails
    assert contato.telefones==p.contato.telefones
    assert contato.endereco==cp.contato.endereco and contato.endereco.numero==''
    assert any(r.codigo=='CONTATO_COMPLEMENTADO_DA_INADIMPLENCIA'and len(r.origens)==2 for r in unido.ressalvas)
    assert unido.boletos==fin.boletos


@pytest.mark.parametrize('prova',['hash_diferente','unidade_diferente','cadastro_ausente'])
def test_nome_historico_sem_vinculo_estrutural_documental_continua_retido(tmp_path,prova):
    dados=documentos('OUTRO CONTATO SINTETICO');fin,cad=lotes(dados)
    old=legado(cad,'TITULAR_DIVERGENTE',origem=fin.pessoas[0].origem)
    if prova=='hash_diferente':old=old.model_copy(update={'origem':old.origem.model_copy(update={'sha256':'f'*64})})
    if prova=='unidade_diferente':old=old.model_copy(update={'registro_id':'outra_unidade'})
    r=executar(tmp_path,dados['inadimplencia'],cadastro=None if prova=='cadastro_ausente'else dados['cadastro'],historico=(old,))
    assert not r['reavaliacoes_historicas']
    assert r['resumo']['revisao']>0
    assert old.model_dump(mode='json')in r['ocorrencias']
