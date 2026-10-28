"""Associação BBZ por unidade e identidade pessoal; nunca prefere cadastro por suposição."""
from collections import Counter
from copy import deepcopy
from datetime import date
import json
import re

from conversor.domain.bbz_cadastro import FichaCadastroBBZ
from conversor.domain.canonical import (Contato, Endereco, EvidenciaDocumento, LoteCanonico,
    Origem, Pessoa, RessalvaLeitura, documento_validado)
from conversor.domain.documents import resolver_documento
from conversor.domain.identity import chave_unidade
from conversor.domain.recognition import normalizar_assinatura
from conversor.readers.text_support import ErroLeitura

POLITICA = 'bbz_associacao_por_papel@1.0.0'


def registrar_temporalidade_cadastro(lote, auditoria, emissoes, *, data_ref):
    """Defasagem comprovada é ressalva; não prova troca de titular ou vigência."""
    anteriores = [e for e in emissoes if date.fromisoformat(e['emitido_em'][:10]) < data_ref]
    referencia = {'data_referencia_processamento': data_ref.isoformat(), 'emissoes': emissoes,
        'periodo_anterior': bool(anteriores), 'atualidade_atestada': False,
        'limite': 'Emissão não é vigência nem prova de titularidade atual. Associação exige unidade e identidade concordantes; conflitos ficam retidos.'}
    ressalvas = list(lote.ressalvas)
    if anteriores:
        ressalvas.append(RessalvaLeitura(codigo='BBZ_CADASTRO_PERIODO_ANTERIOR', gravidade='alerta',
            origens=tuple(Origem.model_validate(e['origem']) for e in anteriores),
            valores_originais=(json.dumps(referencia, ensure_ascii=False),)))
    return lote.model_copy(update={'ressalvas': tuple(ressalvas)}), auditoria | {'referencia_temporal': referencia}


def reter_documentos_historicos_conflitantes(lote, auditoria, conflitos):
    """Retém só a associação contestada; preserva fontes e decisão financeira."""
    if not conflitos:return lote,auditoria
    por_unidade={}
    for e in conflitos:por_unidade.setdefault(e['unidade_id'],[]).append(e)
    pessoas={p.unidade_id:p for p in lote.pessoas};saida=deepcopy(auditoria);ressalvas=list(lote.ressalvas)
    codigo='BBZ_DOCUMENTO_HISTORICO_CONFLITANTE_ASSOCIACAO_RETIDA'
    for uid,evidencias in por_unidade.items():
        p=pessoas[uid];info=saida['unidades'][uid]
        info.update(estado='associacao_retida',documento_vinculado=False,telefones_aproveitados=0,
            emails_aproveitados=0,dados_retidos=['documentos','telefones','emails'],
            projecao_antes_da_retencao=p.model_dump(mode='json'),conflitos_referencia=evidencias,
            politica_revisao_documental='bbz_revisao_documental_historica@1.0.0')
        info['motivos']=sorted(set(info['motivos']+[codigo]))
        pessoas[uid]=Pessoa.model_validate(p.model_dump()|{'documento':None,'documento_origem':None,
            'evidencias_documentais':(),'contato':Contato(endereco=p.contato.endereco,origem=p.contato.origem)})
        ressalvas.append(RessalvaLeitura(codigo=codigo,gravidade='alerta',registro_id=uid,
            origens=(p.origem,)+tuple(e.origem for e in p.evidencias_documentais)+tuple(Origem.model_validate(e['origem']) for e in evidencias),
            valores_originais=(json.dumps(info,ensure_ascii=False),)))
    resumo=saida['resumo'];infos=saida['unidades'].values()
    resumo.update(documentos_validos_vinculados=sum(i['documento_vinculado'] for i in infos),
        telefones_aproveitados=sum(i['telefones_aproveitados'] for i in infos),
        emails_aproveitados=sum(i['emails_aproveitados'] for i in infos),
        associacoes_retidas=sum(i['estado']=='associacao_retida' for i in infos),
        documentos_ausentes=sum(not resolver_documento(p).evidencias for uid,p in pessoas.items() if uid not in por_unidade),
        documentos_retidos_revisao=len(por_unidade),
        conflitos_documentais_historicos=len(por_unidade))
    return LoteCanonico(unidades=lote.unidades,boletos=lote.boletos,pessoas=tuple(pessoas[p.unidade_id] for p in lote.pessoas),
        ressalvas=tuple(ressalvas)),saida


def endereco_fisico(texto):
    """Só aceita seis campos explicitamente segmentáveis do cabeçalho físico."""
    partes=texto.rsplit(' - ',4)
    if len(partes)!=5:return Endereco()
    rua,bairro,cidade,uf,cep=partes
    m=re.fullmatch(r'(.+?)[,\s]+(\d+[A-Za-z]?|S/N)',rua)
    cep=re.sub(r'^CEP:\s*','',cep)
    if not m or not re.fullmatch(r'[A-Z]{2}',uf)or not re.fullmatch(r'\d{5}-?\d{3}',cep):
        return Endereco()
    return Endereco(logradouro=m[1].rstrip(','),numero=m[2],bairro=bairro,cidade=cidade,uf=uf,cep=cep.replace('-',''))


