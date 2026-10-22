"""Lê histórico privado de forma completa e reproduz o mapeamento de identidades."""
from hashlib import sha256

from pydantic import ValidationError

from conversor.application.ports import ErroAplicacao
from conversor.domain.audit_identity import (FonteHistorico, LocalizacaoHistorica, ReconciliacaoOcorrencias, VinculoOcorrencia, id_auditoria)
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.canonical import Ocorrencia
from .billing_authority import ler_protegido
from .json_repository import ler_json_bytes


def reconstruir_reconciliacao(*, id_, condominio_id, ambiente, fontes):
    # Importação local evita ciclo com o adapter do repositório, que também verifica históricos.
    from .private_simulation_json import conferir_local_privado
    try:
        fontes = tuple(FonteHistorico.model_validate(f.model_dump(warnings=False)) for f in fontes)
        registros = []
        for fonte in sorted(fontes, key=lambda f: f.arquivo.arquivo_id):
            conteudo = ler_protegido(conferir_local_privado(fonte.arquivo.caminho, arquivo=True))
            if len(conteudo) != fonte.arquivo.tamanho or sha256(conteudo).hexdigest() != fonte.arquivo.sha256:
                raise ErroAplicacao('FONTE_HISTORICA_ALTERADA_OU_PARCIAL')
            dados = ler_json_bytes(conteudo)
            if fonte.estrutura == 'lista_ocorrencias':
                if not isinstance(dados, list):
                    raise ErroAplicacao('COLECAO_HISTORICA_OBRIGATORIA_AUSENTE')
                colecoes = [('', dados)]
            else:
                if not isinstance(dados, dict) or not isinstance(dados.get('casos'), list):
                    raise ErroAplicacao('CASOS_DOCUMENTAIS_OBRIGATORIOS_AUSENTES')
                colecoes = []
                for i, caso in enumerate(dados['casos']):
                    if not isinstance(caso, dict) or not isinstance(caso.get('ocorrencias'), list):
                        raise ErroAplicacao('OCORRENCIAS_DO_CASO_OBRIGATORIAS_AUSENTES')
                    colecoes.append((f'/casos/{i}/ocorrencias', caso['ocorrencias']))
            for prefixo, colecao in colecoes:
                for i, bruto in enumerate(colecao):
                    original = Ocorrencia.model_validate(bruto)
                    localizacao = LocalizacaoHistorica(arquivo_id=fonte.arquivo.arquivo_id,
                        arquivo_sha256=fonte.arquivo.sha256, ponteiro_json=f'{prefixo}/{i}',
                        namespace=fonte.namespace, produtor_id=fonte.produtor_id, produtor_versao=fonte.produtor_versao)
                    registros.append(VinculoOcorrencia(id_interno=id_auditoria(localizacao, original),
                        id_legado=original.id, hash_original=hash_modelo(original),
                        hash_registro_bruto=sha256(bytes_canonicos(bruto)).hexdigest(),
                        localizacao=localizacao, original=original))
        return ReconciliacaoOcorrencias(id=id_, condominio_id=condominio_id, ambiente=ambiente,
            fontes=tuple(sorted(fontes, key=lambda f: f.arquivo.arquivo_id)),
            registros=tuple(sorted(registros, key=lambda r: r.id_interno)))
    except ErroAplicacao:
        raise
    except (ValidationError, ValueError, UnicodeError):
        raise ErroAplicacao('HISTORICO_DE_OCORRENCIAS_INVALIDO') from None
    except OSError:
        raise ErroAplicacao('HISTORICO_DE_OCORRENCIAS_INDISPONIVEL') from None


def conferir_reconciliacao(reconciliacao):
    reconciliacao = ReconciliacaoOcorrencias.model_validate(reconciliacao.model_dump(warnings=False))
    reconstruida = reconstruir_reconciliacao(id_=reconciliacao.id, condominio_id=reconciliacao.condominio_id,
        ambiente=reconciliacao.ambiente, fontes=reconciliacao.fontes)
    if reconstruida != reconciliacao:
        raise ErroAplicacao('RECONCILIACAO_OMITE_OU_ALTERA_REGISTROS_HISTORICOS')
