"""Exemplos inteiramente sintéticos de geometria real; sem PDFs privados no Git."""
from datetime import date
from decimal import Decimal
from hashlib import sha256

import pytest

from conversor.application.cadastro import cruzar_cadastro
from conversor.application.reading import resultado_leitura
from conversor.domain.canonical import Documento, EvidenciaDocumento, LoteCanonico, Pessoa
from conversor.domain.documents import resolver_documento
from conversor.export.build_lines import PerfilSaidaLaboratorio, construir_linhas
from conversor.readers.contracts import FonteProtegida
from conversor.readers.operational import RegistroLeitores, validar_assinatura_para_leitura
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from examples.fase3.layouts_sinteticos import cadastro_paginas, fl_paginas, habita_paginas, pdf_posicionado


IDS={'habita':'habita_composicao_real_v1','fl':'fl_composicao_real_v1','cadastro':'cadastro_fl_real_v1'}
PAGINAS={'habita':habita_paginas,'fl':fl_paginas,'cadastro':cadastro_paginas}


def ler(familia,paginas=None,*,codigo='9999',condominio='cond_sintetico',arquivo=None):
    blob=pdf_posicionado(paginas if paginas is not None else PAGINAS[familia]())
    ident=arquivo or familia
    class Fontes:
        def ler(self,fonte):return blob
    class Contextos:
        def resolver(self,fonte,*,formato_id,condominio_id):
            return ContextoLeitura(condominio,'adm_sintetica','fmt_'+familia,fonte.arquivo_id,codigo,leitor_versao=IDS[familia]+'@1')
    fonte=FonteProtegida(arquivo_id=ident,sha256=sha256(blob).hexdigest())
    return RegistroLeitores(Fontes(),Contextos()).obter(IDS[familia],'1').ler(fonte,formato_id='fmt_'+familia,condominio_id=condominio)


def trocar(paginas,antes,depois):
    return [[(x,y,t.replace(antes,depois))for x,y,t in pagina]for pagina in paginas]


def test_habita_atualizacao_monsta_emissao_sem_inferencia_e_continuacao():
    lote=ler('habita');b=lote.boletos[0]
    assert (len(lote.unidades),len(lote.boletos),len(b.composicao.itens))==(1,1,2)
    assert b.composicao.total_original==Decimal('120.00')
    assert (b.multa,b.correcao,b.juros)==tuple(map(Decimal,('2.00','3.00','4.00')))
    assert b.competencia is None and b.emissao is None and b.emissao_original=='090926'
    assert b.vencimento==date(2026,9,17)
    assert {o.pagina for o in b.origens}=={1,2}
    assert b.composicao.itens[1].origem.continuacao_de==b.composicao.itens[0].origem.identificador
    assert resolver_documento(lote.pessoas[0]).valor=='00000000191'


@pytest.mark.parametrize('antes,depois,codigo',[
    ('20,00 0,00 0,00 0,00 20,00','20,00 0,00 0,00 0,00 99,00','SOMA_ITEM_INCONSISTENTE'),
    ('Total do boleto: 120,00','Total do boleto: 121,00','SOMA_ITEM_INCONSISTENTE'),
    ('1 Total Geral:','2 Total Geral:','CONTAGEM_DE_UNIDADES_DIVERGENTE'),
    ('17/09/26','17/13/26','DATA_DE_BOLETO_INVALIDA'),
    ('100,00 2,00 3,00 4,00 109,00','100,00 2,00 4,00 106,00','LINHA_FINANCEIRA_NAO_RECONHECIDA'),
    ('90000001 17/09','90000001 X 17/09','CABECALHO_BOLETO_INVALIDO'),
])
def test_habita_nao_ignora_campos_financeiros_invalidos(antes,depois,codigo):
    with pytest.raises(ErroLeitura,match=codigo):ler('habita',trocar(habita_paginas(),antes,depois))


def test_habita_truncada_sem_global_bloqueia():
    with pytest.raises(ErroLeitura,match='TOTAL_GERAL_AUSENTE'):ler('habita',habita_paginas()[:1])


def test_habita_repeticao_de_boleto_no_mesmo_pagina_bloqueia():
    ps=habita_paginas();ps[1].insert(8,(31,690,ps[1][7][2]))
    with pytest.raises(ErroLeitura,match='DUPLICIDADE_NAO_RECONCILIADA'):ler('habita',ps)


