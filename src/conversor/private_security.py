"""Auditoria somente de leitura das permissões da área privada; não altera ACLs."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

from conversor.adapters.private_permissions import conferir_windows, _sem_redirecionamento
from conversor.application.ports import ErroAplicacao


def auditar(raiz):
    raiz=Path(os.path.abspath(raiz));falhas=Counter();arquivos=diretorios=0
    def conferir(path):
        try:
            _sem_redirecionamento(path)
            if os.name=='nt':conferir_windows(path)
            elif os.name=='posix':
                if path.stat().st_mode&0o077:raise ErroAplicacao('PERMISSOES_PRIVADAS_INSEGURAS')
            else:raise ErroAplicacao('PERMISSOES_NAO_VERIFICAVEIS')
            return True
        except (OSError,ErroAplicacao)as e:
            falhas[str(e) if isinstance(e,ErroAplicacao)else'ARQUIVO_INDISPONIVEL']+=1;return False
    if not raiz.is_dir():falhas['DIRETORIO_INDISPONIVEL']+=1
    elif conferir(raiz):
        def erro_passeio(_):falhas['DIRETORIO_NAO_PERCORRIDO']+=1
        for atual,dirs,files in os.walk(raiz,followlinks=False,onerror=erro_passeio):
            diretorios+=1
            dirs[:]=[d for d in dirs if conferir(Path(atual)/d)]
            for name in files:
                arquivos+=1;conferir(Path(atual)/name)
    return dict(versao='auditoria_permissoes@1',sistema=os.name,estado='nao_comprovado'if falhas else'politica_local_confere',
        arquivos=arquivos,diretorios=diretorios,falhas=dict(falhas),alteracoes_realizadas=0,
        limite='Política local de acesso; não atesta documentos, identidades, pertencimento ou produção. Administradores do sistema e a conta local continuam na fronteira de confiança.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private-dir',type=Path,required=True)
    p.add_argument('--comparar-leituras',action='store_true',help='Compara APIs nativas e GetAccessRules sem alterar ACLs ou exibir identidades reais.')
    a=p.parse_args()
    if a.comparar_leituras:
        from conversor.acl_diagnostics import diagnosticar
        r=diagnosticar(a.private_dir);print(json.dumps(r,ensure_ascii=True))
        return 0 if r.get('estado')=='leituras_coerentes'and r.get('politica_local')=='confere'else 2
    r=auditar(a.private_dir);print(json.dumps(r,ensure_ascii=True));return 2 if r['falhas']else 0


if __name__=='__main__':raise SystemExit(main())
