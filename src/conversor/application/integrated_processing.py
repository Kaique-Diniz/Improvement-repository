"""Orquestração sintética: inventário 4.3A -> motor 4.2/4.3B.1 -> histórico A/B."""
from hashlib import sha256
from importlib import import_module
from pathlib import Path

from pydantic import ValidationError

from conversor.domain.billing_rules import hash_modelo
from conversor.domain.billing_evaluation import ProvaPlanoSimulado
from conversor.domain.integrated_processing import (
    AtoOperadorSintetico, ExecucaoIntegradaSintetica, PedidoProcessamentoIntegrado,
    ReproducaoIntegradaSintetica,
)
from .billing_evaluation import normalizar_entrada, ocorrencias_aplicaveis, ocorrencias_da_entrada
from .billing_evaluation_ports import VerificadorEstadoPlanos
from .billing_ports import CredencialOperador, RepositorioPlanos
from .integrated_processing_ports import AutenticadorEnsaioSintetico, RepositorioProcessamentosSinteticos
from .ports import ErroAplicacao, RepositorioAdministradoras, RepositorioCondominios
from .private_simulation import hash_implementacao, _SnapshotHistorico
from .private_simulation_ports import VerificadorHistoricoPlanos
from .simulation_inventory import conferir_pacote
from .synthetic_processing import SimularProcessamentoSintetico, _entrada_com_revisoes


def hash_implementacao_integrada():
    # Não alterar o pin histórico do 4.3A: esta extensão possui pin próprio.
    digest = sha256(hash_implementacao().encode())
    for nome in ('domain.synthetic_processing', 'application.synthetic_processing',
                 'domain.integrated_processing', 'application.integrated_processing',
                 'adapters.integrated_processing_json'):
        modulo = import_module('conversor.' + nome)
        digest.update(nome.encode() + b'\0' + Path(modulo.__file__).read_bytes() + b'\0')
    return digest.hexdigest()


def conferir_contexto_integrado(pedido, preparacao, estado, regua, administradora, condominio):
    if preparacao.ambiente != 'sintetico' or estado.acervo.ambiente != 'sintetico':
        raise ErroAplicacao('CONTEXTO_INTEGRADO_SOMENTE_SINTETICO')
    if (preparacao.id, hash_modelo(preparacao), preparacao.condominio_id) != (
            pedido.preparacao_id, pedido.preparacao_hash, pedido.condominio_id):
        raise ErroAplicacao('PREPARACAO_INTEGRADA_DIVERGENTE')
    conferir_pacote(preparacao.candidato)
    if any(u.administradora_id != pedido.administradora_id for u in preparacao.candidato.entrada.lote.unidades):
        raise ErroAplicacao('UNIDADE_DE_OUTRA_ADMINISTRADORA')
    if (administradora.id, condominio.id, condominio.administradora_id) != (
            pedido.administradora_id, pedido.condominio_id, pedido.administradora_id
            ) or not administradora.ativo or not condominio.ativo:
        raise ErroAplicacao('VINCULO_ADMINISTRADORA_CONDOMINIO_INVALIDO')
    if not any(v.administradora_id == administradora.id and v.inicio <= pedido.data_ref
               and (v.fim is None or pedido.data_ref < v.fim) for v in condominio.vinculos):
        raise ErroAplicacao('ADMINISTRADORA_FORA_DO_VINCULO_NA_REFERENCIA')
    registros = [r for r in estado.acervo.registros if (r.conteudo.id, r.conteudo.versao) == (
        pedido.plano_id, pedido.plano_versao)]
    if len(registros) != 1:
        raise ErroAplicacao('PLANO_INTEGRADO_INEXISTENTE_OU_AMBIGUO')
    plano = registros[0].conteudo
    if plano.natureza != 'sintetico' or plano.condominio_id != pedido.condominio_id:
        raise ErroAplicacao('PLANO_INTEGRADO_DE_OUTRO_CONTEXTO')
    if hash_modelo(plano) != pedido.plano_hash:
        raise ErroAplicacao('VERSAO_OU_HASH_SOLICITADO_DIVERGENTE')
    if registros[0].estado != 'ativo':
        raise ErroAplicacao('PLANO_NAO_ATIVO_OU_REVOGADO')
    if not (plano.vigente_de <= pedido.data_ref and (plano.vigente_ate is None or pedido.data_ref < plano.vigente_ate)):
        raise ErroAplicacao('DATA_REF_FORA_DA_VIGENCIA_DO_PLANO')
    if (regua.id, regua.versao, regua.condominio_id) != (
            pedido.regua.arquivo_id, pedido.regua.versao, pedido.condominio_id):
        raise ErroAplicacao('VERSAO_REGUA_INTEGRADA_DIVERGENTE')
    if (any((o.arquivo_id, o.sha256) != (regua.id, pedido.regua.sha256) for o in plano.fontes)
            or not {r.fonte_id for r in plano.regras} <= set(regua.regra_ids)):
        raise ErroAplicacao('PLANO_NAO_VINCULADO_A_REGUA_INVENTARIADA')


