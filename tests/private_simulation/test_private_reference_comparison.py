from datetime import datetime

import pytest

from tests.private_simulation.test_private_reproduction import salvar
from tests.private_simulation.test_private_inventory import critico
from conversor.adapters.simulation_reference import ComparadorReferenciaXLSX
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.canonical import Documento, LoteCanonico
from conversor.domain.simulation_comparison import MapeamentoReferencia
from conversor.domain.template import COLUNAS


def comparar(c):
    return c.servico.comparar(id_='comparacao_sintetica', execucao_id='execucao_sintetica', mapeamento=c.mapeamento,
        template=c.template, comparador=ComparadorReferenciaXLSX(), credencial=c.gestor)


def test_comparacao_deterministica_30_colunas_sem_exportacao(laboratorio):
    c = laboratorio()
    salvar(c)
    antes = c.xlsx.read_bytes()
    resultado = comparar(c)
    assert resultado.divergencias == ()
    assert resultado.colunas == COLUNAS and resultado.colunas[2] == 'CPF'
    assert resultado.colunas_nao_avaliadas == COLUNAS[:2] + COLUNAS[24:28]
    assert not resultado.referencia_e_gabarito_absoluto and not resultado.autoriza_cobranca
    assert not resultado.permite_exportacao_operacional
    assert c.xlsx.read_bytes() == antes
    assert c.armazenamento.carregar_comparacao(resultado.id) == resultado
    assert c.servico.reproduzir_comparacao(resultado.id, comparador=ComparadorReferenciaXLSX()) == resultado


@pytest.mark.parametrize('coluna,valor,categoria,codigo', [
    (30, 110.00, 'dados', 'VALOR_ORIGINAL_DIFERE_DA_REFERENCIA_SEM_ATRIBUIR_CAUSA'),
    (30, '100.00', 'formatacao', 'VALOR_MONETARIO_COMO_TEXTO'),
    (30, True, 'dados', 'VALOR_ORIGINAL_DIFERE_DA_REFERENCIA_SEM_ATRIBUIR_CAUSA'),
    (30, '=SUM(1,99)', 'nao_avaliavel', 'FORMULA_NAO_EXECUTADA'),
    (29, datetime(2026, 9, 18), 'dados', 'VENCIMENTO_DIVERGENTE_OU_NAO_VERIFICAVEL'),
    (29, '17/09/2026', 'formatacao', 'REPRESENTACAO_DA_DATA'),
    (29, 46282, 'dados', 'VENCIMENTO_DIVERGENTE_OU_NAO_VERIFICAVEL'),
    (22, 'exemplo@invalid.example', 'dados', 'CAMPO_CADASTRAL_DIVERGENTE'),
    (4, 'Outro Nome Sintético', 'dados', 'CAMPO_CADASTRAL_DIVERGENTE'),
])
def test_distingue_dados_formatacao_e_nao_executa_formulas(laboratorio, coluna, valor, categoria, codigo):
    def alterar(aba):
        aba.cell(2, coluna).value = valor
        if coluna == 29 and isinstance(valor, int):
            aba.cell(2, coluna).number_format = 'General'
    c = laboratorio(modificar_excel=alterar)
    salvar(c)
    resultado = comparar(c)
    assert any(d.categoria == categoria and d.motivo_codigo == codigo and d.coluna == COLUNAS[coluna - 1] for d in resultado.divergencias)
    assert all(d.exige_revisao_humana for d in resultado.divergencias)
    assert c.pacote.entrada.lote.boletos[0].composicao.total_original == 100
    # Células brutas não integram o relatório: apenas hashes e fontes.
    assert 'Outro Nome Sintético' not in resultado.model_dump_json()
    assert 'exemplo@invalid.example' not in resultado.model_dump_json()


def test_divergencia_de_regra_nao_desbloqueia_unidade(laboratorio, origem):
    c = laboratorio(ocorrencias=(critico(origem),))
    execucao = salvar(c)
    resultado = comparar(c)
    assert any(d.categoria == 'regras' for d in resultado.divergencias)
    assert execucao.relatorio.boletos[0].situacao == 'bloqueado'
    assert all(any(o.pagina == 1 for o in d.origens) for d in resultado.divergencias)


@pytest.mark.parametrize('tipo,valor', [('cpf', '00000000191'), ('cnpj', '00000000000191')])
def test_cpf_cnpj_textuais_e_zeros_perdidos(laboratorio, pessoa, unidade, boleto, tipo, valor):
    pessoa = pessoa.model_copy(update={'documento': Documento(tipo=tipo, valor=valor)})
    c = laboratorio(lote=LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,)),
                    modificar_excel=lambda aba: setattr(aba.cell(2, 3), 'value', int(valor)))
    salvar(c)
    resultado = comparar(c)
    codigos = {d.motivo_codigo for d in resultado.divergencias}
    assert {'DOCUMENTO_ARMAZENADO_COMO_NUMERO', 'ZEROS_INICIAIS_PERDIDOS'} <= codigos
    assert all(d.categoria == 'formatacao' for d in resultado.divergencias)
    assert c.pacote.entrada.lote.pessoas[0].documento.valor == valor


