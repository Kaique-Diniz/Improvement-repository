from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from conversor.domain.billing_rules import PlanoCobranca, hash_modelo
from conversor.domain.canonical import LoteCanonico, Ocorrencia, RessalvaLeitura
from conversor.domain.synthetic_processing import SolicitacaoProcessamentoSintetico
from conversor.application.ports import ErroAplicacao


def composicao(origem, *valores):
    return {'total_original': format(sum(map(Decimal, valores)), '.2f'),
            'itens': [{'codigo': 'item_' + str(i), 'valor': v, 'origem': origem}
                      for i, v in enumerate(valores)]}


def rodar(c):
    return c.servico.executar(c.s, c.e)


@pytest.mark.parametrize('dias,situacao', [(31, 'elegivel_na_simulacao'), (30, 'excluido'),
                                          (29, 'excluido'), (0, 'excluido'), (-5, 'excluido')])
def test_prazo_estrito_com_ramo_complementar_auditado(montar, dias, situacao):
    c = montar(specs=[{'dias': dias}])
    r = rodar(c)
    d = r.relatorio_motor.boletos[0]
    assert d.situacao == situacao
    assert len(d.avaliacoes) == 6
    ids = {a.regra_id for a in d.avaliacoes if a.passo.resultado == 'verdadeiro'}
    assert ids == ({'tree_prazo_30'} if dias > 30 else {'tree_prazo_30_nao_atingido'})


@pytest.mark.parametrize('encargos', [False, True])
@pytest.mark.parametrize('dias', [-5, 30, 31])
def test_centavo_integral_com_e_sem_encargos_independe_do_vencimento(montar, origem, encargos, dias):
    spec = {'dias': dias, 'composicao': composicao(origem, '0.01')}
    if encargos:
        spec |= {'multa': '2.00', 'juros': '3.00', 'correcao': '4.00'}
    c = montar(specs=[spec])
    antes = c.e.model_dump_json()
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'excluido' and 'tree_centavo' in d.regras_decisivas
    assert c.e.model_dump_json() == antes
    a = next(a for a in d.avaliacoes if a.regra_id == 'tree_centavo')
    assert a.passo.observados[0].valor == '0.01'


def test_componente_centavo_em_cota_maior_nao_exclui(montar, origem):
    c = montar(specs=[{'composicao': composicao(origem, '0.01', '149.99')}])
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'elegivel_na_simulacao'
    assert next(a for a in d.avaliacoes if a.regra_id == 'tree_centavo').passo.resultado == 'falso'


@pytest.mark.parametrize('ap,id_', [('A', 'tree_apontamento_a'), ('AJ', 'tree_apontamento_aj'), ('J', 'tree_apontamento_j')])
@pytest.mark.parametrize('dias', [-5, 30, 31])
def test_codigo_exato_exclui_so_cota(montar, ap, id_, dias):
    c = montar(specs=[{'ap': ap, 'dias': dias}, {'dias': 31}])
    ds = {d.boleto_id: d for d in rodar(c).relatorio_motor.boletos}
    assert ds['boleto_0'].situacao == 'excluido' and id_ in ds['boleto_0'].regras_decisivas
    assert ds['boleto_1'].situacao == 'elegivel_na_simulacao'


@pytest.mark.parametrize('ap', ['A', 'AJ', 'J'])
def test_centavo_e_apontamento_preservam_ambas_justificativas(montar, origem, ap):
    c = montar(specs=[{'composicao': composicao(origem, '0.01'), 'ap': ap}])
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'excluido'
    assert set(d.regras_decisivas) == {'tree_centavo', 'tree_apontamento_' + ap.lower()}
    assert next(a for a in d.avaliacoes if a.regra_id == 'tree_prazo_30').passo.resultado == 'falso'


def test_guarda_impede_inclusao_mesmo_com_prioridade_sintetica_maior(montar):
    def editar(dados):
        next(r for r in dados['regras'] if r['id'] == 'tree_prazo_30')['prioridade'] = 999
    c = montar(specs=[{'ap': 'AJ'}], editar_plano=editar)
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'excluido'
    assert next(a for a in d.avaliacoes if a.regra_id == 'tree_prazo_30').passo.resultado == 'falso'


@pytest.mark.parametrize('cobertura,situacao', [(True, 'elegivel_na_simulacao'), (False, 'pendente_revisao')])
def test_campo_vazio_comprovado_difere_de_ausencia_de_evidencia(montar, cobertura, situacao):
    c = montar(specs=[{'cobertura': cobertura}], modo='B')
    r = rodar(c)
    assert r.relatorio_motor.boletos[0].situacao == situacao
    assert not r.candidatos_cadastrais
    assert bool(r.retencoes_cadastrais) == (not cobertura)


def test_namespace_errado_nao_e_evidencia_da_regua(montar):
    c = montar(specs=[{'ap': 'A', 'namespace': 'outro_formato', 'cobertura': False}])
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'pendente_revisao'
    assert all(a.passo.resultado == 'indeterminado' for a in d.avaliacoes if a.regra_id.startswith('tree_apontamento_'))


