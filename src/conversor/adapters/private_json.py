"""JSON local atômico, com permissão 0600; nunca escreve conteúdo no terminal."""
import json
import os
from pathlib import Path
import tempfile

from .private_permissions import proteger_novo_windows


def escrever_json(caminho, dados):
    conteudo = (json.dumps(dados, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, prefix=".json-", delete=False) as arq:
            temporario = Path(arq.name)
            proteger_novo_windows(temporario)
            arq.write(conteudo)
            arq.flush()
            os.fsync(arq.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
