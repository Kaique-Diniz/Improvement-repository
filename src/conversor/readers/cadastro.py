"""Cadastro Geral FL do laboratório; associação exige condomínio, torre e unidade."""
import re

from conversor.domain.canonical import Contato, Documento, Endereco, Pessoa
from .text_support import ContextoLeitura, ErroLeitura, TextoPDF, id_estavel, telefone


class LeitorCadastroFLSintetico:
    formato_id = "cadastro_fl_sintetico_v1"

    def ler(self, conteudo: bytes, *, contexto: ContextoLeitura):
        fonte = TextoPDF(conteudo, contexto)
        # W045A identifica o Cadastro, não é outro condomínio em relação ao W002A.
        codigos = {m[1].strip() for p in fonte.paginas for l in p
                   if (m := re.fullmatch(r"W\w+ CONDOMINIO EDIFICIO (.+?) \(AMOSTRA SINTETICA\)", l.texto))}
        if codigos != {contexto.codigo_condominio}: raise ErroLeitura("CADASTRO_CONDOMINIO_DIVERGENTE")
        resultado = {}
        atual = None
        for pagina in fonte.paginas:
            for linha in pagina:
                texto = linha.texto.strip()
                if re.match(r"^\w+\s+TORRE\s+\w+\s{2,}", texto):
                    campos = re.split(r"\s{2,}", texto)
                    if len(campos) != 6: raise ErroLeitura("CADASTRO_INCOMPLETO", pagina=linha.pagina, linha=linha.numero)
                    match = re.fullmatch(r"(\w+) TORRE (\w+)", campos[0])
                    if not match: raise ErroLeitura("IDENTIDADE_CADASTRAL_INVALIDA", pagina=linha.pagina, linha=linha.numero)
                    unidade, bloco = match.groups()
                    chave = (contexto.condominio_id, bloco, unidade)
                    if chave in resultado: raise ErroLeitura("CADASTRO_AMBIGUO", pagina=linha.pagina, linha=linha.numero)
                    uid = id_estavel("uni", contexto.condominio_id, bloco, unidade)
                    endereco = re.fullmatch(r"(.+?),\s*(\S+)", campos[3])
                    if not endereco: raise ErroLeitura("ENDERECO_CADASTRAL_INVALIDO", pagina=linha.pagina, linha=linha.numero)
                    documento = Documento(tipo="cpf", valor=campos[4]) if campos[4] != "(vazio)" else None
                    emails = () if campos[5] == "(vazio)" else (campos[5],)
                    contato = Contato(endereco=Endereco(logradouro=endereco[1], numero=endereco[2]), emails=emails, origem=fonte.origem(linha))
                    resultado[chave] = Pessoa(id=id_estavel("pes", uid), unidade_id=uid, nome=campos[1], documento=documento,
                        relacao_unidade=campos[2], contato=contato, origem=fonte.origem(linha))
                    atual = chave
                elif texto.startswith("+55"):
                    if atual is None: raise ErroLeitura("TELEFONE_SEM_TITULAR", pagina=linha.pagina, linha=linha.numero)
                    pessoa = resultado[atual]
                    dados = pessoa.contato.model_dump() | {"telefones": pessoa.contato.telefones + (telefone(texto),),
                                                           "origem": fonte.origem(linha)}
                    resultado[atual] = Pessoa.model_validate(pessoa.model_dump() | {"contato": Contato.model_validate(dados)})
        if not resultado: raise ErroLeitura("CADASTRO_SEM_REGISTROS")
        return resultado