@pytest.mark.parametrize('codigo', ['AA', 'AJJ', 'JURIDICO', 'A '])
def test_codigo_desconhecido_sem_cobertura_nao_vira_coincidencia_parcial(montar, codigo):
    c = montar(specs=[{'ap': codigo, 'cobertura': False}])
    d = rodar(c).relatorio_motor.boletos[0]
    assert d.situacao == 'pendente_revisao'
    assert not any(a.passo.resultado == 'verdadeiro' for a in d.avaliacoes if a.regra_id.startswith('tree_apontamento_'))


@pytest.mark.parametrize('codigo,escopo', [('SUBTOTAL_BLOCO_DIVERGENTE', 'arquivo'),
                                         ('TITULARIDADE_FL_NAO_CONFIRMADA', 'registro'),
                                         ('APONTAMENTO_LEITURA_INCONCLUSIVA', 'registro')])
def test_critico_prevalece_sobre_condicoes_financeiras(montar, origem, unidade, codigo, escopo):
    o = Ocorrencia(id='critico_sintetico', processamento_id='historico_sintetico', codigo=codigo,
                  gravidade='critico', escopo=escopo, registro_id=unidade.id if escopo == 'registro' else None,
                  origem=origem)
    c = montar(ocorrencias=(o,), modo='B')
    r = rodar(c)
    assert r.relatorio_motor.boletos[0].situacao == 'bloqueado'
    assert o in r.relatorio_motor.ocorrencias_anteriores
    assert not r.boletos_divida and not r.candidatos_cadastrais
    assert r.retencoes_cadastrais


@pytest.mark.parametrize('valor', [None, '', '21/10/2026', '2026-02-30', True, 123])
def test_referencia_ausente_ou_invalida_rejeitada_sem_default(montar, valor):
    c = montar()
    s = c.s.model_copy(update={'data_ref': valor})
    with pytest.raises(ErroAplicacao, match='CONTRATO_DE_PROCESSAMENTO_SINTETICO_INVALIDO'):
        c.servico.executar(s, c.e)
    dados = c.s.model_dump()
    dados.pop('data_ref')
    with pytest.raises(ValidationError):
        SolicitacaoProcessamentoSintetico.model_validate(dados)


def test_data_ref_auditavel_diferente_da_vigencia_e_sem_hoje(montar):
    c = montar(specs=[{'dias': 30}])
    a = rodar(c)
    b = c.servico.executar(c.s.model_copy(update={'data_ref': date(2026, 10, 22)}), c.e)
    assert a.relatorio_motor.boletos[0].situacao == 'excluido'
    assert b.relatorio_motor.boletos[0].situacao == 'elegivel_na_simulacao'
    assert a.relatorio_motor.solicitacao.data_ref != c.p.vigente_de
    assert a.hash_auditoria != b.hash_auditoria


def test_rastreabilidade_e_determinismo_sem_modificar_entrada(montar):
    c = montar(specs=[{'ap': 'AJ'}, {'dias': 30}, {'dias': 31}], modo='B')
    antes = hash_modelo(c.e)
    a, b = rodar(c), rodar(c)
    assert a == b and a.hash_auditoria == b.hash_auditoria
    assert hash_modelo(c.e) == antes
    assert a.relatorio_motor.solicitacao.plano_hash == hash_modelo(c.p)
    assert a.hash_relatorio_motor == hash_modelo(a.relatorio_motor)
    for d in a.relatorio_motor.boletos:
        assert d.origens and d.regras_decisivas
        assert all(r.fonte_regra and r.plano_versao == c.p.versao and r.passo.motivo_codigo for r in d.avaliacoes)


@pytest.mark.parametrize('estado', ['rascunho', 'aguardando_aprovacao', 'aprovado', 'revogado'])
def test_plano_sem_estado_administrativo_necessario_nao_executa(montar, estado):
    c = montar(estado=estado)
    with pytest.raises(ErroAplicacao, match='PLANO_NAO_ATIVO_OU_REVOGADO'):
        rodar(c)


def test_ambiente_privado_recusado_antes_de_qualquer_acesso(montar):
    c = montar()
    def proibido():
        pytest.fail('Nao deveria consultar plano privado')
    c.repo.carregar = proibido
    with pytest.raises(ErroAplicacao, match='CONTRATO_DE_PROCESSAMENTO_SINTETICO_INVALIDO'):
        c.servico.executar(c.s.model_copy(update={'ambiente': 'privado'}), c.e)


def test_hash_de_plano_alterado_nao_e_aceito(montar):
    c = montar()
    with pytest.raises(ErroAplicacao, match='VERSAO_OU_HASH_SOLICITADO_DIVERGENTE'):
        c.servico.executar(c.s.model_copy(update={'plano_hash': 'f' * 64}), c.e)


def test_float_na_condicao_monetaria_e_no_total_canonico_rejeitado(montar):
    c = montar()
    dados = c.p.model_dump()
    dados['regras'][0]['quando']['valor'] = 0.01
    with pytest.raises(ValidationError):
        PlanoCobranca.model_validate(dados)
    dados = c.e.lote.model_dump()
    dados['boletos'][0]['composicao']['total_original'] = 100.0
    with pytest.raises(ValidationError, match='DINHEIRO_EXIGE_DECIMAL_OU_TEXTO'):
        LoteCanonico.model_validate(dados)
