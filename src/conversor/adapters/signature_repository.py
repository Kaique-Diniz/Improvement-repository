from pathlib import Path

from pydantic import ValidationError

from conversor.application.ports import ErroAplicacao
from conversor.domain.recognition import CatalogoAssinaturas
from .json_repository import ler_json_bytes


class AssinaturasJSON:
    """Leitura de uma versão completa; runtime não altera nem aprova assinaturas."""
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo

    def carregar(self) -> CatalogoAssinaturas:
        try:
            with self.arquivo.open("rb") as fonte:
                conteudo = fonte.read(1024 * 1024 + 1)
            if len(conteudo) > 1024 * 1024:
                raise ErroAplicacao("ASSINATURAS_LIMITE_EXCEDIDO")
            dados = ler_json_bytes(conteudo)
            if not isinstance(dados, dict) or dados.get("schema_version") != "1.0":
                raise ErroAplicacao("ASSINATURAS_SCHEMA_NAO_SUPORTADO")
            return CatalogoAssinaturas.model_validate(dados)
        except ValidationError:
            raise ErroAplicacao("ASSINATURAS_INVALIDAS") from None
        except OSError:
            raise ErroAplicacao("FALHA_ACESSO_ASSINATURAS") from None
