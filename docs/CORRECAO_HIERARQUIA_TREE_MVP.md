# Correção da hierarquia TREE no MVP

## Causa e alcance

O leitor já vinculava os boletos à unidade correta. A falha estava na orquestração
do MVP: exclusões configuradas no alvo `boleto`, ausência da avaliação por unidade
na resolução e contador `resumo.cotas` preenchido com a quantidade de boletos.

A definição atual do responsável é: **cota TREE = unidade**, identificada por
condomínio + bloco/torre + unidade; seus boletos contêm os componentes financeiros.
Substitui a interpretação anterior de cota como boleto para novas análises do MVP.
Contratos canônicos, leitores e registros históricos não foram reescritos.

Configuração diagnóstica TREE **1.1.0** reutiliza as cláusulas e o motor existente:
as quatro exclusões têm alvo `unidade`, prioridade 1 e condição `existe_boleto`.
Comparam original integral `Boleto.composicao.total_original == Decimal('0.01')`
ou apontamento exato A/AJ/J no namespace validado. Prazo permanece individual,
`dias_atraso > 30`, prioridade 0, sob data explícita. Sem filtros judiciais ou
autônomos de garantidora. Nenhum plano real foi aprovado, assinado ou ativado.

Cada grupo preserva as avaliações da unidade e todos os boletos causadores com
regra, versão e origem. Decisões individuais referenciam esse grupo, sem duplicar
ou consolidar dívidas. Ausência/inconclusão de evidência mantém revisão. Veto de
uma unidade não atinge outra. Indeterminações e bloqueios críticos não autorizam
cobrança.

## Evidências privadas — referência 23/10/2026

| Indicador | Antes | Depois |
|---|---:|---:|
| Unidades/cotas reais | 112 | 112 |
| Boletos | 769 | 769 |
| Rótulo indevido de quantidade de cotas | 769 | Corrigido para 112 |
| Unidades com algum boleto financeiramente selecionado | 35 | 15 |
| Boletos financeiramente selecionados | 138 | 63 |
| Dívidas efetivamente geradas | 0 | 0 |

Depois: 71 cotas vetadas por centavo, oito por A/AJ/J, total de 79 cotas vetadas e
682 boletos excluídos coletivamente. Nas demais unidades, 24 boletos não atingem o
prazo; 18 unidades ficam sem boleto no prazo. Os 75 boletos antes indevidamente
selecionados passam a ser excluídos pelos vetos do conjunto.

O responsável confirmou que `2829 - TREE MORUMBI.xlsx` é renomeação da referência
privada inventariada. **63/63** pares unidade/boleto e respectivos vencimentos e
valores coincidem, distribuídos em **15 contratos**. Nenhum valor foi ajustado.
Uma anotação fora das 30 colunas na referência permanece classificada como
formatação; não é copiada. Competências ausentes continuam ausentes.

O bloqueio Habita/VG permanece: **112 cotas e 769 boletos retidos tecnicamente**,
inclusive os 63 selecionados financeiramente. A: 63 dívidas previstas, zero
geradas. B: mesmas 63 dívidas previstas e 103 cadastros previstos, todos retidos;
zero gerados. Não foi produzido XLSX TREE nem removido bloqueio para obter
coincidência. A correspondência financeira não equivale a homologação operacional.

Canônico completo preservado byte a byte, incluindo valores, IDs e componentes;
33 continuidades preservadas. As 904 ocorrências históricas mantêm IDs e conteúdo.
Ocorrências da nova leitura possuem os IDs da nova execução e conteúdo/origem
equivalentes. Fontes e arquivos históricos permanecem íntegros e privados.

**PLAZA:** 50 unidades, 115 boletos, 69 selecionados e 46 fora do prazo. Modo A:
69 dívidas; B: 69 dívidas + 46 cadastros. XLSX de teste idênticos byte a byte aos
anteriores, incluindo as 30 colunas, documentos textuais e parcelas sequenciais.
Conflitos documentais continuam sujeitos aos controles existentes.

## Interface, testes e limites

A interface distingue quantidades de unidades e boletos, veto coletivo, seleção
por prazo e retenção técnica. Grupos expansíveis mostram boletos, componentes e
causadores. `resumo.cotas` agora conta unidades; `resumo.boletos` conta boletos.
O campo legado `decisoes[].cota` continua como alias do identificador do boleto
para compatibilidade; usar `boleto`, `cota_id` e `cotas[]` nas novas consultas.
Campos antigos de contagem por regra continuam contadores de boletos; a interface
usa os novos campos explícitos. Auditoria mantém a versão diagnóstica aplicada.

**1.259 testes aprovados**: 1.199 regulares e 60 suítes explícitas, com 16 novos
casos sintéticos. Oito verificações de schemas aprovadas. Casos: dez centavos
numa unidade; veto por único boleto, inclusive recente; A/AJ/J; múltiplos vetos;
componente isolado de centavo; dia 30/31; unidades independentes; continuidade;
modos A/B; bloqueio técnico e apontamento inconclusivo. Chromium: expansão de
componentes/causadores, retenção independente da régua, mobile, downloads e
regressão da remoção de arquivos sem recarga, sem erros de JavaScript.

Detalhes por unidade, documentos e resultados reais ficam exclusivamente na área
privada. Permanecem pendentes o subtotal Habita/VG, a homologação dos identificadores
TREE e a compatibilidade integral de importação. Sem Fase 5, CRM, push ou merge.
Sistema **não homologado para produção**.
