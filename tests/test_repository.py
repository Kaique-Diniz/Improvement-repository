from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from datetime import date

from filelock import FileLock
import pytest

from conversor.adapters.json_repository import RepositorioJSON, ler_json_bytes
from conversor.application.configuration import Configuracao
from conversor.application.ports import ErroAplicacao
from conversor.domain.catalog import Catalogo
from test_catalog import aprovar, processamento


@pytest.fixture
def repo(tmp_path):
    return RepositorioJSON(tmp_path / "dados", timeout=0.05)


def test_ausente_nao_e_silenciosamente_catalogo_vazio(repo):
    with pytest.raises(ErroAplicacao, match="REPOSITORIO_NAO_INICIALIZADO"):
        repo.carregar()
    assert not repo.raiz.exists()


def test_roundtrip_oito_arquivos_versao_e_backup(repo, catalogo):
    assert repo.salvar(catalogo, revisao_esperada=0).revisao == 1
    assert repo.carregar().catalogo == catalogo
    antigo = (repo.raiz / "current.json").read_bytes()
    repo.salvar(catalogo, revisao_esperada=1)
    assert repo.carregar().revisao == 2
    manifesto = json.loads(antigo)
    pasta = repo.raiz / "generations" / manifesto["geracao"]
    assert len(list(pasta.glob("*.json"))) == 9  # 8 coleções + manifesto de backup
    assert (pasta / "manifest.json").read_bytes() == antigo
    assert json.loads((pasta / "administradoras.json").read_text())["schema_version"] == "1.0"
    if os.name == "posix":
        assert (repo.raiz / "current.json").stat().st_mode & 0o777 == 0o600


def test_revisao_antiga_rejeitada(repo, catalogo):
    repo.salvar(catalogo, revisao_esperada=0)
    with pytest.raises(ErroAplicacao, match="CONFLITO_DE_REVISAO"):
        repo.salvar(catalogo, revisao_esperada=0)


def test_concorrencia_um_vencedor_sem_atualizacao_perdida(repo, catalogo):
    repo.salvar(catalogo, revisao_esperada=0)
    def escrever(_):
        try:
            RepositorioJSON(repo.raiz, timeout=2).salvar(catalogo, revisao_esperada=1)
            return "ok"
        except ErroAplicacao as erro:
            return str(erro)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(escrever, range(2)))
    assert sorted(resultados) == ["CONFLITO_DE_REVISAO", "ok"]
    assert repo.carregar().revisao == 2


def test_lock_ativo_bloqueia_escrita(repo, catalogo):
    repo.salvar(catalogo, revisao_esperada=0)
    with FileLock(repo.raiz / ".write.lock"):
        with pytest.raises(ErroAplicacao, match="REPOSITORIO_OCUPADO"):
            repo.salvar(catalogo, revisao_esperada=1)


def test_falha_antes_commit_preserva_snapshot(repo, catalogo, monkeypatch):
    repo.salvar(catalogo, revisao_esperada=0)
    anterior = (repo.raiz / "current.json").read_bytes()
    replace = os.replace
    def falhar(origem, destino):
        if Path(destino).name == "current.json":
            raise OSError("sentinela_privada")
        replace(origem, destino)
    monkeypatch.setattr(os, "replace", falhar)
    with pytest.raises(ErroAplicacao, match="FALHA_GRAVACAO_REPOSITORIO") as erro:
        repo.salvar(catalogo, revisao_esperada=1)
    assert "sentinela_privada" not in str(erro.value)
    assert (repo.raiz / "current.json").read_bytes() == anterior
    assert repo.carregar().catalogo == catalogo
    assert not list(repo.raiz.glob(".current-*.tmp"))


def test_falha_no_meio_dos_arquivos_nao_publica_parcial(repo, catalogo, monkeypatch):
    import conversor.adapters.json_repository as modulo
    repo.salvar(catalogo, revisao_esperada=0)
    gravar = modulo._gravar
    def falhar(path, conteudo):
        if path.name == "formatos.json":
            raise OSError("falha_simulada")
        return gravar(path, conteudo)
    monkeypatch.setattr(modulo, "_gravar", falhar)
    with pytest.raises(ErroAplicacao):
        repo.salvar(catalogo, revisao_esperada=1)
    assert repo.carregar().revisao == 1
    assert not list((repo.raiz / "generations").glob(".tmp-*"))


@pytest.mark.parametrize("conteudo,codigo", [(b'{', "JSON_INVALIDO"),
    (b'{"schema_version":"2.0"}', "SCHEMA_NAO_SUPORTADO"),
    (b'{"schema_version":"1.0","schema_version":"2.0"}', "JSON_COM_CHAVE_DUPLICADA")])
