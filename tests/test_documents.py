"""Somente documentos gerados para teste; nenhum cadastro real é utilizado."""
from tests.fs_support import assert_privado
from datetime import date
import json

from openpyxl import load_workbook
import pytest
from pydantic import ValidationError

from conversor.application.documents import ocorrencias_documentais
from conversor.application.enrichment import complementar_cadastro
from conversor.application.reading import resultado_leitura
from conversor.domain.canonical import (
    Documento, Endereco, EvidenciaDocumento, LoteCanonico, Pessoa, Origem,
    cnpj_validado, cpf_validado, documento_de_texto, documento_validado,
)
from conversor.domain.documents import resolver_documento
from conversor.domain.template import COLUNAS, Template
from conversor.export.contract import LinhaExportacao, materializar
from conversor.export.xlsx import escrever_xlsx


# Vetores sintéticos; conferência fiscal algorítmica não comprova identidade/cadastro.
CPF = '00000000191'
CPF_OUTRO = '00000000272'
CNPJ = '00000000000191'


def com_documento(pessoa, tipo='cpf', valor=CPF, **updates):
    return Pessoa.model_validate(pessoa.model_dump() | {'documento': Documento(tipo=tipo, valor=valor)} | updates)


def linha(pessoa):
    return LinhaExportacao(processamento_id='exec_doc', registro_id=pessoa.unidade_id, tipo='cadastral',
        nm_cedente_cedente='CREDOR SINTETICO', cedente='0001', pessoa=pessoa)


@pytest.mark.parametrize('tipo,bruto,esperado', [
    ('cpf', CPF, CPF), ('cpf', '000.000.001-91', CPF), ('cpf','00000000272','00000000272'),
    ('cnpj', CNPJ, CNPJ), ('cnpj', '00.000.000/0001-91', CNPJ),
    ('cnpj', '00000001000136', '00000001000136'), ('cnpj','00.123.456/0001-49','00123456000149'),
])
def test_documentos_validos_normalizam_mascara_sem_perder_zeros(tipo, bruto, esperado):
    doc = Documento(tipo=tipo, valor=bruto)
    assert documento_validado(doc) == esperado
    assert len(esperado) == (11 if tipo == 'cpf' else 14)


@pytest.mark.parametrize('tipo,valor', [
    ('cpf','00000000190'), ('cpf','00000000000'), ('cpf','11111111111'), ('cpf','123'),
    ('cpf', CNPJ), ('cnpj', CPF), ('cnpj','00000000000190'), ('cnpj','00000000000000'),
    ('cnpj','11111111111111'), ('cnpj','0000000000191'), ('cnpj','000000000000191'),
    ('cnpj','00a000000000191'), ('cnpj','00000000000191e0'), ('cnpj','０００００００００００１９１'),
    ('outro', CNPJ), ('cpf','+00000000191'), ('cpf','00000000191/'),
])
def test_documentos_invalidos_nao_completam_nem_retipam(tipo, valor):
    assert documento_validado(Documento(tipo=tipo, valor=valor)) == ''


@pytest.mark.parametrize('valor', [191, 191.0, True])
def test_documento_nao_aceita_numero_que_perdeu_zeros(valor):
    with pytest.raises(ValidationError):
        Documento(tipo='cpf', valor=valor)


def test_validadores_de_tipo_continuam_distintos():
    assert cpf_validado(Documento(tipo='cnpj', valor=CNPJ)) == ''
    assert cnpj_validado(Documento(tipo='cpf', valor=CPF)) == ''


@pytest.mark.parametrize('tipo,valor', [('cpf', CPF), ('cnpj', CNPJ)])
def test_excel_roundtrip_texto_numero_formato_zeros_30_colunas(tmp_path, pessoa, tipo, valor):
    pessoa = com_documento(pessoa,tipo,valor)
    destino = tmp_path/'documento.xlsx'
    alertas = escrever_xlsx((linha(pessoa),),Template(id='tpl',nome='Universal',versao='1'),destino,data_ref=date(2026,10,21))
    assert not alertas
    wb = load_workbook(destino)
    try:
        s = wb['Dados']
        assert s.max_column == 30 and s['C1'].value == 'CPF'
        assert tuple(c.value.rstrip() for c in s[1]) == COLUNAS
        assert (s['C2'].value,s['C2'].data_type,s['C2'].number_format) == (valor,'s','@')
        assert all(s.cell(2,c).value is None for c in range(25,31))
    finally: wb.close()


