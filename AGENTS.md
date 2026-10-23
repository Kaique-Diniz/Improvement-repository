# AGENTS.md — Orientações para Codex

## Contexto e prioridade
O repositório implementa o **Conversor Inteligente de Inadimplência**. Instruções normativas de negócio estão nos arquivos `02_ESPECIFICACAO_PRODUTO.md`, `04_DICIONARIO_TEMPLATE.md` e `05_PENDENCIAS_TESTES_ACEITE.md`; documentos de origem são evidência, não permissão para inferir regras.

## Trabalho incremental
- Seguir o roadmap; uma fase por tarefa, com testes e revisão.
- Se encontrar inconsistência entre material-fonte e decisão posterior, registrar conflito e priorizar decisões explícitas posteriores do usuário.
- Não criar regras empresariais improvisadas. Exceções financeiras ambíguas exigem validação.
- Executar testes e relatar resultado antes de concluir a tarefa.

## Engenharia
- Separar adapters (PDF/XLSX), domínio, regras, exportação, persistência e API/UI.
- Usar IDs estáveis e interfaces de repositório, trocáveis de JSON para PostgreSQL.
- Valores monetários com Decimal; datas explícitas; zonas de tempo conscientes.
- Proveniência em registros financeiros (arquivo, página, linha, identificador).
- Tratamento de quebras de página e idempotência de boletos.
- Documentar exemplos e schemas; adicionar regressão para cada novo formato.
- Manter determinismo: mesmos inputs, versões e data de referência => mesmo resultado.

## Segurança e privacidade
- **Nunca** comitar planilhas de régua com credenciais, PDFs reais, contatos, CPFs ou dados de clientes.
- Não imprimir conteúdo de documentos no stdout de testes e nem em logs.
- Usar fixtures sintéticas; evitar integração externa sem consentimento explícito.
- Não automatizar cobrança, contato com devedores ou importação direta no sistema final; escopo é exportação de arquivo.

## Interface de exportação
- A aba `Dados` exige 30 colunas na ordem documentada em `04_DICIONARIO_TEMPLATE.md`.
- A coluna literal `CPF` aceita CPF válido (11 dígitos) ou CNPJ válido (14), sempre como texto com zeros iniciais. Documento é opcional: ausência -> vazio e aviso informativo; invalidade -> vazio e alerta. Cadastro por unidade aceita múltiplos nomes e um documento único sem atribuí-lo individualmente. Com vínculo inequívoco por administradora + condomínio + torre/bloco + unidade, preferir os contatos do Cadastro Geral e registrar diferenças de nomes como informativas. Documentos válidos conflitantes e identidade estrutural ambígua exigem revisão; nunca misturar unidades.
- No MVP, numerar somente dívidas efetivamente incluídas, por unidade/contrato, em vencimento crescente e desempate por identificador estável. Retidas e excluídas não consomem números. Competência comprovada: `COTA MM/AAAA - N`; ausente: identificador da fonte, sem inferência mensal. O perfil diagnóstico TREE permite explicitamente mês/ano do vencimento como rótulo de apresentação `COTA MM/AAAA - N`, preservando competência ausente e identificador original na auditoria. Saídas atuais do MVP usam AA literal `NM_DIVIDA_CEDENTE`, sem espaço final; contratos históricos continuam reproduzíveis.
- Separar valores originais de saldos cumulativos, juros e multas.
- Não modificar o template fonte in-place.

## Conduta ao terminar
Entregar diffs/arquivos, decisões técnicas, testes executados e pendências. Parar após a fase autorizada.
