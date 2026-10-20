# 06 — Prompt pronto para enviar ao Codex

Você vai desenvolver uma ferramenta brasileira chamada **Conversor Inteligente de Inadimplência**.

## Contexto obrigatório
Leia e obedeça os documentos deste repositório nesta ordem:
1. `AGENTS.md`
2. `01_PLANO_ETAPAS.md`
3. `02_ESPECIFICACAO_PRODUTO.md`
4. `03_MODELO_DADOS_JSON.md`
5. `04_DICIONARIO_TEMPLATE.md`
6. `05_PENDENCIAS_TESTES_ACEITE.md`
7. `FONTES_E_IMPORTACAO.md`

A aplicação irá reconhecer formatos variados de relatórios de inadimplência de administradoras de condomínios, extrair dados para um modelo comum, aplicar réguas de cobrança específicas, enriquecer com Cadastro Geral e gerar um Excel de 30 colunas. Deve haver bloqueios automáticos quando existir risco de cobrança incorreta. Um CPF ausente não é bloqueante: fica em branco e gera alerta. CNPJ não pode ocupar o campo CPF.

## Solicitação: **implemente somente a Fase 1**
1. Proponha a estrutura modular do projeto, com arquitetura pronta para leitores de centenas de formatos e regras por condomínio; sem assumir um leitor por condomínio.
2. Crie entidades de domínio, validações e interfaces de repositório separando regra, administradora, condomínio, formato, template e histórico.
3. Crie o repositório JSON com leitura, escrita atômica, integridade referencial, versão de schema, erro explícito e testes. Dados reais/credenciais **nunca** devem ser comitados.
4. Defina e teste o contrato de modelo canônico `Unidade`, `Pessoa/Contato`, `Boleto`, `Composicao`, `Apontamento`, `Origem`, `ResultadoCobranca` e `Ocorrencia`.
5. Modele e teste o contrato de exportação universal com as 30 colunas na ordem exata, incluindo linha de dívida vs cadastral, mas **não precisa implementar ainda a extração PDF**.
6. Crie fixtures 100% sintéticas, testes automatizados, README de execução local e exemplos de configuração sem dados pessoais.
7. Documente decisões técnicas e pontos que precisam ser homologados. Não invente interpretações das particularidades da régua.
8. Ao concluir, mostre resumo de arquivos criados, comando de testes e limitações, e pare aguardando aprovação da próxima fase.

## Restrições inegociáveis
- Não desenvolver múltiplas fases numa única tarefa.
- Sem OCR/LLM como única fonte de verdade de valor financeiro.
- CPF ausente -> célula vazia + alerta; nunca inserir CNPJ no campo CPF.
- A arquitetura deverá permitir JSON -> PostgreSQL sem reescrever os casos de uso.
- Não logar senhas/tokens nem expor dados pessoais.
- Dados de exemplo reais (PDFs e régua) serão disponibilizados separadamente em ambiente autorizado, sem commit.
- Diferenciar formato conhecido validado, desconhecido e ambíguo; nunca presumir classificação.
- Priorizar testes determinísticos, pequenos commits e documentação verificável.

Se um detalhe não aprovado for imprescindível para a Fase 1, registre a hipótese como decisão provisória, explique impacto e peça confirmação. Não transforme proposta em regra de cobrança aprovada.
