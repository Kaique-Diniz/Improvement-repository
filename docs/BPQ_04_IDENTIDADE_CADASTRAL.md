# BPQ-04 — Identidade individual comprovada no Beach Parque

Implementação inicialmente entregue para revisão local. Branch `fix/bpq04-identidade-cadastral-beach-int02`,
base BPQ-03 `5260989a8a1ad2fa66355661bdaeddfc6fa481fc`.
A BPQ-04-B autoriza um único commit e push nesta branch, sem PR ou merge.
Referência: 09/11/2026. A publicação não constitui homologação operacional.

## Diagnóstico anonimizado

### Caso do sobrenome

O nome financeiro concorda integralmente, após normalização A1, com o nome do
titular. A ficha identifica uma pessoa física, um único titular e um CPF válido
no campo do titular em Dados pessoais. O documento canônico mantém essa origem
e titularidade; não há documento concorrente do titular. O registro do pagador
permanece separado. A retenção era exclusivamente
`PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO`, produzida pela função genérica
que considera o conectivo E um marcador de multiplicidade. B1 respeitava essa
retenção A1 e não promovia os dados.

Existe um telefone e um e-mail já aprovados pelo leitor BPQ-02. Um segundo
telefone aparece na mesma linha e papel, com anotação de inclusão datada,
repartida entre células geométricas. O leitor BPQ-02 retinha esse campo como
anotação desconhecida. Não se ampliou sua gramática geral: há outras fichas com
esse marcador, e uma alteração geral afetaria participantes fora desta tarefa.

A prova privada conserva página, linha, seção, papel, geometria, valores brutos
e vínculo de origem. Nenhum nome, documento, contato ou código de unidade real
integra este relatório ou as fixtures.

### Caso do documento

O campo CPF em Dados pessoais do titular está vazio. O CPF fiscalmente válido
aparece exclusivamente na linha de Dados do pagador, em Dados gerais, em outra
coluna. O parser mantém corretamente esse papel. Não existe evidência documental
do titular canônico que autorize a transferência. Telefone e e-mail do titular
também estão ausentes.

Fluxo conferido: PDF → CampoCadastroBBZ (pagador) → ParticipanteBBZ (pagador).
Ele não se torna EvidenciaDocumento da Pessoa titular. resolver_documento()
retorna ausência para o titular, A1 retém a associação com
`BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA` e B1 conserva
`BPQ_B1_DOCUMENTO_TITULAR_AUSENTE`. O documento não se perdeu; a separação entre
papéis funciona. Não se copiou documento do template. Não há exigência de
telefone/e-mail para exportar um CPF comprovado.

## Correção específica e critérios de rejeição

A função compartilhada de multiplicidade e sua utilização pelos demais
condomínios permanecem byte a byte inalteradas. A associação Beach primeiro
executa a A1 anterior. Só reconsidera uma retenção exclusivamente por
multiplicidade, no condomínio/administradora Beach, com concordância nominal.

A forma textual é somente um filtro conservador: um único E em posição
penúltima, pelo menos dois componentes anteriores e um posterior, todos
alfabéticos. Não são usados dicionários de sobrenomes, nomes reais ou exceções
por unidade/CPF. A forma textual nunca basta para aprovar a associação.

É necessário comprovar conjuntamente:

- Exatamente uma ficha original para a unidade e um participante titular.
- Cabeçalhos, origem da pessoa e identidade da ficha coerentes.
- Nome completo do participante igual ao nome canônico e ao financeiro.
- Campo explícito Tipo de pessoa: Física na seção Dados pessoais do titular.
- Exatamente um CPF válido nessa seção, com origem igual à do documento do
  participante e de todas as evidências canônicas vinculadas à própria pessoa.
- Resolução documental válida, sem conflito ou documento de outro participante.

Listas com `/` ou `;`, nomes curtos unidos por E, dois nomes completos unidos por
E, vários conectivos, ausência de ficha/prova, papel divergente, CPF ausente,
inválido ou conflitante continuam retidos. Não se pretende certificar um nome
civil apenas pela sua grafia. Situações que não satisfazem a prova individual
fechada permanecem para revisão documental.

Para esse titular comprovado, é admitida exclusivamente a anotação neutra
`incluído/incluída em DD/MM/AAAA`, com data válida e campo completo. Reconstrói-se
somente o sufixo de células contíguas da mesma página, linha, seção e papel.
Não são descartados textos residuais. O contato-base ainda precisa passar na
gramática BPQ-02. Anotação de terceiro, excluído, data inválida ou ambiguidade
não recupera o contato. A evidência bruta e o diagnóstico original permanecem
na auditoria temporária; não se cria cadastro permanente. Contatos já aprovados
mantêm ordem, deduplicação e limites de cinco telefones/três e-mails.

