"""Infraestrutura dos leitores textuais; gramáticas precisam de homologação por versão."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from hashlib import sha256
import re

from pydantic import ValidationError

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import (
    Apontamento, Boleto, Composicao, Contato, Documento, ItemComposicao,
    LoteCanonico, Origem, Pessoa, Telefone, Unidade,
)

NUMERO_BRL = r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}"
VALOR_BRL = rf"(?:-?{NUMERO_BRL}|\({NUMERO_BRL}\))"


class ErroLeitura(Exception):
    def __init__(self, codigo, *, pagina=None, linha=None, boleto=None):
        super().__init__(codigo)
        self.codigo, self.pagina, self.linha, self.boleto = codigo, pagina, linha, boleto


def id_estavel(prefixo: str, *partes) -> str:
    return prefixo + ":" + sha256("\x1f".join(str(p) for p in partes).encode()).hexdigest()


def dinheiro_brl(valor: str) -> Decimal:
    if not re.fullmatch(VALOR_BRL, valor):
        raise ErroLeitura("VALOR_MONETARIO_INVALIDO")
    sinal = -1 if valor.startswith("(") else 1
    return Decimal(valor.strip("()").replace(".", "").replace(",", ".")) * sinal


def data_curta(valor: str, linha=None) -> date:
    # Convenção explícita dos documentos de laboratório (anos 2000..2099).
    try:
        dia, mes, ano = map(int, valor.split("/"))
        return date(2000 + ano, mes, dia)
    except (ValueError, TypeError):
        raise ErroLeitura("DATA_DE_BOLETO_INVALIDA", pagina=linha.pagina if linha else None,
                          linha=linha.numero if linha else None) from None


def telefone(valor: str) -> Telefone:
    digitos = re.sub(r"\D", "", valor)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    try:
        return Telefone(ddd=digitos[:2], numero=digitos[2:])
    except ValidationError:
        raise ErroLeitura("TELEFONE_INVALIDO") from None


@dataclass(frozen=True)
class ContextoLeitura:
    condominio_id: str
    administradora_id: str
    formato_id: str
    arquivo_id: str
    codigo_condominio: str
    leitor_versao: str | None = None


@dataclass(frozen=True)
class LinhaFonte:
    pagina: int
    numero: int
    texto: str = field(repr=False)


class TextoPDF:
    def __init__(self, conteudo: bytes, contexto: ContextoLeitura):
        self.contexto = contexto
        self.sonda = SondadorLocal().sondar(conteudo, arquivo_id=contexto.arquivo_id)
        if self.sonda.bloqueios or not self.sonda.completo or self.sonda.tipo != "pdf_texto":
            raise ErroLeitura("PDF_NAO_EXTRAIVEL_COM_SEGURANCA")
        self.paginas = tuple(tuple(LinhaFonte(pagina, i, texto) for i, texto in enumerate(fragmento.texto.splitlines(), 1))
                             for pagina, fragmento in enumerate(self.sonda.fragmentos, 1))

    def origem(self, linha: LinhaFonte, *, continuacao_de=None) -> Origem:
        return Origem(arquivo_id=self.contexto.arquivo_id, sha256=self.sonda.arquivo_hash,
                      leitor_versao=self.contexto.leitor_versao or self.contexto.formato_id, pagina=linha.pagina, linha=linha.numero,
                      identificador=f"p{linha.pagina}_l{linha.numero}", continuacao_de=continuacao_de)


@dataclass
class BoletoEmLeitura:
    numero: str
    unidade: Unidade
    vencimento: date
    competencia: str
    apontamento: str | None = None
    itens: list = field(default_factory=list)
    origens: list = field(default_factory=list)
    multa: Decimal = Decimal("0.00")
    juros: Decimal = Decimal("0.00")
    saldo: Decimal | None = None

    def item(self, valor, origem, *, multa=Decimal("0.00"), juros=Decimal("0.00"), saldo=None):
        self.itens.append(ItemComposicao(codigo=f"item_{len(self.itens)+1:04}", valor=valor, origem=origem))
        self.origens.append(origem)
        self.multa += multa
        self.juros += juros
        self.saldo = saldo

    def concluir(self, contexto):
        if not self.itens:
            raise ErroLeitura("BOLETO_SEM_COMPOSICAO", boleto=self.numero)
        try:
            return Boleto(id=id_estavel("bol", self.unidade.id, self.numero), identificador=self.numero,
                condominio_id=self.unidade.condominio_id, unidade_id=self.unidade.id, vencimento=self.vencimento,
                competencia=self.competencia, composicao=Composicao(itens=tuple(self.itens),
                    total_original=sum((i.valor for i in self.itens), Decimal("0.00"))),
                multa=self.multa, juros=self.juros, saldo_acumulado=self.saldo, origens=tuple(self.origens),
                apontamentos=(Apontamento(codigo_original=self.apontamento, namespace_formato=contexto.formato_id,
                              origem=self.origens[0]),) if self.apontamento else ())
        except ValidationError:
            raise ErroLeitura("CONTRATO_DE_BOLETO_INVALIDO", boleto=self.numero) from None


class AcumuladorLeitura:
    def __init__(self, fonte):
        self.fonte = fonte
        self.unidades = {}
        self.pessoas = {}
        self.boletos = []
        self.atual = None
        self.boleto = None
        self.pendente = False
        self.continuacao = False

    def unidade(self, bloco, unidade, nome, linha, documento=None):
        self.finalizar()
        if self.pendente:
            self.falhar("CONTINUACAO_AUSENTE", linha)
        chave = (bloco, unidade)
        if chave in self.unidades:
            self.falhar("UNIDADE_REPETIDA_NAO_RECONCILIADA", linha)
        contexto = self.fonte.contexto
        objeto = Unidade(id=id_estavel("uni", contexto.condominio_id, bloco, unidade),
            condominio_id=contexto.condominio_id, administradora_id=contexto.administradora_id,
            bloco_original=bloco, unidade_original=unidade, chave_normalizada=f"{bloco}/{unidade}",
            normalizador_versao="identidade_textual_lab_v1", origem=self.fonte.origem(linha))
        pessoa = Pessoa(id=id_estavel("pes", objeto.id), unidade_id=objeto.id, nome=nome.strip(),
            documento=documento, relacao_unidade="titular_informado", origem=self.fonte.origem(linha))
        self.unidades[chave], self.pessoas[objeto.id] = objeto, pessoa
        self.atual = objeto

    def iniciar(self, numero, vencimento, competencia, linha, apontamento=None):
        if self.atual is None or self.pendente:
            self.falhar("BOLETO_SEM_UNIDADE_OU_CONTINUACAO", linha)
        self.finalizar()
        if any(b.unidade_id == self.atual.id and b.identificador == numero for b in self.boletos):
            self.falhar("DUPLICIDADE_NAO_RECONCILIADA", linha, numero)
        self.boleto = BoletoEmLeitura(numero, self.atual, vencimento, competencia, apontamento)
        self.continuacao = False

    def origem_item(self, linha):
        if self.boleto is None:
            self.falhar("COMPOSICAO_SEM_BOLETO", linha)
        anterior = self.boleto.origens[-1].identificador if self.continuacao and self.boleto.origens else None
        return self.fonte.origem(linha, continuacao_de=anterior)

    def finalizar(self):
        if self.pendente:
            origem = self.boleto.origens[-1] if self.boleto and self.boleto.origens else None
            raise ErroLeitura("CONTINUACAO_AUSENTE", boleto=self.boleto.numero if self.boleto else None,
                              pagina=origem.pagina if origem else None, linha=origem.linha if origem else None)
        if self.boleto is not None:
            self.boletos.append(self.boleto.concluir(self.fonte.contexto))
            self.boleto = None
        self.continuacao = False

    def marcar_continuacao(self, linha):
        if self.boleto is None or self.pendente:
            self.falhar("CONTINUACAO_SEM_BOLETO", linha)
        self.pendente = True

    def continuar(self, numero, bloco, unidade, linha):
        if (not self.pendente or self.boleto is None or self.boleto.numero != numero
                or self.atual.bloco_original != bloco or self.atual.unidade_original != unidade):
            self.falhar("CONTINUACAO_DIVERGENTE", linha, numero)
        if linha.pagina != self.boleto.origens[-1].pagina + 1:
            self.falhar("PAGINA_DE_CONTINUACAO_INVALIDA", linha, numero)
        self.boleto.origens.append(self.fonte.origem(linha, continuacao_de=self.boleto.origens[-1].identificador))
        self.pendente = False
        self.continuacao = True

    def fim_pagina(self, pagina):
        if self.boleto is not None and not self.pendente and pagina != len(self.fonte.paginas):
            self.falhar("QUEBRA_SEM_MARCADOR", self.fonte.paginas[pagina-1][-1])

    def resultado(self):
        self.finalizar()
        if not self.unidades or not self.boletos:
            raise ErroLeitura("RELATORIO_SEM_UNIDADES_OU_BOLETOS")
        try:
            return LoteCanonico(unidades=tuple(self.unidades.values()), boletos=tuple(self.boletos), pessoas=tuple(self.pessoas.values()))
        except ValidationError:
            raise ErroLeitura("LOTE_CANONICO_INVALIDO") from None

    def falhar(self, codigo, linha, numero=None):
        raise ErroLeitura(codigo, pagina=linha.pagina, linha=linha.numero,
                          boleto=numero or (self.boleto.numero if self.boleto else None))
