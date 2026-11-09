"""Cadastro Beach Parque por geometria: papéis separados e continuidade comprovada.

Reutiliza a extração geométrica e contratos de evidência existentes, sem
classificar a administradora como BBZ nem reutilizar sua política de associação.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
import re
from conversor.domain.bbz_cadastro import CampoCadastroBBZ, FichaCadastroBBZ, ParticipanteBBZ
from conversor.domain.canonical import Contato, Documento, EvidenciaDocumento, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from conversor.domain.recognition import normalizar_assinatura
from .bbz_cadastro import FonteCadastroBBZ, SECOES, _telefone, email_valido, falha
from .passaredo_cadastro import normalizar_documento
from .text_support import id_estavel

FORMATO = 'beach_parque_cadastro_pdf_v1'
ALIAS = 'terraco beach parque'

CONTATO_SEGMENTADO = 'BPQ_CONTATO_ANOTADO_SEGMENTADO'
CONTATO_AMBIGUO = 'BPQ_CONTATO_ATRIBUICAO_AMBIGUA'
CONTATO_TERCEIRO = 'BPQ_CONTATO_TERCEIRO_IDENTIFICADO'
ANOTACAO_DESCONHECIDA = 'BPQ_CONTATO_ANOTACAO_DESCONHECIDA'
DIAGNOSTICOS_CONTATO = {CONTATO_SEGMENTADO, CONTATO_AMBIGUO, CONTATO_TERCEIRO,
    ANOTACAO_DESCONHECIDA, 'EMAIL_NAO_SEGMENTADO', 'TELEFONE_NAO_SEGMENTADO',
    'BBZ_CONTATO_NAO_SEGMENTADO'}
ROTULO_CONTATO = re.compile(r'(E-mail|Celular|Telefone residencial|Telefone comercial|Telefone|Fax)\s*-\s*(.*)', re.I)
ATUALIZACAO = r'(?:atualizad[oa]|alterad[oa]) em ([0-9]{2}/[0-9]{2}/[0-9]{4})\.?'
ANOTACOES_NEUTRAS = (
    re.compile(r'(.+?)\s+-\s+(' + ATUALIZACAO + r')', re.I),
    re.compile(r'(.+?)\s+\((' + ATUALIZACAO + r')\)\.?', re.I),
)


@dataclass(frozen=True)
class ContatoSegmentado:
    """Resultado local; seção, papel e geometria ficam em CampoCadastroBBZ.

    Nenhuma anotação é prova de titularidade ou de vigência. Os valores brutos
    ficam separados dos normalizados e nunca participam do repr/log de erros.
    """
    rotulo: str
    valor_original: str = field(repr=False)
    anotacao_original: str = field(default='', repr=False)
    telefones: tuple = field(default=(), repr=False)
    emails: tuple = field(default=(), repr=False)
    codigo: str | None = None


def segmentar_contato(celula):
    """Gramática BPQ fechada: campo completo, opcionalmente anotação neutra.

    Não busca o primeiro número/endereço em texto livre. Desconhecidos e
    atribuições a terceiros bloqueiam o campo inteiro, inclusive listas.
    """
    m = ROTULO_CONTATO.fullmatch(celula)
    if not m:
        return ContatoSegmentado('', celula, codigo='BBZ_CONTATO_NAO_SEGMENTADO')
    rotulo, original = m[1], m[2].strip()
    email = rotulo.lower() == 'e-mail'
    valor, anotacao = original, ''
    for padrao in ANOTACOES_NEUTRAS:
        anotado = padrao.fullmatch(original)
        if anotado:
            try:
                datetime.strptime(anotado[3], '%d/%m/%Y')
            except ValueError:
                return ContatoSegmentado(rotulo, original, codigo=ANOTACAO_DESCONHECIDA)
            valor, anotacao = anotado[1].strip(), anotado[2]
            break
    if email:
        partes = tuple(p.strip() for p in re.split(r'[;,]', valor) if p.strip())
        valido = bool(partes) and all(email_valido(p) for p in partes)
        telefones, emails = (), tuple(dict.fromkeys(partes)) if valido else ()
    else:
        telefones, valido = _telefone(valor)
        emails = ()
    if valido:
        return ContatoSegmentado(rotulo, original, anotacao, telefones, emails,
            CONTATO_SEGMENTADO if anotacao else None)
    # Estas buscas só classificam a rejeição; nunca recuperam um contato.
    if re.search(r'(?:telefone|contato|e-mail) d[oa] (?:filh[oa]|locat[aá]ri[oa]|pagador|familiar|representante|funcion[aá]ri[oa]|espos[oa]|marido)\b', original, re.I):
        codigo = CONTATO_TERCEIRO
    elif re.search(r'(?:verificar|conferir|confirmar) (?:titular|titularidade|respons[aá]vel)\b', original, re.I):
        codigo = CONTATO_AMBIGUO
    elif re.search(r'\s+-\s+|\([^)]*[A-Za-z]', original) or anotacao:
        codigo = ANOTACAO_DESCONHECIDA
    else:
        codigo = 'EMAIL_NAO_SEGMENTADO' if email else 'TELEFONE_NAO_SEGMENTADO'
    return ContatoSegmentado(rotulo, original, anotacao, codigo=codigo)


def conferir_identidade(identidade, contexto=None):
    if identidade['nome'] != ALIAS or identidade['codigo'] != '3075':
        falha('BPQ_CADASTRO_IDENTIDADE_DIVERGENTE')
    if contexto and (contexto.administradora_id,contexto.condominio_id) != ('habitacional','condominio_terraco_beach_parque'):
        falha('BPQ_CADASTRO_CONTEXTO_DIVERGENTE')


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


class FonteCadastroBeach(FonteCadastroBBZ):
    """Extração limitada compartilhada; identidade e cabeçalho próprios.

    A fonte não imprime CNPJ no cabeçalho. Nenhum documento é inferido.
    """
    def _conferir(self):
        identidades=set();enderecos=set();resumo=None
        for pi, linhas in enumerate(self.paginas,1):
            if sum(l.texto()=='Relatório de Unidades - Completo' for l in linhas)!=1:
                falha('BPQ_CADASTRO_TITULO_INVALIDO')
            rodapes=[l for l in linhas if l.y<45 and l.texto().startswith('Emitido em ')]
            m=re.fullmatch(r'Emitido em [0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} - Página ([0-9]+) de ([0-9]+)',rodapes[0].texto()) if len(rodapes)==1 else None
            if not m or tuple(map(int,m.groups()))!=(pi,len(self.paginas)):
                falha('BPQ_CADASTRO_PAGINACAO_INVALIDA')
            headers=[l for l in linhas if re.match(r'^Condom[ií]nio\s*:',l.texto())]
            if len(headers)!=1 or headers[0].y<=730:
                falha('BPQ_CADASTRO_IDENTIDADE_INCOMPLETA', headers[0] if headers else linhas[0])
            m=re.fullmatch(r'Condom[ií]nio\s*:\s*([0-9]+)\s*-\s*(.+)',headers[0].texto())
            if not m:falha('BPQ_CADASTRO_IDENTIDADE_INVALIDA')
            identidades.add((m[1],normalizar_assinatura(m[2])))
            ends=[l for l in linhas if l.y>730 and l.texto().startswith('Endereço:')]
            if len(ends)!=1:falha('BPQ_CADASTRO_ENDERECO_CABECALHO_INVALIDO')
            enderecos.add(ends[0].texto()[len('Endereço:'):].strip())
            if pi==1:self.cabecalho_inicial=(headers[0],ends[0])
            totais=[l for l in linhas if l.texto().startswith('Total de Unidade')]
            if totais:
                if pi!=len(self.paginas) or len(totais)!=1 or resumo is not None:
                    falha('BPQ_CADASTRO_RESUMO_AMBIGUO')
                m=re.fullmatch(r'Total de Unidade\s*([0-9]+)',totais[0].texto(0,210))
                if not m:falha('BPQ_CADASTRO_RESUMO_INVALIDO')
                resumo=int(m[1]);self.resumo_linha=totais[0]
        if len(identidades)!=1 or len(enderecos)!=1 or not resumo:
            falha('BPQ_CADASTRO_COMPLETUDE_INVALIDA')
        codigo,nome=next(iter(identidades))
        result=dict(codigo=codigo,nome=nome,unidades_resumo=resumo,paginas=len(self.paginas))
        conferir_identidade(result)
        return result


def identificar(conteudo):
    return FonteCadastroBeach(conteudo).identidade


class LeitorCadastroBeachParque:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        fonte = FonteCadastroBeach(conteudo)
        conferir_identidade(fonte.identidade, contexto)
        emissoes = {}
        for pagina in fonte.paginas:
            rodape = next(l for l in pagina if l.y < 45 and l.texto().startswith('Emitido em '))
            try:
                emissoes[rodape.pagina] = datetime.strptime(rodape.texto()[11:30], '%d/%m/%Y %H:%M:%S')
            except ValueError:
                falha('BPQ_CADASTRO_EMISSAO_INVALIDA', rodape)
        def origem(l, inicio=0, fim=600):
            return Origem(arquivo_id=contexto.arquivo_id,sha256=fonte.digest,
                leitor_versao=contexto.leitor_versao or FORMATO+'@1',pagina=l.pagina,linha=l.numero,
                identificador=f'p{l.pagina}_l{l.numero}_x{int(inicio)}_{int(fim)}',data_fonte=emissoes[l.pagina].date())
        fichas = {}; atual = None; secao = ''; papel = 'geral'; cabecalhos = 0; continuidades = 0; em_resumo=False
        for pi, linhas in enumerate(fonte.paginas,1):
            primeiro = True
            for l in linhas:
                texto = l.texto(); norm = normalizar_assinatura(texto)
                if (l.y < 45 and texto.startswith('Emitido em ')) or l.y > 750 or re.match(r'^Condom[ií]nio\s*:',texto):
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
                    from conversor.domain.beach_parque import complemento_unidade
                    try: complemento_unidade(bloco[1],unidade[1])
                    except ValueError: falha('BPQ_CADASTRO_UNIDADE_INVALIDA',l)
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
                            cabecalhos=[],campos=[],alertas_origens={},iniciou_cobranca=False,participantes={p:dict(nome='',docs=[],tels=[],emails=[])
                            for p in ('titular','locatario','pagador','unidade')},alertas=[],diagnosticos_contatos=[])
                        atual['participantes']['titular']['nome']=unidade[2]
                        fichas[chave]=atual;secao='cabecalho';papel='titular'
                    if re.search(r'\blitigio\b',normalizar_assinatura(unidade[2])):
                        codigo='BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO'
                        atual['alertas'].append(codigo)
                        atual['alertas_origens'].setdefault(codigo,origem(l))
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
                        falha('BPQ_CADASTRO_LOCATARIO_AMBIGUO',l)
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
                    n_celula = normalizar_assinatura(celula)
                    restricao = None
                    if re.fullmatch(r'bloquear reenvio automatico de boletos\s*:\s*sim',n_celula):
                        restricao = 'BPQ_REVISAO_BLOQUEIO_REENVIO'
                    elif re.fullmatch(r'recebe carta(?: de cobranca)?\s*:\s*nao',n_celula):
                        restricao = 'BPQ_REVISAO_NAO_RECEBER_CARTA'
                    elif ('litig' in n_celula and campo.strip() == 'Classificação'):
                        restricao = 'BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO'
                    if restricao:
                        atual['alertas'].append(restricao)
                        atual['alertas_origens'].setdefault(restricao,origem(l,inicio,fim))
                    doc=re.fullmatch(r'(CPF|CNPJ)\s*:\s*(.*)',celula)
                    if doc and papel_campo in atual['participantes']:
                        if doc[2].strip():
                            atual['participantes'][papel_campo]['docs'].append((Documento(tipo=doc[1].lower(),valor=doc[2]),origem(l,inicio,fim)))
                if secao.startswith('telefone/e-mail'):
                    for inicio,fim in ((0,300),(300,600)):
                        celula=l.texto(inicio,fim)
                        if not celula:continue
                        contato=segmentar_contato(celula)
                        contato_origem=origem(l,inicio,fim)
                        if contato.codigo:
                            atual['alertas'].append(contato.codigo)
                            atual['diagnosticos_contatos'].append((contato.codigo,contato_origem))
                        dados=atual['participantes'][papel]
                        dados['emails'].extend((email,contato_origem)for email in contato.emails)
                        dados['tels'].extend((telefone,contato_origem)for telefone in contato.telefones)
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
            p=Pessoa(id=pid,unidade_id=uid,nome=titular.nome,relacao_unidade='titular_cadastrado_beach_parque',origem=o,
                evidencias_documentais=tuple(EvidenciaDocumento(documento=d,origem=orig,titular_id=pid)for d,orig in titular.documentos),
                contato=Contato(telefones=tuple(tels[:5]),emails=tuple(emails[:3]),origem=o))
            unidades.append(u);pessoas.append(p)
            ressalvas.append(RessalvaLeitura(codigo='BPQ_CADASTRO_FICHA_ORIGINAL',gravidade='informativo',registro_id=uid,
                origens=ficha.cabecalhos,valores_originais=(ficha.model_dump_json(),)))
            for codigo in ficha.alertas:
                if codigo in DIAGNOSTICOS_CONTATO:continue
                ressalvas.append(RessalvaLeitura(codigo=codigo,registro_id=uid,origens=(f['alertas_origens'].get(codigo,o),)))
            for codigo,contato_origem in dict.fromkeys(f['diagnosticos_contatos']):
                ressalvas.append(RessalvaLeitura(codigo=codigo,registro_id=uid,
                    gravidade='informativo'if codigo==CONTATO_SEGMENTADO else'alerta',origens=(contato_origem,)))
            if len(tels)>5 or len(emails)>3:
                ressalvas.append(RessalvaLeitura(codigo='CONTATOS_EXCEDENTES_PRESERVADOS',registro_id=uid,origens=(o,)))
        primeiro=fonte.paginas[0][0]
        ressalvas.append(RessalvaLeitura(codigo='BPQ_CADASTRO_IDENTIDADE_E_COMPLETUDE',gravidade='informativo',
            origens=(origem(primeiro),origem(fonte.cabecalho_inicial[0]),origem(fonte.cabecalho_inicial[1]),origem(fonte.resumo_linha)),valores_originais=(json.dumps(dict(fonte.identidade,
                cabecalhos=cabecalhos,continuidades=continuidades),ensure_ascii=False,sort_keys=True),)))
        ressalvas.append(RessalvaLeitura(codigo='BPQ_CADASTRO_TEMPORALIDADE', gravidade='informativo',
            origens=(origem(fonte.cabecalho_inicial[0]),), valores_originais=(json.dumps({
                'datas_emissao':sorted({d.date().isoformat() for d in emissoes.values()}),
                'paginas':len(fonte.paginas),'registros':len(unidades),'fuso_documental':None}),)))
        return sanitizar(LoteCanonico(unidades=tuple(unidades),pessoas=tuple(pessoas),boletos=(),ressalvas=tuple(ressalvas)))
