"""Natureza da obrigação por evidência de todos os componentes, sem seleção financeira.

Competência só é lida no histórico principal; medições e índices de rateio não
definem competência da cota. A política é independente de condomínio e recibo.
"""
from hashlib import sha256
import json
import re
import unicodedata

from conversor.domain.canonical import LoteCanonico, RessalvaLeitura
from conversor.domain.debt_description import (
    ComponenteInterpretado, DescricaoRecibo, PoliticaDescricoes, RegraHistorico,
)

MESES = {m: f'{i:02d}' for i, nomes in enumerate((
    ('JAN', 'JANEIRO'), ('FEV', 'FEVEREIRO'), ('MAR', 'MARCO'),
    ('ABR', 'ABRIL'), ('MAI', 'MAIO'), ('JUN', 'JUNHO'),
    ('JUL', 'JULHO'), ('AGO', 'AGOSTO'), ('SET', 'SETEMBRO'),
    ('OUT', 'OUTUBRO'), ('NOV', 'NOVEMBRO'), ('DEZ', 'DEZEMBRO'),
), 1) for m in nomes}
MES = r'(?:0?[1-9]|1[0-2]|' + '|'.join(MESES) + ')'
# Grafia de consumos/rateios, sem resolver o século e sem definir competência.
PERIODO = MES + r'/?(?:[0-9]{4}|[0-9]{2})'
COMPETENCIA = r'(?P<mes>' + MES + r')/(?P<ano>(?!0000)[0-9]{4})'


def _principal(id, padrao, natureza, rotulo, competencia=False):
    return RegraHistorico(id=id, padrao=padrao, papel='principal',
        natureza=natureza, rotulo=rotulo, natureza_competencia=competencia)


def _acessorio(id, padrao, *, ajuste=False):
    return RegraHistorico(id=id, padrao=padrao, papel='ajuste' if ajuste else 'acessorio',
        naturezas_compativeis=('cota_condominial',))


POLITICA_BBZ = PoliticaDescricoes(id='descricao_obrigacao_bbz', versao='1.1.0',
    namespace_formato='bbz_inadimplencia_xlsx_v1', regras=(
        _principal('cota_documental', r'COTA CONDOMINIAL(?: (?:COMPETENCIA:? )?' + COMPETENCIA + r')?',
                   'cota_condominial', 'COTA', True),
        _principal('reembolso_sinistro_documental', r'REEMBOLSO(?: DE)? SINISTRO',
                   'reembolso_sinistro', 'REEMBOLSO SINISTRO'),
        _principal('extraordinaria_documental', r'COBRANCA EXTRAORDINARIA',
                   'cobranca_extraordinaria', 'COBRANÇA EXTRAORDINÁRIA'),
        _principal('locacao_espaco_documental', r'LOCACAO DE ESPACO(?: [0-9]{2}/[0-9]{2}/[0-9]{4})?',
                   'locacao_espaco', 'LOCAÇÃO DE ESPAÇO'),
        _acessorio('fundo_reserva', r'FUNDO DE RESERVA(?: ' + PERIODO + r')?'),
        _acessorio('consumo_energia', r'CONSUMO ENERGIA'),
        _acessorio('agua', r'AGUA (?:RATEIO|AREA COMUM|FRIA|QUENTE) ' + PERIODO +
                   r'(?: [0-9]+(?:[.,][0-9]+)? M3)?'),
        _acessorio('gas', r'GAS(?: (?:SISTEMA|PISCINA|INDIVIDUAL))?(?: ' + PERIODO + r')?'),
        _acessorio('recomposicao_saldo', r'RECOMPOSICAO SALDO [0-9]+/[0-9]+'),
        _acessorio('projeto_seguranca', r'PROJETO SEGURANCA PC\. [0-9]+/[0-9]+'),
        _acessorio('rateio_fachada', r'FACHADA PC\. [0-9]+/[0-9]+'),
        _acessorio('reforma_espaco_pet', r'REFORMA ESPACO PET -PC UNICA'),
        _acessorio('desconto_cota', r'DESCONTO COTA CONDOMINIAL', ajuste=True),
        _acessorio('desconto_fundo', r'DESCONTO FUNDO DE RESERVA', ajuste=True),
    ))

