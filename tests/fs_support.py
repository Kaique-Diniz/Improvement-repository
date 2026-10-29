"""Apoio a fixtures sintéticas; nunca usar para alterar a pasta privada do usuário."""
import os
import pytest


def symlink_ou_skip_1314(link, destino, **kwargs):
    try:link.symlink_to(destino,**kwargs)
    except OSError as erro:
        if getattr(erro,'winerror',None)==1314:
            pytest.skip('WinError 1314: criação de symlink indisponível sem privilégio adicional; somente este cenário de link real foi omitido.')
        raise


def assert_privado(path):
    if os.name=='posix':assert path.stat().st_mode&0o777 == (0o700 if path.is_dir() else 0o600)
    elif os.name=='nt':
        from conversor.adapters.private_permissions import conferir_windows
        conferir_windows(path)
    else:pytest.fail('Não há verificador de privacidade para este sistema.')


def ampliar_acesso_sintetico(path):
    if os.name=='posix':path.chmod(0o755 if path.is_dir()else 0o644)
    elif os.name=='nt':
        from conversor.adapters.private_permissions import _WindowsACL
        api=_WindowsACL();f='OICI'if path.is_dir()else''
        sddl='D:P'+''.join(f'(A;{f};FA;;;{sid})'for sid in (api.usuario(),'S-1-5-18','S-1-5-32-544'))+f'(A;{f};FR;;;WD)'
        api._aplicar_dacl(path,sddl)
    else:pytest.fail('Não há injeção de permissão equivalente para este sistema.')
