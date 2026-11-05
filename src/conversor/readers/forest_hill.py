"""AUTO GESTÃO Forest Hill: reutilização do leitor tabular e do cadastro A1.

Os códigos de evidência PASSAREDO_* identificam o componente reutilizado;
condomínio, contexto, hashes e unidades continuam segregados por identidade.
"""
from conversor.domain.forest_hill import complemento_unidade
from .passaredo_cadastro import LeitorPassaredoCadastro
from .passaredo_inadimplencia import LeitorPassaredoInadimplencia
from .passaredo_canonical import ler_financeiro as ler_tabular, ler_cadastro as ler_cadastro_tabular
from .text_support import ErroLeitura


def identificar(conteudo, *, cadastro=False):
    registros = (LeitorPassaredoCadastro() if cadastro else LeitorPassaredoInadimplencia()).ler(conteudo)
    for registro in registros:
        try:
            complemento_unidade(registro.unidade)
        except ValueError:
            raise ErroLeitura('FOREST_HILL_UNIDADE_NAO_RECONHECIDA', linha=registro.linha) from None


def ler_financeiro(conteudo, *, contexto):
    identificar(conteudo)
    return ler_tabular(conteudo, contexto=contexto)


def ler_cadastro(conteudo, *, contexto):
    identificar(conteudo, cadastro=True)
    return ler_cadastro_tabular(conteudo, contexto=contexto)
