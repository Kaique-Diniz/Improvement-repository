"""Comparação independente; resultados esperados nunca alimentam leitores ou cálculo."""
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256

from openpyxl import load_workbook

from conversor.domain.template import COLUNAS


def _vazio(valor):
    return "" if valor is None else valor


def _normalizar(valor):
    if isinstance(valor, datetime): return valor.date().isoformat()
    if isinstance(valor, date): return valor.isoformat()
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool): return Decimal(str(valor))
    return _vazio(valor)


def _hash_texto(valor):
    return sha256(str(_vazio(valor)).encode()).hexdigest()


def comparar_excel(gerado, referencia, referencias):
    atual = load_workbook(gerado, read_only=True, data_only=False)
    gabarito = load_workbook(referencia, read_only=True, data_only=False)
    try:
        a = list(atual["Dados"].iter_rows(values_only=True))
        b = list(gabarito["Dados"].iter_rows(values_only=True))
        diferencas, representacao = [], []
        if tuple(a[0]) != tuple(b[0]):
            diferencas.append({"campo": "cabecalho", "codigo": "CABECALHO_DIVERGENTE"})
        if len(a) != len(b):
            diferencas.append({"campo": "linhas", "codigo": "QUANTIDADE_LINHAS_DIVERGENTE", "obtido": len(a)-1, "esperado": len(b)-1})
        for indice, (linha_a, linha_b) in enumerate(zip(a[1:], b[1:]), 2):
            for coluna, (valor_a, valor_b) in enumerate(zip(linha_a, linha_b)):
                fonte = dict(referencias[indice-2])
                campos = fonte.pop("origens_campos", {})
                local = {"linha_excel": indice, "campo": COLUNAS[coluna], **fonte, **campos.get(COLUNAS[coluna], {})}
                if _normalizar(valor_a) != _normalizar(valor_b):
                    # Não expõe nomes, CPFs, telefones ou e-mails, mesmo em relatório.
                    diferencas.append(local | {"codigo": "VALOR_DIVERGENTE", "obtido_hash": _hash_texto(valor_a),
                                              "esperado_hash": _hash_texto(valor_b)})
                elif type(valor_a) is not type(valor_b) and valor_a is not None and valor_b is not None:
                    representacao.append(local | {"codigo": "TIPO_DIFERENTE_VALOR_EQUIVALENTE",
                        "obtido_tipo": type(valor_a).__name__, "esperado_tipo": type(valor_b).__name__})
        return {"linhas_geradas": len(a)-1, "linhas_referencia": len(b)-1,
                "divergencias_conteudo": diferencas, "diferencas_representacao": representacao}
    finally:
        atual.close()
        gabarito.close()


def conferir_financeiro(lote, resultados, linhas, ocorrencias, esperado):
    unidades = {u.id: u for u in lote.unidades}
    boletos = {b.id: b for b in lote.boletos}
    elegiveis = {boletos[r.boleto_id].identificador: boletos[r.boleto_id].composicao.total_original
                 for r in resultados if r.acao == "incluir"}
    excluidas = sorted({unidades[r.unidade_id].chave_normalizada for r in resultados if r.acao == "excluir"})
    cadastrais = [unidades[l.pessoa.unidade_id].chave_normalizada for l in linhas if l.tipo == "cadastral"]
    cpf = sum(o.codigo == "CPF_AUSENTE_OU_INVALIDO" for o in ocorrencias)
    verificacoes = []
    def checar(campo, atual, ouro):
        verificacoes.append({"campo": campo, "ok": atual == ouro,
                             "obtido": atual, "esperado": ouro})
    checar("unidades", len(lote.unidades), esperado["unidades"])
    checar("boletos_unicos", len(lote.boletos), esperado["boletos_unicos"])
    checar("boletos_elegiveis", {k: str(v.quantize(Decimal("0.01"))) for k, v in elegiveis.items()},
           {k: str(Decimal(str(v)).quantize(Decimal("0.01"))) for k, v in esperado["boletos_elegiveis"].items()})
    if "unidades_excluidas" in esperado: checar("unidades_excluidas", excluidas, sorted(esperado["unidades_excluidas"]))
    if "registros_divida_elegivel" in esperado: checar("registros_divida_elegivel", len(elegiveis), esperado["registros_divida_elegivel"])
    for campo in ("boletos_que_nao_entram", "boletos_ainda_nao_elegiveis"):
        if campo in esperado:
            fora = sorted(boletos[r.boleto_id].identificador for r in resultados if r.acao != "incluir")
            checar(campo, fora, sorted(esperado[campo]))
    if "cadastros_sem_divida_esperados" in esperado:
        checar("cadastros_sem_divida", sorted(cadastrais), sorted(esperado["cadastros_sem_divida_esperados"]))
    if "avisos_cpf_ausente" in esperado: checar("avisos_cpf_ausente", cpf, esperado["avisos_cpf_ausente"])
    for numero in esperado.get("boletos_continuados", {}):
        encontrados = [b for b in lote.boletos if b.identificador == numero]
        paginas = sorted({o.pagina for b in encontrados for o in b.origens})
        checar(f"continuidade_{numero}", len(encontrados) == 1 and len(paginas) > 1, True)
    return verificacoes


def conferir_resumo_xlsx(caminho, lote):
    livro = load_workbook(caminho, read_only=True, data_only=False)
    try:
        linhas = list(livro["Resumo"].iter_rows(values_only=True))
        if tuple(linhas[0]) != ("Torre", "Unidade", "Boleto", "Vencimento", "Competencia", "Subtotal_Boleto"):
            return [{"codigo": "RESUMO_CABECALHO_DIVERGENTE"}]
        unidades = {u.id: u for u in lote.unidades}
        atual = {(unidades[b.unidade_id].bloco_original, unidades[b.unidade_id].unidade_original, b.identificador): b for b in lote.boletos}
        divergencias, vistos = [], set()
        for indice, row in enumerate(linhas[1:], 2):
            chave = (str(row[0]), str(row[1]).zfill(4), str(row[2]))
            boleto = atual.get(chave)
            if boleto is None or chave in vistos:
                divergencias.append({"linha": indice, "codigo": "RESUMO_BOLETO_INEXISTENTE_OU_DUPLICADO"})
                continue
            vistos.add(chave)
            if boleto.composicao.total_original != Decimal(str(row[5])):
                divergencias.append({"linha": indice, "boleto": boleto.identificador, "codigo": "RESUMO_VALOR_DIVERGENTE"})
            vencimento = _normalizar(row[3])
            if isinstance(vencimento, str) and len(vencimento) == 10 and vencimento[2:3] == "/" and vencimento[5:6] == "/":
                vencimento = vencimento[6:] + "-" + vencimento[3:5] + "-" + vencimento[:2]
            if vencimento != boleto.vencimento.isoformat():
                divergencias.append({"linha": indice, "boleto": boleto.identificador, "codigo": "RESUMO_VENCIMENTO_DIVERGENTE"})
            competencia = str(row[4])
            if len(competencia) == 7 and competencia[2] == "/":
                competencia = competencia[3:] + "-" + competencia[:2]
            if competencia != boleto.competencia:
                divergencias.append({"linha": indice, "boleto": boleto.identificador, "codigo": "RESUMO_COMPETENCIA_DIVERGENTE"})
        if vistos != set(atual): divergencias.append({"codigo": "RESUMO_BOLETOS_AUSENTES"})
        return divergencias
    finally:
        livro.close()
