"""Inventário exato e verificável, sem inferir fatos ausentes nem ler texto de régua."""
from conversor.domain.billing_rules import hash_modelo
from conversor.domain.canonical import Origem
from conversor.domain.private_simulation import (CampoAusente, InventarioEntrada, RegistroInventariado)
from .billing_evaluation import normalizar_entrada, ocorrencias_da_entrada, ocorrencias_aplicaveis
from .ports import ErroAplicacao


def consolidar_ocorrencias_externas(colecoes):
    """Repetição idêntica é idempotente; mesmo ID com outra evidência é impedimento."""
    mapa = {}
    for colecao in colecoes:
        for ocorrencia in colecao:
            if ocorrencia.id in mapa and mapa[ocorrencia.id] != ocorrencia:
                raise ErroAplicacao('IDENTIDADE_DE_OCORRENCIA_EXTERNA_CONFLITANTE')
            mapa[ocorrencia.id] = ocorrencia
    return tuple(mapa[k] for k in sorted(mapa))


def origens_do_modelo(modelo):
    mapa = {}

    def visitar(valor):
        if isinstance(valor, dict):
            if {'arquivo_id', 'sha256', 'leitor_versao', 'identificador'} <= valor.keys():
                origem = Origem.model_validate(valor)
                mapa[hash_modelo(origem)] = origem
            for filho in valor.values():
                visitar(filho)
        elif isinstance(valor, (list, tuple)):
            for filho in valor:
                visitar(filho)

    visitar(modelo.model_dump(mode='json'))
    return tuple(mapa[k] for k in sorted(mapa))


def inventariar(entrada, catalogos, reconciliacao=None):
    """Candidato para revisão humana; gerar este DTO NÃO atesta completude."""
    entrada = normalizar_entrada(entrada)
    registros, ausencias, origens = [], [], {}
    colecoes = [('unidade', entrada.lote.unidades), ('boleto', entrada.lote.boletos),
                ('pessoa', entrada.lote.pessoas), ('fato', entrada.fatos),
                ('ocorrencia', entrada.ocorrencias_anteriores), ('cobertura', entrada.coberturas_apontamentos),
                ('ressalva', entrada.lote.ressalvas), ('catalogo', catalogos)]

    def faltas(dados, registro_id, caminho=''):
        if isinstance(dados, dict):
            for chave, valor in sorted(dados.items()):
                campo = f'{caminho}.{chave}' if caminho else chave
                if valor is None or valor == '' or valor == []:
                    ausencias.append(CampoAusente(registro_id=registro_id, campo=campo))
                else:
                    faltas(valor, registro_id, campo)
        elif isinstance(dados, list):
            for i, valor in enumerate(dados):
                faltas(valor, registro_id, f'{caminho}[{i}]')

    for tipo, objetos in colecoes:
        for obj in objetos:
            digest = hash_modelo(obj)
            id_ = getattr(obj, 'id', None) or digest
            registros.append(RegistroInventariado(tipo=tipo, id=id_, sha256=digest))
            if tipo in ('unidade', 'boleto', 'pessoa', 'fato'):
                faltas(obj.model_dump(mode='json'), id_)
            for origem in origens_do_modelo(obj):
                origens[hash_modelo(origem)] = origem
    inventario = InventarioEntrada(hash_entrada=hash_modelo(entrada),
        registros=tuple(sorted(registros, key=lambda r: (r.tipo, r.id, r.sha256))),
        apontamentos=sum(len(b.apontamentos) for b in entrada.lote.boletos),
        itens_composicao=sum(len(b.composicao.itens) for b in entrada.lote.boletos),
        origens=tuple(origens[k] for k in sorted(origens)),
        campos_ausentes=tuple(sorted(ausencias, key=lambda a: (a.registro_id, a.campo))))
    if reconciliacao is None:
        return inventario
    from conversor.domain.audit_identity import InventarioReconciliado, origem_historico
    for fonte in reconciliacao.fontes:
        origem = origem_historico(fonte)
        origens[hash_modelo(origem)] = origem
    return InventarioReconciliado(**(inventario.model_dump() | {
        'origens': tuple(origens[k] for k in sorted(origens)), 'reconciliacao_hash': hash_modelo(reconciliacao)}))


