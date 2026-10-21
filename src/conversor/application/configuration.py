from datetime import date

from pydantic import ValidationError

from conversor.domain.catalog import (Administradora, Catalogo, Condominio, Formato,
                                     PerfilCondominio, Processamento, RegraCobranca)
from conversor.domain.canonical import Ocorrencia
from conversor.domain.template import Template
from .ports import ErroAplicacao, Repositorio

COLECOES = tuple(nome for nome in Catalogo.model_fields if nome != "schema_version")


class Configuracao:
    def __init__(self, repositorio: Repositorio):
        self.repositorio = repositorio

    def inicializar(self):
        return self.repositorio.salvar(Catalogo(), revisao_esperada=0)

    # Fachadas tipadas por responsabilidade, sobre a mesma unidade de trabalho.
    def get_administradora(self, id_: str) -> Administradora:
        return self.obter("administradoras", id_)

    def get_condominio(self, id_: str) -> Condominio:
        return self.obter("condominios", id_)

    def get_formato(self, id_: str) -> Formato:
        return self.obter("formatos", id_)

    def formatos_da_administradora(self, administradora_id: str) -> tuple[Formato, ...]:
        self.get_administradora(administradora_id)
        return tuple(f for f in self.repositorio.carregar().catalogo.formatos if administradora_id in f.administradora_ids)

    def get_perfil(self, id_: str) -> PerfilCondominio:
        return self.obter("perfis_condominio", id_)

    def get_regra(self, id_: str) -> RegraCobranca:
        return self.obter("regras_cobranca", id_)

    def get_template(self, id_: str) -> Template:
        return self.obter("templates", id_)

    def get_processamento(self, id_: str) -> Processamento:
        return self.obter("processamentos", id_)

    def salvar_processamento(self, processamento: Processamento, *, revisao_esperada: int):
        return self.gravar("processamentos", processamento.model_dump(mode="json"), revisao_esperada=revisao_esperada)

    def salvar_ocorrencia(self, ocorrencia: Ocorrencia, *, revisao_esperada: int):
        return self.gravar("ocorrencias", ocorrencia.model_dump(mode="json"), revisao_esperada=revisao_esperada)

    def importar(self, catalogo: Catalogo, *, revisao_esperada: int):
        return self.repositorio.salvar(catalogo, revisao_esperada=revisao_esperada)

    def obter(self, colecao: str, id_: str):
        self._colecao(colecao)
        for item in getattr(self.repositorio.carregar().catalogo, colecao):
            if item.id == id_:
                return item
        raise ErroAplicacao("REGISTRO_INEXISTENTE")

    def listar_ids(self, colecao: str):
        self._colecao(colecao)
        return tuple(sorted(i.id for i in getattr(self.repositorio.carregar().catalogo, colecao)))

    def gravar(self, colecao: str, registro: dict, *, revisao_esperada: int):
        self._colecao(colecao)
        estado = self.repositorio.carregar()
        if estado.revisao != revisao_esperada:
            raise ErroAplicacao("CONFLITO_DE_REVISAO")
        dados = estado.catalogo.model_dump(mode="json")
        itens = dados[colecao]
        dados[colecao] = [i for i in itens if i["id"] != registro.get("id")] + [registro]
        return self._salvar_dados(dados, revisao_esperada)

    def excluir(self, colecao: str, id_: str, *, revisao_esperada: int):
        self._colecao(colecao)
        estado = self.repositorio.carregar()
        if estado.revisao != revisao_esperada:
            raise ErroAplicacao("CONFLITO_DE_REVISAO")
        dados = estado.catalogo.model_dump(mode="json")
        itens = dados[colecao]
        dados[colecao] = [i for i in itens if i["id"] != id_]
        if len(dados[colecao]) == len(itens):
            raise ErroAplicacao("REGISTRO_INEXISTENTE")
        return self._salvar_dados(dados, revisao_esperada)

    def encontrar_condominio(self, administradora_id: str, codigo: str):
        for condo in self.repositorio.carregar().catalogo.condominios:
            if (condo.administradora_id, condo.codigo_na_administradora) == (administradora_id, codigo):
                return condo
        raise ErroAplicacao("REGISTRO_INEXISTENTE")

    def regra_aprovada(self, condominio_id: str, data_ref: date):
        regras = [r for r in self.repositorio.carregar().catalogo.regras_cobranca
                  if r.condominio_id == condominio_id and r.status == "aprovada"
                  and r.vigente_de <= data_ref and (r.vigente_ate is None or data_ref < r.vigente_ate)]
        if len(regras) != 1:
            raise ErroAplicacao("REGRA_APROVADA_INDISPONIVEL")
        return regras[0]

    def validar_classificacao(self, classificacao):
        """Valida declaração recebida; não reconhece arquivos nem escolhe candidato."""
        if classificacao.bloqueante:
            raise ErroAplicacao("FORMATO_NAO_RESOLVIDO")
        formato = self.obter("formatos", classificacao.candidatos[0])
        if formato.status != "validado":
            raise ErroAplicacao("FORMATO_NAO_VALIDADO")
        return formato

    @staticmethod
    def _colecao(colecao):
        if colecao not in COLECOES:
            raise ErroAplicacao("COLECAO_INVALIDA")

    def _salvar_dados(self, dados, revisao):
        try:
            catalogo = Catalogo.model_validate(dados)
        except ValidationError:
            raise ErroAplicacao("CONFIGURACAO_INVALIDA_OU_REFERENCIA_VIOLADA") from None
        return self.repositorio.salvar(catalogo, revisao_esperada=revisao)
