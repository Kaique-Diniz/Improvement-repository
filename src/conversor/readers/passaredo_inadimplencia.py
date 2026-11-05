"""Leitor Passaredo: XLSX de inadimplência (aba Sheet1) em contrato canônico."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from conversor.adapters.xlsx_reader import celula_data, decodificar_moeda
from conversor.readers.text_support import ErroLeitura
from .passaredo_table import tabela

COLUNAS_OBRIGATORIAS = (
    "UNIDADE", "RESPONSAVEL", "DESCRICAO", "VENCIMENTO", "DIAS",
    "VALOR", "JUROS", "MULTA", "CORRECAO", "HONORARIOS", "ATUAL",
)
ZERO = Decimal("0.00")

@dataclass(frozen=True)
class DebitoPassaredo:
    linha: int
    unidade: str
    responsavel: str
    descricao: str
    vencimento: date
    dias: int
    valor: Decimal
    juros: Decimal
    multa: Decimal
    correcao: Decimal
    honorarios: Decimal
    atual: Decimal
    nu_parcela: int

def _texto(valor):
    return "" if valor is None else str(valor).strip()

def _inteiro(valor, campo, linha):
    texto = _texto(valor)
    if isinstance(valor, bool) or not re.fullmatch(r'[+-]?\d{1,7}(?:\.0{1,6})?', texto):
        raise ErroLeitura(f"PASSAREDO_{campo}_INVALIDO", linha=linha)
    return int(texto.split('.')[0])


def _original(valor, linha):
    # A origem não pode ganhar um valor arredondado para caber no Excel.
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
        try:
            numero = Decimal(str(valor))
            if not numero.is_finite() or numero != numero.quantize(Decimal('.01')):
                raise ValueError
        except (InvalidOperation, ValueError):
            raise ErroLeitura('PASSAREDO_ORIGINAL_PRECISAO_INVALIDA', linha=linha) from None
    elif isinstance(valor, str) and re.search(r',\d{3,}', valor.strip()):
        raise ErroLeitura('PASSAREDO_ORIGINAL_PRECISAO_INVALIDA', linha=linha)
    return decodificar_moeda(valor)

def identificar(conteudo: bytes):
    plan = tabela(conteudo, arquivo_id="identificacao_passaredo",
                  obrigatorias=COLUNAS_OBRIGATORIAS, permitidas=COLUNAS_OBRIGATORIAS)
    chaves = tuple(c for c, _ in plan.colunas)
    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in chaves]
    if faltantes:
        raise ErroLeitura("PASSAREDO_COLUNAS_AUSENTES")
    extras = [c for c in chaves if c not in COLUNAS_OBRIGATORIAS and c != "__LINHA__"]
    if extras:
        raise ErroLeitura("PASSAREDO_COLUNAS_NAO_RECONHECIDAS")
    return plan

class LeitorPassaredoInadimplencia:
    formato_id = "passaredo_inadimplencia_xlsx_v1"
    versao = "1"

    def ler(self, conteudo: bytes, *, condominio_id: str = "condominio_passaredo",
            administradora_id: str = "auto_gestao", arquivo_id: str = "passaredo_inadimplencia") -> tuple[DebitoPassaredo, ...]:
        plan = identificar(conteudo)
        debitos = []
        
        for registro in plan.linhas:
            linha = registro["__linha__"]
            unidade = _texto(registro["UNIDADE"])
            if not unidade:
                raise ErroLeitura("PASSAREDO_UNIDADE_VAZIA", linha=linha)
                
            descricao = _texto(registro["DESCRICAO"])
            if not descricao:
                raise ErroLeitura("PASSAREDO_DESCRICAO_VAZIA", linha=linha)
                
            valores = {
                campo: _original(registro[campo], linha) if campo == 'VALOR' else decodificar_moeda(registro[campo])
                for campo in ("VALOR", "JUROS", "MULTA", "CORRECAO", "HONORARIOS", "ATUAL")
            }
            
            soma = sum((valores[c] for c in ("VALOR", "JUROS", "MULTA", "CORRECAO", "HONORARIOS")), ZERO)
            if soma != valores["ATUAL"]:
                raise ErroLeitura("PASSAREDO_COMPOSICAO_INCONSISTENTE", linha=linha)
                
            debitos.append(DebitoPassaredo(
                linha=linha,
                unidade=unidade,
                responsavel=_texto(registro["RESPONSAVEL"]),
                descricao=descricao,
                vencimento=celula_data(registro["VENCIMENTO"]),
                dias=_inteiro(registro["DIAS"], "DIAS", linha),
                nu_parcela=0,
                **{campo.lower(): valor for campo, valor in valores.items()},
            ))
        return self._sequenciar(debitos)

    def _sequenciar(self, debitos):
        saida = []
        por_unidade = {}
        for debito in debitos:
            por_unidade.setdefault(debito.unidade, []).append(debito)
            
        for unidade in sorted(por_unidade):
            ordenados = sorted(por_unidade[unidade], key=lambda d: (d.vencimento, d.linha))
            for indice, debito in enumerate(ordenados, start=1):
                saida.append(DebitoPassaredo(**{**debito.__dict__, "nu_parcela": indice}))
                
        return tuple(saida)
