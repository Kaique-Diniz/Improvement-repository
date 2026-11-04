import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from conversor.domain.billing_evaluation import RelatorioSimulacao,SolicitacaoSimulacao,EntradaSimulacao
from conversor.evaluation_schemas import documentos,main
from tests.evaluation.conftest import fato


def test_relatorio_roundtrip_sem_capacidade_operacional(preparar):
    s,r,e,p=preparar();rel=s.executar(r,e)
    assert RelatorioSimulacao.model_validate_json(rel.model_dump_json())==rel
    for campo in ('autoriza_cobranca','permite_exportacao_operacional'):
        dados=rel.model_dump();dados[campo]=True
        with pytest.raises(ValidationError):RelatorioSimulacao.model_validate(dados)


@pytest.mark.parametrize('campo,valor',[('data_ref',None),('data_ref','21/10/2026'),('data_ref',1720000000),
    ('modo','operacional'),('ambiente','producao')])
def test_solicitacao_sem_data_ou_capacidade_operacional_recusada(preparar,campo,valor):
    s,r,e,p=preparar();dados=r.model_dump();dados[campo]=valor
    with pytest.raises(ValidationError):SolicitacaoSimulacao.model_validate(dados)


def test_colecoes_de_evidencia_obrigatorias_e_sem_duplicados(preparar):
    s,r,e,p=preparar()
    for campo in ('fatos','ocorrencias_anteriores','coberturas_apontamentos'):
        dados=e.model_dump();dados.pop(campo)
        with pytest.raises(ValidationError):EntradaSimulacao.model_validate(dados)
    with pytest.raises(ValidationError):EntradaSimulacao.model_validate(e.model_dump()|{'fatos':(fato(),fato())})


def test_schema_reproduzivel_e_protecao_somente_simulacao(tmp_path):
    assert main(['--check'])==0
    assert main(['--saida',str(tmp_path)])==0
    for nome,conteudo in documentos():assert (tmp_path/nome).read_text(encoding='utf-8')==conteudo
    schema=json.loads((tmp_path/'relatorio.schema.json').read_text(encoding='utf-8'))
    assert schema['properties']['autoriza_cobranca']['const']is False
    assert schema['properties']['permite_exportacao_operacional']['const']is False
    assert schema['additionalProperties']is False


def test_demonstracao_sintetica_contem_as_quatro_decisoes():
    from examples.fase4.gerar_relatorio_4_2 import demonstrar
    rel=demonstrar()
    assert {d.situacao for d in rel.boletos}=={
        'elegivel_na_simulacao','excluido','bloqueado','pendente_revisao'}
    assert not rel.autoriza_cobranca and not rel.permite_exportacao_operacional
    # O arquivo é exemplo de formato. Sua autoridade temporária já foi descartada.
    exemplo=RelatorioSimulacao.model_validate_json(Path('examples/fase4/relatorio_sintetico_4_2.json').read_text())
    assert [(d.situacao,d.motivo_codigo)for d in exemplo.boletos]==[(d.situacao,d.motivo_codigo)for d in rel.boletos]
