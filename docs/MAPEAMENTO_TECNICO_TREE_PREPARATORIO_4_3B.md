# Mapeamento técnico Habita/TREE — preparação do 4.3B

**22/10/2026. Validação de leitura e de campos, sem execução de regras reais.**
Conferido o PDF TREE já autorizado na área privada, com hash comparado ao
inventário original. Escopo: este arquivo/layout e os leitores existentes.
Não há atesto humano, plano real criado/aprovado/assinado/ativado, simulação
financeira, exportação operacional ou início da Fase 5. Sistema não homologado
para produção. Alterações de produção em leitores, domínio e motor: **nenhuma**.

## Correspondência financeira comprovada

A tabela do PDF tem cinco colunas financeiras, nesta ordem:
**Valor, Multa, Atualização Monetária, Juros, Total**. O rótulo Atualização
Monetária ocupa duas linhas no cabeçalho, sem criar uma sexta coluna.

| Campo na fonte | Significado e associação | Campo canônico / verificação |
|---|---|---|
| `Valor` na linha de composição | Valor original daquele componente, não automaticamente o boleto inteiro | `Boleto.composicao.itens[i].valor`, com origem de arquivo/hash/página/linha |
| `Valor` em `Total do boleto:` | Original integral da cota/boleto com vários componentes; fechamento, não novo componente | `Boleto.composicao.total_original`, igual à soma exata dos componentes e ao fechamento explícito |
| `Valor` de boleto com um único componente | A linha do próprio boleto representa também seu original integral; a fonte não apresenta fechamento separado nesses casos | Mesmo `Boleto.composicao.total_original`; soma de um item, sem fabricar linha de fechamento |
| `Multa` | Encargo por componente; totalizar apenas componentes do mesmo boleto | `Boleto.multa` |
| `Atualização Monetária` | Correção por componente, separada do original, multa e juros | `Boleto.correcao` |
| `Juros` | Juros por componente, separados da correção e do original | `Boleto.juros` |
| `Total` | Valor atualizado por linha ou fechamento | Sem campo canônico próprio para total atualizado. Nesta inspeção, confrontado com original + multa + correção + juros; não substituir original por esse total |
| Totais de unidade, bloco e geral | Fechamentos em outro escopo, não boletos/componentes adicionais | Usados para reconciliação; subtotal inconsistente continua ressalva crítica |

**Campo confirmado para comparar a cota integral com R$ 0,01:
`Boleto.composicao.total_original`.** O predicado existente `valor_original`
consulta exatamente esse campo em `src/conversor/rules/conditions.py`.
`Boleto.valor_original` não é um atributo do contrato atual. Não comparar a lista
de componentes por `qualquer item == 0.01`, nem usar encargos, total atualizado,
saldo ou total da unidade como valor integral do boleto.

O original integral é a soma em Decimal dos valores originais dos componentes do
mesmo boleto. Em boleto multicomponente, o fechamento explícito é conferido e não
somado novamente. Um componente de centavo numa cota maior não satisfaz o
predicado da cota; inversamente, uma cota de centavo pode ter total atualizado
diferente por encargos sem deixar de ter original de centavo.

A chave de associação do PDF é **condomínio + bloco/unidade + número do boleto**.
O canônico conserva unidade, identificador e origens dos componentes. Repetição
do cabeçalho na página seguinte não cria outro boleto. Competência não é necessária
para essa associação e continua ausente, sem inferência de vencimento/emissão.

## Apontamento → boleto

Na fonte, A, AJ ou J aparece como código próprio **entre o número de oito dígitos
do boleto e seu vencimento**, na linha inicial de composição. A posição horizontal
observada foi x=69,02 no espaço da página, antes de Vencimento (x=85,99).
Essas coordenadas são evidência deste PDF, não novas constantes universais do leitor.

O leitor existente usa a estrutura da linha, não procura letras em textos livres:
`número [A|AJ|J] vencimento ... cinco valores`. A letra em histórico/descrição não
ocupa o campo de apontamento. Comparação de código é exata: AJ não vira A ou J.
O canônico registra:

- `Boleto.apontamentos[].codigo_original`: código da fonte.
- `namespace_formato`: `ContextoLeitura.formato_id`, não um namespace financeiro universal.
- `origem`: primeira linha de composição do respectivo boleto, incluindo arquivo,
  hash, leitor/versão, página e linha.

