# Verificação técnica final e decisões humanas restantes — 4.3B.2B

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

**Decisão de negócio confirmada de vigência — ainda sem aprovação formal:**
para TREE MORUMBI e PLAZA MAYOR IPIRANGA, `vigente_de: 2026-09-10` (inclusivo),
`vigente_ate: null`, com fim aberto expressamente definido até substituição ou
revogação expressa. A referência do processamento continua independente e não
foi escolhida. **Ressalva obrigatória:** 10/09/2026 antecede o rótulo documental
20/10/2026; o fundamento dessa aplicabilidade anterior deve ser validado
formalmente antes da liberação operacional. Essa validação continua pendente.
Registrar o negócio não aprova plano, atesta fonte, assina ou ativa regras.

**Atualização documental após o recebimento do original:** tamanho de 712.353
bytes e SHA-256 esperado conferidos exatamente. Fonte privada vinculada à aba
`RÉGUA DE COBRANÇA`, linhas 366 (TREE) e 329 (PLAZA), com rastreabilidade dos
oito IDs. [Versão, coordenadas, diferenças de redação e validação formal pendente](VIGENCIA_E_VERSOES.md).
Não há aprovação ou atesto humano; os cinco originais de inadimplência/cadastro/
referência e pacotes assinados não foram reabertos ou modificados.
Nesta incorporação executaram-se somente verificações de integridade e vínculo;
os resultados de testes abaixo permanecem históricos, sem alegar nova regressão.

**22/10/2026 — America/Sao_Paulo.** Executada somente verificação sintética e
conferência de inventários/metadados existentes. Nenhum dos cinco originais foi
aberto/processado. Sem assinatura/ativação de plano real, atesto humano, simulação
real, liberação de crítico, XLSX operacional ou início da Fase 5.

## Prioridades: compatibilidade demonstrada, aprovação ainda pendente

O [motor existente](../../src/conversor/rules/engine.py) ordena avaliações por
`(-prioridade, id)` e escolhe os candidatos verdadeiros de **maior prioridade**
com `max(...)`. Foi confirmado por testes que **1 prevalece sobre 0** quando
as condições são conclusivas, no mesmo escopo, sem bloqueio superior.

Os 21 testes novos em
[`test_priorities_1_0.py`](../../tests/synthetic_processing/test_priorities_1_0.py)
usam apenas modelos/funções puras, em memória. Não usam repositório de planos,
autoridade, assinaturas, eventos de aprovação/ativação ou atestos. Nenhuma data
real de regra/processamento foi criada; as datas são as das fixtures sintéticas
preexistentes e o parâmetro explícito de referência.

- Oito casos: centavo/A/AJ/J com prazo satisfeito, com e sem guarda da inclusão.
  Sem guarda, ambas as ações são verdadeiras e a exclusão 1 vence a inclusão 0;
  com a guarda, a inclusão é falsa. Todas as seis avaliações são preservadas.
- Seis casos: centavo junto de A/AJ/J, com e sem guarda. As duas exclusões 1
  permanecem decisivas, com ambas as justificativas, sem duplicar a cota.
- Três contraprovas genéricas, sem guarda: exclusão 1/inclusão 0 exclui;
  inversão 0/1 inclui; empate 0/0 exige revisão. As duas últimas são diagnósticos
  puros da ordenação, **não propostas TREE**. O motor genérico não garante
  exclusão individual por simples preferência de ação; números e guarda importam.
- Dois casos: evidência de apontamento ausente, com e sem centavo comprovado,
  resulta em revisão. Prioridade não silencia indeterminação; a exclusão
  conhecida continua no conjunto completo de avaliações e não há inclusão.
- Um caso: duas cotas da mesma unidade, AJ numa e prazo satisfeito na outra,
  resultam em exclusão/eligibilidade distintas. Inverter ordem de regras não
  muda avaliações/decisões; nenhuma entrada é modificada.
- Um caso: bloqueio diagnóstico de unidade na prioridade 0 prevalece sobre
  candidatos de boleto nas prioridades 1/0. É teste da capacidade de segurança,
  não nova regra particular de TREE.

Os críticos externos de unidade/lote foram também cobertos pela regressão
existente: `test_bloqueio_critico_nao_e_anulado_por_inclusao_ou_exclusao`,
`test_subtotal_divergente_permanece_bloqueio_de_lote`,
`test_critico_prevalece_sobre_condicoes_financeiras` e os testes integrados de
preservação Habita/VG/FL. O serviço aplica críticos externos sobre o resultado
financeiro, fora da disputa numérica. Nenhuma alteração foi feita no motor.

