"""Infraestrutura para layouts reais; nenhum perfil de condomínio ou régua embutido."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import re

from pypdf import PdfReader

from conversor.domain.canonical import (
    Apontamento, Boleto, Composicao, Contato, ItemComposicao, LoteCanonico, Origem,
    Pessoa, RessalvaLeitura, Telefone, Unidade,
)
from conversor.domain.recognition import normalizar_assinatura
from conversor.domain.identity import chave_unidade
from .text_support import ErroLeitura, LinhaFonte, VALOR_BRL, dinheiro_brl, id_estavel

MOEDA = re.compile(VALOR_BRL)
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
ZERO = Decimal('0.00')


def falhar(codigo, linha=None):
    raise ErroLeitura(codigo, pagina=linha.pagina if linha else None, linha=linha.numero if linha else None)


def data_real(valor, linha):
    try:
        d,m,a = map(int,valor.split('/'))
        return date(a if a >= 100 else 2000+a,m,d)
    except ValueError:
        falhar('DATA_DE_BOLETO_INVALIDA',linha)


class PDFReal:
    def __init__(self, conteudo, contexto, *, layout=False, coordenadas=False):
        self.contexto=contexto
        self.hash=sha256(conteudo).hexdigest()
        self.paginas=[]
        self.fragmentos=[]
        try:
            reader=PdfReader(BytesIO(conteudo), strict=True)
            if reader.is_encrypted:falhar('PDF_PROTEGIDO')
            for pi,page in enumerate(reader.pages,1):
                chunks=[]
                def visitor(text,cm,tm,font,size):
                    if text.strip():
                        # Coordenadas no espaço da página, incluindo a matriz de transformação.
                        x=tm[4]*cm[0]+tm[5]*cm[2]+cm[4]
                        y=tm[4]*cm[1]+tm[5]*cm[3]+cm[5]
                        chunks.append((text.strip(),x,y))
                texto=page.extract_text(visitor_text=visitor) if coordenadas else page.extract_text(extraction_mode='layout' if layout else 'plain')
                if not texto or not texto.strip():falhar('PDF_NAO_EXTRAIVEL_COM_SEGURANCA')
                self.paginas.append(tuple(LinhaFonte(pi,i,t) for i,t in enumerate(texto.splitlines(),1)))
                self.fragmentos.append(tuple((LinhaFonte(pi,i,t),x,y)for i,(t,x,y)in enumerate(chunks,1)))
        except ErroLeitura:raise
        except Exception:
            falhar('PDF_REAL_INVALIDO')
        if not self.paginas:falhar('PDF_VAZIO')

    def origem(self, linha, *, continuacao_de=None):
        return Origem(arquivo_id=self.contexto.arquivo_id,sha256=self.hash,
            leitor_versao=self.contexto.leitor_versao or self.contexto.formato_id,
            pagina=linha.pagina,linha=linha.numero,identificador=f'p{linha.pagina}_l{linha.numero}',
            continuacao_de=continuacao_de)

    def rodape_validado(self,pi):
        textos=[l.texto for l,x,y in self.fragmentos[pi-1]if y<=65]
        if any(MOEDA.search(t)for t in textos):falhar('RODAPE_CONTEM_VALOR_FINANCEIRO')
        matches=[re.fullmatch(r'(\d+) de (\d+)',t.strip())for t in textos]
        matches=[m for m in matches if m]
        if len(matches)!=1 or tuple(map(int,matches[0].groups()))!=(pi,len(self.paginas)):
            falhar('PAGINACAO_INCOMPLETA')
        return textos

    def validar_condominio(self, familia):
        pattern = (r'Condom[ií]nio:\s*(\d+)\s*-' if familia=='habita'
                   else rf'{"W045A" if familia=="cadastro" else "W002A"}\s+[^\n]*?\((\d+)\)')
        ids={m[1] for pa in self.paginas for l in pa for m in re.finditer(pattern,l.texto,re.I)}
        if ids!={self.contexto.codigo_condominio}:falhar('CONDOMINIO_DIVERGENTE_OU_AMBIGUO')
        cabecalho=r'^\s*Condom[ií]nio:'if familia=='habita'else rf'^\s*{"W045A"if familia=="cadastro"else"W002A"}\b'
        if any(re.search(cabecalho,l.texto,re.I)and not re.search(pattern,l.texto,re.I)
               for pa in self.paginas for l in pa):falhar('CABECALHO_CONDOMINIO_INVALIDO')
        # Cabeçalhos de outra família não são aceitos como continuação.
        if familia!='habita' and any(re.search(r'W(?:002A|045A)',l.texto)and not re.search('W045A'if familia=='cadastro'else'W002A',l.texto)
                                   for pa in self.paginas for l in pa):falhar('CABECALHO_DE_OUTRO_FORMATO')


@dataclass
class Bilhete:
    unidade: Unidade
    numero: str
    vencimento: date
    competencia: str | None
    apontamento: str | None = None
    emissao_original: str | None = None
    itens: list = field(default_factory=list)
    valores: list = field(default_factory=list)
    saldo: Decimal | None = None
    origens_suplementares: list = field(default_factory=list)
    acrescimos_informados: bool = True

    def adicionar(self, valores, descricao, linha, fonte):
        anterior=self.itens[-1].origem if self.itens else None
        origem=fonte.origem(linha,continuacao_de=anterior.identificador if anterior and anterior.pagina!=linha.pagina else None)
        self.itens.append(ItemComposicao(codigo=f'item_{len(self.itens)+1:04}',valor=valores[0],
            descricao_original=descricao,origem=origem))
        self.valores.append(valores)

    def totais(self):
        return tuple(sum((v[i]for v in self.valores),ZERO)for i in range(5))

    def continuar_descricao(self,linha,fonte):
        if not self.itens:falhar('DESCRICAO_SEM_COMPOSICAO',linha)
        item=self.itens[-1]
        self.itens[-1]=ItemComposicao.model_validate(item.model_dump()|{'descricao_original':item.descricao_original+' '+linha.texto.strip()})
        self.origens_suplementares.append(fonte.origem(linha,continuacao_de=item.origem.identificador))

    def concluir(self, contexto):
        if not self.itens:falhar('BOLETO_SEM_COMPOSICAO')
        v=self.totais()
        return Boleto(id=id_estavel('bol',self.unidade.id,self.numero),identificador=self.numero,
            condominio_id=self.unidade.condominio_id,unidade_id=self.unidade.id,vencimento=self.vencimento,
            competencia=self.competencia,emissao_original=self.emissao_original,
            composicao=Composicao(itens=tuple(self.itens),total_original=v[0]),
            multa=v[1]if self.acrescimos_informados else None,correcao=v[2]if self.acrescimos_informados else None,
            juros=v[3]if self.acrescimos_informados else None,saldo_acumulado=self.saldo,
            origens=tuple(i.origem for i in self.itens)+tuple(self.origens_suplementares),
            apontamentos=(Apontamento(codigo_original=self.apontamento,namespace_formato=contexto.formato_id,
                origem=self.itens[0].origem),)if self.apontamento else ())


class AcervoReal:
    def __init__(self,fonte):
        self.fonte=fonte;self.unidades={};self.pessoas={};self.boletos={};self.ressalvas=[]

    def ressalva(self,codigo,linha,*,unidade=None,critico=False,valores=(),gravidade='alerta'):
        self.ressalvas.append(RessalvaLeitura(codigo=codigo,gravidade='critico'if critico else gravidade,
            registro_id=unidade.id if unidade else None,origens=(self.fonte.origem(linha),),valores_originais=tuple(valores)))

    def unidade(self,bloco,numero,nome,linha,documento=None):
        chave=chave_unidade(bloco,numero);ctx=self.fonte.contexto
        if chave in self.unidades:
            pessoa=self.pessoas[self.unidades[chave].id]
            if normalizar_assinatura(pessoa.nome)!=normalizar_assinatura(nome) or pessoa.documento!=documento:
                falhar('CABECALHO_UNIDADE_DIVERGENTE',linha)
            return self.unidades[chave]
        u=Unidade(id=id_estavel('uni_real',ctx.condominio_id,chave),condominio_id=ctx.condominio_id,
            administradora_id=ctx.administradora_id,bloco_original=bloco,unidade_original=numero,
            chave_normalizada=chave,normalizador_versao='identidade_real_v1',origem=self.fonte.origem(linha))
        self.unidades[chave]=u
        self.pessoas[u.id]=Pessoa(id=id_estavel('pes_real',u.id,normalizar_assinatura(nome)),unidade_id=u.id,
            nome=nome,documento=documento,relacao_unidade='titular_informado_na_fonte',origem=self.fonte.origem(linha))
        return u

    def contato(self,unidade,linhas,telefones,emails,endereco=None):
        p=self.pessoas[unidade.id]
        telefones=list(dict.fromkeys(telefones));emails=list(dict.fromkeys(emails))
        if len(telefones)>5 or len(emails)>3:
            self.ressalva('CONTATOS_EXCEDENTES_PRESERVADOS',linhas[0],unidade=unidade,
                          valores=[l.texto for l in linhas])
        contato=Contato(telefones=tuple(Telefone(ddd=t[:2],numero=t[2:])for t in telefones[:5]),
            emails=tuple(emails[:3]),origem=self.fonte.origem(linhas[0]),**({'endereco':endereco}if endereco else{}))
        self.pessoas[unidade.id]=Pessoa.model_validate(p.model_dump()|{'contato':contato})

    def resultado(self):
        if not self.unidades:falhar('RELATORIO_SEM_UNIDADES')
        return LoteCanonico(unidades=tuple(self.unidades.values()),pessoas=tuple(self.pessoas.values()),
            boletos=tuple(b.concluir(self.fonte.contexto)for b in self.boletos.values()),ressalvas=tuple(self.ressalvas))
