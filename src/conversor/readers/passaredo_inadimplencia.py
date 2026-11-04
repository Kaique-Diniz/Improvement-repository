"""Leitor Passaredo: XLSX de inadimplência (aba Sheet1) em contrato canônico."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from conversor.adapters.xlsx_reader import celula_data, decodificar_moeda, ler_planilha
from conversor.readers.text_support import ErroLeitura

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
    texto = _texto(valor).replace(".", "").replace(",", "")
    try:
        return int(texto)
    except ValueError:
        raise ErroLeitura(f"PASSAREDO_{campo}_INVALIDO", linha=linha) from None

def identificar(conteudo: bytes):
    plan = ler_planilha(conteudo, arquivo_id="identificacao_passaredo", aba="Sheet1")
    chaves = tuple(c for c, _ in plan.colunas)
    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in chaves]
    if faltantes:
        raise ErroLeitura("PASSAREDO_COLUNAS_AUSENTES")
    extras = [c for c in chaves if c not in COLUNAS_OBRIGATORIAS and c != "__LINHA__"]
    if extras:
        raise ErroLeitura("PASSAREDO_COLUNAS_NAO_RECONHECIDAS")
    return True

class LeitorPassaredoInadimplencia:
    formato_id = "passaredo_inadimplencia_xlsx_v1"
    versao = "1"

    def ler(self, conteudo: bytes, *, condominio_id: str = "condominio_passaredo",
            administradora_id: str = "auto_gestao", arquivo_id: str = "passaredo_inadimplencia") -> tuple[DebitoPassaredo, ...]:
        identificar(conteudo)
        plan = ler_planilha(conteudo, arquivo_id=arquivo_id, aba="Sheet1")
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
                campo: decodificar_moeda(registro[campo])
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
                **valores,
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
