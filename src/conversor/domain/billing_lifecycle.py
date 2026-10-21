"""Máquina de estados dos planos. Não é o motor de avaliação de cobrança."""
from datetime import date

from .billing_rules import AcervoPlanos, ErroPlano, EventoPlano, RegistroPlano, hash_modelo

TRANSICOES = {
    (None, 'criar'): 'rascunho',
    ('rascunho', 'submeter'): 'aguardando_aprovacao',
    ('aguardando_aprovacao', 'rejeitar'): 'rascunho',
    ('aguardando_aprovacao', 'aprovar'): 'aprovado',
    ('aprovado', 'ativar'): 'ativo',
    ('aprovado', 'revogar'): 'revogado',
    ('ativo', 'revogar'): 'revogado',
}


def conferir_acervo(acervo: AcervoPlanos):
    registros = {r.conteudo.id: r for r in acervo.registros}
    if len(registros) != len(acervo.registros):
        raise ErroPlano('PLANO_ID_DUPLICADO')
    versoes = {(r.conteudo.condominio_id, r.conteudo.versao) for r in acervo.registros}
    if len(versoes) != len(acervo.registros):
        raise ErroPlano('VERSAO_DE_PLANO_DUPLICADA')
    for registro in acervo.registros:
        if registro.hash_conteudo != hash_modelo(registro.conteudo):
            raise ErroPlano('HASH_DE_CONTEUDO_DIVERGENTE')
        natureza = 'sintetico' if acervo.ambiente == 'sintetico' else 'operacional'
        if registro.conteudo.natureza != natureza:
            raise ErroPlano('NATUREZA_INCOMPATIVEL_COM_AMBIENTE')
    estados = {}
    ultimo_hash = '0' * 64
    ultimo_instante = None
    for seq, evento in enumerate(acervo.eventos, 1):
        if evento.ambiente != acervo.ambiente:
            raise ErroPlano('EVENTO_DE_OUTRO_AMBIENTE')
        if evento.sequencia != seq or evento.hash_anterior != ultimo_hash:
            raise ErroPlano('CADEIA_DE_EVENTOS_INVALIDA')
        if ultimo_instante is not None and evento.em < ultimo_instante:
            raise ErroPlano('EVENTO_FORA_DE_ORDEM_TEMPORAL')
        registro = registros.get(evento.plano_id)
        if registro is None:
            raise ErroPlano('EVENTO_SEM_PLANO')
        p = registro.conteudo
        if (evento.hash_conteudo, evento.versao, evento.condominio_id) != (
                registro.hash_conteudo, p.versao, p.condominio_id):
            raise ErroPlano('EVENTO_NAO_CORRESPONDE_A_VERSAO')
        estado = TRANSICOES.get((estados.get(p.id), evento.acao))
        if estado is None:
            raise ErroPlano('TRANSICAO_DE_PLANO_INVALIDA')
        if evento.acao == 'ativar':
            if not (p.vigente_de <= evento.data_ref and (p.vigente_ate is None or evento.data_ref < p.vigente_ate)):
                raise ErroPlano('ATIVACAO_FORA_DA_VIGENCIA')
            for outro_id, outro_estado in estados.items():
                if outro_id == p.id or outro_estado != 'ativo':
                    continue
                outro = registros[outro_id].conteudo
                if outro.condominio_id == p.condominio_id and (
                        p.vigente_de < (outro.vigente_ate or date.max)
                        and outro.vigente_de < (p.vigente_ate or date.max)):
                    raise ErroPlano('PLANOS_ATIVOS_SOBREPOSTOS')
        estados[p.id] = estado
        ultimo_hash = hash_modelo(evento)
        ultimo_instante = evento.em
    if set(estados) != set(registros) or any(r.estado != estados[k] for k, r in registros.items()):
        raise ErroPlano('ESTADO_SEM_HISTORICO_VALIDO')


def acrescentar_evento(acervo: AcervoPlanos, evento: EventoPlano, plano=None) -> AcervoPlanos:
    registros = list(acervo.registros)
    if plano is not None:
        if any(r.conteudo.id == plano.id for r in registros):
            raise ErroPlano('VERSAO_OU_CONTEUDO_IMUTAVEL')
        registros.append(RegistroPlano(conteudo=plano, hash_conteudo=hash_modelo(plano), estado='rascunho'))
    indice = next((i for i, r in enumerate(registros) if r.conteudo.id == evento.plano_id), None)
    if indice is None:
        raise ErroPlano('PLANO_INEXISTENTE')
    atual = registros[indice]
    anterior = None if plano is not None else atual.estado
    estado = TRANSICOES.get((anterior, evento.acao))
    if estado is None:
        raise ErroPlano('TRANSICAO_DE_PLANO_INVALIDA')
    registros[indice] = RegistroPlano(conteudo=atual.conteudo, hash_conteudo=atual.hash_conteudo, estado=estado)
    novo = AcervoPlanos(ambiente=acervo.ambiente, registros=tuple(registros), eventos=acervo.eventos + (evento,))
    conferir_acervo(novo)
    return novo
