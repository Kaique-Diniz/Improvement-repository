# Revisão individual das 21 diferenças — 21/10/2026

**Resultado:** nenhum erro de extração ou normalização comprovado nas células
analisadas. As 17 diferenças de contato são inconsistências do gabarito; as quatro
datas apresentam o mesmo dia, com representação diferente no Excel de referência.
O sistema continua **não homologado para produção**.

## Procedimento e evidência

A execução foi repetida em `dados/homologacao_pacote_revisao/`, com os mesmos
dez artefatos, byte a byte, da etapa sintética aprovada. A revisão independente em
`conversor.laboratorio.review` releu os PDFs usando pypdf, sem chamar os leitores
ou o normalizador de telefone do conversor. Para cada célula, comparou:

1. O contato no bloco completo do titular na fonte, ou o vencimento na linha do
   boleto. A ausência de e-mail foi verificada até o próximo titular, incluindo
   a continuidade entre páginas, e não apenas numa linha sem contato.
2. O valor canônico após enriquecimento, respeitando a decisão já aprovada de
   priorizar Cadastro Geral na FL somente neste laboratório.
3. A célula exportada, seu tipo e o formato de exibição no Excel.
4. A célula original do gabarito, sem modificá-la.

Os telefones documentais foram conferidos removendo apenas separadores e o DDI
`+55` quando presente; DDD e número permaneceram texto. E-mails foram comparados
literalmente, sem substituir domínio, alterar caixa ou inventar valores. Datas
foram confrontadas com o dia documental, o modelo e o texto ISO do gabarito.

O diagnóstico é interrompido se fonte, modelo e saída divergirem; não atribui
automaticamente falhas novas ao gabarito. O arquivo local
`dados/revisao_individual_final/revisao_individual.json` registra cada diagnóstico,
origem, provas booleanas e hashes, sem nomes ou valores de contato. Os nove arquivos
do pacote permanecem intactos por SHA-256.

## Classificação de cada célula

Legenda: **G** = inconsistência do gabarito, **pendente de revisão do gabarito**.
**R** = problema de representação no Excel **do gabarito**, esclarecido sem
correção necessária na saída. Nos 21 casos, fonte → canônico → saída conferem.

| ID | Caso | Célula / campo | Boleto ou linha | Fonte: página/linha | Classe | Diagnóstico e tratamento |
|---|---|---|---|---|---|---|
| H01 | Habita | L2 / DDD1 | 80000101 | Inadimplência 1/5 | G | DDD documentado; referência vazia. Preservar saída. |
| H02 | Habita | M2 / FONE1 | 80000101 | Inadimplência 1/5 | G | Número documentado; referência vazia. Preservar saída. |
| H03 | Habita | V2 / EMAIL1 | 80000101 | Inadimplência 1/5 | G | E-mail da referência difere do documental. Preservar saída. |
| H04 | Habita | V3 / EMAIL1 | 80000105 | Inadimplência 2/4 | G | Referência preenche e-mail ausente de todo o bloco documental. Preservar vazio. |
| H05 | Habita | AC2 / VENCIMENTO | 80000101 | Inadimplência 1/7 | R | Mesmo dia nas três etapas; referência texto ISO, saída data nativa. |
| H06 | Habita | AC3 / VENCIMENTO | 80000105 | Inadimplência 2/6 | R | Mesmo dia nas três etapas; referência texto ISO, saída data nativa. |
| F01 | FL | L2 / DDD1 | 900101 | Cadastro 1/7 | G | DDD documentado; referência vazia. Preservar saída. |
| F02 | FL | M2 / FONE1 | 900101 | Cadastro 1/7 | G | Número documentado; referência vazia. Preservar saída. |
| F03 | FL | V2 / EMAIL1 | 900101 | Cadastro 1/6 | G | E-mail da referência difere do Cadastro Geral. Preservar saída. |
| F04 | FL | L3 / DDD1 | Cadastral A/0041 | Cadastro 1/7 | G | Mesmo DDD da unidade da linha 2; referência vazia. |
| F05 | FL | M3 / FONE1 | Cadastral A/0041 | Cadastro 1/7 | G | Mesmo número da unidade da linha 2; referência vazia. |
| F06 | FL | V3 / EMAIL1 | Cadastral A/0041 | Cadastro 1/6 | G | Mesmo e-mail documental da linha 2; referência divergente. |
| F07 | FL | L4 / DDD1 | Cadastral B/0012 | Cadastro 1/9 | G | DDD do Cadastro após resolução auditada do titular; referência vazia. |
| F08 | FL | M4 / FONE1 | Cadastral B/0012 | Cadastro 1/9 | G | Número do Cadastro após resolução auditada do titular; referência vazia. |
| F09 | FL | V4 / EMAIL1 | Cadastral B/0012 | Cadastro 1/8 | G | E-mail do titular do Cadastro corretamente priorizado; referência divergente. |
| F10 | FL | L5 / DDD1 | 900104 | Cadastro 1/11 | G | DDD documentado; referência vazia. Preservar saída. |
| F11 | FL | M5 / FONE1 | 900104 | Cadastro 1/11 | G | Número documentado; referência vazia. Preservar saída. |
| F12 | FL | V5 / EMAIL1 | 900104 | Cadastro 1/10 | G | E-mail da referência difere do Cadastro Geral. Preservar saída. |
| F13 | FL | V6 / EMAIL1 | Cadastral A/0142 | Cadastro 1/12 | G | Referência preenche e-mail ausente de todo o bloco cadastral. Preservar vazio. |
| F14 | FL | AC2 / VENCIMENTO | 900101 | Inadimplência 1/7 | R | Mesmo dia nas três etapas; referência texto ISO, saída data nativa. |
| F15 | FL | AC5 / VENCIMENTO | 900104 | Inadimplência 1/21 | R | Mesmo dia nas três etapas; referência texto ISO, saída data nativa. |

