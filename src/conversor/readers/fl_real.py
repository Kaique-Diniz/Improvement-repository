"""FL W002A: componentes assinados e saldo por unidade; continuidade contextual."""
import json
import re

from conversor.domain.canonical import RessalvaLeitura

from .real_support import AcervoReal, Bilhete, MOEDA, PDFReal, ZERO, data_real, falhar
from .text_support import LinhaFonte, VALOR_BRL, dinheiro_brl

UNIDADE=re.compile(r'^(\d{4})\s+TORRE\s+(\w+)\s*-\s*(.+)$')
INICIO=re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{4})\s+(\d+)\s+(.*)$')
CAUDA=re.compile(r'('+VALOR_BRL+r')\s+('+VALOR_BRL+r')\s*$')
NOTIFICACAO = r'\d+\s*(?:[º°ª]|[oa]\.?)\s+Notifica[cç][aã]o'
MARCADOR = re.compile(r'(?:'+NOTIFICACAO+r'|Jur[ií]dico)', re.I)
# "Jurídico" exige fragmento independente na coluna administrativa. Não usar
# como sufixo textual genérico: pode integrar legitimamente o nome de empresa.
SUFIXO_ADMINISTRATIVO = re.compile(r'(.+?)\s+('+NOTIFICACAO+r')$', re.I)


def nome_do_cabecalho(fonte, pagina, unidade):
    """Só o cabeçalho de unidade; não modifica descrições ou notas financeiras."""
    candidatos = [(linha,x,y,m) for linha,x,y in fonte.fragmentos[pagina-1]
                  if (m := UNIDADE.fullmatch(linha.texto.strip())) and (m[1],m[2]) == (unidade[1],unidade[2])]
    if len(candidatos) > 1:
        falhar('CABECALHO_UNIDADE_AMBIGUO')
    nome = unidade[3].strip()
    marcadores = []
    if candidatos:
        linha,x,y,m = candidatos[0]
        separados = [(l,xx,yy) for l,xx,yy in fonte.fragmentos[pagina-1]
                     if abs(yy-y) < 1 and 450 <= xx < 600 and xx > x and MARCADOR.fullmatch(l.texto.strip())]
        if separados:
            base = m[3].strip()
            combinado = ' '.join([base] + [l.texto.strip() for l,_,_ in separados])
            if ' '.join(nome.split()) not in {' '.join(base.split()), ' '.join(combinado.split())}:
                falhar('CABECALHO_UNIDADE_AMBIGUO',linha)
            nome = base
            marcadores = separados
        elif sufixo := SUFIXO_ADMINISTRATIVO.fullmatch(nome):
            nome = sufixo[1].strip()
            marcadores = [(LinhaFonte(linha.pagina,linha.numero,sufixo[2]),x,y)]
    return nome, marcadores


