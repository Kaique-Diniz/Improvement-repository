"""Parser de cadastro auxiliar Passaredo (XLSX, aba Sheet1).

Campos lidos: UNIDADE, RESPONSAVEL, EMAIL, CPF/CNPJ, FONE, CELULAR, ENDERECO.

Conversões:
- ENDERECO (formato administradora: "LOGRADOURO , RUA ..., 3269, 007, BAIRRO,
  CEP, CIDADE, UF") → Endereco(canônico): logradouro, numero, cep, bairro,
  cidade, uf;
- telefones múltiplos em FONE/CELULAR → Telefone(ddd, numero) máx. 5;
- EMAIL com múltiplos valores → até EMAIL1..EMAIL3;
- CPF/CNPJ normalizado: apenas dígitos (11 ou 14), zeros preservados.

Somente fixtures sintéticas neste repositório; nada de dados reais.
"""
from dataclasses import dataclass, field
import re
import unicodedata

from conversor.adapters.xlsx_reader import ler_planilha
from conversor.domain.canonical import Contato, Documento, Endereco, Telefone
from conversor.readers.text_support import ErroLeitura

CAMPOS_OBRIGATORIOS = ("UNIDADE", "RESPONSAVEL", "EMAIL", "CPF_CNPJ", "FONE", "CELULAR", "ENDERECO")
EMAIL_VALIDO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# "(92) 8200-6513", "92 99181-7346", "+55 (92) 98276-2157", "92982762157"
TELEFONE_BR = re.compile(
    r"(?:(?:\+|$$)?55[\)\.\s-]*)?"      # código país opcional
    r"\(?(?P<ddd>\d{2})\)?[\s.\-]*"     # DDD com ou sem parênteses
    r"(?P<num>(?:\d[\s.\-]*){7,8}\d)"   # 7/8 dígitos com separadores opcionais
)


def _sem_acentos(texto):
    norm = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in norm if not unicodedata.combining(c))


def _texto(valor):
    return "" if valor is None else str(valor).strip()


def normalizar_documento(valor):
    """Remove formatação de CPF/CNPJ; preserva zeros; valida comprimento."""
    digitos = re.sub(r"\D", "", _texto(valor))
    if not digitos:
        return None
    if len(digitos) not in (11, 14):
        raise ErroLeitura("PASSAREDO_DOCUMENTO_INVALIDO")
    tipo = "cpf" if len(digitos) == 11 else "cnpj"
    return Documento(tipo=tipo, valor=digitos)


def extrair_telefones(valor):
    """'(92) 8200-6513 (92) 99181-7346' → [Telefone(92, 82006513), ...] (máx. 5)."""
    telefones = []
    for m in TELEFONE_BR.finditer(_texto(valor)):
        digitos = m["ddd"] + re.sub(r"\D", "", m["num"])
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]
        try:
            telefone = Telefone(ddd=digitos[:2], numero=digitos[2:])
        except Exception:
            raise ErroLeitura("PASSAREDO_TELEFONE_INVALIDO") from None
        if telefone not in telefones:
            telefones.append(telefone)
    if len(telefones) > 5:
        raise ErroLeitura("PASSAREDO_EXCESSO_TELEFONES")
    return tuple(telefones)


def extrair_emails(valor):
    emails = [e.strip().lower() for e in re.split(r"[;,\s]+", _texto(valor)) if e.strip()]
    validos = []
    for email in emails:
        if not EMAIL_VALIDO.fullmatch(email):
            raise ErroLeitura("PASSAREDO_EMAIL_INVALIDO")
        if email not in validos:
            validos.append(email)
    if len(validos) > 3:
        raise ErroLeitura("PASSAREDO_EXCESSO_EMAILS")
    return tuple(validos)


