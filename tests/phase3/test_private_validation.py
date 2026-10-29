from tests.fs_support import assert_privado
from hashlib import sha256
import json
import subprocess
import sys

import pytest

from conversor.readers.text_support import ErroLeitura
from conversor.validacao_leitores import ManifestoValidacao, _ContextosDeclarados, executar_validacao, main
from conversor.adapters.protected_sources import FontesLocaisProtegidas
from conversor.readers.operational import RegistroLeitores


@pytest.fixture
def area(tmp_path, fontes_sinteticas):
    (tmp_path / "fontes").mkdir()
    (tmp_path / "gabaritos").mkdir()
    casos = []
    for familia, codigo in (("habita", "9999"), ("fl", "LAB"), ("cadastro", "LAB")):
        dados = fontes_sinteticas[familia]
        (tmp_path / "fontes" / f"{familia}.pdf").write_bytes(dados)
        casos.append({"id": familia, "fonte": {"arquivo_id": familia, "sha256": sha256(dados).hexdigest()},
            "arquivo": f"fontes/{familia}.pdf", "gabarito": f"gabaritos/{familia}.json", "gabarito_sha256": "0" * 64,
            "leitor_id": "cadastro_fl_sintetico_v1" if familia == "cadastro" else familia + "_composicao_sintetico_v1",
            "formato_id": "fmt_" + familia, "condominio_id": "cond_lab", "administradora_id": "adm_lab",
            "codigo_condominio": codigo, "data_ref": "2026-10-20"})
    dados = {"finalidade": "validacao_privada_fase3", "natureza": "sintetica", "autorizacao_id": "fixture_sintetica", "casos": casos}
    config = ManifestoValidacao.model_validate(dados)
    fontes = FontesLocaisProtegidas(tmp_path, {c.fonte.arquivo_id: c.arquivo for c in config.casos})
    registro = RegistroLeitores(fontes, _ContextosDeclarados(config.casos))
    for caso in config.casos:
        lote = registro.obter(caso.leitor_id, caso.leitor_versao).ler(caso.fonte, formato_id=caso.formato_id, condominio_id=caso.condominio_id)
        # Fixture de contrato do comparador, não gabarito real homologado.
        # A extração/valores são verificados independentemente em test_operational_readers.
        b = lote.model_dump_json().encode()
        (tmp_path / caso.gabarito).write_bytes(b)
        next(c for c in dados["casos"] if c["id"] == caso.id)["gabarito_sha256"] = sha256(b).hexdigest()
    manifesto = tmp_path / "manifesto.json"
    manifesto.write_text(json.dumps(dados))
    return tmp_path, manifesto


def test_tres_casos_e_sem_canonicos_por_padrao(area, capsys):
    raiz, manifesto = area
    destino = raiz / "resultado"
    assert main(["--raiz", str(raiz), "--manifesto", str(manifesto), "--saida", str(destino)]) == 0
    resumo = json.loads(capsys.readouterr().out)
    assert resumo["estados"] == {"comparacao_confere": 3}
    assert resumo["homologado_producao"] is False
    assert sorted(p.name for p in destino.iterdir()) == ["relatorio_leitores.json"]
    r = json.loads((destino / "relatorio_leitores.json").read_text())
    assert [c["boletos"] for c in r["casos"]] == [1, 1, 0]
    assert all(c["alertas"] == {"DOCUMENTO_AUSENTE": 1} for c in r["casos"])
    assert "example.invalid" not in (destino / "relatorio_leitores.json").read_text()


def test_canonicos_so_por_opcao_explicita_na_area_privada(area):
    raiz, manifesto = area
    destino = raiz / "resultado"
    executar_validacao(raiz, manifesto, destino, salvar_canonicos=True)
    assert len(list(destino.glob("*.canonico.json"))) == 3
    assert_privado(destino / "habita.canonico.json")


def test_conflito_documental_nao_confirma_gabarito_e_grava_auditoria_protegida(area,monkeypatch,capsys):
    from conversor.application.reading import resultado_leitura
    from conversor.domain.canonical import Documento, EvidenciaDocumento, LoteCanonico, Pessoa
    raiz,manifesto=area
    def com_conflito(lote,*,processamento_id):
        pessoa=lote.pessoas[0]
        a=EvidenciaDocumento(documento=Documento(tipo='cpf',valor='00000000191'),
            origem=pessoa.origem,titular_id=pessoa.id)
        b=EvidenciaDocumento(documento=Documento(tipo='cnpj',valor='00000000000191'),
            origem=pessoa.origem,titular_id=pessoa.id)
        pessoa=Pessoa.model_validate(pessoa.model_dump()|{'documento':None,'evidencias_documentais':(a,b)})
        novo=LoteCanonico.model_validate(lote.model_dump()|{'pessoas':(pessoa,)})
        return resultado_leitura(novo,processamento_id=processamento_id)
    monkeypatch.setattr('conversor.validacao_leitores.resultado_leitura',com_conflito)
    destino=raiz/'revisao'
    assert main(['--raiz',str(raiz),'--manifesto',str(manifesto),'--saida',str(destino)])==2
    stdout=capsys.readouterr().out
    assert '00000000191'not in stdout and '00000000000191'not in stdout
    relatorio=json.loads((destino/'relatorio_leitores.json').read_text())
    assert all(c['status']=='revisao_humana'for c in relatorio['casos'])
    assert all(c['total_campos_divergentes']==0 for c in relatorio['casos'])
    assert not list(destino.glob('*.canonico.json'))
    for c in relatorio['casos']:
        auditoria=destino/c['auditoria_revisao']
        assert_privado(auditoria)
        dados=json.loads(auditoria.read_text())
        fontes=dados['ocorrencias'][0]['evidencias_documentais']
        assert {f['documento']['tipo']for f in fontes}=={'cpf','cnpj'}


