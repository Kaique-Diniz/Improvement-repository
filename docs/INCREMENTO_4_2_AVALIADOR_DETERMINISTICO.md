# Incremento 4.2 — avaliador determinístico para simulação

Implementado para revisão técnica, após o aceite do 4.1. **Sem homologação para
produção.** Não foram implementadas regras específicas de condomínios reais,
ativação de planos reais, envio de cobrança, Excel operacional ou workflow 4.3.
Os leitores, canônico, contratos/schema de planos do 4.1, CPF/CNPJ e as 30 colunas
universais permanecem inalterados.

## Implementação

| Arquivo | Responsabilidade |
|---|---|
| `domain/billing_evaluation.py` | Entrada com canônico, fatos, ocorrências e cobertura de campos; solicitação com pin de versão/hash; trilhas e relatório somente de simulação |
| `rules/conditions.py` | Condições e operadores tipados existentes no 4.1, lógica de três valores e proveniência |
| `rules/engine.py` | Candidatos por escopo, prioridade, conflitos e resolução conservadora; não autentica planos nem produz autorização |
| `application/billing_evaluation.py` | Entrada pública `SimularCobranca`, validação, proteção de bloqueios, decisões e conferência administrativa antes/depois |
| `application/billing_evaluation_ports.py` | Verificador independente da autoridade/revisão atual, substituível por outro backend |
| `adapters/billing_evaluation_authority.py` | Ponte somente de leitura para HMAC, permissões históricas e âncora do JSON 4.1 |
| `evaluation_schemas.py` | Três schemas de entrada/solicitação/relatório em `schemas/simulacao/1.0/` |
| `examples/fase4/gerar_relatorio_4_2.py` | Demonstração fixa criada do zero; não recebe PDFs ou planos externos |
| `examples/fase4/relatorio_sintetico_4_2.json` | Relatório ilustrativo completo com as quatro situações |
| `tests/evaluation/` | 121 casos novos sintéticos, usando autoridade temporária do 4.1 |

Os caminhos de código na tabela são relativos a `src/conversor/`. Testes criados:
`conftest.py`, `test_rule_conditions.py`, `test_rule_resolution.py`,
`test_simulation_service.py` e `test_simulation_schema.py`, em `tests/evaluation/`.
Documentação de status atualizada em README, plano 01, especificação 02,
arquitetura Fase 4 e relatório histórico do 4.1.

## Porta de avaliação e prova administrativa

```python
from conversor.application.billing_evaluation import SimularCobranca
from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON

servico = SimularCobranca(repo_planos_4_1, VerificadorPlanosJSON(repo_planos_4_1))
relatorio = servico.executar(solicitacao_tipada, entrada_tipada)
```

A avaliação não recebe plano ou declaração de aprovação do chamador. A solicitação
identifica condomínio, ambiente, plano, versão, hash exato, processamento e data de
referência obrigatória. Não há fallback para outra versão ou para a data atual.

O serviço carrega o estado do repositório e exige verificação independente contra
sua autoridade atual. O adapter 4.1 verifica assinaturas de manifesto/eventos,
políticas históricas autorizadas, cadeia, estados, versão/hash e âncora externa.
O serviço revalida os contratos e o histórico e exige configuração ativa, aprovação,
ativação e vigência na data pedida. `ativo` isoladamente não satisfaz a verificação.
O relatório referencia revisão/hash do estado, sequência/hash da aprovação e da
ativação. Não cria novos eventos administrativos nem recebe credencial para isso.

Antes de retornar, confere novamente a autoridade e a revisão. Revogação ou
mudança administrativa concorrente invalida a simulação inteira. Inclusive uma
mudança em outro plano da mesma revisão impede devolver um resultado com prova
obsoleta. É uma política conservadora; não há transação longa bloqueando aprovações.
A prova descreve o snapshot verificado, não uma permissão duradoura de cobrança.

Assinatura inválida, plano alterado/revogado/inativo, contrato inválido, pin errado,
condomínio divergente e vigência incompatível causam recusa integral com código
estável, sem resultado elegível nem dados privados na mensagem. Backends novos
precisam implementar a verificação contra autoridade; apenas desserializar um
EstadoPlanos não substitui essa garantia. O host/verificador configurado pertence
à fronteira confiável, conforme o limite de confiança do 4.1.

## Condições, fatos e ausência de evidência

Reutilizam-se exclusivamente cláusulas/condições e valores do 4.1: comparações
`eq/ne/gt/gte/lt/lte`, dias de atraso, valor original, apontamento com namespace,
fatos declarados, `todas`, `qualquer`, `nao`, `existe_boleto` e `todos_boletos`.
Operadores desconhecidos são recusados; nunca se executa texto livre.

- Atraso é a diferença assinada entre data de referência e vencimento; vencimento
  futuro produz dias negativos. Não se presume limite global de 30/60 dias.
- Valor comparado é o original canônico. Comparações monetárias usam Decimal,
  sem somar saldo acumulado, encargos ou refazer dívida. A entrada é revalidada
  pelas invariantes existentes; seus objetos/valores não são modificados.
