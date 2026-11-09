"""Beach Parque: A1 por lançamento; somente titular válido transfere contatos."""
from collections import Counter
from datetime import datetime
import json
import re
from pydantic import ValidationError
from conversor.application.passaredo_cadastro import associar as associar_a1
from conversor.domain.bbz_cadastro import FichaCadastroBBZ
from conversor.domain.canonical import Contato, RessalvaLeitura, documento_validado
from conversor.domain.documents import resolver_documento
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.beach_parque_xlsx import originais

POLITICA = 'beach_parque_titular_nominal_documento_valido_A1@1.1'
RETIDO_SEM_DOCUMENTO = 'BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA'
MOTIVOS = ('PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO',
    'PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO',
    'PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO', RETIDO_SEM_DOCUMENTO)

POLITICA_B1 = 'beach_parque_linha_cadastral_individual_comprovada_B1@1.1'


def _titular_individual_comprovado(pessoa, cadastro):
    """Exceção Beach fechada: ficha individual, não uma inferência pelo E.

    Apenas conectivo terminal entre componentes, com pelo menos dois anteriores.
    Listas, dois nomes completos e nomes curtos continuam exigindo revisão.
    A grafia é só um filtro de rejeição; sozinha nunca prova individualidade.
    """
    nome = normalizar_assinatura(pessoa.nome)
    partes = nome.split()
    if (len(partes) < 4 or partes[-2] != 'e' or partes.count('e') != 1
            or any(not parte.isalpha() for parte in partes)
            or pessoa.relacao_unidade != 'titular_cadastrado_beach_parque'):
        return None
    notas = [r for r in cadastro.ressalvas if r.codigo == 'BPQ_CADASTRO_FICHA_ORIGINAL'
        and r.registro_id == pessoa.unidade_id]
    if len(notas) != 1 or len(notas[0].valores_originais) != 1:
        return None
    try:
        ficha = FichaCadastroBBZ.model_validate_json(notas[0].valores_originais[0])
    except ValidationError:
        return None
    titulares = [p for p in ficha.participantes if p.papel == 'titular']
    if (ficha.unidade_id != pessoa.unidade_id or ficha.cabecalhos != notas[0].origens
            or pessoa.origem not in ficha.cabecalhos or len(titulares) != 1):
        return None
    titular = titulares[0]
    resolucao = resolver_documento(pessoa)
    if (normalizar_assinatura(titular.nome) != nome or len(titular.documentos) != 1
            or resolucao.bloqueante or not resolucao.valor):
        return None
    doc, origem_doc = titular.documentos[0]
    if doc.tipo != 'cpf' or documento_validado(doc) != resolucao.valor:
        return None
    if not resolucao.evidencias or any(e.titular_id != pessoa.id or
            e.documento.tipo != 'cpf' or documento_validado(e.documento) != resolucao.valor
            or e.origem != origem_doc for e in resolucao.evidencias):
        return None
    pessoais = [c for c in ficha.campos if c.papel == 'titular' and c.secao == 'dados pessoais']
    # O parser conserva campos nominais brutos mesmo quando não cria um segundo
    # Participante. Um CPF e o cabeçalho não podem apagar essa prova de pluralidade.
    nominais = [c for c in pessoais if normalizar_assinatura(c.campo) in
        {'nome','nome do titular','titular','responsavel'}]
    pluralidade = any(normalizar_assinatura(c.campo) in
        {'nomes','titulares','responsaveis','coproprietarios','proprietarios'} for c in pessoais)
    if (pluralidade or len(nominais) > 1 or any(normalizar_assinatura(
            c.valor_original.partition(':')[2]) != nome for c in nominais)):
        return None
    campos_conhecidos = {'tipo de pessoa','cpf','cnpj','data de nascimento',
        'tipo de identidade','orgao emissor','data de expedicao',
        'nome','nome do titular','titular','responsavel'}
    if any(normalizar_assinatura(c.campo) not in campos_conhecidos for c in pessoais):
        return None  # Campo pessoal desconhecido não comprova individualidade.
    tipos = [c for c in pessoais if normalizar_assinatura(c.valor_original).startswith('tipo de pessoa:')]
    campos_doc = [c for c in pessoais if re.match(r'^(CPF|CNPJ)\s*:', c.valor_original)]
    if (len(tipos) != 1 or normalizar_assinatura(tipos[0].valor_original) != 'tipo de pessoa: fisica'
            or len(campos_doc) != 1 or campos_doc[0].origem != origem_doc):
        return None
    # Confirma também o valor bruto, sem atribuir documento de outra coluna/papel.
    from conversor.readers.passaredo_cadastro import normalizar_documento
    extraido = normalizar_documento(campos_doc[0].valor_original.split(':', 1)[1].strip())
    if extraido is None or extraido.tipo != 'cpf' or extraido.valor != resolucao.valor:
        return None
    return pessoa.model_copy(update={'contato': _contato_individual(ficha, pessoa.contato)})


