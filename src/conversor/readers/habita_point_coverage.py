"""Conferência técnica do campo Habita. Não aprova fontes, planos ou cobranças."""
import re
from typing import Literal

from pydantic import Field, model_validator

from conversor.domain.base import Id, Modelo
from conversor.domain.canonical import LoteCanonico, Ocorrencia, Origem
from .real_support import PDFReal
from .text_support import ContextoLeitura, ErroLeitura, id_estavel

CODIGOS = ('A', 'AJ', 'J')
UNIDADE = re.compile(r'^\s*Bloco:\s*(\w+)\s*•\s*Unidade:\s*(\w+)\b')
CABECALHO = re.compile(r'^\s*(\d{8})\s+(.*?)\b(\d{2}/\d{2}/\d{2})\s+')
TOLERANCIA_Y = 0.3


class CampoApontamentoConferido(Modelo):
    boleto_id: Id
    unidade_id: Id
    namespace: Id
    estado: Literal['vazio_validado', 'preenchido_validado', 'inconclusivo']
    codigo: Literal['A', 'AJ', 'J'] | None = None
    motivo_codigo: Id
    origens: tuple[Origem, ...] = Field(min_length=1, repr=False)

    @model_validator(mode='after')
    def codigo_coerente(self):
        if (self.estado == 'preenchido_validado') != (self.codigo is not None):
            raise ValueError('ESTADO_CAMPO_INCOERENTE')
        return self


class ConferenciaApontamentosHabita(Modelo):
    natureza: Literal['conferencia_tecnica_nao_atesto'] = 'conferencia_tecnica_nao_atesto'
    autoriza_exportacao_divida: Literal[False] = False
    atesto_humano: Literal[False] = False
    campos: tuple[CampoApontamentoConferido, ...] = Field(repr=False)

    @model_validator(mode='after')
    def unicos(self):
        if len({c.boleto_id for c in self.campos}) != len(self.campos):
            raise ValueError('COBERTURA_BOLETO_DUPLICADA')
        return self

    def ocorrencias_revisao(self, *, processamento_id: str) -> tuple[Ocorrencia, ...]:
        """Inconclusão é crítico por boleto; não altera o lote ou seus históricos."""
        return tuple(Ocorrencia(
            id=id_estavel('oc_campo_habita', processamento_id, c.boleto_id),
            processamento_id=processamento_id, codigo='APONTAMENTO_LEITURA_INCONCLUSIVA',
            gravidade='critico', escopo='registro', registro_id=c.boleto_id,
            origem=c.origens[0]) for c in self.campos if c.estado == 'inconclusivo')


def conferir_posicao(fragmentos, *, numero: str, vencimento: str):
    """Retorna estado/código/motivo. Falta de âncora nunca comprova campo vazio.

    Fragmentos são (texto, x, y). O intervalo do campo é definido pelos rótulos
    da página e pela linha com número/data. Não há x fixo de condomínio.
    """
    ancoras = []
    for texto, x, y in fragmentos:
        if texto != 'Boleto':
            continue
        datas = [(xx, yy) for t, xx, yy in fragmentos
                 if t == 'Vencimento' and xx > x and abs(yy-y) <= 1]
        emissoes = [(xx, yy) for t, xx, yy in fragmentos
                    if t == 'Emissão' and abs(yy-y) <= 1]
        rotulos = {'Valor', 'Multa', 'Juros', 'Total'}
        if (len(datas) == len(emissoes) == 1 and emissoes[0][0] > datas[0][0]
                and all(any(t == label and xx > datas[0][0] and abs(yy-y) <= 6
                                    for t, xx, yy in fragmentos) for label in rotulos)):
            ancoras.append((x, datas[0][0], emissoes[0][0]))
    if len(ancoras) != 1:
        return 'inconclusivo', None, 'ANCORAS_CAMPO_NAO_COMPROVADAS'
    x_boleto, x_vencimento, x_emissao = ancoras[0]
    linhas = [(x, y) for t, x, y in fragmentos
              if t == numero and abs(x-x_boleto) <= 2
              and any(td == vencimento and x_vencimento <= xd < x_emissao and abs(yd-y) <= TOLERANCIA_Y
                      for td, xd, yd in fragmentos)]
    if len(linhas) != 1:
        return 'inconclusivo', None, 'LINHA_BOLETO_NAO_UNIVOCA'
    x_numero, y = linhas[0]
    interior = [(t, x) for t, x, yy in fragmentos
                if abs(yy-y) <= TOLERANCIA_Y and x_numero < x < x_vencimento]
    if not interior:
        return 'vazio_validado', None, 'INTERVALO_DOCUMENTAL_VAZIO_CONFERIDO'
    if len(interior) == 1 and interior[0][0] in CODIGOS:
        return 'preenchido_validado', interior[0][0], 'CODIGO_NO_CAMPO_PROPRIO'
    return 'inconclusivo', None, 'CONTEUDO_CAMPO_NAO_RECONHECIDO'


