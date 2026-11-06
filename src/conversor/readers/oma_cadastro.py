"""Cadastro OMA por geometria: papéis separados e continuidade comprovada.

Reutiliza a extração geométrica e contratos de evidência existentes, sem
classificar a administradora como BBZ nem reutilizar sua política de associação.
"""
import json
from datetime import datetime
import re
from conversor.domain.bbz_cadastro import CampoCadastroBBZ, FichaCadastroBBZ, ParticipanteBBZ
from conversor.domain.canonical import Contato, Documento, EvidenciaDocumento, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from conversor.domain.recognition import normalizar_assinatura
from .bbz_cadastro import FonteCadastroBBZ, SECOES, _telefone, email_valido, falha
from .passaredo_cadastro import normalizar_documento
from .text_support import id_estavel

FORMATO = 'oma_cadastro_pdf_v1'
ALIAS = 'cond. edif. pq residencial santa monica'


def conferir_identidade(identidade, contexto=None):
    if identidade['nome'] != ALIAS or identidade['codigo'] != '566':
        falha('OMA_CADASTRO_IDENTIDADE_DIVERGENTE')
    if contexto and (contexto.administradora_id,contexto.condominio_id) != ('oma','condominio_parque_santa_monica'):
        falha('OMA_CADASTRO_CONTEXTO_DIVERGENTE')


def sanitizar(lote):
    pessoas, notas = [], list(lote.ressalvas)
    for p in lote.pessoas:
        validas = []
        for ev in p.evidencias_documentais:
            doc = normalizar_documento(ev.documento.valor)
            if doc is None or doc.tipo != ev.documento.tipo:
                notas.append(RessalvaLeitura(codigo='PASSAREDO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO',
                    registro_id=p.unidade_id, origens=(ev.origem,), valores_originais=(ev.documento.valor,)))
            else:
                validas.append(ev.model_copy(update={'documento':doc}))
        pessoas.append(p.model_copy(update={'evidencias_documentais':tuple(validas)}))
    return lote.model_copy(update={'pessoas':tuple(pessoas), 'ressalvas':tuple(notas)})


