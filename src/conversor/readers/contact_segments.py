"""Segmentação conservadora de campos explícitos; não consulta CEP nem presume DDD."""
import re

from conversor.domain.canonical import Endereco
from .real_support import EMAIL


def segmentar_telefones(linhas: list[str]) -> tuple[list[str], list[str]]:
    fragmentos = []
    for linha in linhas:
        if fragmentos and fragmentos[-1].count('(') > fragmentos[-1].count(')'):
            fragmentos[-1] += ' ' + linha.strip()
        else:
            fragmentos.append(linha.strip())
    validos, pendentes = [], []
    for texto in fragmentos:
        for parte in texto.split(';'):
            # Um telefone completo entre parênteses pode ser alternativa ao número
            # anterior. DDD entre parênteses permanece junto do número que o segue.
            alternativas = [m for m in re.finditer(r'\([+\d\s-]+\)', parte)
                            if len(re.sub(r'\D', '', m[0])) >= 10]
            candidatos = [m[0] for m in alternativas]
            for m in reversed(alternativas):
                parte = parte[:m.start()] + parte[m.end():]
            candidatos.insert(0, parte)
            for candidato in candidatos:
                if not candidato.strip():
                    continue
                digits = re.sub(r'\D', '', candidato)
                if len(digits) in (12, 13) and digits.startswith('55'):
                    digits = digits[2:]
                permitido = re.fullmatch(r'[+\d\s()\-]+', candidato)
                balanceado = candidato.count('(') == candidato.count(')')
                if permitido and balanceado and len(digits) in (10, 11):
                    validos.append(digits)
                else:
                    pendentes.append(candidato.strip())
    return list(dict.fromkeys(validos)), pendentes


def segmentar_emails(linhas: list[str]) -> tuple[list[str], list[str]]:
    # W045A quebra a célula em fragmentos, inclusive dentro do domínio.
    # Não validar um prefixo do fragmento antes de reconstruir o campo completo.
    texto = ''
    for linha in linhas:
        linha = linha.strip()
        # Dois sinais @ em fragmentos sucessivos denotam entradas distintas;
        # um domínio cortado continua sem introduzir pontuação nova no endereço.
        if '@' in re.split(r'[;,]', texto)[-1] and '@' in re.split(r'[;,]', linha)[0]:
            texto += ';'
        texto += linha
    validos, pendentes = [], []
    for parte in re.split(r'[;,]', texto):
        parte = parte.strip()
        if not parte:
            continue
        (validos if EMAIL.fullmatch(parte) else pendentes).append(parte)
    return list(dict.fromkeys(validos)), pendentes


def segmentar_endereco(linhas: list[str]) -> tuple[Endereco, str | None]:
    linhas = [' '.join(l.split()) for l in linhas if l.strip()]
    if not linhas:
        return Endereco(), 'ENDERECO_AUSENTE'
    # Dois fechamentos postais são dois endereços, não um complemento.
    localidades = [i for i, l in enumerate(linhas) if re.search(r' - [A-Z]{2} -', l)]
    if len(localidades) > 1:
        return Endereco(), 'ENDERECOS_MULTIPLOS_NAO_SEGMENTADOS'
    if not localidades:
        return Endereco(), 'ENDERECO_ORIGINAL_NAO_SEGMENTADO'
    i = localidades[0]
    partes = ' '.join(linhas[i:]).split(' - ')
    if len(partes) != 4 or not re.fullmatch(r'[A-Z]{2}', partes[2]):
        return Endereco(), 'ENDERECO_ORIGINAL_NAO_SEGMENTADO'
    bairro, cidade, uf, cep = partes
    # Não apagar caracteres arbitrários para fabricar um CEP válido.
    cep_valido = re.fullmatch(r'\d{5}-?\d{3}', cep)
    dados = dict(bairro=bairro, cidade=cidade, uf=uf, cep=cep.replace('-', '') if cep_valido else '')
    rua = ' '.join(linhas[:i])
    m = re.fullmatch(r'(.+?)(?:,\s*|\s+)(\d+[A-Za-z]?|S/N)(?:\s*-\s*(.+))?', rua, re.I)
    if m:
        dados.update(logradouro=m[1], numero=m[2], complemento=m[3] or '')
    else:
        # A linha inteira permanece logradouro; não escolher um número no meio do texto.
        dados['logradouro'] = rua
    endereco = Endereco(**dados)
    faltantes = not all(getattr(endereco, k) for k in ('logradouro', 'numero', 'bairro', 'cidade', 'uf', 'cep'))
    return endereco, 'ENDERECO_PARCIALMENTE_SEGMENTADO' if faltantes else None
