from datetime import date

import pytest
from pydantic import ValidationError

from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.canonical import Documento, EvidenciaDocumento, LoteCanonico, Pessoa, RessalvaLeitura
from conversor.domain.synthetic_processing import ProjecaoProcessamentoSintetico
from conversor.domain.billing_rules import hash_modelo
from conversor.application.ports import ErroAplicacao
from conversor.readers.contracts import FonteProtegida
from conversor.readers.operational import RegistroLeitores
from conversor.readers.text_support import ContextoLeitura
from conversor.readers.habita_point_coverage import conferir_apontamentos_habita
from tests.phase3.test_habita_point_coverage import pdf_campo
from tests.synthetic_processing.conftest import NAMESPACE
from tests.synthetic_processing.test_tree_conditions import composicao, rodar


def test_modos_a_b_coexistencia_uma_cadastral_por_unidade_sem_xlsx(montar, origem, tmp_path):
    c = montar(specs=[{'dias': 31}, {'dias': 30}, {'composicao': composicao(origem, '0.01')}])
    a = rodar(c)
    b = c.servico.executar(c.s.model_copy(update={'modo_cadastro': 'B'}), c.e)
    assert a.boletos_divida == b.boletos_divida == ('boleto_0',)
    assert not a.candidatos_cadastrais
    assert len(b.candidatos_cadastrais) == 1
    cad = b.candidatos_cadastrais[0]
    assert cad.unidade_id == c.e.lote.unidades[0].id and cad.divida is None
    assert cad.boletos_nao_elegiveis == ('boleto_1', 'boleto_2')
    assert not b.retencoes_cadastrais
    assert a.relatorio_motor == b.relatorio_motor and a.hash_relatorio_motor == b.hash_relatorio_motor
    assert a.hash_auditoria != b.hash_auditoria
    assert not b.autoriza_cobranca and not b.permite_exportacao_operacional
    assert not list(tmp_path.rglob('*.xlsx'))


@pytest.mark.parametrize('dias', [31, 30])
def test_so_cotas_elegiveis_ou_so_nao_elegiveis(montar, dias):
    c = montar(specs=[{'dias': dias}], modo='B')
    r = rodar(c)
    assert bool(r.boletos_divida) == (dias == 31)
    assert bool(r.candidatos_cadastrais) == (dias == 30)


def test_unidade_somente_no_cadastro_complementar_nao_e_projetada(montar, unidade, pessoa):
    c = montar(modo='B', specs=[{'dias': 30}])
    extra = unidade.model_copy(update={'id': 'unidade_extra', 'chave_normalizada': 'somente_cadastro'})
    p = pessoa.model_copy(update={'id': 'titular_extra', 'unidade_id': extra.id})
    lote = LoteCanonico.model_validate(c.e.lote.model_dump() | {
        'unidades': (*c.e.lote.unidades, extra), 'pessoas': (*c.e.lote.pessoas, p)})
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': lote})
    r = rodar(c)
    assert {x.unidade_id for x in r.candidatos_cadastrais} == {unidade.id}


@pytest.mark.parametrize('modo', ['A', 'B'])
@pytest.mark.parametrize('tipo,valor', [('cpf', '123'), ('cnpj', '00000000000000')])
def test_documento_invalido_alerta_sem_bloquear_cotas_ou_cadastro(montar, pessoa, tipo, valor, modo):
    c = montar(specs=[{'dias': 31}, {'dias': 30}], modo=modo)
    p = Pessoa.model_validate(pessoa.model_dump() | {'documento': Documento(tipo=tipo, valor=valor)})
    lote = LoteCanonico.model_validate(c.e.lote.model_dump() | {'pessoas': (p,)})
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': lote})
    antes = hash_modelo(c.e)
    r = rodar(c)
    assert [d.situacao for d in r.relatorio_motor.boletos] == ['elegivel_na_simulacao', 'excluido']
    assert r.boletos_divida == ('boleto_0',)
    assert len(r.candidatos_cadastrais) == (1 if modo == 'B' else 0)
    codigos = {o.codigo for o in r.relatorio_motor.ocorrencias_anteriores}
    assert 'DOCUMENTO_INVALIDO' in codigos and 'DOCUMENTO_INVALIDO_REQUER_REVISAO_43B1' not in codigos
    assert hash_modelo(c.e) == antes and c.e.lote.pessoas[0].documento.valor == valor