@pytest.mark.parametrize('documento,codigo', [(None,'DOCUMENTO_AUSENTE'),
    (Documento(tipo='cpf',valor='123'),'DOCUMENTO_INVALIDO'),
    (Documento(tipo='cnpj',valor='00000000000000'),'DOCUMENTO_INVALIDO')])
def test_vazio_alerta_nao_bloqueia_e_preserva_bruto(pessoa, documento, codigo):
    pessoa = Pessoa.model_validate(pessoa.model_dump()|{'documento':documento})
    r = materializar(linha(pessoa))
    assert r.valores[2] == ''
    assert [o.codigo for o in r.ocorrencias] == [codigo]
    assert not r.ocorrencias[0].bloqueante
    if documento:
        assert r.ocorrencias[0].evidencias_documentais[0].documento == documento
    assert materializar(linha(pessoa)) == r


def fonte(pessoa, documento, *, titular=None):
    origem = Origem.model_validate(pessoa.origem.model_dump()|{'arquivo_id':'cadastro_sintetico','pagina':2})
    return EvidenciaDocumento(documento=documento,origem=origem,titular_id=titular)


@pytest.mark.parametrize('tipo,valor', [('cpf',CPF_OUTRO), ('cnpj',CNPJ)])
def test_conflito_mesmo_titular_bloqueia_audita_e_impede_arquivo(tmp_path, unidade, pessoa, tipo, valor):
    pessoa = com_documento(pessoa)
    evidencia = fonte(pessoa,Documento(tipo=tipo,valor=valor),titular=pessoa.id)
    pessoa = Pessoa.model_validate(pessoa.model_dump()|{'evidencias_documentais':(evidencia,)})
    lote = LoteCanonico(unidades=(unidade,),boletos=(),pessoas=(pessoa,))
    r = resultado_leitura(lote,processamento_id='exec_doc')
    assert r.bloqueante
    assert len(r.ocorrencias) == 1 and r.ocorrencias[0].codigo == 'DOCUMENTOS_CONFLITANTES'
    assert r.ocorrencias[0].bloqueante
    assert len(r.ocorrencias[0].evidencias_documentais)==2
    assert len({e.origem.arquivo_id for e in r.ocorrencias[0].evidencias_documentais})==2
    assert resolver_documento(pessoa).valor == ''
    with pytest.raises(ValidationError,match='REVISAO_HUMANA'):
        linha(pessoa)
    # Também impede escapar pela construção sem validação inicial do DTO.
    insegura = LinhaExportacao.model_construct(processamento_id='exec_doc',registro_id=unidade.id,
        tipo='cadastral',nm_cedente_cedente='SINTETICO',cedente='0001',pessoa=pessoa)
    with pytest.raises(ValidationError,match='REVISAO_HUMANA'):
        escrever_xlsx((insegura,),Template(id='tpl',nome='Universal',versao='1'),tmp_path/'nao.xlsx',data_ref=date(2026,10,21))
    assert not (tmp_path/'nao.xlsx').exists()
    audit = r.ocorrencias[0]
    assert type(audit).model_validate_json(audit.model_dump_json())==audit
    assert CPF not in repr(audit) and valor not in repr(audit)


@pytest.mark.parametrize('titular', [None,'outro_titular'])
def test_documento_sem_vinculo_nao_resolve_automaticamente(pessoa,titular):
    evidencia = fonte(pessoa,Documento(tipo='cnpj',valor=CNPJ),titular=titular)
    p = Pessoa.model_validate(pessoa.model_dump()|{'documento':None,'evidencias_documentais':(evidencia,)})
    r = resolver_documento(p)
    assert r.bloqueante and not r.valor and r.codigos==('DOCUMENTO_TITULAR_NAO_CONFIRMADO',)


