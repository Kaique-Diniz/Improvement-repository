"""Delimita destino por referência explícita + unidade/recibo/nome comprovados.

Não usa filename, prefixo, endereço ou código genérico como prova de torre.
Não importa dados pessoais do histórico. Falta de prova retém somente a unidade.
"""
from hashlib import sha256
from io import BytesIO
from decimal import Decimal, InvalidOperation
from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.canonical import Origem
from conversor.domain.document_scope import EscopoDestinoDiagnostico, UnidadeEscopoDestino
from conversor.domain.recognition import normalizar_assinatura
from conversor.domain.template import COLUNAS
from conversor.export.historical_comparison import data
from conversor.readers.text_support import ErroLeitura


def delimitar_escopo_destino(lote, *, referencia, perfil_saida, perfil, codigo_origem):
    membros = {u.id: {'unidade_id': u.id, 'chave_original': u.chave_normalizada,
        'estado': 'nao_comprovado', 'recibos_comprovantes': [], 'evidencias': []} for u in lote.unidades}
    motivo = 'REFERENCIA_DE_ESCOPO_NAO_FORNECIDA'
    digest = sha256(referencia).hexdigest() if referencia else None
    if referencia and perfil_saida:
        sonda = SondadorLocal().sondar(referencia, arquivo_id='referencia')
        motivo = 'REFERENCIA_DE_ESCOPO_NAO_AVALIAVEL'
        if sonda.tipo == 'xlsx' and not sonda.bloqueios and sonda.completo:
            w = load_workbook(BytesIO(referencia), read_only=True, data_only=False, keep_links=False)
            try:
                candidatas = [s for s in w if tuple(str(v).strip() for v in next(s.values, ())[:30]) == COLUNAS]
                if len(candidatas) == 1:
                    aba = candidatas[0]
                    pessoas = {p.unidade_id: p for p in lote.pessoas}
                    codigos = {}
                    for u in lote.unidades:
                        try:
                            cedente, complemento = perfil_saida.codificar(u, administradora_id=u.administradora_id)
                        except ErroLeitura:
                            continue
                        codigos.setdefault((cedente, complemento), []).append(u.id)
                    contestadas = set()
                    for n, row in enumerate(aba.iter_rows(min_row=2), 2):
                        if len(row) < 30 or any(c.data_type == 'f' for c in row):
                            continue
                        valores = tuple(c.value for c in row)
                        if (normalizar_assinatura(str(valores[0] or '')) != normalizar_assinatura(perfil_saida.nome_cedente) or
                            not valores[25] or not valores[24]):
                            continue
                        key = (str(valores[1] or ''), str(valores[6] or ''))
                        ids = codigos.get(key, ())
                        if len(ids) != 1 or str(valores[24]) != key[0]:
                            continue
                        uid = ids[0]
                        if normalizar_assinatura(str(valores[3] or '')) != normalizar_assinatura(pessoas[uid].nome):
                            continue
                        try:
                            valor = Decimal(str(valores[29])) if not isinstance(valores[29], bool) else None
                        except InvalidOperation:
                            continue
                        if valor is None or not valor.is_finite():
                            continue
                        candidatos = [b for b in lote.boletos if b.unidade_id == uid and
                            b.vencimento == data(valores[28]) and b.composicao.total_original == valor]
                        if len(candidatos) != 1:
                            continue
                        membro = membros[uid]
                        if str(valores[25]) != perfil_saida.produto:
                            contestadas.add(uid)
                        else:
                            membro['estado'] = 'comprovado_documentalmente'
                            membro['motivo_codigo'] = 'UNIDADE_NOME_RECIBO_E_DESTINO_DOCUMENTALMENTE_VINCULADOS'
                        if candidatos[0].id not in membro['recibos_comprovantes']:
                            membro['recibos_comprovantes'].append(candidatos[0].id)
                        membro['evidencias'].append(Origem(arquivo_id='referencia', sha256=digest,
                            leitor_versao='vinculo_destino_template@1', linha=n,
                            identificador=f'xlsx_aba{w.sheetnames.index(aba.title)+1}_r{n}_B_G_Y_Z_AC_AD'))
                    for uid in contestadas:
                        membros[uid].update(estado='nao_comprovado', motivo_codigo='REFERENCIA_DESTINO_CONFLITANTE')
                    motivo = 'CONFRONTO_DOCUMENTAL_REALIZADO_SEM_PRESUMIR_COBERTURA_TOTAL'
            finally:
                w.close()
    return EscopoDestinoDiagnostico(administradora_id=perfil['administradora_id'],
        condominio_candidato_id=perfil['condominio_id'], codigo_destino=perfil['codigo_easycollector'],
        codigo_origem=codigo_origem, perfil_saida_sha256=hash_modelo(perfil_saida) if perfil_saida else None,
        fonte_financeira_sha256=lote.unidades[0].origem.sha256,
        referencia_sha256=digest, motivo_referencia=motivo,
        unidades=tuple(UnidadeEscopoDestino.model_validate(m) for m in membros.values()))