def conferir_preservacao_integrada(execucao, preparacao):
    """Integridade/coverage, sem recalcular nem duplicar decisões financeiras."""
    p = execucao.pedido
    entrada = normalizar_entrada(_entrada_com_revisoes(preparacao.candidato.entrada, p.processamento_id))
    rel = execucao.projecao.relatorio_motor
    estado = execucao.estado_planos
    aprovacoes = [e for e in estado.acervo.eventos if e.plano_id == p.plano_id and e.acao == 'aprovar']
    ativacoes = [e for e in estado.acervo.eventos if e.plano_id == p.plano_id and e.acao == 'ativar']
    if not aprovacoes or not ativacoes:
        raise ErroAplicacao('APROVACAO_OU_ATIVACAO_AUSENTE')
    prova = ProvaPlanoSimulado(revisao_repositorio=estado.revisao, hash_estado=hash_modelo(estado),
        aprovacao_sequencia=aprovacoes[-1].sequencia, aprovacao_hash=hash_modelo(aprovacoes[-1]),
        ativacao_sequencia=ativacoes[-1].sequencia, ativacao_hash=hash_modelo(ativacoes[-1]))
    if rel.prova_plano != prova:
        raise ErroAplicacao('PROVA_INTEGRADA_DIVERGE_DOS_ATOS_ASSINADOS')
    ocorrencias = ocorrencias_da_entrada(entrada, p.processamento_id)
    if (rel.hash_entrada != hash_modelo(entrada) or rel.ocorrencias_anteriores != ocorrencias
            or rel.fatos_recebidos != entrada.fatos or rel.ressalvas_origem != entrada.lote.ressalvas
            or rel.coberturas_recebidas != entrada.coberturas_apontamentos):
        raise ErroAplicacao('EXECUCAO_INTEGRADA_OMITE_EVIDENCIAS')
    boletos = {b.id: b for b in entrada.lote.boletos}
    unidades = {u.id: u for u in entrada.lote.unidades}
    if (len(rel.boletos) != len(boletos) or {d.boleto_id for d in rel.boletos} != set(boletos)
            or len(rel.unidades) != len(unidades) or {d.unidade_id for d in rel.unidades} != set(unidades)):
        raise ErroAplicacao('EXECUCAO_INTEGRADA_OMITE_REGISTROS')
    for d in rel.boletos:
        b = boletos[d.boleto_id]
        locais = ocorrencias_aplicaveis(ocorrencias, unidades[b.unidade_id], b, entrada.lote)
        if (d.unidade_id != b.unidade_id or d.ocorrencias_preservadas != locais
                or any(o.bloqueante for o in locais) and d.situacao != 'bloqueado'):
            raise ErroAplicacao('EXECUCAO_INTEGRADA_CONTORNA_BLOQUEIOS')


