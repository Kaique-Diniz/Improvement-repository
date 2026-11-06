"""Reconhecimento Itajubá; cadastro sem nome interno exige hash homologado."""
from hashlib import sha256
from .itajuba_pdf import LeitorItajubaPDF
from .itajuba_cadastro import LeitorCadastroItajuba
from .text_support import ContextoLeitura,ErroLeitura

PERFIL='itajuba'


class IdentidadeItajubaNaoComprovada(ErroLeitura):
    candidatos=(PERFIL,)

    def __init__(self):super().__init__('ITAJUBA_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL')


def reconhecer_itajuba(conteudo,perfis,*,cadastro=False,escolha=None):
    parser=LeitorCadastroItajuba()if cadastro else LeitorItajubaPDF()
    parser.ler(conteudo,contexto=ContextoLeitura('condominio_itajuba','bn_planner',parser.formato_id,'identificacao',PERFIL))
    role='cadastro'if cadastro else'inadimplencia';digest=sha256(conteudo).hexdigest()
    known=[p['id']for p in perfis.values()if p.get('fontes_homologacao_sha256',{}).get(role)==digest]
    if len(known)>1 or(known and known!=[PERFIL])or escolha not in(None,'auto',PERFIL):
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    if cadastro and not known:raise ErroLeitura('ITAJUBA_CADASTRO_IDENTIDADE_NAO_COMPROVADA')
    if not known and escolha in(None,'auto'):raise IdentidadeItajubaNaoComprovada()
    return dict(perfis[PERFIL],identificacao_diagnostica='fonte_homologada_por_hash'if known else'condominio_informado_pelo_usuario'),PERFIL,parser.formato_id
