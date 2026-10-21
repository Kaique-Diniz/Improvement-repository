from conversor.domain.canonical import Contato, Endereco, LoteCanonico, Ocorrencia, Pessoa
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
            if origem.nome.strip().casefold() != pessoa.nome.strip().casefold():
                if politica_titular != "cadastro_confirmado_no_laboratorio":
                    raise ErroLeitura("TITULAR_DIVERGENTE", pagina=pessoa.origem.pagina, linha=pessoa.origem.linha)
                if processamento_id is None or alertas is None:
                    raise ErroLeitura("RESOLUCAO_DE_TITULAR_EXIGE_AUDITORIA")
                alertas.append(Ocorrencia(id=id_estavel("oc_titular", processamento_id, unidade.id),
                    processamento_id=processamento_id, codigo="TITULAR_DIVERGENTE_RESOLVIDO_NO_LAB", gravidade="alerta",
                    escopo="registro", registro_id=unidade.id, origem=pessoa.origem))
            elif pessoa.documento is None:
                # Só preserva documento anterior se é a mesma pessoa; nunca entre titulares divergentes.
                pessoa = Pessoa.model_validate(pessoa.model_dump() | {"documento": origem.documento})
            origem = pessoa
        # Só preenche ausências com perfil explícito; não sobrepõe endereço da fonte.
        endereco = Endereco.model_validate({campo: getattr(origem.contato.endereco, campo) or getattr(endereco_perfil, campo)
                                           for campo in Endereco.model_fields})
        contato = Contato.model_validate(origem.contato.model_dump() | {"endereco": endereco})
        pessoas[unidade.id] = Pessoa.model_validate(origem.model_dump() | {"contato": contato})
    return LoteCanonico(unidades=lote.unidades, boletos=lote.boletos, pessoas=tuple(pessoas[u.id] for u in lote.unidades))
