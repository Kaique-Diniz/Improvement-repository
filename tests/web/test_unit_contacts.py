"""Cadastros por unidade: somente nomes/documentos inteiramente sintéticos."""
from io import BytesIO

from openpyxl import load_workbook
import pytest

from conversor.application.cadastro import cruzar_cadastro, reavaliar_pendencias_cadastrais
from conversor.domain.canonical import Documento, EvidenciaDocumento, Ocorrencia, Pessoa
from conversor.domain.documents import CONTATO_UNIDADE, resolver_documento
from conversor.web.demo import documentos_demo
from conversor.web.service import PedidoDiagnostico, analisar, ler, reconhecer
from examples.fase3.layouts_sinteticos import cadastro_paginas, pdf_posicionado

CPF = '00000000191'
OUTRO_CPF = '00000000272'
CNPJ = '00000000000191'
NOME = 'TITULAR SINTETICO'
DOIS_NOMES = 'TITULAR SINTETICO / OUTRA PESSOA SINTETICA'


def documentos(nome=DOIS_NOMES, docs=(CPF,)):
    dados = documentos_demo()
    ps = cadastro_paginas()
    ps = [[(x, y, t.replace('EDIFICIO SINTETICO', 'EDIFICIO PLAZA MAYOR IPIRANGA'))
           for x, y, t in page] for page in ps]
    ps[0] = [(x, y, nome if x == 91 and t == NOME else t)
             for x, y, t in ps[0] if x != 534 or t == 'CPF/CNPJ']
    ps[0].extend((534, 740-i*12, d) for i, d in enumerate(docs))
    dados['cadastro'] = pdf_posicionado(ps)
    return dados


def lotes(dados):
    perfil, codigo, formato = reconhecer(dados['inadimplencia'])
    financeiro, _ = ler(dados['inadimplencia'], perfil, codigo, formato, 'inadimplencia')
    perfil, codigo, formato = reconhecer(dados['cadastro'], cadastro=True)
    cadastral, _ = ler(dados['cadastro'], perfil, codigo, formato, 'cadastro')
    return financeiro, cadastral


def executar(tmp_path, dados, *, modo='B', historico=()):
    return analisar(dados['inadimplencia'], PedidoDiagnostico(data_ref='2026-10-21', modo=modo),
        processamento_id='contatos_sinteticos', destino=tmp_path,
        cadastro=dados['cadastro'], historico=historico)


@pytest.mark.parametrize('modo', ['A', 'B'])
@pytest.mark.parametrize('nome,docs,esperado,codigo', [
    (NOME, (CPF,), CPF, None),
    (DOIS_NOMES, (CPF,), CPF, None),
    (DOIS_NOMES, (), '', 'DOCUMENTO_AUSENTE'),
    (NOME, (), '', 'DOCUMENTO_AUSENTE'),
    (DOIS_NOMES, (CNPJ,), CNPJ, None),
    (DOIS_NOMES, ('123',), '', 'DOCUMENTO_INVALIDO'),
])
def test_nomes_e_documento_opcional_nao_duplicam_pessoas_cotas_ou_linhas(tmp_path, modo, nome, docs, esperado, codigo):
    dados = documentos(nome, docs)
    financeiro, cad = lotes(dados)
    unido = cruzar_cadastro(financeiro, cad)
    pessoa = unido.pessoas[0]
    assert len(unido.pessoas) == len(unido.unidades) == 2
    assert unido.boletos == financeiro.boletos
    assert pessoa.nome == nome and pessoa.relacao_unidade == CONTATO_UNIDADE
    assert resolver_documento(pessoa).valor == esperado
    assert all(e.titular_id is None for e in resolver_documento(pessoa).evidencias)
    r = executar(tmp_path, dados, modo=modo)
    assert r['resumo']['elegivel'] == 2 and r['resumo']['nao_elegivel'] == 1
    assert r['resumo'].get('revisao', 0) == 0
    ds = [d for d in r['decisoes'] if d['bloco'] == 'A']
    assert all(not d['pendencias_documentais'] and not d['bloqueios'] for d in ds)
    if codigo:
        assert all(codigo in d['alertas_cadastrais'] for d in ds)
        alertas = [o for o in r['ocorrencias'] if o['codigo'] == codigo]
        assert alertas and all(o['gravidade'] == ('informativo' if codigo == 'DOCUMENTO_AUSENTE' else 'alerta') for o in alertas)
    assert not r['autoriza_cobranca'] and not r['permite_exportacao_operacional']
    wb = load_workbook(tmp_path / 'TESTE_LOCAL_NAO_IMPORTAR.xlsx')
    sheet = wb['Dados']
    assert sheet.max_column == 30 and sheet['C1'].value == 'CPF'
    rows = list(sheet.iter_rows(min_row=2))
    assert len(rows) == (3 if modo == 'B' else 2)
    da_unidade = [row for row in rows if row[3].value == nome]
    assert len(da_unidade) == (2 if modo == 'B' else 1)
    assert all((row[2].value or '') == esperado for row in da_unidade)
    if esperado:
        assert all(row[2].data_type == 's' and row[2].number_format == '@' for row in da_unidade)
    if modo == 'B':
        assert sum(all(c.value is None for c in row[24:30]) for row in rows) == 1
    # O documento da outra torre permanece vinculado somente àquela unidade.
    assert next(row[2].value for row in rows if row[3].value == 'EMPRESA SINTETICA') == CNPJ
    wb.close()


