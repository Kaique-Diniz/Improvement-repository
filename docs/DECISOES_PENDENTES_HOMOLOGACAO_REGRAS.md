# Perguntas e decisões antes dos planos reais

Preparação documental, sem respostas presumidas ou aprovação emitida. Responder
no ambiente privado, com responsável, data e evidência. Não colar CPFs, nomes,
contatos, valores de clientes ou credenciais no repositório. Uma resposta ao
levantamento não equivale, sozinha, à aprovação da versão/hash de um plano.

## Decisões comuns aos dois condomínios

| ID | Pergunta objetiva | O que precisa ficar registrado |
|---|---|---|
| Q01 | Quem conferirá cada fonte, consolidará o atesto do conjunto e aprovará as regras? Quem decide titularidade? | Pessoas/funções competentes, escopo da responsabilidade e evidência privada de cada manifestação; o serviço automático não é aprovador humano |
| Q02 | Qual é a versão vigente da régua aplicável a cada condomínio e onde está o extrato autorizado para revisão? | Fonte, versão, hash, trecho pertinente, vigência documental e responsável; remover acesso/credenciais do material de trabalho compartilhável |
| Q03 | Qual data de referência exata será usada e como se conta o prazo em cada condomínio? | Data expressa, dias corridos ou outro critério aprovado, fronteiras e papel do fuso; nunca assumir a data atual |
| Q04 | A partir de quando e até quando cada regra/plano vale? | Início, eventual fim aberto expressamente escolhido, versão e fundamento; período de um PDF não define vigência do plano |
| Q05 | Qual campo financeiro cada condição deve comparar e o que explica o valor da referência? | Total original, componentes ou outro campo comprovado, com definição exata; separar saldo acumulado, descontos e encargos, sem alterar valores para reproduzir a planilha |
| Q06 | Qual é o alcance, a ação e a prioridade numérica de cada uma das oito regras? Como interagem? | Unidade ou boleto, ação exata, prioridades e casos de sobreposição; empates incompatíveis continuam em revisão, sem superar bloqueios críticos |
| Q07 | Quais evidências comprovam apontamento, situação jurídica, garantidora ou outra exceção? | Fonte, significado, namespace quando aplicável, entidade afetada, confirmação e vigência dos fatos; não equiparar termos de formatos diferentes |
| Q08 | Quais fatos/campos são necessários para cada decisão e onde obtê-los quando não constam nos PDFs? | Fonte comprovada adicional ou pendência de revisão; falta, contradição ou ausência de cobertura não vira permissão presumida |
| Q09 | Quais documentos e vigências fundamentarão a revisão das titularidades e dos conflitos documentais FL? | Responsável, vínculo ao titular, fontes e fundamento por caso em dossiê privado; os bloqueios continuam até decisão própria, sem prioridade automática de Cadastro |
| Q10 | A futura comparação exige competência para Habita? Há fonte adicional comprovada que a forneça? | Finalidade e fonte, ou limitação explícita; manter as 769 competências ausentes, sem inferir vencimento, emissão ou descrição |

## TREE MORUMBI

| ID | Pergunta objetiva | Regras relacionadas |
|---|---|---|
| Q11 | Para o boleto de R$ 0,01, qual campo comprova a igualdade exata e quais boletos entram na busca? Inclui futuros, fora do prazo ou com situação especial? | `tree_centavo`; a proposta é igualdade exata, sem arredondamento/tolerância inventados |
| Q12 | A presença desse boleto deve excluir a unidade inteira, todos os seus boletos e também eventual cadastro sem dívida? | Confirmar ação/alcance de `tree_centavo`; se a exclusão terminal de unidade for aprovada, ela não pode ser desfeita por permissão de boleto |
| Q13 | O que significa A, em qual campo/namespace é comprovado, e qual efeito deve produzir? | `tree_apontamento_a`; confirmar unidade/boleto e ação, sem tomar a hipótese histórica por aprovação |
| Q14 | O que significa AJ e como tratá-lo quando coexistir com A ou J? | `tree_apontamento_aj`; confirmar fonte, escopo, efeito e relação com as demais regras |
| Q15 | O que significa J e há evidência de que deva afetar toda a unidade ou somente um boleto? | `tree_apontamento_j`; não transformar J automaticamente em fato jurídico ou aplicar o prazo Plaza |
| Q16 | Confirmam-se o corte candidato estrito `> 30` e sua contagem? Qual ação/escopo ocorre antes, no dia 30 e após o corte? | `tree_prazo_30`; responder aos casos de 29/30/31 dias e à interação com o centavo/apontamentos |

