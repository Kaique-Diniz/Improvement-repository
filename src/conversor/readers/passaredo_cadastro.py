"""Parser de cadastro auxiliar Passaredo (XLSX, aba Sheet1)."""
from dataclasses import dataclass
import json
import re
import unicodedata
from openpyxl.utils import get_column_letter

from conversor.domain.canonical import Contato, Documento, Endereco, Telefone
from conversor.readers.text_support import ErroLeitura
from .passaredo_table import tabela

CAMPOS_OBRIGATORIOS = ("UNIDADE", "RESPONSAVEL", "EMAIL", "CPF_CNPJ", "FONE", "CELULAR", "ENDERECO")
CAMPOS_PERMITIDOS = CAMPOS_OBRIGATORIOS + (
    'FRACAO', 'HABILITADO', 'ALUGADO', 'PETS', 'CONDOMINOS', 'RG', 'CPF',
    'PROFISSAO', 'VEICULOS', 'DESDE',
)
EMAIL_VALIDO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
TELEFONE_BR = re.compile(r"\(?\s*(\d{2})\s*\)?[\s.-]*(\d{4,5})[\s.-]*(\d{4})")

def _sem_acentos(texto):
    norm = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in norm if not unicodedata.combining(c))

def _texto(valor):
    return "" if valor is None else str(valor).strip()

def normalizar_documento(valor):
    digitos = re.sub(r"\D", "", _texto(valor))
    if not digitos:
        return None
    if len(digitos) not in (11, 14):
        raise ErroLeitura("PASSAREDO_DOCUMENTO_INVALIDO")
    tipo = "cpf" if len(digitos) == 11 else "cnpj"
    return Documento(tipo=tipo, valor=digitos)

def extrair_telefones(valor):
    telefones = []
    texto = _texto(valor)
    for match in TELEFONE_BR.finditer(texto):
        ddd = match.group(1)
        numero = match.group(2) + match.group(3)
        numero = re.sub(r"\D", "", numero)
        telefone = Telefone(ddd=ddd, numero=numero)
        if telefone not in telefones:
            telefones.append(telefone)
    
    return tuple(telefones)

def extrair_emails(valor):
    emails = [e.strip().lower() for e in re.split(r"[;,\s]+", _texto(valor)) if e.strip()]
    validos = []
    for email in emails:
        if not EMAIL_VALIDO.fullmatch(email):
            raise ErroLeitura("PASSAREDO_EMAIL_INVALIDO")
        if email not in validos:
            validos.append(email)
    return tuple(validos)

def parsear_endereco(valor):
    texto = _sem_acentos(_texto(valor)).upper()
    if not texto:
        return Endereco(logradouro="", numero="", complemento="", cep="", bairro="", cidade="", uf=""), True
    
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    if not partes:
        return Endereco(), True
        
    uf = partes.pop() if len(partes) >= 1 and re.fullmatch(r"[A-Z]{2}", partes[-1]) else ""
    cidade = partes.pop() if len(partes) >= 1 else ""
    
    cep_idx = -1
    for i in range(len(partes) - 1, -1, -1):
        if re.fullmatch(r"\d{8}", partes[i].replace(".", "").replace("-", "")):
            cep_idx = i
            break
            
    if cep_idx != -1:
        cep = partes[cep_idx].replace(".", "").replace("-", "")
        bairro = partes[cep_idx - 1].strip() if cep_idx > 0 else ""
        antes_cep = partes[:cep_idx - 1] if cep_idx > 1 else []
        
        numero = ""
        complemento = ""
        logradouro_parts = []
        
        for p in antes_cep:
            p = p.strip()
            if not p:
                continue
            if re.fullmatch(r"\d+", p):
                if not numero:
                    numero = p
                else:
                    complemento = p
            else:
                logradouro_parts.append(p)
                
        if not numero and antes_cep:
            ultimo = antes_cep[-1].strip()
            if re.fullmatch(r"\d+", ultimo):
                numero = ultimo
                logradouro_parts = antes_cep[:-1]
            else:
                logradouro_parts = antes_cep
                
        logradouro = ", ".join(logradouro_parts).strip(" ,")
    else:
        cep = ""
        bairro = partes.pop() if partes else ""
        logradouro = ", ".join(partes).strip(" ,")
        numero = ""
        complemento = ""

    endereco = Endereco(
        logradouro=logradouro.title() if logradouro else "",
        numero=numero,
        complemento=complemento.title() if complemento else "",
        cep=cep,
        bairro=bairro.title() if bairro else "",
        cidade=cidade.title() if cidade else "",
        uf=uf
    )
    
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
    documentos: tuple[Documento, ...] = ()
    documentos_colunas: tuple[str, ...] = ()
    telefones_excedentes: tuple[Telefone, ...] = ()
    emails_excedentes: tuple[str, ...] = ()
    valores_originais: str = ""

