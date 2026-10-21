from copy import deepcopy
import json
from pathlib import Path

import pytest

from conversor.adapters.document_probe import SondadorLocal
from conversor.adapters.json_repository import RepositorioJSON
from conversor.adapters.signature_repository import AssinaturasJSON
from conversor.application.recognition import ReconhecerDocumento
from conversor.domain.catalog import Catalogo
from examples.fase2.gerar_demo import catalogo_sintetico, pdf_sintetico

EXEMPLOS = Path(__file__).resolve().parents[2] / "examples/fase2"


@pytest.fixture
def textos_sinteticos():
    return json.loads((EXEMPLOS / "documentos.sinteticos.json").read_text(encoding="utf-8"))


@pytest.fixture
def dados_reconhecimento(origem):
    # Aprovações artificiais só no teste; não homologam formatos/amostras reais.
    dados = catalogo_sintetico().model_dump(mode="json")
    aprovacao = {"responsavel_id": "teste_sintetico", "evidencia_id": "fixture_nao_producao", "em": "2026-10-21T00:00:00Z"}
    for formato in dados["formatos"]:
        formato.update(status="validado", aprovacao=deepcopy(aprovacao))
    for perfil in dados["perfis_condominio"]:
        perfil.update(status="aprovado", aprovacao=deepcopy(aprovacao))
    for regra in dados["regras_cobranca"]:
        regra.update(status="aprovada", aprovacao=deepcopy(aprovacao), fonte=origem.model_dump(mode="json"),
            condicoes=[{"campo": "fixture_sintetica", "operador": "igual", "valor": "nao_producao",
                        "alcance": "boleto", "acao": "alertar", "prioridade": 0}])
    return dados


@pytest.fixture
def assinaturas_reconhecimento():
    dados = json.loads((EXEMPLOS / "assinaturas.sinteticas.json").read_text(encoding="utf-8"))
    dados.update(status="homologado", aprovacao={"responsavel_id": "teste_sintetico", "evidencia_id": "fixture_nao_producao",
                                               "em": "2026-10-21T00:00:00Z"})
    return dados


@pytest.fixture
def reconhecer(tmp_path, dados_reconhecimento, assinaturas_reconhecimento):
    contador = 0
    def executar(paginas, *, catalogo=None, assinaturas=None, data_ref=None):
        from datetime import date
        nonlocal contador
        contador += 1
        raiz = tmp_path / f"exec_{contador}"
        repo = RepositorioJSON(raiz)
        repo.salvar(Catalogo.model_validate(catalogo or dados_reconhecimento), revisao_esperada=0)
        arquivo = raiz / "assinaturas.json"
        arquivo.write_text(json.dumps(assinaturas or assinaturas_reconhecimento), encoding="utf-8")
        conteudo = paginas if isinstance(paginas, bytes) else pdf_sintetico(paginas)
        sonda = SondadorLocal().sondar(conteudo, arquivo_id="fonte_sintetica")
        return ReconhecerDocumento(repo, AssinaturasJSON(arquivo)).executar(sonda, data_ref=data_ref or date(2026, 10, 21))
    return executar