# Variação documental da família: adotada somente por perfil explícito.
# A política histórica permanece intacta e reproduzível.
POLITICA_BBZ_CONDOMINIO = PoliticaDescricoes(id='descricao_obrigacao_bbz_condominio', versao='1.0.0',
    namespace_formato=POLITICA_BBZ.namespace_formato, regras=POLITICA_BBZ.regras + (
        _principal('condominio_documental', r'CONDOMINIO ' + COMPETENCIA,
                   'cota_condominial', 'COTA', True),
        _principal('cond_abreviado_documental', r'COND ' + COMPETENCIA,
                   'cota_condominial', 'COTA', True),))
# Assinaturas documentais estritas: descrevem natureza, sem eleger ano/século
# para os períodos brutos. A versão anterior continua disponível para reprodução.
POLITICA_BBZ_CONDOMINIO_V11 = PoliticaDescricoes(id=POLITICA_BBZ_CONDOMINIO.id, versao='1.1.0',
    namespace_formato=POLITICA_BBZ.namespace_formato, regras=POLITICA_BBZ_CONDOMINIO.regras + (
        _principal('locacao_salas_documental', r'LOCACAO(?: DE)? SALAS(?: (?:LOCACAO )?' + PERIODO + r')?',
                   'locacao_salas','LOCAÇÃO DE SALAS'),
        _principal('feira_gastronomica_documental',
                   r'FEIRA GASTRONOMICA (?:0?[1-9]|1[0-2])/(?!0000)[0-9]{4}(?: FEIRA - ' + PERIODO + r')?',
                   'feira_gastronomica','FEIRA GASTRONÔMICA'),
        _principal('esportes_atividade_documental',
                   r'ESPORTES (?:REF\. (?:0?[1-9]|1[0-2])/(?!0000)[0-9]{4} (?:BOXE|FIT DANCE)|AULAS(?:- [0-9]+ ALUNOS)? ' + PERIODO + r')',
                   'esportes','ESPORTES'),))
POLITICAS_BBZ = {p.id+'@'+p.versao:p for p in (POLITICA_BBZ,POLITICA_BBZ_CONDOMINIO,POLITICA_BBZ_CONDOMINIO_V11)}


def normalizar_historico(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', texto.upper())
                           if not unicodedata.combining(c)).split())


def _metadados(lote, boleto):
    """Somente metadados produzidos pelo leitor para este recibo e mesma origem."""
    result = {}
    for r in lote.ressalvas:
        if r.codigo != 'BBZ_RECIBO_RECONCILIADO' or r.registro_id != boleto.id:
            continue
        if not all((o.arquivo_id, o.sha256, o.leitor_versao) ==
                   (boleto.origens[0].arquivo_id, boleto.origens[0].sha256, boleto.origens[0].leitor_versao)
                   for o in r.origens):
            continue
        for raw in r.valores_originais:
            dados = json.loads(raw)
            for item in dados['componentes']:
                result[item['linha']] = dict(item, aba=dados['aba'])
    return result