def test_habita_subtotal_divergente_preserva_valores_mas_bloqueia_exportacao():
    ps=habita_paginas();ps[1].insert(-1,(31,655,'Total do Bloco VG: 120,00 2,00 3,00 4,00 129,00'))
    lote=ler('habita',ps)
    assert lote.boletos[0].composicao.total_original==Decimal('120.00')
    r=resultado_leitura(lote,processamento_id='exec')
    assert r.bloqueante and any(o.codigo=='SUBTOTAL_BLOCO_DIVERGENTE'for o in r.ocorrencias)
    perfil=PerfilSaidaLaboratorio(codificador='habita_bloco_unidade',nome_cedente='SINTETICO',produto='SINTETICO')
    with pytest.raises(ErroLeitura,match='LEITURA_COM_PENDENCIA_CRITICA'):
        construir_linhas(lote,(),perfil,politica_cadastro='nunca',processamento_id='exec')


def test_fl_reconstroi_desconto_saldo_e_valores_em_linhas_separadas():
    lote=ler('fl')
    assert (len(lote.unidades),len(lote.boletos))==(2,3)
    assert [b.composicao.total_original for b in lote.boletos]==list(map(Decimal,('85.00','10.00','40.00')))
    assert [i.valor for i in lote.boletos[0].composicao.itens]==list(map(Decimal,('100.00','-20.00','5.00')))
    assert lote.boletos[1].saldo_acumulado==Decimal('95.00')
    assert lote.boletos[0].correcao is None and lote.boletos[0].multa is None
    assert {o.pagina for o in lote.boletos[0].origens}=={1,2}
    assert all('administradora'not in i.descricao_original.casefold()for b in lote.boletos for i in b.composicao.itens)
    assert any(r.codigo=='NOTA_ADMINISTRATIVA_COM_VALOR'for r in lote.ressalvas)


@pytest.mark.parametrize('antes,depois,codigo',[
    ('5,00 85,00','5,00 99,00','SALDO_ACUMULADO_INCONSISTENTE'),
    ('(20,00) 80,00','20,00 80,00','SALDO_ACUMULADO_INCONSISTENTE'),
    ('10,00 95,00','10,00','LINHA_FINANCEIRA_NAO_RECONHECIDA'),
    ('900002','900001','DUPLICIDADE_NAO_RECONCILIADA'),
    ('2 de 2','2 de 3','PAGINACAO_INCOMPLETA'),
    ('2 unidades inadimplentes','3 unidades inadimplentes','CONTAGEM_DE_UNIDADES_DIVERGENTE'),
    ('(1,00%) 135,00','(1,00%) 136,00','SOMA_GERAL_INCONSISTENTE'),
    ('18/09/26 09/2026','18/09/26 13/2026','CONTRATO_DE_LEITURA_INVALIDO'),
])
def test_fl_bloqueia_saldo_duplicidade_e_paginacao(antes,depois,codigo):
    with pytest.raises(ErroLeitura,match=codigo):ler('fl',trocar(fl_paginas(),antes,depois))


def test_fl_pagina_faltante_bloqueia():
    with pytest.raises(ErroLeitura,match='PAGINACAO_INCOMPLETA'):ler('fl',fl_paginas()[:1])


def test_fl_descricao_depois_do_valor_continua_sem_virar_novo_item():
    ps=fl_paginas();ps[1].insert(1,(31,792,'COMPLEMENTO DA DESCRICAO ANTERIOR'))
    lote=ler('fl',ps)
    assert 'COMPLEMENTO DA DESCRICAO ANTERIOR'in lote.boletos[0].composicao.itens[1].descricao_original
    assert len(lote.boletos[0].composicao.itens)==3


def test_fl_leitura_de_consumo_na_descricao_nao_vira_valor_financeiro():
    ps=fl_paginas();ps[1].insert(1,(31,792,'   AGUA CONSUMO 1.000,0000 - 1.005,'))
    lote=ler('fl',ps)
    assert lote.boletos[0].composicao.total_original==Decimal('85.00')
    assert '1.000,0000'in lote.boletos[0].composicao.itens[-1].descricao_original


def test_fl_consumo_na_coluna_descricao_termina_em_decimal():
    ps=fl_paginas();ps[1].insert(1,(262.7,792,'(m3) = 12,00'))
    lote=ler('fl',ps)
    assert lote.boletos[0].composicao.total_original==Decimal('85.00')
    assert '(m3) = 12,00'in lote.boletos[0].composicao.itens[1].descricao_original


def test_fl_nota_com_par_de_valores_nao_e_ignorada():
    ps=fl_paginas();ps[1]=ps[1][:8]+[(31,688,'   VALOR AMBIGUO 10,00 105,00')]+[(x,y-14 if y>65 else y,t)for x,y,t in ps[1][8:]]
    with pytest.raises(ErroLeitura,match='VALOR_FINANCEIRO_EM_NOTA_AMBIGUA'):ler('fl',ps)


