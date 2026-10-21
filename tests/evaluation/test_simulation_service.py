from datetime import date
from hashlib import sha256
import json

import pytest

from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.application.billing_evaluation import SimularCobranca
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_evaluation import EntradaSimulacao, FatoEvidenciado, SolicitacaoSimulacao
from conversor.domain.billing_rules import EstadoPlanos, hash_modelo
from conversor.domain.canonical import (Boleto,LoteCanonico,Ocorrencia,Origem,Pessoa,RessalvaLeitura,
                                       Documento,EvidenciaDocumento,Unidade)
from tests.evaluation.conftest import regra,fato
from tests.rules.test_plan_repository import executar,arquivo_atual


def alterar(modelo,**campos):return type(modelo).model_validate(modelo.model_dump()|campos)


@pytest.mark.parametrize('escopo,registro',[('arquivo',None),('processamento',None),('registro','unidade_a'),
    ('registro','pessoa_sintetica'),('registro','boleto_a'),('registro','nao_localizado')])
def test_bloqueio_critico_nao_e_anulado_por_inclusao_ou_exclusao(preparar,origem,escopo,registro):
    oc=Ocorrencia(id='critico_anterior',processamento_id='leitura_anterior',codigo='PENDENCIA_CRITICA',
        gravidade='critico',escopo=escopo,registro_id=registro,origem=origem)
    s,r,e,p=preparar(ocorrencias=(oc,),regras=(regra('permitir',prioridade=999),
        regra('excluir_unidade',acao='excluir',alvo='unidade',prioridade=1)))
    rel=s.executar(r,e);d=rel.boletos[0]
    assert d.situacao=='bloqueado'and d.motivo_codigo=='BLOQUEIO_CRITICO_PRESERVADO'
    assert oc in d.ocorrencias_preservadas and oc in rel.ocorrencias_anteriores
    assert d.motivo_regras=='EXCLUSAO_TERMINAL_DA_UNIDADE'
    assert not rel.autoriza_cobranca and not rel.permite_exportacao_operacional


@pytest.mark.parametrize('gravidade',['informativo','alerta'])
def test_alerta_nao_bloqueante_nao_vira_bloqueio_financeiro(preparar,origem,gravidade):
    oc=Ocorrencia(id='alerta',processamento_id='anterior',codigo='DOCUMENTO_AUSENTE',gravidade=gravidade,
        escopo='registro',registro_id='unidade_a',origem=origem)
    s,r,e,p=preparar(ocorrencias=(oc,))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='elegivel_na_simulacao'and oc in d.ocorrencias_preservadas


def test_subtotal_divergente_permanece_bloqueio_de_lote(preparar,unidade,boleto,origem):
    ressalva=RessalvaLeitura(codigo='SUBTOTAL_BLOCO_DIVERGENTE',gravidade='critico',origens=(origem,),
        valores_originais=('ROTULO SINTETICO','SEM VALORES REAIS'))
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,),ressalvas=(ressalva,))
    s,r,e,p=preparar(lote=lote)
    rel=s.executar(r,e)
    assert rel.boletos[0].situacao=='bloqueado'and rel.ressalvas_origem==(ressalva,)
    assert any(o.codigo=='SUBTOTAL_BLOCO_DIVERGENTE'for o in rel.boletos[0].ocorrencias_preservadas)


def test_conflitos_documentais_no_canonico_sao_reverificados(preparar,unidade,boleto,pessoa,origem):
    fontes=tuple(EvidenciaDocumento(documento=Documento(tipo='cpf',valor=v),origem=origem,titular_id=pessoa.id)
                 for v in ('00000000191','00000000272'))
    p=alterar(pessoa,evidencias_documentais=fontes)
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,),pessoas=(p,))
    s,r,e,plano=preparar(lote=lote)
    rel=s.executar(r,e);d=rel.boletos[0]
    assert d.situacao=='bloqueado'
    ocorrencia=next(o for o in d.ocorrencias_preservadas if o.codigo=='DOCUMENTOS_CONFLITANTES')
    assert ocorrencia.evidencias_documentais==fontes
    assert e.lote.pessoas[0].evidencias_documentais==fontes


@pytest.mark.parametrize('documento',[None,Documento(tipo='cpf',valor='00000000191'),Documento(tipo='cnpj',valor='00000000000191')])
def test_documento_ausente_cpf_cnpj_nao_e_substituido(preparar,pessoa,unidade,boleto,documento):
    p=alterar(pessoa,documento=documento)
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,),pessoas=(p,))
    s,r,e,plano=preparar(lote=lote)
    rel=s.executar(r,e)
    assert rel.boletos[0].situacao=='elegivel_na_simulacao'
    assert e.lote.pessoas[0].documento==documento


