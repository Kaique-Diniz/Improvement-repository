"""Identidade tabular: estrutura compartilhada não comprova condomínio.

O registro associa gramática e despacho de cada perfil; nunca escolhe um leitor
pela ordem dos candidatos. Não altera dados ou critérios financeiros.
"""
from dataclasses import dataclass
from typing import Callable

from conversor.domain.forest_hill import complemento_unidade
from .passaredo_cadastro import LeitorPassaredoCadastro
from .passaredo_inadimplencia import LeitorPassaredoInadimplencia
from .passaredo_canonical import ler_financeiro as ler_passaredo, ler_cadastro as ler_cadastro_passaredo
from .forest_hill import ler_financeiro as ler_forest_hill, ler_cadastro as ler_cadastro_forest_hill
from .text_support import ErroLeitura


def unidade_passaredo(texto):
    # Mesma faixa numérica documentada pelo perfil unidade_sufixo de quatro
    # dígitos. Zeros/texto originais não são modificados no canônico.
    if not texto.isascii() or not texto.isdigit() or len(texto.lstrip('0') or '0') > 4:
        raise ValueError('PASSAREDO_GRAMATICA_DE_UNIDADE_DIVERGENTE')


@dataclass(frozen=True)
class PerfilTabular:
    id: str
    validar_unidade: Callable
    financeiro: Callable
    cadastro: Callable

    def formato(self, cadastro=False):
        return self.id + ('_cadastro_xlsx_v1' if cadastro else '_inadimplencia_xlsx_v1')


PERFIS_TABULARES = {
    'passaredo': PerfilTabular('passaredo', unidade_passaredo, ler_passaredo, ler_cadastro_passaredo),
    'forest_hill': PerfilTabular('forest_hill', complemento_unidade, ler_forest_hill, ler_cadastro_forest_hill),
}


class IdentidadeTabularNaoComprovada(ErroLeitura):
    def __init__(self, candidatos):
        self.candidatos = tuple(candidatos)
        # Compatibilidade com clientes Passaredo já publicados. A mensagem
        # humana e a lista de candidatos são sempre específicas do documento.
        codigo = ('PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL' if self.candidatos == ('passaredo',)
                  else 'AUTO_GESTAO_LAYOUT_RECONHECIDO_INFORME_PERFIL')
        super().__init__(codigo)


def perfis_compativeis(conteudo, *, cadastro=False):
    leitor = LeitorPassaredoCadastro() if cadastro else LeitorPassaredoInadimplencia()
    registros = leitor.ler(conteudo)
    if not registros:
        raise ErroLeitura('AUTO_GESTAO_DOCUMENTO_SEM_UNIDADES')
    candidatos = []
    for id_, spec in PERFIS_TABULARES.items():
        try:
            for registro in registros:
                spec.validar_unidade(registro.unidade)
        except ValueError:
            continue
        candidatos.append(id_)
    if not candidatos:
        raise ErroLeitura('AUTO_GESTAO_NENHUM_PERFIL_COMPATIVEL')
    return tuple(candidatos)


def reconhecer_tabular(conteudo, perfis, *, cadastro=False, escolha=None):
    from hashlib import sha256
    candidatos = tuple(id_ for id_ in perfis_compativeis(conteudo, cadastro=cadastro) if id_ in perfis)
    if not candidatos:
        raise ErroLeitura('AUTO_GESTAO_NENHUM_PERFIL_CONFIGURADO')
    papel = 'cadastro' if cadastro else 'inadimplencia'
    digest = sha256(conteudo).hexdigest()
    conhecidos = [p for p in perfis.values() if p.get('fontes_homologacao_sha256', {}).get(papel) == digest]
    if len(conhecidos) > 1:
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    conhecido = conhecidos[0] if conhecidos else None
    if conhecido and escolha not in (None, 'auto', conhecido['id']):
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    escolhido = conhecido['id'] if conhecido else escolha
    if conhecido and escolhido not in PERFIS_TABULARES:
        raise ErroLeitura('PERFIL_TABULAR_AINDA_NAO_IMPLEMENTADO')
    if escolhido in (None, 'auto'):
        raise IdentidadeTabularNaoComprovada(candidatos)
    if escolhido not in candidatos or escolhido not in perfis:
        raise ErroLeitura('PERFIL_TABULAR_INCOMPATIVEL_COM_UNIDADES')
    perfil = dict(perfis[escolhido], identificacao_diagnostica=(
        'fonte_homologada_por_hash' if conhecido else 'condominio_informado_pelo_usuario'))
    return perfil, '', PERFIS_TABULARES[escolhido].formato(cadastro)


def ler_tabular(conteudo, *, contexto, perfil_id, formato, papel):
    spec = PERFIS_TABULARES.get(perfil_id)
    if spec is None or papel not in ('cadastro', 'inadimplencia') or formato != spec.formato(papel == 'cadastro'):
        raise ErroLeitura('LEITOR_TABULAR_DE_OUTRO_PERFIL')
    if perfil_id not in perfis_compativeis(conteudo, cadastro=papel == 'cadastro'):
        raise ErroLeitura('PERFIL_TABULAR_INCOMPATIVEL_COM_UNIDADES')
    funcao = spec.cadastro if papel == 'cadastro' else spec.financeiro
    return funcao(conteudo, contexto=contexto)