def test_fl_valor_em_nota_administrativa_sem_saldo_nao_integra_cobranca():
    ps=fl_paginas();ps[1]=ps[1][:8]+[(31,688,'123,00 EM 2 PARCELAS REGISTRO ADMINISTRATIVO')]+[(x,y-14 if y>65 else y,t)for x,y,t in ps[1][8:]]
    lote=ler('fl',ps)
    assert [b.composicao.total_original for b in lote.boletos]==list(map(Decimal,('85.00','10.00','40.00')))
    assert sum(r.codigo=='NOTA_ADMINISTRATIVA_COM_VALOR'for r in lote.ressalvas)==2


def test_cadastro_coordenadas_torre_quebrada_contato_entre_paginas_e_cnpj():
    lote=ler('cadastro')
    assert len(lote.unidades)==2 and not lote.boletos
    assert {u.chave_normalizada for u in lote.unidades}=={'A/1','B/2'}
    assert resolver_documento(lote.pessoas[0]).valor=='00000000191'
    assert resolver_documento(lote.pessoas[1]).valor=='00000000000191'
    assert lote.pessoas[0].contato.telefones[0].numero=='900000001'
    assert lote.pessoas[0].contato.origem.pagina==1 # e-mail com origem inicial preservada
    brutos=next(r for r in lote.ressalvas if r.codigo=='CADASTRO_CAMPOS_ORIGINAIS')
    assert any('"pagina": 2'in s for s in brutos.valores_originais)
    assert all('ADMINISTRADORA SINTETICA'not in p.nome for p in lote.pessoas)


def test_cadastro_docs_validos_conflitantes_nao_escolhe_cpf_ou_cnpj():
    ps=cadastro_paginas();ps[0].append((534,720,'00000000000191'))
    lote=ler('cadastro',ps)
    resolucao=resolver_documento(lote.pessoas[0])
    assert resolucao.bloqueante and not resolucao.valor
    assert len(resolucao.evidencias)==2
    assert {'DOCUMENTOS_CONFLITANTES','DOCUMENTO_TITULAR_NAO_CONFIRMADO'}<=set(resolucao.codigos)


def test_cadastro_torre_ausente_bloqueia():
    ps=cadastro_paginas();ps[0]=[c for c in ps[0]if c[2]!='A']
    with pytest.raises(ErroLeitura,match='CADASTRO_IDENTIDADE_INCOMPLETA'):ler('cadastro',ps)


def test_cadastro_chave_repetida_bloqueia():
    ps=cadastro_paginas();ps[1]=[(x,y,t.replace('0002 TORRE','0001 TORRE').replace('B','A')if x==31 else t)for x,y,t in ps[1]]
    with pytest.raises(ErroLeitura,match='CADASTRO_AMBIGUO'):ler('cadastro',ps)


def test_cadastro_contatos_excedentes_auditados():
    ps=cadastro_paginas();ps[0].append((609,720,'a@example.invalid;b@example.invalid;c@example.invalid;d@example.invalid'))
    lote=ler('cadastro',ps)
    assert len(lote.pessoas[0].contato.emails)==3
    assert any(r.codigo=='CONTATOS_EXCEDENTES_PRESERVADOS'for r in lote.ressalvas)
    assert any('d@example.invalid'in v for r in lote.ressalvas for v in r.valores_originais)


def test_cadastro_mudanca_geometrica_da_coluna_documento_bloqueia():
    from conversor.readers.cadastro_real import LeitorCadastroFLReal
    ps=cadastro_paginas();ps[0]=[(x+60 if t=='CPF/CNPJ'else x,y,t)for x,y,t in ps[0]]
    with pytest.raises(ErroLeitura,match='COLUNAS_CADASTRAIS_INCOMPATIVEIS'):
        LeitorCadastroFLReal().ler(pdf_posicionado(ps),contexto=ContextoLeitura('cond','adm','fmt','fixture','9999'))


def test_cadastro_sem_ultima_pagina_bloqueia():
    with pytest.raises(ErroLeitura,match='PAGINACAO_INCOMPLETA'):ler('cadastro',cadastro_paginas()[:1])


def test_revisoes_sintetica_e_real_misturadas_bloqueiam():
    ps=fl_paginas();ps[1].insert(0,(31,830,'W002A CONDOMINIO EDIFICIO SINTETICO (AMOSTRA SINTETICA)'))
    with pytest.raises(ErroLeitura,match='CABECALHO_CONDOMINIO_INVALIDO'):ler('fl',ps)


