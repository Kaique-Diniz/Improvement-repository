"""Identidade OMA: nomes/códigos documentais distintos do identificador destino."""
from hashlib import sha256
from .oma_cadastro import conferir_identidade
from .oma_xlsx import LeitorOMAXLSX
from .text_support import ContextoLeitura, ErroLeitura

PERFIL = 'parque_santa_monica'


class IdentidadeOMANaoComprovada(ErroLeitura):
    candidatos = (PERFIL,)

    def __init__(self):
        super().__init__('OMA_IDENTIDADE_PROVAVEL_CONFIRME_PERFIL')


def reconhecer_oma(conteudo, perfis, *, cadastro=False, escolha=None, identidade_pdf=None):
    if cadastro:
        conferir_identidade(identidade_pdf)
        formato = 'oma_cadastro_pdf_v1'
    else:
        contexto = ContextoLeitura('condominio_parque_santa_monica','oma','oma_inadimplencia_xlsx_v1','identificacao',PERFIL)
        LeitorOMAXLSX().ler(conteudo, contexto=contexto)
        formato = 'oma_inadimplencia_xlsx_v1'
    papel = 'cadastro' if cadastro else 'inadimplencia'
    digest = sha256(conteudo).hexdigest()
    conhecidos = [p['id'] for p in perfis.values() if p.get('fontes_homologacao_sha256',{}).get(papel)==digest]
    if len(conhecidos)>1 or (conhecidos and conhecidos != [PERFIL]) or escolha not in (None,'auto',PERFIL):
        raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
    if not conhecidos and escolha in (None,'auto'):
        raise IdentidadeOMANaoComprovada()
    return dict(perfis[PERFIL], identificacao_diagnostica='fonte_homologada_por_hash' if conhecidos else 'condominio_informado_pelo_usuario'), PERFIL, formato


def validar_cadastro_protegido(conteudo, financeiro, *, escolha, perfis):
    """Exceção restrita ao cadastro OMA: senha vazia e EXTRACT explícito.

    Não remove proteção, não grava cópia descriptografada, não aceita senha
    fornecida pelo cliente e mantém limites de páginas, streams e caracteres.
    """
    from .bbz_cadastro import FonteCadastroBBZ
    perfil, _, _ = reconhecer_oma(financeiro, perfis, escolha=escolha)
    if perfil['id'] != PERFIL:
        raise ErroLeitura('OMA_CADASTRO_DE_OUTRO_PERFIL')
    fonte = FonteCadastroBBZ(conteudo)
    conferir_identidade(fonte.identidade)
