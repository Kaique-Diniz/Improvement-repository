# Documentos de origem e transferência segura para o Codex

## Documentos disponibilizados nesta conversa

| Documento | Uso previsto | Observação |
|---|---|---|
| `Claude.pdf` | Contexto histórico e correções de interpretação | Regras posteriores deste dossiê prevalecem em divergências |
| `REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx` | Fonte atual da régua geral | Aba `RÉGUA DE COBRANÇA`: A1:I710, 709 linhas de registros após o cabeçalho; inclui informações de acesso/credenciais em textos |
| `TEMPLATE - PLAZA_MAYOR_IPIRANGA_outubro_2026(1).xlsx` | Exemplo de XLSX final | Aba `Dados`, 30 colunas, 112 linhas de dados, 43 linhas com 6 últimos campos vazios |
| `InadimplenciaAtualizada.pdf` | Relatório de entrada Habita / TREE MORUMBI | 149 páginas; não é XLSX de referência confirmado para Tree |
| `Devedores PMI 14.10.pdf` | Relatório de entrada FL / Plaza Mayor | 24 páginas, composição e saldos acumulados |
| `Cadastro Geral- PMI.pdf` | Complemento de identificação dos titulares e contatos | 25 páginas; contém dados pessoais |
| `PMI BLOCO A 14.10.xlsx` até `PMI BLOCO G 14.10.xlsx` | Fontes alternativas/tabulares de dados por torre | Servem a cruzamento e teste de extração |
| Imagens anexadas | Exemplos de identificadores de cedente diferentes | Devem ser convertidas em fixtures sintéticas antes de ir ao repo |

**Nota:** a versão da régua 19/10/2026 e o template anterior foram substituídos pelos arquivos atualizados de 20/10/2026 (não sobrescrever histórico operacional, mas usar versão mais recente como referência desta especificação).

## Como transferir ao Codex
1. Crie **repositório privado** e adicione apenas os documentos deste pacote; preferir GitHub para Codex Cloud.
2. Utilize o arquivo `06_PROMPT_INICIAL_CODEX.md` como primeira tarefa.
3. Para os documentos reais, priorize acesso temporário/privado ao ambiente de desenvolvimento; não anexar o bruto a tickets públicos, commits ou prompts que serão compartilhados.
4. Uma cópia da régua para testes deve ter **credenciais, logins, tokens, e-mails/senhas de acesso e dados pessoais desnecessários removidos**. Manter somente código/administradora/condomínio/campos de regras pertinentes ao exemplo.
5. Criar fixtures com CPF, nomes, e-mails, endereços e boletos **fictícios** mantendo a estrutura e casos de borda.
6. Guardar referências/hash das fontes e versões usadas; validar saídas em ambiente isolado antes de importar no sistema de destino.

## Atenções observadas
- PDF Tree é **fonte de entrada**; há referência histórica a `TREE MORUMBI_OUTUBRO 2026.xlsx`, mas o arquivo não foi disponibilizado como XLSX nesta conversa. O **modelo universal de exportação** foi definido como Plaza Mayor.
- A regra de outro jurídico não pode ser inferida apenas por termos genéricos da FL.
- O cabeçalho `NM_DIVIDA_CEDENTE ` contém espaço final no XLSX recebido: teste obrigatório com destino.
- Referências do template manual não implicam que ele seja um gabarito perfeito; o cadastro antecipado pode ser opcional.
