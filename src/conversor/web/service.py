"""Orquestração diagnóstica: leitores, núcleo 4.2 e XLSX; nunca autoriza operação.

Não usa repositórios de planos nem fabrica assinaturas/atestos. As decisões de
negócio confirmadas alimentam apenas as funções puras diagnósticas existentes.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Literal

from openpyxl import load_workbook
from pydantic import Field

from conversor.adapters.document_probe import SondadorLocal
from conversor.adapters.integration_identity_json import RepositorioIdentidadesIntegracaoJSON
from conversor.adapters.private_json import escrever_json
from conversor.application.cadastro import cruzar_cadastro, reavaliar_pendencias_cadastrais
from conversor.application.debt_descriptions import interpretar_lote_bbz
from conversor.application.grouped_diagnostics import projetar_cotas
from conversor.application.reading import resultado_leitura
from conversor.domain.audit_identity import ReconciliacaoOcorrencias
from conversor.domain.base import Data, Modelo
from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.billing_rules import ClausulaCobranca, bytes_canonicos, hash_modelo
from conversor.domain.canonical import Contato, Endereco, Ocorrencia, Origem, Pessoa
from conversor.domain.documents import resolver_documento
from conversor.domain.identity import chave_unidade
from conversor.domain.template import Template
from conversor.export.contract import DividaExportacao, LinhaExportacao, materializar
from conversor.export.identifiers import POLITICA_ENDERECO_CONDOMINIO, preencher_endereco, selecionar_perfil, registrar_codigo_integracao
from conversor.export.xlsx import escrever_xlsx
from conversor.export.historical_comparison import classificar_historico
from conversor.readers.contracts import FonteProtegida
from conversor.readers.habita_point_coverage import conferir_apontamentos_habita
from conversor.readers.habita_closing import conferir_fechamento_habita
from conversor.readers.operational import GRAMATICAS, RegistroLeitores, validar_assinatura_para_leitura
from conversor.readers.bbz_xlsx import LeitorBBZXLSX, identificar as identificar_bbz
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from conversor.rules.engine import avaliar_regras, resolver_candidatos

PERFIS_PATH = Path(__file__).with_name('perfis.json')
PERFIS_SAIDA_PATH = Path(__file__).with_name('perfis_saida.json')
IDENTIDADES_PATH = Path(__file__).with_name('identidades_integracao.json')
PERFIS = {p['id']: p for p in json.loads(PERFIS_PATH.read_text())}
LIMIT = 20 * 1024 * 1024


class PedidoDiagnostico(Modelo):
    data_ref: Data
    modo: Literal['A', 'B']
    condominio: Literal['auto', 'tree', 'plaza', 'nova_york'] = 'auto'


def normalizar(s):
    from conversor.domain.recognition import normalizar_assinatura
    return re.sub(r'[^a-z0-9]', '', normalizar_assinatura(s))


def reconhecer(conteudo, *, cadastro=False, repositorio_identidades=None):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id='upload')
    if sonda.tipo == 'xlsx' and not cadastro:
        codigo,nome = identificar_bbz(conteudo)
        repo=repositorio_identidades or RepositorioIdentidadesIntegracaoJSON(IDENTIDADES_PATH)
        catalogo,digest=repo.carregar()
        candidatos=catalogo.candidatos(nome,codigo)
        if len(candidatos)!=1:
            raise ErroLeitura('CONDOMINIO_DESCONHECIDO_OU_AMBIGUO')
        identidade=candidatos[0]
        matches = [p for p in PERFIS.values() if p['familia']=='bbz' and
                   (p['administradora_id'],p['condominio_id'])==(identidade.administradora_id,identidade.condominio_id)]
        if len(matches)!=1:
            raise ErroLeitura('CONDOMINIO_IDENTIFICADO_LEITOR_NAO_HABILITADO')
        if matches[0].get('codigo_easycollector')!=identidade.codigo_easycollector:
            raise ErroLeitura('CODIGO_DESTINO_DIVERGENTE_DO_PERFIL')
        perfil=dict(matches[0],identidade_integracao={
            **identidade.model_dump(mode='json'),'codigo_origem_observado':codigo,
            'catalogo_versao':catalogo.versao,'catalogo_sha256':digest,
            'origem_codigo_easycollector':catalogo.origem_codigos_destino})
        return perfil,codigo,LeitorBBZXLSX.formato_id
    if sonda.tipo != 'pdf_texto' or sonda.bloqueios or not sonda.completo:
        raise ErroLeitura('PDF_NAO_EXTRAIVEL_COM_SEGURANCA')
    texto = '\n'.join(p.texto for p in sonda.fragmentos)
    candidatos = []
    for id_ in GRAMATICAS:
        if ('cadastro' in id_) != cadastro:
            continue
        try:
            validar_assinatura_para_leitura(conteudo, id_)
            candidatos.append(id_)
        except ErroLeitura as e:
            if e.codigo == 'FORMATO_AMBIGUO':
                raise
    if len(candidatos) != 1:
        raise ErroLeitura('FORMATO_AMBIGUO' if candidatos else 'FORMATO_DESCONHECIDO')
    leitor = candidatos[0]
    familia = 'habita' if leitor.startswith('habita') else 'fl'
    pattern = (r'Condom[ií]nio:\s*(\d+)\s*-\s*([^\n]+)' if familia == 'habita' else
               rf'W{"045A" if cadastro else "002A"}\s+([^\n]*?)\s*\((\d+)\)')
    headers = list(re.finditer(pattern, texto, re.I))
    identidades = set()
    for m in headers:
        codigo, nome = (m[1], m[2]) if familia == 'habita' else (m[2], m[1])
        # Identificação fiscal do condomínio pode compartilhar a linha do título.
        # Não integra o nome nem o documento do titular da unidade.
        nome = re.split(r'\s+(?:CNPJ|CPF)\s*:', nome, maxsplit=1, flags=re.I)[0]
        limpo = normalizar(nome)
        for prefixo in ('condominioedificio', 'condominiodoedificio', 'condominio', 'edificio'):
            if limpo.startswith(prefixo):
                limpo = limpo[len(prefixo):]
                break
        matches = [p['id'] for p in PERFIS.values() if p['familia'] == familia
                   and limpo in {normalizar(a) for a in p['aliases']}]
        if len(matches) != 1:
            raise ErroLeitura('CONDOMINIO_DESCONHECIDO_OU_AMBIGUO')
        identidades.add((matches[0], codigo))
    if len(identidades) != 1:
        raise ErroLeitura('CONDOMINIO_DIVERGENTE_OU_AMBIGUO')
    perfil, codigo = identidades.pop()
    return PERFIS[perfil], codigo, leitor


def ler(conteudo, perfil, codigo, leitor, papel):
    fonte = FonteProtegida(arquivo_id=papel, sha256=sha256(conteudo).hexdigest())
    ctx = ContextoLeitura(perfil['condominio_id'], perfil['administradora_id'], leitor,
                         papel, codigo, leitor_versao=leitor + '@1')
    class Fontes:
        def ler(self, f):
            if f != fonte:
                raise ErroLeitura('FONTE_DIVERGENTE')
            return conteudo
    class Contextos:
        def resolver(self, f, **kwargs):
            return ctx
    lote = RegistroLeitores(Fontes(), Contextos()).obter(leitor, '1').ler(
        fonte, formato_id=leitor, condominio_id=perfil['condominio_id'])
    return lote, ctx


@dataclass(frozen=True)
class ConfiguracaoDiagnostica:
    """Compartilha cláusulas 4.1; não é PlanoCobranca aprovado ou ativo."""
    versao: str
    fontes: tuple
    regras: tuple
    fatos: tuple = ()


def configurar(perfil, namespace):
    fontes, regras, exclusoes = [], [], []
    config_hash = sha256(PERFIS_PATH.read_bytes()).hexdigest()
    def regra(id_, condicao, acao, prioridade, fonte_id=None, alvo='boleto'):
        fonte_id = fonte_id or id_
        if not any(f.identificador == fonte_id for f in fontes):
            fontes.append(Origem(arquivo_id='decisoes_negocio_mvp', sha256=config_hash,
                          leitor_versao='configuracao_diagnostica@1', identificador=fonte_id))
        regras.append(ClausulaCobranca(id=id_, prioridade=prioridade, alvo=alvo,
            quando=condicao, acao=acao, motivo_codigo=id_, fonte_id=fonte_id))
    for spec in perfil['exclusoes']:
        condicao = {k: v for k, v in spec.items() if k != 'id'}
        if condicao['tipo'] == 'apontamento':
            condicao['namespace'] = namespace
        exclusoes.append(condicao)
        alvo = perfil.get('escopo_exclusao', 'boleto')
        regra(spec['id'], {'tipo': 'existe_boleto', 'condicao': condicao} if alvo == 'unidade' else condicao,
              'excluir', perfil['prioridade_exclusao'], alvo=alvo)
    prazo = {'tipo': 'dias_atraso', 'operador': 'gt', 'valor': perfil['dias']}
    inclusao = {'tipo': 'todas', 'condicoes': [prazo,
        {'tipo': 'nao', 'condicao': {'tipo': 'qualquer', 'condicoes': exclusoes}}]} if exclusoes and perfil.get('escopo_exclusao') != 'unidade' else prazo
    regra(perfil['regra_prazo'], inclusao, 'incluir', perfil['prioridade_prazo'])
    regra(perfil['regra_prazo'] + '_nao_atingido',
          {'tipo': 'dias_atraso', 'operador': 'lte', 'valor': perfil['dias']},
          'excluir', perfil['prioridade_prazo'], perfil['regra_prazo'])
    return ConfiguracaoDiagnostica(perfil.get('configuracao_versao', '1.0.0'), tuple(fontes), tuple(regras))


def comparar_referencia(conteudo, lote, decisoes, mapeamento=None, identificadores=None, *, permitir_aba_historica=False, recibos_individuais=False):
    """Confronto estrito por identificador de origem ou bloco/unidade explícitos.

    Não infere torre numérica a partir de letra, não ajusta valores ou seleção.
    Sem vínculo inequívoco, a linha é não avaliável, nunca coincidência presumida.
    """
    def data_excel(valor):
        if isinstance(valor, datetime):
            return valor.date()
        if type(valor) is date:
            return valor
        if isinstance(valor, str):
            for formato in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(valor, formato).date()
                except ValueError:
                    pass
        return None
    sonda = SondadorLocal().sondar(conteudo, arquivo_id='referencia')
    if sonda.tipo != 'xlsx' or sonda.bloqueios or not sonda.completo:
        raise ErroLeitura('REFERENCIA_XLSX_INVALIDA')
    livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=False)
    try:
        if 'Dados' in livro.sheetnames:
            aba = livro['Dados']
        elif permitir_aba_historica:
            logicas=Template(id='ref',nome='ref',versao='1').colunas_logicas
            candidatas=[s for s in livro if tuple(str(v).strip()for v in next(s.iter_rows(values_only=True),())[:30])==logicas]
            if len(candidatas)!=1:raise ErroLeitura('REFERENCIA_ABA_AMBIGUA_OU_INVALIDA')
            aba=candidatas[0]
        else:
            raise ErroLeitura('REFERENCIA_SEM_ABA_DADOS')
        rows = list(aba.iter_rows(values_only=True))
        if not rows or tuple(str(x).strip() for x in rows[0][:30]) != Template(id='ref', nome='ref', versao='1').colunas_logicas:
            raise ErroLeitura('REFERENCIA_FORA_DAS_30_COLUNAS')
        resumo = Counter()
        detalhes = []
        vinculos = {v['linha_excel']: v for v in (mapeamento or [])}
        if len(vinculos) != len(mapeamento or []):
            raise ErroLeitura('MAPEAMENTO_REFERENCIA_AMBIGUO')
        for i, row in enumerate(rows[1:], 2):
            if any(v is not None and v != '' for v in row[30:]):
                resumo['anotacoes_fora_das_30_colunas'] += 1
                resumo['formatacao'] += 1
                detalhes.append({'linha_excel': i, 'categoria': 'formatacao',
                    'codigo': 'REFERENCIA_CONTEM_ANOTACAO_FORA_DO_TEMPLATE'})
            row = row[:30]
            if not any(v is not None for v in row):
                continue
            tipo = 'cadastral' if all(v is None or v == '' for v in row[24:30]) else 'divida'
            resumo[tipo] += 1
            chave = str(row[1] or '')
            complemento = str(row[6] or '')
            unidades = [u for u in lote.unidades if chave == u.chave_normalizada]
            if re.fullmatch(r'\w+/\w+', chave):
                bloco, numero = chave.split('/')
                unidades = [u for u in lote.unidades if chave_unidade(bloco, numero) == u.chave_normalizada]
            m = re.fullmatch(r'BL(\w+)-UNI(\d+)', complemento)
            if m:
                unidades = [u for u in lote.unidades if u.bloco_original == m[1]
                            and int(u.unidade_original) == int(m[2])]
            if not unidades and identificadores:
                unidades = [u for u in lote.unidades if identificadores[u.id]['estado'] == 'codificado_para_teste'
                            and (chave, complemento) == (identificadores[u.id]['cedente'], identificadores[u.id]['complemento'])]
            vinculo = vinculos.get(i)
            if vinculo:
                unidades = [u for u in lote.unidades if u.chave_normalizada == vinculo['unidade']]
            codigo = 'VINCULO_NAO_COMPROVADO'
            categoria = 'nao_avaliavel'
            if len(unidades) == 1:
                u = unidades[0]
                if tipo == 'divida':
                    boletos = [b for b in lote.boletos if b.unidade_id == u.id and
                        (b.identificador == vinculo['boleto'] if vinculo else
                         b.vencimento == data_excel(row[28]))]
                    if recibos_individuais and not vinculo and len(boletos)>1:
                        candidatos=[b for b in boletos if row[29]is not None and b.composicao.total_original==Decimal(str(row[29]))]
                        # Nunca somar recibos distintos para imitar uma linha da referência.
                        boletos=candidatos if len(candidatos)==1 else []
                    if boletos and row[29] is not None and not isinstance(row[29], str):
                        original = sum((b.composicao.total_original for b in boletos), Decimal('0.00'))
                        if original == Decimal(str(row[29])):
                            resumo['valores_coincidentes'] += 1
                            codigo = 'VALOR_ORIGINAL_COINCIDENTE'
                            categoria = 'coincidente'
                            if any(decisoes[b.id]['situacao'] == 'revisao' for b in boletos):
                                resumo['linhas_financeiras_retidas_por_bloqueio_ou_revisao'] += 1
                            if any(decisoes[b.id]['situacao_financeira'] != 'elegivel_na_simulacao' for b in boletos):
                                categoria, codigo = 'regras', 'REFERENCIA_CONTEM_COTA_NAO_ELEGIVEL_NESTA_REFERENCIA'
                        else:
                            categoria, codigo = 'dados', 'VALOR_ORIGINAL_DIVERGENTE'
                elif tipo == 'cadastral':
                    categoria, codigo = 'regras', 'CADASTRO_DEPENDE_DO_MODO_E_CONTEXTO_DA_REFERENCIA'
                pessoa = next((p for p in lote.pessoas if p.unidade_id == u.id), None)
                if pessoa:
                    if (row[3] or '').strip().casefold() != pessoa.nome.strip().casefold():
                        resumo['nomes_divergentes'] += 1
                    doc = resolver_documento(pessoa)
                    if doc.bloqueante:
                        resumo['documentos_exigem_revisao'] += 1
                    elif str(row[2] or '') != doc.valor:
                        resumo['documentos_divergentes_ou_ausentes'] += 1
            if row[2] is not None and not isinstance(row[2], str):
                resumo['documentos_com_representacao_numerica'] += 1
            resumo[categoria] += 1
            detalhes.append({'linha_excel': i, 'categoria': categoria, 'codigo': codigo})
        return {'resumo': dict(resumo), 'linhas': detalhes, 'aba_referencia': aba.title,
                'vinculo_tecnico_historico_utilizado': bool(mapeamento),
                'referencia_nao_e_gabarito_absoluto': True,
                'limite': 'Sem inferir vínculos, nomes, agrupamentos ou torres; ver linhas não avaliáveis.'}
    finally:
        livro.close()


def analisar(conteudo, pedido: PedidoDiagnostico, *, processamento_id, destino,
             cadastro=None, referencia=None, historico=None, origem='upload',
             mapeamento_referencia=None, estado_historico=None, progresso=lambda etapa: None,
             perfis_saida=None, buscar_endereco=None):
    progresso('Reconhecendo formato e condomínio')
    perfil, codigo, leitor = reconhecer(conteudo)
    if pedido.condominio != 'auto' and pedido.condominio != perfil['id']:
        raise ErroLeitura('SELECAO_DIVERGENTE_DO_CABECALHO')
    progresso('Extraindo unidades, cotas e composições')
    lote, ctx = ler(conteudo, perfil, codigo, leitor, 'inadimplencia')
    lote_extraido = lote if perfil['familia'] == 'bbz' else None
    descricoes_recibos = {}
    if perfil['familia'] == 'bbz':
        lote, descricoes_recibos = interpretar_lote_bbz(lote)
    saida_bytes = Path(perfis_saida or PERFIS_SAIDA_PATH).read_bytes()
    perfil_saida = selecionar_perfil(json.loads(saida_bytes), administradora_id=perfil['administradora_id'],
                                     condominio_id=perfil['condominio_id'])
    if perfil_saida is None and perfis_saida:
        # Perfis privados antigos não precisam ser editados para receber um novo
        # condomínio comprovado. Nunca mesclar/sobrescrever um perfil já presente.
        integrados=PERFIS_SAIDA_PATH.read_bytes()
        perfil_integrado=selecionar_perfil(json.loads(integrados),administradora_id=perfil['administradora_id'],
                                         condominio_id=perfil['condominio_id'])
        if perfil_integrado:
            perfil_saida,saida_bytes=perfil_integrado,integrados
    endereco_cadastrado = buscar_endereco(perfil['administradora_id'], perfil['condominio_id']) if buscar_endereco else None
    padrao_endereco = endereco_cadastrado or (perfil_saida.endereco_padrao if perfil_saida else None)
    origem_endereco = ('cadastro_usuario' if endereco_cadastrado else 'perfil_privado_existente' if padrao_endereco else 'nao_cadastrado')
    identificadores, codigos = {}, {}
    for u in lote.unidades:
        cedente, complemento, estado, motivo = u.chave_normalizada, u.chave_normalizada, 'provisorio', 'PERFIL_SAIDA_NAO_CONFIGURADO'
        if perfil_saida:
            try:
                cedente, complemento = perfil_saida.codificar(u, administradora_id=perfil['administradora_id'])
                estado, motivo = 'codificado_para_teste', None
            except ErroLeitura as erro:
                if erro.codigo not in ('TORRE_SEM_MAPEAMENTO_DOCUMENTAL', 'UNIDADE_SEM_CODIFICACAO_DOCUMENTAL', 'UNIDADE_FORA_DA_LARGURA_DOCUMENTADA'):
                    raise
                motivo = erro.codigo
        registrar_codigo_integracao(codigos,cedente,u.id,u.origem)
        identificadores[u.id] = {'estado': estado, 'motivo': motivo, 'cedente': cedente, 'complemento': complemento,
            'contrato': cedente, 'nome_cedente': perfil_saida.nome_cedente if perfil_saida else perfil['nome'],
            'produto': perfil_saida.produto if perfil_saida else perfil['nome'],
            'unidade_original': u.unidade_original, 'bloco_original': u.bloco_original,
            'chave_normalizada': u.chave_normalizada, 'origem_unidade': u.origem.model_dump(mode='json')}
    fontes = [{'papel': 'inadimplencia', 'sha256': sha256(conteudo).hexdigest(), 'leitor': leitor + '@1'}]
    if perfil.get('origem_regua'):
        fontes.append({'papel':'regua_requisitos_documentais','evidencia':perfil['origem_regua'],
                       'aprovacao_operacional':False})
    cad = None
    if cadastro:
        if perfil['familia']=='bbz':
            raise ErroLeitura('CADASTRO_BBZ_AINDA_NAO_SUPORTADO')
        progresso('Cruzando o cadastro e preservando conflitos')
        pc, cc, lc = reconhecer(cadastro, cadastro=True)
        if (pc['id'], cc) != (perfil['id'], codigo):
            raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
        cad, _ = ler(cadastro, pc, cc, lc, 'cadastro')
        lote = cruzar_cadastro(lote, cad)
        fontes.append({'papel': 'cadastro', 'sha256': sha256(cadastro).hexdigest(), 'leitor': lc + '@1'})
    ocorrencias = list(resultado_leitura(lote, processamento_id=processamento_id).ocorrencias)
    estado_historico = estado_historico or ('carregado' if historico else 'nao_disponivel')
    if estado_historico == 'nao_disponivel':
        ocorrencias.append(Ocorrencia(id='historico_info_' + sha256(processamento_id.encode()).hexdigest(),
            processamento_id=processamento_id, codigo='HISTORICO_TECNICO_NAO_DISPONIVEL',
            gravidade='informativo', escopo='processamento'))
    coberturas = ()
    if leitor == 'habita_composicao_real_v1':
        progresso('Conferindo o campo de apontamentos e continuidades')
        conferencia = conferir_apontamentos_habita(conteudo, contexto=ctx, lote=lote)
        coberturas = tuple(CoberturaApontamentos(boleto_id=c.boleto_id, namespace=c.namespace, origens=c.origens)
            for c in conferencia.campos if c.estado != 'inconclusivo')
        ocorrencias.extend(conferencia.ocorrencias_revisao(processamento_id=processamento_id))
    if historico:
        ocorrencias.extend(historico)
    reavaliacoes = reavaliar_pendencias_cadastrais(lote, historico, cadastro=cad)
    reavaliadas = {r['ocorrencia_id'] for r in reavaliacoes}
    fechamento = (conferir_fechamento_habita(conteudo, contexto=ctx, lote=lote, ocorrencias=ocorrencias)
        if perfil['id'] == 'tree' and leitor == 'habita_composicao_real_v1' else None)
    reconciliadas_diagnostico = set(fechamento['ocorrencias_preservadas']) if fechamento else set()
    entrada = EntradaSimulacao(lote=lote, fatos=(), ocorrencias_anteriores=(), coberturas_apontamentos=coberturas)
    config = configurar(perfil, ctx.formato_id)
    progresso('Avaliando condições e bloqueios no motor existente')
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    unidades = {u.id: u for u in lote.unidades}
    avaliacoes_unidade = {u.id: avaliar_regras(config, entrada, pedido.data_ref, u) for u in lote.unidades}
    identidades = set(unidades) | {b.id for b in lote.boletos} | {p.id for p in lote.pessoas}
    # Dispensa estritamente diagnóstica. Canônico, gravidade e histórico permanecem
    # intactos; o motor e a autorização operacional não recebem essa dispensa.
    efetivas = [o for o in ocorrencias if o.id not in reavaliadas | reconciliadas_diagnostico]
    globais = [o for o in efetivas if o.bloqueante and (o.escopo != 'registro' or o.registro_id not in identidades)]
    fora_vigencia = bool(perfil['vigente_de'] and pedido.data_ref < date.fromisoformat(perfil['vigente_de']))
    decisoes, linhas, linhas_info, previa = [], [], [], []
    rotulos_template, enderecos_template = {}, {}

    def prever(tipo, u, base, *, decisao=None, divida=None, bloqueios=(), parcela_final=None):
        # Somente visualização. Nunca encaminha linhas retidas ao escritor XLSX
        # nem contorna a validação documental do DTO de exportação.
        pessoa = base['pessoa']
        valores = None
        conflito_documental = resolver_documento(pessoa).bloqueante
        if not conflito_documental and (tipo == 'cadastral' or divida is not None):
            dto = LinhaExportacao(**base, tipo=tipo, divida=divida)
            valores = [v.isoformat() if isinstance(v, date) else format(v, '.2f') if isinstance(v, Decimal) else v
                       for v in materializar(dto).valores]
            if tipo == 'divida' and parcela_final is None:
                valores[27] = ''  # Projeção retida não recebe número final.
        previa.append({'tipo': tipo, 'unidade_id': u.id, 'bloco': u.bloco_original, 'unidade': u.unidade_original,
            'boleto_id': decisao['id'] if decisao else None, 'cota': decisao['cota'] if decisao else None,
            'bloqueada': bool(bloqueios), 'motivos': sorted(set(bloqueios)), 'valores': valores,
            'parcela_final': parcela_final, 'numeracao_pendente': tipo == 'divida' and parcela_final is None,
            'campos_retidos_por_conflito_documental': conflito_documental})
    for b in lote.boletos:
        u = unidades[b.unidade_id]
        avaliacoes = avaliar_regras(config, entrada, pedido.data_ref, u, b)
        regras_cota = avaliacoes_unidade[u.id]
        resolucao = resolver_candidatos(regras_cota, avaliacoes)
        pessoa = pessoas.get(u.id)
        documento = resolver_documento(pessoa) if pessoa else None
        problemas = [o for o in efetivas if o.bloqueante and
                     (o in globais or o.registro_id in {u.id, b.id, pessoa.id if pessoa else None})]
        motivos = [o.codigo for o in problemas]
        if fora_vigencia:
            motivos.append('REFERENCIA_ANTERIOR_A_VIGENCIA_CONFIGURADA')
        if pessoa is None or not pessoa.nome.strip():
            motivos.append('TITULAR_AUSENTE')
        if documento and documento.bloqueante:
            motivos.extend(documento.codigos)
        if b.composicao.total_original <= 0:
            motivos.append('VALOR_ORIGINAL_NAO_POSITIVO')
        status = 'revisao' if motivos or resolucao.revisao_humana else (
            'elegivel' if resolucao.situacao == 'elegivel_na_simulacao' else 'nao_elegivel')
        regras = [r for r in (*regras_cota, *avaliacoes) if r.passo.resultado == 'verdadeiro']
        veto = any(r.alvo == 'unidade' and r.acao == 'excluir' for r in regras)
        pendencias_documentais = sorted(set(
            (list(documento.codigos) if documento and documento.bloqueante else []) +
            [o.codigo for o in problemas if o.codigo in ('DOCUMENTOS_CONFLITANTES', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO')]))
        decisoes.append({'id': b.id, 'unidade_id': u.id, 'condominio': perfil['nome'],
            'bloco': u.bloco_original, 'unidade': u.unidade_original, 'cota': b.identificador,
            'boleto': b.identificador, 'cota_id': u.id, 'veto_coletivo': veto,
            'motivo_selecao': ('veto_coletivo' if veto else 'prazo_nao_atingido' if resolucao.situacao == 'excluido'
                              else 'prazo_satisfeito' if resolucao.situacao == 'elegivel_na_simulacao' else 'indeterminado'),
            'vencimento': b.vencimento.isoformat(), 'competencia': b.competencia,
            'valor': format(b.composicao.total_original, '.2f'), 'situacao': status,
            'situacao_financeira': resolucao.situacao,
            'motivos': sorted(set(motivos + [r.motivo_codigo for r in regras] +
                                  ([resolucao.motivo] if resolucao.revisao_humana else []))),
            'origens': [o.model_dump(mode='json') for o in b.origens],
            'regras_avaliadas': [r.model_dump(mode='json') for r in avaliacoes],
            'regras_da_cota': [r.regra_id for r in regras_cota],
            'componentes': [i.model_dump(mode='json') for i in b.composicao.itens],
            'documento': {'estado': list(documento.codigos) if documento else ['TITULAR_AUSENTE']},
            'contato': {'documento': ('revisao' if pendencias_documentais else
                         'disponivel' if documento.valor else 'invalido' if 'DOCUMENTO_INVALIDO' in documento.codigos else 'ausente')
                         if documento else 'ausente',
                        'telefone': bool(pessoa and pessoa.contato.telefones),
                        'email': bool(pessoa and pessoa.contato.emails)},
            'pendencias_documentais': pendencias_documentais,
            'alertas_cadastrais': sorted(set((list(documento.codigos) if documento and not documento.bloqueante else []) +
                [o.codigo for o in efetivas if not o.bloqueante and o.registro_id == u.id and o.codigo in (
                    'DIVERGENCIA_NOME_ENTRE_FONTES','MARCADOR_ADMINISTRATIVO_NO_CABECALHO','CONTATO_COMPLEMENTADO_DA_INADIMPLENCIA','TELEFONE_SEM_DDD','CONTATOS_EXCEDENTES_PRESERVADOS')])),
            'impedimentos_exportacao_operacional': sorted(set(motivos +
                (['SUBTOTAL_BLOCO_DIVERGENTE'] if reconciliadas_diagnostico else []) + ['EXPORTACAO_OPERACIONAL_INDISPONIVEL'])),
            'anomalia_global_reconciliada': bool(reconciliadas_diagnostico),
            'apto_xlsx_diagnostico': status == 'elegivel',
            'bloqueios': motivos})
    cotas = projetar_cotas(lote, decisoes, avaliacoes_unidade)
    # Uma cota/unidade vetada não afeta outras unidades; linhas são por boleto.
    for u in lote.unidades:
        ds = [d for d in decisoes if d['unidade_id'] == u.id]
        pessoa = pessoas.get(u.id)
        if pessoa is None:
            continue
        identificacao = identificadores[u.id]
        endereco_atual = pessoa.contato.endereco
        endereco_saida, estado_endereco = preencher_endereco(endereco_atual, padrao_endereco)
        conflitos_endereco, campos_substituidos, alertas_endereco = [], [], []
        if padrao_endereco:
            esperado = padrao_endereco.endereco.model_dump(exclude={'complemento'})
            atual = endereco_atual.model_dump(exclude={'complemento'})
            normal = lambda s: ' '.join(s.split()).casefold()
            conflitos_endereco = [k for k in esperado if esperado[k] and atual[k] and normal(esperado[k]) != normal(atual[k])]
            campos_substituidos = [k for k in esperado if esperado[k] != atual[k]]
            if campos_substituidos and any(atual.values()):
                alertas_endereco.append('ENDERECO_CADASTRADO_PRIORIZADO')
            for d in ds:
                d['alertas_cadastrais'] = sorted(set(d['alertas_cadastrais'] + alertas_endereco))
        enderecos_template[u.id] = {'estado': estado_endereco,
            'alertas': alertas_endereco, 'campos_conflitantes': conflitos_endereco,
            'campos_substituidos': campos_substituidos,
            'politica_aplicacao': POLITICA_ENDERECO_CONDOMINIO if padrao_endereco else 'endereco_da_fonte',
            'endereco_origem': endereco_atual.model_dump(mode='json'),
            'endereco_aplicado': endereco_saida.model_copy(update={'complemento': identificacao['complemento']}).model_dump(mode='json'),
            'evidencia': padrao_endereco.evidencia.model_dump(mode='json') if padrao_endereco else None}
        contato = Contato.model_validate(pessoa.contato.model_dump() | {
            'endereco': endereco_saida.model_dump() | {'complemento': identificacao['complemento']}})
        pessoa_saida = Pessoa.model_validate(pessoa.model_dump() | {'contato': contato})
        base = dict(processamento_id=processamento_id, registro_id=u.id,
                    nm_cedente_cedente=identificacao['nome_cedente'], cedente=identificacao['cedente'], pessoa=pessoa_saida)
        boletos_por_id = {b.id: b for b in lote.boletos if b.unidade_id == u.id}
        ordenadas = sorted(ds, key=lambda d: (boletos_por_id[d['id']].vencimento,
                                              boletos_por_id[d['id']].identificador, d['id']))
        parcela = 0
        for d in ordenadas:
            if d['situacao_financeira'] != 'elegivel_na_simulacao':
                continue
            boleto = boletos_por_id[d['id']]
            parcela_final = None
            if d['situacao'] == 'elegivel':
                parcela += 1
                parcela_final = parcela
            nome_divida = boleto.identificador
            base_rotulo = 'identificador_origem'
            if boleto.id in descricoes_recibos:
                base_rotulo = 'natureza_documental_bbz'
                nome_divida = descricoes_recibos[boleto.id].descricao
            elif perfil_saida and perfil_saida.rotulo_divida == 'vencimento_apresentacao':
                base_rotulo = 'vencimento_apresentacao'
                nome_divida = f'COTA {boleto.vencimento:%m/%Y}' + (f' - {parcela_final}' if parcela_final else '')
            elif boleto.competencia:
                base_rotulo = 'competencia_comprovada'
                ano,mes = boleto.competencia.split('-')
                nome_divida = f'COTA {mes}/{ano}' + (f' - {parcela_final}' if parcela_final else '')
            rotulos_template[boleto.id] = {'rotulo': nome_divida, 'base': base_rotulo,
                'identificador_origem': boleto.identificador, 'competencia': boleto.competencia,
                'vencimento': boleto.vencimento.isoformat(), 'origens': [o.model_dump(mode='json') for o in boleto.origens]}
            divida = DividaExportacao(contrato=identificacao['contrato'], produto=identificacao['produto'],
                nome_divida=nome_divida, parcela=parcela_final or 1, vencimento=boleto.vencimento,
                valor=boleto.composicao.total_original) if boleto.composicao.total_original > 0 else None
            bloqueios = d['bloqueios'] or (['CONDICAO_INDETERMINADA'] if d['situacao'] == 'revisao' else [])
            prever('divida', u, base, decisao=d, divida=divida, bloqueios=bloqueios,parcela_final=parcela_final)
            if d['situacao'] == 'elegivel':
                linhas.append(LinhaExportacao(**base, tipo='divida', divida=divida))
                linhas_info.append({'tipo': 'divida', 'unidade_id': u.id, 'boleto_id': boleto.id})
        if pedido.modo == 'B' and any(d['situacao_financeira'] == 'excluido' for d in ds):
            pendencias = [m for d in ds if d['situacao'] == 'revisao' for m in d['bloqueios']]
            if any(d['situacao'] == 'revisao' and not d['bloqueios'] for d in ds):
                pendencias.append('CONDICAO_INDETERMINADA')
            prever('cadastral', u, base, bloqueios=pendencias)
        if pedido.modo == 'B' and any(d['situacao'] == 'nao_elegivel' for d in ds) and not any(d['situacao'] == 'revisao' for d in ds):
            linhas.append(LinhaExportacao(**base, tipo='cadastral'))
            linhas_info.append({'tipo': 'cadastral', 'unidade_id': u.id})
    output = Path(destino)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if linhas:
        progresso('Gerando o arquivo de teste com as 30 colunas')
        escrever_xlsx(linhas, Template(id='mvp_teste', nome='Universal local', versao='1.1', espaco_final_coluna_27=False),
                      output / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx', data_ref=pedido.data_ref,
                      titulo='TESTE LOCAL DIAGNOSTICO - NAO IMPORTAR - SEM APROVACAO OPERACIONAL')
    aviso_fechamento = ('Habita/VG: o subtotal impresso diverge do VG calculado e repete o total geral. '
        'Reconciliação integral comprovada somente para XLSX DIAGNÓSTICO LOCAL. A ocorrência crítica '
        'original permanece preservada; confira o fechamento. Exportação operacional e importação no CRM proibidas.')
    manifesto = {'versao': 'manifesto_xlsx_diagnostico@1', 'processamento_id': processamento_id,
        'finalidade': 'DIAGNOSTICO_LOCAL_NAO_IMPORTAR', 'autoriza_cobranca': False,
        'permite_exportacao_operacional': False, 'data_ref': pedido.data_ref.isoformat(), 'modo': pedido.modo,
        'fontes': fontes, 'configuracao_hash': sha256(PERFIS_PATH.read_bytes()).hexdigest(),
        'perfil_saida_sha256': sha256(saida_bytes).hexdigest(),
        'fechamento_habita': fechamento, 'ocorrencias_criticas_preservadas':
            [o.model_dump(mode='json') for o in ocorrencias if o.bloqueante],
        'enderecos_template': enderecos_template,
        'endereco_condominio': {'administradora_id': perfil['administradora_id'], 'condominio_id': perfil['condominio_id'],
            'origem': origem_endereco, 'cadastrado': padrao_endereco is not None,
            'politica_aplicacao': POLITICA_ENDERECO_CONDOMINIO if padrao_endereco else 'endereco_da_fonte',
            'configuracao': padrao_endereco.model_dump(mode='json') if padrao_endereco else None},
        'aviso': aviso_fechamento if reconciliadas_diagnostico else 'Somente diagnóstico local. Não importar no CRM.',
        'arquivo': {'nome': 'TESTE_LOCAL_NAO_IMPORTAR.xlsx',
            'sha256': sha256((output / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx').read_bytes()).hexdigest(),
            'linhas_divida': sum(l.tipo == 'divida' for l in linhas),
            'linhas_cadastrais': sum(l.tipo == 'cadastral' for l in linhas),
            'colunas': 30, 'aba': 'Dados'} if linhas else None}
    if perfil.get('identidade_integracao'):
        manifesto['identidade_integracao']=perfil['identidade_integracao']
    if descricoes_recibos:
        d = next(iter(descricoes_recibos.values()))
        manifesto['politica_descricoes'] = {'id': d.politica_id, 'versao': d.politica_versao,
                                          'sha256': d.politica_sha256, 'efeito': 'somente_descricao_e_competencia_documental'}
    resumo = dict(Counter(d['situacao'] for d in decisoes))
    resumo.update(unidades=len(lote.unidades), cotas=len(lote.unidades), boletos=len(lote.boletos),
                  cotas_elegiveis_pela_regua=sum(c['situacao_financeira'] == 'elegivel' for c in cotas),
                  cotas_excluidas_por_veto=sum(c['situacao_financeira'] == 'excluida_por_veto' for c in cotas),
                  cotas_sem_boleto_no_prazo=sum(c['situacao_financeira'] == 'sem_boleto_no_prazo' for c in cotas),
                  cotas_indeterminadas=sum(c['situacao_financeira'] == 'pendente_revisao' for c in cotas),
                  cotas_excluidas_centavo=sum(any(x['regra_id'] == 'tree_centavo' for x in c['causas_veto']) for c in cotas),
                  cotas_excluidas_apontamentos=sum(any(x['regra_id'] in ('tree_apontamento_a','tree_apontamento_aj','tree_apontamento_j') for x in c['causas_veto']) for c in cotas),
                  boletos_selecionados_pela_regua=sum(d['situacao_financeira'] == 'elegivel_na_simulacao' for d in decisoes),
                  boletos_nao_selecionados_prazo=sum(d['motivo_selecao'] == 'prazo_nao_atingido' for d in decisoes),
                  boletos_excluidos_por_veto=sum(d['veto_coletivo'] for d in decisoes),
                  cotas_retidas=sum(c['retida_tecnicamente'] for c in cotas),
                  boletos_retidos=sum(d['situacao'] == 'revisao' for d in decisoes),
                  dividas_efetivamente_geradas=sum(l.tipo == 'divida' for l in linhas),
                  elegiveis_pela_regua=sum(d['situacao_financeira'] == 'elegivel_na_simulacao' for d in decisoes),
                  nao_elegiveis_pela_regua=sum(d['situacao_financeira'] == 'excluido' for d in decisoes),
                  indeterminadas_pela_regua=sum(d['situacao_financeira'] not in ('elegivel_na_simulacao', 'excluido') for d in decisoes),
                  cadastros_adicionais=sum(l.tipo == 'cadastral' for l in linhas),
                  linhas_teste=len(linhas), ocorrencias=len(ocorrencias))
    resumo['anomalias_globais_reconciliadas_diagnostico'] = int(bool(reconciliadas_diagnostico))
    resultado = {'id': processamento_id, 'condominio': perfil['nome'], 'perfil': perfil['id'],
        'administradora_id': perfil['administradora_id'], 'condominio_id': perfil['condominio_id'],
        'administradora': perfil['administradora'], 'reconhecimento': 'identificado_para_diagnostico',
        'formato_homologado_producao': False, 'data_ref': pedido.data_ref.isoformat(), 'modo': pedido.modo,
        'origem_execucao': origem, 'configuracao_hash': sha256(PERFIS_PATH.read_bytes()).hexdigest(),
        'configuracao_versao': config.versao, 'vigente_de': perfil['vigente_de'], 'vigente_ate': None,
        'aprovacao_formal_plano': False, 'autoriza_cobranca': False,
        'permite_exportacao_operacional': False, 'fontes': fontes, 'resumo': resumo,
        'registros_historicos_carregados': len(historico or ()),
        'historico_tecnico': {'estado': estado_historico, 'registros_carregados': len(historico or ()),
            'aviso': ('Sem histórico anterior: análise limitada aos documentos enviados; não comprova ausência de pendências anteriores.'
                      if estado_historico == 'nao_disponivel' else 'Histórico vinculado ou verificação de integridade registrada.')},
        'previa_template': {'colunas': list(Template(id='previa', nome='Universal', versao='1.1', espaco_final_coluna_27=False).cabecalhos_fisicos),
                           'linhas': previa, 'somente_conferencia': True, 'exportacao_operacional': False},
        'politica_cadastral': 'cadastro_por_unidade@2',
        'codificacao_template': {'perfil_id': perfil_saida.id if perfil_saida else None,
            'versao': perfil_saida.versao if perfil_saida else None, 'configuracao_sha256': sha256(saida_bytes).hexdigest(),
            'uso': 'diagnostico_nao_operacional', 'evidencia': perfil_saida.evidencia.model_dump(mode='json') if perfil_saida else None,
            'unidades': identificadores, 'pendentes': sum(i['estado'] == 'provisorio' for i in identificadores.values())},
        'reavaliacoes_historicas': reavaliacoes,
        'rotulos_template': rotulos_template, 'enderecos_template': enderecos_template,
        'endereco_condominio': manifesto['endereco_condominio'],
        'fechamento_habita': fechamento, 'manifesto_diagnostico': manifesto,
        'avisos': perfil['ressalvas'] + ['Prévia diagnóstica; não homologada para produção.',
            'Codificação de integração apenas para teste; unidades sem mapa explícito conservam identificadores provisórios. Importação no easyCollector não homologada.',
            'Competências ausentes permanecem ausentes; nenhum dado pessoal é inventado.'] +
            ([aviso_fechamento] if reconciliadas_diagnostico else []),
        'cotas': cotas, 'hierarquia': 'condominio_bloco_unidade_cota_boletos_componentes@1',
        'decisoes': decisoes, 'linhas_teste': linhas_info,
        'ocorrencias': [o.model_dump(mode='json') for o in ocorrencias],
        'arquivo_teste_disponivel': bool(linhas), 'comparacao': None}
    if referencia:
        progresso('Comparando com a referência, sem ajustar os dados')
        try:
            resultado['comparacao'] = comparar_referencia(referencia, lote, {d['id']: d for d in decisoes}, mapeamento_referencia, identificadores,
                permitir_aba_historica=perfil['familia']=='bbz',recibos_individuais=perfil['familia']=='bbz')
        except ErroLeitura as erro:
            resultado['comparacao'] = {'resumo': {'referencia_nao_avaliavel': 1}, 'linhas': [],
                'codigo': erro.codigo, 'referencia_nao_e_gabarito_absoluto': True,
                'limite': 'Não foi possível confrontar esta referência. A análise do relatório e os bloqueios permanecem preservados.'}
        resultado['fontes'].append({'papel': 'referencia', 'sha256': sha256(referencia).hexdigest()})
        if perfil['familia']=='bbz':
            resultado['comparacao']['contrato_atual']=classificar_historico(referencia,
                linhas=linhas,linhas_info=linhas_info,identificadores=identificadores,
                comparacao=resultado['comparacao'],modo=pedido.modo,descricoes=descricoes_recibos)
    if perfil.get('identidade_integracao'):
        resultado['identidade_integracao']=perfil['identidade_integracao']
    if descricoes_recibos:
        resultado['politica_descricoes'] = manifesto['politica_descricoes']
        resultado['descricoes_recibos'] = {id_: d.model_dump(mode='json') for id_, d in descricoes_recibos.items()}
    if lote_extraido is not None:
        caminho_extraido = output / 'canonico_extraido.json'
        escrever_json(caminho_extraido, lote_extraido.model_dump(mode='json'))
        manifesto['canonico_extraido'] = {'nome': caminho_extraido.name,
                                         'sha256': sha256(caminho_extraido.read_bytes()).hexdigest()}
    escrever_json(output / 'manifesto_diagnostico.json', manifesto)
    escrever_json(output / 'auditoria.json', resultado)
    escrever_json(output / 'canonico.json', lote.model_dump(mode='json'))
    return resultado
