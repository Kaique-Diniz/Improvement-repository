# PSM-01 — Esclarecimento cadastral antes da aprovação

Complemento da entrega local do Parque Santa Mônica. O código de produção, o parser, a política A1, os filtros financeiros, os schemas e os perfis anteriores permanecem inalterados nesta verificação. Foram acrescentadas regressões sintéticas e esta documentação. Publicação controlada autorizada junto à PSM-01 para auditoria externa e testes locais, sem merge ou homologação operacional.

## Situação das três referências

A revisão externa retirou **267 casos/38 unidades** dos critérios de aceite: não há script nem critérios suficientes para reproduzi-los. Essa referência é preliminar, não reproduzida e não bloqueadora. Não se alterou nenhum parser, documento ou retenção para alcançá-la.

**142/30 e 92/15 são reproduzíveis, mas medem coisas diferentes.** Ambas usam as 1.663 células preenchidas entre as 2.640 linhas do template histórico, excluindo 977 células vazias. A contagem de unidades é distinta dentro de cada grupo, não o denominador de lançamentos.

| Método | Valor do Excel | Documento do PDF | Divergências / unidades |
| --- | --- | --- | ---: |
| Relatório anterior | `str(valor_da_celula)`, sem normalização de representação nem zeros | Somente titular, em Dados pessoais | 142 / 30 |
| Titular, representação normalizada | Remove pontuação/espaços e converte número integral sem `.0` | Somente titular | 129 / 21 |
| Titular, zeros recompostos para comparação | Também recompõe 11 posições quando o candidato é CPF fiscalmente válido | Somente titular | 125 / 20 |
| Principal técnico comparativo | Mesma normalização e zeros | Titular quando há documento válido; caso contrário, primeiro válido do pagador | 92 / 15 |

A definição que reproduz 92/15 também equivale, nesta fonte, ao primeiro documento fiscalmente válido em ordem de página/linha. Isso descreve uma comparação técnica do PDF; **não comprova que o documento do pagador pertence ao titular financeiro**. Não se atribui ao auditor externo um algoritmo não fornecido: informa-se precisamente a definição que reproduziu sua contagem.

A ponte é exata: **142 − 13 de representação − 4 de zeros − 33 da escolha do papel = 92**. São conjuntos de células distintos nessa sequência, sem novas divergências introduzidas. As 33 células correspondem a cinco unidades cujo titular não tem documento, mas o pagador tem; não se tornam associações pessoais autorizadas por coincidirem com o template.

## Universo e células vazias

As linhas financeiras do template são as 2.338 dívidas elegíveis confirmadas. As 302 cadastrais históricas representam os não elegíveis, com repetições; não são as 207 linhas adicionais do modo B atual.

| Universo histórico | Linhas | CPF preenchido | CPF vazio | Titular normalizado, vazios excluídos | Principal técnico, vazios excluídos |
| --- | ---: | ---: | ---: | ---: | ---: |
| Todas | 2.640 | 1.663 | 977 | 125 / 20 unidades | 92 / 15 unidades |
| Financeiras/elegíveis | 2.338 | 1.395 | 943 | 101 / 11 unidades | 76 / 7 unidades |
| Cadastrais/não elegíveis | 302 | 268 | 34 | 24 / 17 unidades | 16 / 12 unidades |

Lançamentos podem ser somados entre universos disjuntos; unidades não, pois uma unidade pode aparecer nos dois.

| Universo | Titular normalizado, incluindo vazios | Principal técnico, incluindo vazios |
| --- | ---: | ---: |
| Todas | 623 / 48 unidades | 1.069 / 45 unidades |
| Financeiras/elegíveis | 568 / 28 unidades | 1.019 / 26 unidades |
| Cadastrais/não elegíveis | 55 / 38 unidades | 50 / 35 unidades |

Essas contagens incluindo vazios respondem a outra pergunta: também contam o template vazio diante de documento presente no PDF. Não substituem 142/30 ou 92/15. A comparação anterior sem normalização tinha 106 divergências nas linhas financeiras e 36 nas cadastrais, totalizando 142, sempre excluindo vazios.

## Normalização e validade fiscal

O template possui 48 células numéricas de documento. Apenas quatro precisam de zeros à esquerda para representar o CPF de 11 posições; as outras 44 já têm a largura completa. Não há textos compostos somente de dígitos com menos de 11 posições nessa fonte. Há 13 células textuais com pontuação ou espaços internos, explicando a outra diferença de representação. As 1.663 células preenchidas são fiscalmente válidas depois da normalização explicitada.

Para a comparação: valores vazios continuam vazios; booleanos, números não finitos e números fracionários não são documentos válidos. Número integral é convertido sem parte decimal; pontuação fiscal e espaços são removidos. Um CPF curto recebe zeros até 11 posições somente como hipótese de comparação, com verificador fiscal. Não se converte texto arbitrário em documento e não se trunca CNPJ. Esta análise não escreve no template, não preenche o Excel de saída e não altera a atribuição cadastral: a saída continua usando apenas documentos da fonte cadastral, validados e associados segundo A1.

