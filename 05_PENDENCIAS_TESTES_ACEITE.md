# 05 — Pendências, decisões e plano de testes

## Decisões aprovadas

- JSON agora, PostgreSQL depois.
- Administradora -> muitos condomínios; condomínio -> uma administradora atual.
- Reconhecimento e processamento automático para formato conhecido **sem confirmação**.
- Segurança bloqueia inconsistências críticas; alertas não bloqueantes para CPF ausente.
- CPF é exclusivamente CPF; CNPJ não pode ser substituto no template.
- Template universal Plaza Mayor de 30 colunas; linhas cadastrais sem contrato/dívida.
- Régua de cobrança geral: versão atual `REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx`.
- Cadastro antecipado configurável (não obrigatório para todos).
- Mudanças de regra somente em versão revisada/aprovada.

## Pendências que podem ser decididas sem impedir Fase 1

| ID | Pergunta | Proposta para MVP | Quando decidir |
|---|---|---|---|
| P01 | Uma execução aceita vários condomínios? | Um por execução; múltiplos anexos do mesmo condomínio | Antes da interface |
| P02 | Data padrão para prazo da régua? | Data de processamento configurável, registrada na auditoria; checar corte estrito `>N` | Antes do motor |
| P03 | Novos formatos podem ser criados pela operação? | Inicialmente técnico/config JSON; futuro assistente visual | Antes da fase 7 |
| P04 | CPF de empresa/único CNPJ, proprietário múltiplo, titular divergente? | CPF vazio + alerta; nenhuma atribuição indevida | Antes da homologação de cadastros |
| P05 | Alterações entre cadastro geral e inadimplência com datas distintas? | Gerar ocorrência, não substituir automaticamente titular | Antes da fase 3 |
| P06 | Cabeçalho `NM_DIVIDA_CEDENTE ` com espaço final? | Compatibilidade fiel ao arquivo-base até teste contra importador | Antes da fase 5 |
| P07 | Modalidade judicial e exceções específicas: importação vs negociação? | Manter separadas; aplicar só condições aprovadas de importação | Antes da fase 4 |
| P08 | Quais casos devem bloquear lote todo vs somente registro? | Matriz explícita com tipo/severidade/escopo | Antes da fase 4 |
| P09 | Política de retenção e acesso a PDFs/CPFs? | Pasta temporária protegida com prazo definido, sem salvar conteúdo em logs | Antes da produção |
| P10 | Saída TREE MORUMBI de referência? | Criar fixture/gabarito aprovado com resultados esperados a partir do PDF; sem XLSX dourado confirmado na conversa | Antes dos testes finais |
| P11 | Qual stack e ambiente? | Python + testes; FastAPI/React opcionais a validar | Antes da UI |
| P12 | Sistema importador aceita CPF vazio, duplicados, valores e datas em quais tipos? | Homologar com importação controlada | **Bloqueante para produção** |

## Matriz mínima de testes

### Reconhecimento
- Habita/TREE reconhecido pelo conteúdo e layout; FL/PMI reconhecido por assinatura; rejeitar documento sem correspondência segura.
- Mesmo formato em outro condomínio não usar perfil errado.
- Formato desconhecido não é silenciosamente processado.

### Leitura
- Habita: 149 páginas, campos no cabeçalho, composição; apontamento no boleto; reconciliação de unidade.
- FL: 24 páginas, unidades TORRE A–G, 'Valor' por linha de composição e 'Saldo' cumulativo; notas entre boletos.
- Várias páginas: boleto e unidade continuam na página seguinte; **não duplicar**.
- Caso `BLDEP-UNI0040`: continuação de página não deve ser contada como novo boleto (histórico da conversa indicou 22, não 23).
- Comparar extração com XLSX blocos A–G, quando aplicável.

### Regras
- TREE: qualquer boleto de R$0,01 exclui unidade inteira; A/AJ/J exclui unidade; idade estritamente >30; valores sem acréscimos.
- FL: 17/09 vs 10/10 sob data de referência configurada; judicial 60 requer semântica aprovada; cadastro antecipado.
- Apontamento J em Habita não é automaticamente o mesmo que anotação 'Jurídico' em FL.
- Toda exclusão deve registrar condição, regra/versionamento e evidência.

### Contrato de saída
- 30 cabeçalhos exatos, ordem A:AD, aba Dados.
- CPF ausente e CNPJ sem CPF -> célula CPF vazia com ocorrência não bloqueante.
- Linhas cadastrais com Y:AD vazias; linhas de cobrança com data/valor corretos.
- Zeros iniciais preservados em CPF/CEP/códigos quando presentes.
- Reprocessar mesmas fontes/config/data produz saída determinística, sem duplicação.
- Plaza Mayor: 112 linhas de referência (69 com dívida, 43 cadastrais, 47 cedentes distintos) **somente como gabarito de comparação condicionado à mesma data/política/versões**; não copiar números para todas as execuções.

### Segurança
- Nenhuma senha/token/login da régua aparece no código, fixtures, relatório de saída ou log.
- Não incluir CPFs reais em repositório público.
- Possibilidade de auditar processamento sem expor o documento integral.

## Critério de aceite por fase
Teste automatizado verde + comparação amostral manual com fonte e registros de exceção + documentação de riscos/pontos não atendidos. Cada fase deve ter demonstrativo curto de como executá-la.
