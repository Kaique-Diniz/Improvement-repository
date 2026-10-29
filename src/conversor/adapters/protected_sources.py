"""Acesso local limitado a arquivos previamente autorizados por ID e SHA-256."""
from hashlib import sha256
import os
from pathlib import Path
import stat

from conversor.readers.contracts import FonteProtegida
from conversor.readers.text_support import ErroLeitura
from conversor.application.ports import ErroAplicacao
from .private_permissions import conferir_windows


class FontesLocaisProtegidas:
    def __init__(self, raiz: Path, arquivos: dict[str, str], *, limite_bytes=20 * 1024 * 1024):
        # Não apagar a evidência de redirecionamento resolvendo a raiz antes de conferir.
        self.raiz = Path(os.path.abspath(raiz))
        if any(p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400)
               for p in (self.raiz,*self.raiz.parents)):
            raise ErroLeitura('FONTE_CONTEM_LINK')
        self._arquivos = dict(arquivos)
        self.limite_bytes = limite_bytes

    def ler(self, fonte: FonteProtegida) -> bytes:
        if fonte.arquivo_id not in self._arquivos:
            raise ErroLeitura("FONTE_NAO_AUTORIZADA")
        relativo = Path(self._arquivos[fonte.arquivo_id])
        caminho = self.raiz / relativo
        if relativo.is_absolute() or ".." in relativo.parts or not caminho.resolve().is_relative_to(self.raiz):
            raise ErroLeitura("FONTE_FORA_DA_AREA_AUTORIZADA")
        if any(p.is_symlink() for p in (caminho, *caminho.parents) if p.is_relative_to(self.raiz)):
            raise ErroLeitura("FONTE_CONTEM_LINK")
        if not caminho.is_file():
            raise ErroLeitura("FONTE_INDISPONIVEL")
        try:
            conferir_windows(self.raiz);conferir_windows(caminho)
        except ErroAplicacao:
            raise ErroLeitura('PERMISSOES_DA_FONTE_NAO_COMPROVADAS')from None
        try:
            with caminho.open("rb") as arquivo:
                if not stat.S_ISREG(os.fstat(arquivo.fileno()).st_mode):
                    raise ErroLeitura("FONTE_NAO_REGULAR")
                conteudo = arquivo.read(self.limite_bytes + 1)
        except OSError:
            raise ErroLeitura("FONTE_INDISPONIVEL") from None
        if len(conteudo) > self.limite_bytes:
            raise ErroLeitura("FONTE_LIMITE_EXCEDIDO")
        if sha256(conteudo).hexdigest() != fonte.sha256:
            raise ErroLeitura("HASH_FONTE_DIVERGENTE")
        return conteudo
