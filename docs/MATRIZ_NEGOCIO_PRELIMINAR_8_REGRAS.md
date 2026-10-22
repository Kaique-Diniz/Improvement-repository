# Oito propostas de regra para revisão do negócio

**Situação de todas as linhas: pendente de aprovação humana.** Esta matriz é
documental e não executável. Reexpressa os mesmos oito IDs de
[`matriz_preliminar_4_3A.json`](../examples/fase4/matriz_preliminar_4_3A.json),
sem alterar o JSON, criar planos ou aprovar interpretações históricas.

Evidência disponível nesta matriz: solicitação de levantamento do 4.3A. Cada
regra ainda precisa de vínculo à fonte operacional vigente revisada pelo
responsável. Nome do condomínio, histórico de conversa e Excel de referência
isolado não substituem esse vínculo.

## O que já pertence ao motor geral

Estas proteções gerais foram implementadas e aceitas tecnicamente. Não são oito
regras adicionais da régua nem podem ser anuladas por prioridade de condomínio.

| Proteção geral | Consequência para a decisão de negócio |
|---|---|
| Plano versionado, aprovação válida e vínculo com hash, vigência e estado administrativo | Estar ativo ou editar o JSON não basta; ausência de regra aprovada não autoriza cobrança |
| Data de referência explícita e entrada completa verificada | Não usar a data atual por omissão nem simular com fonte/bloqueio omitido |
| Bloqueios críticos preservados | Habita/VG, titularidade e documentos FL continuam retidos mesmo diante de regra permissiva |
| Escopos distintos | Excluir/bloquear terminalmente a unidade prevalece sobre seus boletos; permissão genérica da unidade não libera cada boleto |
| Prioridade e conflito | Maior prioridade numérica prevalece onde permitido; empate incompatível exige revisão; prioridade não supera segurança |
| Resolução conservadora atual | Regra verdadeira de bloquear retém o escopo mesmo diante de permissão de prioridade maior; `adiar` e indeterminações relevantes mantêm revisão, sem presumir agenda ou elegibilidade |
| Evidência insuficiente ou contraditória | Não presumir condição falsa/verdadeira nem selecionar a fonte mais recente automaticamente; resultado seguro de revisão/bloqueio |
| Valores, competência e cadastro | Não recalcular valores ou inferir competência; CPF/CNPJ válido como texto; ausente/inválido vazio + alerta, conflito retido |
| Simulação não operacional | Decisão explicada não é autorização de envio, exportação ou importação no easyCollector |

## Como ler prioridade, vigência e ação

**Prioridade proposta: ainda não definida para nenhuma das oito regras.** Nenhum
número ou ordenação particular foi proposto como regra pronta. A discussão de
precedência aparece abaixo e deve ser respondida pelo responsável. A precedência
de bloqueios e exclusões terminais já descrita é restrição geral do motor, não
uma prioridade financeira inventada.

**Vigência: início e fim pendentes em todas as linhas.** O período dos documentos
ou a data desta preparação não se torna vigência do plano. Cada aprovação futura
deverá identificar versão, período, responsável, fundamento e evidência.

`>` significa estritamente maior: no candidato de 30 dias, exatamente 30 não
satisfaz a condição. Isso descreve a proposta recebida, sem ativá-la. Para os 60
dias jurídicos, nem o operador nem o marco inicial estão confirmados.

## TREE MORUMBI — cinco propostas particulares