class LeitorFLReal:
    formato_id='fl_composicao_real_v1'

    def ler(self,conteudo,*,contexto):
        fonte=PDFReal(conteudo,contexto,coordenadas=True);fonte.validar_condominio('fl')
        acc=AcervoReal(fonte);atual=None;ativo=None;saldos={};pendente=[];item_pendente=False;notas=False;fechado=False
        marcadores_cabecalho = set()
        for pi,page in enumerate(fonte.paginas,1):
            footer=fonte.rodape_validado(pi)
            for linha in page:
                s=linha.texto.strip()
                if not s:continue
                if s in footer:continue
                resumo=re.fullmatch(r'(\d+)\s+unidades inadimplentes\s+\([\d.,]+%\)\s+('+VALOR_BRL+')',s,re.I)
                if resumo:
                    if fechado or item_pendente:falhar('FECHAMENTO_DE_RELATORIO_INVALIDO',linha)
                    total=dinheiro_brl(resumo[2])
                    original=sum((b.totais()[0]for b in acc.boletos.values()),ZERO)
                    if int(resumo[1])!=len(acc.unidades):falhar('CONTAGEM_DE_UNIDADES_DIVERGENTE',linha)
                    if sum(saldos.values(),ZERO)!=total or original!=total:falhar('SOMA_GERAL_INCONSISTENTE',linha)
                    fechado=True;continue
                if fechado:falhar('CONTEUDO_APOS_FECHAMENTO',linha)
                if m:=UNIDADE.fullmatch(s):
                    if item_pendente:falhar('COMPOSICAO_INCOMPLETA',linha)
                    nome,marcadores = nome_do_cabecalho(fonte,pi,m)
                    atual=acc.unidade(m[2],m[1],nome,linha)
                    marcadores_cabecalho = {(pi,l.texto.strip()) for l,_,_ in marcadores}
                    for l,x,y in marcadores:
                        origem = fonte.origem(l).model_copy(update={
                            'identificador':f'fl_cabecalho_fragmento_p{pi}_l{l.numero}'})
                        acc.ressalvas.append(RessalvaLeitura(codigo='MARCADOR_ADMINISTRATIVO_NO_CABECALHO',
                            gravidade='informativo',registro_id=atual.id,origens=(fonte.origem(linha),origem),
                            valores_originais=(linha.texto,l.texto,json.dumps({'x':x,'y':y,'namespace':'fragmentos_pdf'}))))
                    if atual.id in saldos:falhar('UNIDADE_REPETIDA_NAO_RECONCILIADA',linha)
                    ativo=None;pendente=[];notas=False;continue
                if ativo is None and (pi,s) in marcadores_cabecalho:
                    continue
                if m:=INICIO.fullmatch(s):
                    if atual is None:falhar('BOLETO_SEM_UNIDADE',linha)
                    if item_pendente:falhar('COMPOSICAO_INCOMPLETA',linha)
                    key=(atual.id,m[3])
                    if key in acc.boletos:falhar('DUPLICIDADE_NAO_RECONCILIADA',linha)
                    mes,ano=m[2].split('/')
                    ativo=Bilhete(atual,m[3],data_real(m[1],linha),ano+'-'+mes,acrescimos_informados=False)
                    acc.boletos[key]=ativo;pendente=[];s=m[4];item_pendente=True;notas=False
                elif re.match(r'^\d{2}/\d{2}/\d{2}',s):
                    # Datas de exclusão/notas ficam em linha própria, não são boletos.
                    if re.match(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{4}',s):falhar('CABECALHO_BOLETO_INVALIDO',linha)
                    if not notas and ativo is not None:
                        if item_pendente:pendente.append(linha)
                        else:ativo.continuar_descricao(linha,fonte)
                    continue
                elif re.search(r'^Data\s+(?:Hora|Exclusão)|^Data\b.*\bMotivo\b',s,re.I):
                    if item_pendente:falhar('COMPOSICAO_INCOMPLETA',linha)
                    notas=True;continue
                elif re.search(r'^Emitido em|^W002A|^Posição em|^Inadimplência com|^Venc\.',s):
                    continue
                if notas:
                    if MOEDA.search(s):
                        if CAUDA.search(s):falhar('VALOR_FINANCEIRO_EM_NOTA_AMBIGUA',linha)
                        acc.ressalva('NOTA_ADMINISTRATIVA_COM_VALOR',linha,unidade=atual,valores=(s,),gravidade='informativo')
                    continue
                tail=CAUDA.search(s)
                if tail:
                    if tail.start()>0 and s[tail.start()-1]in '0123456789.,':falhar('VALOR_MONETARIO_AMBIGUO',linha)
                    if ativo is None:falhar('COMPOSICAO_SEM_BOLETO',linha)
                    a,b=map(dinheiro_brl,tail.groups())
                    anterior=saldos.get(atual.id,ZERO)
                    if anterior+a!=b:falhar('SALDO_ACUMULADO_INCONSISTENTE',linha)
                    descricao=' '.join([l.texto.strip()for l in pendente]+[s[:tail.start()].strip()]).strip()
                    if not descricao:falhar('COMPOSICAO_SEM_DESCRICAO',linha)
                    ativo.adicionar((a,ZERO,ZERO,ZERO,a),descricao,linha,fonte)
                    ativo.origens_suplementares.extend(fonte.origem(l)for l in pendente)
                    ativo.saldo=b;saldos[atual.id]=b;pendente=[];item_pendente=False
                else:
                    if re.search(VALOR_BRL+r'\s*$',s):
                        descricao_geometrica=any(l.texto.strip()==s and 230<=x<400
                            for l,x,y in fonte.fragmentos[pi-1])
                        if not descricao_geometrica:falhar('LINHA_FINANCEIRA_NAO_RECONHECIDA',linha)
                    if ativo is not None:
                        if item_pendente or linha.texto.startswith(' '):
                            pendente.append(LinhaFonte(linha.pagina,linha.numero,s));item_pendente=True
                        else:ativo.continuar_descricao(linha,fonte)
        if item_pendente:falhar('COMPOSICAO_INCOMPLETA')
        if not fechado:falhar('TOTAL_GERAL_AUSENTE')
        if not acc.boletos:falhar('RELATORIO_SEM_BOLETOS')
        return acc.resultado()