O CPF do titular vem de Dados pessoais, vinculado ao registro/nome do cadastro. O pagador é outro papel. Documentos adicionais e suas origens são mantidos separadamente; conflitos não são resolvidos escolhendo o primeiro. A contagem de principal técnico acima só é usada na auditoria; nesta fonte não há conflito de documentos válidos do titular que a obrigue a escolher entre candidatos.

## Continuidade do PDF

Foram preservados 817 registros com 1.101 cabeçalhos de unidade. Há 284 registros com cabeçalho repetido na continuação, sem criar novas unidades. Entre os documentos lidos, 62 do titular e 125 do pagador estão em páginas posteriores ao primeiro cabeçalho de sua ficha. São contagens de evidências documentais, não de dívidas.

A reunião exige a mesma unidade, cliente, nome e continuidade de página. Um novo registro limpa o estado; uma continuação válida preserva seções, papéis, documentos e origens. O titular canônico recebe apenas evidências do titular. Usar somente a primeira ou a última página muda indevidamente o universo de documentos: por exemplo, com a normalização e principal técnico descritos, a primeira página isolada produziria 162/29 e a última 501/53, em vez de 92/15. Essas variações servem para demonstrar a importância da reunião; não são usadas pelo conversor.

As novas regressões provam titular sem CPF e pagador válido na mesma página e em continuação, CPF do titular somente na segunda página, e documentos adicionais conflitantes em páginas distintas. Não se perde documento nem se atribui o pagador ao titular para obter uma contagem menor.

## As 530 retenções

As 239 unidades financeiras existem no PDF. A concordância nominal de 233 unidades não é, isoladamente, prova suficiente para atribuir documento e contatos.

| Motivo primário, conforme prioridade A1 | Código mantido | Unidades | Lançamentos totais | Elegíveis | Não elegíveis |
| --- | --- | ---: | ---: | ---: | ---: |
| Nome financeiro e cadastro divergentes | PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO | 6 | 10 | 5 | 5 |
| Responsáveis múltiplos sem vínculo individual suficiente | PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO | 6 | 8 | 1 | 7 |
| Titular sem documento; documento válido somente do pagador | OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA | 7 | 512 | 501 | 11 |
| **Total** | | **19** | **530** | **507** | **23** |

São motivos primários mutuamente exclusivos, não uma contagem de todos os possíveis sinais coexistentes. Não representam 530 pessoas ou documentos distintos: representam associações por lançamento. As unidades destes grupos são disjuntas na fonte. As outras 220 unidades têm 2.110 associações aceitas no lote total; toda associação aceita possui documento válido.

| Categoria solicitada | Lançamentos retidos por esse motivo primário |
| --- | ---: |
| Nome divergente | 10 |
| Nome múltiplo | 8 |
| Documento conflitante | 0 |
| Documento fiscalmente inválido | 0 |
| Ausência de cadastro | 0 |
| Ausência de documento do titular, com pagador válido | 512 |
| Ambiguidade de extração identificada | 0 |

Nas sete unidades do grupo de 512, a evidência original mostra explicitamente CPF vazio em Dados pessoais e documento preenchido em Dados do pagador. Não é ausência de documento no PDF inteiro nem falha de reunir páginas. Quatro dessas fichas têm continuidade e três estão em uma página; em todas, os papéis foram preservados. O código existente cobre ausência ou invalidade do titular; nesta fonte a causa efetiva é ausência, não invalidade.

Todos os **530** lançamentos retidos possuem algum documento fiscalmente válido no PDF, mas sem associação pessoal suficiente ao responsável financeiro: nos 18 casos de nome/multiplicidade ele está no papel de titular; nos 512 restantes está somente em outro papel, o pagador. Entre elegíveis, são seis no primeiro grupo e 501 no segundo. Não se autoriza associação porque o documento existe em algum lugar da unidade ou coincide com o template.

A conferência confirmou documento, telefones e e-mails pessoais vazios nas associações retidas. Evidências de origem permanecem temporariamente preservadas e as dívidas não são excluídas. Não foi encontrado erro efetivo no parser ou razão para flexibilizar A1; o ajuste necessário é tornar explícitas as definições do relatório comparativo.

## Financeiro, validação e limites

O código de produção continua byte a byte igual ao estado anterior à verificação cadastral, incluindo leitor OMA, regra >60, exportador, configuração de 30 campos, hashes e modo B. Os perfis anteriores não foram modificados. A entrega da auditoria acompanha testes e nova conferência financeira anonimizada do fluxo efêmero.

A referência 267/38 foi formalmente retirada dos critérios de aceite. Permanecem a revisão externa, a confirmação operacional da inclusividade/vigência dos 60 dias e as limitações já documentadas do MVP. Não há autorização de cobrança, CRM ou exportação operacional. A publicação ocorre exclusivamente na branch PSM-01, sem merge, criação de PR ou alteração da INT-01, main e demais branches/PRs existentes.