@pytest.mark.parametrize('familia',['habita','fl','cadastro'])
def test_identidade_forte_divergente_e_ambigua_bloqueia(familia):
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DIVERGENTE_OU_AMBIGUO'):ler(familia,codigo='8888')
    ps=PAGINAS[familia]();ps[-1].append((31,120,('Condominio: 8888 - OUTRO'if familia=='habita'else
        ('W045A'if familia=='cadastro'else'W002A')+' CONDOMINIO OUTRO (8888)')))
    with pytest.raises(ErroLeitura,match='CONDOMINIO_DIVERGENTE_OU_AMBIGUO'):ler(familia,ps)


@pytest.mark.parametrize('familia',['habita','fl','cadastro'])
def test_leitor_real_reutilizavel_em_outro_condominio(familia):
    outro=trocar(PAGINAS[familia](),'9999','8888')
    a=ler(familia);b=ler(familia,outro,codigo='8888',condominio='outro_condominio')
    assert a.unidades[0].id!=b.unidades[0].id
    assert [b.composicao.total_original for b in a.boletos]==[b.composicao.total_original for b in b.boletos]


@pytest.mark.parametrize('familia',['habita','fl','cadastro'])
def test_proveniencia_real_versao_hash_pagina_linha(familia):
    ps=PAGINAS[familia]();blob=pdf_posicionado(ps);lote=ler(familia,ps)
    for u in lote.unidades:
        assert (u.origem.arquivo_id,u.origem.sha256,u.origem.leitor_versao)==(familia,sha256(blob).hexdigest(),IDS[familia]+'@1')
        assert u.origem.pagina>=1 and u.origem.linha>=1
    assert lote==ler(familia,ps)


def test_layout_real_e_sintetico_nao_sao_selecionados_ambiguamente():
    blob=pdf_posicionado(habita_paginas())
    validar_assinatura_para_leitura(blob,IDS['habita'])
    with pytest.raises(ErroLeitura,match='FORMATO_DIVERGENTE_DO_LEITOR'):
        validar_assinatura_para_leitura(blob,'habita_composicao_sintetico_v1')
    blob=pdf_posicionado(habita_paginas()+fl_paginas())
    with pytest.raises(ErroLeitura,match='FORMATO_AMBIGUO'):validar_assinatura_para_leitura(blob,IDS['habita'])


def test_cruzamento_canonico_por_condominio_torre_e_unidade():
    devedor=ler('fl');cadastro=ler('cadastro')
    unido=cruzar_cadastro(devedor,cadastro)
    assert unido.boletos==devedor.boletos
    assert [resolver_documento(p).valor for p in unido.pessoas]==['00000000191','00000000000191']
    assert all(p.documento_origem.arquivo_id=='cadastro'for p in unido.pessoas)
    assert all(u.origem.arquivo_id=='fl'for u in unido.unidades)
    with pytest.raises(ErroLeitura,match='CADASTRO_DE_OUTRO_CONDOMINIO'):
        cruzar_cadastro(devedor,ler('cadastro',condominio='outra_identidade'))


def test_cruzamento_nao_aplica_prioridade_laboratorial_a_titular_divergente():
    devedor=ler('fl');cadastro=ler('cadastro',trocar(cadastro_paginas(),'TITULAR SINTETICO','OUTRO TITULAR'))
    unido=cruzar_cadastro(devedor,cadastro)
    r=resultado_leitura(unido,processamento_id='exec_real')
    assert any(o.codigo=='TITULAR_DIVERGENTE'and o.bloqueante for o in r.ocorrencias)
    assert unido.pessoas[0].nome==devedor.pessoas[0].nome
    assert not resolver_documento(unido.pessoas[0]).valor


def test_cruzamento_cpf_valido_conflitante_mantem_duas_fontes():
    devedor=ler('fl');cadastro=ler('cadastro')
    p=Pessoa.model_validate(devedor.pessoas[0].model_dump()|{'documento':Documento(tipo='cpf',valor='00000000272')})
    devedor=LoteCanonico.model_validate(devedor.model_dump()|{'pessoas':(p,devedor.pessoas[1])})
    unido=cruzar_cadastro(devedor,cadastro)
    resolucao=resolver_documento(unido.pessoas[0])
    assert resolucao.bloqueante and not resolucao.valor
    assert {e.origem.arquivo_id for e in resolucao.evidencias}=={'fl','cadastro'}


