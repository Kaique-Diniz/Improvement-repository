# BPQ-02 — Contatos anotados do Terraço Beach Parque

Implementação para auditoria técnica externa. Branch
`fix/bpq02-contatos-cadastrais-int02`, worktree
`/workspace/Improvement-bpq02-contatos`, HEAD/base exata
`35f57d98fd0fca18b045b03fa4850835a92488cd` (INT-02).
A entrega local foi preparada sem commit e com staging vazio. A BPQ-02-B
autoriza somente um commit e push nesta branch para revisão, sem PR ou merge.
Windows não executado.
Não há homologação operacional nem autorização de cobrança ou contato.

## Estado inicial e isolamento

INT-02 estava limpa no HEAD esperado, sem arquivos não rastreados. Antes da
criação da branch foram registrados os heads e estados dos 13 worktrees
preexistentes. A branch nova nasceu exatamente da referência e não recebeu
commit durante a implementação local. Alterações locais dos demais worktrees foram preservadas,
inclusive os experimentos Windows; nenhuma branch original ou PR foi alterado.
Não se executou limpeza, reset, staging global ou mudança de configuração.

## Causa e correção mínima

O leitor reconhecia o rótulo e a seção corretamente, mas passava o valor inteiro
anotado a `_telefone()` ou `email_valido()`. Esses validadores corretamente
rejeitam texto residual. O erro era de segmentação específica desta fonte,
não de validação fiscal, identidade, A1 ou regra financeira.

Foi alterado somente `src/conversor/readers/beach_parque_cadastro.py` em produção:

- `segmentar_contato()` exige rótulo completo conhecido e valor integralmente
  validável; não busca o primeiro número/e-mail em texto livre.
- `ContatoSegmentado` separa rótulo, valor original, anotação e contatos validados;
  valores pessoais são excluídos do repr. Seção, papel e geometria permanecem
  em `CampoCadastroBBZ`; participantes mantêm a origem individual do contato.
- `LeitorCadastroBeachParque.ler()` usa o resultado só na seção telefone/e-mail
  reconhecida e conserva titular, pagador, locatário e unidade separados.
- Diagnósticos por ocorrência têm origem exata, código fixo e nenhum contato no
  texto. Duplicatas do mesmo código/origem são removidas; campos distintos têm
  diagnósticos distintos. Alertas não equivalem a retenções A1 por lançamento.

Não se alteraram `application/beach_parque_cadastro.py`, BBZ compartilhado,
modelos canônicos, validadores fiscais, leitor financeiro, exportador, perfis,
service, frontend, endereços, segurança de sessão ou infraestrutura Windows.
Os arquivos protegidos foram comparados byte a byte com HEAD.

### Gramática admitida

Rótulos existentes: E-mail, Celular, Telefone residencial, Telefone comercial,
Telefone e Fax. Valores sem anotação continuam usando os validadores existentes.
Somente estes sufixos neutros são reconhecidos, com data calendário válida:

```text
Celular - (11) 91234-5678 - atualizado em 10/01/2025.
Celular - (11) 91234-5678 - atualizada em 10/01/2025.
E-mail - pessoa@example.invalid - alterado em 10/01/2025
E-mail - pessoa@example.invalid (atualizado em 10/01/2025)
```

O verbo é `atualizado/atualizada/alterado/alterada`, seguido exatamente de
`em DD/MM/AAAA`; admite ponto terminal e os delimitadores explicitados nos
exemplos. Não se aceitam siglas, data solta, verbo sem `em`, data impossível,
texto adicional ou anotação desconhecida. Não se remove texto arbitrário.
Esses metadados não comprovam identidade pessoal nem vigência em 2026.

Listas só são aceitas se todos os valores e delimitadores forem válidos.
Um fragmento válido não resgata uma lista com anotação ambígua ou de terceiro.
Telefones não herdam DDD; pares distintos não são fundidos. A deduplicação e os
limites existentes de cinco telefones e três e-mails são preservados, com
excedentes na evidência temporária. Nenhum contato preexistente foi perdido
nas 622 fichas reais verificadas.

### Códigos

| Código | Gravidade | Efeito |
| --- | --- | --- |
| `BPQ_CONTATO_ANOTADO_SEGMENTADO` | Informativo | Valor completo e sufixo neutro reconhecidos; não supera A1 ou comprova atualidade. |
| `BPQ_CONTATO_ATRIBUICAO_AMBIGUA` | Alerta | Titularidade explicitamente incerta; não transfere contato. |
| `BPQ_CONTATO_TERCEIRO_IDENTIFICADO` | Alerta | Referência explícita a terceiro; não transfere contato. |
| `BPQ_CONTATO_ANOTACAO_DESCONHECIDA` | Alerta | Gramática ou data não comprovada; mantém retenção do campo. |