class LeitorPassaredoCadastro:
    formato_id = "passaredo_cadastro_xlsx_v1"
    versao = "1"

    def identificar(self, conteudo: bytes):
        plan = tabela(conteudo, arquivo_id="identificacao_passaredo_cadastro",
                      obrigatorias=tuple(c for c in CAMPOS_OBRIGATORIOS if c != 'CPF_CNPJ'),
                      permitidas=CAMPOS_PERMITIDOS)
        chaves = {c for c, _ in plan.colunas}
        if "CPF_CNPJ" not in chaves and "CPF" in chaves:
            chaves.add("CPF_CNPJ")
            
        faltantes = [c for c in CAMPOS_OBRIGATORIOS if c not in chaves]
        if faltantes:
            raise ErroLeitura("PASSAREDO_CADASTRO_COLUNAS_AUSENTES")
        return plan

    def ler(self, conteudo: bytes, *, arquivo_id: str = "passaredo_cadastro") -> tuple[CadastroPassaredo, ...]:
        plan = self.identificar(conteudo)
            
        registros = []
        vistos = set()
        colunas = {nome: get_column_letter(i) for i, (nome, _) in enumerate(plan.colunas, 1)}
        
        for registro in plan.linhas:
            linha = registro["__linha__"]
            unidade = _texto(registro.get("UNIDADE"))
            if not unidade:
                raise ErroLeitura("PASSAREDO_CADASTRO_UNIDADE_VAZIA", linha=linha)
            if unidade in vistos:
                raise ErroLeitura("PASSAREDO_CADASTRO_UNIDADE_DUPLICADA", linha=linha)
            vistos.add(unidade)
            
            fone_val = registro.get("FONE", "")
            celular_val = registro.get("CELULAR", "")
            telefones = list(extrair_telefones(fone_val))
            for t in extrair_telefones(celular_val):
                if t not in telefones:
                    telefones.append(t)
            telefones = tuple(telefones)
            
            emails = extrair_emails(registro.get("EMAIL", ""))
            endereco, parcial = parsear_endereco(registro.get("ENDERECO", ""))
            contato = Contato(telefones=telefones[:5], emails=emails[:3], endereco=endereco)
            
            doc_raw = registro.get("CPF_CNPJ", registro.get("CPF/CNPJ", registro.get("CPF", "")))
            documentos, documentos_colunas = [], []
            for campo in ('CPF_CNPJ', 'CPF'):
                valor = registro.get(campo)
                documento = normalizar_documento(valor)
                if documento is not None:
                    documentos.append(documento)
                    documentos_colunas.append(colunas[campo])
            
            registros.append(CadastroPassaredo(
                linha=linha, 
                unidade=unidade,
                responsavel=_texto(registro.get("RESPONSAVEL")),
                documento=normalizar_documento(doc_raw),
                contato=contato, 
                endereco_parcial=parcial,
                desde=_texto(registro.get("DESDE")),
                documentos=tuple(documentos),
                documentos_colunas=tuple(documentos_colunas),
                telefones_excedentes=telefones[5:],
                emails_excedentes=emails[3:],
                valores_originais=json.dumps(registro, ensure_ascii=False, default=str),
            ))
        return tuple(registros)
