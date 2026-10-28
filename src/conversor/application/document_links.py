"""Candidatos, comprovação histórica e retenções independentes de regras financeiras."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json

from openpyxl import load_workbook

from conversor.adapters.scope_reference import delimitar_escopo_destino
from conversor.domain.canonical import Origem
from conversor.domain.document_links import IdentidadeOrigem, EvidenciaVinculo, VinculoDocumental, PendenciaDocumental, hash_dados
from conversor.domain.document_scope import EscopoDestinoPersistente, UnidadeEscopoPersistente
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.text_support import ErroLeitura
from .document_link_ports import RepositorioVinculosDocumentais


def identidade_origem(lote, unidade, codigo):
    meta=next(r for r in lote.ressalvas if r.codigo=='BBZ_FECHAMENTO_RECONCILIADO')
    empreendimento=json.loads(meta.valores_originais[0])['identidade_original'].split(' - ',1)[1]
    return IdentidadeOrigem(administradora_id=unidade.administradora_id, empreendimento=empreendimento,
        codigo_original=codigo, bloco_literal=unidade.bloco_original, unidade_literal=unidade.unidade_original)


def hash_perfil(perfil_saida):
    return hash_dados(perfil_saida.model_dump(mode='json', exclude={'endereco_padrao','evidencia'}))


def _candidatos_comprovados(repo, lote, *, referencia, perfil, perfil_saida, codigo):
    prova=delimitar_escopo_destino(lote,referencia=referencia,perfil_saida=perfil_saida,perfil=perfil,codigo_origem=codigo)
    pessoas={p.unidade_id:p for p in lote.pessoas};unidades={u.id:u for u in lote.unidades}
    registros=[];now=datetime.now(timezone.utc)
    for m in prova.unidades:
        if m.estado!='comprovado_documentalmente':continue
        u=unidades[m.unidade_id];identity=identidade_origem(lote,u,codigo)
        ev=tuple(EvidenciaVinculo(papel='referencia',origem=o,conciliacao_sha256=hash_dados(m.recibos_comprovantes))for o in m.evidencias)
        ev+=(EvidenciaVinculo(papel='financeiro',origem=u.origem,conciliacao_sha256=hash_dados(m.recibos_comprovantes)),)
        registros.append(VinculoDocumental(id=identity.id,identidade=identity,codigos_observados=(codigo,),
            condominio_destino_id=perfil['condominio_id'],codigo_destino=perfil['codigo_easycollector'],
            versao=1,estado='candidato',nome_financeiro_hmac=repo.impressao(normalizar_assinatura(pessoas[u.id].nome)),
            perfil_versao=perfil_saida.versao,perfil_sha256=hash_perfil(perfil_saida),evidencias=ev,
            recibos_historicos=m.recibos_comprovantes,registrado_em=now,atualizado_em=now,
            motivo='CONFRONTO_DOCUMENTAL_ESTRITO_APROVACAO_PENDENTE'))
    return tuple(registros)


def candidatos_documentais(repo: RepositorioVinculosDocumentais, lote, *, referencia, financeiro, perfil, perfil_saida, codigo,
                            revisao_esperada, responsavel, sessao_sha256, apenas_novos=False):
    s=repo.consultar()
    registros=_candidatos_comprovados(repo,lote,referencia=referencia,perfil=perfil,perfil_saida=perfil_saida,codigo=codigo)
    if apenas_novos:registros=tuple(r for r in registros if r.id not in s.registros)
    if registros:
        repo.guardar_fonte(financeiro);repo.guardar_fonte(referencia)
        return repo.candidatar(tuple(registros),revisao_esperada=revisao_esperada,responsavel=responsavel,sessao_sha256=sessao_sha256)
    if s.revisao!=revisao_esperada:raise ErroLeitura('VINCULOS_ALTERADOS_RECARREGUE')
    return s


def comprovar_reabertura(repo, registro, lote, *, financeiro, referencia, perfil, perfil_saida, codigo):
    """Reconcilia bytes históricos e contexto atual; não grava nem aprova vínculos."""
    if not perfil.get('exigir_escopo_documental_destino') or perfil_saida is None:
        raise ErroLeitura('REABERTURA_PERFIL_NAO_COMPROVADO')
    hashes={(e.papel,e.origem.sha256)for e in registro.evidencias if e.papel in ('financeiro','referencia')}
    if hashes!={('financeiro',sha256(financeiro).hexdigest()),('referencia',sha256(referencia).hexdigest())}:
        raise ErroLeitura('REABERTURA_FONTES_ORIGINAIS_INCOMPATIVEIS')
    candidatos=_candidatos_comprovados(repo,lote,referencia=referencia,perfil=perfil,perfil_saida=perfil_saida,codigo=codigo)
    prova=next((r for r in candidatos if r.id==registro.id),None)
    if prova is None:raise ErroLeitura('REABERTURA_CONCILIACAO_ORIGINAL_NAO_COMPROVADA')
    return prova


def _unidades_na_referencia(referencia, perfil_saida, lote):
    """Somente localizar linhas para suspender prova contraditória, nunca aprovar."""
    vistos={}
    with BytesIO(referencia)as stream:
        w=load_workbook(stream,read_only=True,data_only=False,keep_links=False)
        try:
            mapa={}
            for u in lote.unidades:
                try:mapa[perfil_saida.codificar(u,administradora_id=u.administradora_id)]=u.id
                except ErroLeitura:continue
            for si,sh in enumerate(w,1):
                for n,row in enumerate(sh.iter_rows(min_row=2),2):
                    if len(row)>=30:
                        uid=mapa.get((str(row[1].value or ''),str(row[6].value or '')))
                        if uid:vistos.setdefault(uid,[]).append(Origem(arquivo_id='referencia',
                            sha256=sha256(referencia).hexdigest(),leitor_versao='confronto_destino@1',
                            identificador=f'xlsx_aba{si}_r{n}_B_G_Y_Z',linha=n))
        finally:w.close()
    return vistos


def resolver_vinculos(repo: RepositorioVinculosDocumentais, lote, *, financeiro, referencia, perfil, perfil_saida, codigo, data_ref):
    prova=delimitar_escopo_destino(lote,referencia=referencia,perfil_saida=perfil_saida,perfil=perfil,codigo_origem=codigo)
    s=None;erro=None;membros=[];pessoas={p.unidade_id:p for p in lote.pessoas};hashes=set()
    if referencia:hashes.add(sha256(referencia).hexdigest())
    try:
        s=repo.consultar()
        # Descoberta só registra candidatos. Ninguém é aprovado pelo processamento.
        if prova.permitidas:
            s=candidatos_documentais(repo,lote,referencia=referencia,financeiro=financeiro,perfil=perfil,
                perfil_saida=perfil_saida,codigo=codigo,revisao_esperada=s.revisao,
                responsavel='descoberta_documental_sem_aprovacao',sessao_sha256='0'*64,apenas_novos=True)
        presentes=_unidades_na_referencia(referencia,perfil_saida,lote) if referencia and prova.motivo_referencia=='CONFRONTO_DOCUMENTAL_REALIZADO_SEM_PRESUMIR_COBERTURA_TOTAL'else set()
        for u in lote.unidades:
            id_=identidade_origem(lote,u,codigo).id;r=s.registros.get(id_)
            if not r:continue
            motivo=None
            if (r.condominio_destino_id,r.codigo_destino)!=(perfil['condominio_id'],perfil['codigo_easycollector']):motivo='DESTINO_PERSISTENTE_CONFLITANTE'
            elif r.nome_financeiro_hmac!=repo.impressao(normalizar_assinatura(pessoas[u.id].nome)):motivo='IDENTIDADE_FINANCEIRA_ALTERADA'
            elif r.perfil_sha256!=hash_perfil(perfil_saida):motivo='PERFIL_DE_IDENTIFICACAO_ALTERADO'
            elif r.revalidar_ate and data_ref>r.revalidar_ate:motivo='VINCULO_EXIGE_REVALIDACAO'
            elif u.id in presentes and u.id not in prova.permitidas:motivo='REFERENCIA_ATUAL_CONTRADITORIA_OU_NAO_CONCILIADA'
            if motivo:
                repo.guardar_fonte(financeiro)
                ev=[EvidenciaVinculo(papel='confronto',origem=u.origem,conciliacao_sha256=sha256(financeiro).hexdigest())]
                if u.id in presentes:
                    repo.guardar_fonte(referencia)
                    ev.extend(EvidenciaVinculo(papel='confronto',origem=o,conciliacao_sha256=o.sha256)for o in presentes[u.id])
                s=repo.observar(id_,motivo=motivo,evidencias=tuple(ev))
        for r in s.registros.values():hashes.update(e.origem.sha256 for e in r.evidencias)
    except ErroLeitura as e:
        erro=e.codigo;s=None
    invalid_reference=bool(referencia and prova.motivo_referencia=='REFERENCIA_DE_ESCOPO_NAO_AVALIAVEL')
    atuais={u.unidade_id:u for u in prova.unidades}
    for u in lote.unidades:
        original=atuais[u.id];dados=original.model_dump();identity=identidade_origem(lote,u,codigo);r=s.registros.get(identity.id)if s else None
        origem=None;motivo=dados['motivo_codigo'];estado='nao_comprovado'
        if erro:motivo=erro
        elif invalid_reference:motivo='REFERENCIA_ATUAL_NAO_VERIFICAVEL'
        elif r and r.estado in ('revogado','recusado','pendente','conflitante'):motivo=r.motivo
        elif r and r.estado=='aprovado':
            estado='comprovado_documentalmente';origem='cadastro_persistente';motivo='VINCULO_HISTORICO_APROVADO_E_VERIFICADO'
            dados.update(evidencias=tuple(e.origem for e in r.evidencias if e.papel=='referencia'),recibos_comprovantes=r.recibos_historicos)
        elif original.estado=='comprovado_documentalmente':estado=original.estado;origem='referencia_atual'
        membros.append(UnidadeEscopoPersistente.model_validate(dados|{'estado':estado,'motivo_codigo':motivo,
            'origem_comprovacao':origem,'vinculo_id':r.id if r else None,'vinculo_versao':r.versao if r else None,
            'estado_vinculo':r.estado if r else 'nao_registrado'}))
    counts=Counter(m.origem_comprovacao for m in membros)
    resumo={'unidades_reconhecidas':len(membros),'comprovadas_cadastro_persistente':counts['cadastro_persistente'],
        'comprovadas_referencia_atual':counts['referencia_atual'],'pendentes':sum(m.estado!='comprovado_documentalmente'for m in membros),
        'conflitantes_ou_revogadas':sum(m.estado_vinculo in ('conflitante','revogado','recusado')or m.motivo_codigo=='DESTINO_PERSISTENTE_CONFLITANTE'for m in membros),
        'novas_evidencias':int(bool(referencia)),'contradicoes':sum('CONTRADITORIA'in m.motivo_codigo or'ALTERAD'in m.motivo_codigo for m in membros)}
    base=prova.model_dump(exclude={'versao','unidades','limite'})
    return EscopoDestinoPersistente(**base,unidades=tuple(membros),cadastro_revisao=s.revisao if s else None,
        cadastro_sha256=s.sha256 if s else None,hashes_fontes_verificadas=tuple(sorted(hashes)),resumo_cadastro=resumo,erro_cadastro=erro),s


def registrar_conflitos(repo, snapshot, lote, *, codigo, conflitos, cadastro_bytes, referencia_bytes):
    if not conflitos:return snapshot
    repo.guardar_fonte(cadastro_bytes);repo.guardar_fonte(referencia_bytes)
    unidades={u.id:u for u in lote.unidades};pessoas={p.unidade_id:p for p in lote.pessoas};grupos={}
    for c in conflitos:
        id_=identidade_origem(lote,unidades[c['unidade_id']],codigo).id
        orig=Origem.model_validate(c['origem'])
        person=pessoas[c['unidade_id']]
        cad_origin=person.documento_origem or next((e.origem for e in person.evidencias_documentais
            if e.origem.sha256==sha256(cadastro_bytes).hexdigest()),None)
        if cad_origin is None or cad_origin.sha256!=sha256(cadastro_bytes).hexdigest():
            raise ErroLeitura('ORIGEM_CADASTRAL_DO_CONFLITO_NAO_COMPROVADA')
        docs=tuple(sorted((repo.impressao(c['documento_atual']),repo.impressao(c['documento_historico']))))
        ev=(EvidenciaVinculo(papel='referencia',origem=orig,conciliacao_sha256=hash_dados(docs)),
            EvidenciaVinculo(papel='cadastro',origem=cad_origin,conciliacao_sha256=hash_dados(docs)))
        pend=PendenciaDocumental(id=hash_dados([id_,docs,orig.sha256]),documentos_hmac=docs,evidencias=ev)
        if pend.id in grupos:
            old=grupos[pend.id][1]
            pend=old.model_copy(update={'evidencias':tuple(dict.fromkeys((*old.evidencias,*pend.evidencias)))})
        grupos[pend.id]=(id_,pend)
    for id_,pend in grupos.values():snapshot=repo.observar(id_,motivo='DOCUMENTOS_VALIDOS_CONFLITANTES',pendencia=pend)
    return snapshot


def retencoes_do_snapshot(snapshot,lote,codigo):
    if not snapshot:return {}
    return {u.id:r.pendencias_documentais for u in lote.unidades
        if (r:=snapshot.registros.get(identidade_origem(lote,u,codigo).id))and r.pendencias_documentais}
