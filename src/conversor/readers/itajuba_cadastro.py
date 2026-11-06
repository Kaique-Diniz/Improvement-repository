"""Cadastro BN Planner: identidade externa confiável, tabela sem inferências."""
from hashlib import sha256
from io import BytesIO
import json
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Contato, EvidenciaDocumento, LoteCanonico, Origem, Pessoa, RessalvaLeitura
from .itajuba_pdf import unidade
from .passaredo_cadastro import EMAIL_VALIDO, extrair_telefones, normalizar_documento
from .text_support import ErroLeitura, id_estavel

FORMATO='itajuba_cadastro_xlsx_v1'
CABECALHO=('Quadra','Lote','Proprietário','CPF/CNPJ','Telefone','Celular','e-mail','Inad Prop')
TITULO='Lista de Proprietários - Boletos Emissão Administradora'


class LeitorCadastroItajuba:
    formato_id=FORMATO

    def ler(self,conteudo,*,contexto):
        if(contexto.administradora_id,contexto.condominio_id)!=('bn_planner','condominio_itajuba'):
            raise ErroLeitura('ITAJUBA_CADASTRO_CONTEXTO_DIVERGENTE')
        probe=SondadorLocal().sondar(conteudo,arquivo_id='verificacao_cadastro_itajuba')
        if probe.tipo!='xlsx' or probe.bloqueios or not probe.completo:
            raise ErroLeitura('ITAJUBA_CADASTRO_NAO_EXTRAIVEL')
        book=load_workbook(BytesIO(conteudo),data_only=False,keep_links=False)
        try:
            if book.sheetnames!=['Sheet1'] or book.active.max_column!=8:
                raise ErroLeitura('ITAJUBA_CADASTRO_ABA_OU_COLUNAS_INVALIDAS')
            s=book.active
            if any(c.data_type=='f'for row in s for c in row):raise ErroLeitura('ITAJUBA_CADASTRO_FORMULA_NAO_SUPORTADA')
            if s['A1'].value!=TITULO or any(c.value is not None for c in s[1][1:])or tuple(c.value for c in s[2])!=CABECALHO:
                raise ErroLeitura('ITAJUBA_CADASTRO_CABECALHO_INVALIDO')
            digest=sha256(conteudo).hexdigest();units=[];people=[];notes=[];seen=set()
            for row in s.iter_rows(min_row=3):
                values=tuple(c.value for c in row);n=row[0].row
                if all(v is None or v==''for v in values):continue
                text=tuple(''if v is None else str(v).strip()for v in values)
                if not text[2]:raise ErroLeitura('ITAJUBA_CADASTRO_RESPONSAVEL_AUSENTE',linha=n)
                origin=Origem(arquivo_id=contexto.arquivo_id,sha256=digest,leitor_versao=contexto.leitor_versao or FORMATO+'@1',
                    linha=n,identificador=f'Sheet1_A_H_{n}')
                u=unidade(text[0],text[1],contexto,origin)
                if u.id in seen:raise ErroLeitura('ITAJUBA_CADASTRO_UNIDADE_DUPLICADA',linha=n)
                seen.add(u.id);units.append(u)
                pid=id_estavel('cadastro_itajuba',u.id,text[2]);doc=normalizar_documento(values[3])
                doc_origin=origin.model_copy(update={'identificador':f'Sheet1_D{n}'})
                phones=[]
                for field in text[4:6]:
                    parsed=extrair_telefones(field)
                    for phone in parsed:
                        if phone not in phones:phones.append(phone)
                    if field and not parsed:
                        notes.append(RessalvaLeitura(codigo='ITAJUBA_TELEFONE_INVALIDO_NAO_ATRIBUIDO',registro_id=u.id,
                            origens=(origin,),valores_originais=(field,)))
                tokens=[v for v in re.split(r'[;,\s]+',text[6])if v]
                emails=tuple(dict.fromkeys(v.lower()for v in tokens)) if all(EMAIL_VALIDO.fullmatch(v)for v in tokens)else ()
                if text[6]and not emails:
                    notes.append(RessalvaLeitura(codigo='ITAJUBA_EMAIL_INVALIDO_NAO_ATRIBUIDO',registro_id=u.id,
                        origens=(origin,),valores_originais=(text[6],)))
                people.append(Pessoa(id=pid,unidade_id=u.id,nome=text[2],documento=doc,documento_origem=doc_origin if doc else None,
                    evidencias_documentais=(EvidenciaDocumento(documento=doc,origem=doc_origin,titular_id=pid),)if doc else (),
                    contato=Contato(telefones=tuple(phones[:5]),emails=emails[:3]),relacao_unidade='proprietario_cadastrado',origem=origin))
                notes.append(RessalvaLeitura(codigo='ITAJUBA_CADASTRO_ORIGINAL',gravidade='informativo',registro_id=u.id,
                    origens=(origin,),valores_originais=(json.dumps(dict(zip(CABECALHO,values)),ensure_ascii=False,default=str),)))
                if text[3]and doc is None:
                    notes.append(RessalvaLeitura(codigo='ITAJUBA_DOCUMENTO_INVALIDO_NAO_ATRIBUIDO',registro_id=u.id,
                        origens=(doc_origin,),valores_originais=(text[3],)))
            if not units:raise ErroLeitura('ITAJUBA_CADASTRO_VAZIO')
            return LoteCanonico(unidades=tuple(units),pessoas=tuple(people),boletos=(),ressalvas=tuple(notes))
        finally:book.close()
