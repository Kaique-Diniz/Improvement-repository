"""Ponte de leitura para a autoridade/âncora do repositório 4.1; não grava nada."""
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import EstadoPlanos, hash_modelo
from .billing_json import RepositorioPlanosJSON


class VerificadorPlanosJSON:
    def __init__(self, repositorio_confiavel: RepositorioPlanosJSON):
        self.repositorio = repositorio_confiavel

    def conferir(self, estado: EstadoPlanos) -> None:
        # carregar verifica assinatura de manifesto/eventos, permissões históricas,
        # cadeia, versão/hash e ponteiro externo. Um DTO ativo isolado não basta.
        confiavel = self.repositorio.carregar()
        if hash_modelo(estado) != hash_modelo(confiavel):
            raise ErroAplicacao('ESTADO_NAO_CORRESPONDE_A_AUTORIDADE_ATUAL')
