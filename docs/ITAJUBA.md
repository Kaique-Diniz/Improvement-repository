# ITJ-01 — Condomínio Itajubá / BN PLANNER

Implementação isolada para auditoria na branch `feat/itajuba-bn-planner-efemero`,
baseada em `2b7d6347d23e0ea79e16216c10042b5a20674344`. A publicação controlada não
representa homologação operacional ou autorização de integração definitiva.
A base não incorpora Vero Encanto; sua branch independente permanece preservada.
Não há dependência de módulos Vero ou da infraestrutura experimental Windows.

## Identidade e leitura

Leitores próprios para PDF `Lista de Ctas a Receber` e cadastro XLSX `Sheet1`.
O nome CONDOMINIO ITAJUBA, a emissão e a paginação são conferidos em todas as
páginas. As colunas financeiras aparecem apenas na primeira página; continuações
usam a mesma geometria e validações. Ordem, página e posição são preservadas.
Páginas faltantes, reordenadas, cabeçalhos alterados e formatos ambíguos falham.

O reconhecimento automático exige identidade/gramática e hash homologado do papel
correto. PDF novo compatível exige confirmação. Seleção e hash não dispensam as
verificações estruturais. O cadastro não identifica internamente o condomínio:
apenas seu hash homologado, fornecido por configuração confiável, permite vinculá-lo.
Nome de arquivo, seleção manual ou coincidência de unidades não substituem essa
prova. Cadastros atualizados sem identidade exigem homologação separada; é possível
converter sem cadastro. Hashes são sempre calculados sobre os bytes reais.

Cada linha gera uma ocorrência distinta. Doc. original pode se repetir; é mantido
na evidência e na prévia. A identidade técnica combina dados documentais e número
da ocorrência. O identificador ordenável mantém a ordem documental nos empates,
sem modificar o desempate universal do exportador por identificador estável.
Não se deduplicam linhas financeiramente iguais.

Para cada unidade, a chave universal continua sendo vencimento, identificador
estável e ID. Apenas na adaptação Itajubá, o identificador técnico contém a ordem
documental da ocorrência e seu hash; assim, empates de vencimento respeitam a
ordem da fonte. Linhas excluídas ou retidas não consomem parcela. Uma regressão
específica repete a conversão dos mesmos bytes com vencimentos empatados,
documento repetido e linha excluída, exigindo os mesmos dados e bytes XLSX.
A ordenação dos demais condomínios permanece integralmente preservada.

Tx Cond e Outros são componentes separados e sua soma deve conferir com o Total
original. Encargos externos não são calculados. Inquilino e marcador de acordo
permanecem em campos próprios de auditoria temporária, sem atribuição de titularidade,
exclusão automática ou autorização para renegociar.

São conferidos todos os subtotais efetivamente impressos e o total geral. Na fonte,
112 subtotais conferem; sete unidades não têm subtotal próprio. Essas ausências
ficam como avisos explícitos `ITAJUBA_SUBTOTAL_NAO_IMPRESSO`, sem fabricar uma
conferência local. Todas as linhas, inclusive dessas unidades, integram o total
geral obrigatório e reconciliado. Subtotal presente divergente continua bloqueando.

## Prazo, escopo e descrições

A linha 438 da régua de 04/11/2026 é evidência dos requisitos. Informações de acesso
e contatos operacionais não são transportados para esta configuração.

A hipótese diagnóstica é `(data_ref - vencimento).days > 30`. Inclusividade e
vigência operacional não estão homologadas. Na referência de emissão 20/10/2026,
todos os 3.784 lançamentos passam pelo prazo e têm vencimento desde dezembro/2023.
Vencimentos anteriores a 01/12/2023 geram revisão crítica por lançamento; são
preservados no canônico e não seguem silenciosamente ao mesmo fluxo. O teste pelo
vencimento é uma guarda diagnóstica: não comprova competência contábil, cobertura
contratual ou responsabilidade da garantidora. Judicial permanece sem operação.

Prefixos documentais determinam os rótulos: Tt = COTA CONDOMINIAL, Mlt = MULTA,
Ext = COTA EXTRA, AcT = ACORDO. Usa-se `TIPO (MM/AAAA) - N`; mês/ano é apresentação
do vencimento, sem preencher competência contábil. Parcelas são numeradas somente
entre dívidas incluídas, em vencimento crescente e desempate pelo identificador
estável. Descrições e parcelas são comparadas separadamente dos valores.

