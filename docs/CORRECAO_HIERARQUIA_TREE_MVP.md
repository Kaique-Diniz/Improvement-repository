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

**1.262 testes aprovados**: 1.202 regulares e 60 suítes explícitas, incluindo os
16 casos da hierarquia e três casos adicionais de escopo do subtotal. Oito
verificações de schemas aprovadas. Casos: dez centavos
numa unidade; veto por único boleto, inclusive recente; A/AJ/J; múltiplos vetos;
componente isolado de centavo; dia 30/31; unidades independentes; continuidade;
modos A/B; bloqueio técnico e apontamento inconclusivo. Chromium: expansão de
componentes/causadores, retenção independente da régua, mobile, downloads e
regressão da remoção de arquivos sem recarga, sem erros de JavaScript.

Detalhes por unidade, documentos e resultados reais ficam exclusivamente na área
privada. Permanecem pendentes o subtotal Habita/VG, a homologação dos identificadores
TREE e a compatibilidade integral de importação. Sem Fase 5, CRM, push ou merge.
Sistema **não homologado para produção**.

## Consolidação e investigação direta Habita/VG

Branch de revisão: `fix/mvp-consolidado-habita-vg`. `f40ea8e` (remoção individual
dos arquivos) já é ancestral de `67dfce2` (hierarquia TREE), assim como `c11d487`
(identificadores PLAZA). Não há duas versões concorrentes da interface a mesclar:
a versão integrada já contém as três correções. Não foi realizado merge ou push.

Conferência direta do PDF privado, com extração de texto e coordenadas, sem OCR ou
inferência de valores:

- **149 páginas**, 112 unidades, 769 boletos e **2.082 componentes**. Recontagem
  independente confrontou os cinco valores monetários, vencimentos, quantidades
  de componentes e suas páginas/linhas com o canônico. Nenhuma diferença.
- **95 fechamentos explícitos de unidade** e **326 de boleto** reconciliados. São
  os fechamentos impressos, não o número de unidades ou boletos conferidos.
  As 33 continuidades estão preservadas.
- Bloco VG: **15 unidades e 120 boletos**. Outros blocos: **649 boletos**.
- Na página **149**, linha de layout **15**, o PDF contém literalmente
  `Total do Bloco VG:`; na linha **17**, contém quantidade de unidades e
  `Total Geral:`. Coordenadas verticais dos rótulos: 419,07 e 404,90 pontos,
  respectivamente, abaixo do fechamento da última unidade. Não há outros
  subtotais de bloco impressos nesse arquivo.
- O **total geral coincide exatamente com a soma dos 769 boletos nas cinco
  colunas**: original, multa, atualização monetária, juros e total atualizado.
  O valor rotulado VG repete esse total geral; não coincide com a soma dos 120
  boletos VG. Sua diferença é exatamente a soma dos outros 649 boletos.

**Conclusão:** não foi comprovado erro de extração nem divergência aritmética dos
boletos com o total geral. Existe uma inconsistência documental de escopo: a
rotulagem atribui ao VG valores do condomínio inteiro. A hipótese de um fechamento
geral rotulado com o último bloco é compatível com os números e a posição, mas
isso não comprova a semântica do gerador. O leitor não confundiu os dois rótulos;
ambos existem separadamente na fonte. Reinterpretar silenciosamente o primeiro
como geral retiraria uma retenção crítica sem evidência suficiente.

**Bloqueio mantido**, sem alterar o leitor, os valores ou o histórico. Para
resolver essa pendência, é necessária evidência do escopo do fechamento no
relatório de origem ou um relatório com subtotal VG explicitamente reconciliado.
Não se exige nova resposta sobre as regras financeiras já definidas. Cálculos
monetários detalhados e localizações por registro permanecem exclusivamente em
`/workspace/validacao-privada-fase3/mvp/consolidacao_investigacao_vg/`.

### Reprocessamento integrado — 23/10/2026

| Indicador TREE | Modo A | Modo B |
|---|---:|---:|
| Cotas/unidades | 112 | 112 |
| Boletos | 769 | 769 |
| Cotas vetadas | 79 | 79 |
| Boletos selecionados financeiramente | 63 | 63 |
| Dívidas efetivamente produzidas | 0 | 0 |
| Cadastros adicionais efetivamente produzidos | 0 | 0 |
| Dívidas previstas, retidas | 63 | 63 |
| Cadastros adicionais previstos, retidos | 0 | 103 |
| Cotas / boletos retidos tecnicamente | 112 / 769 | 112 / 769 |

Os **63/63** boletos coincidem com a referência por unidade, identificador,
vencimento e valor. A interface conserva a seleção financeira, os motivos de veto
e `SUBTOTAL_BLOCO_DIVERGENTE` como impedimento técnico, inclusive nos detalhes de
cada retenção. Não foi gerado XLSX TREE.

Reprocessamento com histórico preservou as **904 ocorrências históricas**
integralmente, além do canônico byte a byte. Hashes das fontes e do histórico não
mudaram. Upload comum também foi exercitado no Chromium com os documentos reais,
sem catálogo, nos dois modos, sem capturas contendo dados pessoais.

PLAZA, upload comum com Cadastro atual, nos dois modos: **50 unidades, 115 boletos,
69 dívidas; modo B acrescenta 46 cadastros**. Canônico e XLSX de teste permanecem
idênticos byte a byte aos anteriores, preservando as parcelas, os identificadores,
as 30 colunas e os valores. Isso não resolve conflitos históricos conhecidos nem
autoriza exportação operacional.

Três testes sintéticos adicionais verificam: subtotal VG exclusivo correto;
subtotal VG repetindo o geral sem remoção automática do bloqueio; e subtotal
repetindo um geral aritmeticamente incorreto, que continua rejeitado. Chromium
também repetiu remoção dos três inputs, troca PLAZA → TREE na mesma sessão,
substituição da referência, invalidação de prévias/downloads, teclado e mobile.
Sem erros de JavaScript. Nenhum teste nativo do Windows foi executado.

### Atualização Windows após autorização de publicação

Os commits continuam locais. **Não executar a atualização esperando estas
correções na `main` antes da publicação autorizada.** Pare o servidor com Ctrl+C,
abra o PowerShell na pasta do projeto e, com a árvore de trabalho limpa, execute
após a integração autorizada no GitHub:

```powershell
git status --short
git switch main
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m pip install -e ".[web,test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m conversor.web --private-dir "C:\ConversorPrivado\mvp"
```

Use o diretório privado já adotado na instalação em lugar do caminho ilustrativo.
Confira então TREE e PLAZA com referência 23/10/2026 e modos A/B. Habita/VG deve
continuar retido enquanto a ambiguidade documental persistir. Sem exportação
operacional, CRM, novas fases ou homologação para produção.
