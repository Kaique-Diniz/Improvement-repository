# BPQ-01 — Complemento cadastral e de restrições

Esclarecimento local para revisão externa, na referência de **16/10/2026**.
Branch `feat/terraco-beach-parque-habitacional-efemero`, HEAD/base
`2b7d6347d23e0ea79e16216c10042b5a20674344`. Sem commit, push, PR ou merge.
Nenhum módulo de produção, regra financeira ou política A1 foi alterado nesta
revisão. O complemento acrescenta somente este relatório e quatro casos de
regressão sintéticos em `tests/beach_parque/test_cadastral_clarification.py`.

## Universo e método reproduzível

Os SHA-256 dos dois documentos privados foram reconferidos antes da leitura.
O financeiro fornece 1.010 ocorrências documentais, sem deduplicar recibos,
em 183 unidades. O PDF fornece 622 fichas distintas e 206 continuações.
A identidade da unidade exige administradora, condomínio, bloco e unidade;
nenhum número de documento é selecionado por coincidência de unidade.

1. Ler as fontes pelos leitores próprios e preservar cada ocorrência financeira.
2. Aplicar a associação existente `beach_parque_titular_nominal_documento_valido_A1@1`.
3. Vincular o código de retenção ao ID de cada boleto, sem contar uma mesma
   ocorrência mais de uma vez na matriz de motivos principais.
4. Separar elegíveis pela regra já aprovada para diagnóstico:
   `(date(2026, 10, 16) - vencimento).days > 30`.
5. Contar ocorrências e unidades distintas por motivo. As contagens de unidades
   elegíveis e não elegíveis podem se sobrepor; não devem ser somadas.
6. Examinar separadamente os documentos de titular, pagador e locatário nas
   fichas originais. Validar formato e dígitos fiscais com o normalizador
   existente, sem completar documento nem transferi-lo entre papéis.
7. Contar os alertas por unidade distinta no cadastro completo e, em separado,
   sua interseção com unidades e lançamentos financeiros.

Nenhum nome, CPF/CNPJ, telefone, endereço individual, identificador de unidade,
texto jurídico ou número de processo real integra este relatório. Os agregados
secundários abaixo descrevem interseções, sem criar novos motivos de retenção.

## Matriz exclusiva das 115 retenções

