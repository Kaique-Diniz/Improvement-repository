"""Diferenças do histórico frente à saída atual; nunca altera dados ou elegibilidade."""
from collections import Counter
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from io import BytesIO
from typing import Literal

from openpyxl import load_workbook
from pydantic import Field

from conversor.domain.base import Modelo,Id
from conversor.domain.template import COLUNAS
from .contract import materializar


class DivergenciaTemplate(Modelo):
    categoria: Literal['formato_resolvido','cadastral','identificador','financeira','sem_explicacao']
    codigo: Id
    linha_excel: int = Field(ge=1)
    campos: tuple[str,...] = ()
    revisao_humana: bool = False


def texto(v):return ''if v is None else str(v)


def data(v):
    if isinstance(v,datetime):return v.date()
    if type(v)is date:return v
    if isinstance(v,str):
        for fmt in('%d/%m/%Y','%Y-%m-%d'):
            try:return datetime.strptime(v,fmt).date()
            except ValueError:pass
    return None


def valor(v):
    if v is None or isinstance(v,bool):return None
    try:
        n=Decimal(str(v))
        return n if n.is_finite()else None
    except(InvalidOperation,ValueError):return None


def classificar_historico(conteudo,*,linhas,linhas_info,identificadores,comparacao,modo,descricoes=None):
    divergencias=[]
    def add(categoria,codigo,n,campos=(),revisao=False):
        divergencias.append(DivergenciaTemplate(categoria=categoria,codigo=codigo,linha_excel=n,
            campos=tuple(campos),revisao_humana=revisao))
    if comparacao.get('codigo'):
        add('sem_explicacao',comparacao['codigo'],1,revisao=True)
        return finalizar(divergencias)
    esperadas=[(info,materializar(linha).valores)for info,linha in zip(linhas_info,linhas,strict=True)]
    por_codigo={}
    for uid,cod in identificadores.items():por_codigo.setdefault((cod['cedente'],cod['complemento']),[]).append(uid)
    anteriores={r['linha_excel']:r for r in comparacao['linhas']}
    w=load_workbook(BytesIO(conteudo),read_only=True,data_only=False,keep_links=False)
    try:
        aba=w[comparacao['aba_referencia']];rows=list(aba.values)
        if aba.title!='Dados':add('formato_resolvido','ABA_ATUAL_DADOS',1,('aba',))
        if tuple(rows[0][:30])!=COLUNAS:add('formato_resolvido','CABECALHOS_ATUAIS_LITERAIS',1,('cabecalhos',))
        cadastros_vistos=set()
        for n,row in enumerate(rows[1:],2):
            if any(v is not None and v!=''for v in row[30:]):
                add('formato_resolvido','ANOTACOES_FORA_DAS_30_COLUNAS',n,('fora_A_AD',))
            row=tuple(row[:30])
            if not any(v is not None for v in row):continue
            cadastral=all(v is None or v==''for v in row[24:30])
            chave=texto(row[1]),texto(row[6])
            textuais=[COLUNAS[j]for j in(2,7,*range(11,21))if row[j]is not None and not isinstance(row[j],str)]
            if textuais:add('formato_resolvido','CAMPOS_TEXTUAIS_NO_CONTRATO_ATUAL',n,textuais)
            if cadastral:
                if chave in cadastros_vistos:add('formato_resolvido','CADASTRO_HISTORICO_DUPLICADO',n,('CEDENTE',))
                cadastros_vistos.add(chave)
                if modo=='A':add('formato_resolvido','MODO_A_SOMENTE_FINANCEIRO',n,tuple(COLUNAS[24:30]))
            ids=por_codigo.get(chave,[])
            if len(ids)!=1:
                add('identificador','VINCULO_UNIDADE_NAO_COMPROVADO',n,('CEDENTE','COMPLEMENTO'),True)
                if cadastral:add('cadastral','CADASTRO_HISTORICO_FORA_DA_SELECAO',n,('CEDENTE',))
                continue
            uid=ids[0];unidade=[(i,v)for i,v in esperadas if i['unidade_id']==uid]
            candidatas=[(i,v)for i,v in unidade if i['tipo']==('cadastral'if cadastral else'divida')]
            if cadastral:
                if not candidatas:add('cadastral','CADASTRO_HISTORICO_FORA_DA_POLITICA_ATUAL',n,('CEDENTE',))
                atual=unidade[0][1]if unidade else None
            else:
                # Rótulo idêntico só vincula após identidade da unidade comprovada.
                exatas=[(i,v)for i,v in candidatas if texto(v[26])==texto(row[26])]
                candidatas=exatas if len(exatas)==1 else[(i,v)for i,v in candidatas if v[28]==data(row[28])]
                if len(candidatas)>1:candidatas=[(i,v)for i,v in candidatas if v[29]==valor(row[29])]
                if len(candidatas)!=1:
                    categoria='financeira'if anteriores.get(n,{}).get('categoria')=='regras'else'sem_explicacao'
                    add(categoria,'LINHA_FINANCEIRA_HISTORICA_NAO_VINCULADA',n,tuple(COLUNAS[24:30]),True)
                    continue
                atual=candidatas[0][1]
                financeiros=[]
                if atual[28]!=data(row[28]):financeiros.append('VENCIMENTO')
                if atual[29]!=valor(row[29]):financeiros.append('VL_PARCELA')
                if financeiros:add('financeira','DADOS_FINANCEIROS_DIVERGENTES',n,financeiros,True)
                if texto(atual[26])!=texto(row[26]):
                    descricao=(descricoes or {}).get(candidatas[0][0].get('boleto_id'))
                    if descricao:
                        add('sem_explicacao', 'DESCRICAO_DA_OBRIGACAO_EM_REVISAO' if descricao.estado=='pendente'
                            else 'DESCRICAO_DOCUMENTAL_DIFERE_DO_HISTORICO',n,('NM_DIVIDA_CEDENTE',),True)
                    else:
                        add('formato_resolvido','ROTULO_ATUAL_NAO_INFERE_COMPETENCIA',n,('NM_DIVIDA_CEDENTE',))
                if atual[27]!=row[27]:add('formato_resolvido','PARCELAS_SEQUENCIAIS_POR_CONTRATO',n,('NU_PARCELA',))
            if atual is None:continue
            contatos=[COLUNAS[j]for j in range(2,24)if j!=6 and texto(atual[j])!=texto(row[j])]
            if contatos:add('cadastral','CONTATOS_DA_FONTE_ATUAL_DIFEREM_DO_HISTORICO',n,contatos)
            campos_identidade=(0,1,6)if cadastral else(0,1,6,24,25)
            ids_diff=[COLUNAS[j]for j in campos_identidade if texto(atual[j])!=texto(row[j])]
            if ids_diff:add('identificador','CODIFICACAO_ATUAL_DIFERE_DO_HISTORICO',n,ids_diff,True)
        return finalizar(divergencias)
    finally:w.close()


def finalizar(divergencias):
    ordenadas=sorted(divergencias,key=lambda d:(d.linha_excel,d.categoria,d.codigo))
    return {'contrato_atual_preservado':True,'historico_nao_e_contrato_definitivo':True,
        'nenhum_dado_ou_decisao_alterado':True,'resumo_por_categoria':dict(Counter(d.categoria for d in ordenadas)),
        'divergencias':[d.model_dump(mode='json')for d in ordenadas]}
