"""Habita com composição de cinco valores; versão técnica sem homologação produtiva."""
import re

from conversor.domain.canonical import documento_de_texto
from .real_support import AcervoReal, Bilhete, EMAIL, MOEDA, PDFReal, ZERO, data_real, falhar
from .text_support import VALOR_BRL, dinheiro_brl

UNIDADE=re.compile(r'^\s*Bloco:\s*(\w+)\s*•\s*Unidade:\s*(\w+)\s+(.+?)\s+(?:CPF(?:/CNPJ)?|CNPJ):\s*(.*?)\s*$')
INICIO=re.compile(r'^\s*(\d{8})\s+(?:(A|AJ|J)\s+)?(\d{2}/\d{2}/\d{2})\s+(.*)$')
CAUDA=re.compile(r'\s+('+VALOR_BRL+r')\s+('+VALOR_BRL+r')\s+('+VALOR_BRL+r')\s+('+VALOR_BRL+r')\s+('+VALOR_BRL+r')\s*$')


class LeitorHabitaReal:
    formato_id='habita_composicao_real_v1'

    def ler(self,conteudo,*,contexto):
        fonte=PDFReal(conteudo,contexto,layout=True);fonte.validar_condominio('habita')
        acc=AcervoReal(fonte);atual=None;ativo=None;geral=False;contatos={}
        for page in fonte.paginas:
            for linha in page:
                text=linha.texto.strip()
                if m:=UNIDADE.fullmatch(text):
                    if geral:falhar('UNIDADE_APOS_TOTAL_GERAL',linha)
                    unidade=acc.unidade(m[1],m[2],m[3].strip(),linha,documento_de_texto(m[4]))
                    if atual is None or atual.id!=unidade.id:ativo=None
                    atual=unidade
                    continue
                if 'Bloco:'in text and 'Unidade:'in text:falhar('CABECALHO_UNIDADE_INVALIDO',linha)
                if any(label in text for label in ('Celular:','Telefone','E-mail:')):
                    if atual is None:falhar('CONTATO_SEM_UNIDADE',linha)
                    contatos.setdefault(atual.id,[]).append(linha);continue
                cauda=CAUDA.search(linha.texto)
                if not cauda:
                    if MOEDA.search(text):
                        # Resumo suplementar após o fechamento geral: quantidade + valor;
                        # não faz parte da composição, preservado como ressalva.
                        if geral and re.fullmatch(r'[^\d]+\s+\d+\s+'+VALOR_BRL,text):
                            acc.ressalva('RESUMO_SUPLEMENTAR_PRESERVADO',linha,valores=(text,),gravidade='informativo');continue
                        falhar('LINHA_FINANCEIRA_NAO_RECONHECIDA',linha)
                    continue
                valores=tuple(dinheiro_brl(v)for v in cauda.groups())
                if sum(valores[:4],ZERO)!=valores[4]:falhar('SOMA_ITEM_INCONSISTENTE',linha)
                prefixo=' '.join(linha.texto[:cauda.start()].split())
                if prefixo=='Total do boleto:':
                    if ativo is None or ativo.totais()!=valores:falhar('SOMA_BOLETO_INCONSISTENTE',linha)
                    ativo=None;continue
                if prefixo=='Total da Unidade:':
                    if atual is None:falhar('TOTAL_SEM_UNIDADE',linha)
                    bills=[b for (uid,_),b in acc.boletos.items()if uid==atual.id]
                    total=tuple(sum((b.totais()[i]for b in bills),ZERO)for i in range(5))
                    if total!=valores:falhar('SOMA_UNIDADE_INCONSISTENTE',linha)
                    ativo=None;continue
                if re.search(r'\bTotal Geral:$',prefixo):
                    if prefixo!='Total Geral:':
                        quantidade=re.fullmatch(r'Quantidade\b[^0-9:]*:\s*(\d+)\s+Total Geral:',prefixo,re.I)
                        if not quantidade or int(quantidade[1])!=len(acc.unidades):falhar('CONTAGEM_DE_UNIDADES_DIVERGENTE',linha)
                    if geral:falhar('TOTAL_GERAL_DUPLICADO',linha)
                    total=tuple(sum((b.totais()[i]for b in acc.boletos.values()),ZERO)for i in range(5))
                    if total!=valores:falhar('SOMA_GERAL_INCONSISTENTE',linha)
                    geral=True;ativo=None;continue
                if prefixo.startswith('Total do Bloco ')and prefixo.endswith(':'):
                    bloco=prefixo[len('Total do Bloco '):-1].strip()
                    bills=[b for b in acc.boletos.values()if b.unidade.bloco_original==bloco]
                    total=tuple(sum((b.totais()[i]for b in bills),ZERO)for i in range(5))
                    if not bills or total!=valores:
                        acc.ressalva('SUBTOTAL_BLOCO_DIVERGENTE',linha,critico=True,valores=(prefixo,*map(str,valores),*map(str,total)))
                    ativo=None;continue
                if prefixo.startswith('Total'):falhar('TOTAL_NAO_RECONHECIDO',linha)
                if geral:falhar('COMPOSICAO_APOS_TOTAL_GERAL',linha)
                if m:=INICIO.fullmatch(prefixo):
                    if atual is None:falhar('BOLETO_SEM_UNIDADE',linha)
                    key=(atual.id,m[1]);venc=data_real(m[3],linha)
                    emissao=re.match(r'^(\d{6})\s+',m[4]);token=emissao[1]if emissao else None
                    if key in acc.boletos:
                        existente=acc.boletos[key]
                        if (existente is not ativo or not existente.itens or existente.itens[-1].origem.pagina!=linha.pagina-1
                            or existente.vencimento!=venc or existente.apontamento!=m[2]
                            or (token and existente.emissao_original and token!=existente.emissao_original)):
                            falhar('DUPLICIDADE_NAO_RECONCILIADA',linha)
                        ativo=existente
                        if token and existente.emissao_original is None:existente.emissao_original=token
                    else:
                        # Emissão de seis dígitos NÃO é competência. Preservar o token bruto.
                        ativo=Bilhete(atual,m[1],venc,None,m[2],token)
                        acc.boletos[key]=ativo
                    descricao=m[4]
                else:
                    if re.match(r'^\d{5,}\s+(?:\S+\s+)?\d{2}/\d{2}/\d{2}',prefixo):falhar('CABECALHO_BOLETO_INVALIDO',linha)
                    if ativo is None:falhar('COMPOSICAO_SEM_BOLETO',linha)
                    descricao=prefixo
                ativo.adicionar(valores,descricao,linha,fonte)
        if not geral:falhar('TOTAL_GERAL_AUSENTE')
        for b in acc.boletos.values():
            if b.competencia is None:
                acc.ressalva('COMPETENCIA_AUSENTE_NA_FONTE',
                    next(l for l in fonte.paginas[b.itens[0].origem.pagina-1]if l.numero==b.itens[0].origem.linha),
                    unidade=b.unidade,valores=(b.numero,))
        for uid,linhas in contatos.items():
            tels=[];emails=[]
            for l in linhas:
                emails.extend(EMAIL.findall(l.texto))
                part=l.texto.split('E-mail:')[0]
                for m in re.finditer(r'(?:\((\d{2})\)|(\d{2}))\s*(\d{4,5}[- ]?\d{4})(?!\d)',part):
                    tels.append((m[1]or m[2])+re.sub(r'\D','',m[3]))
                if re.search(r'Telefone\s+\w+:\s*\d{8}(?!\d)',part):
                    acc.ressalva('TELEFONE_SEM_DDD',l,unidade=next(u for u in acc.unidades.values()if u.id==uid),valores=(l.texto,))
            u=next(u for u in acc.unidades.values()if u.id==uid)
            acc.contato(u,linhas,tels,emails)
            acc.ressalva('CONTATO_ORIGINAL_PRESERVADO',linhas[0],unidade=u,valores=[l.texto for l in linhas],gravidade='informativo')
        for u in acc.unidades.values():
            p=acc.pessoas[u.id]
            linha=next(l for l in fonte.paginas[p.origem.pagina-1]if l.numero==p.origem.linha)
            if not p.contato.telefones:acc.ressalva('TELEFONE_AUSENTE_OU_NAO_VALIDADO',linha,unidade=u)
            if not p.contato.emails:acc.ressalva('EMAIL_AUSENTE_OU_NAO_VALIDADO',linha,unidade=u)
        return acc.resultado()