Permanecem os códigos de erro de formato `TELEFONE_NAO_SEGMENTADO`,
`EMAIL_NAO_SEGMENTADO` e `BBZ_CONTATO_NAO_SEGMENTADO`. A nova validação de listas
não aproveita parcialmente um e-mail válido quando o restante torna a
atribuição incerta. Isso não removeu contatos anteriores na amostra privada.

## Oito casos prioritários — diagnóstico anonimizado

P01–P08 seguem a ordem da solicitação privada. Códigos reais de unidade, contatos,
nomes, documentos, endereços e anotações identificáveis não integram este relatório.
Todos os campos abaixo estão em `telefone/e-mail do cliente`, papel `titular`;
a associação A1 dos lançamentos correspondentes já estava aprovada.

| Caso | Tipo | Categoria | Antes (contatos) | Depois (contatos) | Dívidas | Linhas corrigidas | Justificativa |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| P01 | telefone | A | 0 | 1 | 3 | 3 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P02 | telefone | A | 0 | 1 | 5 | 5 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P03 | telefone | A | 0 | 1 | 16 | 16 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P04 | telefone | B | 0 | 0 | 1 | 0 | Duas anotações textuais desconhecidas; atribuição não comprovada, sem escolher alternativa |
| P05 | telefone | A | 0 | 1 | 1 | 1 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P06 | email | A | 0 | 1 | 4 | 4 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P07 | email | A | 0 | 1 | 3 | 3 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |
| P08 | email | A | 0 | 1 | 7 | 7 | Campo completo válido e atualização/alteração neutra reconhecida; A1 e documento válido já aprovados |

Antes/depois mede contatos distintos exportáveis no caso; linhas corrigidas
mede dívidas, não o número de campos DDD/FONE ou de contatos.

Resultado: sete casos A (quatro de telefone, três de e-mail), um caso B e nenhum
caso C/D/E entre os oito prioritários. Recuperação nos prioritários: telefone
em 25 dívidas, e-mail em 14. O caso B tem uma dívida e dois campos telefônicos
com texto não reconhecido; não há prova para atribuí-los, mesmo com A1 aprovada.
Nenhuma alternativa é escolhida pelo primeiro valor ou pela unidade isolada.

### Complemento BPQ-02-B: 26 prioritárias, 28 telefones e 42 registros distintos

As cinco unidades prioritárias de telefone somam **26 dívidas**. O caso P04
mantém uma dívida sem telefone por ambiguidade: **26 - 1 = 25** linhas recuperadas
nos casos prioritários. A revisão ampliada encontrou ainda um caso anonimizado
X01, fora dos oito prioritários, com **três dívidas** que já tinham um telefone
exportado e recuperaram um segundo. Portanto, **25 + 3 = 28** linhas com telefone
corrigido. Não são 28 recuperações dentro das 26 prioritárias.

X01 foi submetido às mesmas condições: seção `telefone/e-mail do cliente`,
papel titular, unidade canônica exata, contato completo válido, sufixo neutro
reconhecido, documento válido e associação A1 aprovada nos três lançamentos.
O telefone anterior foi preservado. Não se aplicou uma tolerância especial ao
caso adicional nem se alterou CPF/CNPJ ou política A1.

As **42 linhas são registros financeiros distintos**, em ambos os modos. São
28 registros com telefone e 14 com e-mail; **a interseção é zero**. A comparação
usa a identidade de contrato/cedente e parcela, além da comparação posição a
posição das saídas. Alterar DDD e FONE da mesma linha não conta como duas linhas.
As 42 correções do modo B são as mesmas do A; nenhuma das 159 linhas cadastrais
extras foi alterada e não se somam os modos como 84 dívidas corrigidas.


## Revisão ampliada: 19 unidades com telefone e nove com e-mail

Universo: unidades com pelo menos uma dívida elegível e associação A1 aprovada.
Conta-se como campo descartado aquele explicitamente rotulado, na seção do
titular, cujo valor completo o validador anterior rejeitava. Conta-se a unidade
canônica uma vez por tipo, mesmo quando há mais de um campo. Não se contam
pagador, locatário, unidade, observações, cabeçalhos ou rodapés como contato do
cliente. A revisão reproduziu as duas contagens, sem usá-las como gabarito.

