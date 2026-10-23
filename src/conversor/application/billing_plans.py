"""Consulta de configuração ativa. Não seleciona nem avalia boletos."""
from datetime import date

from .billing_ports import RepositorioPlanos
from .ports import ErroAplicacao
from conversor.domain.billing_rules import PlanoCobranca
from conversor.domain.billing_rules import ErroPlano
from conversor.domain.billing_lifecycle import conferir_acervo


def consultar_plano_ativo(repositorio: RepositorioPlanos, *, condominio_id: str,
                         data_ref: date) -> PlanoCobranca:
    if type(data_ref) is not date:
        raise ErroAplicacao('DATA_REF_EXPLICITA_OBRIGATORIA')
    acervo = repositorio.carregar().acervo
    try:
        conferir_acervo(acervo)
    except ErroPlano as erro:
        raise ErroAplicacao(str(erro)) from None
    candidatos = [r.conteudo for r in acervo.registros
                  if r.estado == 'ativo' and r.conteudo.condominio_id == condominio_id
                  and r.conteudo.vigente_de <= data_ref
                  and (r.conteudo.vigente_ate is None or data_ref < r.conteudo.vigente_ate)]
    if len(candidatos) != 1:
        raise ErroAplicacao('PLANO_ATIVO_UNICO_INDISPONIVEL')
    return candidatos[0]
