from typing import Literal

from pydantic import Field

from conversor.domain.base import Modelo
from conversor.domain.canonical import LoteCanonico, ResultadoCobranca
from conversor.readers.text_support import ErroLeitura
from .contract import DividaExportacao, LinhaExportacao


class PerfilSaidaLaboratorio(Modelo):
    escopo: Literal["somente_testes_sinteticos"] = "somente_testes_sinteticos"
    codificador: Literal["habita_bloco_unidade", "fl_torre_unidade"]
    nome_cedente: str
    produto: str
    sufixo_cedente: str = ""
    torres: dict[str, str] = Field(default_factory=dict)
    parcela: int = Field(default=1, ge=1, strict=True)

    def codificar(self, unidade):
        if not unidade.unidade_original.isascii() or not unidade.unidade_original.isdigit():
            raise ErroLeitura("CODIFICACAO_UNIDADE_NAO_SUPORTADA")
        numero = str(int(unidade.unidade_original)).zfill(4)
        bloco = unidade.bloco_original
        if self.codificador == "habita_bloco_unidade":
            bloco = bloco.zfill(2) if bloco.isdigit() else bloco
            complemento = f"BL{bloco}-UNI{numero}"
            return complemento + self.sufixo_cedente, complemento
        if bloco not in self.torres:
            raise ErroLeitura("TORRE_SEM_MAPEAMENTO")
        torre = self.torres[bloco]
        return torre + numero, f"UNI{numero}-BL{torre}"


def construir_linhas(lote: LoteCanonico, resultados: tuple[ResultadoCobranca, ...], perfil: PerfilSaidaLaboratorio,
                     *, politica_cadastro: str, processamento_id: str, ocorrencias_extras=()):
    if politica_cadastro not in ("nunca", "unidades_com_boleto_adiado", "todas_unidades", "unidades_sem_divida"):
        raise ErroLeitura("POLITICA_CADASTRAL_INVALIDA")
    if any(o.bloqueante or o.processamento_id != processamento_id for o in ocorrencias_extras):
        raise ErroLeitura("EXPORTACAO_COM_BLOQUEIO")
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    if len(pessoas) != len(lote.pessoas):
        raise ErroLeitura("TITULAR_AMBIGUO")
    boletos = {b.id: b for b in lote.boletos}
    if len(resultados) != len(boletos) or {r.boleto_id for r in resultados} != set(boletos):
        raise ErroLeitura("RESULTADOS_DE_COBRANCA_INCOMPLETOS")
    if any(r.processamento_id != processamento_id or r.unidade_id != boletos[r.boleto_id].unidade_id for r in resultados):
        raise ErroLeitura("RESULTADO_DE_OUTRA_EXECUCAO_OU_UNIDADE")
    if any(r.acao in ("bloquear", "pendente") or any(o.bloqueante for o in r.ocorrencias) for r in resultados):
        raise ErroLeitura("EXPORTACAO_COM_BLOQUEIO")
    linhas, referencias, cedentes = [], [], {}
    for unidade in lote.unidades:
        avaliacoes = [r for r in resultados if r.unidade_id == unidade.id]
        if any(r.acao == "excluir" for r in avaliacoes):
            continue  # unidade excluída não fabrica linhas de contrato/dívida/cadastro
        if unidade.id not in pessoas:
            raise ErroLeitura("PESSOA_SEM_ORIGEM")
        pessoa = pessoas[unidade.id]
        extras = tuple(o for o in ocorrencias_extras if o.registro_id == unidade.id)
        origem_contato = pessoa.contato.origem or pessoa.origem
        origem_email = pessoa.origem if pessoa.origem.leitor_versao == "cadastro_fl_sintetico_v1" else origem_contato
        def ref(origem):
            return {"fonte_origem": origem.arquivo_id, "pagina": origem.pagina, "linha_fonte": origem.linha}
        origens_campos = {"NOME": ref(pessoa.origem), "CPF": ref(pessoa.origem)}
        origens_campos.update({campo: ref(origem_contato) for i in range(1, 6) for campo in (f"DDD{i}", f"FONE{i}")})
        origens_campos.update({f"EMAIL{i}": ref(origem_email) for i in range(1, 4)})
        cedente, complemento = perfil.codificar(unidade)
        if cedente in cedentes and cedentes[cedente] != unidade.id:
            raise ErroLeitura("CEDENTE_AMBIGUO_APOS_CODIFICACAO")
        cedentes[cedente] = unidade.id
        endereco = pessoa.contato.endereco.model_dump() | {"complemento": complemento}
        contato = pessoa.contato.model_dump() | {"endereco": endereco}
        pessoa = type(pessoa).model_validate(pessoa.model_dump() | {"contato": contato})
        base = dict(processamento_id=processamento_id, registro_id=unidade.id, nm_cedente_cedente=perfil.nome_cedente,
                    cedente=cedente, pessoa=pessoa)
        elegiveis = [r for r in avaliacoes if r.acao == "incluir"]
        for resultado in elegiveis:
            boleto = boletos[resultado.boleto_id]
            if boleto.composicao.total_original <= 0:
                raise ErroLeitura("VALOR_DE_COBRANCA_NAO_POSITIVO", boleto=boleto.identificador)
            ano, mes = boleto.competencia.split("-")
            divida = DividaExportacao(contrato=cedente, produto=perfil.produto,
                nome_divida=f"COTA {mes}/{ano} - {perfil.parcela}", parcela=perfil.parcela,
                vencimento=boleto.vencimento, valor=boleto.composicao.total_original)
            linhas.append(LinhaExportacao(**base, tipo="divida", divida=divida, ocorrencias=extras + resultado.ocorrencias))
            referencias.append({"tipo": "divida", "unidade_id": unidade.id, "boleto": boleto.identificador,
                "pagina": boleto.origens[0].pagina, "linha_fonte": boleto.origens[0].linha, "origens_campos": origens_campos})
        cadastrar = (politica_cadastro == "todas_unidades"
                     or (politica_cadastro == "unidades_com_boleto_adiado" and any(r.acao == "adiar" for r in avaliacoes))
                     or (politica_cadastro == "unidades_sem_divida" and not elegiveis))
        if cadastrar:
            linhas.append(LinhaExportacao(**base, tipo="cadastral", ocorrencias=extras))
            referencias.append({"tipo": "cadastral", "unidade_id": unidade.id, "boleto": None,
                "pagina": pessoa.origem.pagina, "linha_fonte": pessoa.origem.linha, "origens_campos": origens_campos})
    return tuple(linhas), referencias