class ProcessarEnsaioSintetico:
    def __init__(self, armazenamento: RepositorioProcessamentosSinteticos,
                 planos: RepositorioPlanos, atual: VerificadorEstadoPlanos,
                 historico: VerificadorHistoricoPlanos, autenticador: AutenticadorEnsaioSintetico,
                 administradoras: RepositorioAdministradoras, condominios: RepositorioCondominios):
        if armazenamento.ambiente != 'sintetico':
            raise ErroAplicacao('ARMAZENAMENTO_INTEGRADO_SOMENTE_SINTETICO')
        self.armazenamento, self.planos = armazenamento, planos
        self.atual, self.historico, self.autenticador = atual, historico, autenticador
        self.administradoras, self.condominios = administradoras, condominios

    def executar(self, pedido: PedidoProcessamentoIntegrado,
                 *, credencial: CredencialOperador) -> ExecucaoIntegradaSintetica:
        try:
            p = PedidoProcessamentoIntegrado.model_validate(pedido.model_dump(warnings=False))
        except ValidationError:
            raise ErroAplicacao('PEDIDO_INTEGRADO_INVALIDO') from None
        ator = self.autenticador.autenticar(p, credencial)
        if ator.responsavel_id != p.operador_id:
            raise ErroAplicacao('OPERADOR_INTEGRADO_NAO_AUTENTICADO')
        prep = self.armazenamento.carregar_preparacao_tecnica(p.preparacao_id)
        adm = self.administradoras.get_administradora(p.administradora_id)
        cond = self.condominios.get_condominio(p.condominio_id)
        regua = self.armazenamento.carregar_regua(p.preparacao_id, p.regua)
        estado = self.planos.carregar()
        self.atual.conferir(estado)
        conferir_contexto_integrado(p, prep, estado, regua, adm, cond)
        projecao = SimularProcessamentoSintetico(self.planos, self.atual).executar(
            p.solicitacao_sintetica(), prep.candidato.entrada)
        if projecao.relatorio_motor.prova_plano.hash_estado != hash_modelo(estado):
            raise ErroAplicacao('CONFIGURACAO_ALTERADA_DURANTE_PROCESSAMENTO')
        execucao = ExecucaoIntegradaSintetica(id=p.processamento_id, condominio_id=p.condominio_id,
            pedido=p, administradora=adm, condominio=cond, estado_planos=estado, projecao=projecao,
            ato=AtoOperadorSintetico(**ator.model_dump(), em=p.em, fundamento=p.fundamento,
                                   evidencia_id=p.evidencia_id), implementacao_hash=hash_implementacao_integrada())
        conferir_preservacao_integrada(execucao, prep)
        self.atual.conferir(estado)
        if hash_modelo(self.armazenamento.carregar_preparacao_tecnica(p.preparacao_id)) != hash_modelo(prep):
            raise ErroAplicacao('PREPARACAO_ALTERADA_DURANTE_PROCESSAMENTO')
        if (self.administradoras.get_administradora(adm.id) != adm
                or self.condominios.get_condominio(cond.id) != cond):
            raise ErroAplicacao('CATALOGO_ALTERADO_DURANTE_PROCESSAMENTO')
        salvo = self.armazenamento.salvar_processamento(execucao, credencial=credencial)
        self.atual.conferir(estado)
        return salvo

    def reproduzir(self, id_) -> ReproducaoIntegradaSintetica:
        original = self.armazenamento.carregar_processamento(id_)
        p = original.pedido
        prep = self.armazenamento.carregar_preparacao_tecnica(p.preparacao_id)
        regua = self.armazenamento.carregar_regua(p.preparacao_id, p.regua)
        conferir_contexto_integrado(p, prep, original.estado_planos, regua,
                                   original.administradora, original.condominio)
        if original.implementacao_hash != hash_implementacao_integrada():
            raise ErroAplicacao('IMPLEMENTACAO_INTEGRADA_HISTORICA_INDISPONIVEL')
        self.historico.conferir(original.estado_planos)
        projecao = SimularProcessamentoSintetico(_SnapshotHistorico(original.estado_planos),
            self.historico).executar(p.solicitacao_sintetica(), prep.candidato.entrada)
        if hash_modelo(projecao) != hash_modelo(original.projecao):
            raise ErroAplicacao('REPRODUCAO_INTEGRADA_DIVERGENTE')
        return ReproducaoIntegradaSintetica(execucao_id=original.id,
            hash_execucao=hash_modelo(original), projecao=projecao)