def test_documento_ausente_permanece_alerta_sem_bloquear(montar):
    c = montar()
    r = rodar(c)
    assert r.boletos_divida == ('boleto_0',)
    assert any(o.codigo == 'DOCUMENTO_AUSENTE' and not o.bloqueante for o in r.relatorio_motor.ocorrencias_anteriores)


@pytest.mark.parametrize('tipo,valor', [('cpf', '00000000191'), ('cnpj', '00000001000136')])
def test_cpf_cnpj_validos_preservam_tipo_e_zeros(montar, pessoa, tipo, valor):
    c = montar()
    p = Pessoa.model_validate(pessoa.model_dump() | {'documento': Documento(tipo=tipo, valor=valor)})
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': LoteCanonico.model_validate(
        c.e.lote.model_dump() | {'pessoas': (p,)})})
    assert rodar(c).boletos_divida == ('boleto_0',)
    assert c.e.lote.pessoas[0].documento.valor == valor


def test_documentos_validos_conflitantes_bloqueiam_identidade_e_cadastro(montar, pessoa, origem):
    c = montar(specs=[{'dias': 31}, {'dias': 30}], modo='B')
    docs = tuple(EvidenciaDocumento(documento=Documento(tipo=t, valor=v), origem=origem, titular_id=pessoa.id)
                 for t, v in [('cpf', '00000000191'), ('cnpj', '00000001000136')])
    p = Pessoa.model_validate(pessoa.model_dump() | {'evidencias_documentais': docs})
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': LoteCanonico.model_validate(
        c.e.lote.model_dump() | {'pessoas': (p,)})})
    r = rodar(c)
    assert all(d.situacao == 'bloqueado' for d in r.relatorio_motor.boletos)
    assert not r.candidatos_cadastrais
    assert any(o.codigo == 'DOCUMENTOS_CONFLITANTES' and len(o.evidencias_documentais) == 2
               for o in r.relatorio_motor.ocorrencias_anteriores)


@pytest.mark.parametrize('caso', ['sem_titular', 'nome_vazio', 'dois_titulares'])
def test_identidade_obrigatoria_ausente_ou_ambigua_retem_unidade(montar, pessoa, caso):
    c = montar(modo='B')
    pessoas = {'sem_titular': (), 'nome_vazio': (pessoa.model_copy(update={'nome': ''}),),
               'dois_titulares': (pessoa, pessoa.model_copy(update={'id': 'titular_outro'}))}[caso]
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': LoteCanonico.model_validate(
        c.e.lote.model_dump() | {'pessoas': pessoas})})
    r = rodar(c)
    assert not r.boletos_divida and not r.candidatos_cadastrais
    assert r.relatorio_motor.boletos[0].situacao == 'bloqueado'


def test_subtotal_critico_habita_preservado_sem_cadastro_alternativo(montar, origem):
    c = montar(specs=[{'dias': 31}, {'dias': 30}], modo='B')
    ressalva = RessalvaLeitura(codigo='SUBTOTAL_BLOCO_DIVERGENTE', gravidade='critico',
                              origens=(origem,), valores_originais=('evidencia_inventada',))
    c.e = EntradaSimulacao.model_validate(c.e.model_dump() | {'lote': LoteCanonico.model_validate(
        c.e.lote.model_dump() | {'ressalvas': (ressalva,)})})
    r = rodar(c)
    assert not r.boletos_divida and not r.candidatos_cadastrais
    assert r.relatorio_motor.ressalvas_origem == (ressalva,)
    assert all(d.situacao == 'bloqueado' for d in r.relatorio_motor.boletos)


@pytest.mark.parametrize('modo', [None, '', 'C', True])
def test_modo_obrigatorio_sem_default_e_sem_valores_ambiguos(montar, modo):
    c = montar()
    with pytest.raises(ErroAplicacao, match='CONTRATO_DE_PROCESSAMENTO_SINTETICO_INVALIDO'):
        c.servico.executar(c.s.model_copy(update={'modo_cadastro': modo}), c.e)


def test_contrato_saida_nao_admite_autorizacao_operacional(montar):
    dados = rodar(montar()).model_dump()
    for campo in ['autoriza_cobranca', 'permite_exportacao_operacional']:
        with pytest.raises(ValidationError):
            ProjecaoProcessamentoSintetico.model_validate(dados | {campo: True})