def test_valores_composicao_e_competencia_ausente_sao_preservados(preparar,boleto,unidade):
    b=alterar(boleto,competencia=None,emissao_original='010126')
    lote=LoteCanonico(unidades=(unidade,),boletos=(b,))
    s,r,e,p=preparar(lote=lote);antes=e.model_dump_json()
    s.executar(r,e)
    assert e.model_dump_json()==antes and e.lote.boletos[0].competencia is None
    assert e.lote.boletos[0].composicao==boleto.composicao
    assert (e.lote.boletos[0].multa,e.lote.boletos[0].juros,e.lote.boletos[0].saldo_acumulado)==(
        boleto.multa,boleto.juros,boleto.saldo_acumulado)


@pytest.mark.parametrize('mudanca,codigo', [({'plano_id':'outro'},'PLANO_SOLICITADO_INDISPONIVEL'),
    ({'plano_versao':'9.0.0'},'VERSAO_OU_HASH_SOLICITADO_DIVERGENTE'),
    ({'plano_hash':'1'*64},'VERSAO_OU_HASH_SOLICITADO_DIVERGENTE'),
    ({'condominio_id':'cond_outro'},'PLANO_DE_OUTRO_AMBIENTE_OU_CONDOMINIO'),
    ({'ambiente':'privado'},'PLANO_DE_OUTRO_AMBIENTE_OU_CONDOMINIO'),
    ({'data_ref':'2027-01-01'},'DATA_REF_FORA_DA_VIGENCIA_DO_PLANO'),
    ({'data_ref':'2025-12-31'},'DATA_REF_FORA_DA_VIGENCIA_DO_PLANO')])
def test_pin_e_vigencia_sem_fallback(preparar,mudanca,codigo):
    s,r,e,p=preparar()
    with pytest.raises(ErroAplicacao,match=codigo):s.executar(alterar(r,**mudanca),e)


def test_plano_aprovado_ainda_inativo_nao_e_avaliado(preparar):
    s,r,e,p=preparar(ativar=False)
    with pytest.raises(ErroAplicacao,match='PLANO_NAO_ATIVO_OU_REVOGADO'):s.executar(r,e)


def test_plano_revogado_recusado(preparar,gestor):
    s,r,e,p=preparar();executar(s.repositorio,p,gestor,'revogar')
    with pytest.raises(ErroAplicacao,match='PLANO_NAO_ATIVO_OU_REVOGADO'):s.executar(r,e)


def test_adulteracao_do_plano_assinado_nao_e_avaliada(preparar):
    s,r,e,p=preparar();path=arquivo_atual(s.repositorio);dados=json.loads(path.read_text())
    dados['registros'][0]['conteudo']['regras'][0]['acao']='excluir';path.write_text(json.dumps(dados))
    with pytest.raises(ErroAplicacao,match='SNAPSHOT_DE_PLANOS_ADULTERADO'):s.executar(r,e)


def test_estado_ativo_forjado_nao_substitui_autoridade(preparar):
    s,r,e,p=preparar(ativar=False);real=s.repositorio;estado=real.carregar()
    falso=estado.model_copy(update={'acervo':estado.acervo.model_copy(update={
        'registros':(estado.acervo.registros[0].model_copy(update={'estado':'ativo'}),)})})
    class FonteNaoConfiavel:
        def carregar(self):return falso
    serv=SimularCobranca(FonteNaoConfiavel(),VerificadorPlanosJSON(real))
    with pytest.raises(ErroAplicacao,match='ESTADO_NAO_CORRESPONDE_A_AUTORIDADE_ATUAL'):serv.executar(r,e)


def test_versao_ativa_antiga_nao_pode_ser_reproduzida_como_atual_apos_revogacao(preparar,gestor):
    s,r,e,p=preparar();real=s.repositorio;antigo=real.carregar();executar(real,p,gestor,'revogar')
    class CacheAntigo:
        def carregar(self):return antigo
    serv=SimularCobranca(CacheAntigo(),VerificadorPlanosJSON(real))
    with pytest.raises(ErroAplicacao,match='ESTADO_NAO_CORRESPONDE_A_AUTORIDADE_ATUAL'):serv.executar(r,e)


