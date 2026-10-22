# Propostas e contratos históricos da Fase 4

## Exemplo exclusivamente sintético — 4.3B.1

[`tree_43b1.sintetico.json`](tree_43b1.sintetico.json) demonstra as cinco condições
TREE no contrato de plano 4.1 existente, para `cond_sintetico`. Contém seis
cláusulas técnicas: quatro exclusões, inclusão por prazo protegida pelas exclusões
e ramo complementar do mesmo prazo (`<=30`). Não é plano real ou previamente
aprovado; fontes, prioridades `0` e vigências são inventadas. Os testes criam os
eventos necessários somente em repositórios sintéticos temporários, nunca em
produção. O serviço de simulação não cria aprovações/ativações. Veja
[modelo, decisões A/B e testes](../../docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md).

## Proposta de negócio pendente e histórico

A proposta documental atual é
[`proposta_configuracao_4_3B.revisada.json`](proposta_configuracao_4_3B.revisada.json).
Não é plano executável nem usa schema de runtime. Não aprova/ativa planos,
atesta fontes ou autoriza simulação real. Prioridades/vigências e escolhas de
execução permanecem pendentes. Consultar a
[matriz revisada](../../docs/MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md).

Preservados para histórico e reprodução:

- `matriz_preliminar_4_3A.json`: levantamento original de oito propostas, sujeito
  ao contrato histórico. Centavo por unidade, filtro judicial e cadastro particular
  estão superados como proposta de negócio; nenhum será importado para plano real.
- `plano_regras.proposta.json`: exemplo sintético anterior a 4.1, não executável,
  com valores/prioridades/vigências inventados para ilustrar arquitetura. Não é
  a configuração de TREE ou Plaza; a capacidade genérica de excluir unidade não
  aprova esse escopo para a nova regra do centavo.

O exemplo sintético não altera contratos nem comportamento dos exemplos/testes
históricos. Configuração, aprovação e ativação reais continuam pendentes.
