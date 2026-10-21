"""Cadastro FL W045A por colunas, sem escolher titular em situações ambíguas."""
import json
import re

from conversor.domain.canonical import EvidenciaDocumento, Pessoa, documento_de_texto
from conversor.domain.recognition import normalizar_assinatura
from .real_support import AcervoReal, PDFReal, falhar
from .contact_segments import segmentar_emails, segmentar_endereco, segmentar_telefones


class LeitorCadastroFLReal:
    formato_id='cadastro_fl_real_v1'

    def ler(self,conteudo,*,contexto):
        fonte=PDFReal(conteudo,contexto,coordenadas=True);fonte.validar_condominio('cadastro')
        for label,inicio,fim in [('Unidade',30,40),('Nome/Telefone/Celular',90,220),('Tipo',240,330),
                                 ('Endereço',345,525),('CPF/CNPJ',533,590),('E-mail',600,740)]:
            xs=[x for page in fonte.fragmentos for l,x,y in page if normalizar_assinatura(l.texto)==normalizar_assinatura(label)]
            if not xs or any(not inicio<=x<fim for x in xs):falhar('COLUNAS_CADASTRAIS_INCOMPATIVEIS')
        acc=AcervoReal(fonte);registros=[];atual=None
        for pi,page in enumerate(fonte.fragmentos,1):
            fonte.rodape_validado(pi)
            for linha,x,y in page:
                if y<=65:continue
                s=linha.texto.strip()
                if 30<x<40 and (m:=re.fullmatch(r'(\d{4})\s+TORRE(?:\s+(\w+))?',s)):
                    atual={'numero':m[1],'bloco':m[2],'linha':linha,'campos':[]}
                    registros.append(atual);continue
                if atual is None:continue
                if 30<x<40 and re.fullmatch(r'[A-Z]',s):
                    if atual['bloco']is not None:falhar('CADASTRO_TORRE_DUPLICADA',linha)
                    atual['bloco']=s;continue
                if re.search(r'Emitido em|W045A|Cadastro de unidades',s):continue
                if s in ('Unidade','Nome/Telefone/Celular','Tipo','Endereço','CPF/CNPJ','E-mail'):continue
                campo=None
                if 90<=x<220:campo='telefone'if re.fullmatch(r'[\d\s+();.,/\-]+',s)else'nome'
                elif 240<=x<330:campo='tipo'
                elif 345<=x<525:campo='endereco'
                elif 533<=x<590:campo='documento'
                elif 600<=x<740:campo='email'
                if campo:atual['campos'].append((campo,linha,x,y))
        vistas=set()
        for r in registros:
            if not r['bloco']:falhar('CADASTRO_IDENTIDADE_INCOMPLETA',r['linha'])
            chave=(r['bloco'],r['numero'])
            if chave in vistas:falhar('CADASTRO_AMBIGUO',r['linha'])
            vistas.add(chave)
            nomes=[l.texto for c,l,x,y in r['campos']if c=='nome']
            if not nomes:falhar('CADASTRO_SEM_NOME',r['linha'])
            u=acc.unidade(r['bloco'],r['numero'],' '.join(nomes),r['linha'])
            p=acc.pessoas[u.id];docs=[];telefones=[];enderecos=[]
            for campo,l,x,y in r['campos']:
                if campo=='documento':
                    doc=documento_de_texto(l.texto)
                    if doc:docs.append((doc,fonte.origem(l)))
                elif campo=='endereco':enderecos.append(l)
            telefone_linhas=[l for c,l,x,y in r['campos']if c=='telefone']
            telefones,pendentes=segmentar_telefones([l.texto for l in telefone_linhas])
            if pendentes:acc.ressalva('TELEFONE_INVALIDO_OU_SEM_DDD',telefone_linhas[0],unidade=u,valores=pendentes)
            email_linhas=[l for c,l,x,y in r['campos']if c=='email']
            emails,pendentes=segmentar_emails([l.texto for l in email_linhas])
            if pendentes:acc.ressalva('EMAIL_NAO_SEGMENTADO',email_linhas[0],unidade=u,valores=pendentes)
            tipos=[l.texto for c,l,x,y in r['campos']if c=='tipo']
            multiplos=len({(d.tipo,d.valor)for d,_ in docs})>1 or len(tipos)>1 or any('/'in n for n in nomes)
            evidencias=tuple(EvidenciaDocumento(documento=d,origem=o,titular_id=None if multiplos else p.id)for d,o in docs)
            p=Pessoa.model_validate(p.model_dump()|{'documento':None,'evidencias_documentais':evidencias,
                'relacao_unidade':'titular_nao_resolvido'if multiplos else'titular_informado_na_fonte'})
            acc.pessoas[u.id]=p
            if multiplos:acc.ressalva('TITULAR_MULTIPLO_OU_NAO_SEGMENTADO',r['linha'],unidade=u,critico=True,valores=nomes)
            endereco,pendencia=segmentar_endereco([l.texto for l in enderecos])
            if pendencia:
                acc.ressalva(pendencia,enderecos[0]if enderecos else r['linha'],unidade=u,
                    critico=pendencia=='ENDERECOS_MULTIPLOS_NAO_SEGMENTADOS',valores=[l.texto for l in enderecos])
            else:
                acc.ressalva('ENDERECO_SEGMENTADO_DA_FONTE',enderecos[0],unidade=u,gravidade='informativo',
                    valores=[l.texto for l in enderecos])
            # Dados não segmentados/contatos excedentes nunca são descartados silenciosamente.
            acc.ressalva('CADASTRO_CAMPOS_ORIGINAIS',r['linha'],unidade=u,gravidade='informativo',
                valores=[json.dumps({'campo':c,'texto':l.texto,'origem':fonte.origem(l).model_dump(mode='json'),'x':x,'y':y},ensure_ascii=False)
                         for c,l,x,y in r['campos']])
            contato_linhas=[l for c,l,x,y in r['campos']if c in ('telefone','email','endereco')]
            acc.contato(u,contato_linhas or [r['linha']],telefones,emails,endereco)
            if not telefones:acc.ressalva('TELEFONE_AUSENTE_OU_NAO_VALIDADO',r['linha'],unidade=u)
            if not emails:acc.ressalva('EMAIL_AUSENTE_OU_NAO_VALIDADO',r['linha'],unidade=u)
        return acc.resultado()
