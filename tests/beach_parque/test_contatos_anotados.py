"""BPQ-02: somente documentos fictícios; nenhum contato de homologação real."""
from hashlib import sha256
import json

import pytest

from conversor.domain.template import COLUNAS
from conversor.application.beach_parque_cadastro import POLITICA
from conversor.readers.beach_parque_cadastro import (
    ANOTACAO_DESCONHECIDA, CONTATO_AMBIGUO, CONTATO_SEGMENTADO,
    CONTATO_TERCEIRO, segmentar_contato,
)
from conversor.readers.bbz_cadastro import _telefone, email_valido
from conversor.readers.text_support import ErroLeitura
from .fixtures import CPF, NOME, cadastro, dividir, ficha, financeiro, recibo
from .test_beach_parque import PROFILE, executar, ler_cad, rows

PHONE='(11) 91234-5678'
EMAIL='pessoa@example.invalid'


def fonte(contatos, **kw):
    return cadastro([ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,contatos=contatos,**kw)])


def evidencia(lote):
    return json.loads(next(r.valores_originais[0]for r in lote.ressalvas if r.codigo=='BPQ_CADASTRO_FICHA_ORIGINAL'))


@pytest.mark.parametrize('anotacao',[
    '', ' - atualizado em 10/01/2025', ' - atualizado em 10/01/2025.',
    ' - atualizada em 10/01/2025.', ' - alterado em 10/01/2025',
    ' - alterada em 10/01/2025.', ' (atualizado em 10/01/2025)',
    ' (Alterada em 10/01/2025).',
])
@pytest.mark.parametrize('tipo',['telefone','email'])
def test_valor_completo_e_anotacao_neutra_preservam_origem_e_colunas(tmp_path,anotacao,tipo):
    cell=('Celular - '+PHONE if tipo=='telefone'else'E-mail - '+EMAIL)+anotacao
    raw=fonte([cell]);lote=ler_cad(raw);person=lote.pessoas[0];ev=evidencia(lote)
    participant=next(p for p in ev['participantes']if p['papel']=='titular')
    values=participant['telefones'if tipo=='telefone'else'emails']
    assert len(values)==1
    origin=values[0][1]
    assert origin['sha256']==sha256(raw).hexdigest()and origin['pagina']==1
    original=next(c for c in ev['campos']if c['valor_original']==cell)
    assert original['papel']=='titular'and original['secao']=='telefone/e-mail do cliente'
    assert original['origem']['pagina']==origin['pagina']and original['origem']['linha']==origin['linha']
    assert original['x_inicio']==0 and original['x_fim']==210 and original['y']>0
    if anotacao:
        # Confirma a causa anterior, sem alterar o validador BBZ compartilhado.
        assert not (email_valido(EMAIL+anotacao)if tipo=='email'else _telefone(PHONE+anotacao)[1])
        notes=[n for n in lote.ressalvas if n.codigo==CONTATO_SEGMENTADO]
        assert len(notes)==1 and notes[0].origens[0].identificador.endswith('_x0_300')
        assert notes[0].gravidade=='informativo'and not notes[0].valores_originais
    result=executar(tmp_path,cad=raw);row=rows(tmp_path)[1]
    assert row[2]==CPF and result['cadastro_'+PROFILE]['associacoes_retidas']==0
    if tipo=='telefone':assert row[11:13]==('11','912345678')and not person.contato.emails
    else:assert row[21]==EMAIL and not person.contato.telefones
    assert result['politica_cadastral']==POLITICA
    assert not result['autoriza_cobranca']and not result['permite_exportacao_operacional']


