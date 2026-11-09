"""Cadastro Lello Vero por participante; nunca escolhe um titular de dívida."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import re

from pypdf import PdfReader

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Contato, Endereco, EvidenciaDocumento, LoteCanonico, Origem, Pessoa, RessalvaLeitura, Unidade
from conversor.domain.identity import chave_unidade
from conversor.domain.recognition import normalizar_assinatura
from conversor.domain.vero_encanto import torre_unidade
from .passaredo_cadastro import EMAIL_VALIDO, extrair_telefones, normalizar_documento
from .text_support import ErroLeitura, id_estavel

FORMATO = 'vero_cadastro_pdf_v1'


def falha(codigo, pagina=None, linha=None):
    raise ErroLeitura('VERO_CADASTRO_' + codigo, pagina=pagina, linha=linha)


@dataclass(frozen=True)
class Linha:
    pagina: int
    numero: int
    partes: tuple

    def texto(self, minimo=0, maximo=600):
        return ' '.join(t for x,t in self.partes if minimo <= x < maximo).strip()


def linhas_pdf(conteudo):
    probe = SondadorLocal().sondar(conteudo, arquivo_id='cadastro_vero')
    if probe.tipo != 'pdf_texto' or probe.bloqueios or not probe.completo:
        falha('PDF_NAO_EXTRAIVEL')
    output = []
    try:
        with BytesIO(conteudo) as stream:
            reader = PdfReader(stream, strict=True)
            for pi, page in enumerate(reader.pages, 1):
                if not 594 <= float(page.mediabox.width) <= 596 or not 841 <= float(page.mediabox.height) <= 843:
                    falha('GEOMETRIA_INCOMPATIVEL', pi)
                parts = []

                def visitor(text, cm, tm, font, size):
                    t = text.replace('\r','').replace('\n','').strip()
                    if t:
                        x = tm[4]*cm[0]+tm[5]*cm[2]+cm[4]
                        y = tm[4]*cm[1]+tm[5]*cm[3]+cm[5]
                        if not 0 <= x < 596 or not 0 <= y <= 843:
                            falha('GEOMETRIA_INCOMPATIVEL', pi)
                        parts.append((x,y,t))

                page.extract_text(visitor_text=visitor)
                groups = []
                for x,y,t in sorted(parts,key=lambda v:(-v[1],v[0])):
                    if groups and abs(groups[-1][0]-y) < .7:
                        groups[-1][1].append((x,t))
                    else:
                        groups.append((y,[(x,t)]))
                output.extend(Linha(pi,n,tuple(sorted(items))) for n,(_,items) in enumerate(groups,1))
    except ErroLeitura:
        raise
    except Exception:
        falha('PDF_INVALIDO')
    return output


def conferir_identidade(linhas):
    refs = [l for l in linhas if l.texto(0,100) == 'Referência']
    if not refs or any(re.sub(r'\s','',l.texto(100,300)) != '10888-10' for l in refs):
        falha('IDENTIDADE_DIVERGENTE')
    esperado = re.sub(r'[^a-z0-9]','',normalizar_assinatura('PROJETO IMOBILIARIO DI 31 I VERO ENCANTO'))
    if any(re.sub(r'[^a-z0-9]','',normalizar_assinatura(l.texto(370))) != esperado for l in refs):
        falha('IDENTIDADE_DIVERGENTE')
    if linhas[0].texto() != 'Dados do condomínio':
        falha('CABECALHO_INVALIDO')


class LeitorCadastroVero:
    formato_id = FORMATO

    def ler(self, conteudo, *, contexto):
        if (contexto.administradora_id, contexto.condominio_id) != ('lello_2','condominio_vero_encanto'):
            falha('CONTEXTO_DIVERGENTE')
        linhas = linhas_pdf(conteudo)
        conferir_identidade(linhas)
        digest = sha256(conteudo).hexdigest()

        def origem(l):
            return Origem(arquivo_id=contexto.arquivo_id, sha256=digest,
                leitor_versao=contexto.leitor_versao or FORMATO+'@1', pagina=l.pagina,
                linha=l.numero, identificador=f'p{l.pagina}_l{l.numero}')

        units, people, notes = {}, [], []
        current, participant, care = None, None, False
        expect_unit = False
        per_unit = defaultdict(int)

        def concluir():
            nonlocal participant
            if participant is None:
                return
            if not participant['name'] or not participant['tipo'] or participant['participacao'] is None:
                falha('PARTICIPANTE_INCOMPLETO', participant['start'].pagina)
            raw = participant
            valid = []
            invalid = []
            for kind,value,line in raw['docs']:
                doc = normalizar_documento(value)
                if doc is not None and doc.tipo == kind:
                    if (raw['tipo'],kind) not in (('Física','cpf'),('Jurídica','cnpj')):
                        invalid.append(value)
                    else:
                        valid.append((doc,origem(line)))
                elif value not in ('','N/A'):
                    invalid.append(value)
            per_unit[current.id] += 1
            pid = id_estavel('participante_vero',current.id,per_unit[current.id])
            evidence = tuple(EvidenciaDocumento(documento=d,origem=o,titular_id=pid) for d,o in valid)
            person = Pessoa(id=pid, unidade_id=current.id, nome=raw['name'],
                documento=valid[0][0] if valid else None, documento_origem=valid[0][1] if valid else None,
                evidencias_documentais=evidence, relacao_unidade='condomino_cadastrado',
                origem=origem(raw['start']), contato=Contato(telefones=tuple(raw['phones']), emails=tuple(raw['emails']),
                    endereco=Endereco(**raw['address'])))
            people.append(person)
            notes.append(RessalvaLeitura(codigo='VERO_PARTICIPANTE_ORIGINAL', gravidade='informativo',
                registro_id=pid, origens=tuple(origem(l) for l in raw['lines']),
                valores_originais=(json.dumps({'tipo':raw['tipo'], 'participacao':str(raw['participacao']),
                    'linhas':[{'pagina':l.pagina,'linha':l.numero,'texto':l.texto()} for l in raw['lines']],
                    'terceiros_nao_transferidos':True},ensure_ascii=False),)))
            if invalid:
                notes.append(RessalvaLeitura(codigo='VERO_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO',
                    registro_id=pid, origens=(origem(raw['start']),),valores_originais=tuple(invalid)))
            participant = None

        for line in linhas:
            full, left, right = line.texto(), line.texto(0,100), line.texto(300,390)
            if line.texto(0,300) == 'Bloco' and line.texto(300) == 'Unidade':
                expect_unit = True
                continue
            if expect_unit:
                code = line.texto(300)
                try:
                    tower,_ = torre_unidade(code)
                except ValueError:
                    # O relatório contém também um registro textual adicional.
                    # Preservá-lo sem lhe atribuir codificação de unidade financeira.
                    tower_match = re.fullmatch(r'TORRE ([AB])',line.texto(0,300))
                    if not tower_match or not re.fullmatch(r'[A-Z]{1,20}',code):
                        falha('UNIDADE_INVALIDA',line.pagina,line.numero)
                    tower = tower_match[1]
                if line.texto(0,300) != 'TORRE '+tower:
                    falha('TORRE_DIVERGENTE',line.pagina,line.numero)
                uid = id_estavel('uni_real', contexto.condominio_id, chave_unidade(tower,code))
                if uid in units:
                    if current is None or current.id != uid or line.pagina <= current.origem.pagina:
                        falha('UNIDADE_DUPLICADA',line.pagina,line.numero)
                else:
                    concluir()
                    current = Unidade(id=uid,condominio_id=contexto.condominio_id,administradora_id=contexto.administradora_id,
                        bloco_original=tower,unidade_original=code,chave_normalizada=chave_unidade(tower,code),
                        normalizador_versao='vero_identidade_textual@1',origem=origem(line))
                    units[uid] = current
                    if not re.fullmatch(r'[AB]0[0-9]{4}',code):
                        notes.append(RessalvaLeitura(codigo='VERO_REGISTRO_CADASTRAL_SEM_CODIFICACAO_FINANCEIRA',
                            registro_id=uid,origens=(origem(line),),valores_originais=(code,)))
                expect_unit = False
                continue
            if full == 'Condômino':
                if current is None:
                    falha('PARTICIPANTE_SEM_UNIDADE',line.pagina,line.numero)
                concluir()
                participant = {'name':None,'tipo':None,'participacao':None,'docs':[], 'phones':[],'emails':[],
                    'address':{},'start':line,'lines':[]}
                care = False
                continue
            if participant is None:
                continue
            participant['lines'].append(line)
            if left == 'Nome' and right == 'Tipo de pessoa:':
                if participant['name'] is not None:
                    falha('NOME_DUPLICADO',line.pagina,line.numero)
                participant['name'], participant['tipo'] = line.texto(140,300), line.texto(390)
                if participant['tipo'] not in ('Física','Jurídica'):
                    falha('TIPO_PESSOA_INVALIDO',line.pagina,line.numero)
            if left in ('CPF','CNPJ'):
                participant['docs'].append((left.lower(),line.texto(140,300),line))
            if right == '% de participação':
                try:
                    percent = Decimal(line.texto(390).replace(',','.'))
                    if not percent.is_finite() or not 0 <= percent <= 100 or participant['participacao'] is not None:
                        raise ValueError
                    participant['participacao'] = percent
                except (InvalidOperation,ValueError):
                    falha('PARTICIPACAO_INVALIDA',line.pagina,line.numero)
            if left == 'Aos cuidados de':
                care = True
            if not care:
                if right in ('E-mail','E-mail boleto'):
                    value = line.texto(390)
                    if value and value != 'N/A':
                        for token in re.split(r'[;,\s]+',value):
                            if EMAIL_VALIDO.fullmatch(token) and token.lower() not in participant['emails']:
                                participant['emails'].append(token.lower())
                if right == 'Telefone':
                    for phone in extrair_telefones(line.texto(390)):
                        if phone not in participant['phones']:
                            participant['phones'].append(phone)
                for label,key in (('Endereço','logradouro'),('Bairro','bairro'),('Estado','uf'),('CEP','cep')):
                    if left == label:
                        value = line.texto(140,300)
                        if key == 'cep':
                            value = re.sub(r'[-\s]','',value)
                            value = value if re.fullmatch(r'[0-9]{8}',value) else ''
                        if key == 'uf' and not re.fullmatch(r'[A-Z]{2}',value):
                            value = ''
                        participant['address'][key] = value
                if right == 'Cidade':
                    participant['address']['cidade'] = line.texto(390)
        concluir()
        if expect_unit or not units or set(per_unit) != set(units):
            falha('CADASTRO_INCOMPLETO')
        return LoteCanonico(unidades=tuple(units.values()), pessoas=tuple(people), boletos=(), ressalvas=tuple(notes))
