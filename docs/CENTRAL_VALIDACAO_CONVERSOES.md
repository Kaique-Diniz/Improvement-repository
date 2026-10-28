# Marco de homologação e Central de Validação de Conversões

## Base homologada em testes locais (28/10/2026)

O usuário realizou testes no Windows com documentos privados da BBZ. O cenário ABROLHOS sem reenvio do template histórico e com aprovações individuais dos vínculos produziu, segundo conferência dos arquivos de saída na conversa:

- **Modo A:** 103 dívidas de 25 unidades; R$ 94.970,42.
- **Modo B:** 103 dívidas + 24 cadastros adicionais = 127 linhas; mesmo total financeiro.
- **Escopo:** 65 unidades sem prova individual permanecem retidas.
- **Pendências:** duas unidades com documentos/contatos conflitantes (9 linhas financeiras), sem liberação dos campos protegidos; 4 descrições `RECIBO` neutras.
- **Equivalência:** arquivos A e B sem template histórico relatados como idênticos aos XLSX de base obtidos com referência. Este documento **registra resultado de homologação humana**, não incorpora arquivos privados no Git nem equivale a homologação de importação/produção.

Persistência dos vínculos, revisão e revogação permanecem em `--private-dir` com histórico íntegro; **não apagar nem copiar chaves, evidências ou arquivos privados para o Git**.

## Nova etapa: Central de Validação de Conversões — MVP

Implementada inicialmente na branch `feature/central-validacao-conversoes`. Tem como função **conferir os bytes do Excel diagnóstico efetivamente gerado**, confrontando o conteúdo com as linhas materiais planejadas pelo contrato, decisões de elegibilidade, identificadores de unidades e retenções conhecidas. Não é um segundo motor financeiro nem autoriza cobranças.

### Verificações e resultados

- **Estrutura:** apenas aba `Dados`, cabeçalhos e ordem das 30 colunas, número de linhas, ausência de fórmulas.
- **Conteúdo:** cada célula comparada com o valor planejado; vencimento como data, documento como texto, dívida positiva, soma financeira e cadastros adicionais com Y:AD vazias.
- **Rastreabilidade e retenções:** confronto entre boletos elegíveis e linhas destinadas ao XLSX, pertencimento comprovado quando requerido e documento/contatos vazios para unidades com retenção persistente.
- **Ressalvas:** quantidade de boletos em revisão, unidade sem escopo comprovado e unidades com dados de contato/documento retidos.
- **Estados:** `conforme`, `conforme_com_ressalvas`, `erro_critico` e `sem_arquivo`. Um erro crítico desabilita o endpoint de download do XLSX; arquivo e laudo permanecem privados para auditoria.

O relatório de validação não contém nomes de titulares, CPFs, contatos ou valores individuais. Permanece acessível apenas na mesma sessão autenticada do processamento, inclusive como `validacao-conversao.json`. O manifesto indica o arquivo e o estado da validação; o resultado da análise mostra um painel legível.

### Limitações explícitas

O validador garante **consistência do XLSX com as linhas e decisões fornecidas pelo próprio processamento**, mas não prova que as decisões estejam corretas perante documentos ambíguos. Não declara que todos os números de uma fonte foram extraídos corretamente e não inventa gabarito financeiro quando não há comparação externa. Conflitos cadastrais legítimos geram ressalvas quando os campos protegidos permanecerem vazios; o sistema nunca os desbloqueia automaticamente.

## Homologação exigida antes de merge

1. Executar `python -m pytest -q tests/test_conversion_validation.py` e a suíte completa `python -m pytest -q` na branch.
2. Rodar os testes de contratos, schemas e regressões existentes (incluindo ABROLHOS) em ambiente de desenvolvimento.
3. No Windows, processar novamente ABROLHOS em modos A e B **sem referência**, usando a pasta privada original; confirmar saídas idênticas aos baselines e sem alteração das aprovações.
4. Conferir painel, laudo e bloqueio de download em cenários sintéticos com falha de cabeçalho/valor ou contato indevidamente exibido.
5. Validar TREE, PLAZA, NOVA YORK, INNOVA BLUE, NOVA REBOUÇAS e WIN sem diferenças em seus XLSX.
6. Só então abrir/revisar PR e integrar a branch à `main`. A referência de homologação de 28/10/2026 permanece diagnóstico local, sem exportação operacional.
