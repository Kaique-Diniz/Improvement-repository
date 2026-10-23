"""Cruzamento canônico por condomínio + bloco/torre + unidade, sem prioridade implícita."""
from conversor.domain.canonical import Endereco, EvidenciaDocumento, LoteCanonico, Pessoa, RessalvaLeitura
from conversor.domain.documents import evidencias_documento
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
        try:
            pequeno=LoteCanonico(unidades=(u,),boletos=(),pessoas=(atual,))
            key=(u.condominio_id,u.bloco_original,u.unidade_original)
            unido=complementar_cadastro(pequeno,{key:complementar},Endereco())
            pessoas.append(unido.pessoas[0])
        except ErroLeitura as erro:
            if erro.codigo!='TITULAR_DIVERGENTE':raise
            # Não escolhe o titular do Cadastro. Mantém ambos os nomes e documentos
            # na auditoria e impede a resolução automática do registro afetado.
            fontes=list(evidencias_documento(atual))
            fontes.extend(EvidenciaDocumento(documento=e.documento,origem=e.origem,titular_id=None)
                          for e in evidencias_documento(complementar))
            pessoas.append(Pessoa.model_validate(atual.model_dump()|{'evidencias_documentais':tuple(fontes)}))
            ressalvas.append(RessalvaLeitura(codigo='TITULAR_DIVERGENTE',gravidade='critico',registro_id=u.id,
                origens=(atual.origem,complementar.origem),valores_originais=(atual.nome,complementar.nome)))
    return LoteCanonico(unidades=lote.unidades,boletos=lote.boletos,pessoas=tuple(pessoas),ressalvas=tuple(ressalvas))
