"""Classifica motivos comprovados sem alterar a retenção ou deduzir por totais."""
CONFLITOS_DOCUMENTAIS = frozenset((
    'DOCUMENTOS_CONFLITANTES','DOCUMENTOS_VALIDOS_CONFLITANTES',
    'BBZ_DOCUMENTOS_CONFLITANTES_ASSOCIACAO_RETIDA',
    'BBZ_DOCUMENTO_HISTORICO_CONFLITANTE_ASSOCIACAO_RETIDA','BBZ_CONFLITO_DOCUMENTAL_PERSISTENTE'))


def classificar_retencoes(*, pendencias_persistentes, cadastro, escopo):
    por_unidade = {}
    def registrar(uid,motivo):por_unidade.setdefault(uid,set()).add(motivo)
    if escopo:
        for m in escopo.unidades:
            if m.estado != 'comprovado_documentalmente':registrar(m.unidade_id,'PERTENCIMENTO_NAO_COMPROVADO')
    for uid, pendencias in pendencias_persistentes.items():
        for p in pendencias:
            registrar(uid,'CONFLITO_DOCUMENTAL' if p.codigo in CONFLITOS_DOCUMENTAIS else 'OUTRA_RESTRICAO_DOCUMENTAL')
    if cadastro:
        for uid,info in cadastro['unidades'].items():
            if not {'documentos','telefones','emails'}.intersection(info.get('dados_retidos',())):continue
            motivos=set(info.get('motivos',()))
            if info.get('estado')=='escopo_nao_comprovado' or 'DESTINO_TORRE_NAO_COMPROVADO' in motivos:
                registrar(uid,'PERTENCIMENTO_NAO_COMPROVADO')
            if motivos.intersection(CONFLITOS_DOCUMENTAIS) or info.get('conflitos_referencia') or info.get('conflitos_persistentes'):
                registrar(uid,'CONFLITO_DOCUMENTAL')
            outros=motivos-CONFLITOS_DOCUMENTAIS-{'DESTINO_TORRE_NAO_COMPROVADO'}
            if outros:registrar(uid,'OUTRA_RESTRICAO_CADASTRAL')
            if uid not in por_unidade:registrar(uid,'MOTIVO_NAO_CLASSIFICADO')
    return {uid:tuple(sorted(motivos))for uid,motivos in sorted(por_unidade.items())}
