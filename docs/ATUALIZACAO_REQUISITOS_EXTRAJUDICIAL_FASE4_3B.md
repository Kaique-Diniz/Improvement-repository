# Atualização documental de requisitos extrajudiciais — 4.3B

**22/10/2026. Escopo: somente documentação, matriz e proposta de configuração.**
Fonte: esclarecimentos expressos do responsável pelo projeto nesta revisão.
Prevalecem sobre hipóteses históricas; não são aprovação formal de versão/hash
nem atesto humano das fontes. Não há início efetivo do 4.3B ou da Fase 5.

**Atualização específica TREE recebida depois desta primeira revisão:** o
responsável confirmou A/AJ/J como exclusões da cota inteira e componentes, com
o mesmo alcance do centavo. A hipótese anterior de escopo/efeito ainda pendentes
fica superada. Permanecem pendentes validação dos campos, vínculo à régua,
aprovações técnicas/formais, assinaturas e atestos. A matriz documental passa à
revisão 2.1, sem implementação nem execução de regras reais.

**Etapa preparatória técnica autorizada posteriormente:** o
[mapeamento TREE](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md) foi conferido no
PDF privado, com testes sintéticos de leitor/predicados e proposta documental 2.2.
Isso supera a pendência de conferência técnica do mapeamento neste arquivo,
mantendo atestos, aprovação de planos e autorização do 4.3B efetivo pendentes.
As seções documentais anteriores abaixo registram seus escopos originais; a
validação posterior não executou regras reais nem alterou leitores/motor.

## Decisões e rastreabilidade

| Decisão do responsável | Incorporação documental | Questões impactadas |
|---|---|---|
| Conversor seleciona cotas extrajudiciais; CRM analisa medidas posteriores | Retirado filtro judicial, sem exigir configuração de 60/90 dias para Excel | Q06–Q08, Q17–Q20, Q23–Q24 |
| Prazo de 30 significa estritamente mais de 30 dias corridos, referência explícita | Dia 30 não satisfaz; dia 31 satisfaz somente prazo. Outros condomínios podem ter outros prazos aprovados | Q03, Q06, Q08, Q16–Q17 |
| R$ 0,01 exclui só a cota e seus componentes, independentemente do vencimento | Retirada hipótese de exclusão de unidade pelo centavo; exigir mapeamento do campo Valor antes de ativar | Q05–Q06, Q08, Q11–Q12, Q24 |
| Garantidora isolada não exclui | Sem condição autônoma nem duplicação da regra monetária TREE | Q07–Q08, Q11, Q24 |
| Cadastro antecipado universal A/B por processamento | Sem default; B permite uma linha cadastral adicional por unidade com cotas não elegíveis, inclusive coexistindo com dívidas elegíveis; Y:AD vazias | Q06, Q08, Q12, Q21–Q24 |
| Mesma identidade autorizada pode acumular três papéis | Administrador, Revisor, Operador; eventos independentes, sem aprovação/atesto automáticos | Q01, Q09, Q25–Q26 |
| TREE: A, AJ ou J comprovado no campo apropriado exclui cota/componentes | Confirmado efeito/escopo: uma condição basta, independente do vencimento; não excluir outras cotas nem apagar evidências. Validar campos/namespace e associação à cota; rejeitar gatilhos em legendas/observações/descrições | Q06–Q08, Q12–Q16, Q24 |
| TREE: Valor confirmado como referência do boleto; prazo extrajudicial de 30 confirmado | Validar mapeamento real distinguindo componentes, multa, juros e totais; dia 31 satisfaz somente prazo, sem anular centavo/A/AJ/J ou bloqueios | Q05–Q06, Q11–Q16 |

A [matriz revisada](MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md) contém os oito IDs,
condições, escopos, ações, prioridades/vigências pendentes e situação das decisões.
O [quadro Q01–Q26](DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md) preserva todas as
perguntas originais, com respostas atualizadas e indicação do que ainda bloqueia.

## Proposta de configuração, não contrato executável

O arquivo
[`proposta_configuracao_4_3B.revisada.json`](../examples/fase4/proposta_configuracao_4_3B.revisada.json)
é um documento estruturado de requisitos. Não usa o schema de um plano aprovado
nem pode ser importado como tal. Todas as permissões operacionais estão falsas;
identidade, prioridades, vigências, mapeamento e escolhas de execução estão
pendentes. Não introduz schema de runtime ou nova ação do motor.

Separação proposta para implementação posterior:

1. **Plano por condomínio:** somente condições extrajudiciais aplicáveis,
   versionadas, com fontes, prioridades, vigências e aprovação válida.
2. **Mapeamento da fonte:** provar qual campo `Valor` corresponde à cota e aos
   componentes. Registrar arquivo/hash, formato/versão, página/linha, identificador
   da cota, campo canônico e prova da associação. Não escolher entre componente,
   total e saldo por aproximação. Todos esses vínculos concretos continuam pendentes.
3. **Contexto de processamento:** referência explícita, modo A/B obrigatório sem
   default e versão da política. Proposta é persistir/reproduzir a mesma escolha
   no histórico e auditoria, sem herdar booleano silenciosamente do condomínio.
4. **Projeção futura:** somente cotas elegíveis como dívida; B admite uma linha
   cadastral por unidade com cotas comprovadamente não elegíveis. Indeterminação
   relevante exige revisão, não serve como atalho para cadastro. Y:AD vazias,
   30 colunas e CPF/CNPJ textual preservados.
5. **Autoridade:** identidade autorizada pode acumular os três papéis. Cada ação,
   decisão humana, aprovação e atesto tem registro próprio com ator, papel,
   instante, fundamento e vínculo à evidência/conteúdo. Isso não cria concessões
   de acesso nem novos eventos reais nesta tarefa.