**Resultado:** não foi encontrada incompatibilidade da semântica numérica com a
configuração 1/0. A confirmação posterior estabelece esses números como
decisão de negócio; **o plano continua sem aprovação formal e não aplicado**. TREE
deve manter a guarda `>30 AND NOT(centavo OR A OR AJ OR J)`; um indeterminado
relevante pode levar a revisão mesmo com exclusão conhecida. Não se alterou esse
comportamento conservador para transformar revisão em exclusão presumida.

## Conferência anterior dos cinco anexos — histórico preservado

Foram consultados os inventários de integridade 001, o relatório de metadados
007 e os dois `*_excel.metadados.json` existentes. Os cinco IDs/tamanhos/hashes
de fonte coincidem entre 001/007; o inventário anterior registra igualdade entre
anexo e cópia. Isso confirma o **vínculo entre os metadados históricos**, não uma
nova leitura, rehash dos originais, assinatura técnica ou atesto humano.

A referência geral candidata continua
`REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx`, citada em
[Fontes e importação](../../FONTES_E_IMPORTACAO.md). **A régua não integra as cinco
fontes desses inventários. Seu SHA-256 não está disponível nos metadados
consultados**, nem há vínculo comprovado de extrato/versão por condomínio.
Não foi gerado hash de nome/relatório/fixture no lugar do hash da régua.
**Esse resultado descreve a etapa anterior ao anexo atual**; o original depois
recebido foi incorporado ao complemento privado sem reescrever os inventários
001/007. A identificação atual está na ficha de versões vinculada acima.

O complemento privado está em
`/workspace/validacao-privada-fase3/resultados/verificacao_final_aprovacoes_4_3B_2B/`:
`CONFERENCIA_PRIVADA_REGUA_E_FONTES.md` e `METADADOS_CONFERENCIA_FINAL.json`.
Contém os cinco hashes completos de fonte, suas versões registradas e a
indisponibilidade então registrada dos hashes de régua TREE/PLAZA, preservada
em snapshot. A seção posterior de incorporação contém o hash agora verificado. Todas as decisões
humanas continuam vazias; não se sobrescreveram as fichas/relatórios anteriores.

**Data do documento:** 20/10/2026 é somente rótulo nominal do nome candidato;
a data interna ainda não foi comprovada. **Início e fim de vigência naquela etapa:** ainda não
informados. A decisão posterior no início deste documento fixa 2026-09-10
inclusivo e fim aberto expresso como negócio, sem aprovação formal. **Data de referência:** escolha
explícita por processamento, não escolhida nesta tarefa. Nenhuma dessas datas
é inferida de hoje, do mês do Excel ou do rótulo do arquivo. O contrato temporal
existente permanece `[vigente_de, vigente_ate)`.

## Tabela única de decisão final

