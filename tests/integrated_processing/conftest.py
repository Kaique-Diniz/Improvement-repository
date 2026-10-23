"""Integração real dos adapters com fontes inventadas; nenhum atesto humano."""
from hashlib import sha256
from types import SimpleNamespace

import pytest

from conversor.adapters.audit_history import reconstruir_reconciliacao
from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.adapters.integrated_processing_json import (
    AutenticadorHMACEnsaioSintetico, RepositorioProcessamentosSinteticosJSON,
)
from conversor.adapters.private_simulation_json import VerificadorHistoricoHMAC
from conversor.application.billing_evaluation import normalizar_entrada
from conversor.application.integrated_processing import ProcessarEnsaioSintetico
from conversor.application.ports import ErroAplicacao
from conversor.application.simulation_inventory import inventariar
from conversor.domain.audit_identity import CandidatoReconciliado, FonteHistorico, PreparacaoTecnica
from conversor.domain.billing_evaluation import EntradaSimulacao
from conversor.domain.billing_rules import bytes_canonicos, hash_modelo
from conversor.domain.catalog import Administradora, Condominio
from conversor.domain.integrated_processing import DocumentoReguaSintetica, PedidoProcessamentoIntegrado
from conversor.domain.private_simulation import CATEGORIAS, CatalogoImpedimentos, FontePrivada
from tests.synthetic_processing.conftest import montar, repo, gestor, seguranca


