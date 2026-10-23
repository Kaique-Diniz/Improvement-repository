"""Comparação diagnóstica por vínculos explícitos. XLSX só é aberto para leitura."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.canonical import Origem
from conversor.domain.documents import resolver_documento
from conversor.domain.simulation_comparison import (ComparacaoPrivada, DivergenciaSimulacao, MapeamentoReferencia)
from conversor.domain.template import COLUNAS, Template
from .billing_authority import ler_protegido
from .private_simulation_json import conferir_local_privado, seguro


def _hash(valor):
    return sha256(bytes_canonicos({'valor': str(valor) if valor is not None else None})).hexdigest()


def _data(valor):
    if isinstance(valor, datetime):
        return valor.date() if valor.time().isoformat() == '00:00:00' else None
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        for formato in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(valor, formato).date()
            except ValueError:
                pass
    return None


@seguro
def comparar_referencia(*, id_, execucao, pacote, mapeamento, template: Template):
    mapeamento = MapeamentoReferencia.model_validate(mapeamento.model_dump(warnings=False))
    template = Template.model_validate(template.model_dump(warnings=False))
    if (execucao.pacote_id, execucao.pacote_hash) != (pacote.id, hash_modelo(pacote)):
        raise ErroAplicacao('COMPARACAO_DE_OUTRO_PACOTE')
    fonte = next((f for f in pacote.fontes if f.arquivo_id == mapeamento.referencia_id), None)
    if fonte is None or fonte.papel != 'referencia' or fonte.sha256 != mapeamento.referencia_hash:
        raise ErroAplicacao('REFERENCIA_NAO_VINCULADA_AO_PACOTE')
    conteudo = ler_protegido(conferir_local_privado(fonte.caminho, arquivo=True))
    if sha256(conteudo).hexdigest() != fonte.sha256 or len(conteudo) != fonte.tamanho:
        raise ErroAplicacao('REFERENCIA_ALTERADA_OU_PARCIAL')
    try:
        livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=False, keep_links=False)
    except Exception:
        raise ErroAplicacao('XLSX_DE_REFERENCIA_INVALIDO') from None
    divergencias = []
    boletos = {b.id: b for b in pacote.entrada.lote.boletos}
    unidades = {u.id: u for u in pacote.entrada.lote.unidades}
    pessoas = {p.id: p for p in pacote.entrada.lote.pessoas}
    decisoes = {d.boleto_id: d for d in execucao.relatorio.boletos}

    def adicionar(categoria, codigo, *, v=None, linha=None, coluna=None, esperado=None, observado=None):
        origens = tuple(o for b in (v.boletos_ids if v else ()) for o in boletos[b].origens)
        linha = v.linha if v else linha
        ref = Origem(arquivo_id=fonte.arquivo_id, sha256=fonte.sha256, leitor_versao='comparador-4.3A.0',
                     linha=linha, identificador=f'linha_{linha}' if linha else 'cabecalho')
        divergencias.append(DivergenciaSimulacao(categoria=categoria, motivo_codigo=codigo, linha=linha,
            coluna=coluna, unidade_id=v.unidade_id if v else None, boletos_ids=v.boletos_ids if v else (),
            esperado_hash=_hash(esperado) if esperado is not None else None,
            observado_hash=_hash(observado) if observado is not None else None, origens=origens + (ref,)))

    try:
        if template.nome_aba not in livro.sheetnames:
            raise ErroAplicacao('ABA_UNIVERSAL_AUSENTE_NA_REFERENCIA')
        aba = livro[template.nome_aba]
        cabecalhos = tuple(c.value for c in next(aba.iter_rows(min_row=1, max_row=1)))
        if aba.max_column != 30 or len(cabecalhos) != 30:
            raise ErroAplicacao('REFERENCIA_FORA_DAS_30_COLUNAS')
        if cabecalhos != template.cabecalhos_fisicos:
            # Única variação conhecida: espaço final físico em AA; não renomear CPF.
            if any(c != esperado and not (i == 26 and c in (COLUNAS[26], COLUNAS[26] + ' '))
                   for i, (c, esperado) in enumerate(zip(cabecalhos, template.cabecalhos_fisicos))):
                raise ErroAplicacao('CABECALHOS_DE_REFERENCIA_INCOMPATIVEIS')
            adicionar('formatacao', 'ESPACO_FISICO_DO_CABECALHO', linha=1, coluna=COLUNAS[26])
        linhas = {i: tuple(c for c in row) for i, row in enumerate(aba.iter_rows(min_row=2), 2)
                  if any(c.value is not None and c.value != '' for c in row)}
        vinculadas = {v.linha for v in mapeamento.vinculos}
        if not vinculadas <= linhas.keys():
            raise ErroAplicacao('VINCULO_DE_LINHA_INEXISTENTE')
        for linha in sorted(linhas.keys() - vinculadas):
            adicionar('nao_avaliavel', 'LINHA_SEM_IDENTIDADE_REVISADA', linha=linha)
        cobertura = vinculadas == linhas.keys()
        for v in sorted(mapeamento.vinculos, key=lambda x: x.linha):
            if v.unidade_id not in unidades or any(b not in boletos or boletos[b].unidade_id != v.unidade_id for b in v.boletos_ids):
                raise ErroAplicacao('VINCULO_DE_OUTRA_UNIDADE_OU_BOLETO')
            if v.pessoa_id is not None and (v.pessoa_id not in pessoas or pessoas[v.pessoa_id].unidade_id != v.unidade_id):
                raise ErroAplicacao('VINCULO_DE_OUTRO_TITULAR')
            row = linhas[v.linha]
            formulas = {i for i, c in enumerate(row) if c.data_type == 'f'}
            for i in sorted(formulas):
                adicionar('nao_avaliavel', 'FORMULA_NAO_EXECUTADA', v=v, coluna=COLUNAS[i])
            if v.tipo == 'divida':
                for b in v.boletos_ids:
                    if b not in decisoes:
                        raise ErroAplicacao('DECISAO_DO_BOLETO_AUSENTE')
                    if decisoes[b].situacao != 'elegivel_na_simulacao':
                        adicionar('regras', 'REFERENCIA_COM_DIVIDA_E_SIMULACAO_RETIDA', v=v,
                                  esperado='divida', observado=decisoes[b].situacao)
                valores = {b: boletos[b] for b in v.boletos_ids}
                datas = {b.vencimento for b in valores.values()}
                if len(datas) != 1:
                    adicionar('nao_avaliavel', 'AGRUPAMENTO_COM_VENCIMENTOS_DISTINTOS', v=v, coluna='VENCIMENTO')
                elif 28 not in formulas:
                    previsto = next(iter(datas)); observado = row[28].value
                    if _data(observado) != previsto:
                        adicionar('dados', 'VENCIMENTO_DIVERGENTE_OU_NAO_VERIFICAVEL', v=v, coluna='VENCIMENTO', esperado=previsto, observado=observado)
                    elif not isinstance(observado, (date, datetime)) or row[28].number_format not in ('dd/mm/yyyy', 'DD/MM/YYYY'):
                        adicionar('formatacao', 'REPRESENTACAO_DA_DATA', v=v, coluna='VENCIMENTO')
                if 29 not in formulas:
                    previsto = sum((b.composicao.total_original for b in valores.values()), Decimal('0.00'))
                    observado = row[29].value
                    try:
                        numero = Decimal(str(observado)) if not isinstance(observado, bool) else None
                    except InvalidOperation:
                        numero = None
                    if numero is None or not numero.is_finite() or numero != previsto:
                        adicionar('dados', 'VALOR_ORIGINAL_DIFERE_DA_REFERENCIA_SEM_ATRIBUIR_CAUSA', v=v, coluna='VL_PARCELA', esperado=previsto, observado=observado)
                    elif isinstance(observado, str):
                        adicionar('formatacao', 'VALOR_MONETARIO_COMO_TEXTO', v=v, coluna='VL_PARCELA')
            elif any(row[i].value is not None and row[i].value != '' for i in range(24, 30)):
                adicionar('dados', 'LINHA_CADASTRAL_CONTEM_CAMPOS_DE_DIVIDA', v=v)
            if v.pessoa_id is None:
                adicionar('nao_avaliavel', 'TITULAR_NAO_VINCULADO_PARA_COMPARACAO', v=v)
                continue
            pessoa = pessoas[v.pessoa_id]
            resolucao = resolver_documento(pessoa)
            if resolucao.bloqueante:
                adicionar('nao_avaliavel', 'DOCUMENTO_OU_TITULAR_EXIGE_REVISAO', v=v, coluna='CPF')
            else:
                esperado = resolucao.valor
                observado = row[2].value
                if 2 not in formulas:
                    if observado is not None and not isinstance(observado, str):
                        adicionar('formatacao', 'DOCUMENTO_ARMAZENADO_COMO_NUMERO', v=v, coluna='CPF')
                    texto = '' if observado is None else str(observado)
                    # Diagnostica perda de zero apenas com documento canônico válido já associado.
                    zeros = (esperado.startswith('0') and isinstance(observado, (int, float))
                             and not isinstance(observado, bool) and Decimal(str(observado)) == Decimal(esperado))
                    if texto != esperado:
                        adicionar('formatacao' if zeros else 'dados', 'ZEROS_INICIAIS_PERDIDOS' if zeros else 'DOCUMENTO_DIVERGENTE',
                                  v=v, coluna='CPF', esperado=esperado, observado=observado)
            contato = pessoa.contato
            end = contato.endereco
            campos = {3: pessoa.nome, 4: end.logradouro, 5: end.numero, 6: end.complemento, 7: end.cep,
                      8: end.bairro, 9: end.cidade, 10: end.uf}
            for i in range(5):
                tel = contato.telefones[i] if i < len(contato.telefones) else None
                campos[11 + 2 * i] = tel.ddd if tel else ''
                campos[12 + 2 * i] = tel.numero if tel else ''
            for i in range(3):
                campos[21 + i] = contato.emails[i] if i < len(contato.emails) else ''
            for i, esperado in campos.items():
                if i in formulas:
                    continue
                observado = row[i].value
                if ('' if observado is None else str(observado)) != esperado:
                    mesmo_numero = (esperado.isdigit() and isinstance(observado, (int, float))
                        and not isinstance(observado, bool) and Decimal(esperado) == Decimal(str(observado)))
                    adicionar('formatacao' if mesmo_numero else 'dados',
                              'REPRESENTACAO_NUMERICA_DE_CAMPO_TEXTUAL' if mesmo_numero else 'CAMPO_CADASTRAL_DIVERGENTE',
                              v=v, coluna=COLUNAS[i], esperado=esperado, observado=observado)
                elif observado is not None and not isinstance(observado, str):
                    adicionar('formatacao', 'CAMPO_CADASTRAL_NAO_TEXTUAL', v=v, coluna=COLUNAS[i])
        referenciados = {b for v in mapeamento.vinculos for b in v.boletos_ids}
        for b, decisao in sorted(decisoes.items()):
            if b not in boletos:
                raise ErroAplicacao('DECISAO_SEM_BOLETO_CANONICO')
            if b not in referenciados and decisao.situacao == 'elegivel_na_simulacao':
                divergencias.append(DivergenciaSimulacao(categoria='regras' if cobertura else 'nao_avaliavel',
                    motivo_codigo='ELEGIVEL_SEM_DIVIDA_DE_REFERENCIA' if cobertura else 'AUSENCIA_NA_REFERENCIA_NAO_COMPROVADA',
                    unidade_id=decisao.unidade_id, boletos_ids=(b,), origens=boletos[b].origens))
        return ComparacaoPrivada(id=id_, condominio_id=execucao.condominio_id, ambiente=execucao.ambiente,
            execucao_id=execucao.id, execucao_hash=hash_modelo(execucao), mapeamento=mapeamento,
            comparador_hash=sha256(Path(__file__).read_bytes()).hexdigest(), template=template,
            divergencias=tuple(divergencias), colunas=COLUNAS,
            colunas_nao_avaliadas=COLUNAS[:2] + COLUNAS[24:28], cobertura_referencia_completa=cobertura)
    except ErroAplicacao:
        raise
    except Exception:
        raise ErroAplicacao('LEITURA_DA_REFERENCIA_FALHOU') from None
    finally:
        livro.close()


class ComparadorReferenciaXLSX:
    comparar = staticmethod(comparar_referencia)
