"""Codificação de integração explícita; não muda a identidade ou a elegibilidade."""
import re
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from conversor.domain.base import Hash, Id, Modelo, Texto
from conversor.domain.canonical import Endereco, Unidade
from conversor.readers.text_support import ErroLeitura

POLITICA_ENDERECO_CONDOMINIO = 'endereco_condominio_prioritario@2'


class EvidenciaCodificacao(Modelo):
    arquivo: Texto
    sha256: Hash
    aba: Texto
    celulas: dict[str, Texto]


class OrigemEnderecoUsuario(Modelo):
    tipo: Literal['configuracao_fornecida_pelo_usuario'] = 'configuracao_fornecida_pelo_usuario'
    registro_id: Id
    versao: Annotated[int, Field(strict=True, ge=1)]
    registrado_em: AwareDatetime
    sessao_sha256: Hash


class EnderecoPadrao(Modelo):
    endereco: Endereco
    evidencia: EvidenciaCodificacao | OrigemEnderecoUsuario

    @model_validator(mode='after')
    def endereco_explicito(self):
        if not self.endereco.logradouro.strip() or self.endereco.complemento:
            raise ValueError('ENDERECO_PADRAO_EXIGE_LOGRADOURO_SEM_COMPLEMENTO_DE_UNIDADE')
        return self


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
    codificador: Literal['torre_unidade', 'bloco_unidade_sufixo'] = 'torre_unidade'
    sufixo_cedente: Texto | None = None
    rotulo_divida: Literal['competencia_ou_identificador', 'vencimento_apresentacao'] = 'competencia_ou_identificador'
    endereco_padrao: EnderecoPadrao | None = None

    @model_validator(mode='after')
    def mapa_explicito(self):
        codigo = r'[0-9]{1,6}' if self.codificador == 'torre_unidade' else r'[A-Z0-9]{1,6}'
        if not self.torres or any(not k or k != k.strip().upper() or
                                 not re.fullmatch(codigo, v) for k, v in self.torres.items()):
            raise ValueError('MAPEAMENTO_DE_TORRES_INVALIDO')
        if len(set(self.torres.values())) != len(self.torres):
            raise ValueError('CODIGOS_DE_TORRES_CONFLITANTES')
        if (self.codificador == 'bloco_unidade_sufixo') != (self.sufixo_cedente is not None):
            raise ValueError('SUFIXO_INCOMPATIVEL_COM_CODIFICADOR')
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
        if self.codificador == 'bloco_unidade_sufixo':
            complemento = f'BL{torre}-UNI{numero}'
            return f'{complemento}-{self.sufixo_cedente}', complemento
        return torre + numero, f'UNI{numero}-BL{torre}'

    def preencher_endereco(self, atual: Endereco) -> tuple[Endereco, str]:
        return preencher_endereco(atual, self.endereco_padrao)


def preencher_endereco(atual: Endereco, padrao: EnderecoPadrao | None) -> tuple[Endereco, str]:
    if padrao is None:
        return atual, 'sem_endereco_configurado'
    # Decisão explícita: endereço do edifício prevalece no XLSX inteiro.
    # Não completar campos vazios com outro endereço; a fonte fica no canônico.
    return padrao.endereco.model_copy(update={'complemento': atual.complemento}), 'endereco_explicito_configurado'


def selecionar_perfil(dados, *, administradora_id, condominio_id):
    perfis = [PerfilIdentificadores.model_validate(p) for p in dados]
    chaves = [(p.administradora_id, p.condominio_id) for p in perfis]
    if len(set(chaves)) != len(chaves):
        raise ErroLeitura('PERFIL_IDENTIFICADORES_AMBIGUO')
    return next((p for p in perfis if (p.administradora_id, p.condominio_id) ==
                 (administradora_id, condominio_id)), None)