@pytest.mark.parametrize("falha,codigo", [("hash", "HASH_FONTE_DIVERGENTE"), ("gabarito_ausente", "FONTE_INDISPONIVEL"),
    ("fonte_ausente", "FONTE_INDISPONIVEL"), ("contexto", "CONDOMINIO_DIVERGENTE")])
def test_incompatibilidade_bloqueia_somente_caso_sem_salvar_parcial(area, falha, codigo):
    raiz, manifesto = area
    dados = json.loads(manifesto.read_text())
    if falha == "hash": dados["casos"][0]["fonte"]["sha256"] = "0" * 64
    elif falha == "gabarito_ausente": dados["casos"][0]["gabarito"] = "ausente.json"
    elif falha == "fonte_ausente": dados["casos"][0]["arquivo"] = "ausente.pdf"
    else: dados["casos"][0]["codigo_condominio"] = "8888"
    manifesto.write_text(json.dumps(dados))
    destino = raiz / "resultado"
    r = executar_validacao(raiz, manifesto, destino, salvar_canonicos=True)
    assert r["casos"][0]["codigo"] == codigo
    assert r["casos"][0]["status"] == "bloqueado"
    assert not (destino / "habita.canonico.json").exists()
    assert all(c["status"] == "comparacao_confere" for c in r["casos"][1:])


def test_gabarito_divergente_nao_alimenta_valor_extraido(area, capsys):
    raiz, manifesto = area
    p = raiz / "gabaritos/habita.json"
    esperado = json.loads(p.read_text())
    esperado["boletos"][0]["composicao"]["itens"][0]["valor"] = "101.00"
    esperado["boletos"][0]["composicao"]["total_original"] = "121.00"
    p.write_text(json.dumps(esperado))
    dados = json.loads(manifesto.read_text())
    dados["casos"][0]["gabarito_sha256"] = sha256(p.read_bytes()).hexdigest()
    manifesto.write_text(json.dumps(dados))
    destino = raiz / "resultado"
    assert main(["--raiz", str(raiz), "--manifesto", str(manifesto), "--saida", str(destino), "--salvar-canonicos"]) == 1
    r = json.loads((destino / "relatorio_leitores.json").read_text())
    assert r["casos"][0]["total_campos_divergentes"] == 2
    assert all("valor" not in d for d in r["casos"][0]["campos_divergentes"])
    atual = json.loads((destino / "habita.canonico.json").read_text())
    assert atual["boletos"][0]["composicao"]["total_original"] == "120.00"
    assert "120.00" not in capsys.readouterr().out


def test_fonte_privada_nao_pode_estar_em_checkout_git(area):
    raiz, manifesto = area
    subprocess.run(["git", "init", "--quiet", str(raiz)], check=True)
    with pytest.raises(ErroLeitura, match="AREA_PRIVADA_DEVE_FICAR_FORA_DO_GIT"):
        executar_validacao(raiz, manifesto, raiz / "resultado")


def test_destino_existente_nao_e_sobrescrito(area):
    raiz, manifesto = area
    destino = raiz / "resultado"
    destino.mkdir()
    with pytest.raises(ErroLeitura, match="SAIDA_PRIVADA_DEVE_SER_NOVA_E_INTERNA"):
        executar_validacao(raiz, manifesto, destino)


def test_json_invalido_tem_erro_seguro(area, capsys):
    raiz, manifesto = area
    manifesto.write_text('{"segredo":"SENTINELA_NAO_EXIBIR",')
    assert main(["--raiz", str(raiz), "--manifesto", str(manifesto), "--saida", str(raiz / "resultado")]) == 2
    assert "SENTINELA_NAO_EXIBIR" not in capsys.readouterr().out


def test_validador_fase3_nao_importa_motor_de_cobranca_ou_exportacao():
    programa = ('import sys,json; import conversor.validacao_leitores; '
                'print(json.dumps([m for m in sys.modules if m.startswith(("conversor.rules", "conversor.export", "conversor.laboratorio"))]))')
    resultado = subprocess.run([sys.executable, "-c", programa], capture_output=True, text=True, check=True)
    assert json.loads(resultado.stdout) == []
