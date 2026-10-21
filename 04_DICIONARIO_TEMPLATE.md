# 04 — Contrato universal de exportação XLSX

## Referência verificada
Arquivo: `TEMPLATE - PLAZA_MAYOR_IPIRANGA_outubro_2026(1).xlsx`. Aba: **Dados**. 30 colunas `A:AD`, 112 linhas de dados. Destas, 43 têm os 6 campos finais (Y:AD) vazios. Existem 47 valores distintos de `CEDENTE` na referência.

### Colunas exatas na ordem definida pelo usuário

| Posição | Coluna | Origem / significado | Regra de preenchimento |
|---:|---|---|---|
| 1 | `NM_CEDENTE_CEDENTE` | Nome/código do cedente (perfil/administradora) | Obrigatório existir; conteúdo conforme perfil |
| 2 | `CEDENTE` | Identificador do cliente/cedente conforme perfil | Obrigatório existir; código não pode ser inventado |
| 3 | `CPF` | CPF válido (11 dígitos) ou CNPJ válido (14), associado ao titular | Texto obrigatório com zeros; ausente/inválido vazio + alerta; conflito exige revisão |
| 4 | `NOME` | Nome do titular/cliente | Nome obtido da origem/cadastro |
| 5 | `ENDERECO` | Logradouro | Texto cadastral |
| 6 | `NUMERO` | Número do endereço | Texto para preservar caracteres |
| 7 | `COMPLEMENTO` | Bloco/unidade/código no padrão do perfil | Texto conforme codificador do condomínio |
| 8 | `CEP` | CEP, conservar zeros à esquerda | Texto com zeros |
| 9 | `BAIRRO` | Bairro | Texto |
| 10 | `CIDADE` | Cidade | Texto |
| 11 | `UF` | UF | Sigla |
| 12 | `DDD1` | DDD do contato 1 | Texto |
| 13 | `FONE1` | Telefone do contato 1 | Texto |
| 14 | `DDD2` | DDD do contato 2 | Texto |
| 15 | `FONE2` | Telefone do contato 2 | Texto |
| 16 | `DDD3` | DDD do contato 3 | Texto |
| 17 | `FONE3` | Telefone do contato 3 | Texto |
| 18 | `DDD4` | DDD do contato 4 | Texto |
| 19 | `FONE4` | Telefone do contato 4 | Texto |
| 20 | `DDD5` | DDD do contato 5 | Texto |
| 21 | `FONE5` | Telefone do contato 5 | Texto |
| 22 | `EMAIL1` | E-mail 1 | Texto |
| 23 | `EMAIL2` | E-mail 2 | Texto |
| 24 | `EMAIL3` | E-mail 3 | Texto |
| 25 | `NM_CONTRATO_CEDENTE` | Identificador do contrato segundo o perfil | Vazio em linha cadastral |
| 26 | `PRODUTO_CEDENTE` | Produto/condomínio conforme perfil | Vazio em linha cadastral |
| 27 | `NM_DIVIDA_CEDENTE` | Nome da dívida/parcela conforme configuração | Vazio em linha cadastral |
| 28 | `NU_PARCELA` | Índice sequencial da parcela | Vazio em linha cadastral |
| 29 | `VENCIMENTO` | Data do vencimento | Vazio em linha cadastral |
| 30 | `VL_PARCELA` | Valor original da parcela, sem juros/multa quando regra assim determinar | Vazio em linha cadastral |

## Observação de compatibilidade de cabeçalho
O arquivo real possui **espaço final** no cabeçalho `NM_DIVIDA_CEDENTE ` da coluna AA. O nome lógico canônico é `NM_DIVIDA_CEDENTE`, sem espaço. **Pendente:** testar se o importador de destino exige o espaço final; não alterar uma nomenclatura de integração sem validação.

## Contratos de preenchimento
- A planilha sempre possui os **30 campos em mesma ordem** e a aba `Dados`.
- Campos de cadastro sem valor conhecido permanecem vazios, sem valores fabricados.
- `CPF` permanece o nome literal da coluna C: aceita CPF ou CNPJ válido, com dígitos verificadores, associado ao titular. Ausência/invalidade -> vazio + alerta. Conflitos entre documentos válidos ou vínculo não confirmado impedem resolução/exportação automática do cadastro e exigem revisão humana com auditoria das fontes.
- CPF e CNPJ são sempre gravados como texto literal, formato `@`, nunca números. CEP, telefone, DDD, CEDENTE e códigos com zeros também preservam representação textual. Nunca completar documentos inválidos por inferência.
- `VENCIMENTO`: data reconhecível/importável no Excel; confirmar convenção de serial e formato com destino.
- `VL_PARCELA`: número monetário com precisão de centavos, não string formatada com `R$`.
- Em linha cadastral (sem dívida), **Y:AD** (`NM_CONTRATO_CEDENTE`, `PRODUTO_CEDENTE`, `NM_DIVIDA_CEDENTE`, `NU_PARCELA`, `VENCIMENTO`, `VL_PARCELA`) devem permanecer vazias.
- Em linha com dívida, as 6 colunas finais devem refletir exatamente contrato, produto, competência, parcela, vencimento e valor elegíveis segundo perfil/regra.
- Uma mesma unidade pode ter uma linha cadastral além de linhas com dívidas caso política/perfil/exemplo homologado assim estabeleça.
- Evitar fórmulas ou macros nos campos de dados; não alterar o template original em disco.

## Compatibilidade documental confirmada — easyCollector

Em 21/10/2026 o responsável pelo processo confirmou que o CRM easyCollector
aceita CPF e CNPJ na coluna literal `CPF`. Esse requisito está aprovado. A
homologação integral dos demais campos, formatos e comportamentos de importação
permanece pendente; não foi realizada importação no destino nesta tarefa.