@pytest.mark.parametrize('cell,code',[
    ('Celular - '+PHONE+' - telefone do filho',CONTATO_TERCEIRO),
    ('E-mail - '+EMAIL+' - contato do locatário',CONTATO_TERCEIRO),
    ('Celular - '+PHONE+' - contato da esposa',CONTATO_TERCEIRO),
    ('E-mail - '+EMAIL+' - verificar titular',CONTATO_AMBIGUO),
    ('Celular - '+PHONE+' - confirmar titularidade',CONTATO_AMBIGUO),
    ('Celular - '+PHONE+' - Pessoa Totalmente Ficticia',ANOTACAO_DESCONHECIDA),
    ('E-mail - '+EMAIL+' - anotação desconhecida',ANOTACAO_DESCONHECIDA),
    ('Celular - '+PHONE+' - 10/01/2025',ANOTACAO_DESCONHECIDA),
    ('Celular - '+PHONE+' - atualizado 10/01/2025',ANOTACAO_DESCONHECIDA),
    ('E-mail - '+EMAIL+' - atualizado em 31/02/2025',ANOTACAO_DESCONHECIDA),
    ('Celular - '+PHONE+' - atualizado em 10/01/20250',ANOTACAO_DESCONHECIDA),
    ('Celular - '+PHONE+' - atualizado em 10/01/2025 - telefone do filho',CONTATO_TERCEIRO),
    ('E-mail - '+EMAIL+' - contato do locatário (atualizado em 10/01/2025)',CONTATO_TERCEIRO),
    ('Celular - 9123-45','TELEFONE_NAO_SEGMENTADO'),
    ('E-mail - pessoa@@example.invalid','EMAIL_NAO_SEGMENTADO'),
    ('E-mail - '+EMAIL+' texto residual','EMAIL_NAO_SEGMENTADO'),
    ('Celular - 123456789012345','TELEFONE_NAO_SEGMENTADO'),
    ('E-mail - '+EMAIL+' outra@example.invalid','EMAIL_NAO_SEGMENTADO'),
    ('E-mail - '+EMAIL+'; outro@example.invalid - contato do filho',CONTATO_TERCEIRO),
    ('texto livre '+PHONE,'BBZ_CONTATO_NAO_SEGMENTADO'),
])
def test_campos_ambiguos_terceiros_e_invalidos_nao_recuperam_primeiro_contato(tmp_path,cell,code):
    raw=fonte([cell]);lote=ler_cad(raw)
    assert not lote.pessoas[0].contato.telefones and not lote.pessoas[0].contato.emails
    notes=[n for n in lote.ressalvas if n.codigo==code]
    assert len(notes)==1 and not notes[0].valores_originais
    assert notes[0].origens[0].sha256==sha256(raw).hexdigest()
    assert notes[0].origens[0].identificador.endswith('_x0_300')
    assert cell in [c['valor_original']for c in evidencia(lote)['campos']]
    r=executar(tmp_path,cad=raw);row=rows(tmp_path)[1]
    assert row[2]==CPF and not any(row[11:24])
    assert r['resumo']['dividas_efetivamente_geradas']==1


@pytest.mark.parametrize('papel,secao',[
    ('pagador','Telefone/e-mail do pagador'),
    ('locatario','Telefone/e-mail de locatário'),
    ('unidade','Telefone/e-mail da unidade'),
    ('correspondencia','Endereço de cobrança'),
    ('observacoes','Observações:'),
])
def test_contatos_de_outros_papeis_nao_sao_promovidos(tmp_path,papel,secao):
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,contatos=['E-mail - titular@example.invalid'])
    body.extend([(240,240,secao),(24,228,'Celular - '+PHONE+' - atualizado em 10/01/2025'),
        (24,216,'E-mail - terceiro@example.invalid - alterado em 10/01/2025')])
    # Retomar correspondência depois da ficha reproduziria uma ficha repetida;
    # nesse papel substituímos somente o campo da seção inicial já existente.
    if papel=='correspondencia':
        body=body[:-3]
        body.insert(5,(24,body[4][1]-1,'Celular - '+PHONE+' - atualizado em 10/01/2025'))
    cad=cadastro([body]);lote=ler_cad(cad)
    original=[c for c in evidencia(lote)['campos']if c['valor_original'].startswith('Celular - '+PHONE)]
    assert original and all(c['papel']==papel for c in original)
    r=executar(tmp_path,cad=cad);row=rows(tmp_path)[1]
    assert row[21]=='titular@example.invalid'and not any(row[11:21])
    assert 'terceiro@example.invalid'not in row and r['resumo']['dividas_efetivamente_geradas']==1


@pytest.mark.parametrize('situacao',['divergente','multiplo','ausente','invalido','conflitante'])
@pytest.mark.parametrize('modo',['A','B'])
def test_segmentacao_nao_supera_politica_a1(tmp_path,situacao,modo):
    financial_name='Pessoa Ficticia Um / Pessoa Ficticia Dois'if situacao=='multiplo'else NOME
    cad_name='Outra Pessoa Ficticia'if situacao=='divergente'else financial_name
    doc=''if situacao=='ausente'else'00000000000'if situacao=='invalido'else CPF
    body=ficha(bloco='A',numero='A00001',nome=cad_name,documento=doc,
        segundo_documento='00000000272'if situacao=='conflitante'else None,
        contatos=['Celular - '+PHONE+' - atualizado em 10/01/2025','E-mail - '+EMAIL+' - alterado em 10/01/2025'])
    fin=financeiro([('A','A00001',financial_name,[recibo('101',31),recibo('102',30)])])
    result=executar(tmp_path,fin,cadastro([body]),mode=modo);table=rows(tmp_path)
    assert result['cadastro_'+PROFILE]['associacoes_retidas']==2
    assert result['resumo']['dividas_efetivamente_geradas']==1
    assert len(table)==2+int(modo=='B')and table[0]==COLUNAS
    assert all(not r[2]and not any(r[11:24])for r in table[1:])