## Reconciliação privada, somente agregados

- 3.784 lançamentos, 119 unidades em cinco torres; R$ 1.044.815,15 de original.
- 3.682 Tt, 44 Mlt, 30 Ext e 28 AcT; cinco grupos com multiplicidade financeira.
- Zero diferenças no multiconjunto de complemento, vencimento e original.
- Modo A: 3.784 linhas financeiras. Modo B: 3.784 financeiras e zero cadastrais.
- 115 cadastros: 113 unidades presentes no financeiro e dois registros adicionais;
  seis unidades financeiras sem cadastro permanecem com suas seis dívidas.
- Seis unidades têm nomes financeiros históricos distintos.
- O fluxo HTTP real local também concluiu as 3.784 linhas, com download e descarte.

Nenhuma dessas contagens está fixada no leitor.

## Cadastro conservador A1

A1 é reutilizada sem alteração, por lançamento, usando o nome financeiro daquela
linha e a unidade/torre textuais. Não se copia o documento do proprietário atual
para um responsável antigo. Nome financeiro é preservado mesmo quando a associação
é retida. CPF/CNPJ inválido ou malformado não é atribuído; o original permanece na
auditoria temporária. Documentos válidos conflitantes e multiplicidade seguem A1.

Telefones são capturados por tokens completos, sem correspondência parcial em
sequências maiores. DDD pode ficar vazio e não é herdado. E-mails precisam cumprir
a validação estrita do campo; números, códigos e espaços não viram endereços.
Na origem, 77 células de e-mail contêm somente espaços e 38 contêm e-mails válidos.
Espaços são ausência, sem apagar a evidência bruta. Inad Prop é preservado como
campo cadastral e nunca gera boletos ou modifica o original financeiro.

| Resultado cadastral por lançamento | Lançamentos | Unidades distintas |
| --- | ---: | ---: |
| Associação A1 com documento válido | 2.914 | 89 |
| Nome divergente, associação pessoal retida | 864 | 29 |
| Cadastro ausente, associação não realizada | 6 | 6 |

Unidades por motivo podem se sobrepor: a mesma unidade pode conter responsáveis
históricos concordantes e divergentes. A soma dos lançamentos é 3.784; o universo
continua sendo 119 unidades. As 864 divergências são reproduzidas tanto pela
comparação sem caixa quanto pela normalização A1 de caixa, acentos e espaços.
Nenhuma dívida foi excluída por esses problemas cadastrais.

## Comparação das 30 colunas

O pareamento é por multiconjunto financeiro, com ordem de ocorrência dentro das
cinco chaves repetidas. Não é uma prova de identidade pessoal e não alimenta a
associação. None e célula vazia são equivalentes; data e dinheiro são comparados
em sua representação contratual. A tabela abaixo registra comparação de conteúdo,
sem corrigir a saída para imitar o histórico.

| Coluna | Iguais | Diferentes |
| --- | ---: | ---: |
| NM_CEDENTE_CEDENTE | 3784 | 0 |
| CEDENTE | 3784 | 0 |
| CPF | 6 | 3778 |
| NOME | 2920 | 864 |
| ENDERECO | 0 | 3784 |
| NUMERO | 0 | 3784 |
| COMPLEMENTO | 3784 | 0 |
| CEP | 0 | 3784 |
| BAIRRO | 0 | 3784 |
| CIDADE | 0 | 3784 |
| UF | 0 | 3784 |
| DDD1 | 2908 | 876 |
| FONE1 | 1875 | 1909 |
| DDD2 | 3288 | 496 |
| FONE2 | 2255 | 1529 |
| DDD3 | 3784 | 0 |
| FONE3 | 3784 | 0 |
| DDD4 | 3784 | 0 |
| FONE4 | 3784 | 0 |
| DDD5 | 3784 | 0 |
| FONE5 | 3784 | 0 |
| EMAIL1 | 3552 | 232 |
| EMAIL2 | 3784 | 0 |
| EMAIL3 | 3784 | 0 |
| NM_CONTRATO_CEDENTE | 3784 | 0 |
| PRODUTO_CEDENTE | 3784 | 0 |
| NM_DIVIDA_CEDENTE | 3718 | 66 |
| NU_PARCELA | 3719 | 65 |
| VENCIMENTO | 3784 | 0 |
| VL_PARCELA | 3784 | 0 |