def conferir_pacote(pacote):
    entrada = normalizar_entrada(pacote.entrada)
    if not entrada.lote.unidades or {u.condominio_id for u in entrada.lote.unidades} != {pacote.condominio_id}:
        raise ErroAplicacao('PACOTE_DE_OUTRO_CONDOMINIO_OU_VAZIO')
    if entrada != pacote.entrada:
        raise ErroAplicacao('ENTRADA_FORA_DA_ORDEM_CANONICA')
    unidades = {u.id for u in entrada.lote.unidades}
    boletos = {b.id: b for b in entrada.lote.boletos}
    pessoas = {p.id for p in entrada.lote.pessoas}
    if len(unidades | boletos.keys() | pessoas) != len(unidades) + len(boletos) + len(pessoas):
        raise ErroAplicacao('IDENTIDADES_AMBIGUAS_NO_PACOTE')
    for fato in entrada.fatos:
        if fato.condominio_id != pacote.condominio_id or fato.unidade_id not in unidades:
            raise ErroAplicacao('FATO_FORA_DO_PACOTE')
        if fato.boleto_id is not None and (fato.boleto_id not in boletos or boletos[fato.boleto_id].unidade_id != fato.unidade_id):
            raise ErroAplicacao('FATO_FORA_DO_BOLETO')
    for cobertura in entrada.coberturas_apontamentos:
        boleto = boletos.get(cobertura.boleto_id)
        if boleto is None or not {(o.arquivo_id, o.sha256) for o in cobertura.origens} <= {
                (o.arquivo_id, o.sha256) for o in boleto.origens}:
            raise ErroAplicacao('COBERTURA_FORA_DO_BOLETO')
    reconciliacao = getattr(pacote, 'reconciliacao', None)
    if reconciliacao is not None:
        from conversor.domain.audit_identity import ReconciliacaoOcorrencias
        reconciliacao = ReconciliacaoOcorrencias.model_validate(reconciliacao.model_dump(warnings=False))
        if (reconciliacao.condominio_id, reconciliacao.ambiente) != (pacote.condominio_id, pacote.ambiente):
            raise ErroAplicacao('RECONCILIACAO_DE_OUTRO_CONTEXTO')
        if reconciliacao.ocorrencias() != entrada.ocorrencias_anteriores:
            raise ErroAplicacao('ENTRADA_OMITE_OU_ALTERA_OCORRENCIAS_RECONCILIADAS')
    if inventariar(entrada, pacote.catalogos, reconciliacao) != pacote.inventario:
        raise ErroAplicacao('INVENTARIO_INCOMPLETO_OU_DIVERGENTE')
    esperadas = {o.id: o for o in entrada.ocorrencias_anteriores}
    carregadas = {}
    for catalogo in pacote.catalogos:
        for o in catalogo.ocorrencias:
            if o.id in carregadas and carregadas[o.id] != o:
                raise ErroAplicacao('CATALOGOS_COM_OCORRENCIAS_CONTRADITORIAS')
            if o.bloqueante and o.origem is None and not o.evidencias_documentais:
                raise ErroAplicacao('BLOQUEIO_EXTERNO_SEM_FONTE')
            carregadas[o.id] = o
    if esperadas != carregadas:
        raise ErroAplicacao('OCORRENCIAS_EXTERNAS_AUSENTES_OU_PARCIAIS')
    fontes = {f.arquivo_id: f for f in pacote.fontes}
    for origem in pacote.inventario.origens:
        fonte = fontes.get(origem.arquivo_id)
        if fonte is None or fonte.sha256 != origem.sha256:
            raise ErroAplicacao('ORIGEM_SEM_FONTE_INTEGRA_NO_INVENTARIO')
    # Nenhuma fonte entra acidentalmente no pacote; até a referência precisa de origem declarada.
    if set(fontes) != {o.arquivo_id for o in pacote.inventario.origens}:
        raise ErroAplicacao('FONTE_SEM_VINCULO_COM_INVENTARIO')


def conferir_resultado_preservado(execucao, pacote):
    """Checagens de cobertura e segurança, sem recalcular decisões financeiras."""
    relatorio = execucao.relatorio
    if relatorio.solicitacao.data_ref != pacote.atesto.data_ref:
        raise ErroAplicacao('RELATORIO_FORA_DA_DATA_REF_ATESTADA')
    if relatorio.hash_entrada != pacote.inventario.hash_entrada:
        raise ErroAplicacao('RELATORIO_DE_OUTRA_ENTRADA')
    boletos = {b.id: b for b in pacote.entrada.lote.boletos}
    unidades = {u.id: u for u in pacote.entrada.lote.unidades}
    if (len(relatorio.boletos) != len(boletos) or {d.boleto_id for d in relatorio.boletos} != set(boletos) or
            len(relatorio.unidades) != len(unidades) or {u.unidade_id for u in relatorio.unidades} != set(unidades)):
        raise ErroAplicacao('RELATORIO_COM_REGISTROS_OMITIDOS_OU_DUPLICADOS')
    ocorrencias = ocorrencias_da_entrada(pacote.entrada, relatorio.solicitacao.processamento_id)
    if (relatorio.ocorrencias_anteriores != ocorrencias or relatorio.ressalvas_origem != pacote.entrada.lote.ressalvas or
            relatorio.fatos_recebidos != pacote.entrada.fatos or relatorio.coberturas_recebidas != pacote.entrada.coberturas_apontamentos):
        raise ErroAplicacao('RELATORIO_OMITE_EVIDENCIAS_OU_IMPEDIMENTOS')
    for decisao in relatorio.boletos:
        boleto = boletos[decisao.boleto_id]
        if decisao.unidade_id != boleto.unidade_id:
            raise ErroAplicacao('RELATORIO_CRUZA_OUTRA_UNIDADE')
        locais = ocorrencias_aplicaveis(ocorrencias, unidades[boleto.unidade_id], boleto, pacote.entrada.lote)
        if decisao.ocorrencias_preservadas != locais or any(o.bloqueante for o in locais) and decisao.situacao != 'bloqueado':
            raise ErroAplicacao('RELATORIO_CONTORNA_BLOQUEIOS_CRITICOS')
