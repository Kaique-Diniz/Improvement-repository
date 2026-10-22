"""Execução atual verificada e reprodução histórica explicitamente não operacional."""
from hashlib import sha256
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
import platform

from conversor.domain.billing_rules import hash_modelo
from conversor.domain.private_simulation import ExecucaoPrivada, ReproducaoHistorica
from .billing_evaluation import SimularCobranca
from .billing_evaluation_ports import VerificadorEstadoPlanos
from .billing_ports import RepositorioPlanos
from .ports import ErroAplicacao
from .private_simulation_ports import RepositorioSimulacoes, VerificadorHistoricoPlanos
from .simulation_inventory import conferir_pacote


def hash_implementacao():
    """Pin do código que interpreta os DTOs/regras, independente do caminho do host."""
    digest = sha256()
    digest.update(platform.python_version().encode())
    for pacote in ('pydantic', 'openpyxl'):
        digest.update((pacote + ':' + version(pacote)).encode())
    for nome in ('domain.base', 'domain.canonical', 'domain.documents', 'domain.billing_rules',
                 'domain.billing_lifecycle', 'domain.billing_evaluation', 'domain.private_simulation',
                 'application.documents', 'application.billing_evaluation', 'application.simulation_inventory',
                 'application.private_simulation', 'rules.conditions', 'rules.engine'):
        modulo = import_module('conversor.' + nome)
        digest.update(nome.encode() + b'\0' + Path(modulo.__file__).read_bytes() + b'\0')
    return digest.hexdigest()


class _SnapshotHistorico:
    """Só usado após autenticar o arquivo privado e todos os eventos históricos."""
    def __init__(self, estado):
        self.estado = estado

    def carregar(self):
        return self.estado


class SimuladorPrivado:
    def __init__(self, armazenamento: RepositorioSimulacoes, planos: RepositorioPlanos,
                 verificador_atual: VerificadorEstadoPlanos, verificador_historico: VerificadorHistoricoPlanos):
        self.armazenamento = armazenamento
        self.planos = planos
        self.atual = verificador_atual
        self.historico = verificador_historico

    def executar(self, *, id_, pacote_id, solicitacao, em, fundamento, evidencia_id, credencial):
        # Não recebe canônico/ocorrências avulsas: só pacote registrado sob autoridade.
        pacote = self.armazenamento.carregar_pacote(pacote_id)
        conferir_pacote(pacote)
        if (solicitacao.condominio_id, solicitacao.ambiente) != (pacote.condominio_id, pacote.ambiente):
            raise ErroAplicacao('SOLICITACAO_DE_OUTRO_PACOTE')
        if solicitacao.data_ref != pacote.atesto.data_ref:
            raise ErroAplicacao('COMPLETUDE_NAO_ATESTADA_PARA_DATA_REF')
        estado = self.planos.carregar()
        self.atual.conferir(estado)
        relatorio = SimularCobranca(self.planos, self.atual).executar(solicitacao, pacote.entrada)
        if relatorio.prova_plano.hash_estado != hash_modelo(estado):
            raise ErroAplicacao('CONFIGURACAO_ALTERADA_DURANTE_SIMULACAO_PRIVADA')
        execucao = ExecucaoPrivada(id=id_, condominio_id=pacote.condominio_id, ambiente=pacote.ambiente,
            pacote_id=pacote.id, pacote_hash=hash_modelo(pacote), implementacao_hash=hash_implementacao(),
            estado_planos=estado, relatorio=relatorio, em=em, fundamento=fundamento, evidencia_id=evidencia_id)
        # Conferência também após avaliar; persistir não estende a autorização temporal.
        self.atual.conferir(estado)
        if hash_modelo(self.armazenamento.carregar_pacote(pacote_id)) != hash_modelo(pacote):
            raise ErroAplicacao('PACOTE_ALTERADO_DURANTE_SIMULACAO')
        self.armazenamento.gravar_execucao(execucao, credencial=credencial)
        # Se a configuração mudar durante a gravação, não devolver resultado como execução atual.
        # O arquivo já comprometido continua evidência histórica, sempre sem autorização operacional.
        self.atual.conferir(estado)
        return execucao

    def reproduzir(self, id_):
        """Pode reproduzir decisão antiga revogada, jamais a promover a autorização atual."""
        execucao = self.armazenamento.carregar_execucao(id_)
        pacote = self.armazenamento.carregar_pacote(execucao.pacote_id)
        conferir_pacote(pacote)
        if hash_modelo(pacote) != execucao.pacote_hash:
            raise ErroAplicacao('PACOTE_HISTORICO_DIVERGENTE')
        if hash_implementacao() != execucao.implementacao_hash:
            raise ErroAplicacao('IMPLEMENTACAO_HISTORICA_INDISPONIVEL')
        self.historico.conferir(execucao.estado_planos)
        # Snapshot só entra aqui, autenticado pelo armazenamento e pela autoridade 4.1.
        snapshot = _SnapshotHistorico(execucao.estado_planos)
        relatorio = SimularCobranca(snapshot, self.historico).executar(
            execucao.relatorio.solicitacao, pacote.entrada)
        if hash_modelo(relatorio) != hash_modelo(execucao.relatorio):
            raise ErroAplicacao('REPRODUCAO_HISTORICA_DIVERGENTE')
        return ReproducaoHistorica(execucao_id=execucao.id,
            hash_relatorio_original=hash_modelo(execucao.relatorio), relatorio=relatorio)

    def comparar(self, *, id_, execucao_id, mapeamento, template, comparador, credencial):
        # Verificar decisões arquivadas, não aceitar relatório solto do chamador.
        self.reproduzir(execucao_id)
        execucao = self.armazenamento.carregar_execucao(execucao_id)
        pacote = self.armazenamento.carregar_pacote(execucao.pacote_id)
        resultado = comparador.comparar(id_=id_, execucao=execucao, pacote=pacote,
            mapeamento=mapeamento, template=template)
        self.armazenamento.gravar_comparacao(resultado, credencial=credencial)
        return resultado

    def reproduzir_comparacao(self, id_, *, comparador):
        original = self.armazenamento.carregar_comparacao(id_)
        self.reproduzir(original.execucao_id)
        execucao = self.armazenamento.carregar_execucao(original.execucao_id)
        pacote = self.armazenamento.carregar_pacote(execucao.pacote_id)
        atual = comparador.comparar(id_=original.id, execucao=execucao, pacote=pacote,
            mapeamento=original.mapeamento, template=original.template)
        if hash_modelo(atual) != hash_modelo(original):
            raise ErroAplicacao('COMPARACAO_HISTORICA_DIVERGENTE')
        return atual