Os cabeçalhos de continuação repetem o mesmo código; o leitor mantém um
apontamento por boleto e todas as origens dos componentes. Divergência de código
na continuação é rejeitada, sem escolher uma versão. Os códigos fora da posição
financeira não foram transformados em apontamentos. Não se interpretou a legenda
como regra ou como evidência de que um boleto possui apontamento.

A condição é fato da cota, independente do vencimento. Uma futura configuração
TREE deverá excluir a cota/componentes se houver **centavo OU A OU AJ OU J**, sem
excluir automaticamente outras cotas. Isso permanece uma decisão de negócio;
nesta tarefa não se produziram decisões financeiras de inclusão/exclusão.

Lista vazia de apontamentos **não** substitui `CoberturaApontamentos`. O avaliador
existente exige evidência de completude do campo/namespace para concluir ausência;
sem cobertura, a condição negativa continua indeterminada. Esta inspeção não cria
coberturas humanas, atestos ou pacotes assinados automaticamente.

## Evidências da inspeção privada

O procedimento refez a leitura operacional e uma inspeção independente das cinco
colunas, associando linhas e fechamentos aos boletos. Não importou as regex ou a
função monetária do leitor para o confronto independente. A geometria dos códigos
foi confrontada com os fragmentos do PDF. Todos os itens/origens, totais originais,
encargos e apontamentos foram comparados ao canônico; a nova leitura também é
integralmente igual ao canônico preservado da Fase 3.

| Verificação | Resultado agregado |
|---|---:|
| Páginas / cabeçalhos financeiros | 149 / 149 |
| Unidades / boletos únicos / componentes | 112 / 769 / 2.082 |
| Boletos multicomponentes e fechamentos explícitos conferidos | 326 |
| Boletos de componente único, sem fechamento separado | 443 |
| Cabeçalhos de boleto observados / repetições por continuidade | 802 / 33 |
| Boletos com componentes atravessando páginas | 33 |
| Boletos com original integral de centavo | 426 |
| Componentes de centavo em boleto cujo total original é diferente | 0 neste arquivo; contraprova coberta por fixture sintética |
| Boletos com A / AJ / J | 15 / 9 / 117 |
| Linhas com A / AJ / J, incluindo continuação | 18 / 10 / 132 |
| Códigos isolados fora da posição de apontamento, não associados aos boletos | 447 |
| Divergências de inventário, valores e apontamentos no confronto | 0 |
| Competências ausentes preservadas | 769 |
| Arquivos privados anteriores com hash preservado | 122 |

As contagens são de **leitura**, não cotas autorizadas, selecionadas ou excluídas
pela régua. Nenhum total financeiro individual, titular ou documento aparece
neste relatório público. O bloqueio crítico **Habita/VG permanece no lote**;
nenhuma interpretação de Valor/apontamento o remove. Impedimentos FL e demais
artefatos privados não foram alterados.

## Dossiê privado e reprodução

Fora do Git, em
`/workspace/validacao-privada-fase3/resultados/mapeamento_tree_preparatorio_4_3B_008/`:

- `validar_mapeamento_privado.py`: inspeção reproduzível, sem chamada ao motor,
  simulação, repositório de planos ou exportador; não enviar a fontes externas.
- `manifesto_fontes_e_preservacao_privado.json`: identificação/hash/tamanho da
  fonte, versão do leitor e hashes dos artefatos anteriores.
- `mapeamento_por_boleto_privado.json`: valores por coluna e componente, chave
  do boleto, fechamentos, apontamentos e suas páginas/linhas/coordenadas.
- `resumo_sem_dados_pessoais.json`: verificações agregadas, sem autorização operacional.
- `runtime_e_codigo_privado.json`: versões Python/dependências, revisão Git e
  hashes do código e script usados para reprodução.

Arquivos 0600 e diretório 0700. Dados completos e hashes reais ficam privados.
O manifesto é diagnóstico técnico, **não** recibo de aprovação/atesto ou nova
assinatura de pacote. Contratos, IDs, pacotes 1.0/1.1 e originais são preservados.
Para reproduzir, usar a mesma fonte/hash, contexto, versões e ambiente Python do
projeto, e executar o script privado com `.venv/bin/python`. Resultado divergente
exige investigação, não atualização silenciosa do histórico.