def cruzar_cadastro_bbz(lote, cadastro, *, endereco_configurado=None):
    financeiras={u.id:u for u in lote.unidades};cadastrais={}
    if {(u.administradora_id,u.condominio_id)for u in cadastro.unidades}!={(u.administradora_id,u.condominio_id)for u in lote.unidades}:
        raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
    if cadastro.boletos:raise ErroLeitura('CADASTRO_NAO_PODE_CRIAR_BOLETOS')
    for u in cadastro.unidades:
        key=(u.administradora_id,u.condominio_id,chave_unidade(u.bloco_original,u.unidade_original))
        if key in cadastrais:raise ErroLeitura('CADASTRO_AMBIGUO')
        cadastrais[key]=u
    pessoas={p.unidade_id:p for p in lote.pessoas};cadastradas={p.unidade_id:p for p in cadastro.pessoas}
    if len(pessoas)!=len(lote.pessoas)or len(cadastradas)!=len(cadastro.pessoas):raise ErroLeitura('TITULAR_AMBIGUO')
    try:
        fichas={r.registro_id:FichaCadastroBBZ.model_validate_json(r.valores_originais[0])for r in cadastro.ressalvas
                if r.codigo=='BBZ_CADASTRO_FICHA_ORIGINAL'}
        metas=[r for r in cadastro.ressalvas if r.codigo=='BBZ_CADASTRO_IDENTIDADE_E_COMPLETUDE']
        if len(metas)!=1 or set(fichas)!={u.id for u in cadastro.unidades}:
            raise ValueError
        if not set(financeiras)<=set(pessoas)or not set(fichas)<=set(cadastradas):raise ValueError
        meta=json.loads(metas[0].valores_originais[0])
    except (ValueError,IndexError):
        raise ErroLeitura('BBZ_CADASTRO_CONTRATO_INCOMPLETO')from None
    fisico=endereco_fisico(meta['endereco']);ressalvas=list(lote.ressalvas);auditoria={};stats=Counter()
    def alerta(codigo,u,origens,*,valores=(),gravidade='alerta'):
        ressalvas.append(RessalvaLeitura(codigo=codigo,gravidade=gravidade,registro_id=u.id,
            origens=tuple(origens),valores_originais=tuple(valores)))
    for uid,u in financeiras.items():
        original=pessoas[uid]
        cad=cadastrais.get((u.administradora_id,u.condominio_id,chave_unidade(u.bloco_original,u.unidade_original)))
        info={'unidade_id':uid,'politica':POLITICA,'estado':'sem_cadastro','motivos':[],
              'documento_vinculado':False,'telefones_aproveitados':0,'emails_aproveitados':0,
              'financeiro_original':original.model_dump(mode='json'),'dados_retidos':[]}
        if cad is None:
            info['motivos']=['CADASTRO_COMPLEMENTAR_AUSENTE']
            alerta('CADASTRO_COMPLEMENTAR_AUSENTE',u,(u.origem,));auditoria[uid]=info;continue
        if cad.id!=uid:raise ErroLeitura('NORMALIZADORES_DE_UNIDADE_INCOMPATIVEIS')
        ficha=fichas[uid];titular=cadastradas[uid]
        stats['unidades_financeiras_localizadas']+=1
        info.update(ficha=ficha.model_dump(mode='json'),cadastro_original=titular.model_dump(mode='json'))
        # Endereço físico é independente do titular. Correspondência/locação não entram.
        if fisico!=Endereco() and original.contato.endereco==Endereco():
            pessoas[uid]=Pessoa.model_validate(original.model_dump()|{'contato':original.contato.model_dump()|{'endereco':fisico}})
        if normalizar_assinatura(original.nome)!=normalizar_assinatura(titular.nome):
            info.update(estado='associacao_retida',motivos=['TITULAR_DIVERGENTE_ENTRE_FONTES'],
                        dados_retidos=['documentos','telefones','emails'])
            stats['conflitos_titulares']+=1
            alerta('TITULAR_DIVERGENTE_ENTRE_FONTES',u,(original.origem,titular.origem),
                   valores=(original.nome,titular.nome))
        elif resolver_documento(original).bloqueante:
            info.update(estado='associacao_retida',motivos=['BLOQUEIO_DOCUMENTAL_PREEXISTENTE'],
                        dados_retidos=['documentos','telefones','emails'])
        else:
            fontes=list(titular.evidencias_documentais)
            docs={documento_validado(f.documento)for f in fontes if documento_validado(f.documento)}
            antigo=resolver_documento(original).valor
            if antigo:docs.add(antigo)
            if len(docs)>1:
                info.update(estado='associacao_retida',motivos=['BBZ_DOCUMENTOS_CONFLITANTES_ASSOCIACAO_RETIDA'],
                            dados_retidos=['documentos','telefones','emails'])
                alerta('BBZ_DOCUMENTOS_CONFLITANTES_ASSOCIACAO_RETIDA',u,(original.origem,titular.origem),
                       valores=(json.dumps([f.model_dump(mode='json')for f in fontes],ensure_ascii=False),))
                if antigo:
                    pessoas[uid]=Pessoa.model_validate(pessoas[uid].model_dump()|{
                        'documento':None,'documento_origem':None,'evidencias_documentais':()})
            else:
                evidencias=list(original.evidencias_documentais)
                evidencias.extend(EvidenciaDocumento(documento=f.documento,origem=f.origem,titular_id=original.id)for f in fontes)
                # Não fundir pessoas. A evidência do titular só é vinculada após nome e unidade conferidos.
                unicas={e.model_dump_json():e for e in evidencias}
                pessoa=Pessoa.model_validate(pessoas[uid].model_dump()|{'evidencias_documentais':tuple(unicas.values()),
                    'contato':Contato(telefones=titular.contato.telefones or original.contato.telefones,
                        emails=titular.contato.emails or original.contato.emails,
                        endereco=pessoas[uid].contato.endereco,origem=titular.contato.origem)})
                pessoas[uid]=pessoa;resolucao=resolver_documento(pessoa)
                documento_vinculado=bool(resolucao.valor and any(documento_validado(f.documento)==resolucao.valor for f in fontes))
                info.update(estado='vinculado',documento_vinculado=documento_vinculado,
                            telefones_aproveitados=len(titular.contato.telefones),emails_aproveitados=len(titular.contato.emails))
                stats['documentos_validos_vinculados']+=documento_vinculado
                stats['telefones_aproveitados']+=len(titular.contato.telefones)
                stats['emails_aproveitados']+=len(titular.contato.emails)
                for codigo in resolucao.codigos:info['motivos'].append(codigo)
                for r in cadastro.ressalvas:
                    if r.registro_id==uid and r.codigo!='BBZ_CADASTRO_FICHA_ORIGINAL':ressalvas.append(r)
                if any(not t.ddd for t in titular.contato.telefones):
                    alerta('TELEFONE_SEM_DDD',u,(titular.origem,),gravidade='informativo')
        info['dados_nao_utilizados_por_papel']=['locatario','pagador','unidade','correspondencia','observacoes']
        info['fundamento']='Contato pessoal somente do titular com nome e unidade comprovados; demais papéis preservados, sem transferência automática.'
        auditoria[uid]=info
        alerta('BBZ_ASSOCIACAO_CADASTRAL_AUDITADA',u,(original.origem,titular.origem),
               valores=(json.dumps(info,ensure_ascii=False),),gravidade='informativo')
    resumo=dict(stats,unidades_cadastrais_lidas=len(cadastro.unidades),paginas=meta['paginas'],
        cabecalhos=meta['cabecalhos'],continuidades=meta['continuidades'],
        associacoes_retidas=sum(i['estado']=='associacao_retida'for i in auditoria.values()),
        documentos_ausentes=sum(not resolver_documento(p).evidencias for p in pessoas.values()),
        documentos_invalidos=sum('DOCUMENTO_INVALIDO'in resolver_documento(p).codigos for p in pessoas.values()))
    divergencias_endereco=[]
    if endereco_configurado and fisico!=Endereco():
        divergencias_endereco=[k for k in ('logradouro','numero','cep','bairro','cidade','uf')
            if normalizar_assinatura(getattr(endereco_configurado.endereco,k))!=normalizar_assinatura(getattr(fisico,k))]
        if divergencias_endereco:
            ressalvas.append(RessalvaLeitura(codigo='BBZ_ENDERECO_FISICO_DIVERGENTE',gravidade='alerta',
                origens=(cadastro.unidades[0].origem,),valores_originais=(meta['endereco'],)))
    lote_saida=LoteCanonico(unidades=lote.unidades,boletos=lote.boletos,
        pessoas=tuple(pessoas[u.id]for u in lote.unidades),ressalvas=tuple(ressalvas))
    return lote_saida,{'politica':POLITICA,'reconhecido':True,'resumo':resumo,'unidades':auditoria,
        'identidade_documental':meta,'endereco_fisico_pdf':fisico.model_dump(mode='json'),
        'endereco_original_pdf':meta['endereco'],'divergencias_endereco_configurado':divergencias_endereco,
        'limite':'Associação cadastral não autoriza cobrança, não resolve conflitos e não acrescenta unidades financeiras.'}