| Código existente e descrição | Total de lançamentos | Elegíveis | Não elegíveis | Unidades distintas | Unidades com elegíveis | Unidades com não elegíveis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` — nome financeiro não concorda com o titular cadastral | 65 | 55 | 10 | 13 | 8 | 10 |
| `PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` — nome conjunto sem prova documental individual suficiente | 17 | 16 | 1 | 1 | 1 | 1 |
| `BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA` — nesta amostra, documento do titular ausente | 33 | 32 | 1 | 2 | 2 | 1 |
| `PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO` — documentos válidos conflitantes do titular | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total, sem duplicação de ocorrência** | **115** | **103** | **12** | **16** | **11** | **12** |

Os prefixos `PASSAREDO_` são os códigos históricos compartilhados da A1;
não significam que a fonte foi encaminhada ao leitor financeiro do Passaredo.
A política reportada pelo Beach Parque continua sendo a própria política BPQ.

Nesta amostra, os três motivos não nulos atingem conjuntos distintos de
unidades: 13 + 1 + 2 = 16. Sete dessas unidades possuem simultaneamente
lançamentos elegíveis e não elegíveis. Portanto, 11 unidades com elegíveis e
12 com não elegíveis não representam 23 unidades distintas.

A ordem existente do motivo principal é: divergência nominal; multiplicidade;
conflito documental; ausência/invalidade de documento do titular. Os documentos
originais também foram examinados independentemente dessa prioridade para
verificar se algum conflito ou documento inválido estaria oculto por outro
motivo. Não foi encontrado nenhum desses casos entre os 115 retidos.

## Relação com os 55 e os 32 casos anteriores

- Os **55 elegíveis em oito unidades nominalmente divergentes** são exatamente
  a parcela elegível dos 65 lançamentos do primeiro motivo. Há outros dez
  lançamentos não elegíveis, completando 65 em 13 unidades no universo integral.
- Os **32 elegíveis em duas unidades sem documento do titular** são exatamente
  a parcela elegível dos 33 lançamentos do terceiro motivo. O lançamento
  restante é não elegível. Não se trata de documento fiscal inválido: o campo
  do titular está ausente; existe documento válido apenas no papel de pagador.
- Os **16 elegíveis restantes** pertencem a uma unidade com nome conjunto e
  documento único. Com um não elegível, esse grupo soma 17.

Assim, **55 + 32 + 16 = 103 elegíveis** e **10 + 1 + 1 = 12 não elegíveis**.
Não se acrescentou retenção para coincidir com uma contagem de referência.

Na unidade de multiplicidade, o nome integral das fontes concorda, mas contém
conectivo E, não tem designador empresarial e há um único documento válido do
tipo CPF. Não há separador de lista explícito neste caso. Um CPF fiscalmente
válido não identifica individualmente os participantes de um nome conjunto.
A A1 retém documento e contatos; não escolhe a primeira pessoa. O comportamento
para uma empresa legítima com E, CNPJ válido e designador empresarial continua
coberto pelas regressões existentes e não foi alterado.

## Matriz secundária por situação documental

As linhas desta tabela **não são aditivas**. Cada ocorrência pode ter documento
do pagador ou do locatário além do motivo principal já contado acima.

| Situação observada entre os 115 retidos | Total | Elegíveis | Não elegíveis | Unidades |
| --- | ---: | ---: | ---: | ---: |
| Titular sem documento original | 33 | 32 | 1 | 2 |
| Titular com documento inválido ou malformado, sem documento válido | 0 | 0 | 0 | 0 |
| Titular com documento válido, mas associação nominal/individual não comprovada | 82 | 71 | 11 | 14 |
| Documento válido exclusivamente do pagador, sem documento válido do titular ou do locatário | 33 | 32 | 1 | 2 |
| Documento válido exclusivamente do locatário, sem documento válido do titular ou do pagador | 0 | 0 | 0 | 0 |
| Documento válido do pagador presente, inclusive quando há documento do titular | 115 | 103 | 12 | 16 |
| Documento válido do locatário presente em associação retida | 9 | 8 | 1 | 1 |
| Pagador e locatário com documentos válidos, mas titular sem documento válido | 0 | 0 | 0 | 0 |
| Documentos válidos conflitantes do titular, inclusive como condição secundária | 0 | 0 | 0 | 0 |
| Ausência da ficha cadastral | 0 | 0 | 0 | 0 |

Os 82 casos com documento válido do titular correspondem a 65 por nome
incompatível e 17 por multiplicidade; entre elegíveis, 55 + 16 = 71. Validade
fiscal não comprova a associação pessoal e não supera a divergência de nomes.
Os nove casos com documento válido do locatário são uma sobreposição; não
são nove retenções adicionais nem justificam transferir esse documento.

A ausência de cadastro é a estatística existente `lancamentos_sem_cadastro`,
zerada nesta amostra, não um novo código de retenção. Ausência e invalidade
continuam agrupadas no código BPQ em produção, mas foram distinguidas pela
leitura das evidências originais nesta auditoria. Os contatos pessoais de
todos os 115 retidos ficaram vazios, assim como seus documentos; nomes e
ocorrências financeiras foram preservados.

## Restrições operacionais: universo e interseções

| Código e alerta | Unidades no cadastro completo | Unidades financeiras | Unidades com elegíveis | Lançamentos financeiros afetados | Elegíveis | Não elegíveis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BPQ_REVISAO_LITIGIO_SUSPENSAO_CONTATO` — litígio/suspensão de contato para revisão | 1 | 1 | 1 | 32 | 31 | 1 |
| `BPQ_REVISAO_BLOQUEIO_REENVIO` — bloqueio de reenvio automático de boletos | 9 | 3 | 3 | 37 | 34 | 3 |
| `BPQ_REVISAO_NAO_RECEBER_CARTA` — restrição cadastral a carta | 2 | 2 | 1 | 33 | 31 | 2 |

As nove ocorrências de bloqueio são nove unidades do cadastro inteiro, não
nove unidades com dívida neste lote: só três estão no financeiro atual.
As categorias de alerta se sobrepõem, inclusive entre os mesmos lançamentos;
**não se somam** para obter quantidade de pessoas, unidades ou retenções.
O resumo existente identifica o cadastro completo, enquanto os alertas por
lançamento só se aplicam à sua própria unidade.

