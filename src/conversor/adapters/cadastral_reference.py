"""Evidência histórica para retenção protetiva; nunca prefere dados do template."""
from hashlib import sha256
from io import BytesIO
import re

from openpyxl import load_workbook

from conversor.adapters.document_probe import SondadorLocal
from conversor.domain.canonical import Documento, Origem, documento_validado
from conversor.domain.documents import resolver_documento
from conversor.domain.recognition import normalizar_assinatura
from conversor.domain.template import COLUNAS


def confrontar_documentos_historicos(conteudo, *, lote, identificadores, perfil_saida):
    if perfil_saida is None:return ()
    sonda=SondadorLocal().sondar(conteudo,arquivo_id='referencia')
    if sonda.tipo!='xlsx' or sonda.bloqueios or not sonda.completo:return ()
    w=load_workbook(BytesIO(conteudo),read_only=True,data_only=False,keep_links=False)
    try:
        candidatas=[s for s in w if tuple(str(v).strip() for v in next(s.values,())[:30])==COLUNAS]
        if len(candidatas)!=1:return ()
        aba=candidatas[0];rows=list(aba.values)[1:]
        produtos={normalizar_assinatura(str(r[25])) for r in rows if len(r)>=30 and r[25]}
        if produtos!={normalizar_assinatura(perfil_saida.produto)}:return ()
        por_codigo={}
        for uid,c in identificadores.items():
            if c['estado']=='codificado_para_teste':
                por_codigo.setdefault((c['cedente'],c['complemento']),[]).append(uid)
        pessoas={p.unidade_id:p for p in lote.pessoas};conflitos=[]
        for linha,row in enumerate(rows,2):
            if len(row)<30 or normalizar_assinatura(str(row[0] or ''))!=normalizar_assinatura(perfil_saida.nome_cedente):continue
            ids=por_codigo.get((str(row[1] or ''),str(row[6] or '')),())
            if len(ids)!=1:continue
            p=pessoas.get(ids[0])
            if not p or normalizar_assinatura(p.nome)!=normalizar_assinatura(str(row[3] or '')):continue
            atual=resolver_documento(p)
            if atual.bloqueante or not atual.valor:continue
            raw=str(row[2] or '');digits=re.sub(r'\D','',raw)
            historico=documento_validado(Documento(tipo='cnpj' if len(digits)==14 else 'cpf',valor=raw))
            if not historico or historico==atual.valor:continue
            conflitos.append({'unidade_id':p.unidade_id,'nome_historico':row[3],
                'documento_atual':atual.valor,'documento_historico':historico,'documento_historico_original':raw,
                'aba':aba.title,'linha_excel':linha,'origem':Origem(arquivo_id='referencia',
                    sha256=sha256(conteudo).hexdigest(),leitor_versao='documentos_template_historico@1',
                    linha=linha,identificador=f'xlsx_aba{w.sheetnames.index(aba.title)+1}_r{linha}_C').model_dump(mode='json'),
                'limite':'Contradição documental não prova erro, desatualização ou mudança de titularidade; requer decisão humana.'})
        return tuple(conflitos)
    finally:w.close()