Uma ressalva informativa específica registra a nova comprovação e suas origens;
somente a antiga retenção de multiplicidade daquela associação é retirada.
Contagens A1 são reconciliadas. B1 continua exigindo equivalência integral de
TODOS os lançamentos relevantes excluídos, inclusive evidências e contatos,
e usa a mesma resolução de titular individual. Não aproveita dados de um
boleto elegível para autorizar outra pessoa.

## Versionamento e contratos

A política A1 Beach passa de `beach_parque_titular_nominal_documento_valido_A1@1`
para `beach_parque_titular_nominal_documento_valido_A1@1.1`.
B1 passa de `beach_parque_linha_cadastral_individual_comprovada_B1@1`
para `beach_parque_linha_cadastral_individual_comprovada_B1@1.1`.
Cada decisão B1 e o resumo B1 registram também `politica_a1`; resultado,
manifesto e auditoria mantêm os mesmos identificadores das versões utilizadas.

Duas expectativas literais antigas de versão foram atualizadas para a constante
A1 corrente, preservando as asserções de documento, contato, segurança e
comportamento. As novas regressões fixam explicitamente os identificadores @1.1.
Nenhum teste foi removido ou desabilitado.

Não houve alteração do leitor PDF, leitor financeiro, regra de prazo, domínio
financeiro, ordenação/parcelas, contrato/exportador universal, perfis, HMAC,
hashes, segurança Windows ou ciclo de vida efêmero. A alteração em service.py é
somente o vínculo explícito à política A1 no resumo B1. Não existe acionamento
de cobrança ou comunicação, integração CRM ou liberação operacional.

## Verificação e limitações

Os testes sintéticos cobrem individualização física com E, nomes e evidências
concordantes, CPF com zeros/formatação, papel e origem incorretos, ficha inválida,
listas e ambiguidade, documentos conflitantes, razão social com CNPJ e campos
independentes (CPF sem contatos, com telefone, com e-mail ou com ambos).
Há cenários pagador/locatário, proximidade geométrica e continuidade de página,
sem transferência entre papéis. Inclusão datada tem positivos e negativos,
inclusive terceiros e alteração indevida de interpretação global.

O cadastro histórico não comprova titularidade atual. A aprovação continua
somente documental/diagnóstica. Windows e homologação operacional não são
certificados pela execução Linux/Chromium. As limitações preexistentes de
memória global, cancelamento, limpeza após encerramento forçado e apagamento
forense permanecem abertas. Evidências privadas não são destinadas ao Git.

## Reconciliação final antes/depois

Mesmos bytes privados de fonte e data de referência da BPQ-03. Cada versão foi
executada em processo independente, usando o respectivo worktree. A geometria
nativa do PDF foi extraída uma vez por versão e reutilizada somente no harness
privado para bytes idênticos; não há cache novo no produto. Arquivos de saída
foram confinados a diretórios temporários e descartados após a comparação.

| Indicador | BPQ-03 | BPQ-04 |
| --- | ---: | ---: |
| Dívidas elegíveis A/financeiras B | 850 | 850 |
| Original elegível | R$ 603.477,71 | R$ 603.477,71 |
| Cadastrais adicionais B | 159 | 159 |
| Total modo B | 1.009 | 1.009 |
| Colunas universais | 30 | 30 |
| Documentos financeiros preenchidos | 747 | 763 |
| Linhas financeiras com telefone | 719 | 735 |
| Linhas financeiras com e-mail | 734 | 750 |
| Retenções A1 elegíveis | 103 | 87 |
| Retenções A1 totais, incluindo não elegíveis | 115 | 98 |
| Associações B1 aprovadas | 147 | 148 |
| Associações B1 retidas | 12 | 11 |
| Documentos nas cadastrais B | 147 | 148 |
| Cadastrais B com telefone | 143 | 144 |
| Cadastrais B com e-mail | 144 | 145 |
| Cadastrais B com documento, telefone e e-mail | 142 | 143 |

O caso do sobrenome recuperou 16 linhas financeiras em cada modo e uma linha
cadastral B: CPF, dois telefones e um e-mail. A A1 também recuperou o lançamento
não elegível que justifica essa linha (17 associações por lançamento ao todo).
Não são 17 novas dívidas. A numeração das parcelas e todos os campos financeiros
permanecem iguais. Apenas documento e contatos puderam mudar.

