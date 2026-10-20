# Dossiê de transferência ao Codex — Conversor Inteligente de Inadimplência

**Status:** especificação para desenvolvimento incremental, sem software implementado.  
**Atualização:** 20/10/2026.  
**Idioma do projeto:** português brasileiro.

## Objetivo
Converter relatórios de inadimplência (PDF, XLSX e arquivos complementares) de múltiplas administradoras em um único modelo Excel com 30 colunas, aplicando a régua de cobrança de cada condomínio, com detecção automática de layout, alertas, bloqueios de segurança e auditoria.

## O que compõe este pacote

- `01_PLANO_ETAPAS.md`: fases, dependências, entregáveis e pontos de controle.
- `02_ESPECIFICACAO_PRODUTO.md`: requisitos e comportamento do produto.
- `03_MODELO_DADOS_JSON.md`: entidades, relacionamentos e persistência inicial.
- `04_DICIONARIO_TEMPLATE.md`: contrato de saída, 30 campos e tratamento de linhas.
- `05_PENDENCIAS_TESTES_ACEITE.md`: decisões em aberto, cenários de testes e condições de liberação.
- `06_PROMPT_INICIAL_CODEX.md`: instruções prontas para iniciar a primeira tarefa.
- `AGENTS.md`: guia de implementação, segurança e testes para uso no repositório.
- `FONTES_E_IMPORTACAO.md`: documentos de origem e processo recomendado para entregá-los com segurança.
- `config_exemplos/*.json`: exemplos **não operacionais** de configuração. Não contém CPF, senhas ou clientes reais.

## Como usar

1. Leia `01_PLANO_ETAPAS.md`, depois `02_ESPECIFICACAO_PRODUTO.md` e `05_PENDENCIAS_TESTES_ACEITE.md`.
2. Coloque os documentos `.md`, `AGENTS.md` e `config_exemplos/` em um repositório **privado** para o Codex.
3. Não faça commit de relatórios reais, da régua completa ou de cadastros com dados pessoais/credenciais.
4. Disponibilize arquivos reais ao ambiente autorizado de teste por um caminho seguro e privado, somente quando necessário.
5. Envie a tarefa do arquivo `06_PROMPT_INICIAL_CODEX.md` ao Codex, **implementando apenas a Fase 1**.
6. Revise testes e entregas de cada fase antes de pedir a próxima.

Este pacote substitui a necessidade de colar o histórico integral de conversa no prompt. O PDF com a conversa do Claude é uma referência adicional, não a fonte normativa quando divergir destas decisões posteriores.
