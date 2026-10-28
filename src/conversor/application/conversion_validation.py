"""Conferência observacional do XLSX, do planejamento e dos canônicos do leitor.

Não executa regras, não altera arquivos nem atesta fidelidade integral à fonte.
Nenhum valor de célula ou dado pessoal entra no laudo agregado.
"""
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring
from openpyxl import load_workbook

from conversor.domain.template import COLUNAS

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000


def _dinheiro(valor):
    if type(valor) not in (int, float, Decimal):
        return None
    try:
        d = Decimal(str(valor))
        return d if d.is_finite() and d == d.quantize(Decimal('0.01')) else None
    except (InvalidOperation, ValueError):
        return None


def _data(valor):
    if type(valor) is datetime:
        return valor.date() if valor.time().isoformat() == '00:00:00' else None
    return valor if type(valor) is date else None


def _igual(obtido, esperado):
    if isinstance(esperado, Decimal):
        return _dinheiro(obtido) == esperado
    if type(esperado) is date:
        return _data(obtido) == esperado
    if type(esperado) is int:
        return type(obtido) is int and obtido == esperado
    if isinstance(esperado, str):
        return ('' if obtido is None else obtido) == esperado and (obtido is None or isinstance(obtido, str))
    return obtido == esperado


def _chave_saida(cedente, complemento):
    return tuple('' if v is None else v for v in (cedente, complemento))


def descrever_motivo(codigo):
    textos = {
        'DESTINO_TORRE_NAO_COMPROVADO': 'A unidade não tem pertencimento comprovado ao condomínio selecionado.',
        'DESTINO_PERSISTENTE_CONFLITANTE': 'O destino documental diverge do condomínio selecionado.',
        'IDENTIDADE_FINANCEIRA_ALTERADA': 'A identidade financeira mudou e precisa de nova conferência documental.',
        'PERFIL_DE_IDENTIFICACAO_ALTERADO': 'O perfil de identificação mudou; é necessário revisar o vínculo.',
        'SUBTOTAL_BLOCO_DIVERGENTE': 'O fechamento financeiro exige conferência; a ocorrência original foi preservada.',
        'BBZ_CONFLITO_DOCUMENTAL_PERSISTENTE': 'CPF/CNPJ e contatos permanecem retidos por conflito documental.',
        'BBZ_DOCUMENTO_HISTORICO_CONFLITANTE_ASSOCIACAO_RETIDA': 'Documentos divergentes entre fontes; CPF/CNPJ e contatos retidos.',
        'CONDICAO_INDETERMINADA': 'Faltam evidências suficientes para concluir a condição.',
        'VINCULOS_ALTERADOS_REPROCESSAR': 'O cadastro de vínculos mudou. Faça novo processamento.',
        'PRAZO_NAO_ATINGIDO': 'O boleto não atende ao prazo financeiro configurado.',
        'VETO_COLETIVO': 'Uma exclusão da cota impede a inclusão dos seus boletos.',
        'VALOR_ORIGINAL_ZERO': 'O valor original é zero; o registro permanece na auditoria, sem dívida no Excel.',
    }
    return textos.get(codigo, 'O processamento identificou uma restrição. Confira a decisão e as referências documentais.')


def _origem(o):
    return {k: getattr(o, k) for k in ('arquivo_id', 'sha256', 'leitor_versao', 'pagina', 'linha', 'identificador')}