| Condomínio / item | Já comprovado ou confirmado | Confirmação/ato humano ainda necessário |
|---|---|---|
| **TREE — condições do plano** | Centavo no original integral `Boleto.composicao.total_original` ou A/AJ/J exatos no campo/namespace validado exclui só a cota/componentes, qualquer vencimento; outras cotas continuam. Prazo `>30` dias corridos, com guarda das exclusões. Garantidora isolada não exclui | Não repetir esses efeitos. Vincular fonte/namespace/evidência ao conteúdo final versionado e aprovar seu hash formalmente |
| **TREE — prioridades** | **1 > 0 verificado**. Duas exclusões mantêm dois motivos. Revisão por indeterminação e bloqueios prevalecem sobre a seleção financeira | Números das quatro exclusões **1** e prazo **0** confirmados como negócio; manter guarda e validar a representação final do ramo complementar na aprovação do plano versionado. Não pedir os números novamente |
| **TREE — F01 PDF** | Identidade/hash/tamanho/versionamento registrados nos metadados coincidentes 001/007. 149 páginas, 112 unidades, 769 boletos, 2.082 componentes, 33 continuidades; 628 vazios e A=15/AJ=9/J=117. 769 competências ausentes; **Habita/VG bloqueia o lote** | Atestar arquivo exato, completude/cobertura/ausências e catálogos, com identidade/função/instante/fundamento. Não remover VG pelo atesto |
| **TREE — F02 Excel** | Mesmo vínculo de integridade entre metadados; 63 linhas não vazias: 63 de dívida e zero cadastrais, 15 cedentes distintos. Referência esperada, não gabarito absoluto | Atestar significado/agrupamentos/vínculos e contexto temporal da referência; não inventar competência ou forçar coincidência |
| **PLAZA — condições/prioridade** | Prazo extrajudicial `>30`, sem filtro judicial/garantidora autônomo ou exclusões TREE presumidas. Mesmo mecanismo numérico e revisão conservadora; prazo/ramo `<=30` são condições complementares | Prioridade **0** do prazo confirmada como negócio. Aprovar o futuro conteúdo versionado/hash, incluindo representação do ramo complementar, sem inserir particularidades não autorizadas |
| **PLAZA — F03 PDF** | Identidade/hash/tamanho/versionamento registrados entre 001/007. 24 páginas, 50 unidades, 115 boletos, 985 componentes; 17 continuidades financeiras e três só descritivas. Cadastro incompleto; saldos acumulados não são dívida individual | Atestar completude/ausências/continuidade e vínculos às fontes; preservar as 34 unidades retidas e os 83 críticos externos do conjunto FL |
| **PLAZA — F04 Cadastro** | Mesmo vínculo de integridade; 25 páginas, 390 registros; somente 50 unidades cruzadas por condomínio + torre/bloco + unidade. Ambiguidade de endereço fora dessas 50 mantém seu escopo | Atestar cobertura e vínculo/vigência cadastral. Titularidade e documentos conflitantes exigem decisão própria; não priorizar Cadastro nem importar os 390 automaticamente |
| **PLAZA — F05 Excel** | Mesmo vínculo de integridade; 112 linhas não vazias: 69 de dívida e 43 cadastrais, 47 cedentes distintos. Quatro registros documentais externos/células distintas preservados | Atestar contexto/vínculos da referência, sem escolher titular/documento por ela. Dois conflitos de documentos válidos continuam retidos |
| **AMBOS — régua original/hash** | Original recebido e conferido: 712.353 bytes, fingerprint `c56349e33b54…`, SHA completo privado. Aba `RÉGUA DE COBRANÇA`: TREE linha 366, PLAZA linha 329. Oito IDs vinculados documentalmente | Conferir humanamente a fonte/vínculo e as decisões posteriores que esclarecem sua redação; identificação técnica não aprova aplicabilidade operacional ou vigência |
| **AMBOS — datas/vigência** | **Negócio confirmado:** início inclusivo 2026-09-10 e fim null, aberto até substituição/revogação expressa; referência independente e ainda não escolhida | Informar fundamento/evidência e validar formalmente a aplicabilidade anterior ao rótulo da fonte de 20/10/2026, no plano identificado por versão/hash, sem alterar conteúdo assinado. Aprovação formal pendente |
| **AMBOS — aprovador e atos** | Responsável pode acumular Administrador, Revisor e Operador; contratos separam autenticação, aprovação e execução e exigem integridade verificável | Registrar identidade autorizada e papel em cada ato, instante/fundamento/evidência; concluir atestos e aprovação do plano/versão/hash. Nenhum ato foi preenchido ou emitido |
| **AMBOS — processamento e segurança** | A/B universal por processamento; no máximo um cadastro adicional, Y:AD vazias, sem contornar críticos. 30 colunas e CPF/CNPJ preservados. Fluxo novo permanece restrito a sintéticos | Após aprovações humanas, poderá ser proposta autorização específica da primeira simulação privada e da integração necessária; **nenhuma simulação real/exportação está autorizada agora** |

## Testes executados e resultados

- Novos testes puros: **21 aprovados em 0,06 s**.
- Regressão regular completa: **1.072 aprovados em 21,90 s**.
- Suítes explícitas de homologação sintética: **60 aprovados em 1,16 s**.
- Total sem dupla contagem: **1.132 = 1.111 anteriores + 21 novos**.
- Oito geradores de schemas: todos passaram em `--check`.

```bash
.venv/bin/python -m pytest -q tests/synthetic_processing/test_priorities_1_0.py
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m conversor.billing_schemas --check
.venv/bin/python -m conversor.evaluation_schemas --check
.venv/bin/python -m conversor.private_simulation_schemas --check
.venv/bin/python -m conversor.audit_schemas --check
.venv/bin/python -m conversor.synthetic_processing_schemas --check
.venv/bin/python -m conversor.integrated_processing_schemas --check
```

A regressão preexistente usa fixtures e autoridades sintéticas descartáveis em
temporários; não registra manifestações humanas ou planos reais. Os novos testes
são puros e não emitem sequer esses eventos técnicos temporários. Nenhuma fonte
real foi usada na execução dos testes. Motor/leitores/contratos/schemas/planos
permanecem inalterados; só testes e documentação foram acrescentados/revisados.

Pronto para decisão humana, **não para executar simulação privada agora**. Os
commits `a47e155`, `ed4e179` e `786a272` permanecem inalterados; sem novo commit,
push ou merge. Sistema não homologado para produção; Fase 5 não iniciada.