O esclarecimento do subtotal VG é uma decisão de integridade da fonte, separada
dessas seis perguntas de negócio. Aprovar qualquer resposta não libera o lote.

## PLAZA MAYOR IPIRANGA

| ID | Pergunta objetiva | Regras relacionadas |
|---|---|---|
| Q17 | Confirmam-se o corte candidato estrito `> 30` e a contagem? A elegibilidade é por boleto ou depende do conjunto da unidade? | `plaza_prazo_30`; responder a 29/30/31 dias, ação e exceções comprovadas |
| Q18 | O prazo de 60 dias jurídico serve para qual operação: elegibilidade, modalidade, negociação, encaminhamento ou outra? | `plaza_juridico_60`; prazo judicial não significa exclusão ou cobrança automática |
| Q19 | De qual evento começam os 60 dias, qual operador é aplicável e como comprovar o status jurídico e sua vigência? | `plaza_juridico_60`; responder aos casos 59/60/61, sem inferir o marco ou o status por anotação genérica |
| Q20 | Qual regra decide quando o caso jurídico também satisfaz o prazo de 30 dias? | Prioridade/condições de `plaza_juridico_60` e `plaza_prazo_30`, ação e alcance; não criar exceção que contorne segurança |
| Q21 | Cadastro antecipado estará habilitado para Plaza? Qual é seu gatilho e que unidades podem participar? | `plaza_cadastro_antecipado`; esclarecer boletos fora do prazo, unidade com dívida elegível e casos jurídicos/excluídos, mantendo os bloqueios |
| Q22 | Quantas linhas cadastrais por unidade/titular são desejadas e quais campos são indispensáveis? Podem coexistir com dívida? | `plaza_cadastro_antecipado`; separar política de negócio de implementação da saída na Fase 5; não generalizar a exceção do laboratório |

## Critérios de revisão e autorização posterior

| ID | Pergunta objetiva | Evidência esperada |
|---|---|---|
| Q23 | O que cada linha e agrupamento dos Excel pretende representar e quais diferenças o autor reconhece? | Vínculos revisados por unidade/boleto, base financeira, cadastro e data/política da referência; não usar os 132 encontros financeiros como meta a forçar |
| Q24 | Quais casos e resultados explicáveis serão aceitos na futura homologação privada? | Casos de fronteira, apontamentos, centavo, jurídico, cadastro e conflitos; distinguir resultado candidato da decisão final bloqueada e documentar divergências sem remover retenções |
| Q25 | Depois dos atestos e das decisões, qual escopo será expressamente autorizado para iniciar o 4.3B? | Autorização posterior com tarefas/limites; nenhum início automático por completar o formulário ou aceitar esta documentação |
| Q26 | Quem guardará e poderá consultar fontes, fichas, versões, recibos e contexto de reprodução? | Responsável e local privado de retenção/acesso, sem credenciais ou evidências sensíveis no Git |

Questões sobre a correção de identidade já têm evidência técnica: originais,
IDs legados e novos IDs internos foram preservados, com fontes e hashes. Isso
não resolve a titularidade nem torna correta uma fonte documental conflitante.
O objetivo da revisão humana é decidir com essas evidências, sem escolher pelo
ID, pela recência ou pela simples posição da linha.

## Ficha de resposta por regra — preencher somente no ambiente privado

| Campo | Resposta |
|---|---|
| ID da regra e condomínio | A preencher |
| Questões respondidas e alternativas recusadas | A preencher, com fundamento |
| Fonte operacional, versão, hash e trecho | A preencher |
| Condição, operador e campos/fatos necessários | A preencher |
| Escopo e ação | A preencher |
| Prioridade numérica e relação com as demais regras | A preencher; não há valor presumido |
| Início e fim da vigência | A preencher; ausência não significa vigência ilimitada aprovada |
| Tratamento de falta/contradição de evidência | A preencher dentro dos bloqueios gerais já existentes |
| Casos de fronteira e resultados esperados | A preencher |
| Responsável, função, data/hora com fuso e evidência privada | A preencher |
| Situação | Pendente; não é aprovação de plano |

Uma futura configuração de plano exigirá conferir se a decisão cabe nos contratos
4.1/4.2, criar versão própria e obter aprovação autorizada vinculada ao conteúdo
e hash. Nenhuma resposta deve ser transcrita automaticamente de texto livre para
regra ativa. Se faltar decisão essencial, registrar lacuna e manter a revisão.
