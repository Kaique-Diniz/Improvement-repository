"""Orquestração diagnóstica: leitores, núcleo 4.2 e XLSX; nunca autoriza operação.

Não usa repositórios de planos nem fabrica assinaturas/atestos. As decisões de
negócio confirmadas alimentam apenas as funções puras diagnósticas existentes.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date
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
from conversor.adapters.private_json import escrever_json
from conversor.application.cadastro import cruzar_cadastro, reavaliar_pendencias_cadastrais
from conversor.application.reading import resultado_leitura
from conversor.domain.audit_identity import ReconciliacaoOcorrencias
from conversor.domain.base import Data, Modelo
from conversor.domain.billing_evaluation import CoberturaApontamentos, EntradaSimulacao
from conversor.domain.billing_rules import ClausulaCobranca, bytes_canonicos, hash_modelo
from conversor.domain.canonical import Contato, Endereco, Origem, Pessoa
from conversor.domain.documents import resolver_documento
from conversor.domain.identity import chave_unidade
from conversor.domain.template import Template
from conversor.export.contract import DividaExportacao, LinhaExportacao
from conversor.export.xlsx import escrever_xlsx
from conversor.readers.contracts import FonteProtegida
from conversor.readers.habita_point_coverage import conferir_apontamentos_habita
from conversor.readers.operational import GRAMATICAS, RegistroLeitores, validar_assinatura_para_leitura
from conversor.readers.text_support import ContextoLeitura, ErroLeitura
from conversor.rules.engine import avaliar_regras, resolver_candidatos

PERFIS_PATH = Path(__file__).with_name('perfis.json')
PERFIS = {p['id']: p for p in json.loads(PERFIS_PATH.read_text())}
LIMIT = 20 * 1024 * 1024


class PedidoDiagnostico(Modelo):
    data_ref: Data
    modo: Literal['A', 'B']
    condominio: Literal['auto', 'tree', 'plaza'] = 'auto'


def normalizar(s):
    from conversor.domain.recognition import normalizar_assinatura
    return re.sub(r'[^a-z0-9]', '', normalizar_assinatura(s))


def reconhecer(conteudo, *, cadastro=False):
    sonda = SondadorLocal().sondar(conteudo, arquivo_id='upload')
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
    def regra(id_, condicao, acao, prioridade, fonte_id=None):
        fonte_id = fonte_id or id_
        if not any(f.identificador == fonte_id for f in fontes):
            fontes.append(Origem(arquivo_id='decisoes_negocio_mvp', sha256=config_hash,
                          leitor_versao='configuracao_diagnostica@1', identificador=fonte_id))
        regras.append(ClausulaCobranca(id=id_, prioridade=prioridade, alvo='boleto',
            quando=condicao, acao=acao, motivo_codigo=id_, fonte_id=fonte_id))
    for spec in perfil['exclusoes']:
        condicao = {k: v for k, v in spec.items() if k != 'id'}
        if condicao['tipo'] == 'apontamento':
            condicao['namespace'] = namespace
        exclusoes.append(condicao)
        regra(spec['id'], condicao, 'excluir', perfil['prioridade_exclusao'])
    prazo = {'tipo': 'dias_atraso', 'operador': 'gt', 'valor': perfil['dias']}
    inclusao = {'tipo': 'todas', 'condicoes': [prazo,
        {'tipo': 'nao', 'condicao': {'tipo': 'qualquer', 'condicoes': exclusoes}}]} if exclusoes else prazo
    regra(perfil['regra_prazo'], inclusao, 'incluir', perfil['prioridade_prazo'])
    regra(perfil['regra_prazo'] + '_nao_atingido',
          {'tipo': 'dias_atraso', 'operador': 'lte', 'valor': perfil['dias']},
          'excluir', perfil['prioridade_prazo'], perfil['regra_prazo'])
    return ConfiguracaoDiagnostica('1.0.0', tuple(fontes), tuple(regras))


def comparar_referencia(conteudo, lote, decisoes, mapeamento=None):
    """Confronto estrito por identificador de origem ou bloco/unidade explícitos.

    Não infere torre numérica a partir de letra, não ajusta valores ou seleção.
    Sem vínculo inequívoco, a linha é não avaliável, nunca coincidência presumida.
    """
    sonda = SondadorLocal().sondar(conteudo, arquivo_id='referencia')
    if sonda.tipo != 'xlsx' or sonda.bloqueios or not sonda.completo:
        raise ErroLeitura('REFERENCIA_XLSX_INVALIDA')
    livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=False)
    try:
        if 'Dados' not in livro.sheetnames:
            raise ErroLeitura('REFERENCIA_SEM_ABA_DADOS')
        rows = list(livro['Dados'].iter_rows(values_only=True))
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
                         hasattr(row[28], 'date') and b.vencimento == row[28].date())]
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
        return {'resumo': dict(resumo), 'linhas': detalhes,
                'vinculo_tecnico_historico_utilizado': bool(mapeamento),
                'referencia_nao_e_gabarito_absoluto': True,
                'limite': 'Sem inferir vínculos, nomes, agrupamentos ou torres; ver linhas não avaliáveis.'}
    finally:
        livro.close()


def analisar(conteudo, pedido: PedidoDiagnostico, *, processamento_id, destino,
             cadastro=None, referencia=None, historico=None, origem='upload',
             mapeamento_referencia=None, progresso=lambda etapa: None):
    progresso('Reconhecendo formato e condomínio')
    perfil, codigo, leitor = reconhecer(conteudo)
    if pedido.condominio != 'auto' and pedido.condominio != perfil['id']:
        raise ErroLeitura('SELECAO_DIVERGENTE_DO_CABECALHO')
    progresso('Extraindo unidades, cotas e composições')
    lote, ctx = ler(conteudo, perfil, codigo, leitor, 'inadimplencia')
    fontes = [{'papel': 'inadimplencia', 'sha256': sha256(conteudo).hexdigest(), 'leitor': leitor + '@1'}]
    cad = None
    if cadastro:
        progresso('Cruzando o cadastro e preservando conflitos')
        pc, cc, lc = reconhecer(cadastro, cadastro=True)
        if (pc['id'], cc) != (perfil['id'], codigo):
            raise ErroLeitura('CADASTRO_DE_OUTRO_CONDOMINIO')
        cad, _ = ler(cadastro, pc, cc, lc, 'cadastro')
        lote = cruzar_cadastro(lote, cad)
        fontes.append({'papel': 'cadastro', 'sha256': sha256(cadastro).hexdigest(), 'leitor': lc + '@1'})
    ocorrencias = list(resultado_leitura(lote, processamento_id=processamento_id).ocorrencias)
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
    entrada = EntradaSimulacao(lote=lote, fatos=(), ocorrencias_anteriores=(), coberturas_apontamentos=coberturas)
    config = configurar(perfil, ctx.formato_id)
    progresso('Avaliando condições e bloqueios no motor existente')
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    unidades = {u.id: u for u in lote.unidades}
    identidades = set(unidades) | {b.id for b in lote.boletos} | {p.id for p in lote.pessoas}
    efetivas = [o for o in ocorrencias if o.id not in reavaliadas]
    globais = [o for o in efetivas if o.bloqueante and (o.escopo != 'registro' or o.registro_id not in identidades)]
    fora_vigencia = pedido.data_ref < date.fromisoformat(perfil['vigente_de'])
    decisoes, linhas, linhas_info = [], [], []
    for b in lote.boletos:
        u = unidades[b.unidade_id]
        avaliacoes = avaliar_regras(config, entrada, pedido.data_ref, u, b)
        resolucao = resolver_candidatos((), avaliacoes)
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
        regras = [r for r in avaliacoes if r.passo.resultado == 'verdadeiro']
        pendencias_documentais = sorted(set(
            (list(documento.codigos) if documento and documento.bloqueante else []) +
            [o.codigo for o in problemas if o.codigo in ('DOCUMENTOS_CONFLITANTES', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO')]))
        decisoes.append({'id': b.id, 'unidade_id': u.id, 'condominio': perfil['nome'],
            'bloco': u.bloco_original, 'unidade': u.unidade_original, 'cota': b.identificador,
            'vencimento': b.vencimento.isoformat(), 'competencia': b.competencia,
            'valor': format(b.composicao.total_original, '.2f'), 'situacao': status,
            'situacao_financeira': resolucao.situacao,
            'motivos': sorted(set(motivos + [r.motivo_codigo for r in regras] +
                                  ([resolucao.motivo] if resolucao.revisao_humana else []))),
            'origens': [o.model_dump(mode='json') for o in b.origens],
            'regras_avaliadas': [r.model_dump(mode='json') for r in avaliacoes],
            'componentes': [i.model_dump(mode='json') for i in b.composicao.itens],
            'documento': {'estado': list(documento.codigos) if documento else ['TITULAR_AUSENTE']},
            'contato': {'documento': ('revisao' if pendencias_documentais else
                         'disponivel' if documento.valor else 'invalido' if 'DOCUMENTO_INVALIDO' in documento.codigos else 'ausente')
                         if documento else 'ausente',
                        'telefone': bool(pessoa and pessoa.contato.telefones),
                        'email': bool(pessoa and pessoa.contato.emails)},
            'pendencias_documentais': pendencias_documentais,
            'alertas_cadastrais': list(documento.codigos) if documento and not documento.bloqueante else [],
            'impedimentos_exportacao_operacional': sorted(set(motivos + ['EXPORTACAO_OPERACIONAL_INDISPONIVEL'])),
            'bloqueios': motivos})
    # Projeção A/B por unidade: nenhuma cota excluída derruba as outras.
    for u in lote.unidades:
        ds = [d for d in decisoes if d['unidade_id'] == u.id]
        pessoa = pessoas.get(u.id)
        if pessoa is None:
            continue
        contato = Contato.model_validate(pessoa.contato.model_dump() | {
            'endereco': pessoa.contato.endereco.model_dump() | {'complemento': u.chave_normalizada}})
        pessoa_saida = Pessoa.model_validate(pessoa.model_dump() | {'contato': contato})
        base = dict(processamento_id=processamento_id, registro_id=u.id,
                    nm_cedente_cedente=perfil['nome'], cedente=u.chave_normalizada, pessoa=pessoa_saida)
        for d in ds:
            if d['situacao'] != 'elegivel':
                continue
            boleto = next(b for b in lote.boletos if b.id == d['id'])
            divida = DividaExportacao(contrato=u.chave_normalizada, produto=perfil['nome'],
                nome_divida=boleto.identificador, parcela=1, vencimento=boleto.vencimento,
                valor=boleto.composicao.total_original)
            linhas.append(LinhaExportacao(**base, tipo='divida', divida=divida))
            linhas_info.append({'tipo': 'divida', 'unidade_id': u.id, 'boleto_id': boleto.id})
        if pedido.modo == 'B' and any(d['situacao'] == 'nao_elegivel' for d in ds) and not any(d['situacao'] == 'revisao' for d in ds):
            linhas.append(LinhaExportacao(**base, tipo='cadastral'))
            linhas_info.append({'tipo': 'cadastral', 'unidade_id': u.id})
    output = Path(destino)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if linhas:
        progresso('Gerando o arquivo de teste com as 30 colunas')
        escrever_xlsx(linhas, Template(id='mvp_teste', nome='Universal local', versao='1.0'),
                      output / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx', data_ref=pedido.data_ref,
                      titulo='TESTE LOCAL DIAGNOSTICO - NAO IMPORTAR - SEM APROVACAO OPERACIONAL')
    resumo = dict(Counter(d['situacao'] for d in decisoes))
    resumo.update(unidades=len(lote.unidades), cotas=len(lote.boletos),
                  cadastros_adicionais=sum(l.tipo == 'cadastral' for l in linhas),
                  linhas_teste=len(linhas), ocorrencias=len(ocorrencias))
    resultado = {'id': processamento_id, 'condominio': perfil['nome'], 'perfil': perfil['id'],
        'administradora': perfil['administradora'], 'reconhecimento': 'identificado_para_diagnostico',
        'formato_homologado_producao': False, 'data_ref': pedido.data_ref.isoformat(), 'modo': pedido.modo,
        'origem_execucao': origem, 'configuracao_hash': sha256(PERFIS_PATH.read_bytes()).hexdigest(),
        'configuracao_versao': config.versao, 'vigente_de': perfil['vigente_de'], 'vigente_ate': None,
        'aprovacao_formal_plano': False, 'autoriza_cobranca': False,
        'permite_exportacao_operacional': False, 'fontes': fontes, 'resumo': resumo,
        'registros_historicos_carregados': len(historico or ()),
        'politica_cadastral': 'cadastro_por_unidade@1',
        'reavaliacoes_historicas': reavaliacoes,
        'avisos': perfil['ressalvas'] + ['Prévia diagnóstica; não homologada para produção.',
            'Arquivo de teste usa identificadores de origem para cedente/contrato/dívida; codificação operacional do easyCollector ainda não homologada.',
            'Competências ausentes permanecem ausentes; nenhum dado pessoal é inventado.'],
        'decisoes': decisoes, 'linhas_teste': linhas_info,
        'ocorrencias': [o.model_dump(mode='json') for o in ocorrencias],
        'arquivo_teste_disponivel': bool(linhas), 'comparacao': None}
    if referencia:
        progresso('Comparando com a referência, sem ajustar os dados')
        try:
            resultado['comparacao'] = comparar_referencia(referencia, lote, {d['id']: d for d in decisoes}, mapeamento_referencia)
        except ErroLeitura as erro:
            resultado['comparacao'] = {'resumo': {'referencia_nao_avaliavel': 1}, 'linhas': [],
                'codigo': erro.codigo, 'referencia_nao_e_gabarito_absoluto': True,
                'limite': 'Não foi possível confrontar esta referência. A análise do PDF e os bloqueios permanecem preservados.'}
        resultado['fontes'].append({'papel': 'referencia', 'sha256': sha256(referencia).hexdigest()})
    escrever_json(output / 'auditoria.json', resultado)
    escrever_json(output / 'canonico.json', lote.model_dump(mode='json'))
    return resultado
