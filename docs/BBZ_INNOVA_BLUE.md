# INNOVA BLUE — expansão diagnóstica BBZ

Somente o piloto INNOVA foi habilitado nesta entrega. WIN, NOVA REBOUÇAS e
ABROLHOS continuam bloqueados. Não há plano operacional aprovado/ativo,
integração easyCollector, cobrança automática ou homologação para produção.

## Implementação

| Componente | Alteração |
|---|---|
| `readers/bbz_xlsx.py` | Preserva linha de recibo sem Conta/Histórico somente quando ambos estão ausentes, as seis colunas monetárias são zero e não há outro componente; exige todos os fechamentos. Não inventa histórico. |
| `readers/bbz_cadastro.py` | Aceita `Condominio`/`Condomínio`; usa posições dos rótulos em faixas validadas para CNPJ, unidade e cliente, inclusive fragmentação dos dois-pontos. Mantém CNPJ válido, identidade consistente, paginação e resumo obrigatórios. |
| `application/debt_descriptions.py` | Política adicional `descricao_obrigacao_bbz_condominio@1.0.0`, selecionada explicitamente pelo perfil; reconhece `CONDOMINIO MM/AAAA` e `COND MM/AAAA`, com nomes de meses documentais. Não infere século, vencimento ou competência. A política NOVA YORK 1.1.0 permanece intacta. |
| `web/perfis.json` | Identidade do catálogo existente: destino 363, origem 1392; hipótese diagnóstica `atraso > 31`, original zero excluído individualmente e elegível para cadastro B. Sem filtro judicial ou veto TREE. |
| `web/perfis_saida.json` | Reutiliza `bloco_unidade_textual`: `Bloc{BLOCO}-Uni{UNIDADE}`; largura numérica quatro comprovada, palavras e blocos preservados. Cedente, complemento e contrato compartilham o código. Sem sufixo 363. |
| `web/service.py` e interface | Seleção manual/automática INNOVA, Cadastro opcional, motivo financeiro específico para zero e indicador separado do prazo. Mesmos controles de acesso e de diagnóstico. |
| `export/historical_comparison.py` | Sufixo histórico de parcela é formatação somente quando coincide com a descrição documental acrescida do número da parcela do próprio histórico. A parcela atual é conferida separadamente. Não altera dados nem seleção. |

Não foram copiados leitores por condomínio. Cadastro por papel, documentos,
telefones, endereço prioritário, parcelas, auditoria, contrato de 30 colunas e
motor determinístico são reutilizados. Nenhum arquivo original foi alterado.

## Evidências técnicas privadas

| Conferência | Resultado |
|---|---:|
| Unidades financeiras / recibos / componentes | 108 / 645 / 4.095 |
| Recibos com original positivo / original zero | 639 / 6 |
| Páginas / unidades cadastrais | 328 / 885 |
| Cabeçalhos / continuações cadastrais | 1.196 / 311 |
| Unidades financeiras localizadas | 108 |
| Unidades com documento válido associado | 108 |
| Telefones / e-mails aproveitados, por unidade | 76 / 156 |
| Associações retidas entre financeiro e Cadastro atual | 0 |
| Modo A / modo B, com ou sem Cadastro | 639 dívidas / mesmas 639 + 6 cadastros |

Todas as seis colunas monetárias são conferidas por componente, recibo, unidade
e condomínio. Composições negativas e positivas, marcadores, zeros e origens
são preservados. Os valores e os relatórios por registro ficam somente na área
privada. Recibos zerados não consomem parcela nem geram dívida; Y:AD permanecem
vazias nos seis cadastros. Não se incluem as demais unidades do Cadastro Geral.

O vínculo cadastral exige administradora + condomínio + bloco/unidade e nome
comprovado, preservando os papéis. Documentos ausentes/inválidos são opcionais,
com alertas; conflitos reais retêm a associação. Endereço físico explícito do
cabeçalho é utilizado quando segmentável; o cadastro privado do usuário prevalece
nas seis colunas de endereço, preservando complemento e evidências divergentes.

## Comparação com a referência histórica

- 637 dívidas possuem identidade literal, vencimento e valor coincidentes.
- Duas linhas históricas PASTEL/bloco 0 têm candidatos investigativos no bloco
  INAT, confirmado pelas duas fontes atuais. Não há equivalência automática,
  mudança de CEDENTE ou alegação de correspondência literal 639/639.
- Há 554 descrições documentais com diferença apenas do sufixo histórico da
  parcela. Outras 85 dívidas usam descrição neutra e alerta por insuficiência ou
  ambiguidade; incluem os dois casos INAT. Não copiar competência do template.
  Os seis zeros também conservam seus históricos ausentes, sem dívida exportada.
- Existem diferenças de endereço, contatos, documento e sequência histórica de
  parcelas, registradas individualmente no comparativo privado. A referência não
  substitui o Cadastro atual ou a ordenação determinística por vencimento e ID.
  Oito linhas de duas unidades apresentam documentos históricos válidos distintos
  do Cadastro atual; exigem conferência do histórico, sem mistura entre fontes.
  Em seis linhas a parcela histórica é uma posição maior e pertence a unidade
  com recibo zerado: a saída atual não consome parcela para esses recibos.
- Diferenças de representação de datas não são divergências financeiras.
  Nenhum valor foi alterado para reproduzir o histórico.

## Execução e pendências

No upload comum, selecionar o XLSX, Cadastro BBZ PDF opcional e referência
opcional; escolher explicitamente `26/10/2026` nesta conferência e modo A/B.
O processamento não depende de inventário histórico do Codex. As fontes são
identificadas pelo conteúdo/catalogação, não pelo nome do arquivo.

Artefatos e relatório individual: diretório privado
`bbz/innova_blue/diagnosticos_finais/{com_cadastro,sem_cadastro}/{A,B}/`.
O inventário privado registra nome, bytes, SHA-256 e a régua exata; a referência
de regras está na aba `RÉGUA DE COBRANÇA`, E523. Observações de acordos e acesso
não são ativadas como regras; conteúdo sensível não integra o repositório.

Pendências: confirmar inclusividade do prazo antes de uso operacional; comprovar
vigência; revisar descrições não comprovadas, diferenças do histórico e eventual
equivalência INAT/0 por decisão humana. Não foi criado esse mapeamento. Teste
nativo Windows e homologação operacional continuam pendentes.

**1.661 testes aprovados**: 1.601 regulares e 60 nas três suítes históricas
explícitas, incluindo 56 novos casos sintéticos. Oito verificações de schemas
passaram. No Chromium: uploads reais A/B com Cadastro e referência, downloads,
remoção do complemento, novo processamento sem ele, autenticação, bloqueio
operacional e viewport móvel sem overflow/erros JavaScript. TREE, PLAZA e NOVA YORK tiveram seus
canônicos e XLSX comparados com as saídas privadas anteriores, sem diferenças.
Os casos sintéticos cobrem limite 31/32 dias, zeros com/sem encargos, centavo,
A/AJ/J/AE, componentes negativos, alfanuméricos, colisões, papéis e documentos,
continuações/geometria, descrição, modos A/B e acesso autenticado.

```bash
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```