CPF tem 3.778 diferenças literais de formato/conteúdo. Na comparação fiscal
adicional, retirando apenas formatação e recompondo zeros apenas de células
numéricas do template, há 2.920 valores iguais (incluindo seis vazios) e 864
diferentes. Não se altera o arquivo nem se atribuem documentos a partir desse
procedimento comparativo.

As quatro diferenças de classificação são três MULTA e um ACORDO que o template
rotula como COTA CONDOMINIAL. A saída mantém a evidência documental da origem.
O template contém 54 grupos de unidade/vencimento empatados. Há 65 diferenças
de parcela, todas em empates de vencimento na mesma unidade;
a numeração determinística da ocorrência não foi substituída pela sequência
histórica. Há 66 rótulos completos diferentes ao considerar classe e parcela,
com zero diferenças de mês/ano. Não houve alteração de valor para ajustar rótulos.

Os campos de endereço não são preenchidos a partir do template. O cadastro não os
fornece; o usuário pode configurar o endereço do condomínio em memória, por sessão.
Diferenças de contatos refletem formato e/ou associação A1 retida; não autorizam
copiar dados pessoais históricos.

## Interface, retenção e segurança

Fluxo clássico local sem senha manual, sessão técnica, CSRF, Host/Origin, identificação,
confirmação, cadastro opcional, endereço em memória, auditoria, modos A/B e Excel.
São preservadas as 30 colunas universais e AA `NM_DIVIDA_CEDENTE` sem espaço final.
BN PLANNER é o cedente nominal; complemento `QUAT01-LTA0001` e contrato/cedente
`QUAT01-LTA0001-CONDOMINIO ITAJUBA` vêm da codificação documental, sem código de
destino inferido do nome de arquivo. As cinco torres têm mapeamento comprovado.

Uploads são processados sob os limites existentes. Canônico, auditoria e XLSX
intermediário ficam em diretório temporário isolado, limpo no finally, inclusive
em erro. Falha de limpeza impede retorno do resultado e fica pendente para nova
tentativa. Download/prévia ficam em memória por até 15 minutos, respeitando respostas
ativas; janitor também atua em inatividade. Não há histórico pessoal persistente.
Somente perfis, referências documentais à régua e layouts permanecem como configuração; a planilha confidencial da régua não é incorporada.

Limitações existentes: cache de resultados de 32 MiB, duas conversões simultâneas,
20 MiB por upload e até oito resultados; esses limites não certificam um teto de
RSS dos parsers. A auditoria deste relatório ocupa aproximadamente 25,6 MiB; um
resultado grande pode exigir terminar o download ou descartar antes de outro.
Cancelamento pode aguardar o processamento para liberar recursos. Encerramento
forçado pode deixar áreas órfãs, sem varredura automática implementada na inicialização.
Não se promete apagamento físico de mídia nem exclusão enquanto houver resposta ativa.

## Testes, execução e pendências

58 testes sintéticos Itajubá, incluindo continuação/paginação, nomes históricos,
locatário, classes, documentos e linhas repetidos, somas, subtotais, cabeçalhos,
cadastro, CPF inválido, captura integral de telefone, e-mail inválido, limites de
29/30/31 dias, novembro/dezembro de 2023, modos A/B e sessão/download/descarte.
Conjunto direcionado com os perfis anteriores: 412 aprovados. Suíte Linux: 2.270
aprovados, sem falhas, erros ou skips, com um aviso Starlette/AnyIO de depreciação.
Pip check, compileall, sintaxe JavaScript e whitespace aprovados.

Chromium real usa exclusivamente documentos fictícios e binding de hash da fixture
no processo de teste: identificação, confirmação, cadastro, endereço, prévia,
auditoria com Doc. original, modos A/B, download isolado, CSRF, Host/Origin,
expiração em inatividade com relógio controlado e encerramento normal limpo.
Os hashes reais do perfil de produção não são trocados por hashes sintéticos.

```bash
cd /workspace/Improvement-itajuba
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web
```

Abrir http://127.0.0.1:8000, usando o modo efêmero padrão. Não utilizar a opção de
legado persistente para este fluxo. A homologação operacional continua pendente:
confirmar inclusividade, vigência e escopo de competência/garantidora. Windows
requer ambiente real e não foi certificado no Linux. A integração com Vero Encanto
é uma etapa futura separada. Não há CRM, cobrança real ou exportação operacional.