@pytest.mark.parametrize('outro', [OUTRO_CPF, CNPJ])
def test_dois_documentos_validos_conflitantes_retem_so_unidade_afetada(tmp_path, outro):
    dados = documentos(docs=(CPF, outro))
    r = executar(tmp_path, dados)
    a = [d for d in r['decisoes'] if d['bloco'] == 'A']
    assert all(d['situacao'] == 'revisao' and 'DOCUMENTOS_CONFLITANTES' in d['pendencias_documentais'] for d in a)
    assert [d['situacao_financeira'] for d in a] == ['elegivel_na_simulacao', 'excluido']
    assert all('TITULAR_MULTIPLO_OU_NAO_SEGMENTADO' not in d['bloqueios'] for d in a)
    assert r['resumo']['linhas_teste'] == 1 and r['resumo']['cadastros_adicionais'] == 0
    assert next(d['situacao'] for d in r['decisoes'] if d['bloco'] == 'B') == 'elegivel'


def test_duas_mascaras_do_mesmo_documento_nao_sao_dois_documentos(tmp_path):
    r = executar(tmp_path, documentos(docs=(CPF, '000.000.001-91')))
    assert not r['resumo'].get('revisao', 0)


def test_nomes_diferentes_preferem_cadastro_sem_afirmar_titularidade(tmp_path):
    dados = documentos('OUTRA PESSOA SINTETICA / TERCEIRA PESSOA SINTETICA')
    financeiro, cad = lotes(dados)
    unido = cruzar_cadastro(financeiro, cad)
    assert unido.pessoas[0].nome == cad.pessoas[0].nome
    evidencia = next(r for r in unido.ressalvas if r.codigo == 'DIVERGENCIA_NOME_ENTRE_FONTES')
    assert evidencia.valores_originais == (NOME, cad.pessoas[0].nome)
    assert len({o.sha256 for o in evidencia.origens}) == 2
    r = executar(tmp_path, dados)
    assert not r['resumo'].get('revisao',0)
    assert all(not d['bloqueios'] for d in r['decisoes'])
    assert all('DIVERGENCIA_NOME_ENTRE_FONTES' in d['alertas_cadastrais'] for d in r['decisoes'] if d['bloco']=='A')


def legado(cad, codigo, *, origem=None, id_='legado_sintetico'):
    p = cad.pessoas[0]
    return Ocorrencia(id=id_, processamento_id='historico_sintetico', codigo=codigo, gravidade='critico',
        escopo='registro', registro_id=p.unidade_id, origem=origem or p.origem,
        evidencias_documentais=p.evidencias_documentais if codigo == 'DOCUMENTO_TITULAR_NAO_CONFIRMADO' else ())