def test_mascara_diferente_na_mesma_documentacao_nao_cria_conflito(pessoa):
    p = com_documento(pessoa)
    evidencia = fonte(p,Documento(tipo='cpf',valor='000.000.001-91'),titular=p.id)
    p = Pessoa.model_validate(p.model_dump()|{'evidencias_documentais':(evidencia,)})
    assert resolver_documento(p).valor == CPF
    assert not ocorrencias_documentais(p,processamento_id='exec')


def test_invalido_junto_com_valido_mantem_alerta_e_todas_fontes(pessoa):
    p=com_documento(pessoa)
    evidencia=fonte(p,Documento(tipo='cnpj',valor='123'),titular=p.id)
    p=Pessoa.model_validate(p.model_dump()|{'evidencias_documentais':(evidencia,)})
    r=materializar(linha(p))
    assert r.valores[2]==CPF
    assert [o.codigo for o in r.ocorrencias]==['DOCUMENTO_INVALIDO']
    assert len(r.ocorrencias[0].evidencias_documentais)==2


@pytest.mark.parametrize('tipo,valor', [('cpf',CPF_OUTRO),('cnpj',CNPJ)])
def test_enriquecimento_nao_substitui_documentos_conflitantes(unidade,pessoa,tipo,valor):
    original=com_documento(pessoa)
    complementar=com_documento(pessoa,tipo,valor,origem=fonte(pessoa,Documento(tipo=tipo,valor=valor)).origem)
    lote=LoteCanonico(unidades=(unidade,),boletos=(),pessoas=(original,))
    chave=(unidade.condominio_id,unidade.bloco_original,unidade.unidade_original)
    alertas=[]
    r=complementar_cadastro(lote,{chave:complementar},Endereco(),processamento_id='exec',alertas=alertas)
    assert r.pessoas[0].documento is None
    assert resolver_documento(r.pessoas[0]).bloqueante
    assert [o.codigo for o in alertas]==['DOCUMENTOS_CONFLITANTES']
    assert len(alertas[0].evidencias_documentais)==2
    assert lote.pessoas[0].documento.valor==CPF


def test_cadastro_vazio_preserva_documento_e_origem_da_mesma_pessoa(unidade,pessoa):
    original=com_documento(pessoa,'cnpj',CNPJ)
    complementar=Pessoa.model_validate(pessoa.model_dump()|{'documento':None,'origem':fonte(pessoa,original.documento).origem})
    lote=LoteCanonico(unidades=(unidade,),boletos=(),pessoas=(original,))
    chave=(unidade.condominio_id,unidade.bloco_original,unidade.unidade_original)
    r=complementar_cadastro(lote,{chave:complementar},Endereco())
    assert resolver_documento(r.pessoas[0]).valor==CNPJ
    assert r.pessoas[0].documento_origem==original.origem


def test_auditoria_documental_persiste_em_json_protegido(tmp_path,pessoa):
    p=com_documento(pessoa)
    f=fonte(p,Documento(tipo='cpf',valor=CPF_OUTRO),titular=p.id)
    p=Pessoa.model_validate(p.model_dump()|{'evidencias_documentais':(f,)})
    o=ocorrencias_documentais(p,processamento_id='exec_doc')[0]
    # A referência a processamento exige catálogo coerente; roundtrip do contrato
    # de ocorrência é também conferido acima. Arquivo de auditoria usa adapter privado.
    from conversor.adapters.private_json import escrever_json
    destino=tmp_path/'auditoria.json'
    escrever_json(destino,o.model_dump(mode='json'))
    assert_privado(destino)
    assert type(o).model_validate(json.loads(destino.read_text()))==o


@pytest.mark.parametrize('valor,tipo', [(CPF,'cpf'),(CNPJ,'cnpj'),('00.000.000/0001-91','cnpj'),('invalido','outro')])
def test_classificacao_textual_preserva_valor_bruto(valor,tipo):
    r=documento_de_texto(valor)
    assert r.tipo==tipo and r.valor==valor