class LeitorCadastroOMA:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        fonte = FonteCadastroBBZ(conteudo)
        conferir_identidade(fonte.identidade, contexto)
        emissoes = {}
        for pagina in fonte.paginas:
            rodape = next(l for l in pagina if l.y < 45 and l.texto().startswith('Emitido em '))
            try:
                emissoes[rodape.pagina] = datetime.strptime(rodape.texto()[11:30], '%d/%m/%Y %H:%M:%S')
            except ValueError:
                falha('OMA_CADASTRO_EMISSAO_INVALIDA', rodape)
        def origem(l, inicio=0, fim=600):
            return Origem(arquivo_id=contexto.arquivo_id,sha256=fonte.digest,
                leitor_versao=contexto.leitor_versao or FORMATO+'@1',pagina=l.pagina,linha=l.numero,
                identificador=f'p{l.pagina}_l{l.numero}_x{int(inicio)}_{int(fim)}',data_fonte=emissoes[l.pagina].date())
        fichas = {}; atual = None; secao = ''; papel = 'geral'; cabecalhos = 0; continuidades = 0; em_resumo=False
        for pi, linhas in enumerate(fonte.paginas,1):
            primeiro = True
            for l in linhas:
                texto = l.texto(); norm = normalizar_assinatura(texto)
                if (l.y < 45 and texto.startswith('Emitido em ')) or l.y > 750 or re.match(r'^Condom[ií]nio:',texto):
                    continue
                if l.y > 730 and texto.startswith('Endereço:'):continue
                if texto.startswith('Quantidade de Unidade por tipo'):
                    em_resumo=True;continue
                if em_resumo:
                    if texto.startswith('Bloco'):falha('BBZ_CADASTRO_CONTEUDO_APOS_RESUMO',l)
                    continue
                if texto.startswith('Bloco'):
                    pos_unidade=[x for t,x in l.partes if re.match(r'^Unidade(?:\s*:|$)',t.strip()) and 140<=x<=180]
                    pos_cliente=[x for t,x in l.partes if re.match(r'^Código do cliente(?:\s*:|$)',t.strip()) and 450<=x<=510]
                    if len(pos_unidade)!=1 or len(pos_cliente)!=1:falha('BBZ_CADASTRO_CABECALHO_UNIDADE_INVALIDO',l)
                    x_unidade,x_cliente=pos_unidade[0],pos_cliente[0]
                    bloco = re.fullmatch(r'Bloco\s*:\s*(\S+)',l.texto(0,x_unidade))
                    unidade = re.fullmatch(r'Unidade\s*:\s*(\S+)\s+-\s+(.+)',l.texto(x_unidade,x_cliente))
                    cliente = re.fullmatch(r'Código do cliente\s*:\s*(\S+)',l.texto(x_cliente,600))
                    if not all((bloco,unidade,cliente)):falha('BBZ_CADASTRO_CABECALHO_UNIDADE_INVALIDO',l)
                    chave = chave_unidade(bloco[1],unidade[1]);cabecalhos += 1
                    anterior = fichas.get(chave)
                    if anterior:
                        if (bloco[1],unidade[1])!=(anterior['bloco'],anterior['unidade']):
                            falha('BBZ_CADASTRO_COLISAO_IDENTIDADE_NORMALIZADA',l)
                        if not (primeiro and atual is anterior and pi > anterior['cabecalhos'][-1].pagina):
                            falha('BBZ_CADASTRO_UNIDADE_DUPLICADA',l)
                        if (cliente[1],normalizar_assinatura(unidade[2])) != (anterior['cliente'],normalizar_assinatura(anterior['nome'])):
                            falha('BBZ_CADASTRO_CONTINUACAO_DIVERGENTE',l)
                        continuidades += 1
                        atual = anterior
                    else:
                        atual = dict(bloco=bloco[1],unidade=unidade[1],nome=unidade[2],cliente=cliente[1],
                            cabecalhos=[],campos=[],iniciou_cobranca=False,participantes={p:dict(nome='',docs=[],tels=[],emails=[])
                            for p in ('titular','locatario','pagador','unidade')},alertas=[])
                        atual['participantes']['titular']['nome']=unidade[2]
                        fichas[chave]=atual;secao='cabecalho';papel='titular'
                    atual['cabecalhos'].append(origem(l));primeiro=False
                    continue
                if primeiro:falha('BBZ_CADASTRO_CONTINUACAO_SEM_CABECALHO',l)
                if atual is None:continue
                inicio_texto=min((x for t,x in l.partes if t.strip()),default=0)
                if norm in SECOES and 180 <= inicio_texto <= 450:
                    if norm=='endereco de cobranca':
                        if atual['iniciou_cobranca']:falha('BBZ_CADASTRO_FICHA_REPETIDA',l)
                        atual['iniciou_cobranca']=True
                    papel = SECOES[norm];secao=norm
                    continue
                if 180 <= inicio_texto <= 450 and norm.startswith(('dados do ','dados da ')) and norm not in SECOES:
                    falha('BBZ_CADASTRO_SECAO_NAO_SUPORTADA',l)
                if norm.startswith('observacoes:'):
                    papel='observacoes';secao='observacoes'
                if papel=='locatario' and texto.startswith('Locatário:'):
                    m=re.fullmatch(r'Locatário:\s*\S+\s+-\s+(.+)',texto)
                    if m:
                        atual['participantes']['locatario']['nome']=m[1]
                    elif not re.fullmatch(r'Locatário:\s*',texto):
                        falha('OMA_CADASTRO_LOCATARIO_AMBIGUO',l)
                    # Campo explicitamente vazio não identifica locatário.
                    # O original continua em campos; nunca transfere titularidade.
                if papel in ('locatario','pagador') and texto.startswith(('Nome:','Pagador:')):
                    atual['participantes'][papel]['nome']=texto.split(':',1)[1].strip()
                for inicio,fim in ((0,210),(210,392),(392,600)):
                    celula=l.texto(inicio,fim)
                    if not celula:continue
                    papel_campo = 'pagador' if secao=='dados gerais' and (
                        any('Dados do pagador' in l.texto(a,b) for a,b in ((0,210),(210,392),(392,600)))) else papel
                    # Linha específica do pagador não muda o papel das linhas gerais seguintes.
                    campo = celula.split(':',1)[0] if ':'in celula else 'texto_original'
                    atual['campos'].append(CampoCadastroBBZ(papel=papel_campo,secao=secao,campo=campo,
                        valor_original=celula,origem=origem(l,inicio,fim),x_inicio=inicio,x_fim=fim,y=l.y))
                    doc=re.fullmatch(r'(CPF|CNPJ)\s*:\s*(.*)',celula)
                    if doc and papel_campo in atual['participantes']:
                        if doc[2].strip():
                            atual['participantes'][papel_campo]['docs'].append((Documento(tipo=doc[1].lower(),valor=doc[2]),origem(l,inicio,fim)))
                if secao.startswith('telefone/e-mail'):
                    for inicio,fim in ((0,300),(300,600)):
                        celula=l.texto(inicio,fim)
                        if not celula:continue
                        m=re.fullmatch(r'(E-mail|Celular|Telefone residencial|Telefone comercial|Telefone|Fax)\s*-\s*(.*)',celula,re.I)
                        if not m:
                            atual['alertas'].append('BBZ_CONTATO_NAO_SEGMENTADO');continue
                        dados=atual['participantes'][papel]
                        if m[1].lower()=='e-mail':
                            for email in re.split(r'[;,]',m[2]):
                                email=email.strip()
                                if email_valido(email):dados['emails'].append((email,origem(l,inicio,fim)))
                                elif email:atual['alertas'].append('EMAIL_NAO_SEGMENTADO')
                        else:
                            telefones,valido=_telefone(m[2])
                            if not valido:atual['alertas'].append('TELEFONE_NAO_SEGMENTADO')
                            for telefone in telefones:dados['tels'].append((telefone,origem(l,inicio,fim)))
        if len(fichas)!=fonte.identidade['unidades_resumo']:
            falha('BBZ_CADASTRO_CONTAGEM_UNIDADES_DIVERGENTE')
        unidades=[];pessoas=[];ressalvas=[]
        for chave,f in fichas.items():
            uid=id_estavel('uni_real',contexto.condominio_id,chave);o=f['cabecalhos'][0]
            u=Unidade(id=uid,administradora_id=contexto.administradora_id,condominio_id=contexto.condominio_id,
                bloco_original=f['bloco'],unidade_original=f['unidade'],chave_normalizada=chave,
                normalizador_versao='identidade_real_v1',origem=o)
            participantes=tuple(ParticipanteBBZ(papel=p,nome=d['nome'],documentos=tuple(d['docs']),
                telefones=tuple(d['tels']),emails=tuple(d['emails']))for p,d in f['participantes'].items())
            ficha=FichaCadastroBBZ(unidade_id=uid,codigo_cliente_original=f['cliente'],cabecalhos=tuple(f['cabecalhos']),
                participantes=participantes,campos=tuple(f['campos']),alertas=tuple(sorted(set(f['alertas']))))
            titular=participantes[0];pid=id_estavel('pessoa_bbz_cadastro',uid)
            tels=list(dict.fromkeys(t for t,o in titular.telefones));emails=list(dict.fromkeys(e for e,o in titular.emails))
            p=Pessoa(id=pid,unidade_id=uid,nome=titular.nome,relacao_unidade='titular_cadastrado_bbz',origem=o,
                evidencias_documentais=tuple(EvidenciaDocumento(documento=d,origem=orig,titular_id=pid)for d,orig in titular.documentos),
                contato=Contato(telefones=tuple(tels[:5]),emails=tuple(emails[:3]),origem=o))
            unidades.append(u);pessoas.append(p)
            ressalvas.append(RessalvaLeitura(codigo='BBZ_CADASTRO_FICHA_ORIGINAL',gravidade='informativo',registro_id=uid,
                origens=ficha.cabecalhos,valores_originais=(ficha.model_dump_json(),)))
            for codigo in ficha.alertas:
                ressalvas.append(RessalvaLeitura(codigo=codigo,registro_id=uid,origens=(o,)))
            if len(tels)>5 or len(emails)>3:
                ressalvas.append(RessalvaLeitura(codigo='CONTATOS_EXCEDENTES_PRESERVADOS',registro_id=uid,origens=(o,)))
        primeiro=fonte.paginas[0][0]
        ressalvas.append(RessalvaLeitura(codigo='BBZ_CADASTRO_IDENTIDADE_E_COMPLETUDE',gravidade='informativo',
            origens=(origem(primeiro),origem(fonte.cabecalho_inicial[0]),origem(fonte.cabecalho_inicial[1]),origem(fonte.resumo_linha)),valores_originais=(json.dumps(dict(fonte.identidade,
                cabecalhos=cabecalhos,continuidades=continuidades),ensure_ascii=False,sort_keys=True),)))
        ressalvas.append(RessalvaLeitura(codigo='OMA_CADASTRO_TEMPORALIDADE', gravidade='informativo',
            origens=(origem(fonte.cabecalho_inicial[0]),), valores_originais=(json.dumps({
                'datas_emissao':sorted({d.date().isoformat() for d in emissoes.values()}),
                'paginas':len(fonte.paginas),'registros':len(unidades),'fuso_documental':None}),)))
        return sanitizar(LoteCanonico(unidades=tuple(unidades),pessoas=tuple(pessoas),boletos=(),ressalvas=tuple(ressalvas)))
