from conversor.domain.canonical import Contato, Endereco, EvidenciaDocumento, LoteCanonico, Ocorrencia, Pessoa, RessalvaLeitura, documento_validado
from conversor.domain.documents import CONTATO_UNIDADE, evidencias_documento, resolver_documento
from conversor.domain.identity import nomes_compativeis, nomes_do_registro
from .documents import ocorrencias_documentais
from conversor.readers.text_support import ErroLeitura, id_estavel


def complementar_cadastro(lote: LoteCanonico, cadastro: dict, endereco_perfil: Endereco, *,
                         politica_titular="bloquear", processamento_id=None, alertas=None) -> LoteCanonico:
    """O cruzamento estrutural usa cadastro_por_unidade; modos legados conservam replay."""
    if politica_titular not in ("bloquear", "cadastro_confirmado_no_laboratorio", "cadastro_por_unidade"):
        raise ErroLeitura("POLITICA_DE_TITULAR_INVALIDA")
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    if len(pessoas) != len(lote.pessoas):
        raise ErroLeitura("TITULAR_AMBIGUO")
    ressalvas = list(lote.ressalvas)
    for unidade in lote.unidades:
        chave = (unidade.condominio_id, unidade.bloco_original, unidade.unidade_original)
        origem = pessoas[unidade.id]
        pessoa = cadastro.get(chave)
        if pessoa is not None:
            if pessoa.unidade_id != unidade.id:
                raise ErroLeitura('CADASTRO_DE_OUTRA_UNIDADE')
            preferir_cadastro = politica_titular == 'cadastro_por_unidade'
            if preferir_cadastro:
                pessoa = Pessoa.model_validate(pessoa.model_dump() | {'relacao_unidade': CONTATO_UNIDADE})
                if origem.nome.strip().casefold() != pessoa.nome.strip().casefold():
                    ressalvas.append(RessalvaLeitura(codigo='DIVERGENCIA_NOME_ENTRE_FONTES',gravidade='informativo',
                        registro_id=unidade.id,origens=(origem.origem,pessoa.origem),
                        valores_originais=(origem.nome,pessoa.nome)))
            por_unidade = pessoa.relacao_unidade == CONTATO_UNIDADE
            compativeis = por_unidade and nomes_compativeis(origem.nome, pessoa.nome)
            if origem.nome.strip().casefold() != pessoa.nome.strip().casefold() and not compativeis and not preferir_cadastro:
                if politica_titular != "cadastro_confirmado_no_laboratorio":
                    raise ErroLeitura("TITULAR_DIVERGENTE", pagina=pessoa.origem.pagina, linha=pessoa.origem.linha)
                if processamento_id is None or alertas is None:
                    raise ErroLeitura("RESOLUCAO_DE_TITULAR_EXIGE_AUDITORIA")
                alertas.append(Ocorrencia(id=id_estavel("oc_titular", processamento_id, unidade.id),
                    processamento_id=processamento_id, codigo="TITULAR_DIVERGENTE_RESOLVIDO_NO_LAB", gravidade="alerta",
                    escopo="registro", registro_id=unidade.id, origem=pessoa.origem))
            # O cadastro da unidade não afirma titularidade individual. Vínculos
            # expressamente atribuídos a outro registro não são apagados.
            mesmo_titular = (origem.id == pessoa.id and origem.nome.strip().casefold() == pessoa.nome.strip().casefold())
            fontes = list(evidencias_documento(pessoa))
            for fonte in evidencias_documento(origem):
                titular = (None if fonte.titular_id in (None, origem.id) else fonte.titular_id) if por_unidade else (
                    pessoa.id if mesmo_titular and fonte.titular_id == origem.id else None)
                vinculada = EvidenciaDocumento(documento=fonte.documento, origem=fonte.origem,
                    titular_id=titular)
                if vinculada not in fontes:
                    fontes.append(vinculada)
            # Retém todos os nomes completos expressos, nunca uma pessoa por nome.
            nome = (origem.nome if (preferir_cadastro and not pessoa.nome.strip()) or
                    (not preferir_cadastro and compativeis and nomes_do_registro(pessoa.nome) < nomes_do_registro(origem.nome))
                    else pessoa.nome)
            if preferir_cadastro:
                # Cadastro preferencial; ausências só recebem dados comprovados
                # da mesma unidade. Não atribui documento a pessoa individual.
                contato = Contato.model_validate(pessoa.contato.model_dump() | {
                    'telefones': pessoa.contato.telefones or origem.contato.telefones,
                    'emails': pessoa.contato.emails or origem.contato.emails,
                    'endereco': pessoa.contato.endereco if pessoa.contato.endereco != Endereco() else origem.contato.endereco,
                    'origem': pessoa.contato.origem or origem.contato.origem})
                if contato != pessoa.contato and origem.contato.origem:
                    ressalvas.append(RessalvaLeitura(codigo='CONTATO_COMPLEMENTADO_DA_INADIMPLENCIA',gravidade='informativo',
                        registro_id=unidade.id,origens=tuple(o for o in (pessoa.contato.origem,origem.contato.origem)if o)))
                pessoa = Pessoa.model_validate(pessoa.model_dump() | {'contato': contato})
            pessoa = Pessoa.model_validate(pessoa.model_dump() | {"nome": nome, "documento": None, "documento_origem": None,
                                                                 "evidencias_documentais": tuple(fontes)})
            resolucao = resolver_documento(pessoa)
            if resolucao.valor:
                fonte = next(f for f in fontes if documento_validado(f.documento) == resolucao.valor)
                pessoa = Pessoa.model_validate(pessoa.model_dump() | {"documento": fonte.documento, "documento_origem": fonte.origem})
            if alertas is not None and processamento_id is not None:
                for alerta in ocorrencias_documentais(pessoa, processamento_id=processamento_id):
                    if alerta.codigo != "DOCUMENTO_AUSENTE" and alerta not in alertas:
                        alertas.append(alerta)
            origem = pessoa
        # Só preenche ausências com perfil explícito; não sobrepõe endereço da fonte.
        endereco = Endereco.model_validate({campo: getattr(origem.contato.endereco, campo) or getattr(endereco_perfil, campo)
                                           for campo in Endereco.model_fields})
        contato = Contato.model_validate(origem.contato.model_dump() | {"endereco": endereco})
        pessoas[unidade.id] = Pessoa.model_validate(origem.model_dump() | {"contato": contato})
    return LoteCanonico(unidades=lote.unidades, boletos=lote.boletos, pessoas=tuple(pessoas[u.id] for u in lote.unidades),
                        ressalvas=tuple(ressalvas))