def conferir_apontamentos_habita(conteudo: bytes, *, contexto: ContextoLeitura,
                                lote: LoteCanonico) -> ConferenciaApontamentosHabita:
    """Examina todos os cabeçalhos, incluindo continuidades, sem inferir fatos.

    Produz evidência técnica candidata. Não cria CoberturaApontamentos, atesto,
    pacote assinado, plano, decisão financeira ou autorização operacional.
    """
    layout = PDFReal(conteudo, contexto, layout=True)
    coords = PDFReal(conteudo, contexto, coordenadas=True)
    layout.validar_condominio('habita')
    if contexto.leitor_versao != 'habita_composicao_real_v1@1':
        raise ErroLeitura('VERSAO_COBERTURA_NAO_VALIDADA')
    unidades = {u.id: u for u in lote.unidades}
    for u in lote.unidades:
        if (u.condominio_id, u.administradora_id) != (contexto.condominio_id, contexto.administradora_id):
            raise ErroLeitura('CONTEXTO_COBERTURA_DIVERGENTE')
    for b in lote.boletos:
        for o in (*b.origens, *(i.origem for i in b.composicao.itens)):
            if (o.arquivo_id, o.sha256, o.leitor_versao) != (
                    contexto.arquivo_id, layout.hash, contexto.leitor_versao):
                raise ErroLeitura('FONTE_COBERTURA_DIVERGENTE')
    observadas = {}
    unidade = None
    for pagina in layout.paginas:
        for linha in pagina:
            if u := UNIDADE.match(linha.texto):
                unidade = (u[1], u[2])
            if m := CABECALHO.match(linha.texto):
                if unidade is None:
                    raise ErroLeitura('CABECALHO_COBERTURA_SEM_UNIDADE')
                chave = (*unidade, m[1])
                geometria = tuple((l.texto, x, y) for l, x, y in coords.fragmentos[linha.pagina-1])
                estado, codigo, motivo = conferir_posicao(geometria, numero=m[1], vencimento=m[3])
                campo_textual = m[2].strip()
                if ((campo_textual or None) != codigo
                        or campo_textual not in ('', *CODIGOS)):
                    estado, codigo, motivo = 'inconclusivo', None, 'TEXTO_GEOMETRIA_DIVERGENTES'
                observadas.setdefault(chave, []).append((layout.origem(linha), estado, codigo, motivo))
    esperadas = {(unidades[b.unidade_id].bloco_original,
                  unidades[b.unidade_id].unidade_original, b.identificador) for b in lote.boletos}
    if set(observadas) - esperadas:
        raise ErroLeitura('INVENTARIO_COBERTURA_DIVERGENTE')
    campos = []
    for b in lote.boletos:
        u = unidades[b.unidade_id]
        registros = observadas.get((u.bloco_original, u.unidade_original, b.identificador), [])
        estado, codigo, motivo = 'inconclusivo', None, 'CABECALHO_COBERTURA_AUSENTE'
        origens = tuple(r[0] for r in registros) or b.origens
        if registros:
            posicoes = {(i.origem.pagina, i.origem.linha) for i in b.composicao.itens}
            consistent = len({(r[1], r[2]) for r in registros}) == 1
            presentes = tuple((a.codigo_original, a.namespace_formato) for a in b.apontamentos)
            esperado = ((registros[0][2], contexto.formato_id),) if registros[0][2] else ()
            datas_conferem = all(CABECALHO.match(layout.paginas[o.pagina-1][o.linha-1].texto)[3]
                                 == b.vencimento.strftime('%d/%m/%y') for o in origens)
            if (consistent and registros[0][1] != 'inconclusivo'
                    and presentes == esperado and datas_conferem
                    and (origens[0].pagina, origens[0].linha) == (b.origens[0].pagina, b.origens[0].linha)
                    and all((o.pagina, o.linha) in posicoes for o in origens)
                    and all(a.origem == b.composicao.itens[0].origem for a in b.apontamentos)):
                estado, codigo, motivo = registros[0][1:]
            else:
                motivo = 'CAMPO_CONTINUIDADE_OU_CANONICO_INCONCLUSIVO'
        campos.append(CampoApontamentoConferido(boleto_id=b.id, unidade_id=b.unidade_id,
                      namespace=contexto.formato_id, estado=estado, codigo=codigo,
                      motivo_codigo=motivo, origens=origens))
    return ConferenciaApontamentosHabita(campos=tuple(campos))
