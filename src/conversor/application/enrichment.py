from conversor.domain.canonical import Contato, Endereco, EvidenciaDocumento, LoteCanonico, Ocorrencia, Pessoa, documento_validado
from conversor.domain.documents import CONTATO_UNIDADE, evidencias_documento, resolver_documento
from conversor.domain.identity import nomes_compativeis, nomes_do_registro
from .documents import ocorrencias_documentais
from conversor.readers.text_support import ErroLeitura, id_estavel


def complementar_cadastro(lote: LoteCanonico, cadastro: dict, endereco_perfil: Endereco, *,
                         politica_titular="bloquear", processamento_id=None, alertas=None) -> LoteCanonico:
    if politica_titular not in ("bloquear", "cadastro_confirmado_no_laboratorio"):
        raise ErroLeitura("POLITICA_DE_TITULAR_INVALIDA")
    pessoas = {p.unidade_id: p for p in lote.pessoas}
    if len(pessoas) != len(lote.pessoas):
        raise ErroLeitura("TITULAR_AMBIGUO")
    for unidade in lote.unidades:
        chave = (unidade.condominio_id, unidade.bloco_original, unidade.unidade_original)
        origem = pessoas[unidade.id]
        pessoa = cadastro.get(chave)
        if pessoa is not None:
            if pessoa.unidade_id != unidade.id:
                raise ErroLeitura('CADASTRO_DE_OUTRA_UNIDADE')
            por_unidade = pessoa.relacao_unidade == CONTATO_UNIDADE
            compativeis = por_unidade and nomes_compativeis(origem.nome, pessoa.nome)
            if origem.nome.strip().casefold() != pessoa.nome.strip().casefold() and not compativeis:
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
            nome = (origem.nome if compativeis and nomes_do_registro(pessoa.nome) < nomes_do_registro(origem.nome)
                    else pessoa.nome)
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
                        ressalvas=lote.ressalvas)