def test_documento_valido_conflitante_nao_vira_correcao(laboratorio, pessoa, unidade, boleto):
    pessoa = pessoa.model_copy(update={'documento': Documento(tipo='cpf', valor='00000000191')})
    c = laboratorio(lote=LoteCanonico(unidades=(unidade,), boletos=(boleto,), pessoas=(pessoa,)),
                    modificar_excel=lambda aba: setattr(aba.cell(2, 3), 'value', '00000000272'))
    salvar(c)
    resultado = comparar(c)
    assert any(d.categoria == 'dados' and d.motivo_codigo == 'DOCUMENTO_DIVERGENTE' for d in resultado.divergencias)
    assert c.pacote.entrada.lote.pessoas[0].documento.valor == '00000000191'


def test_referencia_sem_vinculo_nao_e_classificada_por_posicao(laboratorio):
    def acrescentar(aba):
        aba.append([''] * 29 + [50])
    c = laboratorio(modificar_excel=acrescentar)
    salvar(c)
    resultado = comparar(c)
    assert not resultado.cobertura_referencia_completa
    assert any(d.motivo_codigo == 'LINHA_SEM_IDENTIDADE_REVISADA' and d.linha == 3 for d in resultado.divergencias)


def test_boleto_elegivel_ausente_na_referencia_e_divergencia_de_decisao(laboratorio, unidade, boleto, pessoa):
    outro = boleto.model_copy(update={'id': 'boleto_b', 'identificador': 'boleto_sintetico_002'})
    c = laboratorio(lote=LoteCanonico(unidades=(unidade,), boletos=(boleto, outro), pessoas=(pessoa,)))
    salvar(c)
    resultado = comparar(c)
    d = next(d for d in resultado.divergencias if d.motivo_codigo == 'ELEGIVEL_SEM_DIVIDA_DE_REFERENCIA')
    assert d.categoria == 'regras' and d.boletos_ids == ('boleto_b',)


@pytest.mark.parametrize('alteracao', ['hash', 'unidade', 'boleto', 'pessoa', 'linha'])
def test_referencia_e_vinculos_integralmente_conferidos(laboratorio, alteracao):
    c = laboratorio()
    salvar(c)
    dados = c.mapeamento.model_dump(mode='json')
    if alteracao == 'hash':
        dados['referencia_hash'] = '0' * 64
    else:
        chave = {'unidade': 'unidade_id', 'boleto': 'boletos_ids', 'pessoa': 'pessoa_id', 'linha': 'linha'}[alteracao]
        dados['vinculos'][0][chave] = ['inexistente'] if alteracao == 'boleto' else 9 if alteracao == 'linha' else 'inexistente'
    c.mapeamento = MapeamentoReferencia.model_validate(dados)
    with pytest.raises(ErroAplicacao):
        comparar(c)


@pytest.mark.parametrize('alteracao', ['31_colunas', 'cpf_renomeado', 'sem_aba'])
def test_template_incompativel_e_recusado(laboratorio, alteracao):
    def alterar(aba):
        if alteracao == '31_colunas':
            aba.cell(1, 31).value = 'EXTRA'
        elif alteracao == 'cpf_renomeado':
            aba.cell(1, 3).value = 'CPF_CNPJ'
        else:
            aba.title = 'Outra'
    c = laboratorio(modificar_excel=alterar)
    salvar(c)
    with pytest.raises(ErroAplicacao):
        comparar(c)


def test_espaco_final_aa_e_representacao_sem_alterar_contrato(laboratorio):
    c = laboratorio(modificar_excel=lambda aba: setattr(aba.cell(1, 27), 'value', COLUNAS[26]))
    salvar(c)
    resultado = comparar(c)
    assert [(d.categoria, d.motivo_codigo) for d in resultado.divergencias] == [('formatacao', 'ESPACO_FISICO_DO_CABECALHO')]


def test_vinculo_cadastral_nao_cria_dados_de_divida(laboratorio):
    def zerar(aba):
        for i in range(25, 31):
            aba.cell(2, i).value = None
    c = laboratorio(modificar_excel=zerar)
    salvar(c)
    dados = c.mapeamento.model_dump(mode='json')
    dados['vinculos'][0].update(tipo='cadastral', boletos_ids=[])
    c.mapeamento = MapeamentoReferencia.model_validate(dados)
    resultado = comparar(c)
    assert any(d.motivo_codigo == 'ELEGIVEL_SEM_DIVIDA_DE_REFERENCIA' for d in resultado.divergencias)
    assert not any(d.motivo_codigo.startswith('VALOR_ORIGINAL') for d in resultado.divergencias)