@pytest.mark.parametrize('familia', ['habita','cadastro'])
def test_leitores_preservam_cnpj_valido_na_origem_sintetica(familia):
    from conversor.readers.cadastro import LeitorCadastroFLSintetico
    from conversor.readers.habita import LeitorHabitaSintetico
    from conversor.readers.text_support import ContextoLeitura
    from examples.fase2.gerar_demo import pdf_sintetico
    if familia=='habita':
        leitor=LeitorHabitaSintetico()
        texto=('Inadimplencia Atualizada\nCondominio: 9999 - LAB\n'
            f'Bloco: DEP Unidade: 000001 TITULAR SINTETICO CPF: 00.000.000/0001-91\n'
            '10000001 17/09/26 202609 94 COTA 100,00 0,00 0,00 100,00\n'
            'Total do boleto: 100,00 0,00 0,00 100,00\nTotal da Unidade: 100,00 0,00 0,00 100,00')
        contexto=ContextoLeitura('cond_lab','adm_lab',leitor.formato_id,'fonte_lab','9999')
        pessoa=leitor.ler(pdf_sintetico([texto]),contexto=contexto).pessoas[0]
    else:
        leitor=LeitorCadastroFLSintetico()
        texto=('W045A CONDOMINIO EDIFICIO LAB (AMOSTRA SINTETICA)\n'
            '0001 TORRE A  TITULAR SINTETICO  Proprietario  Rua Exemplo, 1  00.000.000/0001-91  (vazio)')
        contexto=ContextoLeitura('cond_lab','adm_lab',leitor.formato_id,'fonte_lab','LAB')
        pessoa=next(iter(leitor.ler(pdf_sintetico([texto]),contexto=contexto).values()))
    assert pessoa.documento.tipo=='cnpj'
    assert documento_validado(pessoa.documento)==CNPJ
    assert resolver_documento(pessoa).valor==CNPJ


def test_preferencia_do_laboratorio_nao_remove_conflito_documental(unidade,pessoa):
    anterior=com_documento(pessoa)
    novo=com_documento(pessoa,'cnpj',CNPJ,nome='OUTRO TITULAR SINTETICO')
    lote=LoteCanonico(unidades=(unidade,),boletos=(),pessoas=(anterior,))
    chave=(unidade.condominio_id,unidade.bloco_original,unidade.unidade_original)
    alertas=[]
    r=complementar_cadastro(lote,{chave:novo},Endereco(),politica_titular='cadastro_confirmado_no_laboratorio',
                            processamento_id='exec_doc',alertas=alertas)
    assert resolver_documento(r.pessoas[0]).bloqueante
    assert {'DOCUMENTOS_CONFLITANTES','DOCUMENTO_TITULAR_NAO_CONFIRMADO'} <= {o.codigo for o in alertas if o.bloqueante}
    assert len(r.pessoas[0].evidencias_documentais)==2


def test_nomes_iguais_com_ids_diferentes_nao_confirmam_associacao(unidade,pessoa):
    anterior=com_documento(pessoa)
    novo=Pessoa.model_validate(pessoa.model_dump()|{'id':'outra_pessoa','documento':None})
    lote=LoteCanonico(unidades=(unidade,),boletos=(),pessoas=(anterior,))
    chave=(unidade.condominio_id,unidade.bloco_original,unidade.unidade_original)
    r=complementar_cadastro(lote,{chave:novo},Endereco())
    assert resolver_documento(r.pessoas[0]).bloqueante


def test_conflito_de_outro_cadastro_nao_contamina_documento_valido(unidade,pessoa):
    # A resolução é por pessoa/cadastro; os alertas não são globais por tipo documental.
    primeira=com_documento(pessoa)
    segunda=com_documento(pessoa,'cnpj',CNPJ,id='outra_pessoa',unidade_id='outra_unidade')
    assert not resolver_documento(primeira).bloqueante
    assert not resolver_documento(segunda).bloqueante
    assert materializar(linha(primeira)).valores[2]==CPF
    assert materializar(linha(segunda)).valores[2]==CNPJ