@pytest.mark.parametrize('codigo', ['TITULAR_MULTIPLO_OU_NAO_SEGMENTADO', 'DOCUMENTO_TITULAR_NAO_CONFIRMADO', 'TITULAR_DIVERGENTE'])
def test_reavaliacao_explicita_preserva_historico_identificadores_e_fontes(tmp_path, codigo):
    dados = documentos(); financeiro, cad = lotes(dados)
    old = legado(cad, codigo, origem=financeiro.pessoas[0].origem if codigo == 'TITULAR_DIVERGENTE' else None)
    antes = old.model_dump_json()
    r = executar(tmp_path, dados, historico=(old,))
    assert not r['resumo'].get('revisao', 0)
    assert r['registros_historicos_carregados'] == 1
    assert old.model_dump(mode='json') in r['ocorrencias']
    assert len(r['reavaliacoes_historicas']) == 1
    nova = r['reavaliacoes_historicas'][0]
    assert nova['ocorrencia_id'] == old.id and nova['codigo_original'] == codigo
    assert nova['origens_conferidas'] and nova['efeito'] == 'nao_bloqueante_na_releitura'
    assert old.model_dump_json() == antes
    unido = cruzar_cadastro(financeiro, cad)
    assert reavaliar_pendencias_cadastrais(unido, (old,), cadastro=cad) == r['reavaliacoes_historicas']


@pytest.mark.parametrize('problema', ['hash', 'linha', 'unidade', 'evidencia_diferente', 'evidencia_de_outra_linha', 'codigo_critico', 'id_duplicado'])
def test_nao_reclassifica_historico_sem_prova_ou_bloqueios_diferentes(tmp_path, problema):
    dados = documentos(); _, cad = lotes(dados)
    old = legado(cad, 'DOCUMENTO_TITULAR_NAO_CONFIRMADO')
    if problema == 'hash':old = old.model_copy(update={'origem': old.origem.model_copy(update={'sha256': 'f'*64})})
    if problema == 'linha':old = old.model_copy(update={'origem': old.origem.model_copy(update={'linha': 999})})
    if problema == 'unidade':old = old.model_copy(update={'registro_id': cad.pessoas[1].unidade_id})
    if problema == 'codigo_critico':old = old.model_copy(update={'codigo': 'SUBTOTAL_BLOCO_DIVERGENTE', 'escopo': 'arquivo'})
    if problema == 'evidencia_diferente':
        e = EvidenciaDocumento(documento=Documento(tipo='cpf', valor=OUTRO_CPF), origem=old.origem)
        old = old.model_copy(update={'evidencias_documentais': (e,)})
    if problema == 'evidencia_de_outra_linha':
        e = old.evidencias_documentais[0]
        e = e.model_copy(update={'origem': e.origem.model_copy(update={'linha': 999})})
        old = old.model_copy(update={'evidencias_documentais': (e,)})
    historico = (old, old.model_copy(update={'codigo': 'DOCUMENTOS_CONFLITANTES'})) if problema == 'id_duplicado' else (old,)
    r = executar(tmp_path, dados, historico=historico)
    assert not r['reavaliacoes_historicas']
    assert r['resumo'].get('revisao', 0) > 0
    assert all(o.model_dump(mode='json') in r['ocorrencias'] for o in historico)


def test_reclassificar_falso_multiplo_preserva_aviso_de_nomes(tmp_path):
    dados = documentos('OUTRA PESSOA SINTETICA / TERCEIRA PESSOA SINTETICA')
    _, cad = lotes(dados)
    old = legado(cad, 'TITULAR_MULTIPLO_OU_NAO_SEGMENTADO')
    r = executar(tmp_path, dados, historico=(old,))
    assert len(r['reavaliacoes_historicas']) == 1
    assert not r['resumo'].get('revisao',0)
    assert all(old.codigo not in d['bloqueios'] for d in r['decisoes'])


def test_nomes_nao_vinculam_documento_explicitamente_atribuido_a_outro_registro(pessoa):
    fonte = EvidenciaDocumento(documento=Documento(tipo='cpf', valor=CPF), origem=pessoa.origem, titular_id='outro_registro')
    p = Pessoa.model_validate(pessoa.model_dump() | {'nome': DOIS_NOMES, 'relacao_unidade': CONTATO_UNIDADE,
        'evidencias_documentais': (fonte,)})
    assert resolver_documento(p).bloqueante


