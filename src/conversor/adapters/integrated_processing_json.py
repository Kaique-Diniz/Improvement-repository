"""Persistência sintética aditiva sobre o armazenamento assinado/atômico 4.3A."""
from hashlib import sha256
from pathlib import Path

from filelock import FileLock

from conversor.application.integrated_processing import conferir_contexto_integrado, conferir_preservacao_integrada
from conversor.application.ports import ErroAplicacao
from conversor.domain.integrated_processing import (
    DocumentoReguaSintetica, ExecucaoIntegradaSintetica, IdentidadeOperador,
    ReciboProcessamentoSintetico,
)
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from .billing_authority import ler_protegido, sem_links
from .json_repository import ler_json_bytes
from .private_simulation_json import RepositorioSimulacoesJSON, VerificadorHistoricoHMAC, seguro


class AutenticadorHMACEnsaioSintetico:
    """Permissão técnica `submeter` da autoridade 4.1, nunca aprovação de plano."""
    def __init__(self, autoridade):
        self.autoridade = autoridade

    @seguro
    def autenticar(self, pedido, credencial):
        if pedido.ambiente != 'sintetico':
            raise ErroAplicacao('ATO_OPERADOR_SOMENTE_SINTETICO')
        self.autoridade.conferir_protecao()
        ator, politica = self.autoridade.autorizar(credencial, 'submeter', pedido, 'sintetico')
        return IdentidadeOperador(responsavel_id=ator, politica_autorizacao_hash=politica)


class RepositorioProcessamentosSinteticosJSON(RepositorioSimulacoesJSON):
    @seguro
    def __init__(self, diretorio, *, repositorio_id, autoridade, ambiente='sintetico', timeout=5):
        if ambiente != 'sintetico':
            raise ErroAplicacao('REPOSITORIO_INTEGRADO_SOMENTE_SINTETICO')
        super().__init__(diretorio, repositorio_id=repositorio_id, autoridade=autoridade,
                         ambiente=ambiente, timeout=timeout)

    @seguro
    def carregar_regua(self, preparacao_id, referencia):
        prep = self.carregar_preparacao_tecnica(preparacao_id)
        fontes = [f for f in prep.candidato.fontes if
                  (f.arquivo_id, f.sha256, f.papel) == (referencia.arquivo_id, referencia.sha256, 'requisitos')]
        if len(fontes) != 1:
            raise ErroAplicacao('REGUA_FORA_DAS_FONTES_INVENTARIADAS')
        conteudo = ler_protegido(Path(fontes[0].caminho))
        if len(conteudo) != fontes[0].tamanho or sha256(conteudo).hexdigest() != referencia.sha256:
            raise ErroAplicacao('FONTE_REGUA_ALTERADA_DURANTE_LEITURA')
        documento = DocumentoReguaSintetica.model_validate(ler_json_bytes(conteudo))
        if (documento.id, documento.versao, documento.condominio_id) != (
                referencia.arquivo_id, referencia.versao, prep.condominio_id):
            raise ErroAplicacao('VERSAO_REGUA_INTEGRADA_DIVERGENTE')
        return documento

    def _conferir_execucao(self, execucao):
        prep = self.carregar_preparacao_tecnica(execucao.pedido.preparacao_id)
        regua = self.carregar_regua(prep.id, execucao.pedido.regua)
        VerificadorHistoricoHMAC(self.autoridade).conferir(execucao.estado_planos)
        self.autoridade.conferir_autorizacao_historica(execucao.ato.responsavel_id,
            execucao.ato.politica_autorizacao_hash, acao='submeter',
            condominio_id=execucao.condominio_id, ambiente='sintetico')
        conferir_contexto_integrado(execucao.pedido, prep, execucao.estado_planos, regua,
                                   execucao.administradora, execucao.condominio)
        conferir_preservacao_integrada(execucao, prep)

    @seguro
    def salvar_processamento(self, execucao, *, credencial):
        execucao = ExecucaoIntegradaSintetica.model_validate(execucao.model_dump(warnings=False))
        ator, politica = self.autoridade.autorizar(credencial, 'submeter', execucao, 'sintetico')
        if (ator, politica) != (execucao.ato.responsavel_id, execucao.ato.politica_autorizacao_hash):
            raise ErroAplicacao('ATO_OPERADOR_NAO_CORRESPONDE_A_CREDENCIAL')
        self._conferir_execucao(execucao)
        # Serializa a comparação idempotente e o commit; o lock histórico permanece inalterado.
        lock = sem_links(self.ancoras / 'processamentos.lock')
        with FileLock(lock, timeout=self.timeout, mode=0o600):
            destino, ancora = self._paths('processamento_sintetico', execucao.id)
            if ancora.exists():
                original = self.carregar_processamento(execucao.id)
                if hash_modelo(original) != hash_modelo(execucao):
                    raise ErroAplicacao('PROCESSAMENTO_IMUTAVEL_COM_PEDIDO_DIVERGENTE')
                return original
            if destino.exists() and ler_protegido(destino) != bytes_canonicos(execucao.model_dump(mode='json')):
                raise ErroAplicacao('PROCESSAMENTO_ORFAO_DIVERGENTE_REQUER_REVISAO')
            self._guardar('processamento_sintetico', execucao, credencial, ReciboProcessamentoSintetico)
        return execucao

    @seguro
    def carregar_processamento(self, id_):
        execucao = self._ler('processamento_sintetico', id_, ExecucaoIntegradaSintetica,
                             ReciboProcessamentoSintetico)
        self._conferir_execucao(execucao)
        return execucao