def test_corrupto_versao_futura_e_chaves_duplicadas(repo, catalogo, conteudo, codigo):
    repo.salvar(catalogo, revisao_esperada=0)
    (repo.raiz / "current.json").write_bytes(conteudo)
    with pytest.raises(ErroAplicacao, match=codigo):
        repo.carregar()


@pytest.mark.parametrize("modo", ["hash", "ausente", "referencia", "schema"])
def test_danos_em_colecao_sao_explicitos(repo, catalogo, modo):
    repo.salvar(catalogo, revisao_esperada=0)
    ponteiro = repo.raiz / "current.json"
    manifesto = json.loads(ponteiro.read_text())
    pasta = repo.raiz / "generations" / manifesto["geracao"]
    arquivo = pasta / "administradoras.json"
    if modo == "ausente":
        arquivo.unlink()
    elif modo == "hash":
        arquivo.write_text("{}")
    else:
        dados = json.loads(arquivo.read_text())
        if modo == "referencia":
            dados["administradoras"] = []
        else:
            dados["schema_version"] = "999"
        arquivo.write_text(json.dumps(dados))
        manifesto["arquivos"][arquivo.name] = sha256(arquivo.read_bytes()).hexdigest()
        ponteiro.write_text(json.dumps(manifesto))
        (pasta / "manifest.json").write_bytes(ponteiro.read_bytes())
    with pytest.raises(ErroAplicacao):
        repo.carregar()


def test_integridade_revalidada_antes_de_escrever(repo, catalogo):
    # model_copy pode ignorar validadores de Pydantic: adapter não confia no objeto recebido.
    adulterado = catalogo.model_copy(update={"administradoras": ()})
    with pytest.raises(ErroAplicacao, match="CONTRATO_OU_REFERENCIA_INVALIDA"):
        repo.salvar(adulterado, revisao_esperada=0)
    assert not repo.raiz.exists()


def test_crud_restricoes_e_consultas(repo, catalogo):
    servico = Configuracao(repo)
    servico.inicializar()
    servico.importar(catalogo, revisao_esperada=1)
    assert servico.encontrar_condominio("adm_sintetica_a", "0001").id == "cond_sintetico"
    assert servico.obter("templates", "template_universal_v1").versao == "1"
    servico.gravar("administradoras", {"id": "adm_nova", "nome": "Administradora Sintética Nova"}, revisao_esperada=2)
    assert "adm_nova" in servico.listar_ids("administradoras")
    servico.excluir("administradoras", "adm_nova", revisao_esperada=3)
    with pytest.raises(ErroAplicacao, match="REFERENCIA_VIOLADA"):
        servico.excluir("administradoras", "adm_sintetica_a", revisao_esperada=4)
    assert repo.carregar().revisao == 4
    with pytest.raises(ErroAplicacao, match="REGRA_APROVADA_INDISPONIVEL"):
        servico.regra_aprovada("cond_sintetico", date(2026, 10, 20))


def test_versoes_aprovadas_e_historico_sao_imutaveis(repo, dados_catalogo, origem):
    dados = aprovar(dados_catalogo, origem)
    dados["processamentos"] = [processamento("concluido")]
    original = Catalogo.model_validate(dados)
    repo.salvar(original, revisao_esperada=0)
    for colecao, campo, valor in [("formatos", "nome", "Alterado"), ("regras_cobranca", "versao", "2"),
        ("perfis_condominio", "cadastro_antecipado", True), ("templates", "espaco_final_coluna_27", False),
        ("processamentos", "linhas", 10)]:
        alterado = deepcopy(dados)
        alterado[colecao][0][campo] = valor
        with pytest.raises(ErroAplicacao, match="HISTORICO_OU_VERSAO_IMUTAVEL"):
            repo.salvar(Catalogo.model_validate(alterado), revisao_esperada=1)
    assert repo.carregar().catalogo == original


def test_json_nao_finito_rejeitado():
    with pytest.raises(ErroAplicacao, match="JSON_NAO_FINITO"):
        ler_json_bytes(b'{"numero":NaN}')