def test_documento_historico_distinto_continua_pendente_mesmo_com_cadastro_unico(tmp_path):
    dados = documentos(); _, cad = lotes(dados)
    old = legado(cad, 'DOCUMENTOS_CONFLITANTES')
    docs = (*cad.pessoas[0].evidencias_documentais,
            EvidenciaDocumento(documento=Documento(tipo='cpf', valor=OUTRO_CPF), origem=old.origem))
    old = old.model_copy(update={'evidencias_documentais': docs})
    r = executar(tmp_path, dados, historico=(old,))
    assert not r['reavaliacoes_historicas']
    assert all(d['contato']['documento'] == 'revisao' and 'DOCUMENTOS_CONFLITANTES' in d['pendencias_documentais']
               for d in r['decisoes'] if d['bloco'] == 'A')
    assert old.model_dump(mode='json') in r['ocorrencias']


def test_sem_releitura_do_cadastro_nao_resolve_historico(tmp_path):
    dados = documentos(); _, cad = lotes(dados)
    old = legado(cad, 'TITULAR_MULTIPLO_OU_NAO_SEGMENTADO')
    r = analisar(dados['inadimplencia'], PedidoDiagnostico(data_ref='2026-10-21', modo='B'),
        processamento_id='sem_cadastro', destino=tmp_path, historico=(old,))
    assert not r['reavaliacoes_historicas']
    assert r['resumo']['revisao'] == 2


def test_telefones_emails_e_documentos_ausentes_nao_bloqueiam_financeiro(tmp_path):
    dados = documentos(docs=())
    from pypdf import PdfReader
    from conversor.web.demo import pdf
    reader = PdfReader(BytesIO(dados['cadastro']))
    pages = []
    for page in reader.pages:
        fragments = []
        def visitante(text, cm, tm, font, size):
            if text.strip():fragments.append((tm[4], tm[5], text.strip()))
        page.extract_text(visitor_text=visitante)
        pages.append([(x, y, t) for x, y, t in fragments if not t.startswith('+55') and '@' not in t])
    dados['cadastro'] = pdf(pages)
    r = executar(tmp_path, dados)
    assert r['resumo']['elegivel'] == 2
    assert all(d['contato'] == {'documento':'ausente', 'telefone':False, 'email':False}
               for d in r['decisoes'] if d['bloco'] == 'A')


def test_enriquecimento_nao_transfere_documento_de_outro_registro(unidade, pessoa):
    from conversor.application.enrichment import complementar_cadastro
    from conversor.domain.canonical import Endereco, LoteCanonico
    from conversor.readers.text_support import ErroLeitura
    lote = LoteCanonico(unidades=(unidade,), boletos=(), pessoas=(pessoa,))
    key = (unidade.condominio_id, unidade.bloco_original, unidade.unidade_original)
    estrangeira = pessoa.model_copy(update={'unidade_id':'outra_unidade', 'relacao_unidade':CONTATO_UNIDADE,
                                          'documento':Documento(tipo='cpf', valor=CPF)})
    with pytest.raises(ErroLeitura, match='CADASTRO_DE_OUTRA_UNIDADE'):
        complementar_cadastro(lote, {key:estrangeira}, Endereco())


def test_enriquecimento_nao_apaga_associacao_expressa_a_outro_titular(unidade, pessoa):
    from conversor.application.enrichment import complementar_cadastro
    from conversor.domain.canonical import Endereco, LoteCanonico
    evidencia = EvidenciaDocumento(documento=Documento(tipo='cpf', valor=CPF), origem=pessoa.origem,
                                  titular_id='registro_terceiro')
    anterior = pessoa.model_copy(update={'evidencias_documentais':(evidencia,)})
    cadastro = pessoa.model_copy(update={'relacao_unidade':CONTATO_UNIDADE})
    lote = LoteCanonico(unidades=(unidade,), boletos=(), pessoas=(anterior,))
    key = (unidade.condominio_id, unidade.bloco_original, unidade.unidade_original)
    novo = complementar_cadastro(lote, {key:cadastro}, Endereco())
    r = resolver_documento(novo.pessoas[0])
    assert r.bloqueante and r.evidencias[0].titular_id == 'registro_terceiro'
