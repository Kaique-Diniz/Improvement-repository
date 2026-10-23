"""Regressão da revisão final; identidades e endereços inteiramente fictícios."""
import pytest

from conversor.application.reading import resultado_leitura
from conversor.domain.canonical import Endereco
from conversor.domain.documents import resolver_documento
from conversor.readers.contact_segments import segmentar_endereco
from conversor.readers.contact_segments import segmentar_emails
from conversor.readers.contact_segments import segmentar_telefones
from examples.fase3.layouts_sinteticos import cadastro_paginas, habita_paginas
from tests.phase3.test_real_layouts import ler, trocar


@pytest.mark.parametrize('rua,logradouro,numero,complemento', [
    ('Rua Ficticia, 100', 'Rua Ficticia', '100', ''),
    ('Rua Ficticia 100', 'Rua Ficticia', '100', ''),
    ('Rua Ficticia, 100 - AP 9', 'Rua Ficticia', '100', 'AP 9'),
    ('Rua Ficticia S/N', 'Rua Ficticia', 'S/N', ''),
])
def test_endereco_expresso_sem_consulta_externa(rua, logradouro, numero, complemento):
    endereco, alerta = segmentar_endereco([rua, 'BAIRRO - CIDADE FICTICIA - SP - 00000-000'])
    assert alerta is None
    assert endereco == Endereco(logradouro=logradouro, numero=numero, complemento=complemento,
                               bairro='BAIRRO', cidade='CIDADE FICTICIA', uf='SP', cep='00000000')


def test_endereco_continuado_em_quatro_linhas():
    e, alerta = segmentar_endereco(['Rua Ficticia, 100 - AP', '9', 'BAIRRO - CIDADE - SP -', '00000000'])
    assert alerta is None and e.complemento == 'AP 9' and e.cep == '00000000'


@pytest.mark.parametrize('linhas,codigo', [
    ([], 'ENDERECO_AUSENTE'),
    (['Rua Ficticia, 100'], 'ENDERECO_ORIGINAL_NAO_SEGMENTADO'),
    (['Rua Ficticia', 'BAIRRO - CIDADE - SP - 00000-000'], 'ENDERECO_PARCIALMENTE_SEGMENTADO'),
    (['Rua Ficticia, 100', 'BAIRRO - CIDADE - SP - 0000X-000'], 'ENDERECO_PARCIALMENTE_SEGMENTADO'),
])
def test_endereco_nao_fabrica_campos_ausentes(linhas, codigo):
    e, alerta = segmentar_endereco(linhas)
    assert alerta == codigo
    if '0000X-000' in ' '.join(linhas):
        assert e.cep == ''


def test_dois_enderecos_nao_viram_um_endereco_hibrido():
    e, alerta = segmentar_endereco(['Rua Ficticia, 100', 'BAIRRO - CIDADE - SP - 00000-000',
                                   'Rua Imaginaria, 200', 'OUTRO - CIDADE - RJ - 00000-001'])
    assert e == Endereco() and alerta == 'ENDERECOS_MULTIPLOS_NAO_SEGMENTADOS'


def test_cadastro_segmenta_com_origens_de_ambas_as_paginas_e_preserva_bruto():
    lote = ler('cadastro')
    p = lote.pessoas[0]
    assert p.contato.endereco.numero == '1'
    assert p.contato.endereco.cep == '00000000'
    r = next(r for r in lote.ressalvas if r.codigo == 'CADASTRO_CAMPOS_ORIGINAIS')
    assert any('Rua Ficticia' in v and '"pagina": 1' in v for v in r.valores_originais)
    assert any('BAIRRO FICTICIO' in v and '"pagina": 2' in v for v in r.valores_originais)
    assert resolver_documento(p).valor == '00000000191'


def test_cadastro_sem_telefone_e_email_vazios_com_alertas():
    ps = cadastro_paginas()
    ps = [[(x, y, t) for x, y, t in page if (x != 609 or t == 'E-mail') and not t.startswith('+55')] for page in ps]
    lote = ler('cadastro', ps)
    assert not lote.pessoas[0].contato.telefones and not lote.pessoas[0].contato.emails
    codigos = {r.codigo for r in lote.ressalvas}
    assert {'TELEFONE_AUSENTE_OU_NAO_VALIDADO', 'EMAIL_AUSENTE_OU_NAO_VALIDADO'} <= codigos


