"""Identidade Beach Parque: validação documental precede hash e confirmação."""
from hashlib import sha256
from .beach_parque_xlsx import LeitorBeachParqueXLSX
from .beach_parque_cadastro import conferir_identidade
from .text_support import ContextoLeitura, ErroLeitura

PERFIL = 'terraco_beach_parque'

class IdentidadeBeachParqueNaoComprovada(ErroLeitura):
    candidatos = (PERFIL,)
    def __init__(self):
        super().__init__('BPQ_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL')

def reconhecer_beach(conteudo, perfis, *, cadastro=False, escolha=None, identidade_pdf=None):
    if cadastro:
        conferir_identidade(identidade_pdf)
        formato = 'beach_parque_cadastro_pdf_v1'
    else:
        formato = LeitorBeachParqueXLSX.formato_id
        LeitorBeachParqueXLSX().ler(conteudo, contexto=ContextoLeitura(
            'condominio_terraco_beach_parque','habitacional',formato,'identificacao','3075'))
    papel = 'cadastro' if cadastro else 'inadimplencia'
    digest = sha256(conteudo).hexdigest()
    conhecidos = [p['id'] for p in perfis.values() if p.get('fontes_homologacao_sha256',{}).get(papel)==digest]
    if len(conhecidos)>1 or (conhecidos and conhecidos != [PERFIL]) or escolha not in (None,'auto',PERFIL):
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    if not conhecidos and escolha in (None,'auto'):
        raise IdentidadeBeachParqueNaoComprovada()
    return dict(perfis[PERFIL],identificacao_diagnostica='fonte_homologada_por_hash' if conhecidos else 'condominio_informado_pelo_usuario'), '3075', formato
