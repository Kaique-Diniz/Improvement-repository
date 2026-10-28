"""Pertencimento documental ao destino; não aprova plano ou cobrança."""
from typing import Literal
from pydantic import model_validator
from .base import Hash, Id, Modelo, Texto
from .canonical import Origem


class UnidadeEscopoDestino(Modelo):
    unidade_id: Id
    chave_original: str
    estado: Literal['comprovado_documentalmente', 'nao_comprovado']
    motivo_codigo: Texto = 'SEM_EVIDENCIA_INDIVIDUAL_DE_DESTINO'
    recibos_comprovantes: tuple[Id, ...] = ()
    evidencias: tuple[Origem, ...] = ()

    @model_validator(mode='after')
    def comprovacao_explicita(self):
        if self.estado == 'comprovado_documentalmente' and (not self.recibos_comprovantes or not self.evidencias):
            raise ValueError('ESCOPO_EXIGE_EVIDENCIA_DOCUMENTAL')
        if len(set(self.recibos_comprovantes)) != len(self.recibos_comprovantes):
            raise ValueError('COMPROVANTE_DE_ESCOPO_DUPLICADO')
        return self


class EscopoDestinoDiagnostico(Modelo):
    versao: Literal['escopo_destino_documental@1.0.0'] = 'escopo_destino_documental@1.0.0'
    administradora_id: Id
    condominio_candidato_id: Id
    codigo_destino: Texto
    origem_documental: Literal['empreendimento_compartilhado'] = 'empreendimento_compartilhado'
    codigo_origem: Texto
    perfil_saida_sha256: Hash | None
    referencia_sha256: Hash | None
    fonte_financeira_sha256: Hash
    unidades: tuple[UnidadeEscopoDestino, ...]
    motivo_referencia: Texto
    atesto_humano: None = None
    exportacao_operacional: Literal[False] = False
    limite: str = 'Vínculo documental histórico para diagnóstico; não comprova todas as unidades do empreendimento nem aprova vigência, regras ou titularidade atual.'

    @model_validator(mode='after')
    def universo_unico(self):
        if len({u.unidade_id for u in self.unidades}) != len(self.unidades):
            raise ValueError('UNIDADE_DUPLICADA_NO_ESCOPO')
        if any(u.estado == 'comprovado_documentalmente' for u in self.unidades) and not self.referencia_sha256:
            raise ValueError('ESCOPO_SEM_FONTE')
        if any(o.sha256 != self.referencia_sha256 for u in self.unidades for o in u.evidencias):
            raise ValueError('EVIDENCIA_DE_OUTRA_FONTE_NO_ESCOPO')
        return self

    @property
    def permitidas(self):
        return frozenset(u.unidade_id for u in self.unidades if u.estado == 'comprovado_documentalmente')


class UnidadeEscopoPersistente(UnidadeEscopoDestino):
    origem_comprovacao: Literal['referencia_atual', 'cadastro_persistente'] | None = None
    vinculo_id: Hash | None = None
    vinculo_versao: int | None = None
    estado_vinculo: str = 'nao_registrado'


class EscopoDestinoPersistente(Modelo):
    """1.1 é aditivo; o contrato histórico 1.0 não é reinterpretado."""
    versao: Literal['escopo_destino_documental@1.1.0'] = 'escopo_destino_documental@1.1.0'
    administradora_id: Id
    condominio_candidato_id: Id
    codigo_destino: Texto
    origem_documental: Literal['empreendimento_compartilhado'] = 'empreendimento_compartilhado'
    codigo_origem: Texto
    perfil_saida_sha256: Hash | None
    referencia_sha256: Hash | None
    fonte_financeira_sha256: Hash
    unidades: tuple[UnidadeEscopoPersistente, ...]
    motivo_referencia: Texto
    cadastro_revisao: int | None
    cadastro_sha256: Hash | None
    hashes_fontes_verificadas: tuple[Hash, ...]
    resumo_cadastro: dict[str, int]
    erro_cadastro: str | None = None
    atesto_humano: None = None
    exportacao_operacional: Literal[False] = False
    limite: str = 'Vínculo de destino não aprova identidade pessoal, vigência financeira ou importação operacional.'

    @model_validator(mode='after')
    def conferir(self):
        if len({u.unidade_id for u in self.unidades}) != len(self.unidades):raise ValueError('UNIDADE_DUPLICADA_NO_ESCOPO')
        for u in self.unidades:
            if any(o.sha256 not in self.hashes_fontes_verificadas for o in u.evidencias):raise ValueError('EVIDENCIA_NAO_VERIFICADA')
            if u.estado=='comprovado_documentalmente':
                if u.origem_comprovacao=='cadastro_persistente':
                    if not self.cadastro_sha256 or not u.vinculo_id or u.estado_vinculo!='aprovado':raise ValueError('VINCULO_NAO_APROVADO')
                elif u.origem_comprovacao!='referencia_atual' or not self.referencia_sha256:raise ValueError('ESCOPO_SEM_FONTE')
        return self

    @property
    def permitidas(self):
        return frozenset(u.unidade_id for u in self.unidades if u.estado=='comprovado_documentalmente')
