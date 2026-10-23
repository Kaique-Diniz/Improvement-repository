"""Única entrada de simulação: configuração verificada, pin de versão e revalidação."""
from hashlib import sha256

from pydantic import ValidationError

from conversor.domain.billing_evaluation import (EntradaSimulacao, SolicitacaoSimulacao, ProvaPlanoSimulado,
    RelatorioSimulacao, DecisaoBoletoSimulada, DecisaoUnidadeSimulada)
from conversor.domain.billing_rules import EstadoPlanos, ErroPlano, bytes_canonicos, hash_modelo
from conversor.domain.billing_lifecycle import conferir_acervo
from conversor.domain.canonical import Ocorrencia
from conversor.rules.conditions import origens_unicas
from conversor.rules.engine import avaliar_regras, resolver_candidatos
from .billing_ports import RepositorioPlanos
from .billing_evaluation_ports import VerificadorEstadoPlanos
from .documents import ocorrencias_documentais
from .ports import ErroAplicacao


def normalizar_entrada(entrada):
    """Só ordenar coleções; não transformar conteúdo/valores dos documentos."""
    dados=entrada.model_dump(warnings=False)
    lote=dados['lote']
    for nome in ('unidades','boletos','pessoas'):
        lote[nome]=sorted(lote[nome],key=lambda x:x['id'])
    lote['ressalvas']=[r.model_dump()for r in sorted(entrada.lote.ressalvas,key=hash_modelo)]
    dados['fatos']=sorted(dados['fatos'],key=lambda x:x['id'])
    dados['ocorrencias_anteriores']=sorted(dados['ocorrencias_anteriores'],key=lambda x:x['id'])
    dados['coberturas_apontamentos']=sorted(dados['coberturas_apontamentos'],key=lambda x:(x['boleto_id'],x['namespace']))
    return EntradaSimulacao.model_validate(dados)


def conferir_entrada(entrada,plano,solicitacao):
    unidades={u.id:u for u in entrada.lote.unidades}
    boletos={b.id:b for b in entrada.lote.boletos}
    pessoas={p.id:p for p in entrada.lote.pessoas}
    if not unidades or {u.condominio_id for u in unidades.values()}!={solicitacao.condominio_id}:
        raise ErroAplicacao('LOTE_DE_OUTRO_CONDOMINIO_OU_VAZIO')
    if len(set(unidades)|set(boletos)|set(pessoas))!=len(unidades)+len(boletos)+len(pessoas):
        raise ErroAplicacao('IDENTIDADES_AMBIGUAS_ENTRE_ENTIDADES')
    fatos={f.id:f for f in plano.fatos}
    for f in entrada.fatos:
        definicao=fatos.get(f.fato_id)
        if f.condominio_id!=plano.condominio_id or f.unidade_id not in unidades:
            raise ErroAplicacao('FATO_DE_OUTRO_CONDOMINIO_OU_UNIDADE')
        if definicao is None or definicao.tipo!=f.valor.tipo:
            raise ErroAplicacao('FATO_NAO_DECLARADO_OU_TIPO_INVALIDO')
        if definicao.escopo=='unidade'and f.boleto_id is not None:
            raise ErroAplicacao('ESCOPO_DO_FATO_INVALIDO')
        if definicao.escopo=='boleto'and(f.boleto_id not in boletos or boletos[f.boleto_id].unidade_id!=f.unidade_id):
            raise ErroAplicacao('BOLETO_DO_FATO_INCOMPATIVEL')
    for c in entrada.coberturas_apontamentos:
        if c.boleto_id not in boletos:raise ErroAplicacao('COBERTURA_DE_BOLETO_INEXISTENTE')
        fontes_boleto={(o.arquivo_id,o.sha256)for o in boletos[c.boleto_id].origens}
        if any((o.arquivo_id,o.sha256)not in fontes_boleto for o in c.origens):
            raise ErroAplicacao('COBERTURA_SEM_VINCULO_COM_FONTE_DO_BOLETO')
    # Mesmo ID de arquivo com hashes diferentes é uma origem ambígua, não uma escolha de fonte.
    fontes={}
    def percorrer(dados):
        if isinstance(dados,dict):
            if {'arquivo_id','sha256','leitor_versao','identificador'}<=dados.keys():
                anterior=fontes.setdefault(dados['arquivo_id'],dados['sha256'])
                if anterior!=dados['sha256']:raise ErroAplicacao('HASHES_DE_ORIGEM_CONFLITANTES')
            for valor in dados.values():percorrer(valor)
        elif isinstance(dados,(tuple,list)):
            for valor in dados:percorrer(valor)
    percorrer(entrada.model_dump(mode='json'))
    percorrer(plano.model_dump(mode='json'))