## Correções, resoluções e pendências

| Classificação | Quantidade | Situação |
|---|---:|---|
| Erro de extração | 0 | Nenhuma correção comprovadamente necessária nestas células. |
| Erro de normalização | 0 | DDI, DDD, número e e-mails conferem com a fonte. |
| Representação no Excel | 4 | Diagnóstico esclarecido; preservar datas nativas com `dd/mm/yyyy`. |
| Inconsistência do gabarito | 17 | Pendentes: dez campos telefônicos omitidos, cinco e-mails diferentes e dois e-mails sem fonte. |

**Nenhuma célula, leitor, normalizador ou regra de negócio foi alterado para
igualar o gabarito.** O template permanece com as 30 colunas, na mesma ordem.
Os quatro casos R estão resolvidos quanto ao diagnóstico técnico, mas continuam
com tipos físicos distintos da referência. A compatibilidade com o importador
de destino permanece pendente. As 17 células G exigem nova versão revisada do
gabarito pelo responsável; os arquivos recebidos não foram sobrescritos.

Foi acrescentado somente o diagnóstico reproduzível e sua regressão. Uma falha
no próprio diagnóstico ao ler célula vazia após regravação pelo openpyxl foi
corrigida durante os testes: a coordenada agora é calculada por linha/coluna.
Isso não modificou os Excel nem as diferenças da etapa aprovada.

## Testes e reprodução

```bash
.venv/bin/python -m pytest -q
# 222 aprovados
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py
# 53 aprovados: 25 do pacote e 28 da revisão
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

Os 28 testes novos incluem uma verificação para cada célula e casos negativos:
e-mail canônico errado, telefone normalizado errado, e-mail alterado na saída,
data exportada como texto e dia errado. Nesses casos a revisão bloqueia o
diagnóstico, preservando a possibilidade de investigar extração, normalização
ou representação; não culpa o gabarito indevidamente.

Para revisar novamente, use um destino que ainda não exista:

```bash
.venv/bin/python -m conversor.laboratorio.review \
  --pacote tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor \
  --execucao dados/homologacao_pacote_revisao \
  --saida dados/revisao_individual_nova
```

O status 0 significa diagnóstico concluído; as 17 pendências e o status de
produção continuam explícitos no resultado. O conversor do pacote continua
retornando status 1 pela divergência com o Excel de referência. Consulte também
[a preparação do envio ao GitHub](ENVIO_GITHUB.md).