def parsear_endereco(valor):
    """Parse defensivo do ENDERECO da administradora.

    Estratégia por posição a partir do FIM (mais estável):
      ... , <numero>, <unidade?>, <bairro>, <CEP>, <cidade>, <UF>
    Quando o layout difere, cai no melhor esforço e marca ``parcial``.
    """
    texto = _sem_acentos(_texto(valor)).upper()
    if not texto:
        return Endereco(), True
    # "AVENIDA DO TURISMO , RUA ..." → a sequência " , " (espaço-vírgula-espaço)
    # não é separador de campo: faz parte do logradouro composto do condomínio.
    texto = re.sub(r"\s+,\s+(?=\s)", " ", texto)
    partes = [p.strip() for p in texto.split(",")]
    uf = ""
    if len(partes[-1]) == 2 and re.fullmatch(r"[A-Z]{2}", partes[-1]):
        uf = partes.pop()
    cidade = partes.pop() if partes else ""
    cep = ""
    if partes and re.fullmatch(r"\d{8}", partes[-1].replace(".", "").replace("-", "")):
        cep = partes.pop().replace(".", "").replace("-", "")
    bairro = partes.pop() if partes else ""
    # Número do imóvel: último token numérico curto (≤4 dígitos) antes do bairro;
    # a unidade (ex.: "007") vai para COMPLEMENTO quando presente após o número.
    numero, complemento = "", ""
    for indice in range(len(partes) - 1, -1, -1):
        pedaco = partes[indice]
        if re.fullmatch(r"\d{1,4}([/-]\d{1,4})?", pedaco):
            numero = pedaco
            restante = [p for p in partes[indice + 1:] if p and p != bairro]
            complemento = ", ".join(restante)
            del partes[indice:]
            break
    logradouro = ", ".join(p for p in partes if p).strip(" ,")
    endereco = Endereco(logradouro=logradouro.title() if logradouro else "",
                        numero=numero, complemento=complemento, cep=cep,
                        bairro=bairro.title() if bairro else "",
                        cidade=cidade.title() if cidade else "", uf=uf)
    parcial = not (logradouro and cep and cidade and uf)
    return endereco, parcial


@dataclass(frozen=True)
class CadastroPassaredo:
    linha: int
    unidade: str
    responsavel: str
    documento: Documento | None
    contato: Contato
    endereco_parcial: bool = False
    desde: str = ""


class LeitorPassaredoCadastro:
    formato_id = "passaredo_cadastro_xlsx_v1"
    versao = "1"

    def identificar(self, conteudo: bytes):
        plan = ler_planilha(conteudo, arquivo_id="identificacao_passaredo_cadastro", aba="Sheet1")
        chaves = {c for c, _ in plan.colunas}
        faltantes = [c for c in CAMPOS_OBRIGATORIOS if c not in chaves]
        if faltantes:
            raise ErroLeitura("PASSAREDO_CADASTRO_COLUNAS_AUSENTES")
        return plan

    def ler(self, conteudo: bytes, *, arquivo_id: str = "passaredo_cadastro") -> tuple[CadastroPassaredo, ...]:
        plan = self.identificar(conteudo) if arquivo_id == "passaredo_cadastro" else \
            ler_planilha(conteudo, arquivo_id=arquivo_id, aba="Sheet1")
        registros = []
        vistos = set()
        for registro in plan.linhas:
            linha = registro["__linha__"]
            unidade = _texto(registro.get("UNIDADE"))
            if not unidade:
                raise ErroLeitura("PASSAREDO_CADASTRO_UNIDADE_VAZIA", linha=linha)
            if unidade in vistos:
                raise ErroLeitura("PASSAREDO_CADASTRO_UNIDADE_DUPLICADA", linha=linha)
            vistos.add(unidade)
            telefones = extrair_telefones(registro.get("FONE", "")) + \
                tuple(t for t in extrair_telefones(registro.get("CELULAR", "")) if t not in telefones)
            emails = extrair_emails(registro.get("EMAIL", ""))
            endereco, parcial = parsear_endereco(registro.get("ENDERECO", ""))
            contato = Contato(telefones=tuple(telefones[:5]), emails=emails, endereco=endereco)
            registros.append(CadastroPassaredo(
                linha=linha, unidade=unidade,
                responsavel=_texto(registro.get("RESPONSAVEL")),
                documento=normalizar_documento(registro.get("CPF_CNPJ", registro.get("CPF/CNPJ", ""))),
                contato=contato, endereco_parcial=parcial,
                desde=_texto(registro.get("DESDE")),
            ))
        return tuple(registros)