def ocorrencias_da_entrada(entrada,processamento_id):
    ocorrencias=list(entrada.ocorrencias_anteriores)
    for i,r in enumerate(entrada.lote.ressalvas):
        ocorrencias.append(Ocorrencia(id='ressalva:'+sha256(f'{i}:{hash_modelo(r)}'.encode()).hexdigest(),
            processamento_id=processamento_id,codigo=r.codigo,gravidade=r.gravidade,
            escopo='registro'if r.registro_id else'arquivo',registro_id=r.registro_id,origem=r.origens[0]))
    for p in entrada.lote.pessoas:
        ocorrencias.extend(ocorrencias_documentais(p,processamento_id=processamento_id))
    # IDs de execuções anteriores são preservados; nunca reescrever uma evidência.
    mapa={}
    for o in ocorrencias:
        if o.id in mapa and mapa[o.id]!=o:raise ErroAplicacao('OCORRENCIAS_COM_MESMO_ID_DIVERGENTES')
        mapa[o.id]=o
    return tuple(mapa[k]for k in sorted(mapa))


def ocorrencias_aplicaveis(ocorrencias,unidade,boleto,lote):
    pessoas={p.id:p.unidade_id for p in lote.pessoas}
    unidades={u.id for u in lote.unidades};boletos={b.id for b in lote.boletos}
    conhecidas=unidades|boletos|pessoas.keys()
    return tuple(o for o in ocorrencias if o.escopo!='registro'or o.registro_id not in conhecidas
        or o.registro_id in (unidade.id,boleto.id if boleto else None)or pessoas.get(o.registro_id)==unidade.id)


