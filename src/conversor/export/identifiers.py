"""Codificação de integração explícita; não muda a identidade ou a elegibilidade."""
import re
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from conversor.domain.base import Hash, Id, Modelo, Texto
from conversor.domain.canonical import Endereco, Unidade
from conversor.domain.forest_hill import complemento_unidade
from conversor.domain.oma import complemento_unidade as complemento_oma
from conversor.domain.itajuba import complemento_unidade as complemento_itajuba, TORRES as TORRES_ITAJUBA
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


class FormatoTipoUnidade(Modelo):
    bloco_original: Texto
    tipo: Literal['numerica', 'literal']
    bloco_cedente: Texto
    bloco_complemento: Texto
    prefixo_cedente: str = ''
    prefixo_complemento: str = ''
    largura_cedente: Annotated[int, Field(strict=True, ge=1, le=12)] = 1
    largura_complemento: Annotated[int, Field(strict=True, ge=1, le=12)] = 1
    padrao_literal: Texto | None = None

    @model_validator(mode='after')
    def formato_explicito(self):
        if self.tipo == 'literal':
            # Gramática finita: literais, larguras numéricas e classes de letras.
            if not self.padrao_literal or not re.fullmatch(r'(?:[A-Z0-9]+|\[0-9\]\{[1-9]\}|\[[A-Z]+\])+', self.padrao_literal):
                raise ValueError('PADRAO_LITERAL_DE_UNIDADE_INVALIDO')
        elif self.padrao_literal is not None:
            raise ValueError('PADRAO_LITERAL_INCOMPATIVEL')
        if any(not re.fullmatch(r'[A-Z0-9]{1,6}', v) for v in (self.bloco_cedente, self.bloco_complemento)):
            raise ValueError('BLOCO_DE_SAIDA_INVALIDO')
        if any(not re.fullmatch(r'[A-Z]*', v) for v in (self.prefixo_cedente, self.prefixo_complemento)):
            raise ValueError('PREFIXO_DE_UNIDADE_INVALIDO')
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
    codificador: Literal['torre_unidade', 'bloco_unidade_sufixo', 'unidade_sufixo', 'bloco_unidade_textual', 'bloco_tipo_unidade', 'forest_hill_documental', 'oma_documental', 'itajuba_documental'] = 'torre_unidade'
    formatos_unidade: tuple[FormatoTipoUnidade, ...] = ()
    sufixo_cedente: Texto | None = None
    rotulo_divida: Literal['competencia_ou_identificador', 'vencimento_apresentacao'] = 'competencia_ou_identificador'
    endereco_padrao: EnderecoPadrao | None = None
    tratamento_unidade_numerica: Literal['preservar', 'largura_comprovada'] = 'preservar'

    @model_validator(mode='after')
    def mapa_explicito(self):
        if self.codificador == 'itajuba_documental':
            if (self.torres!=TORRES_ITAJUBA or self.formatos_unidade or self.sufixo_cedente!='CONDOMINIO ITAJUBA'
                    or self.administradora_id!='bn_planner' or self.condominio_id!='condominio_itajuba' or self.largura_unidade!=4):
                raise ValueError('ITAJUBA_PERFIL_DOCUMENTAL_INCOMPATIVEL')
            return self
        if self.codificador == 'oma_documental':
            if (self.torres or self.formatos_unidade or self.sufixo_cedente != 'PARQUE SANTA MONICA'
                    or self.condominio_id != 'condominio_parque_santa_monica' or self.administradora_id != 'oma'):
                raise ValueError('OMA_PERFIL_DOCUMENTAL_INCOMPATIVEL')
            return self
        if self.codificador == 'forest_hill_documental':
            if (self.torres or self.formatos_unidade or self.sufixo_cedente != 'CONDOMINIO RESIDENCIAL FOREST HILL'
                    or self.condominio_id != 'condominio_forest_hill' or self.administradora_id != 'auto_gestao'):
                raise ValueError('FOREST_HILL_PERFIL_DOCUMENTAL_INCOMPATIVEL')
            return self
        if self.codificador == 'bloco_tipo_unidade':
            if (self.torres or not self.sufixo_cedente or not self.formatos_unidade or
                len({f.bloco_original for f in self.formatos_unidade}) != len(self.formatos_unidade)):
                raise ValueError('FORMATOS_DE_UNIDADE_AMBIGUOS_OU_INCOMPLETOS')
            return self
        if self.formatos_unidade:
            raise ValueError('FORMATOS_DE_UNIDADE_INCOMPATIVEIS')
        if self.codificador == 'bloco_unidade_textual':
            if self.torres or self.sufixo_cedente is not None:
                raise ValueError('CODIFICACAO_TEXTUAL_NAO_PRESUME_EQUIVALENCIA_DE_BLOCOS')
            return self
        if self.codificador == 'unidade_sufixo' and not self.torres:
            if self.sufixo_cedente is None:
                raise ValueError('SUFIXO_INCOMPATIVEL_COM_CODIFICADOR')
            return self
        codigo = r'[0-9]{1,6}' if self.codificador == 'torre_unidade' else r'[A-Z0-9]{1,6}'
        if not self.torres or any(not k or k != k.strip().upper() or
                                 not re.fullmatch(codigo, v) for k, v in self.torres.items()):
            raise ValueError('MAPEAMENTO_DE_TORRES_INVALIDO')
        if len(set(self.torres.values())) != len(self.torres):
            raise ValueError('CODIGOS_DE_TORRES_CONFLITANTES')
        if (self.codificador in ('bloco_unidade_sufixo','unidade_sufixo')) != (self.sufixo_cedente is not None):
            raise ValueError('SUFIXO_INCOMPATIVEL_COM_CODIFICADOR')
        return self

    def codificar(self, unidade: Unidade, *, administradora_id: str) -> tuple[str, str]:
        if (administradora_id, unidade.administradora_id, unidade.condominio_id) != (
                self.administradora_id, self.administradora_id, self.condominio_id):
            raise ErroLeitura('PERFIL_IDENTIFICADORES_DE_OUTRO_CONDOMINIO')
        if self.codificador == 'itajuba_documental':
            try:complemento=complemento_itajuba(unidade.bloco_original,unidade.unidade_original)
            except ValueError:raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')from None
            return f'{complemento}-{self.sufixo_cedente}',complemento
        if self.codificador == 'oma_documental':
            try:
                complemento = complemento_oma(unidade.bloco_original, unidade.unidade_original)
            except ValueError:
                raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL') from None
            return f'{complemento}-{self.sufixo_cedente}', complemento
        if self.codificador == 'forest_hill_documental':
            if unidade.bloco_original != '':
                raise ErroLeitura('FOREST_HILL_BLOCO_NAO_DOCUMENTADO')
            try:
                complemento = complemento_unidade(unidade.unidade_original)
            except ValueError:
                raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL') from None
            return f'{complemento}-{self.sufixo_cedente}', complemento
        if self.codificador == 'bloco_tipo_unidade':
            formato = next((f for f in self.formatos_unidade if f.bloco_original == unidade.bloco_original), None)
            if formato is None:
                raise ErroLeitura('TORRE_SEM_MAPEAMENTO_DOCUMENTAL')
            numero = unidade.unidade_original
            if formato.tipo == 'numerica':
                if not numero.isascii() or not numero.isdigit():
                    raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
                cedente = (numero.lstrip('0') or '0').zfill(formato.largura_cedente)
                complemento = (numero.lstrip('0') or '0').zfill(formato.largura_complemento)
                if len(cedente) > formato.largura_cedente:
                    raise ErroLeitura('UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')
            else:
                if not re.fullmatch(formato.padrao_literal, numero):
                    raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
                cedente = complemento = numero
            return (f'BL{formato.bloco_cedente}-{formato.prefixo_cedente}{cedente}-{self.sufixo_cedente}',
                    f'BL{formato.bloco_complemento}-{formato.prefixo_complemento}{complemento}')
        if self.codificador == 'bloco_unidade_textual':
            bloco,numero=unidade.bloco_original,unidade.unidade_original
            if any(not v or v!=v.strip()or any(c.isspace()or not c.isprintable()for c in v)for v in (bloco,numero)):
                raise ErroLeitura('IDENTIFICADOR_TEXTUAL_AMBIGUO')
            if self.tratamento_unidade_numerica=='largura_comprovada'and numero.isascii()and numero.isdigit():
                numero=(numero.lstrip('0')or'0').zfill(self.largura_unidade)
                if len(numero)>self.largura_unidade:
                    raise ErroLeitura('UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')
            # Não usa a chave normalizada nem converte códigos originais para int.
            identificador=f'Bloc{bloco}-Uni{numero}'
            return identificador,identificador
        sem_bloco = self.codificador == 'unidade_sufixo' and not self.torres and unidade.bloco_original == ''
        if not sem_bloco and unidade.bloco_original not in self.torres:
            raise ErroLeitura('TORRE_SEM_MAPEAMENTO_DOCUMENTAL')
        numero = unidade.unidade_original
        if not numero.isascii() or not numero.isdigit():
            raise ErroLeitura('UNIDADE_SEM_CODIFICACAO_DOCUMENTAL')
        numero = (numero.lstrip('0') or '0').zfill(self.largura_unidade)
        if len(numero) > self.largura_unidade:
            raise ErroLeitura('UNIDADE_FORA_DA_LARGURA_DOCUMENTADA')
        if self.codificador == 'unidade_sufixo':
            complemento=f'BL-UNI{numero}'
            return f'{complemento}-{self.sufixo_cedente}',complemento
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


def registrar_codigo_integracao(vistos, codigo, unidade_id, origem=None):
    """Uma representação não pode fundir unidades distintas após codificação."""
    if codigo in vistos and vistos[codigo]!=unidade_id:
        raise ErroLeitura('CEDENTE_AMBIGUO_APOS_CODIFICACAO',
            pagina=origem.pagina if origem else None,linha=origem.linha if origem else None)
    vistos[codigo]=unidade_id