- Fatos precisam de definição no plano, tipo compatível, identidade de condomínio,
  unidade/boleto, fonte, confirmação e intervalo explícito de vigência. Um fato
  não pode vazar para outro boleto/unidade ou ser empregado com tipo diferente.
- Ausência, fato fora de vigência ou não confirmado resultam em indeterminação.
  Valores distintos em fontes simultaneamente vigentes resultam em contradição,
  mesmo que uma fonte seja mais recente ou ambos satisfaçam uma comparação. Não
  se escolhe fonte por proximidade. Valores iguais preservam ambas as evidências.
- Apontamento positivo exige código e namespace exatos. Ausência só é falsa com
  cobertura explícita do campo/namespace daquele boleto, ligada à sua fonte.
  Sem cobertura, fica indeterminada; lista vazia não prova inexistência de marcador.
  Não há conversão automática de apontamento em status jurídico.
- Em `todas`, falso domina; em `qualquer`, verdadeiro domina. Demais combinações
  preservam indeterminação. Negar desconhecido continua desconhecido. Todos os
  ramos são rastreados, inclusive os que não mudam o resultado composto.
- Quantificadores examinam todos os boletos da unidade antes de qualquer decisão.
  `existe_boleto` em unidade vazia é falso; `todos_boletos` em conjunto vazio é
  indeterminado, sem inclusão por verdade vacuamente satisfeita.

Competência não é condição nova, não é preenchida e nunca é inferida. Elegibilidade
financeira simulada não implica prontidão de cadastro/template/importação.

## Resolução e preservação dos bloqueios

| Ordem | Tratamento |
|---|---|
| Segurança | Toda ocorrência crítica aplicável prevalece sobre qualquer candidato; não há opção de ignorar bloqueios |
| Regras de bloqueio | Uma regra verdadeira de bloquear retém o escopo, inclusive diante de permissão de prioridade maior; empate é registrado e requer revisão |
| Condições de unidade | Indeterminação não informativa impede inclusão. Empate incompatível no maior nível aplicável exige revisão |
| Exclusão terminal da unidade | Exclui seus boletos independentemente da prioridade das permissões individuais; a trilha mostra o boleto/apontamento/fato gatilho |
| Adiamento de unidade | Retém os boletos para revisão, sem inferir agenda ou modalidade |
| Regras individuais | Condições indeterminadas retêm; maior prioridade aplicável vence; empate com ações incompatíveis exige revisão |
| Permissões genéricas/alertas/lacunas | Permissão da unidade e alerta não autorizam boleto. Sem decisão individual aplicável, fica pendente |

A prioridade decide entre ações individuais aplicáveis, mas não supera as
restrições superiores. Empates da mesma ação preservam todas as justificativas.
Conflitos de prioridade inferior que não decidem a ação individual não substituem
a maior prioridade. Regra verdadeira de bloqueio sempre conserva a retenção;
um empate com essa regra continua bloqueado e sinaliza revisão humana.

Decisões explícitas por boleto: `elegivel_na_simulacao`, `excluido`, `bloqueado` e
`pendente_revisao`. `adiar` é retenção pendente com motivo próprio, não exclusão
financeira inventada. Regras `alertar` permanecem na trilha, sem decidir inclusão.
O resumo da unidade nunca substitui as decisões individuais: só é elegível se
seus boletos individuais forem elegíveis; decisões mistas ficam pendentes ou
bloqueadas. Unidade sem boleto não recebe dívida fictícia.

Ressalvas canônicas são convertidas em ocorrências sem perder o bruto original;
os documentos das pessoas são novamente submetidos ao resolvedor já aprovado.
Conflitos CPF/CNPJ e vínculo de titular não confirmado continuam críticos. CPF/CNPJ
vazio/inválido gera alerta, sem transformar ausência em bloqueio. Ocorrências
externas — inclusive da comparação documental — são obrigatórias como coleção
explícita e preservam ID, processamento de origem, severidade e evidências.
Bloqueio de arquivo/processamento atinge o lote, cadastro/pessoa atinge sua unidade,
e de boleto atinge o registro. Escopo crítico desconhecido bloqueia todo o lote.
Identidade ambígua entre tipos de entidade é recusada, sem escolha aproximada.

O relatório conserva o motivo do candidato de regra e o motivo final de segurança,
as regras avaliadas, valores observados, verdade/indeterminação, fatos e coberturas
recebidos com vigências, fontes/páginas/linhas, origens financeiras e fontes das
regras. Preserva todas as ocorrências e ressalvas originais. Não escolhe titular
ou documento e não altera os bloqueios anteriores de lote/unidade/cadastro.

Relatórios completos podem conter dados financeiros/documentais: devem permanecer
na área privada e não ser impressos em logs nem publicados no Git. Somente o
exemplo fixo, inteiramente sintético, foi versionado nesta entrega.

## Relatório demonstrativo