O caso do documento conserva vazios CPF, telefone e e-mail nas 31 dívidas e na
linha cadastral adicional. Por isso a projeção condicional de 794 documentos
não se aplica: o CPF exclusivo do pagador não se tornou documento do titular.

A matriz B1 exclusiva agora é: 148 comprovadas, dez divergências nominais e uma
ausência de documento do titular; total 159. As onze retenções continuam efetivas.

Os boletos canônicos são idênticos nas quatro execuções A/B antes/depois. Foram
comparadas todas as posições das 30 colunas: nomes, códigos, endereço, descrição,
parcela, vencimento e valor não mudaram. Todas as demais linhas permaneceram
inteiramente iguais, inclusive documento e contatos. Modo A não é anunciado
como XLSX binariamente igual: seus campos pessoais comprovadamente corrigidos
mudaram, preservando integralmente seus dados financeiros.

### Dez divergências nominais preservadas

As referências abaixo são rótulos anônimos do relatório, sem unidade real,
nome, documento, contato ou chave canônica. Em todos os casos a linha cadastral,
o nome e o código financeiro foram preservados; CPF e contatos continuam vazios
nas linhas financeiras e cadastrais. O motivo permanece
`PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` / `BPQ_B1_NOME_DIVERGENTE`.

| Referência anônima | Elegíveis | Não elegíveis | Cadastral B preservada |
| --- | ---: | ---: | --- |
| R01 | 0 | 1 | Sim |
| R02 | 0 | 1 | Sim |
| R03 | 8 | 1 | Sim |
| R04 | 0 | 1 | Sim |
| R05 | 2 | 1 | Sim |
| R06 | 3 | 1 | Sim |
| R07 | 1 | 1 | Sim |
| R08 | 0 | 1 | Sim |
| R09 | 0 | 1 | Sim |
| R10 | 2 | 1 | Sim |

As dez candidatas B1 acima abrangem 16 lançamentos elegíveis e dez não
elegíveis. Não representam todas as retenções A1 por lançamento: também existem
unidades com divergência nominal sem candidata cadastral B1. Todas as demais
linhas financeiras foram comparadas e permaneceram idênticas. Não somar linhas
cadastrais e retenções por lançamento como se fossem pessoas distintas; são
universos diferentes. Nenhum dado pessoal dessas unidades foi
transferido para alcançar uma contagem projetada.

## Testes da entrega local BPQ-04 e isolamento Git

| Execução | Aprovados | Falhas/erros/skips |
| --- | ---: | --- |
| Novas regressões BPQ-04 | 49 | 0/0/0 |
| Beach Parque completo | 211 | 0/0/0 |
| INT-02 | 108 | 0/0/0 |
| UX-01/INT-01 | 100 | 0/0/0 |
| Linux completo | 2.647 | 0/0/0 |

2.598 anteriores + 49 novos = 2.647. As execuções direcionadas se sobrepõem e
não são somadas. Python 3.12.14; um warning preexistente de depreciação
Starlette/AnyIO. Sem novos skips, xfails ou remoção de testes. Uma primeira
execução coletou 44 novos (2.642 no total); os cinco casos adicionais de
segurança foram incluídos na reexecução completa final acima.

Passaredo, Forest Hill, Parque Santa Mônica, Vero Encanto e Itajubá foram
confrontados separadamente com a BPQ-03 usando os mesmos bytes, data e
parâmetros: dez XLSX A/B binariamente idênticos, assim como dados financeiros,
IDs, decisões, resumos e políticas.

Chromium real, somente documentos fictícios: upload, reconhecimento, conversão
A/B, prévia com 30 colunas e download; CPF/contatos do titular individual
comprovado nos campos esperados. Outra sessão recebeu 404; exportação operacional
recebeu 409; novo download após descarte recebeu 404. Nenhum erro JavaScript,
nenhum arquivo de processamento após o download e área vazia após shutdown.
Nenhuma alteração em autenticação, sessão, limites, TTL ou descarte.

`pip check`, `compileall`, `git diff --check` e whitespace dos dois arquivos
novos aprovados. O staging permanece vazio. HEAD continua na base BPQ-03; não
há commits novos. Os heads e estados preexistentes dos 15 worktrees anteriores
foram preservados. Nenhum push, PR ou merge. Windows não executado.

Arquivos desta entrega local:

- `src/conversor/application/beach_parque_cadastro.py`
- `src/conversor/web/service.py`
- `tests/beach_parque/test_contatos_anotados.py`
- `tests/beach_parque/test_modo_b_cadastral.py`
- `tests/beach_parque/test_identidade_individual.py`
- `docs/BPQ_04_IDENTIDADE_CADASTRAL.md`

Aguardar auditoria externa desta alteração local. As dez divergências nominais
e a ausência de documento comprovado do titular continuam pendências
documentais; não são autorização para flexibilizar a política.

## Estado Git na entrega local anterior à BPQ-04-B

```text
$ git diff --stat
 src/conversor/application/beach_parque_cadastro.py | 127 ++++++++++++++++++++-
 src/conversor/web/service.py                       |   2 +-
 tests/beach_parque/test_contatos_anotados.py       |   3 +-
 tests/beach_parque/test_modo_b_cadastral.py        |   3 +-
 4 files changed, 128 insertions(+), 7 deletions(-)
$ git diff --check
[sem saída; exit 0]
$ git diff --cached --name-only
[sem saída; staging vazio]
```

O stat convencional cobre os quatro arquivos rastreados. O diff completo também
inclui este relatório e os testes novos, conferidos com index temporário externo,
sem modificar o staging real. Nenhuma fonte privada integra esses arquivos.

## Conferência adicional BPQ-04-B

A inspeção exigida antes da publicação reproduziu uma lacuna sintética: o parser
conservava dois campos Nome nos Dados pessoais, mas o resolvedor considerava
somente o participante derivado do cabeçalho, o tipo físico e o CPF. Esse cenário
explícito de duas pessoas podia satisfazer a exceção. Nenhum dado real foi usado
para reproduzir o problema.

A condição foi corrigida nos mesmos seis arquivos autorizados. Para a exceção
individual Beach, campos nominais explícitos devem ser únicos e concordantes;
rótulos plurais sempre retêm. Campos pessoais não reconhecidos também impedem
a exceção, em vez de serem ignorados como se comprovassem individualidade.
Os campos admitidos são os rótulos estruturais de Dados pessoais já homologados,
mais os rótulos singulares de nome/titular/responsável expressamente conferidos.
Isso complementa, sem substituir, a prova de papel, origem, CPF, ficha única,
concordância e formato nominal fechado. A política padrão Passaredo não muda.

Foram acrescentadas sete regressões àquelas 49: dois nomes explícitos, nome
divergente, dois rótulos plurais, dois rótulos pessoais não suportados e um
campo Nome singular concordante. Todos usam o mesmo cabeçalho financeiro e
cadastral, CPF válido e tipo físico; quatro provas superficiais não substituem
a conferência integral da ficha. Os negativos permanecem retidos tanto na A1
como na B1, sem excluir dívida ou linha cadastral.

Contagem final efetivamente executada após a ampliação: 56 testes novos no
total, 218 Beach Parque e 2.654 na suíte Linux, sete acima dos 2.647 relatados
na BPQ-04 local. Zero falhas, erros ou skips; um warning preexistente
Starlette/AnyIO. INT-02: 108 aprovados; UX-01/INT-01: 100 aprovados. Essas
execuções se sobrepõem e não são somadas.
A alteração mantém A1/B1 @1.1: essas versões ainda não tinham sido publicadas.

O volume da entrega é composto por duas alterações de produção localizadas
(aplicação Beach e vínculo da versão A1 no resumo B1), testes sintéticos e este
relatório. Não há reestruturação de leitores ou consumidores, dados privados,
patches, ZIPs, fontes de homologação ou capturas incluídos no Git.

A reconciliação BPQ-03/BPQ-04 foi repetida após o reforço final: 850 dívidas,
R$ 603.477,71, 1.009 linhas B, 30 colunas, 763 documentos financeiros, 87
retenções A1 elegíveis, 148 associações B1 comprovadas e onze retidas. Somente
o caso do sobrenome recebeu dados novos; o caso do pagador e as dez candidatas
B1 nominalmente divergentes permanecem retidos. Todas as demais linhas pessoais
e todos os dados financeiros permaneceram iguais. As linhas financeiras de A
e B têm o mesmo conteúdo; nenhum hash de fonte foi normalizado ou substituído.

Chromium A/B, isolamento, download e descarte foram repetidos depois da
correção. Os dez XLSX sintéticos dos outros cinco perfis continuaram
binariamente idênticos à BPQ-03. `pip check`, `compileall` e whitespace foram
aprovados antes da preparação explícita dos seis arquivos. Fontes, relatórios
privados, patches e pacotes de auditoria permanecem fora do staging. A
publicação isolada está autorizada somente para revisão estática externa.