def test_revogacao_durante_avaliacao_invalida_o_relatorio(preparar,gestor,monkeypatch):
    import conversor.application.billing_evaluation as modulo
    s,r,e,p=preparar();original=modulo.avaliar_regras;alterou=False
    def intercalar(*args,**kwargs):
        nonlocal alterou
        resultado=original(*args,**kwargs)
        if not alterou:alterou=True;executar(s.repositorio,p,gestor,'revogar')
        return resultado
    monkeypatch.setattr(modulo,'avaliar_regras',intercalar)
    with pytest.raises(ErroAplicacao,match='ESTADO_NAO_CORRESPONDE_A_AUTORIDADE_ATUAL'):s.executar(r,e)


def test_isolamento_do_lote_e_fatos(preparar,unidade,boleto):
    outra=alterar(unidade,condominio_id='cond_outro');b=alterar(boleto,condominio_id='cond_outro')
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(outra,),boletos=(b,)))
    with pytest.raises(ErroAplicacao,match='LOTE_DE_OUTRO_CONDOMINIO_OU_VAZIO'):s.executar(r,e)


@pytest.mark.parametrize('mutacao,codigo',[({'condominio_id':'cond_outro'},'FATO_DE_OUTRO_CONDOMINIO_OU_UNIDADE'),
    ({'unidade_id':'outra'},'FATO_DE_OUTRO_CONDOMINIO_OU_UNIDADE'),
    ({'fato_id':'nao_declarado'},'FATO_NAO_DECLARADO_OU_TIPO_INVALIDO'),
    ({'valor':{'tipo':'inteiro','valor':1}},'FATO_NAO_DECLARADO_OU_TIPO_INVALIDO'),
    ({'boleto_id':'boleto_a'},'ESCOPO_DO_FATO_INVALIDO')])
def test_fatos_incompativeis_recusados_sem_inferencias(preparar,mutacao,codigo):
    f=alterar(fato(),**mutacao)
    s,r,e,p=preparar(definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),fatos=(f,))
    with pytest.raises(ErroAplicacao,match=codigo):s.executar(r,e)


def test_origens_com_hashes_conflitantes_recusadas(preparar,origem):
    f=fato();f=alterar(f,origens=(alterar(origem,sha256='1'*64),))
    s,r,e,p=preparar(definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),fatos=(f,))
    with pytest.raises(ErroAplicacao,match='HASHES_DE_ORIGEM_CONFLITANTES'):s.executar(r,e)


def test_reprodutibilidade_e_ausencia_de_logs(preparar,capsys):
    s,r,e,p=preparar();a=s.executar(r,e);b=s.executar(r,e)
    assert a.model_dump_json()==b.model_dump_json()
    assert a.prova_plano.hash_estado==hash_modelo(s.repositorio.carregar())
    assert a.solicitacao.plano_hash==hash_modelo(p)
    assert capsys.readouterr().out==''and capsys.readouterr().err==''


def test_ordenacao_de_colecoes_nao_muda_relatorio(preparar,unidade,boleto,pessoa):
    b2=alterar(boleto,id='boleto_b',identificador='sintetico002')
    lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,b2),pessoas=(pessoa,))
    s,r,e,p=preparar(lote=lote)
    invertido=alterar(e,lote=alterar(lote,boletos=tuple(reversed(lote.boletos))))
    assert s.executar(r,e).model_dump_json()==s.executar(r,invertido).model_dump_json()


def test_rastreabilidade_de_todas_as_regras_e_fontes(preparar):
    s,r,e,p=preparar(regras=(regra('incluir'),regra('falsa',acao='excluir',prioridade=1,
        quando={'tipo':'valor_original','operador':'eq','valor':'999.00'}),regra('aviso',acao='alertar')))
    rel=s.executar(r,e);d=rel.boletos[0]
    assert {a.regra_id for a in d.avaliacoes}=={'incluir','falsa','aviso'}
    assert all(a.plano_versao==p.versao and a.fonte_regra in p.fontes for a in d.avaliacoes)
    assert all(a.passo.origens and a.passo.caminho=='raiz' for a in d.avaliacoes)
    assert d.origens and rel.hash_entrada and rel.prova_plano.aprovacao_hash
    assert rel.modo=='somente_simulacao'and not hasattr(d,'acao')


@pytest.mark.parametrize('estado',['rascunho','aguardando_aprovacao'])
def test_planos_ainda_nao_aprovados_nao_geram_avaliacao(preparar,estado):
    s,r,e,p=preparar(estado=estado)
    with pytest.raises(ErroAplicacao,match='PLANO_NAO_ATIVO_OU_REVOGADO'):s.executar(r,e)


