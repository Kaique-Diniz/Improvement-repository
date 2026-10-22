"""Fontes e referências geradas do zero; nenhuma dependência dos documentos reais."""
from hashlib import sha256
from types import SimpleNamespace

from openpyxl import Workbook
import pytest

from tests.evaluation.conftest import preparar, seguranca, gestor, repo
from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.adapters.private_simulation_json import RepositorioSimulacoesJSON, VerificadorHistoricoHMAC
from conversor.application.billing_evaluation import normalizar_entrada
from conversor.application.private_simulation import SimuladorPrivado
from conversor.application.simulation_inventory import inventariar
from conversor.domain.billing_evaluation import EntradaSimulacao
from conversor.domain.canonical import Origem
from conversor.domain.private_simulation import AtestoCompletude, CATEGORIAS, CatalogoImpedimentos, FontePrivada, PacotePrivado
from conversor.domain.simulation_comparison import MapeamentoReferencia
from conversor.domain.template import Template


@pytest.fixture
def laboratorio(tmp_path, preparar, repo, seguranca, gestor):
    def montar(*, ocorrencias=(), lote=None, estado=None, modificar_excel=None, **kwargs):
        _, solicitacao, entrada, plano = preparar(ocorrencias=ocorrencias, lote=lote, estado=estado, **kwargs)
        primaria = tmp_path / 'documento-sintetico.txt'
        primaria.write_bytes(b'Fonte inteiramente sintetica para integridade, sem dados de pessoas.\n')
        primaria.chmod(0o600)
        digest = sha256(primaria.read_bytes()).hexdigest()
        dados = entrada.model_dump(mode='json')

        def corrigir_hash(valor):
            if isinstance(valor, dict):
                if 'arquivo_id' in valor and 'sha256' in valor:
                    valor['sha256'] = digest
                for filho in valor.values():
                    corrigir_hash(filho)
            elif isinstance(valor, list):
                for filho in valor:
                    corrigir_hash(filho)
        corrigir_hash(dados)
        entrada = normalizar_entrada(EntradaSimulacao.model_validate(dados))
        template = Template(id='template_sintetico', nome='Sintético', versao='1.0.0')
        xlsx = tmp_path / 'referencia-sintetica.xlsx'
        livro = Workbook(); aba = livro.active; aba.title = 'Dados'
        aba.append(template.cabecalhos_fisicos)
        p = entrada.lote.pessoas[0] if entrada.lote.pessoas else None
        b = entrada.lote.boletos[0]
        valores = [''] * 30
        valores[:4] = ['Condomínio sintético', 'sintetico', p.documento.valor if p and p.documento else '', p.nome if p else '']
        valores[24:30] = ['contrato_sintetico', 'produto_sintetico', 'divida_sintetica', 1, b.vencimento, float(b.composicao.total_original)]
        aba.append(valores)
        aba.cell(2, 29).number_format = 'dd/mm/yyyy'
        aba.cell(2, 3).number_format = '@'
        if modificar_excel:
            modificar_excel(aba)
        livro.save(xlsx); livro.close(); xlsx.chmod(0o600)
        referencia = FontePrivada(arquivo_id='referencia_sintetica', caminho=str(xlsx), sha256=sha256(xlsx.read_bytes()).hexdigest(),
                                 tamanho=xlsx.stat().st_size, papel='referencia')
        origem = entrada.lote.unidades[0].origem
        ref_origem = Origem(arquivo_id=referencia.arquivo_id, sha256=referencia.sha256, leitor_versao='revisao_sintetica',
                            linha=2, identificador='referencia_linha_2')
        catalogos = tuple(CatalogoImpedimentos(id='catalogo_' + categoria, categoria=categoria, condominio_id=plano.condominio_id,
            ocorrencias=entrada.ocorrencias_anteriores if categoria == 'leitura' else (),
            origens=(origem, ref_origem) if categoria == 'documentos' else (origem,)) for categoria in CATEGORIAS)
        ids = {o.arquivo_id for o in inventariar(entrada, catalogos).origens} - {referencia.arquivo_id}
        fontes = tuple(FontePrivada(arquivo_id=i, caminho=str(primaria), sha256=digest, tamanho=primaria.stat().st_size,
                                    papel='inadimplencia') for i in sorted(ids)) + (referencia,)
        atesto = AtestoCompletude(em='2026-10-21T12:00:00Z', data_ref=solicitacao.data_ref, fundamento='Conferência apenas sintética',
            evidencia_id='revisao_sintetica', inventario_conferido=True, fontes_e_paginas_conferidas=True,
            catalogos_externos_completos=True, ausencias_conferidas=True)
        pacote = PacotePrivado(id='pacote_sintetico', condominio_id=plano.condominio_id, ambiente='sintetico', entrada=entrada,
            catalogos=catalogos, fontes=fontes, inventario=inventariar(entrada, catalogos), atesto=atesto)
        autoridade = seguranca[0]
        armazenamento = RepositorioSimulacoesJSON(tmp_path / 'simulacoes', repositorio_id='testes_simulacao', ambiente='sintetico',
                                                 autoridade=autoridade, timeout=0.05)
        servico = SimuladorPrivado(armazenamento, repo, VerificadorPlanosJSON(repo), VerificadorHistoricoHMAC(autoridade))
        mapeamento = MapeamentoReferencia(referencia_id=referencia.arquivo_id, referencia_hash=referencia.sha256,
            evidencia_revisao_id='vinculo_sintetico', fundamento='Vínculo de identidades conferido em fixture',
            vinculos=({'linha': 2, 'unidade_id': b.unidade_id, 'pessoa_id': p.id if p else None, 'tipo': 'divida', 'boletos_ids': (b.id,)},))

        def executar(id_='execucao_sintetica'):
            return servico.executar(id_=id_, pacote_id=pacote.id, solicitacao=solicitacao, em='2026-10-21T13:00:00Z',
                                   fundamento='Simulação sintética', evidencia_id='evidencia_sintetica', credencial=gestor)
        return SimpleNamespace(pacote=pacote, armazenamento=armazenamento, servico=servico, executar=executar,
            gestor=gestor, repo=repo, plano=plano, solicitacao=solicitacao, autoridade=autoridade, credenciais=seguranca[1],
            mapeamento=mapeamento, template=template, primaria=primaria, xlsx=xlsx)
    return montar