@pytest.fixture
def integrado(montar, tmp_path, seguranca, gestor):
    def preparar(*, specs=None, modo='A', estado='ativo', ocorrencias=(), documentais=(),
                 editar_plano=None, editar_entrada=None):
        primaria = tmp_path / 'fonte-inventada.txt'
        primaria.write_bytes(b'Fonte de teste sintetica 4.3B.2A; sem documentos reais.\n')
        primaria.chmod(0o600)
        digest = sha256(primaria.read_bytes()).hexdigest()
        regua = DocumentoReguaSintetica(natureza='sintetico', id='requisitos_inventados_43b1',
            versao='1.0.0', condominio_id='cond_sintetico', regra_ids=(
                'tree_centavo', 'tree_apontamento_a', 'tree_apontamento_aj',
                'tree_apontamento_j', 'tree_prazo_30'))
        regua_path = tmp_path / 'regua-inventada.json'
        regua_path.write_bytes(bytes_canonicos(regua.model_dump(mode='json')))
        regua_path.chmod(0o600)
        regua_hash = sha256(regua_path.read_bytes()).hexdigest()
        def editar(dados):
            for o in dados['fontes']:
                o['sha256'] = regua_hash
                o['leitor_versao'] = 'regua_sintetica@1'
            if editar_plano:
                editar_plano(dados)
        c = montar(specs=specs, modo=modo, estado=estado, ocorrencias=ocorrencias, editar_plano=editar)
        dados = c.e.model_dump(mode='json')
        def corrigir_hash(x):
            if isinstance(x, dict):
                if 'arquivo_id' in x and 'sha256' in x:
                    x['sha256'] = digest
                for v in x.values():corrigir_hash(v)
            elif isinstance(x, list):
                for v in x:corrigir_hash(v)
        corrigir_hash(dados)
        if editar_entrada:
            editar_entrada(dados)
        entrada = normalizar_entrada(EntradaSimulacao.model_validate(dados))
        fontes_historico = []
        for nome, namespace, payload in [('ops', 'operacional', entrada.ocorrencias_anteriores),
                                         ('docs', 'documental', documentais)]:
            path = tmp_path / (nome + '.json')
            # Evidências documentais desta fixture também usam a fonte inventada.
            bruto = [o.model_dump(mode='json') for o in payload]
            corrigir_hash(bruto)
            path.write_bytes(bytes_canonicos(bruto)); path.chmod(0o600)
            fontes_historico.append(FonteHistorico(arquivo=FontePrivada(arquivo_id=nome,
                caminho=str(path), sha256=sha256(path.read_bytes()).hexdigest(), tamanho=path.stat().st_size,
                papel='evidencia'), namespace=namespace, produtor_id='fixture_' + nome,
                produtor_versao='1.0', estrutura='lista_ocorrencias'))
        rec = reconstruir_reconciliacao(id_='rec_integrada', condominio_id=c.p.condominio_id,
                                       ambiente='sintetico', fontes=tuple(fontes_historico))
        entrada = normalizar_entrada(EntradaSimulacao.model_validate(entrada.model_dump() | {
            'ocorrencias_anteriores': rec.ocorrencias()}))
        origem = entrada.lote.unidades[0].origem
        catalogos = tuple(CatalogoImpedimentos(id='cat_' + cat, categoria=cat,
            condominio_id=c.p.condominio_id, ocorrencias=tuple(r.para_entrada() for r in rec.registros
                if cat == ('documentos' if r.localizacao.namespace == 'documental' else 'leitura')),
            origens=(origem, *c.p.fontes) if cat == 'documentos' else (origem,)) for cat in CATEGORIAS)
        inventario = inventariar(entrada, catalogos, rec)
        ids = {o.arquivo_id for o in inventario.origens} - {regua.id, 'ops', 'docs'}
        fontes = tuple(FontePrivada(arquivo_id=i, caminho=str(primaria), sha256=digest,
            tamanho=primaria.stat().st_size, papel='inadimplencia') for i in sorted(ids)) + (
            FontePrivada(arquivo_id=regua.id, caminho=str(regua_path), sha256=regua_hash,
                tamanho=regua_path.stat().st_size, papel='requisitos'),
            *(f.arquivo for f in fontes_historico))
        candidato = CandidatoReconciliado(id='candidato_integrado', condominio_id=c.p.condominio_id,
            ambiente='sintetico', entrada=entrada, catalogos=catalogos, fontes=fontes,
            reconciliacao=rec, inventario=inventario)
        prep = PreparacaoTecnica(id='preparacao_integrada', condominio_id=c.p.condominio_id,
                                 ambiente='sintetico', candidato=candidato)
        autoridade = seguranca[0]
        armazenamento = RepositorioProcessamentosSinteticosJSON(tmp_path / 'processamentos',
            repositorio_id='ensaio_integrado', autoridade=autoridade, timeout=0.2)
        armazenamento.gravar_preparacao_tecnica(prep, credencial=gestor)
        adm = Administradora(id='adm_sintetica_a', nome='Administradora inventada')
        cond = Condominio(id=c.p.condominio_id, nome='Condomínio inventado', administradora_id=adm.id,
            codigo_na_administradora='inventado', perfil_version_id='perfil_inventado',
            formato_ids=('formato_inventado',), vinculos=({'administradora_id': adm.id, 'inicio': '2026-01-01'},))
        class Catalogo:
            administradora = adm
            condominio = cond
            def get_administradora(self, id_):
                if id_ != self.administradora.id:raise ErroAplicacao('ADMINISTRADORA_INEXISTENTE')
                return self.administradora
            def get_condominio(self, id_):
                if id_ != self.condominio.id:raise ErroAplicacao('CONDOMINIO_INEXISTENTE')
                return self.condominio
        catalogo = Catalogo()
        servico = ProcessarEnsaioSintetico(armazenamento, c.repo, VerificadorPlanosJSON(c.repo),
            VerificadorHistoricoHMAC(autoridade), AutenticadorHMACEnsaioSintetico(autoridade), catalogo, catalogo)
        pedido = PedidoProcessamentoIntegrado(**c.s.model_dump(), preparacao_id=prep.id,
            preparacao_hash=hash_modelo(prep), administradora_id=adm.id,
            regua={'arquivo_id': regua.id, 'versao': regua.versao, 'sha256': regua_hash},
            operador_id='gestor', em='2026-10-21T13:00:00Z',
            fundamento='Ensaio exclusivamente sintetico', evidencia_id='ensaio_inventado')
        return SimpleNamespace(servico=servico, pedido=pedido, armazenamento=armazenamento,
            repo=c.repo, gestor=gestor, seguranca=seguranca, plano=c.p, preparacao=prep,
            catalogo=catalogo, primaria=primaria, regua_path=regua_path,
            executar=lambda: servico.executar(pedido, credencial=gestor))
    return preparar