def _contato_individual(ficha, contato):
    """Inclusão datada, só para o titular já comprovado acima.

    Reconstrói o sufixo contíguo das células originais da MESMA linha e papel.
    A gramática BPQ-02 e contatos desconhecidos dos demais titulares não mudam.
    Nenhum prefixo, anotação residual ou dado de terceiro pode ser descartado.
    """
    from conversor.readers.beach_parque_cadastro import segmentar_contato
    linhas = {}
    for c in ficha.campos:
        if c.papel == 'titular' and c.secao == 'telefone/e-mail do cliente':
            linhas.setdefault((c.origem.pagina, c.origem.linha), []).append(c)
    telefones, emails = list(contato.telefones), list(contato.emails)
    for campos in linhas.values():
        campos = sorted(campos, key=lambda c: c.x_inicio)
        if len({c.x_inicio for c in campos}) != len(campos):
            continue
        for i, campo in enumerate(campos):
            sufixo = campos[i:]
            if any(a.x_fim != b.x_inicio for a,b in zip(sufixo,sufixo[1:])):
                continue
            texto = ' '.join(c.valor_original for c in sufixo)
            m = re.fullmatch(r'(.+?)\s+-\s+inclu[ií]d[oa] em ([0-9]{2}/[0-9]{2}/[0-9]{4})\.?', texto, re.I)
            if not m:
                continue
            try:
                datetime.strptime(m[2], '%d/%m/%Y')
            except ValueError:
                continue
            segmentado = segmentar_contato(m[1])
            if segmentado.codigo is not None:
                continue
            telefones.extend(segmentado.telefones)
            emails.extend(segmentado.emails)
    return contato.model_copy(update={'telefones': tuple(dict.fromkeys(telefones))[:5],
        'emails': tuple(dict.fromkeys(emails))[:3]})