| Tipo | Unidades com algum campo descartado | Sem nenhum contato desse tipo antes | Com recuperação | Ainda com campo retido | Campos reconhecidos | Campos desconhecidos retidos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| telefone | 19 | 5 | 5 | 14 | 5 | 15 |
| email | 9 | 3 | 3 | 6 | 3 | 6 |

As 19 unidades não eram 19 unidades totalmente sem telefone: só cinco tinham
perda total. Quatro dessas cinco recuperaram o telefone; a quinta é o caso B.
Uma outra unidade já tinha telefone exportado e recuperou um segundo número,
em três dívidas. Assim, cinco campos/contatos foram recuperados em cinco
unidades, alterando telefone em 28 linhas; 25 passaram a ter seu primeiro
telefone. Permanecem 15 campos desconhecidos em 14 unidades, inclusive os dois
do caso B. Campos distintos não são somados como unidades distintas.

Das nove unidades de e-mail, três estavam totalmente sem e-mail e recuperaram
um campo cada, em 14 dívidas. Nas seis restantes, outros e-mails já exportados
foram preservados; o campo adicional desconhecido continua retido. Nenhum
formato foi ampliado apenas para preencher todos os vazios.

## Reconciliação privada antes/depois

Referência idêntica: **09/11/2026**. Cadastro emitido em **22/01/2025**;
a anotação não confirma que seus contatos ou vínculos ainda estejam vigentes.
Também se conferiu a seleção em 16/10/2026: neste lote, a mudança para
09/11/2026 não altera os 850 elegíveis, o original ou as 103 retenções elegíveis.

Método: fontes homologadas pelos hashes reais já configurados, mesmos bytes,
mesma data e modos A/B. A versão anterior do leitor foi carregada diretamente
do commit INT-02, sem alterar o worktree original. A extração geométrica real,
validada, foi reutilizada em memória apenas no harness privado para os mesmos
bytes exatos; os dois leitores e o serviço de conversão foram efetivamente
executados. Não há cache ou nova persistência na implementação do produto.

As linhas são comparadas posição a posição nas 30 colunas. Só os índices de
contato (DDD/FONE/E-mail) podem diferir. Financeiro do template é confrontado
por multiconjunto de complemento documental, vencimento e original, preservando
multiplicidade; datas textuais do Excel são interpretadas estritamente como
DD/MM/AAAA na comparação. Nenhum hash, valor, documento ou fonte é normalizado
para forçar coincidência. Os temporários privados de todas as execuções foram
descartados; somente agregados saem do processo.

| Indicador | Antes | Depois |
| --- | ---: | ---: |
| Dívidas elegíveis, A e B | 850 | 850 |
| Original elegível | R$ 603.477,71 | R$ 603.477,71 |
| Linhas modo A | 850 | 850 |
| Linhas modo B | 1.009 | 1.009 |
| Linhas cadastrais adicionais B | 159 | 159 |
| Colunas | 30 | 30 |
| Documentos preenchidos nas dívidas | 747 | 747 |
| Retenções A1 totais | 115 | 115 |
| Retenções A1 entre elegíveis | 103 | 103 |
| Dívidas com telefone | 694 | 719 |
| Dívidas com e-mail | 720 | 734 |
| Divergências financeiras contra template | 0 | 0 |

Em ambos os modos, 42 linhas financeiras tiveram contato corrigido: 28 de
telefone e 14 de e-mail, sem sobreposição nesta amostra. Mudanças exatas:
DDD1/FONE1 em 25 linhas, DDD2/FONE2 em três e EMAIL1 em 14. Os demais campos são
integralmente idênticos, inclusive CPF/CNPJ, nome, endereço, CEDENTE, contrato,
produto, descrição, parcela, vencimento e original. As linhas financeiras do
modo A e do B também são integralmente idênticas, antes e depois. Nenhuma das
159 linhas cadastrais extras teve contato ou outro campo alterado.

Os documentos, as unidades canônicas e os campos originais das 622 fichas
foram comparados e permanecem intactos, com página, linha, coordenadas e hash.
A origem individual fica em ParticipanteBBZ; o Contato canônico agregado mantém
o contrato anterior de origem da ficha, sem inventar origem única para vários
contatos. Não foram alterados os modelos para esta correção.

## Segurança e restrições

Transferência só pelo titular, na unidade e no condomínio corretos, com valor
validado, atribuição não ambígua, A1 aprovada e documento individual válido.
Pagador, locatário, unidade, correspondência e observações não fornecem contato
ao titular. Campos originais continuam na evidência privada e efêmera.
A política continua `beach_parque_titular_nominal_documento_valido_A1@1`.