class SimularCobranca:
    """Fonte e verificador explícitos. Nunca recebe aprovação/estado do chamador.

    O verificador é configurado pelo host e confere a autoridade/revisão atual.
    Backend substituto deve manter essa garantia, não somente desserializar JSON.
    """
    def __init__(self,repositorio: RepositorioPlanos,verificador: VerificadorEstadoPlanos):
        self.repositorio=repositorio
        self.verificador=verificador

    def executar(self,solicitacao: SolicitacaoSimulacao,entrada: EntradaSimulacao) -> RelatorioSimulacao:
        try:
            solicitacao=SolicitacaoSimulacao.model_validate(solicitacao.model_dump(warnings=False))
            entrada=normalizar_entrada(EntradaSimulacao.model_validate(entrada.model_dump(warnings=False)))
            estado=EstadoPlanos.model_validate(self.repositorio.carregar().model_dump(warnings=False))
            self.verificador.conferir(estado)
            conferir_acervo(estado.acervo)
            registros=[r for r in estado.acervo.registros if r.conteudo.id==solicitacao.plano_id]
            if len(registros)!=1:raise ErroAplicacao('PLANO_SOLICITADO_INDISPONIVEL')
            registro=registros[0];plano=registro.conteudo
            if estado.acervo.ambiente!=solicitacao.ambiente or plano.condominio_id!=solicitacao.condominio_id:
                raise ErroAplicacao('PLANO_DE_OUTRO_AMBIENTE_OU_CONDOMINIO')
            if (plano.versao,hash_modelo(plano))!=(solicitacao.plano_versao,solicitacao.plano_hash):
                raise ErroAplicacao('VERSAO_OU_HASH_SOLICITADO_DIVERGENTE')
            if registro.estado!='ativo':raise ErroAplicacao('PLANO_NAO_ATIVO_OU_REVOGADO')
            if not(plano.vigente_de<=solicitacao.data_ref and(plano.vigente_ate is None or solicitacao.data_ref<plano.vigente_ate)):
                raise ErroAplicacao('DATA_REF_FORA_DA_VIGENCIA_DO_PLANO')
            aprovacoes=[e for e in estado.acervo.eventos if e.plano_id==plano.id and e.acao=='aprovar']
            ativacoes=[e for e in estado.acervo.eventos if e.plano_id==plano.id and e.acao=='ativar']
            if not aprovacoes or not ativacoes:raise ErroAplicacao('APROVACAO_OU_ATIVACAO_AUSENTE')
            conferir_entrada(entrada,plano,solicitacao)
            prova=ProvaPlanoSimulado(revisao_repositorio=estado.revisao,hash_estado=hash_modelo(estado),
                aprovacao_sequencia=aprovacoes[-1].sequencia,aprovacao_hash=hash_modelo(aprovacoes[-1]),
                ativacao_sequencia=ativacoes[-1].sequencia,ativacao_hash=hash_modelo(ativacoes[-1]))
            ocorrencias=ocorrencias_da_entrada(entrada,solicitacao.processamento_id)
            decisoes=[];resumos=[]
            for unidade in entrada.lote.unidades:
                aval_unidade=avaliar_regras(plano,entrada,solicitacao.data_ref,unidade)
                bills=[b for b in entrada.lote.boletos if b.unidade_id==unidade.id]
                por_unidade=[]
                for boleto in bills:
                    aval_boleto=avaliar_regras(plano,entrada,solicitacao.data_ref,unidade,boleto)
                    candidato=resolver_candidatos(aval_unidade,aval_boleto)
                    locais=ocorrencias_aplicaveis(ocorrencias,unidade,boleto,entrada.lote)
                    criticos=[o for o in locais if o.bloqueante]
                    situacao='bloqueado'if criticos else candidato.situacao
                    motivo='BLOQUEIO_CRITICO_PRESERVADO'if criticos else candidato.motivo
                    d=DecisaoBoletoSimulada(unidade_id=unidade.id,boleto_id=boleto.id,situacao=situacao,
                        motivo_codigo=motivo,motivo_regras=candidato.motivo,
                        revisao_humana=bool(criticos)or candidato.revisao_humana,
                        regras_decisivas=candidato.regras,avaliacoes=(*aval_unidade,*aval_boleto),
                        ocorrencias_preservadas=locais,origens=origens_unicas((*boleto.origens,
                            *(o for r in (*aval_unidade,*aval_boleto)for o in r.passo.origens))))
                    por_unidade.append(d);decisoes.append(d)
                estados={d.situacao for d in por_unidade}
                # Resumo, não autorização genérica ou propagação inversa de estado.
                ordem=('bloqueado','pendente_revisao','elegivel_na_simulacao','excluido')
                resumo=next((s for s in ordem if s in estados),'pendente_revisao')
                motivo='RESUMO_DOS_BOLETOS'if len(estados)<=1 else'UNIDADE_COM_DECISOES_MISTAS'
                if len(estados)>1 and resumo!='bloqueado':resumo='pendente_revisao'
                if not bills:
                    candidato=resolver_candidatos(aval_unidade,())
                    resumo=candidato.situacao;motivo=candidato.motivo
                    if any(o.bloqueante for o in ocorrencias_aplicaveis(ocorrencias,unidade,None,entrada.lote)):
                        resumo='bloqueado';motivo='BLOQUEIO_CRITICO_PRESERVADO'
                resumos.append(DecisaoUnidadeSimulada(unidade_id=unidade.id,situacao=resumo,motivo_codigo=motivo,
                    avaliacoes=aval_unidade,boletos_ids=tuple(b.id for b in bills),origens=(unidade.origem,)))
            # Revogação/alteração administrativa concorrente invalida a avaliação,
            # inclusive se outra versão do mesmo conteúdo foi ativada no intervalo.
            self.verificador.conferir(estado)
            atual=self.repositorio.carregar()
            if hash_modelo(atual)!=prova.hash_estado:raise ErroAplicacao('CONFIGURACAO_ALTERADA_DURANTE_SIMULACAO')
            return RelatorioSimulacao(solicitacao=solicitacao,prova_plano=prova,hash_entrada=hash_modelo(entrada),
                unidades=tuple(resumos),boletos=tuple(decisoes),ocorrencias_anteriores=ocorrencias,
                ressalvas_origem=entrada.lote.ressalvas,fatos_recebidos=entrada.fatos,
                coberturas_recebidas=entrada.coberturas_apontamentos)
        except ErroAplicacao:
            raise
        except ErroPlano as erro:
            raise ErroAplicacao(str(erro))from None
        except (ValidationError,UnicodeError):
            raise ErroAplicacao('CONTRATO_DE_SIMULACAO_INVALIDO')from None
