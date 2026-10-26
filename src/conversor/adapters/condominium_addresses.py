"""Cadastro privado de endereços: histórico, concorrência e substituição atômica."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal

from filelock import FileLock
from pydantic import ValidationError, model_validator

from conversor.adapters.private_json import escrever_json
from conversor.domain.base import Id, Modelo
from conversor.domain.canonical import Endereco
from conversor.export.identifiers import EnderecoPadrao, OrigemEnderecoUsuario
from conversor.readers.text_support import ErroLeitura
from conversor.validacao_leitores import _area_fora_do_git


def identidade(administradora_id, condominio_id):
    return 'endereco:' + sha256((administradora_id + '\0' + condominio_id).encode()).hexdigest()


class RegistroEndereco(Modelo):
    administradora_id: Id
    condominio_id: Id
    padrao: EnderecoPadrao

    @model_validator(mode='after')
    def origem_manual(self):
        origem = self.padrao.evidencia
        if not isinstance(origem, OrigemEnderecoUsuario) or origem.registro_id != identidade(self.administradora_id, self.condominio_id):
            raise ValueError('ORIGEM_DO_CADASTRO_INCOMPATIVEL')
        return self


class AcervoEnderecos(Modelo):
    schema_versao: Literal['1.0'] = '1.0'
    registros: tuple[RegistroEndereco, ...] = ()

    @model_validator(mode='after')
    def historico_integro(self):
        vistos = {}
        for r in self.registros:
            chave = (r.administradora_id, r.condominio_id)
            ultimo = vistos.get(chave)
            origem = r.padrao.evidencia
            if origem.versao != (ultimo.versao + 1 if ultimo else 1) or ultimo and origem.registrado_em < ultimo.registrado_em:
                raise ValueError('HISTORICO_DE_ENDERECOS_INVALIDO')
            vistos[chave] = origem
        return self


class RepositorioEnderecos:
    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        _area_fora_do_git(self.raiz)
        self.caminho = self.raiz / 'enderecos_condominios.json'
        self.trava = self.raiz / '.enderecos_condominios.lock'

    def _conferir_caminhos(self):
        if self.raiz.is_symlink() or self.caminho.is_symlink() or self.trava.is_symlink():
            raise ErroLeitura('CADASTRO_ENDERECOS_NAO_PODE_SER_LINK')

    def _carregar(self):
        if not self.caminho.exists():
            return AcervoEnderecos()
        try:
            return AcervoEnderecos.model_validate_json(self.caminho.read_bytes())
        except (ValidationError, OSError):
            raise ErroLeitura('CADASTRO_ENDERECOS_INVALIDO') from None

    def obter(self, administradora_id, condominio_id):
        self._conferir_caminhos()
        with FileLock(self.trava, timeout=5):
            acervo = self._carregar()
        return next((r.padrao for r in reversed(acervo.registros)
            if (r.administradora_id, r.condominio_id) == (administradora_id, condominio_id)), None)

    def salvar(self, administradora_id, condominio_id, endereco: Endereco, *, versao_esperada, sessao_sha256):
        self._conferir_caminhos()
        with FileLock(self.trava, timeout=5):
            acervo = self._carregar()
            anterior = next((r for r in reversed(acervo.registros)
                if (r.administradora_id, r.condominio_id) == (administradora_id, condominio_id)), None)
            versao = anterior.padrao.evidencia.versao if anterior else 0
            if versao != versao_esperada:
                raise ErroLeitura('ENDERECO_ALTERADO_POR_OUTRA_SESSAO')
            registro = RegistroEndereco(administradora_id=administradora_id, condominio_id=condominio_id,
                padrao=EnderecoPadrao(endereco=endereco, evidencia=OrigemEnderecoUsuario(
                    registro_id=identidade(administradora_id, condominio_id), versao=versao+1,
                    registrado_em=datetime.now(timezone.utc), sessao_sha256=sessao_sha256)))
            novo = AcervoEnderecos(registros=(*acervo.registros, registro))
            escrever_json(self.caminho, novo.model_dump(mode='json'))
            return registro.padrao