A exclusão da cota por **centavo OU A OU AJ OU J** é restrição definida pelo
negócio: qualquer condição comprovada basta e não depende do vencimento. Excluir
todos os componentes dessa cota como dívida, preservando-os no canônico e na
auditoria. Outras cotas da unidade seguem avaliadas; prazo de 31 dias ou mais não
anula exclusão. Prioridades numéricas para expressar a interação no plano continuam
pendentes; não inventar números ou exclusão de unidade para consegui-la.

Campo `Valor` foi confirmado pelo responsável como referência do boleto. Essa
definição de negócio não prova sua posição ou correspondência canônica nos PDFs.
Ainda é necessário validar origem/arquivo/hash, página/linha e identificação da
cota e componentes, distinguindo multas, juros, componentes, saldos e totais.
Para A/AJ/J, validar campo próprio e namespace; não inferir apontamento de legenda,
observação ou texto descritivo. Sua expansão nominal/jurídica não foi fornecida
e não será inventada: está confirmado o efeito operacional de exclusão da cota.

## Lacunas de implementação conscientemente preservadas

Esta entrega **não implementa** o novo comportamento. Leitores, schemas,
repositórios, avaliador, exportador e testes permanecem inalterados. Antes de
implementar, conferir aderência dos contratos 4.1/4.2 ao mapeamento de cota/Valor,
à projeção A/B e ao registro/replay do modo. Não afirmar que `incluir` boleto já
significa gerar cadastro ou que o booleano histórico por condomínio implementa
esta opção universal. A saída operacional permanece na Fase 5.

Exemplos históricos da fundação, do laboratório e da arquitetura continuam
reprodutíveis. Não são a proposta atual e não podem alimentar planos reais:

- `config_exemplos/regras.exemplo.json`: centavo por unidade e prazos judiciais
  pertencem à hipótese superada, não a filtros aprovados atuais.
- `config_exemplos/condominios.exemplo.json`: booleanos históricos por condomínio
  não escolhem A/B para processamento futuro.
- `examples/fase4/plano_regras.proposta.json`: exemplo genérico sintético anterior
  a 4.1, não plano TREE nem aprovação de exclusão de unidade pelo centavo.
- `examples/fase4/matriz_preliminar_4_3A.json`: contrato histórico de levantamento
  mantido para seus testes/reprodução; usar a matriz revisada para decisões atuais.

Contratos privados 1.0/1.1, IDs legados/internos, recibos, fontes e decisões
financeiras não são migrados nem reescritos. Não se executou simulação real nem
nova preparação privada para ajustar resultados às novas decisões.

## Condições antes da próxima autorização

- Concluir atestos humanos por fonte e conjunto; integridade automática não substitui.
- Vincular a régua vigente revisada e o mapeamento Valor → cota/componentes.
- Validar campos próprios/namespace e associação de A/AJ/J à cota. Escopo, ação e suficiência de uma condição já confirmados; aprovar prioridades numéricas, vigências e formalização das interações dos planos aplicáveis.
- Registrar identidade autorizada e cada ato humano separadamente na área privada.
- Preservar Habita/VG, titularidades/documentos FL e todos os demais críticos.
- Definir referência e A/B por execução e revisar semântica dos Excel esperados.
- Autorizar expressamente a implementação do 4.3B em tarefa posterior; aprovação
  formal da versão/hash e simulações privadas continuam com seus próprios requisitos.

Sistema **não homologado para produção**. Nenhum documento real, dado pessoal,
credencial ou relatório financeiro privado integra esta revisão.

## Verificações da entrega documental

- Regressão reexecutada: **812 testes regulares + 60 explícitos = 872 aprovados**,
  sem falhas ou skips. Comandos reproduzíveis no
  [relatório de prontidão](PRONTIDAO_DOCUMENTAL_FASE4_3B.md#testes-de-regressão).
- Seis verificações de schemas aprovadas, sem alteração de contratos históricos.
- Proposta JSON sintaticamente válida e não executável; oito IDs e perguntas
  originais Q01–Q26 preservados; 30 cabeçalhos na ordem original conferidos.
- Links locais e diff conferidos; somente Markdown e nova proposta documental.
- Privacidade: 213 arquivos versionáveis examinados, sem cópias idênticas das
  fontes reais nem correspondências identificáveis verificadas; controle
  complementar, sem substituir revisão humana ou provar ausência universal.

Não foram adicionados testes que espelhem texto de documentação. Esta regressão
protege o comportamento existente; não comprova implementação dos requisitos
novos, ainda não autorizada. Alterações locais na branch
`feature/fase-4-motor-cobranca`, sobre `3b2c769`, sem novo commit, push ou merge.

### Escopo da atualização TREE

Alterados apenas documentos e a matriz/proposta documental não executável.
Não houve validação de documentos reais, migração de contratos, alteração de
leitores/avaliador/exportador, planos aprovados/assinados/ativados ou remoção de
evidências e bloqueios. O subtotal Habita/VG continua bloqueando o lote; cadastros
e documentos FL retidos permanecem retidos. Opções universais A/B, 30 colunas e
CPF/CNPJ textual foram preservados integralmente.

Na atualização específica TREE, foram reexecutados **812 testes regulares e 60
explícitos: 872 aprovados**, sem falhas ou skips, além das seis conferências de
schemas. Conferidos os oito IDs, Q01–Q26 originais, decisões documentais das cinco
regras TREE, controles sem ativação, links, 30 colunas e escopo exclusivamente
documental. Nenhum teste novo de execução dessas regras foi criado: implementação
e validação dos PDFs reais continuam fora da autorização desta tarefa.
