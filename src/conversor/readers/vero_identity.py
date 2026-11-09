"""Reconhecimento Lello Vero: estrutura, identidade e confirmação de fontes novas."""
from hashlib import sha256

from .text_support import ContextoLeitura, ErroLeitura
from .vero_xlsx import LeitorVeroXLSX
from .vero_cadastro import LeitorCadastroVero

PERFIL = 'vero_encanto'


class IdentidadeVeroNaoComprovada(ErroLeitura):
    candidatos = (PERFIL,)

    def __init__(self):
        super().__init__('VERO_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL')


def reconhecer_vero(conteudo, perfis, *, cadastro=False, escolha=None):
    parser = LeitorCadastroVero() if cadastro else LeitorVeroXLSX()
    context = ContextoLeitura('condominio_vero_encanto','lello_2',parser.formato_id,'identificacao',PERFIL)
    parser.ler(conteudo,contexto=context)
    role = 'cadastro' if cadastro else 'inadimplencia'
    digest = sha256(conteudo).hexdigest()
    known = [p['id'] for p in perfis.values() if p.get('fontes_homologacao_sha256',{}).get(role) == digest]
    if len(known)>1 or known and known != [PERFIL] or escolha not in (None,'auto',PERFIL):
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    if not known and escolha in (None,'auto'):
        raise IdentidadeVeroNaoComprovada()
    return dict(perfis[PERFIL],identificacao_diagnostica='fonte_homologada_por_hash' if known else
        'condominio_informado_pelo_usuario'), PERFIL, parser.formato_id