def interpretar_recibo(boleto, *, politica=POLITICA_BBZ, metadados=None):
    metadados = metadados or {}
    digest = sha256(politica.model_dump_json().encode()).hexdigest()
    componentes, regras = [], {}
    for item in boleto.composicao.itens:
        texto = normalizar_historico(item.descricao_original)
        matches = [(r, re.fullmatch(r.padrao, texto)) for r in politica.regras]
        matches = [(r, m) for r, m in matches if m is not None]
        namespace_valido = item.origem.leitor_versao.split('@')[0] == politica.namespace_formato
        if not namespace_valido:
            matches = []
        regra, m = matches[0] if len(matches) == 1 else (None, None)
        competencia = None
        if m and 'mes' in m.groupdict() and m['mes']:
            mes = MESES.get(m['mes'], m['mes'].zfill(2))
            competencia = f'{m["ano"]}-{mes}'
        origem = item.origem
        local = re.fullmatch(r'xlsx_aba1_r([0-9]+)_G', origem.identificador)
        origem_hist = origem.model_copy(update={'identificador': f'xlsx_aba1_r{origem.linha}_E'}) if (
            namespace_valido and local and int(local[1]) == origem.linha) else origem
        meta = metadados.get(origem.linha, {})
        # Conta e aba são auxiliares. Não atribuir metadados de outro histórico.
        if meta.get('historico') != item.descricao_original:
            meta = {}
        origem_conta = origem.model_copy(update={'identificador': f'xlsx_aba1_r{origem.linha}_D'}) if meta else None
        comp = ComponenteInterpretado(codigo=item.codigo, historico_original=item.descricao_original,
            valor_original=item.valor, origem=origem, origem_historico=origem_hist,
            aba=meta.get('aba'), conta=meta.get('conta'), origem_conta=origem_conta,
            resultado='reconhecido' if regra else 'ambiguo' if len(matches) > 1 else 'nao_reconhecido',
            regras_candidatas=tuple(r.id for r, _ in matches), papel=regra.papel if regra else None,
            natureza=regra.natureza if regra else None, competencia=competencia)
        componentes.append(comp)
        if regra:
            regras[item.codigo] = regra
    principais = [c for c in componentes if c.papel == 'principal']
    naturezas = {c.natureza for c in principais}
    competencias = {c.competencia for c in principais if c.competencia}
    if boleto.competencia:
        competencias.add(boleto.competencia)
    alertas = []
    if any(c.resultado != 'reconhecido' for c in componentes):
        alertas.append('BBZ_HISTORICO_NAO_RECONHECIDO_OU_AMBIGUO')
    if len(naturezas) > 1:
        alertas.append('BBZ_NATUREZAS_MISTAS')
    if not principais:
        alertas.append('BBZ_NATUREZA_PRINCIPAL_NAO_COMPROVADA')
    if len(naturezas) == 1 and any(c.papel != 'principal' and c.codigo in regras and
            next(iter(naturezas)) not in regras[c.codigo].naturezas_compativeis for c in componentes):
        alertas.append('BBZ_COMPONENTE_DE_OUTRA_OBRIGACAO')
    if len(competencias) > 1:
        alertas.append('BBZ_COMPETENCIAS_CONFLITANTES')
    if any(c.competencia for c in principais) and any(
            regras[c.codigo].natureza_competencia and not c.competencia for c in principais):
        alertas.append('BBZ_COMPETENCIA_PARCIAL_NOS_PRINCIPAIS')
    cotas = [c for c in principais if c.natureza == 'cota_condominial']
    competencias_cota = {c.competencia for c in cotas if c.competencia}
    prefixo_cota = (r'^(?:COTA CONDOMINIAL|CONDOMINIO|COND)(?:\s|$)' if
        any(r.id=='condominio_documental' for r in politica.regras) else r'^COTA CONDOMINIAL(?:\s|$)')
    cota_inconclusiva = any(c.resultado != 'reconhecido' and
        re.match(prefixo_cota, normalizar_historico(c.historico_original))
        for c in componentes)
    priorizar_cota = (bool(cotas) and len(competencias_cota) == 1 and
        all(c.competencia for c in cotas) and not cota_inconclusiva and
        (boleto.competencia is None or boleto.competencia in competencias_cota))
    if priorizar_cota:
        # A cota comprovada define a apresentação do recibo inteiro. Não excluir
        # nem reclassificar os demais componentes; sua natureza continua auditada.
        alertas = [a for a in alertas if a not in (
            'BBZ_NATUREZAS_MISTAS', 'BBZ_COMPETENCIAS_CONFLITANTES',
            'BBZ_COMPETENCIA_PARCIAL_NOS_PRINCIPAIS')]
        if len(naturezas) > 1:
            alertas.append('BBZ_COTA_PRIORIZADA_NA_DESCRICAO')
    pendente = bool(alertas)
    descricao = f'RECIBO {boleto.identificador}'
    competencia = None
    classificacao = 'mista' if len(naturezas) > 1 else 'indeterminada'
    estado_competencia = 'conflitante' if len(competencias) > 1 else 'ausente'
    if priorizar_cota:
        pendente = False
        classificacao, competencia = 'cota_condominial', next(iter(competencias_cota))
        ano, mes = competencia.split('-')
        descricao, estado_competencia = f'COTA {mes}/{ano}', 'comprovada'
    elif not pendente:
        classificacao = next(iter(naturezas))
        # Rótulos da mesma natureza são iguais por contrato; não eleger um componente.
        descricao, exige_competencia = next(iter({(regras[c.codigo].rotulo,
            regras[c.codigo].natureza_competencia) for c in principais}))
        if exige_competencia:
            competencia = next(iter(competencias)) if competencias else None
            estado_competencia = 'comprovada' if competencia else 'ausente'
            if competencia:
                ano, mes = competencia.split('-')
                descricao += f' {mes}/{ano}'
            else:
                alertas.append('BBZ_COMPETENCIA_AUSENTE')
        else:
            estado_competencia = 'nao_aplicavel'
    if pendente:
        alertas.append('BBZ_CLASSIFICACAO_DESCRICAO_PENDENTE')
    return DescricaoRecibo(condominio_id=boleto.condominio_id, unidade_id=boleto.unidade_id,
        boleto_id=boleto.id, identificador_origem=boleto.identificador, descricao=descricao,
        estado='pendente' if pendente else 'comprovada', classificacao=classificacao,
        competencia=competencia, estado_competencia=estado_competencia,
        competencias_encontradas=tuple(sorted(competencias)), ambigua=pendente,
        justificativa=('Cota condominial explícita com competência única define a descrição principal; todos os demais componentes permanecem preservados.'
                       if priorizar_cota else 'Natureza principal explícita e todos os componentes compatíveis no mesmo recibo.'
                       if not pendente else 'Recibo reúne naturezas principais distintas; descrição neutra, sem escolher um componente.'
                       if len(naturezas) > 1 else 'Evidência insuficiente ou conflitante; descrição neutra, sem alterar a seleção financeira.'),
        alertas=tuple(sorted(alertas)), politica_id=politica.id, politica_versao=politica.versao,
        politica_sha256=digest, componentes=tuple(componentes), origens=boleto.origens)