def test_multiplos_contatos_ddd_e_limites_sem_perder_evidencias(tmp_path):
    contacts=[f'Celular - ({11+i}) 91234-5678 - atualizado em 10/01/2025'for i in range(6)]
    contacts += [f'E-mail - pessoa{i}@example.invalid - alterado em 10/01/2025'for i in range(4)]
    cad=fonte(contacts);lote=ler_cad(cad);ev=evidencia(lote)
    titular=next(p for p in ev['participantes']if p['papel']=='titular')
    assert len(titular['telefones'])==6 and len(titular['emails'])==4
    assert any(n.codigo=='CONTATOS_EXCEDENTES_PRESERVADOS'for n in lote.ressalvas)
    assert sum(n.codigo==CONTATO_SEGMENTADO for n in lote.ressalvas)==10
    executar(tmp_path,cad=cad);row=rows(tmp_path)[1]
    assert row[11:21]==tuple(v for i in range(5)for v in(str(11+i),'912345678'))
    assert row[21:24]==tuple(f'pessoa{i}@example.invalid'for i in range(3))


@pytest.mark.parametrize('phone',['0123-4567','91234-5678'])
def test_ddd_ausente_nao_e_inferido(tmp_path,phone):
    executar(tmp_path,cad=fonte(['Celular - '+phone+' - atualizado em 10/01/2025']))
    assert rows(tmp_path)[1][11:13]==(None,phone.replace('-',''))


def test_listas_delimitadas_e_repetidas_mantem_limites_e_deduplicacao():
    r=segmentar_contato('Celular - '+PHONE+'; 0123-4567; '+PHONE+' - atualizado em 10/01/2025')
    assert [(t.ddd,t.numero)for t in r.telefones]==[('11','912345678'),('','01234567')]
    r=segmentar_contato('E-mail - '+EMAIL+'; outra@example.invalid; '+EMAIL+' - alterado em 10/01/2025')
    assert r.emails==(EMAIL,'outra@example.invalid')
    assert PHONE not in repr(r)and EMAIL not in repr(r)


def test_mesmos_numeros_em_blocos_diferentes_nao_cruzam_contatos(tmp_path):
    fin=financeiro([('A','A00001',NOME,[recibo('1')]),('B','B00001',NOME,[recibo('2')])])
    cad=cadastro([ficha(bloco=b,numero=b+'00001',nome=NOME,documento=CPF,
        contatos=[f'E-mail - bloco{b.lower()}@example.invalid - alterado em 10/01/2025'])for b in ('A','B')],total=2)
    executar(tmp_path,fin,cad)
    assert {row[6]:row[21]for row in rows(tmp_path)[1:]}=={
        'BLILHABE-UNIA00001':'blocoa@example.invalid','BLANG-UNIB00001':'blocob@example.invalid'}


def test_cadastro_de_outro_condominio_e_rejeitado(tmp_path):
    with pytest.raises(ErroLeitura):
        executar(tmp_path,cad=cadastro(codigo='3076',nome='OUTRO CONDOMINIO FICTICIO'))


@pytest.mark.parametrize('modo',['A','B'])
def test_alteracao_somente_em_contatos_restricoes_e_financeiro_preservados(tmp_path,modo):
    base=['Celular - '+PHONE,'E-mail - '+EMAIL]
    cadastros=[]
    for annotated in (False,True):
        cells=[c+' - atualizado em 10/01/2025'if annotated else c for c in base]
        body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,contatos=cells)
        body.extend([(24,110,'Bloquear reenvio automático de boletos: Sim'),(216,110,'Recebe carta: Não'),(24,100,'Classificação: Litígio')])
        cadastros.append(cadastro([body]))
    fin=financeiro([('A','A00001',NOME,[recibo('1',31),recibo('2',30)])])
    results=[executar(tmp_path/n,fin,cad,mode=modo)for n,cad in zip(('antes','depois'),cadastros)]
    a,b=[rows(tmp_path/n)for n in ('antes','depois')]
    assert a==b and a[0]==COLUNAS and len(a)==2+int(modo=='B')
    for r in results:
        assert not r['autoriza_cobranca']and not r['permite_exportacao_operacional']
        assert r['cadastro_'+PROFILE]['associacoes_retidas']==0
        assert set(r['cadastro_'+PROFILE]['restricoes_por_codigo'])=={
            'BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO','BPQ_REVISAO_BLOQUEIO_REENVIO','BPQ_REVISAO_NAO_RECEBER_CARTA'}
    assert results[0]['decisoes']==results[1]['decisoes']


def test_continuacao_pdf_preserva_papel_e_origem_do_contato():
    body=ficha(bloco='A',numero='A00001',nome=NOME,documento=CPF,
        contatos=['Celular - '+PHONE+' - atualizado em 10/01/2025','E-mail - '+EMAIL+' - alterado em 10/01/2025'])
    cad=cadastro(dividir(body,2));lote=ler_cad(cad)
    assert lote.pessoas[0].contato.emails==(EMAIL,)
    assert len(evidencia(lote)['cabecalhos'])==2
    assert len({(r.codigo,r.origens)for r in lote.ressalvas if r.codigo==CONTATO_SEGMENTADO})==2
