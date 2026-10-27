"""Família BBZ Relatório de Unidades - Completo. Não seleciona dívidas ou titulares."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import re

from pypdf import PdfReader
from pypdf.constants import UserAccessPermissions

from conversor.adapters.document_probe import LimitesSondagem
from conversor.domain.bbz_cadastro import CampoCadastroBBZ, FichaCadastroBBZ, ParticipanteBBZ
from conversor.domain.canonical import (Contato, Documento, EvidenciaDocumento, LoteCanonico,
    Origem, Pessoa, RessalvaLeitura, Telefone, Unidade, cnpj_validado)
from conversor.domain.identity import chave_unidade
from conversor.domain.recognition import normalizar_assinatura
from .text_support import ErroLeitura, id_estavel

FORMATO = 'bbz_cadastro_geral_pdf_v1'
SECOES = {'endereco de cobranca':'correspondencia', 'dados pessoais':'titular',
    'telefone/e-mail do cliente':'titular', 'telefone/e-mail da unidade':'unidade',
    'unidade alugada':'locatario', 'telefone/e-mail de locatario':'locatario',
    'telefone/e-mail do locatario':'locatario', 'dados do locatario':'locatario',
    'telefone/e-mail do pagador':'pagador',
    'dados do pagador':'pagador', 'dados gerais':'geral', 'observacoes':'observacoes'}
EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')


def email_valido(valor):
    if not EMAIL.fullmatch(valor) or '..' in valor:return False
    local,dominio=valor.split('@')
    return not local.startswith('.') and not local.endswith('.') and all(
        re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?',parte)for parte in dominio.split('.'))


def codigo_origem(valor):
    return valor.lstrip('0') or '0'


@dataclass(frozen=True)
class LinhaBBZ:
    pagina: int
    numero: int
    y: float
    partes: tuple

    def texto(self, inicio=0, fim=600):
        return ''.join(t for t,x in self.partes if inicio <= x < fim).strip()


def falha(codigo, linha=None):
    raise ErroLeitura(codigo, pagina=linha.pagina if linha else None, linha=linha.numero if linha else None)


class FonteCadastroBBZ:
    def __init__(self, conteudo):
        limites = LimitesSondagem()
        if not conteudo.startswith(b'%PDF-') or len(conteudo)>limites.bytes_arquivo:
            falha('PDF_NAO_EXTRAIVEL_COM_SEGURANCA')
        self.digest = sha256(conteudo).hexdigest()
        self.paginas = []
        try:
            pdf = PdfReader(BytesIO(conteudo), strict=True)
            protegido = pdf.is_encrypted
            if protegido and (not pdf.decrypt('') or not pdf.user_access_permissions & UserAccessPermissions.EXTRACT):
                falha('BBZ_CADASTRO_EXTRACAO_NAO_AUTORIZADA')
            if len(pdf.pages)>limites.paginas:falha('LIMITE_ARQUIVO_EXCEDIDO')
            if not pdf.pages or 'Relatório de Unidades - Completo' not in (pdf.pages[0].extract_text() or ''):
                falha('FORMATO_DESCONHECIDO')
            caracteres=0
            for pi, pagina in enumerate(pdf.pages, 1):
                partes = []
                stream=pagina.get_contents()
                if stream is not None and len(stream.get_data())>limites.bytes_stream_pdf:
                    falha('LIMITE_ARQUIVO_EXCEDIDO')
                escala = 595.28 / float(pagina.mediabox.width)
                def visitor(texto, cm, tm, font, size):
                    t = texto.replace('\r', '').replace('\n', '')
                    if t:
                        x = (tm[4]*cm[0]+tm[5]*cm[2]+cm[4])*escala
                        y = tm[4]*cm[1]+tm[5]*cm[3]+cm[5]
                        if x < 0 or y < 0:falha('BBZ_CADASTRO_GEOMETRIA_INCOMPATIVEL')
                        partes.append((t, x, y))
                texto=pagina.extract_text(visitor_text=visitor) or ''
                caracteres+=len(texto)
                if not texto.strip():falha('PDF_NAO_EXTRAIVEL_COM_SEGURANCA')
                if caracteres>limites.caracteres:falha('LIMITE_ARQUIVO_EXCEDIDO')
                grupos = []
                for t,x,y in sorted(partes, key=lambda p:(-p[2],p[1])):
                    if grupos and abs(grupos[-1][0]-y) < .7:
                        grupos[-1][1].append((t,x))
                    else:
                        grupos.append((y, [(t,x)]))
                self.paginas.append(tuple(LinhaBBZ(pi,i,y,tuple(sorted(ps,key=lambda p:p[1])))
                    for i,(y,ps) in enumerate(grupos,1)))
        except ErroLeitura:
            raise
        except Exception:
            falha('BBZ_CADASTRO_PDF_INVALIDO')
        self.identidade = self._conferir()
        self.identidade['abertura_sem_senha_com_extracao_permitida']=protegido

    def _conferir(self):
        identidades = set(); endereco = set(); resumo = None; codigos_originais = set()
        for pi, linhas in enumerate(self.paginas,1):
            textos = [l.texto() for l in linhas]
            if textos.count('Relatório de Unidades - Completo') != 1:
                falha('FORMATO_DESCONHECIDO')
            rodapes = [(l,m) for l in linhas if l.y < 45 and
                (m:=re.fullmatch(r'Emitido em \d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} - Página (\d+) de (\d+)',l.texto()))]
            if len(rodapes) != 1 or tuple(map(int,rodapes[0][1].groups())) != (pi,len(self.paginas)):
                falha('BBZ_CADASTRO_PAGINACAO_INCOMPLETA')
            cab = [l for l in linhas if re.match(r'^Condom[ií]nio:',l.texto())]
            if len(cab) != 1:falha('BBZ_CADASTRO_IDENTIDADE_INCOMPLETA')
            l = cab[0]
            fiscais = [x for t,x in l.partes if re.match(r'^CNPJ(?:\s*:|$)',t.strip()) and 450 <= x < 600]
            if len(fiscais)!=1:falha('BBZ_CADASTRO_IDENTIDADE_INCOMPLETA',l)
            limite = fiscais[0]
            m = re.fullmatch(r'Condom[ií]nio:\s*([0-9]+)\s*-\s*(.+)',l.texto(0,limite))
            fiscal = re.fullmatch(r'CNPJ\s*:\s*(.+)',l.texto(limite,600))
            if not m or not fiscal:falha('BBZ_CADASTRO_IDENTIDADE_INCOMPLETA',l)
            doc = Documento(tipo='cnpj',valor=fiscal[1])
            valido = cnpj_validado(doc)
            if not valido:falha('BBZ_CADASTRO_CNPJ_CONDOMINIO_INVALIDO',l)
            identidades.add((codigo_origem(m[1]),normalizar_assinatura(m[2]),valido))
            codigos_originais.add(m[1])
            linhas_end = [x for x in linhas if x.y > 730 and x.texto().startswith('Endereço:')]
            if len(linhas_end) != 1:falha('BBZ_CADASTRO_ENDERECO_CABECALHO_INVALIDO',l)
            endereco.add(linhas_end[0].texto()[len('Endereço:'):].strip())
            if pi==1:self.cabecalho_inicial=(l,linhas_end[0])
            candidatos = [x for x in linhas if x.texto().startswith('Total de Unidade')]
            if candidatos:
                if pi != len(self.paginas) or len(candidatos) != 1 or resumo is not None:
                    falha('BBZ_CADASTRO_RESUMO_AMBIGUO',candidatos[0])
                totais = re.fullmatch(r'Total de Unidade\s*([0-9]+)',candidatos[0].texto(0,210))
                if not totais:falha('BBZ_CADASTRO_RESUMO_INVALIDO',candidatos[0])
                resumo = int(totais[1])
                self.resumo_linha=candidatos[0]
        if len(identidades) != 1:falha('BBZ_CADASTRO_CONDOMINIO_DIVERGENTE')
        if len(endereco) != 1:falha('BBZ_CADASTRO_ENDERECO_CABECALHO_DIVERGENTE')
        if resumo is None or not resumo:falha('BBZ_CADASTRO_RESUMO_AUSENTE')
        codigo,nome,cnpj = next(iter(identidades))
        return dict(codigo=codigo,codigos_originais=tuple(sorted(codigos_originais)),nome=nome,cnpj=cnpj,endereco=next(iter(endereco)),
                    unidades_resumo=resumo,paginas=len(self.paginas),localizacao_cabecalho={
                        'pagina':1,'linha_identidade':self.cabecalho_inicial[0].numero,
                        'linha_endereco':self.cabecalho_inicial[1].numero,
                        'y_identidade':self.cabecalho_inicial[0].y,'y_endereco':self.cabecalho_inicial[1].y})


def identificar(conteudo):
    return FonteCadastroBBZ(conteudo).identidade


def _telefone(texto):
    """Nunca herda DDD entre alternativas; rejeita texto residual não documentado."""
    numeros = []
    for parte in re.split(r'\s+(?:-|/)\s+|;',texto):
        parte = parte.strip()
        if not parte:continue
        if not re.fullmatch(r'[+0-9() .\-]+',parte) or parte.count('(')!=parte.count(')'):
            return (), False
        grupos=re.findall(r'\(([^()]*)\)',parte)
        if grupos and (len(grupos)!=1 or not re.fullmatch(r'\s*[0-9]{2}\s*',grupos[0])):
            return (), False
        digitos = re.sub(r'\D','',parte)
        if len(digitos) in (12,13) and digitos.startswith('55'):digitos=digitos[2:]
        if len(digitos) in (8,9):numeros.append(Telefone(ddd='',numero=digitos))
        elif len(digitos) in (10,11)and not digitos.startswith('0'):
            numeros.append(Telefone(ddd=digitos[:2],numero=digitos[2:]))
        else:return (), False
    return tuple(dict.fromkeys(numeros)), bool(numeros)


class LeitorCadastroBBZ:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        fonte = FonteCadastroBBZ(conteudo)
        if fonte.identidade['codigo'] != codigo_origem(contexto.codigo_condominio):
            falha('BBZ_CADASTRO_IDENTIDADE_DIVERGENTE')
        def origem(l, inicio=0, fim=600):
            return Origem(arquivo_id=contexto.arquivo_id,sha256=fonte.digest,
                leitor_versao=contexto.leitor_versao or FORMATO+'@1',pagina=l.pagina,linha=l.numero,
                identificador=f'p{l.pagina}_l{l.numero}_x{int(inicio)}_{int(fim)}')
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
                    if not m:falha('BBZ_CADASTRO_LOCATARIO_AMBIGUO',l)
                    atual['participantes']['locatario']['nome']=m[1]
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
        return LoteCanonico(unidades=tuple(unidades),pessoas=tuple(pessoas),boletos=(),ressalvas=tuple(ressalvas))