def ler_pdf_sintetico(blob):
    from hashlib import sha256
    ctx = ContextoLeitura('cond_sintetico', 'adm_sintetica', NAMESPACE, 'pdf_inventado_43b1',
                         '9999', leitor_versao='habita_composicao_real_v1@1')
    class Fontes:
        def ler(self, fonte):return blob
    class Contextos:
        def resolver(self, fonte, **kwargs):return ctx
    lote = RegistroLeitores(Fontes(), Contextos()).obter('habita_composicao_real_v1', '1').ler(
        FonteProtegida(arquivo_id=ctx.arquivo_id, sha256=sha256(blob).hexdigest()),
        formato_id=ctx.formato_id, condominio_id=ctx.condominio_id)
    return ctx, lote


@pytest.mark.parametrize('ancora,ap,situacao', [(True, None, 'elegivel_na_simulacao'),
                                              (True, 'A', 'excluido'), (True, 'AJ', 'excluido'),
                                              (True, 'J', 'excluido'), (False, None, 'bloqueado')])
def test_pdf_inventado_campo_legenda_cobertura_e_motor_existente(montar, ancora, ap, situacao):
    blob = pdf_campo(ap, sem_ancora=not ancora, continuar=True)
    ctx, lote = ler_pdf_sintetico(blob)
    campo = conferir_apontamentos_habita(blob, contexto=ctx, lote=lote)
    # Provedor de evidências exclusivamente do teste sintético. Não é atesto real.
    covers = tuple(CoberturaApontamentos(boleto_id=x.boleto_id, namespace=x.namespace, origens=x.origens)
                   for x in campo.campos if x.estado != 'inconclusivo')
    c = montar(lote=lote, coberturas=covers, data_ref=date(2026, 11, 1),
               ocorrencias=campo.ocorrencias_revisao(processamento_id='teste_43b1'))
    r = rodar(c)
    assert r.relatorio_motor.boletos[0].situacao == situacao
    assert len(r.relatorio_motor.boletos) == 1
    assert len(lote.boletos[0].composicao.itens) == 2
    assert lote.boletos[0].competencia is None
    if ap is None:
        assert not lote.boletos[0].apontamentos  # A/AJ/J da descrição/legenda não viram códigos.


@pytest.mark.parametrize('campo', ['vencimento', 'composicao', 'origens'])
def test_campo_canonico_obrigatorio_invalido_rejeitado_antes_do_motor(montar, campo):
    c = montar()
    b = c.e.lote.boletos[0].model_copy(update={campo: () if campo == 'origens' else None})
    lote = c.e.lote.model_copy(update={'boletos': (b,)})
    entrada = c.e.model_copy(update={'lote': lote})
    with pytest.raises(ErroAplicacao, match='CONTRATO_DE_PROCESSAMENTO_SINTETICO_INVALIDO'):
        c.servico.executar(c.s, entrada)


@pytest.mark.parametrize('adulteracao', ['hash', 'divida_inelegivel', 'cadastro_duplicado', 'modo_a_com_cadastro'])
def test_projecao_nao_aceita_divida_ou_cadastro_incoerente(montar, adulteracao):
    c = montar(specs=[{'dias': 31}, {'dias': 30}], modo='B')
    d = rodar(c).model_dump()
    if adulteracao == 'hash':d['hash_relatorio_motor'] = 'f' * 64
    if adulteracao == 'divida_inelegivel':d['boletos_divida'] = ('boleto_1',)
    if adulteracao == 'cadastro_duplicado':d['candidatos_cadastrais'] *= 2
    if adulteracao == 'modo_a_com_cadastro':d['modo_cadastro'] = 'A'
    with pytest.raises(ValidationError):
        ProjecaoProcessamentoSintetico.model_validate(d)


def test_execucao_nao_emite_eventos_novos_de_aprovacao_ou_ativacao(montar):
    c = montar(specs=[{'dias': 31}, {'dias': 30}], modo='B')
    antes = c.repo.carregar()
    rodar(c)
    c.servico.executar(c.s.model_copy(update={'modo_cadastro': 'A'}), c.e)
    assert c.repo.carregar() == antes
    assert [e.acao for e in antes.acervo.eventos] == ['criar', 'submeter', 'aprovar', 'ativar']
    assert antes.acervo.ambiente == 'sintetico'
    assert all(r.conteudo.natureza == 'sintetico' for r in antes.acervo.registros)