def test_email_invalido_nao_e_inventado_nem_perdido_sem_alerta():
    lote = ler('cadastro', trocar(cadastro_paginas(), 'sintetico@example.invalid', 'EMAIL_INVALIDO'))
    assert not lote.pessoas[0].contato.emails
    assert any(r.codigo == 'EMAIL_NAO_SEGMENTADO' and 'EMAIL_INVALIDO' in r.valores_originais for r in lote.ressalvas)


@pytest.mark.parametrize('linhas,esperados', [
    (['pessoa@example.inva', 'lid'], ['pessoa@example.invalid']),
    (['pessoa@example.invalid;outra@', 'example.invalid'], ['pessoa@example.invalid', 'outra@example.invalid']),
    (['pessoa@example.invalid', 'outra@example.invalid'], ['pessoa@example.invalid', 'outra@example.invalid']),
])
def test_emails_fragmentados_nao_exportam_prefixo_do_dominio(linhas, esperados):
    emails, pendentes = segmentar_emails(linhas)
    assert emails == esperados and not pendentes


def test_telefone_alternativo_continuado_sem_corrigir_pais_duplicado():
    telefones, pendentes = segmentar_telefones(['+55 55 11 90000 0001 (+55 11', '900000002)'])
    assert telefones == ['11900000002']
    assert pendentes == ['+55 55 11 90000 0001']


@pytest.mark.parametrize('linhas,esperados,alerta', [
    (['+55 11 90000-0001'], ['11900000001'], False),
    (['(11) 3000-0001;11 90000-0002'], ['1130000001', '11900000002'], False),
    (['90000-0001'], [], True),
    (['3000', '900000001'], [], True),
])
def test_telefone_nao_inventa_ddd_nem_concatena_numeros_independentes(linhas, esperados, alerta):
    telefones, pendentes = segmentar_telefones(linhas)
    assert telefones == esperados and bool(pendentes) == alerta


def test_cadastro_enderecos_conflitantes_bloqueia_unidade_sem_escolher():
    ps = cadastro_paginas()
    ps[1][2:2] = [(346, 775, 'Rua Imaginaria, 2'), (346, 765, 'OUTRO - CIDADE - RJ - 00000-001')]
    lote = ler('cadastro', ps)
    assert lote.pessoas[0].contato.endereco == Endereco()
    assert any(o.bloqueante and o.codigo == 'ENDERECOS_MULTIPLOS_NAO_SEGMENTADOS'
               for o in resultado_leitura(lote, processamento_id='revisao').ocorrencias)


def test_competencia_ausente_tem_alerta_sem_converter_emissao_ou_vencimento():
    lote = ler('habita', habita_paginas())
    assert lote.boletos[0].competencia is None
    assert lote.boletos[0].emissao_original == '090926'
    r = next(r for r in lote.ressalvas if r.codigo == 'COMPETENCIA_AUSENTE_NA_FONTE')
    assert r.gravidade == 'alerta' and r.origens[0] == lote.boletos[0].origens[0]


@pytest.mark.parametrize('remover_linha', [False, True])
def test_habita_contatos_ausentes_alertam_sem_mudar_financeiro(remover_linha):
    ps = habita_paginas()
    if remover_linha:
        ps = [[l for l in pagina if not l[2].startswith('Celular:')] for pagina in ps]
    else:
        ps = trocar(ps, 'E-mail: sintetico@example.invalid', 'E-mail:')
    lote = ler('habita', ps)
    assert not lote.pessoas[0].contato.emails
    assert any(r.codigo == 'EMAIL_AUSENTE_OU_NAO_VALIDADO' and r.gravidade == 'alerta' for r in lote.ressalvas)
    if remover_linha:
        assert not lote.pessoas[0].contato.telefones
        assert any(r.codigo == 'TELEFONE_AUSENTE_OU_NAO_VALIDADO' for r in lote.ressalvas)
    assert lote.boletos[0].composicao.total_original == ler('habita').boletos[0].composicao.total_original


def test_nome_cadastral_preferencial_nao_exige_correspondencia_textual():
    from conversor.application.cadastro import cruzar_cadastro
    fl = ler('fl')
    cadastro = ler('cadastro', trocar(cadastro_paginas(), 'TITULAR SINTETICO', 'TITULAR'))
    unido = cruzar_cadastro(fl, cadastro)
    assert unido.pessoas[0].nome == cadastro.pessoas[0].nome
    assert unido.boletos == fl.boletos
    assert any(r.codigo == 'DIVERGENCIA_NOME_ENTRE_FONTES' and r.gravidade == 'informativo' for r in unido.ressalvas)
    assert not resolver_documento(unido.pessoas[0]).bloqueante
    assert not resultado_leitura(unido, processamento_id='divergencia').bloqueante