def resolver_linha_cadastral(lote, unidade, pessoa_base, decisoes, pessoas_a1, cadastro):
    """Só reutiliza A1 das ocorrências fora da seleção que justificam a linha.

    Não decide se a linha será exportada nem modifica a pessoa-base. O retorno
    pessoal permanece privado; a decisão auditável não contém dados pessoais.
    """
    ids = sorted(d['id'] for d in decisoes if d['unidade_id'] == unidade.id
        and d['situacao_financeira'] == 'excluido')
    audit = {'politica': POLITICA_B1, 'politica_a1': POLITICA, 'unidade_id': unidade.id,
        'lancamentos_relevantes': ids, 'origens': []}

    def decidir(codigo, pessoa=None):
        return pessoa, dict(audit, estado=codigo, comprovada=pessoa is not None,
            motivo_retencao=None if pessoa is not None else codigo)

    if cadastro is None:
        return decidir('BPQ_B1_CADASTRO_NAO_FORNECIDO')
    if not ids or len(ids) != len(set(ids)):
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    if (unidade.administradora_id, unidade.condominio_id) != ('habitacional', 'condominio_terraco_beach_parque'):
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    boletos = {b.id: b for b in lote.boletos if b.unidade_id == unidade.id}
    if any(id_ not in boletos or id_ not in pessoas_a1 for id_ in ids):
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    associados = [pessoas_a1[id_] for id_ in ids]
    audit['origens'] = [o.model_dump(mode='json') for o in dict.fromkeys(
        o for id_ in ids for o in boletos[id_].origens)]
    nomes = {normalizar_assinatura(p.nome) for p in associados}
    if len(nomes) != 1:
        return decidir('BPQ_B1_RESPONSAVEIS_MULTIPLOS')
    if not pessoa_base or pessoa_base.unidade_id != unidade.id or nomes != {normalizar_assinatura(pessoa_base.nome)}:
        return decidir('BPQ_B1_NOME_DIVERGENTE')
    codigos = {r.codigo for r in lote.ressalvas if r.registro_id in ids and r.codigo in MOTIVOS}
    audit['origens'].extend(o.model_dump(mode='json') for o in dict.fromkeys(
        o for r in lote.ressalvas if r.registro_id in ids and r.codigo in MOTIVOS for o in r.origens))
    for motivo,estado in (
        ('PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO','BPQ_B1_NOME_DIVERGENTE'),
        ('PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO','BPQ_B1_RESPONSAVEIS_MULTIPLOS'),
        ('PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO','BPQ_B1_DOCUMENTO_CONFLITANTE'),
        (RETIDO_SEM_DOCUMENTO,'BPQ_B1_DOCUMENTO_TITULAR_AUSENTE')):
        if motivo in codigos:
            return decidir(estado)
    donos = [p for p in cadastro.pessoas if p.unidade_id == unidade.id]
    unidades_cad = [u for u in cadastro.unidades if u.id == unidade.id]
    if len(donos) != 1 or len(unidades_cad) != 1:
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    dono,uc = donos[0],unidades_cad[0]
    if (uc.administradora_id,uc.condominio_id,uc.bloco_original,uc.unidade_original) != (
            unidade.administradora_id,unidade.condominio_id,unidade.bloco_original,unidade.unidade_original):
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    if dono.relacao_unidade != 'titular_cadastrado_beach_parque' or normalizar_assinatura(dono.nome) not in nomes:
        return decidir('BPQ_B1_NOME_DIVERGENTE')
    dono = _titular_individual_comprovado(dono,cadastro) or dono
    documentos = [resolver_documento(p) for p in associados]
    original = resolver_documento(dono)
    if original.bloqueante or any(d.bloqueante for d in documentos):
        return decidir('BPQ_B1_DOCUMENTO_CONFLITANTE')
    if not original.valor or any(not d.valor for d in documentos):
        return decidir('BPQ_B1_DOCUMENTO_TITULAR_AUSENTE')
    if {d.valor for d in documentos} != {original.valor}:
        return decidir('BPQ_B1_DOCUMENTO_CONFLITANTE')
    relevantes = {unidade.id,dono.id,*ids,*(p.id for p in associados)}
    conhecidas = {*(u.id for u in lote.unidades),*(b.id for b in lote.boletos),
        *(p.id for p in lote.pessoas),*(p.id for p in cadastro.pessoas),*(p.id for p in pessoas_a1.values())}
    if any(r.gravidade == 'critico' and (r.registro_id not in conhecidas or r.registro_id in relevantes) for r in lote.ressalvas):
        return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    fontes_doc = {(ev.documento,ev.origem) for ev in original.evidencias}
    for id_,p,d in zip(ids,associados,documentos):
        if (p.unidade_id != unidade.id or p.origem not in boletos[id_].origens
                or p.relacao_unidade != 'responsavel_informado_na_inadimplencia'
                or not d.evidencias or any(ev.titular_id != p.id or (ev.documento,ev.origem) not in fontes_doc for ev in d.evidencias)
                or p.contato != dono.contato):
            return decidir('BPQ_B1_ASSOCIACAO_INSUFICIENTE')
    # A equivalência foi demonstrada para todos, não escolhida pela ordem.
    pessoa = associados[0]
    audit['origens'].extend(o.model_dump(mode='json') for o in dict.fromkeys(
        ev.origem for d in documentos for ev in d.evidencias))
    return decidir('BPQ_B1_ASSOCIACAO_COMPROVADA',pessoa)


