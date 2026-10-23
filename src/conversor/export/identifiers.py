"""Codificação de integração explícita; não muda a identidade ou a elegibilidade."""
import re
from typing import Annotated, Literal

from pydantic import Field, model_validator

from conversor.domain.base import Hash, Id, Modelo, Texto
from conversor.domain.canonical import Unidade
from conversor.readers.text_support import ErroLeitura


class EvidenciaCodificacao(Modelo):
    arquivo: Texto
    sha256: Hash
    aba: Texto
    celulas: dict[str, Texto]


class PerfilIdentificadores(Modelo):
    id: Id
    versao: Texto
    uso: Literal['diagnostico_nao_operacional']
    administradora_id: Id
    condominio_id: Id
    nome_cedente: Texto
    produto: Texto
    largura_unidade: Annotated[int, Field(strict=True, ge=1, le=12)]
    torres: dict[str, str]
    evidencia: EvidenciaCodificacao

    @model_validator(mode='after')
    def mapa_explicito(self):
        if not self.torres or any(not k or k != k.strip().upper() or
                                 not re.fullmatch(r'[0-9]{1,6}', v) for k, v in self.torres.items()):
            raise ValueError('MAPEAMENTO_DE_TORRES_INVALIDO')
        if len(set(self.torres.values())) != len(self.torres):
            raise ValueError('CODIGOS_DE_TORRES_CONFLITANTES')
        return self

    def codificar(self, unidade: Unidade, *, administradora_id: str) -> tuple[str, str]:
        if (administradora_id, unidade.administradora_id, unidade.condominio_id) != (
                self.administradora_id, self.administradora_id, self.condominio_id):
            raise ErroLeitura('PERFIL_IDENTIFICADORES_DE_OUTRO_CONDOMINIO')
        if unidade.bloco_original not in self.torres:
            raise ErroLeitura('TORRE_SEM_MAPEAMENTO_DOCUMENTAL')
        numero = unidade.unidade_original
        if not numero.isascii() or not numero.isdigit():
            raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
        numero = str(int(numero)).zfill(self.largura_unidade)
        if len(numero) > self.largura_unidade:
            raise ErroLeitura('UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')
        torre = self.torres[unidade.bloco_original]
        return torre + numero, f'UNI{numero}-BL{torre}'


def selecionar_perfil(dados, *, administradora_id, condominio_id):
    perfis = [PerfilIdentificadores.model_validate(p) for p in dados]
    chaves = [(p.administradora_id, p.condominio_id) for p in perfis]
    if len(set(chaves)) != len(chaves):
        raise ErroLeitura('PERFIL_IDENTIFICADORES_AMBIGUO')
    return next((p for p in perfis if (p.administradora_id, p.condominio_id) ==
                 (administradora_id, condominio_id)), None)