def interpretar_lote_bbz(lote, *, politica=POLITICA_BBZ):
    """Enriquece competência comprovada em cópia, conservando o lote extraído e o histórico."""
    descricoes, boletos, ressalvas = {}, [], list(lote.ressalvas)
    for b in lote.boletos:
        d = interpretar_recibo(b, politica=politica, metadados=_metadados(lote, b))
        descricoes[b.id] = d
        if d.competencia and b.competencia is None:
            b = b.model_copy(update={'competencia': d.competencia})
            codigo = 'BBZ_COMPETENCIA_DOCUMENTAL_INTERPRETADA'
            evidencia = json.dumps({'competencia': d.competencia, 'politica_versao': d.politica_versao,
                'politica_sha256': d.politica_sha256}, sort_keys=True)
            ressalvas.append(RessalvaLeitura(codigo=codigo, gravidade='informativo', registro_id=b.id,
                origens=tuple(c.origem_historico for c in d.componentes
                              if c.natureza == d.classificacao and c.competencia == d.competencia),
                valores_originais=(evidencia,)))
        for codigo in d.alertas:
            r = RessalvaLeitura(codigo=codigo,
                gravidade='informativo' if codigo == 'BBZ_COTA_PRIORIZADA_NA_DESCRICAO' else 'alerta',
                registro_id=b.id, origens=b.origens,
                valores_originais=(json.dumps({'politica_versao': d.politica_versao,
                    'politica_sha256': d.politica_sha256, 'descricao': d.descricao}, sort_keys=True),))
            if r not in ressalvas:
                ressalvas.append(r)
        boletos.append(b)
    return LoteCanonico.model_validate(lote.model_dump() | {'boletos': tuple(boletos), 'ressalvas': tuple(ressalvas)}), descricoes
