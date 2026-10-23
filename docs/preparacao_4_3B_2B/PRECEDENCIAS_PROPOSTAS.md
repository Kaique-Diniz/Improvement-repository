# Precedências e prioridades — decisões de negócio confirmadas

**Prioridades confirmadas como decisões de negócio, sem aprovação de plano:**
TREE: `tree_centavo`, `tree_apontamento_a`, `tree_apontamento_aj` e
`tree_apontamento_j` = **1**; `tree_prazo_30` = **0**.
PLAZA: `plaza_prazo_30` = **0**. Os números não precisam de nova confirmação
de negócio. Exclusões afetam só a cota/componentes, com todas as justificativas
simultâneas preservadas. Indeterminações relevantes exigem revisão e críticos
prevalecem sobre prioridades financeiras. A/B é independente. Vigência de negócio
mantida: início inclusivo **2026-09-10**, fim aberto até substituição/revogação
expressa. Continuam pendentes a validação da aplicabilidade anterior à fonte de
rótulo 20/10/2026, a divergência TREE unidade/cota, atestos e aprovação formal do
conteúdo final dos planos. Não há assinatura, ativação ou autorização de simulação.

O arquivo mantém seu nome histórico para preservar links. O motor já demonstrou
**1 > 0** em testes sintéticos. Registrar essa confirmação não configura planos,
não emite aprovação/assinatura, não ativa regras e não atesta fontes.
Motor, schemas, fixtures e JSON históricos de planos permanecem intactos.

## Hierarquia documentada

| Camada | Tratamento | Prioridade / estado |
|---|---|---|
| Integridade/autorização administrativa | Aprovação válida, versão/hash, condomínio, vigência, fontes e controles administrativos necessários antes de autorizar qualquer avaliação | Fora da disputa numérica; atos formais pendentes |
| Bloqueios críticos externos | Lote/unidade/cadastro/documento preservam o bloqueio do escopo, inclusive Habita/VG e FL | Nenhuma prioridade financeira supera o bloqueio |
| Indeterminação relevante ou empate incompatível | Revisão humana, sem autorização presumida; a exclusão conhecida e todas as avaliações continuam auditadas | Não resolver aumentando prioridade |
| `tree_centavo`, `tree_apontamento_a`, `tree_apontamento_aj`, `tree_apontamento_j` | Excluir somente a cota/componentes; outras cotas independentes; múltiplas exclusões conservam todas as justificativas | **1 — negócio confirmado**, sem aprovação/ativação do plano |
| `tree_prazo_30` | Prazo estrito >30 dias corridos, com guarda das quatro exclusões | **0 — negócio confirmado**, sem aprovação/ativação do plano |
| `plaza_prazo_30` | Prazo estrito >30 dias corridos, sem filtro judicial ou condições TREE presumidas | **0 — negócio confirmado**, sem aprovação/ativação do plano |
| Ramo temporal complementar `<=30` | Detalhe de representação proposto na camada 0 da regra de prazo, não regra de negócio adicional | Validar representação no conteúdo final do plano; não pedir novamente os números das seis regras |
| Modos A/B | Projeção independente das prioridades, escolhida explicitamente por processamento; cadastral com Y:AD vazias e mesmos bloqueios | Nenhum modo escolhido; sem exportação nesta tarefa |

No TREE manter a guarda `>30 AND NOT(centavo OR A OR AJ OR J)`.
As fixtures antigas com outras prioridades são sintéticas e permanecem intactas;
não constituem configuração operacional dos condomínios.

## Resultados do motor atual, confirmados pelos testes sintéticos

| Situação | Resultado/justificativa |
|---|---|
| TREE com prazo satisfeito e uma exclusão comprovada, demais evidências conclusivas | Exclusão somente da cota. Inclusão tem guarda `>30 AND NOT(centavo OR A OR AJ OR J)` e será falsa; precedência não depende apenas do número |
| Duas exclusões diferentes comprovadas na mesma cota, demais condições conclusivas | Uma decisão de exclusão; mesma prioridade/ação, ambas as regras/justificativas preservadas. Não duplicar nem excluir outras cotas |
| Cota no dia 30 ou ainda não vencida, com evidências suficientes | Não elegível temporalmente; ramo `<=30` registra exclusão da seleção na referência. Não é exclusão permanente |
| Condição relevante de boleto indeterminada, mesmo havendo outra exclusão verdadeira | **Pendente de revisão**, conforme `resolver_candidatos`: indeterminação antecede a escolha final dos candidatos de boleto. A exclusão conhecida fica auditada e não há dívida elegível. Não usar prioridade para presumir o dado ausente |
| Campo de apontamento vazio com cobertura válida | Ausência comprovada: predicado daquele código falso; demais condições seguem avaliação |
| Campo sem cobertura ou leitura inconclusiva | Sem prova de ausência. Revisão; se houver ocorrência crítica da leitura, resultado final bloqueado |
| Duas ações verdadeiras incompatíveis empatadas no maior nível aplicável | Revisão; se há ação de bloqueio, resultado bloqueado. Não usar ordem de ID como desempate financeiro |
| Nenhuma regra de boleto aplicável | Revisão, não inclusão. Não transformar esse resultado em cota comprovadamente inelegível apenas para cadastro B |
| Crítico externo do lote, incluindo Habita/VG | Todos os boletos do lote ficam bloqueados, qualquer prazo/exclusão; sem candidato cadastral como alternativa |
| Crítico de unidade/cadastro, incluindo FL | Boletos da unidade afetada e seu cadastro ficam retidos; demais unidades continuam sob seus próprios controles |

São descrições de código e testes já existentes, **não resultados de execução
sobre fontes reais nesta tarefa**. O motor conserva todas as avaliações; ação
excluída da seleção não apaga evidência. Havendo indeterminação junto de exclusão,
o resultado conservador de revisão continua impedindo dívida e não altera o
efeito empresarial da exclusão conhecida.

Para PLAZA não se propõe centavo, A/AJ/J, garantidora ou condição jurídica como
filtro adicional. Bloqueios críticos são controles gerais, não particularidades
financeiras inventadas. A prioridade não altera documentos, valores, competência
ausente ou o alcance por cota confirmado pelo negócio.

## Pendências formais, sem nova confirmação de prioridades

- Validar formalmente a divergência TREE entre redação por unidade e decisão
  posterior por cota, sem reverter o comportamento já implementado.
- Fundamentar/validar a aplicabilidade desde 10/09/2026, anterior ao rótulo
  documental 20/10/2026; início inclusivo e fim aberto já confirmados como negócio.
- Concluir atestos das cinco fontes e dos conjuntos, preservando ressalvas/IDs,
  titularidades, documentos conflitantes e bloqueio Habita/VG.
- Fechar e aprovar o conteúdo final identificado por versão/hash e fonte,
  mediante identidade autenticada, papel, instante e fundamento próprios.
- Autorizar posteriormente integração privada, controles administrativos e
  simulação somente de leitura em atos separados. Nada disso está autorizado aqui.

Os campos humanos de atesto/aprovação dos planos continuam vazios.
Nenhum registro preparatório substitui os eventos formais do contrato 4.1.
