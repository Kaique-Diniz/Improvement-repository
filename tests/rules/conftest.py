"""Autoridade e planos criados do zero em temporários; nenhuma credencial real."""
from hashlib import sha256
import json
from pathlib import Path
import secrets
from types import SimpleNamespace

import pytest

from conversor.adapters.billing_authority import AutoridadeHMAC
from conversor.adapters.billing_json import RepositorioPlanosJSON
from conversor.adapters.json_repository import _gravar
from conversor.adapters.private_json import escrever_json
from conversor.adapters.private_permissions import criar_diretorio_privado
from conversor.application.billing_ports import CredencialOperador
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import PlanoCobranca


class CondominiosSinteticos:
    def get_condominio(self, id_):
        if id_ not in ('cond_sintetico', 'cond_outro'):
            raise ErroAplicacao('REFERENCIA_DE_CONDOMINIO_INVALIDA')
        return SimpleNamespace(id=id_)


@pytest.fixture
def dados_plano():
    return json.loads(Path('examples/fase4/plano.sintetico.json').read_text())


@pytest.fixture
def plano(dados_plano):
    return PlanoCobranca.model_validate(dados_plano)


@pytest.fixture
def seguranca(tmp_path):
    raiz = criar_diretorio_privado(tmp_path / 'autoridade')
    _gravar(raiz / 'chave.bin', secrets.token_bytes(32))
    credenciais = {nome: CredencialOperador(secrets.token_hex(32)) for nome in ('gestor', 'editor', 'aprovador', 'ativador')}
    acoes = {'gestor': ['criar', 'submeter', 'rejeitar', 'aprovar', 'ativar', 'revogar'],
             'editor': ['criar', 'submeter'], 'aprovador': ['aprovar', 'rejeitar'], 'ativador': ['ativar', 'revogar']}
    registro = {'schema_version': '1.0', 'concessoes': [{'responsavel_id': n,
        'credencial_sha256': sha256(c.segredo.encode()).hexdigest(), 'acoes': acoes[n],
        'condominio_ids': ['cond_sintetico', 'cond_outro'], 'ambientes': ['sintetico', 'privado']}
        for n,c in credenciais.items()]}
    escrever_json(raiz / 'operadores.json', registro)
    return AutoridadeHMAC(raiz), credenciais


@pytest.fixture
def repo(tmp_path, seguranca):
    autoridade, _ = seguranca
    return RepositorioPlanosJSON(tmp_path/'planos', repositorio_id='testes', ambiente='sintetico',
        autoridade=autoridade, condominios=CondominiosSinteticos(), timeout=0.1)


@pytest.fixture
def gestor(seguranca):
    return seguranca[1]['gestor']
