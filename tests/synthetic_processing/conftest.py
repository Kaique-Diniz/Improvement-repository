"""Autoridade, planos e evidências inventados; tudo em tmp_path, nunca fontes privadas."""
from datetime import date, timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.application.synthetic_processing import SimularProcessamentoSintetico
from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.billing_rules import PlanoCobranca, hash_modelo
from conversor.domain.canonical import Apontamento, Boleto, LoteCanonico
from conversor.domain.synthetic_processing import SolicitacaoProcessamentoSintetico
from tests.rules.conftest import seguranca, gestor, repo
from tests.rules.test_plan_repository import executar

NAMESPACE = 'fmt_habita_sintetico_mapeamento'
DATA_REF = date(2026, 10, 21)


@pytest.fixture
def montar(repo, gestor, origem, unidade, boleto, pessoa):
    def construir(*, specs=None, lote=None, coberturas=None, ocorrencias=(), data_ref=DATA_REF,
                  modo='A', estado='ativo', editar_plano=None):
        dados = json.loads(Path('examples/fase4/tree_43b1.sintetico.json').read_text())
        if editar_plano:
            editar_plano(dados)
        plano = PlanoCobranca.model_validate(dados)
        for acao, alvo in [('criar', 'rascunho'), ('submeter', 'aguardando_aprovacao'),
                           ('aprovar', 'aprovado'), ('ativar', 'ativo'), ('revogar', 'revogado')]:
            executar(repo, plano, gestor, acao, data_ref=DATA_REF if acao == 'ativar' else None)
            if estado == alvo:
                break
        covers = []
        if lote is None:
            bills = []
            for i, spec in enumerate(specs or [{}]):
                spec = dict(spec)
                aps = (Apontamento(codigo_original=spec.get('ap'),
                        namespace_formato=spec.get('namespace', NAMESPACE), origem=origem),) if spec.get('ap') else ()
                b = Boleto.model_validate(boleto.model_dump() | {
                    'id': 'boleto_' + str(i), 'identificador': 'inventado_' + str(i),
                    'vencimento': DATA_REF - timedelta(days=spec.get('dias', 31)), 'apontamentos': aps,
                    **({'composicao': spec['composicao']} if 'composicao' in spec else {}),
                    **({'multa': spec['multa'], 'juros': spec.get('juros', '0.00'),
                        'correcao': spec.get('correcao', '0.00')} if 'multa' in spec else {})})
                bills.append(b)
                if spec.get('cobertura', True):
                    covers.append(CoberturaApontamentos(boleto_id=b.id, namespace=NAMESPACE, origens=b.origens))
            lote = LoteCanonico(unidades=(unidade,), boletos=tuple(bills), pessoas=(pessoa,))
        entrada = EntradaSimulacao(lote=lote, fatos=(), ocorrencias_anteriores=ocorrencias,
                    coberturas_apontamentos=tuple(covers) if coberturas is None else coberturas)
        solicitacao = SolicitacaoProcessamentoSintetico(processamento_id='teste_43b1',
                    condominio_id=plano.condominio_id, plano_id=plano.id, plano_versao=plano.versao,
                    plano_hash=hash_modelo(plano), ambiente='sintetico', data_ref=data_ref, modo_cadastro=modo)
        servico = SimularProcessamentoSintetico(repo, VerificadorPlanosJSON(repo))
        return SimpleNamespace(servico=servico, s=solicitacao, e=entrada, p=plano, repo=repo)
    return construir