def validar_conversao(path: Path, *, registros, linhas_info, decisoes,
                      escopo_destino=None, unidades_contato_retido=(),
                      lote_origem=None, contexto=None, fontes=(), fechamento=None):
    """Distingue observação dos bytes, consistência interna e limites da evidência.

    lote_origem é o canônico extraído antes do enriquecimento. Não equivale a
    extração independente do documento. Não recebe nomes ou contatos no laudo.
    """
    path = Path(path)
    registros = tuple(tuple(r) for r in registros)
    infos = tuple(linhas_info)
    decisoes = tuple(decisoes)
    contexto = contexto or {}
    retidas = set(unidades_contato_retido)
    erros, avisos, detalhes = [], [], []
    contagens_erros = Counter()
    categorias_erros = set()

    def erro(codigo, descricao, categoria='estrutura', linha=None, coluna=None, meta=None):
        contagens_erros[codigo] += 1
        categorias_erros.add(categoria)
        item = dict(codigo=codigo, descricao=descricao, categoria=categoria)
        if linha is not None:item['linha'] = linha
        if coluna is not None:item['coluna'] = coluna
        if meta:
            item.update({k:meta[k] for k in ('unidade_id','boleto_id') if meta.get(k)})
        if len(erros) < 100:erros.append(item)

    def aviso(codigo, descricao, quantidade):
        if quantidade:avisos.append(dict(codigo=codigo, descricao=descricao, quantidade=quantidade))

    ds = {d['id']:d for d in decisoes}
    if len(ds) != len(decisoes):erro('DECISAO_DUPLICADA', 'Há decisões duplicadas para o mesmo boleto.', 'elegibilidade')
    if len(infos) != len(registros):erro('METADADOS_DIVERGENTES', 'O rastreio não cobre todas as linhas previstas.', 'rastreabilidade')
    if any(not m.get('unidade_id') for m in infos):
        erro('UNIDADE_DE_RASTREIO_AUSENTE', 'Há linha sem identificador da unidade de origem.', 'rastreabilidade')
    if any(len(r) != 30 for r in registros):erro('PLANEJAMENTO_FORA_DO_CONTRATO', 'Uma linha prevista não tem 30 campos.', 'planejamento')
    dividas = [m for m in infos if m.get('tipo') == 'divida']
    cadastros = [m for m in infos if m.get('tipo') == 'cadastral']
    selecionados = Counter(d['id'] for d in decisoes if d.get('situacao') == 'elegivel')
    exportados = Counter(m.get('boleto_id') for m in dividas)
    if selecionados != exportados or any(n != 1 for n in exportados.values()):
        erro('BOLETOS_DIVERGENTES', 'As dívidas previstas não correspondem uma a uma às decisões elegíveis.', 'elegibilidade')
    if any(m.get('tipo') not in ('divida','cadastral') for m in infos):
        erro('TIPO_LINHA_INESPERADO', 'Há um tipo de linha não reconhecido.', 'rastreabilidade')
    if any(n > 1 for n in Counter(m.get('unidade_id') for m in cadastros).values()):
        erro('CADASTRO_DUPLICADO', 'Há mais de um cadastro adicional para a mesma unidade.', 'elegibilidade')
    for meta in dividas:
        d = ds.get(meta.get('boleto_id'), {})
        if (d.get('unidade_id', meta.get('unidade_id')) != meta.get('unidade_id') or d.get('bloqueios') or
                d.get('situacao_financeira', 'elegivel_na_simulacao') != 'elegivel_na_simulacao'):
            erro('DIVIDA_INELEGIVEL_PLANEJADA', 'Há uma dívida sem decisão financeira apta ou com bloqueio.', 'elegibilidade', meta=meta)
    for meta in cadastros:
        locais = [d for d in decisoes if d.get('unidade_id') == meta.get('unidade_id')]
        if contexto.get('modo') == 'A' or (contexto.get('modo') == 'B' and
                (not any(d.get('situacao') == 'nao_elegivel' for d in locais) or any(d.get('situacao') == 'revisao' for d in locais))):
            erro('CADASTRO_SEM_FUNDAMENTO', 'O cadastro adicional não atende às decisões do modo A/B.', 'elegibilidade', meta=meta)

    permitidas = None
    if escopo_destino is not None:
        permitidas = set(escopo_destino.permitidas)
        if any(m.get('unidade_id') not in permitidas for m in infos):
            erro('UNIDADE_FORA_DO_ESCOPO', 'Há linha prevista para unidade sem pertencimento comprovado.', 'vinculos')
        if getattr(escopo_destino, 'erro_cadastro', None) and infos:
            erro('INTEGRIDADE_VINCULOS_INDISPONIVEL', 'Não há comprovação íntegra do cadastro de vínculos.', 'vinculos')

    boletos = {b.id:b for b in lote_origem.boletos} if lote_origem is not None else {}
    unidades = {u.id:u for u in lote_origem.unidades} if lote_origem is not None else {}
    if lote_origem is not None and set(ds) != set(boletos):
        erro('INVENTARIO_DECISOES_DIVERGENTE', 'As decisões não cobrem exatamente os boletos canônicos.', 'rastreabilidade')
    fontes_hashes = {f.get('sha256') for f in fontes}
    fontes_canonic = all(o.sha256 in fontes_hashes for b in boletos.values() for o in b.origens) if fontes else False
    if lote_origem is not None and fontes and not fontes_canonic:
        erro('ORIGEM_CANONICA_NAO_VINCULADA', 'Uma origem canônica não corresponde às fontes recebidas.', 'rastreabilidade')
    if any((contexto.get('condominio_id') and u.condominio_id != contexto['condominio_id']) or
           (contexto.get('administradora_id') and u.administradora_id != contexto['administradora_id']) for u in unidades.values()):
        erro('CONDOMINIO_CANONICO_DIVERGENTE', 'O inventário canônico pertence a outro condomínio ou administradora.', 'vinculos')
    total_planejado = Decimal('0.00')
    total_canonico = sum((b.composicao.total_original for id_,b in boletos.items() if id_ in selecionados),Decimal('0.00'))
    mapa_unidades = defaultdict(set)
    for i, (r, meta) in enumerate(zip(registros, infos), 2):
        if len(r) != 30:continue
        mapa_unidades[_chave_saida(r[1],r[6])].add(meta.get('unidade_id'))
        if meta.get('tipo') == 'divida':
            valor = _dinheiro(r[29])
            if valor is None or valor <= 0:erro('VALOR_PLANEJADO_INVALIDO', 'O valor planejado não é monetário positivo com centavos exatos.', 'planejamento', i, 30, meta)
            else:total_planejado += valor
            if lote_origem is not None:
                b = boletos.get(meta.get('boleto_id'))
                if b is None or b.unidade_id != meta.get('unidade_id') or b.unidade_id not in unidades:
                    erro('BOLETO_ORIGEM_DIVERGENTE', 'O boleto não corresponde à unidade canônica indicada.', 'rastreabilidade', i, meta=meta)
                else:
                    if r[29] != b.composicao.total_original:
                        erro('VALOR_DIVERGENTE_CANONICO', 'O valor planejado diverge do original canônico do boleto.', 'dados_leitor', i, 30, meta)
                    if r[28] != b.vencimento:
                        erro('VENCIMENTO_DIVERGENTE_CANONICO', 'O vencimento planejado diverge do boleto canônico.', 'dados_leitor', i, 29, meta)
        if lote_origem is not None and meta.get('unidade_id') not in unidades:
            erro('UNIDADE_ORIGEM_AUSENTE', 'A unidade da linha não consta no inventário canônico.', 'rastreabilidade', i, meta=meta)
    if any(len(ids) != 1 for ids in mapa_unidades.values()):
        erro('IDENTIFICADORES_AMBIGUOS', 'Os identificadores de saída não distinguem as unidades.', 'rastreabilidade')

    total_obtido = Decimal('0.00')
    lidas = dividas_lidas = cadastros_lidos = retidas_lidas = neutras = 0
    unidades_lidas = set()
    digest = None
    arquivo_conferido = False
    try:
        if path.exists():
            if (path.is_symlink() or any(p.is_symlink() for p in path.parents) or path.stat().st_nlink != 1 or
                    any(p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in (path,*path.parents))):
                raise ValueError('ARQUIVO_NAO_REGULAR')
            with path.open('rb') as f:raw = f.read(MAX_BYTES+1)
            digest = sha256(raw).hexdigest()
            if not registros:erro('ARQUIVO_INESPERADO', 'Há XLSX embora nenhuma linha estivesse prevista.')
            if len(raw) > MAX_BYTES:raise ValueError('LIMITE_ARQUIVO')
            with ZipFile(BytesIO(raw)) as z:
                nomes = z.namelist()
                if len(nomes) != len(set(nomes)) or len(nomes) > 1000 or sum(i.file_size for i in z.infolist()) > 100*1024*1024:
                    raise ValueError('ZIP_INVALIDO')
                if any(any(t in n.lower() for t in ('vbaproject','externallinks/','embeddings/','activex/',
                        'macrosheets/','dialogsheets/','connections.xml','querytables/')) for n in nomes):
                    erro('CONTEUDO_EXECUTAVEL', 'O XLSX contém macro, objeto incorporado ou vínculo externo.', 'seguranca')
                for n in nomes:
                    if n.endswith(('.xml','.rels')):
                        xml = fromstring(z.read(n), forbid_dtd=True)
                        if n.endswith('.rels') and any(e.get('TargetMode') == 'External' for e in xml):
                            erro('VINCULO_EXTERNO', 'O XLSX contém relacionamento externo.', 'seguranca')
                if z.testzip() is not None:raise ValueError('ZIP_CORROMPIDO')
            w = load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
            try:
                if w.sheetnames != ['Dados']:erro('ABAS_DIVERGENTES', 'O XLSX deve conter somente a aba Dados.')
                if 'Dados' in w.sheetnames:
                    sh = w['Dados']
                    sh.reset_dimensions()  # Dimensões declaradas não podem esconder células ou linhas.
                    iterator = sh.iter_rows()
                    header = next(iterator, ())
                    if len(header) != 30:erro('QUANTIDADE_COLUNAS_INVALIDA', 'O XLSX não possui exatamente 30 colunas.')
                    if tuple(c.value for c in header) != COLUNAS:erro('CABECALHO_DIVERGENTE', 'Os nomes ou a ordem das 30 colunas divergiram.')
                    for n, row in enumerate(iterator, 2):
                        if n > MAX_ROWS+1:raise ValueError('LIMITE_LINHAS')
                        lidas += 1
                        meta = infos[n-2] if n-2 < len(infos) else {}
                        if len(row) > 30:erro('COLUNAS_NA_LINHA', 'Linha com mais de 30 colunas.', linha=n)
                        cells = tuple(row[:30]) + (None,)*max(0,30-len(row))
                        valores = tuple(c.value if c else None for c in cells)
                        tipo = 'cadastral' if all(v in (None,'') for v in valores[24:30]) else 'divida'
                        if tipo == 'cadastral':cadastros_lidos += 1
                        else:
                            dividas_lidas += 1
                            retidas_lidas += meta.get('unidade_id') in retidas
                            neutras += isinstance(valores[26],str) and valores[26].startswith('RECIBO ')
                        ids = mapa_unidades.get(_chave_saida(valores[1],valores[6]),set())
                        if len(ids) == 1:unidades_lidas.update(ids)
                        else:erro('LINHA_SEM_RASTREIO', 'Os identificadores escritos não têm unidade de origem inequívoca.', 'rastreabilidade', n)
                        if n-2 >= len(registros):erro('LINHA_EXCEDENTE', 'Há linha adicional não justificada no XLSX.', linha=n)
                        else:
                            esperado = registros[n-2]
                            for col, (c,v) in enumerate(zip(cells,valores), 1):
                                if col <= len(esperado) and not _igual(v,esperado[col-1]):
                                    erro('CELULA_DIVERGENTE', 'Valor ou tipo diverge da linha planejada.', 'planejamento', n, col, meta)
                            if meta.get('tipo') == 'cadastral' and tipo != 'cadastral':
                                erro('FINANCEIRO_EM_CADASTRO', 'Cadastro adicional contém campos financeiros.', 'elegibilidade', n, meta=meta)
                        for col,c in enumerate(cells,1):
                            if c and c.data_type == 'f':erro('FORMULA_NO_XLSX', 'Fórmula detectada no arquivo diagnóstico.', 'seguranca', n, col, meta)
                            if c and c.value not in (None,'') and col not in (28,29,30) and c.data_type != 's':
                                erro('IDENTIFICADOR_SEM_TEXTO', 'Campo cadastral ou identificador não está preservado como texto.', 'estrutura', n, col, meta)
                        if tipo == 'divida':
                            valor = _dinheiro(valores[29])
                            if valor is None or valor <= 0:erro('VALOR_DIVIDA_INVALIDO', 'Valor financeiro deve ser positivo e ter centavos exatos.', 'dados_leitor', n, 30, meta)
                            else:total_obtido += valor
                            if _data(valores[28]) is None:erro('VENCIMENTO_INVALIDO', 'Vencimento não é uma data Excel válida sem horário.', 'dados_leitor', n, 29, meta)
                            if type(valores[27]) is not int or valores[27] < 1:erro('PARCELA_INVALIDA', 'Parcela não é um inteiro positivo.', 'estrutura', n, 28, meta)
                            b = boletos.get(meta.get('boleto_id'))
                            if b:
                                if valor != b.composicao.total_original:erro('VALOR_DIVERGENTE_CANONICO', 'O valor escrito diverge do boleto canônico.', 'dados_leitor', n, 30, meta)
                                if _data(valores[28]) != b.vencimento:erro('VENCIMENTO_DIVERGENTE_CANONICO', 'O vencimento escrito diverge do boleto canônico.', 'dados_leitor', n, 29, meta)
                        if meta.get('unidade_id') in retidas and any(valores[c] not in (None,'') for c in (2,*range(11,24))):
                            erro('CONTATO_RETIDO_EXPOSTO', 'Documento ou contato protegido reapareceu no XLSX.', 'retencoes', n, meta=meta)
                        if valores[2] not in (None,'') and (not cells[2] or cells[2].data_type != 's' or cells[2].number_format != '@'):
                            erro('DOCUMENTO_SEM_TEXTO', 'CPF/CNPJ deve ser texto com formato textual.', 'estrutura', n, 3, meta)
                    arquivo_conferido = True
            finally:w.close()
        elif registros:erro('ARQUIVO_AUSENTE', 'O XLSX previsto não está disponível para conferência.')
    except Exception:
        # Fronteira de parsing: exceções de XML/XLSX podem conter dados privados.
        erro('XLSX_ILEGIVEL', 'Não foi possível conferir integralmente o XLSX; download bloqueado.')
    if lidas != len(registros) and registros:erro('TOTAL_LINHAS_DIVERGENTE', 'O total escrito difere do previsto.')
    if total_obtido != total_planejado and registros:erro('SOMA_FINANCEIRA_DIVERGENTE', 'A soma escrita diverge da soma prevista para as dívidas selecionadas.', 'dados_leitor')

    pendentes = Counter(c for d in decisoes if d.get('situacao') == 'revisao' for c in (d.get('bloqueios') or ['CONDICAO_INDETERMINADA']))
    aviso('BOLETOS_EM_REVISAO', 'Boletos retidos permanecem fora do XLSX.', sum(d.get('situacao') == 'revisao' for d in decisoes))
    aviso('CONTATOS_DOCUMENTAIS_RETIDOS', 'Unidades com CPF/CNPJ e contatos protegidos por conflito documental.', len(retidas))
    aviso('ESCOPO_NAO_COMPROVADO', 'Unidades sem pertencimento comprovado permanecem fora do XLSX.', len(escopo_destino.unidades)-len(permitidas) if permitidas is not None else 0)
    aviso('DESCRICOES_NEUTRAS', 'Descrições neutras preservadas; não foi inventada uma competência.', neutras)
    if fechamento and fechamento.get('estado') == 'reconciliado_somente_diagnostico':
        aviso('FECHAMENTO_HABITA_RECONCILIADO', 'Anomalia Habita/VG preservada. Reconciliação vale exclusivamente para diagnóstico.', 1)
    for d in decisoes:
        codigos = list(d.get('bloqueios') or []) if d.get('situacao') == 'revisao' else []
        if d.get('situacao') == 'revisao' and not codigos:codigos = ['CONDICAO_INDETERMINADA']
        if d.get('situacao') == 'nao_elegivel':
            codigos.append({'veto_coletivo':'VETO_COLETIVO','valor_original_zero':'VALOR_ORIGINAL_ZERO'}.get(d.get('motivo_selecao'),'PRAZO_NAO_ATINGIDO'))
        if d.get('unidade_id') in retidas:codigos.append('BBZ_CONFLITO_DOCUMENTAL_PERSISTENTE')
        for codigo in dict.fromkeys(codigos):
            detalhes.append(dict(unidade_id=d.get('unidade_id'),bloco=d.get('bloco',''),unidade=d.get('unidade',''),
                boleto_id=d['id'],boleto=d.get('boleto',''),estado='ressalva' if d.get('situacao') == 'elegivel' else d.get('situacao'),
                categoria='documental' if codigo == 'BBZ_CONFLITO_DOCUMENTAL_PERSISTENTE' else 'financeira' if d.get('situacao') == 'nao_elegivel' else 'retencao',
                codigo=codigo,descricao=descrever_motivo(codigo),origens=[_origem(o) for o in boletos[d['id']].origens] if d['id'] in boletos else []))
    checks = []
    def check(id_, descricao, categorias, *, aplicavel=True, disponivel=True, ressalva=False, evidencia):
        estado = ('erro_critico' if categorias_erros.intersection(categorias) else 'nao_aplicavel' if not aplicavel
                  else 'nao_verificavel' if not disponivel else 'conforme_com_ressalvas' if ressalva else 'conforme')
        checks.append(dict(id=id_,descricao=descricao,estado=estado,evidencia=evidencia))
    check('estrutura','Aba Dados, 30 colunas, datas e identificadores textuais',{'estrutura','seguranca'},aplicavel=bool(registros),disponivel=arquivo_conferido,evidencia='Bytes do XLSX efetivamente lidos; sem modificação do arquivo.')
    check('planejamento','Correspondência entre linhas planejadas e escritas',{'planejamento','rastreabilidade'},aplicavel=bool(registros),disponivel=arquivo_conferido,evidencia='Consistência interna com o planejamento; não é prova independente da fonte.')
    check('dados_leitor','Valores e vencimentos versus canônico do leitor',{'dados_leitor'},aplicavel=bool(dividas),disponivel=arquivo_conferido and lote_origem is not None and fontes_canonic,evidencia='Canônico anterior ao enriquecimento e suas origens/hash; não é uma segunda extração do documento.')
    check('elegibilidade','Linhas permitidas pelas decisões financeiras e pelo modo A/B',{'elegibilidade'},aplicavel=bool(decisoes),evidencia='Decisões existentes; a Central não reexecuta nem modifica a régua.')
    check('vinculos','Pertencimento das unidades e procedência das comprovações',{'vinculos'},aplicavel=escopo_destino is not None,ressalva=bool(escopo_destino and len(permitidas)<len(escopo_destino.unidades)),evidencia='Escopo documental verificado pelo processamento. Cadastro íntegro deve permanecer inalterado até o download.')
    check('retencoes','CPF/CNPJ e contatos protegidos ausentes da saída',{'retencoes'},aplicavel=bool(registros),disponivel=arquivo_conferido,ressalva=bool(retidas),evidencia='Retenções persistentes e associações cadastrais retidas; aprovação de pertencimento não as libera.')
    check('fonte_independente','Fidelidade integral da extração ao documento original',set(),disponivel=False,evidencia='Não comprovável com as fontes disponíveis à Central. O canônico vem do leitor; exige conferência documental ou gabarito independente.')
    return dict(versao='validacao_conversao@2',estado='erro_critico' if contagens_erros else 'sem_arquivo' if not registros else 'conforme_com_ressalvas' if avisos else 'conforme',
        autoriza_cobranca=False,permite_exportacao_operacional=False,
        limite='Conferência técnica diagnóstica; consistência interna e canônicos do leitor não equivalem a atesto humano ou prova independente da extração.',
        contexto={k:contexto[k] for k in ('condominio','administradora','data_ref','modo') if k in contexto},
        arquivo={'sha256':digest,'conferido_integralmente':arquivo_conferido},
        vinculos={'cadastro_sha256':getattr(escopo_destino,'cadastro_sha256',None),'cadastro_revisao':getattr(escopo_destino,'cadastro_revisao',None)},
        indicadores=dict(boletos_analisados=len(decisoes),boletos_elegiveis=sum(d.get('situacao') == 'elegivel' for d in decisoes),
            boletos_elegiveis_financeiros=sum(d.get('situacao_financeira') == 'elegivel_na_simulacao' for d in decisoes),
            boletos_excluidos_financeiros=sum(d.get('situacao_financeira') == 'excluido' or d.get('situacao') == 'nao_elegivel' for d in decisoes),
            boletos_em_revisao=sum(d.get('situacao') == 'revisao' for d in decisoes),linhas_divida=dividas_lidas,
            linhas_cadastrais=cadastros_lidos,linhas_divida_planejadas=len(dividas),linhas_cadastrais_planejadas=len(cadastros),
            linhas_lidas_xlsx=lidas,unidades_no_xlsx=len(unidades_lidas),
            unidades_escopo_comprovado=len(permitidas) if permitidas is not None else None,
            unidades_escopo_pendente=len(escopo_destino.unidades)-len(permitidas) if permitidas is not None else None,
            unidades_vinculo_persistente=sum(getattr(u,'origem_comprovacao',None) == 'cadastro_persistente' and u.estado == 'comprovado_documentalmente' for u in escopo_destino.unidades) if escopo_destino else None,
            unidades_contato_retido=len(retidas),linhas_com_contato_retido=retidas_lidas,
            descricoes_neutras=neutras,valor_financeiro_xlsx=f'{total_obtido:.2f}',valor_financeiro_planejado=f'{total_planejado:.2f}',
            valor_financeiro_canonico=f'{total_canonico:.2f}' if lote_origem is not None else None),
        verificacoes=checks,motivos_retencao=[dict(codigo=k,quantidade=v,descricao=descrever_motivo(k)) for k,v in sorted(pendentes.items())],
        erros=erros,avisos=avisos,total_erros=sum(contagens_erros.values()),contagem_erros=dict(contagens_erros),
        detalhes_limitados=sum(contagens_erros.values())>len(erros),registros=detalhes)