def test_fatos_de_boleto_sao_isolados_por_identidade(preparar,unidade,boleto):
    b2=alterar(boleto,id='boleto_b',identificador='sintetico002')
    c={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(unidade,),boletos=(boleto,b2)),
        definicoes=({'id':'juridico','tipo':'booleano','escopo':'boleto'},),regras=(regra(quando=c),),
        fatos=(fato(boleto_id='boleto_a'),fato('f2',boleto_id='boleto_b',valor=False)))
    rel=s.executar(r,e)
    assert [d.situacao for d in rel.boletos]==['elegivel_na_simulacao','pendente_revisao']
    assert rel.boletos[0].avaliacoes[0].passo.fatos_ids==('f1',)
    assert rel.boletos[1].avaliacoes[0].passo.fatos_ids==('f2',)
    assert rel.fatos_recebidos==e.fatos


def test_fatos_de_unidade_e_bloqueios_nao_vazam_para_outra_unidade(preparar,unidade,boleto,origem):
    u2=alterar(unidade,id='unidade_b',unidade_original='0002',chave_normalizada='sintetica_2')
    b2=alterar(boleto,id='boleto_b',identificador='sintetico002',unidade_id=u2.id)
    oc=Ocorrencia(id='crit_unidade_a',processamento_id='anterior',codigo='TITULAR_DIVERGENTE',gravidade='critico',
        escopo='registro',registro_id=unidade.id,origem=origem)
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(unidade,u2),boletos=(boleto,b2)),ocorrencias=(oc,))
    rel=s.executar(r,e)
    assert [d.situacao for d in rel.boletos]==['bloqueado','elegivel_na_simulacao']
    assert not rel.boletos[1].ocorrencias_preservadas


def test_cobertura_sem_fonte_do_boleto_e_recusada(preparar,origem):
    from conversor.domain.billing_evaluation import CoberturaApontamentos
    o=alterar(origem,arquivo_id='outro_arquivo')
    c=CoberturaApontamentos(boleto_id='boleto_a',namespace='sintetico',origens=(o,))
    s,r,e,p=preparar(coberturas=(c,))
    with pytest.raises(ErroAplicacao,match='COBERTURA_SEM_VINCULO_COM_FONTE_DO_BOLETO'):s.executar(r,e)


def test_bloqueio_em_unidade_sem_boletos_e_preservado(preparar,unidade,origem):
    o=Ocorrencia(id='crit',processamento_id='anterior',codigo='TITULAR_DIVERGENTE',gravidade='critico',
        escopo='registro',registro_id=unidade.id,origem=origem)
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(unidade,),boletos=()),ocorrencias=(o,))
    rel=s.executar(r,e)
    assert rel.unidades[0].situacao=='bloqueado'and not rel.boletos


def test_entrada_adulterada_por_model_copy_e_recusada(preparar):
    s,r,e,p=preparar()
    b=e.lote.boletos[0].model_copy(update={'vencimento':None})
    adulterada=e.model_copy(update={'lote':e.lote.model_copy(update={'boletos':(b,)})})
    with pytest.raises(ErroAplicacao,match='CONTRATO_DE_SIMULACAO_INVALIDO'):s.executar(r,adulterada)


def test_fatos_iguais_de_duas_fontes_nao_sao_conflito(preparar):
    c={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(regras=(regra(quando=c),),definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),
        fatos=(fato(),fato('f2')))
    d=s.executar(r,e).boletos[0]
    assert d.situacao=='elegivel_na_simulacao'and d.avaliacoes[0].passo.fatos_ids==('f1','f2')


def test_fatos_com_valores_distintos_nao_usam_prioridade_ou_data_mais_recente(preparar):
    c={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(regras=(regra(quando=c),),definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),
        fatos=(fato(),fato('f2',valor=False,vigente_de='2026-10-01')))
    assert s.executar(r,e).boletos[0].situacao=='pendente_revisao'


def test_fato_comprovado_de_uma_unidade_nao_completa_outra(preparar,unidade,boleto):
    u2=alterar(unidade,id='unidade_b',unidade_original='0002',chave_normalizada='sintetica_2')
    b2=alterar(boleto,id='boleto_b',identificador='sintetico002',unidade_id=u2.id)
    cond={'tipo':'fato','fato_id':'juridico','operador':'eq','valor':{'tipo':'booleano','valor':True}}
    s,r,e,p=preparar(lote=LoteCanonico(unidades=(unidade,u2),boletos=(boleto,b2)),fatos=(fato(),),
        definicoes=({'id':'juridico','tipo':'booleano','escopo':'unidade'},),regras=(regra(quando=cond),))
    assert [d.situacao for d in s.executar(r,e).boletos]==['elegivel_na_simulacao','pendente_revisao']