def test_classificacao_conhecida_exige_formato_homologado(repo, catalogo, dados_catalogo, origem):
    from conversor.readers.contracts import ClassificacaoFormato
    repo.salvar(catalogo, revisao_esperada=0)
    servico = Configuracao(repo)
    conhecido = ClassificacaoFormato(estado="conhecido_validado", candidatos=("formato_sintetico_v1",), evidencia_hashes=("0" * 64,))
    with pytest.raises(ErroAplicacao, match="FORMATO_NAO_VALIDADO"):
        servico.validar_classificacao(conhecido)
    desconhecido = ClassificacaoFormato(estado="desconhecido", evidencia_hashes=("0" * 64,))
    with pytest.raises(ErroAplicacao, match="FORMATO_NAO_RESOLVIDO"):
        servico.validar_classificacao(desconhecido)
    repo.salvar(Catalogo.model_validate(aprovar(dados_catalogo, origem)), revisao_esperada=1)
    assert servico.validar_classificacao(conhecido).status == "validado"
    assert servico.regra_aprovada("cond_sintetico", date(2026, 10, 20)).status == "aprovada"


def test_service_nao_grava_sobre_leitura_de_outra_revisao(repo, catalogo):
    repo.salvar(catalogo, revisao_esperada=0)
    with pytest.raises(ErroAplicacao, match="CONFLITO_DE_REVISAO"):
        Configuracao(repo).gravar("administradoras", {"id": "adm_nova", "nome": "Sintética"}, revisao_esperada=2)
    assert repo.carregar().revisao == 1


def test_leitor_mantem_snapshot_consistente_durante_commit(repo, catalogo, monkeypatch):
    repo.salvar(catalogo, revisao_esperada=0)
    dados = catalogo.model_dump()
    dados["administradoras"] = list(dados["administradoras"]) + [{"id": "adm_nova", "nome": "Sintética Nova"}]
    atualizado = Catalogo.model_validate(dados)
    leitura = Path.read_bytes
    intercalou = False
    def interceptar(path):
        nonlocal intercalou
        resultado = leitura(path)
        if path == repo.raiz / "current.json" and not intercalou:
            intercalou = True
            repo.salvar(atualizado, revisao_esperada=1)
        return resultado
    monkeypatch.setattr(Path, "read_bytes", interceptar)
    estado = repo.carregar()
    assert intercalou
    assert estado.revisao == 1
    assert estado.catalogo == catalogo
    assert repo.carregar().revisao == 2


def test_uso_do_caso_de_uso_com_outro_backend_sem_mudar_codigo(catalogo):
    from conversor.application.ports import Estado
    class RepositorioMemoria:
        def __init__(self):
            self.estado = Estado(revisao=0, catalogo=Catalogo())
        def carregar(self):
            return self.estado
        def salvar(self, catalogo, *, revisao_esperada):
            if self.estado.revisao != revisao_esperada:
                raise ErroAplicacao("CONFLITO_DE_REVISAO")
            self.estado = Estado(revisao=self.estado.revisao + 1, catalogo=catalogo)
            return self.estado
    caso = Configuracao(RepositorioMemoria())
    caso.importar(catalogo, revisao_esperada=0)
    assert caso.encontrar_condominio("adm_sintetica_a", "0001").id == "cond_sintetico"
    assert caso.get_condominio("cond_sintetico").administradora_id == "adm_sintetica_a"
    assert caso.get_administradora("adm_sintetica_a").ativo
    assert caso.get_formato("formato_sintetico_v1") in caso.formatos_da_administradora("adm_sintetica_b")
    assert caso.get_perfil("perfil_sintetico_v1").template_id == caso.get_template("template_universal_v1").id
    assert caso.get_regra("regra_sintetica_v1").status == "rascunho"
    caso.gravar("administradoras", {"id": "adm_nova", "nome": "Sintética Nova"}, revisao_esperada=1)
    assert "adm_nova" in caso.listar_ids("administradoras")


def test_porta_historico_salva_execucao_e_ocorrencia_sem_reescrever(repo, catalogo):
    from conversor.domain.catalog import Processamento
    from conversor.domain.canonical import Ocorrencia
    repo.salvar(catalogo, revisao_esperada=0)
    servico = Configuracao(repo)
    proc = Processamento.model_validate(processamento())
    servico.salvar_processamento(proc, revisao_esperada=1)
    alerta = Ocorrencia(id="oc_1", processamento_id=proc.id, codigo="CPF_AUSENTE_OU_INVALIDO",
                        gravidade="alerta", escopo="registro", registro_id="pessoa_sintetica")
    servico.salvar_ocorrencia(alerta, revisao_esperada=2)
    assert servico.get_processamento(proc.id) == proc
    assert repo.carregar().catalogo.ocorrencias == (alerta,)
    alterada = Ocorrencia.model_validate(alerta.model_dump() | {"codigo": "OUTRO"})
    with pytest.raises(ErroAplicacao, match="HISTORICO_OU_VERSAO_IMUTAVEL"):
        servico.salvar_ocorrencia(alterada, revisao_esperada=3)