## Casos sintéticos automatizados

Fixture criada do zero:
`tests/fixtures/synthetic/habita_mapeamento_4_3b.json`. Gerador de PDF:
`examples/fase4/habita_mapeamento_sintetico.py`. Suíte:
`tests/phase3/test_habita_rule_mapping.py`.

| Caso | O que se verifica |
|---|---|
| Componente de centavo em cota com outros componentes | Total original da cota não satisfaz igualdade a centavo |
| Cota integral de centavo com encargos | Predicado usa original, não total atualizado |
| Original de centavo composto de itens diferentes de centavo | Comparar soma integral, sem exigir um componente de centavo |
| Multa/correção/juros distintos | Ordem e separação dos campos preservadas |
| A, AJ e J em vários boletos da mesma unidade | Código/namespace/origem ligados só ao boleto correspondente; outros não herdam apontamento |
| Legendas, observações e descrições contendo os códigos | Não criar apontamento; AJ não casa parcialmente com A |
| Ausência de cobertura ou namespace diferente | Indeterminação segura, sem ausência presumida |
| Vencimento futuro, dia zero, dia 30 e 31 | Fatos centavo/apontamento independem da data; prazo é estritamente >30 dias corridos |
| Continuidade com cabeçalho repetido | Sem duplicar boleto, componente ou apontamento; origem/hash e vínculo entre páginas preservados |
| Código desconhecido, código divergente na continuação e fechamento inconsistente | Rejeição, sem correção por aproximação |
| Subtotal crítico inconsistente | Boletos/evidências continuam presentes e o lote permanece bloqueado |

Os testes executam leitor e predicados puros em dados inventados. Usam plano
**sintético apenas em memória**, não aprovado e sem eventos administrativos,
para respeitar o contrato do contexto. Não executam o motor, não escolhem cotas
reais, não implementam as quatro exclusões operacionais ou o exportador.

### Execução e resultados

```bash
.venv/bin/python -m pytest -q tests/phase3/test_habita_rule_mapping.py
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

**43 testes novos aprovados. Regressão completa: 855 regulares + 60 explícitos
= 915 aprovados**, sem falhas ou skips, preservando os 872 anteriores. As seis
verificações `--check` de schemas (catálogo, reconhecimento, planos, avaliação,
simulação privada e auditoria) passaram, sem regenerar contratos.

Conferência complementar de privacidade: **217 arquivos versionáveis** examinados,
sem cópias idênticas dos anexos reais, correspondências identificáveis verificadas
ou permissões privadas divergentes. Isso não substitui revisão humana nem prova
detecção universal de dados sensíveis. Somente relatório agregado, dados
sintéticos e código de testes/geração de fixtures ficam no checkout. Artefatos
privados permanecem fora do Git; não houve push, merge ou novo commit nesta tarefa.

## Ambiguidades e condições para continuidade

**Não foi encontrada ambiguidade impeditiva no mapeamento financeiro ou de
apontamentos deste PDF.** O campo canônico integral e a associação aos boletos
estão tecnicamente confirmados para o conjunto inspecionado. Não houve necessidade
de modificar leitores, contratos ou valores.

Permanecem necessários antes de qualquer execução real:

- Atestos humanos de completude e vínculo à régua/versão vigente; esta conferência
  automática não os substitui.
- Aprovação formal de plano/versão/hash, prioridades numéricas e vigências,
  garantindo que nenhuma permissão por prazo anule as exclusões de cota.
- Tratamento documentado de cobertura negativa dos apontamentos e fontes completas.
  Códigos/campos deslocados, novos layouts ou vários códigos na mesma célula não
  foram homologados por esta amostra e exigirão validação própria, sem interpretação livre.
- Referência explícita e modo universal A/B por execução, auditoria independente
  e preservação das 30 colunas/CPF/CNPJ textual; saída operacional permanece Fase 5.
- Decisão própria sobre bloqueios de lote, unidade, titularidade e documentos.
  O subtotal VG continua impedindo operação no lote, mesmo com mapeamento correto.
- Autorização posterior delimitada para o 4.3B efetivo; esta tarefa é somente
  validação técnica preparatória, não homologação de regras reais ou produção.