Os 32 lançamentos da unidade sinalizada por litígio coincidem com 32 retenções
por documento do titular ausente. O conjunto de bloqueio de reenvio sobrepõe
35 retenções: 32 por ausência de documento e três por divergência nominal.
O conjunto de restrição a carta sobrepõe 33: 32 por ausência e uma por nome.
Essas sobreposições não são causas adicionais de retenção e não apagam dívida.

O litígio é reconhecido pelo marcador do cabeçalho da ficha, além do suporte
existente a uma classificação explícita. A existência de um alerta não
certifica uma situação judicial atual nem autoriza operação: o cadastro é
histórico, de 22/01/2025. Todas as origens dos três tipos de alerta conferem
com o SHA-256 do cadastro; página/linha/coordenadas ficam na evidência privada.
Não foram copiados observação jurídica, número de processo ou nomes reais.
A orientação geral da régua de não enviar cartas permanece independente
somente como restrição diagnóstica; nenhuma funcionalidade de envio foi criada.

## Separação dos papéis e comprovação sintética

Somente os dados de `titular` podem ser candidatos ao vínculo com a pessoa
financeira. `pagador`, `locatario`, contatos da unidade e texto livre continuam
em estruturas/evidências separadas. Não se escolhe o primeiro documento válido
encontrado na ficha. O cadastro completo tem 22 unidades alugadas; a presença
de locatário não muda, por si só, a elegibilidade financeira ou o titular.

A inspeção dos testes encontrou duas lacunas específicas:

1. A regressão prévia de litígio usava `Classificação: Litígio`, enquanto a fonte
   efetiva sinaliza no cabeçalho. Acrescentados dois casos, um por modo A/B,
   com o marcador de cabeçalho e as três restrições simultâneas. Eles comparam
   antes/depois do cadastro: IDs, valores, vencimentos e situações financeiras
   são idênticos; apenas os alertas são acrescentados. Preservam uma dívida e,
   no modo B, uma linha cadastral; não autorizam cobrança nem saída operacional.
2. As regressões anteriores exercitavam documento malformado e outros papéis
   juntos. Acrescentados dois casos de ausência pura de documento do titular:
   documento válido exclusivamente do pagador, e exclusivamente do locatário.
   O teste primeiro comprova que o outro documento foi efetivamente extraído
   e é válido; depois exige documento, DDD, telefone e e-mail vazios na saída
   do titular, mantendo a dívida integral e os bloqueios operacionais.

Não foi preciso modificar parser, associação, A1, configurações ou serviço.
Continuam passando os casos prévios de CPF/CNPJ inválido, conflito fiscal,
nomes divergentes, multiplicidade, empresa com E, dados de terceiros, cadastro
omitido, CSRF, isolamento de sessão, download e descarte.

## Resultados e escopo preservado

- Beach Parque: **63 testes aprovados**, dos quais quatro casos novos neste
  complemento; zero falhas/erros/skips, um warning preexistente Starlette/AnyIO.
- Suíte Linux: **2.275 aprovados**, zero falhas, erros ou skips; o mesmo warning.
- Inspeção de hashes confirma que todos os arquivos anteriores da BPQ-01
  permaneceram byte a byte iguais nesta revisão, inclusive leitores financeiros,
  A1, leitor cadastral, serviço, configurações, UI e testes anteriores.
- Recontagem privada: 1.010 recibos, 7.365 componentes, 183 unidades,
  850 elegíveis somando R$ 603.477,71, 160 não elegíveis em 159 unidades.
- Reconciliação de saída A/B mantém 850 financeiras, 159 cadastrais adicionais,
  duas diferenças históricas de parcela e 30 colunas; não há ajuste para imitar
  os documentos históricos. Isolamento e descarte permanecem cobertos.
- Staging vazio; whitespace, sintaxe e dependências verificados. Somente este
  relatório e o novo arquivo de testes foram acrescentados ao trabalho anterior.
- Branch/HEAD e referências das demais branches permaneceram inalterados.
  Não houve commit, push, PR, merge ou integração com outra frente.

O complemento justifica as 115 retenções sem reduzir suas garantias. A revisão
externa e a validação Windows continuam pendentes; não há homologação operacional.