Permanecem os alertas do cadastro completo: um litígio, nove bloqueios de reenvio
e duas restrições de carta. Não excluem dívida, iniciam contato ou autorizam
cobrança. Os testes comprovam os bloqueios pessoais e operacionais; o confronto
real confirmou a preservação de A1, CPF/CNPJ, nomes, campos financeiros e
contatos anteriores. Não se publicou dado pessoal ou documento real.

## Testes e verificações

| Execução | Aprovados | Falhas/erros/skips |
| --- | ---: | --- |
| Novos BPQ-02 | 60 | 0/0/0 |
| beach_parque | 123 | 0/0/0 |
| int02 | 108 | 0/0/0 |
| ux01_int01 | 100 | 0/0/0 |
| linux | 2559 | 0/0/0 |

Linux/Python 3.12.14, um warning preexistente Starlette/AnyIO na suíte completa.
Na preparação BPQ-02-B, as quatro suítes foram reexecutadas: 123 Beach Parque,
108 INT-02, 100 UX-01/INT-01 e 2.559 Linux; zero falhas/erros/skips. A suíte
completa terminou em 145,72 s, com o mesmo warning preexistente.
Total anterior: 2.499; total atual: 2.559 = 2.499 + 60 regressões novas. Nenhum
teste anterior foi removido, desabilitado ou convertido em skip/xfail.

Os novos testes cobrem anotações neutras, data inválida, telefone incompleto,
sequência longa, múltiplos contatos, DDD vazio, limites e excedentes, listas
ambíguas, referências a terceiros, todos os papéis, nome divergente,
multiplicidade, documento ausente/inválido/conflitante, cadastro de outro
condomínio, identidade de bloco/unidade, continuação PDF, preservação de
origem, restrições jurídicas, A/B e as 30 colunas. INT-02 e a suíte completa
preservam os outros cinco condomínios; UX-01/INT-01 validam o fluxo efêmero.

`pip check`, `compileall`, `git diff --check` e inspeção dos não rastreados
aprovados. Staging permanece vazio. Windows não executado; Linux não certifica
Windows. Não houve nova homologação operacional ou alteração de segurança.

## Pendências e entrega

Anotações desconhecidas continuam exigindo prova adicional: nenhum primeiro
contato é escolhido automaticamente, nem data isolada é prova de titularidade.
Formatos ainda não homologados permanecem retidos; não se relaxa A1 para
reduzir vazios. A validade atual do cadastro histórico não foi certificada.
As limitações anteriores do MVP sobre RSS global, cancelamento e resíduos após
encerramento forçado continuam documentadas e não foram objeto desta etapa.

Arquivos locais da BPQ-02:

- `src/conversor/readers/beach_parque_cadastro.py` (único módulo de produção).
- `tests/beach_parque/test_contatos_anotados.py` (60 regressões fictícias).
- `docs/BPQ_02_CONTATOS_CADASTRAIS.md` (este relatório anonimizado).

O diff integral e os JUnit são entregues fora do Git para revisão. A
implementação local foi entregue sem commit, push, PR ou merge. A autorização
posterior BPQ-02-B permite exclusivamente publicar estes três arquivos em um
único commit nesta branch. Main, INT-02, branches originais e PRs #6/#7 não
receberam alterações. Aguardar auditoria estática após a publicação, antes de
qualquer implementação adicional ou ampliação da gramática.

## Conferência Git antes da publicação

```text
$ git branch --show-current
fix/bpq02-contatos-cadastrais-int02
$ git rev-parse HEAD
35f57d98fd0fca18b045b03fa4850835a92488cd
$ git status --short
 M src/conversor/readers/beach_parque_cadastro.py
?? docs/BPQ_02_CONTATOS_CADASTRAIS.md
?? tests/beach_parque/test_contatos_anotados.py
$ git diff --stat
 src/conversor/readers/beach_parque_cadastro.py | 98 ++++++++++++++++++++++----
 1 file changed, 85 insertions(+), 13 deletions(-)
$ git diff --check
[sem saída; exit 0]
$ git diff --cached --name-only
[sem saída; staging vazio]
```

O stat Git acima cobre somente o arquivo já rastreado. O diff integral de
entrega inclui também os dois arquivos novos sem colocá-los no staging; sua
aplicabilidade à base foi conferida com um index temporário externo. Whitespace
dos não rastreados foi verificado separadamente com `git diff --no-index --check`.