| ID | Condição e operador candidato | Escopo / ação preliminar | Prioridade proposta e discussão | Vigência | Decisões em aberto |
|---|---|---|---|---|---|
| `tree_centavo` | Existir boleto de R$ 0,01; igualdade exata. Campo financeiro a confirmar | Unidade inteira / excluir, como proposta de levantamento | Não definida. Se a exclusão de unidade for aprovada, sua precedência terminal já decorre do motor | Pendente | Qual campo contém o centavo? Examinar todos os boletos, inclusive fora do prazo? Efeito cadastral? Q05, Q11–Q12 |
| `tree_apontamento_a` | Código A na fonte; igualdade, com namespace ainda não confirmado | A confirmar. Histórico sugere exclusão da unidade, ainda sem aprovação operacional | Não definida. Discutir coexistência com AJ/J e prazo | Pendente | Significado, fonte/namespace, escopo e efeito de A. Q06–Q07, Q13 |
| `tree_apontamento_aj` | Código AJ na fonte; igualdade, com namespace ainda não confirmado | A confirmar. Hipótese histórica de exclusão não é regra ativa | Não definida. Discutir combinação com A/J sem presumir que são equivalentes | Pendente | Significado, fonte/namespace, escopo e efeito de AJ. Q06–Q07, Q14 |
| `tree_apontamento_j` | Código J na fonte; igualdade, com namespace ainda não confirmado | A confirmar. Não converter J automaticamente em status jurídico | Não definida. Discutir relação com prazo e demais apontamentos | Pendente | Significado de J, prova do efeito e alcance por unidade/boleto. Q07, Q15 |
| `tree_prazo_30` | Atraso superior a 30 dias em relação à data escolhida; `> 30` candidato | Escopo e ação a confirmar; não liberar toda a unidade por esse critério | Não definida. Discutir efeito das exclusões e situações especiais | Pendente | Contagem, fronteiras 29/30/31, referência, escopo e ação. Q03–Q06, Q16 |

Não criar competência para os 769 boletos Habita. O bloqueio do lote VG continua
superior às cinco propostas, inclusive se o negócio aprovar alguma delas depois.

## PLAZA MAYOR IPIRANGA — três propostas particulares

| ID | Condição e operador candidato | Escopo / ação preliminar | Prioridade proposta e discussão | Vigência | Decisões em aberto |
|---|---|---|---|---|---|
| `plaza_prazo_30` | Atraso superior a 30 dias; `> 30` candidato, com referência explícita | Escopo e ação a confirmar | Não definida. Decidir interação com o jurídico e cadastro antecipado | Pendente | Contagem, corte, efeito e exceções documentadas. Q03–Q06, Q17 |
| `plaza_juridico_60` | Situação jurídica comprovada e prazo de 60 dias; operador e marco inicial pendentes | A confirmar; prazo judicial não significa exclusão automática | Não definida. Resolver relação com a regra de 30 dias e eventuais empates | Pendente | O que é caso jurídico? Prazo para qual operação? `>` ou `>=`? A partir de quando? Q07–Q08, Q18–Q20 |
| `plaza_cadastro_antecipado` | Condição de cadastro antecipado ainda a definir por configuração aprovada | A confirmar: separar decisão cadastral de elegibilidade de boleto e geração de linha Excel | Não definida. Decidir interação com dívida elegível, exclusões e casos jurídicos | Pendente | Habilitação, gatilho, cardinalidade, campos obrigatórios e duplicidade de linhas. Q21–Q22 |

A regra de laboratório não foi promovida a regra geral: gerar uma linha cadastral
por unidade com boleto fora do prazo e priorizar Cadastro em conflito eram
exceções daquele laboratório. Nenhuma delas está aprovada para o produto real.
As 34 unidades FL retidas e os conflitos CPF/CNPJ continuam bloqueados, inclusive
para proposta de cadastro sem dívida.

## Aprovações que a matriz ainda não contém

Para cada ID, preencher a ficha de decisão em
[Perguntas e decisões](DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md): fonte/versão/hash,
condição e operador exatos, dados necessários e ausência, escopo, ação, prioridade,
vigência, relacionamento com as demais regras, responsável e fundamento.

Cadastro antecipado pode exigir política de cadastro/configuração e projeção de
saída, além de uma condição financeira. Os contratos atuais não possuem ação de
regra chamada `gerar_linha_cadastral`; não tratar `incluir` boleto como sinônimo.
Se a decisão exigir extensão de contrato, documentar e submeter em tarefa própria.
A geração operacional das linhas e a homologação de importação continuam na Fase 5.

Garantidora, modalidade judicial e outras exceções eventualmente presentes na
régua são critérios transversais a levantar, não uma nona regra criada aqui.
Texto livre, informação de acesso e credenciais não serão convertidos em condição.
