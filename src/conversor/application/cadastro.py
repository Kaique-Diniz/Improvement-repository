"""Cruzamento estrutural: cadastro preferencial para contatos, financeiro preservado."""
from collections import Counter
from conversor.domain.canonical import Endereco, LoteCanonico, RessalvaLeitura, documento_validado
from conversor.domain.documents import CONTATO_UNIDADE, resolver_documento
from conversor.domain.identity import chave_unidade
from conversor.readers.text_support import ErroLeitura
from .enrichment import complementar_cadastro


def cruzar_cadastro(lote: LoteCanonico, cadastro: LoteCanonico) -> LoteCanonico:
    if {u.condominio_id for u in lote.unidades}!={u.condominio_id for u in cadastro.unidades}:
        raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
    def pessoas_unicas(l):
        ps={p.unidade_id:p for p in l.pessoas}
        if len(ps)!=len(l.pessoas):raise ErroLeitura('TITULAR_AMBIGUO')
        return ps
    originais=pessoas_unicas(lote);cadastradas=pessoas_unicas(cadastro)
    index={}
    for u in cadastro.unidades:
        key=(u.condominio_id,chave_unidade(u.bloco_original,u.unidade_original))
        if key in index:raise ErroLeitura('CADASTRO_AMBIGUO')
        index[key]=u
    pessoas=[];ressalvas=list(lote.ressalvas)
    for u in lote.unidades:
        if u.id not in originais:raise ErroLeitura('PESSOA_SEM_ORIGEM')
        atual=originais[u.id]
        c=index.get((u.condominio_id,chave_unidade(u.bloco_original,u.unidade_original)))
        if c is None:
            ressalvas.append(RessalvaLeitura(codigo='CADASTRO_COMPLEMENTAR_AUSENTE',registro_id=u.id,origens=(u.origem,)))
            pessoas.append(atual);continue
        if c.administradora_id!=u.administradora_id:raise ErroLeitura('CADASTRO_DE_OUTRA_ADMINISTRADORA')
        if c.id not in cadastradas:raise ErroLeitura('CADASTRO_SEM_PESSOA')
        complementar=cadastradas[c.id]
        if c.id!=u.id:raise ErroLeitura('NORMALIZADORES_DE_UNIDADE_INCOMPATIVEIS')
        ressalvas.extend(r for r in cadastro.ressalvas if r.registro_id==c.id)
        pequeno=LoteCanonico(unidades=(u,),boletos=(),pessoas=(atual,))
        key=(u.condominio_id,u.bloco_original,u.unidade_original)
        unido=complementar_cadastro(pequeno,{key:complementar},Endereco(),politica_titular='cadastro_por_unidade')
        pessoas.append(unido.pessoas[0])
        ressalvas.extend(unido.ressalvas)
        ressalvas.append(RessalvaLeitura(codigo='CADASTRO_POR_UNIDADE_CONFERIDO',gravidade='informativo',
            registro_id=u.id,origens=(atual.origem,complementar.origem),
            valores_originais=(atual.nome,complementar.nome)))
    return LoteCanonico(unidades=lote.unidades,boletos=lote.boletos,pessoas=tuple(pessoas),ressalvas=tuple(ressalvas))


def reavaliar_pendencias_cadastrais(lote: LoteCanonico, historico, *, cadastro: LoteCanonico | None = None):
    """Reavalia falsos conflitos antigos; não altera nem exclui o histórico.

    Exige releitura e cruzamento das fontes da mesma unidade. Códigos críticos
    diferentes destes três, conflitos atuais ou evidência não vinculada ficam
    integralmente bloqueantes. Não é uma liberação de lote nem um atesto.
    """
    historico = tuple(historico or ())
    contagens = Counter(o.id for o in historico)
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    unidades = {u.id: u for u in lote.unidades}
    unidades_cadastro = {u.id: u for u in cadastro.unidades} if cadastro else {}
    cadastrais = {}
    # Origens dos dois documentos diferem; comparar identidade estrutural da
    # unidade sem exigir a mesma página/arquivo entre inadimplência e cadastro.
    if cadastro:
        cadastrais = {p.unidade_id: p for p in cadastro.pessoas if p.unidade_id in unidades
            and (u := unidades_cadastro.get(p.unidade_id)) is not None
            and (u.condominio_id, u.administradora_id, u.chave_normalizada) ==
                (unidades[u.id].condominio_id, unidades[u.id].administradora_id, unidades[u.id].chave_normalizada)}
    provas = {r.registro_id: r for r in lote.ressalvas if r.codigo == 'CADASTRO_POR_UNIDADE_CONFERIDO'}
    criticas = {r.registro_id for r in lote.ressalvas if r.gravidade == 'critico'}
    resultado = []
    def local(origem):
        return (origem.sha256, origem.pagina, origem.linha) if origem else None
    for o in historico:
        if contagens[o.id] != 1 or not o.bloqueante or o.escopo != 'registro' or o.codigo not in {
            'TITULAR_MULTIPLO_OU_NAO_SEGMENTADO', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO', 'TITULAR_DIVERGENTE'}:
            continue
        p, prova = pessoas.get(o.registro_id), provas.get(o.registro_id)
        if p is None:
            continue
        raw = cadastrais.get(o.registro_id)
        locais = {local(raw.origem), local(unidades[o.registro_id].origem)} if raw else set()
        if raw and raw.relacao_unidade == CONTATO_UNIDADE and o.codigo != 'TITULAR_DIVERGENTE' and (
            local(o.origem) == local(raw.origem) or
            o.codigo == 'DOCUMENTO_TITULAR_NAO_CONFIRMADO' and local(o.origem) in locais):
            # A falsa exigência individual no próprio Cadastro pode ser revista
            # mesmo que OUTRO conflito entre fontes mantenha a unidade retida.
            doc = resolver_documento(raw)
            origens = (raw.origem, unidades[o.registro_id].origem)
        else:
            if prova is None or (o.registro_id in criticas and o.codigo != 'TITULAR_DIVERGENTE'):
                continue
            if p.relacao_unidade != CONTATO_UNIDADE or len(prova.valores_originais) != 2:
                continue
            doc = resolver_documento(p)
            origens = prova.origens
            if (doc.bloqueante and o.codigo != 'TITULAR_DIVERGENTE') or local(o.origem) not in {local(e) for e in origens}:
                continue
        if o.codigo == 'DOCUMENTO_TITULAR_NAO_CONFIRMADO':
            if not o.evidencias_documentais or not doc.valor:
                continue
            atuais = {(local(e.origem), documento_validado(e.documento)) for e in doc.evidencias}
            if any(not documento_validado(e.documento) or
                   (local(e.origem), documento_validado(e.documento)) not in atuais
                   for e in o.evidencias_documentais):
                continue
        resultado.append({'ocorrencia_id': o.id, 'codigo_original': o.codigo,
            'registro_id': o.registro_id, 'politica': 'cadastro_por_unidade@2',
            'efeito': 'nao_bloqueante_na_releitura',
            'fundamento': 'Vínculo estrutural da unidade conferido. Diferenças de nomes são informativas; Cadastro preferencial sem afirmar titularidade jurídica.',
            'origens_conferidas': [e.model_dump(mode='json') for e in origens]})
    return resultado