def test_habita_competencia_ausente_nao_e_fabricada_no_exportador():
    from conversor.domain.canonical import ResultadoCobranca
    lote=ler('habita');u=lote.unidades[0];b=lote.boletos[0]
    decisao=ResultadoCobranca(processamento_id='exec',unidade_id=u.id,boleto_id=b.id,
        acao='incluir',regra_id='fixture_sem_regra_real',regra_versao='1',motivo_codigo='teste',origens=b.origens)
    perfil=PerfilSaidaLaboratorio(codificador='habita_bloco_unidade',nome_cedente='SINTETICO',produto='SINTETICO')
    with pytest.raises(ErroLeitura,match='COMPETENCIA_NAO_INFORMADA'):
        construir_linhas(lote,(decisao,),perfil,politica_cadastro='nunca',processamento_id='exec')


@pytest.mark.parametrize('familia',['habita','fl','cadastro'])
def test_caso_de_uso_reconhece_le_e_exige_aprovacao_de_configuracao(catalogo_leitura,familia):
    from conversor.adapters.document_probe import SondadorLocal
    from conversor.application.ports import Estado
    from conversor.application.reading import LerDocumento
    from conversor.application.recognition import ReconhecerDocumento
    from conversor.domain.catalog import Catalogo
    from conversor.domain.recognition import CatalogoAssinaturas
    # Somente fixture: esses campos de identificação e aprovações NÃO são inseridos
    # nos PDFs reais nem aprovam cadastros/perfis/regras de produção.
    ps=PAGINAS[familia]();ps[0]=[(31,837,'Administradora: ADM-LAB'),(31,824,'Codigo Condominio: 9999')]+ps[0]
    blob=pdf_posicionado(ps);fonte=FonteProtegida(arquivo_id='fixture_real',sha256=sha256(blob).hexdigest())
    i=['habita','fl','cadastro'].index(familia);dados=catalogo_leitura.model_dump(mode='json')
    for n,c in enumerate(dados['condominios']):c['codigo_na_administradora']=str(9000+n)
    aprovacao={'responsavel_id':'teste','evidencia_id':'fixture_sintetica','em':'2026-10-21T00:00:00Z'}
    dados['formatos'][i].update(leitor_id=IDS[familia],status='validado',aprovacao=aprovacao)
    dados['condominios'][i]['codigo_na_administradora']='9999'
    dados['perfis_condominio'][i].update(status='aprovado',aprovacao=aprovacao)
    dados['regras_cobranca'][i].update(status='aprovada',aprovacao=aprovacao,
        fonte={'arquivo_id':fonte.arquivo_id,'sha256':fonte.sha256,'leitor_versao':'fixture','pagina':1,'identificador':'fixture'},
        condicoes=[{'campo':'fixture','operador':'igual','valor':'teste','alcance':'boleto','acao':'alertar','prioridade':0}])
    class Repo:
        def carregar(self):return Estado(revisao=1,catalogo=Catalogo.model_validate(dados))
    marcadores={'habita':['Inadimplencia Atualizada','Monetaria'],
                'fl':['Inadimplencia com composicao','W002A'],'cadastro':['W045A','CPF/CNPJ']}[familia]
    assinatura=CatalogoAssinaturas.model_validate({'versao':'fixture','status':'homologado','aprovacao':aprovacao,
        'layouts':[{'id':'sig','versao':'1','formato_id':'fmt_'+familia,'minimo_pontos':2,
            'marcadores':[{'id':f'm{n}','texto':t}for n,t in enumerate(marcadores)]}],
        'administradoras':[{'administradora_id':'adm','identificadores':[{'id':'adm','rotulo':'Administradora','valor':'ADM-LAB'}]}],
        'condominios':[{'condominio_id':'cond_'+familia,'identificadores':[{'id':'cond','rotulo':'Codigo Condominio','valor':'9999'}]}]})
    class Assinaturas:
        def carregar(self):return assinatura
    class Fontes:
        def ler(self,fonte):return blob
    reconhecimento=ReconhecerDocumento(Repo(),Assinaturas()).executar(SondadorLocal().sondar(blob,arquivo_id=fonte.arquivo_id),data_ref=date(2026,10,21))
    assert reconhecimento.pronto_para_proxima_etapa
    leitura=LerDocumento(Repo(),Fontes(),Assinaturas()).executar(fonte,reconhecimento,processamento_id='exec_real_fixture')
    assert len(leitura.lote.unidades)==(1 if familia=='habita'else 2)
    # Sem aprovação vigente, o mesmo leitor não pode reutilizar o reconhecimento anterior.
    dados['formatos'][i].update(status='rascunho',aprovacao=None)
    with pytest.raises(ErroLeitura,match='CATALOGO_DIFERE_DO_RECONHECIMENTO'):
        LerDocumento(Repo(),Fontes(),Assinaturas()).executar(fonte,reconhecimento,processamento_id='exec_real_fixture')
