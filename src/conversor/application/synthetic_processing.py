"""Reutiliza SimularCobranca para simulação sintética e projeção universal A/B."""
from hashlib import sha256

from pydantic import ValidationError

from conversor.domain.billing_evaluation import EntradaSimulacao, SolicitacaoSimulacao
from conversor.domain.canonical import Ocorrencia
from conversor.domain.documents import resolver_documento
from conversor.domain.synthetic_processing import (
    CandidatoCadastroSimulado, ProjecaoProcessamentoSintetico,
    RetencaoCadastroSimulado, SolicitacaoProcessamentoSintetico,
)
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.rules.conditions import origens_unicas
from .billing_evaluation import SimularCobranca
from .billing_evaluation_ports import VerificadorEstadoPlanos
from .billing_ports import RepositorioPlanos
from .ports import ErroAplicacao


def _entrada_com_revisoes(entrada, processamento_id):
    # Política restrita ao incremento 4.3B.1, confirmada pelo responsável:
    # CPF/CNPJ inválido exige revisão; ausente continua somente alerta.
    extras = []
    for unidade in entrada.lote.unidades:
        titulares = [p for p in entrada.lote.pessoas if p.unidade_id == unidade.id]
        problemas = []
        if len(titulares) != 1:
            problemas.append(('TITULAR_AUSENTE_OU_AMBIGUO_43B1', unidade.origem, ()))
        else:
            pessoa = titulares[0]
            if not pessoa.nome.strip():
                problemas.append(('NOME_TITULAR_AUSENTE_43B1', pessoa.origem, ()))
            documento = resolver_documento(pessoa)
            if 'DOCUMENTO_INVALIDO' in documento.codigos:
                problemas.append(('DOCUMENTO_INVALIDO_REQUER_REVISAO_43B1',
                                  pessoa.documento_origem or pessoa.origem, documento.evidencias))
        for codigo, origem, evidencias in problemas:
            identidade = sha256(bytes_canonicos([processamento_id, unidade.id, codigo])).hexdigest()
            extras.append(Ocorrencia(id='revisao_sintetica:' + identidade,
                          processamento_id=processamento_id, codigo=codigo, gravidade='critico',
                          escopo='registro', registro_id=unidade.id, origem=origem,
                          evidencias_documentais=evidencias))
    mapa = {o.id: o for o in entrada.ocorrencias_anteriores}
    for o in extras:
        if o.id in mapa and mapa[o.id] != o:
            raise ErroAplicacao('REVISOES_SINTETICAS_COM_IDENTIDADE_CONFLITANTE')
        mapa[o.id] = o
    return EntradaSimulacao.model_validate(entrada.model_dump() | {
        'ocorrencias_anteriores': tuple(mapa[k] for k in sorted(mapa))})


class SimularProcessamentoSintetico:
    """Sem leitura de PDFs, aprovação, ativação, persistência ou exportação.

    Os planos vêm do repositório/verificador 4.1. A solicitação só aceita ambiente
    sintético; conferir_acervo do motor exige natureza sintética nesse ambiente.
    Os mesmos controles de versão/hash/assinatura/vigência permanecem obrigatórios.
    """
    def __init__(self, repositorio: RepositorioPlanos, verificador: VerificadorEstadoPlanos):
        self.motor = SimularCobranca(repositorio, verificador)

    def executar(self, solicitacao: SolicitacaoProcessamentoSintetico,
                 entrada: EntradaSimulacao) -> ProjecaoProcessamentoSintetico:
        try:
            s = SolicitacaoProcessamentoSintetico.model_validate(solicitacao.model_dump(warnings=False))
            e = EntradaSimulacao.model_validate(entrada.model_dump(warnings=False))
            e = _entrada_com_revisoes(e, s.processamento_id)
        except ValidationError:
            raise ErroAplicacao('CONTRATO_DE_PROCESSAMENTO_SINTETICO_INVALIDO') from None
        dados = s.model_dump()
        dados.pop('modo_cadastro')
        rel = self.motor.executar(SolicitacaoSimulacao.model_validate(dados), e)
        dividas = tuple(d.boleto_id for d in rel.boletos if d.situacao == 'elegivel_na_simulacao')
        cadastros, retencoes = [], []
        if s.modo_cadastro == 'B':
            for u in sorted(e.lote.unidades, key=lambda u: u.id):
                decisoes = [d for d in rel.boletos if d.unidade_id == u.id]
                retidos = [d for d in decisoes if d.situacao in ('bloqueado', 'pendente_revisao')]
                excluidos = [d for d in decisoes if d.situacao == 'excluido']
                if retidos:
                    retencoes.append(RetencaoCadastroSimulado(unidade_id=u.id,
                                     motivo_codigo='UNIDADE_COM_BLOQUEIO_OU_REVISAO',
                                     boletos_retidos=tuple(d.boleto_id for d in retidos)))
                elif excluidos:
                    cadastros.append(CandidatoCadastroSimulado(unidade_id=u.id,
                                     boletos_nao_elegiveis=tuple(d.boleto_id for d in excluidos),
                                     origens=origens_unicas(o for d in excluidos for o in d.origens)))
        return ProjecaoProcessamentoSintetico(modo_cadastro=s.modo_cadastro, relatorio_motor=rel,
                   hash_relatorio_motor=hash_modelo(rel), boletos_divida=dividas,
                   candidatos_cadastrais=tuple(cadastros), retencoes_cadastrais=tuple(retencoes))