def associar(lote, cadastro=None):
    lote, pessoas, resumo, _ = associar_a1(lote,cadastro,obter_originais=originais)
    resumo['politica'] = POLITICA
    resumo['historico_nao_comprova_titularidade_atual'] = True
    if cadastro is None:
        return lote,pessoas,resumo,[]
    cad={p.unidade_id:p for p in cadastro.pessoas}
    unidades={u.id:u for u in lote.unidades}
    notas=list(lote.ressalvas)
    # Não modifica a política padrão Passaredo nem apaga outras retenções.
    multiplo = 'PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO'
    recuperados = set()
    for b in lote.boletos:
        motivos = {r.codigo for r in notas if r.registro_id == b.id and r.codigo in MOTIVOS}
        u = unidades[b.unidade_id]
        if motivos != {multiplo} or (u.administradora_id,u.condominio_id) != (
                'habitacional','condominio_terraco_beach_parque'):
            continue
        dono = _titular_individual_comprovado(cad[b.unidade_id],cadastro)
        if dono is None or normalizar_assinatura(pessoas[b.id].nome) != normalizar_assinatura(dono.nome):
            continue
        p = pessoas[b.id]
        pessoas[b.id] = p.model_copy(update={'evidencias_documentais':tuple(
            e.model_copy(update={'titular_id':p.id}) for e in resolver_documento(dono).evidencias),
            'contato':dono.contato})
        recuperados.add(b.id)
        resumo['associacoes_concordantes'] += 1
        resumo['associacoes_retidas'] -= 1
        resumo['documentos_validos_vinculados'] += 1
        notas.append(RessalvaLeitura(codigo='BPQ_TITULAR_INDIVIDUAL_DOCUMENTALMENTE_COMPROVADO',
            gravidade='informativo',registro_id=b.id,origens=(p.origem,dono.origem,
                *tuple(dict.fromkeys(e.origem for e in resolver_documento(dono).evidencias)))))
    notas = [r for r in notas if not (r.codigo == multiplo and r.registro_id in recuperados)]
    resumo['lancamentos_individuais_com_conectivo_comprovados'] = len(recuperados)
    retidos={r.registro_id for r in notas if r.codigo in MOTIVOS}
    for b in lote.boletos:
        p=pessoas[b.id]
        if b.unidade_id not in cad or b.id in retidos or resolver_documento(p).valor:
            continue
        pessoas[b.id]=p.model_copy(update={'contato':Contato(),'documento':None,
            'documento_origem':None,'evidencias_documentais':()})
        notas.append(RessalvaLeitura(codigo=RETIDO_SEM_DOCUMENTO,registro_id=b.id,
            origens=(p.origem,cad[b.unidade_id].origem)))
        resumo['associacoes_concordantes']-=1
        resumo['associacoes_retidas']+=1
    temporais=[r for r in cadastro.ressalvas if r.codigo=='BPQ_CADASTRO_TEMPORALIDADE']
    completude=[r for r in cadastro.ressalvas if r.codigo=='BPQ_CADASTRO_IDENTIDADE_E_COMPLETUDE']
    notas.extend(temporais+completude)
    if len(completude)!=1:
        from conversor.readers.text_support import ErroLeitura
        raise ErroLeitura('BPQ_CADASTRO_COMPLETUDE_AUSENTE_OU_AMBIGUA')
    meta=json.loads(completude[0].valores_originais[0])
    resumo.update(registros_cadastro=meta['unidades_resumo'],paginas_cadastro=meta['paginas'],
        continuidades_cadastro=meta['continuidades'])
    resumo['datas_emissao_cadastro']=sorted({d for r in temporais for d in json.loads(r.valores_originais[0])['datas_emissao']})
    motivos={r.registro_id:r.codigo for r in notas if r.codigo in MOTIVOS}
    resumo['retencoes_por_motivo']=dict(Counter(motivos.values()))
    resumo['unidades_em_revisao']=len({b.unidade_id for b in lote.boletos if b.id in motivos})
    resumo['restricoes_por_codigo']=dict(Counter(r.codigo for r in cadastro.ressalvas if r.codigo.startswith('BPQ_REVISAO_')))
    detalhes={}
    for b in lote.boletos:
        if b.id not in motivos:continue
        u=unidades[b.unidade_id];codigo=motivos[b.id]
        key=(u.id,codigo)
        # Relatório temporário por unidade, sem repetir nomes/documentos.
        d=detalhes.setdefault(key,{'unidade':u.bloco_original+'/'+u.unidade_original,
            'motivo':codigo,'lancamentos':0})
        d['lancamentos']+=1
    return lote.model_copy(update={'ressalvas':tuple(notas)}),pessoas,resumo,list(detalhes.values())
