"""Telefones somente em campos rotulados; DDD pertence ao próprio token."""
import re

from conversor.domain.canonical import Telefone

VERSAO = 'habita_telefones@2'
ROTULO = re.compile(r'\b(?:Telefone(?:\s+[^\W\d_]+)?|Celular)\s*:', re.I)
NUMERO = re.compile(
    r'(?<![0-9+])(?:\+55[\s.-]*)?(?:'
    r'\([0-9]{2}\)\s*[0-9]{4,5}[- ]?[0-9]{4}|'
    r'[0-9]{2}[ -][0-9]{4,5}[- ]?[0-9]{4}|'
    r'[0-9]{10,11}|[0-9]{4,5}[- ][0-9]{4}|[0-9]{8,9})(?![0-9])')


def extrair_telefones(texto):
    """Retorna pares e tokens/classificações para auditoria, sem inferir dígitos.

    Números de 8/9 dígitos exigem campo telefônico identificado. País +55 só é
    retirado quando explícito. Cada token é normalizado independentemente.
    """
    trecho = re.split(r'E-mail\s*:', texto, maxsplit=1, flags=re.I)[0]
    rotulos = list(ROTULO.finditer(trecho))
    partes = [(m.group(), trecho[m.end():rotulos[i+1].start() if i+1<len(rotulos)else len(trecho)])
              for i,m in enumerate(rotulos)]
    if not partes:
        partes = [('', trecho)]
    encontrados = []
    for rotulo, parte in partes:
        for m in NUMERO.finditer(parte):
            original = m.group()
            local = re.sub(r'^\+55[\s.-]*', '', original)
            digitos = re.sub(r'[^0-9]', '', local)
            if len(digitos) in (10,11):
                telefone = Telefone(ddd=digitos[:2], numero=digitos[2:])
            elif rotulo and len(digitos) in (8,9):
                telefone = Telefone(ddd='', numero=digitos)
            else:
                continue
            encontrados.append((telefone, rotulo, original))
    return encontrados