[Exemplo JSON completo](../examples/fase4/relatorio_sintetico_4_2.json), criado do
zero. IDs, regras, fatos e origens são exclusivamente didáticos:

| Unidade sintética | Situação | Justificativa |
|---|---|---|
| 1 | Elegível na simulação | Permissão individual comprovada; nenhuma restrição aplicável |
| 2 | Excluído | Restrição explícita de unidade prevalece sobre permissão do boleto |
| 3 | Pendente | Evidência da permissão individual ausente |
| 4 | Bloqueado | Ocorrência crítica anterior preservada |

O contrato fixa `modo=somente_simulacao`, `autoriza_cobranca=false` e
`permite_exportacao_operacional=false`. Não é ResultadoCobranca de exportação,
não possui ação operacional e não alimenta o exportador. Não há XLSX, envio,
modificação de documentos ou ativação de plano real.

```bash
.venv/bin/python examples/fase4/gerar_relatorio_4_2.py --saida /tmp/relatorio-sintetico-4.2.json
```

A demonstração cria uma autoridade temporária explicitamente sintética e a descarta.
O exemplo versionado não é gabarito real nem prova reutilizável de aprovação.
Chaves/tokens são aleatórios e não são gravados no relatório. A reprodução exata
é verificada duas vezes durante a mesma demonstração. Recriar outra autoridade
muda os hashes de aprovação, portanto não se espera igualdade de todos os bytes
entre demonstrações independentes. Com o mesmo snapshot/entrada/data/versão de
motor, o relatório é idêntico; não usa relógio ou sorteio na avaliação.

## Testes executados

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m conversor.billing_schemas --check
.venv/bin/python -m conversor.evaluation_schemas --check
```

**656 testes regulares + 60 explícitos = 716 aprovados**, incluindo os 595
anteriores e 121 novos. Sem falhas/skips nesta execução Linux. Os testes cobrem
operadores/limites, valores e saldo, todas as condições, conflito/vigência de fatos,
prioridade, empate, exclusão integral, isolamento, estados não aprovados/inativos/
revogados, adulteração e cache obsoleto, revogação concorrente, bloqueios de leitura,
CPF/CNPJ, competências ausentes, determinismo, rastreabilidade e ausência de logs.
Schemas antigos e novos sincronizados. Nenhum PDF/Excel real foi processado nesta
entrega; os 884 boletos e 132 correspondências continuam evidências da Fase 3.

## Limites conhecidos e questões para aprovação no 4.3

1. **Completude das entradas:** o avaliador valida e preserva as evidências que
   recebe e reconstrói bloqueios do canônico. Não autentica sozinho a veracidade
   ou completude dos fatos/coberturas/ocorrências externas. `comprovado` identifica
   a confirmação recebida do chamador confiável, não uma homologação por IA.
   O 4.3 deve definir manifesto de fontes/impedimentos, responsáveis e integração
   privada, evitando omitir os conflitos que só existem em dossiês complementares.
2. **Persistência/reprodução histórica:** este incremento retorna relatório em
   memória e oferece só demonstração sintética. Armazenamento privado, retenção,
   histórico de simulações, hashes de artefatos e replay de revisões antigas ficam
   para aprovação no 4.3. O serviço atual recusa snapshot revogado/obsoleto; não há
   modo de reaproveitar aprovação antiga como autorização atual.
3. **Resolução conservadora:** bloqueio de regra verdadeiro não é sobreposto por
   permissão; `adiar` retém; fato relevante indeterminado de prioridade inferior
   também impede inclusão. Detalhar eventuais flexibilizações apenas com regras e
   aprovação explícitas. Não foram criadas exceções operacionais financeiras.
4. **Planos reais:** precisam de fonte privada autorizada, formalização e aprovação
   próprias, inclusive prazos, efeitos jurídicos, garantidora, exceções e cadastro
   antecipado. Nenhum plano de TREE/Plaza foi implementado ou ativado nesta tarefa.
5. **Operação/importação:** não há autorização de cobrança. Competência Habita
   permanece ausente; destino easyCollector e 30 colunas dependem da Fase 5. Sem
   alteração de CPF/CNPJ ou relaxamento dos bloqueios críticos, incluindo o lote
   Habita/VG e os cadastros FL que exigem revisão humana.

O incremento 4.3 e a Fase 5 **não foram iniciados**. Aguarda-se revisão desta entrega.

## Registro de entrega

Branch `feature/fase-4-motor-cobranca`; implementação, testes, schemas e exemplo
no commit `371d87a`. Documentação em commit separado, preservando os commits do
4.1 e da Fase 3. Sem push/merge em main. A branch ainda contém a base local da
Fase 3, ausente da referência `origin/main`, e essa dependência deve ser considerada
na futura publicação. A conferência exata de privacidade não encontrou cópias das
fontes reais nem nomes completos, e-mails ou documentos válidos do canônico privado
nos arquivos versionáveis. Essa conferência complementa a revisão, sem constituir
garantia universal sobre todos os possíveis dados sensíveis.
