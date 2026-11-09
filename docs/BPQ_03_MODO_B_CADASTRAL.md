# BPQ-03 — Linha cadastral individual comprovada no modo B

Entrega preparada inicialmente sem commit, push, PR ou merge. Branch
`feat/bpq03-modo-b-cadastral-int02`, worktree
`/workspace/Improvement-bpq03-modo-b`, HEAD/base exata
`46dc86da94b93bb6242ee6e73f4431c1e1fc09c5`.
A autorização BPQ-03-B permite somente um commit e push nesta branch para
auditoria externa, sem PR ou merge. Windows não executado. Não há homologação
operacional ou autorização de cobrança.

## A. Condição de início e isolamento

A referência remota BPQ-02 foi consultada e confirmou o SHA acima. Seu único pai
é a INT-02 `35f57d98fd0fca18b045b03fa4850835a92488cd`; os três arquivos BPQ-02
estão presentes. O responsável confirmou expressamente a auditoria estática
concluída sem bloqueadores antes de iniciar código. Não se presumiu aprovação
apenas pela existência da branch ou da publicação.

A BPQ-02 estava limpa. Foram registrados heads e estados dos 14 worktrees
anteriores, inclusive os experimentos Windows não commitados. A branch nova
nasceu do commit BPQ-02 efetivamente aprovado. Main, INT-02, BPQ-02, demais
branches e PRs não foram alterados. Não houve reset ou limpeza destrutiva.

## B. Diagnóstico, com evidências de código

1. `LeitorBeachParqueXLSX.ler()` cria a Pessoa da unidade só com o nome do
   cabeçalho financeiro e a origem. Não atribui documento/contatos cadastrais.
2. `service.analisar()` mantém essa pessoa em `pessoas[unidade_id]` para a
   base da exportação. `associar_beach()` retorna separadamente pessoas A1
   indexadas por boleto, calculadas para todos os recibos, não só elegíveis.
3. No ramo das dívidas, `base_divida` já substituía a pessoa pela associação
   individual A1. No ramo cadastral, `LinhaExportacao(**base,tipo='cadastral')`
   mantinha a pessoa-base sem esses dados. Isso explica as 159 linhas adicionais
   sem CPF/contatos mesmo quando existia associação individual comprovada.
4. Os lançamentos relevantes são exclusivamente os da unidade com
   `situacao_financeira == 'excluido'`. Um boleto elegível não justifica a linha
   cadastral e sua Pessoa não é usada como atalho de preenchimento.
5. O cadastro próprio separa titular/pagador/locatário/unidade. B1 exige o
   titular, identidade completa de condomínio, administradora, bloco e unidade,
   documento válido e evidência original, sem escolher um participante por ordem.
6. Nas unidades mistas, o ramo de dívidas permanece intacto. A linha adicional
   continua única por unidade conforme a seleção anterior; apenas seus campos
   pessoais passam pelo resolvedor. Responsáveis diferentes retêm os dados.
7. O hook B1 exige `familia == 'habitacional_beach'` e modo B. Os cinco outros
   perfis foram confrontados com a BPQ-02 em A/B, usando os mesmos bytes
   sintéticos: XLSX binário, 30 colunas, boletos, decisões, resumo e política
   permaneceram idênticos.

`LinhaExportacao`, `DividaExportacao`, materializador e escritor não foram
alterados. Continuam impondo coerência cadastral/divida e o contrato universal.

## C. Implementação e contrato B1

Política: `beach_parque_linha_cadastral_individual_comprovada_B1@1`.
Ela estende, sem substituir, `beach_parque_titular_nominal_documento_valido_A1@1`.

`resolver_linha_cadastral()` foi acrescentado à aplicação específica BPQ.
Recebe lote, unidade, pessoa-base, decisões financeiras, mapa A1 por lançamento
e cadastro da conversão. Retorna Pessoa comprovada ou None e decisão sanitizada.
Não decide elegibilidade, quantidade de linhas ou exportação operacional.

Aprovação exige, para TODOS os lançamentos relevantes:

- Pelo menos um lançamento excluído, sem IDs duplicados ou associações faltantes.
- Unidade canônica, administradora/condomínio e identidade textual do cadastro
  iguais; exatamente um titular, com papel próprio e nome concordante segundo
  a normalização A1 existente. A Pessoa-base deve representar a mesma identidade.
- Nenhum código A1 de retenção; nenhum conflito fiscal, multiplicidade ou
  documento ausente/inválido. Nenhuma ressalva crítica relevante/global.
- Documento único válido igual ao do titular, evidência vinculada à Pessoa A1
  e origem exatamente presente na documentação do titular.
- Origem financeira da Pessoa A1 presente no boleto correspondente; contato
  igual ao do titular aprovado. A mera presença de Pessoa não basta.

Só após comprovar equivalência integral entre todas as associações é usada uma
representação determinística, ordenada por IDs. Não se escolhe a primeira
alternativa para resolver conflito. Se qualquer condição falhar, não se promove
nenhum dado pessoal. Não se reimplementou normalização fiscal ou nominal A1.
A função `associar()` anterior foi comparada por AST e permanece inalterada.

`service.analisar()` constrói `base_cadastral` separado. Preserva NOME financeiro,
CEDENTE, complemento, endereço configurado e seleção atual. Só reutiliza os dados
pessoais comprovados para aquela linha; nunca modifica a pessoa-base, a Pessoa
A1, o cadastro ou os ramos financeiros. Não copia endereço do PDF, do template
ou de outro participante. NU_PARCELA/VENCIMENTO/VL_PARCELA e demais campos da
dívida continuam vazios na linha cadastral.

### Decisões auditáveis

A chave `modo_b_cadastral_beach_parque` existe somente no modo B do Beach Parque,
com a política e uma decisão por candidata: unidade canônica, IDs dos boletos
relevantes, origens, estado, motivo de retenção, comprovada e exportada.
O estado exportada descreve a seleção anterior, não uma autorização operacional.
As decisões ficam no resultado, manifesto e auditoria temporária. Não duplicam
ressalvas A1 nem aumentam artificialmente a contagem de ocorrências financeiras.

Estados: `BPQ_B1_ASSOCIACAO_COMPROVADA`, `BPQ_B1_NOME_DIVERGENTE`,
`BPQ_B1_RESPONSAVEIS_MULTIPLOS`, `BPQ_B1_DOCUMENTO_TITULAR_AUSENTE`,
`BPQ_B1_DOCUMENTO_CONFLITANTE`, `BPQ_B1_ASSOCIACAO_INSUFICIENTE` e
`BPQ_B1_CADASTRO_NAO_FORNECIDO`. Ausência/invalidade usa o mesmo estado de
retenção documental; a evidência original continua privada. Nenhum texto público
de alerta inclui nome, CPF/CNPJ, telefone ou e-mail.

### Justificativa da alteração no transporte efêmero

O Chromium demonstrou que a lista de campos de detalhes em
`CicloEfemero.processar()` descartava a nova chave, apesar de ela existir no
serviço e nos arquivos temporários. Foram acrescentadas duas linhas em
`web/ephemeral.py` para encaminhá-la somente ao payload de detalhes autenticado
Beach Parque B. O limite de cache continua aplicado DEPOIS da serialização,
incluindo a chave nova. Sessão, CSRF, Host/Origin, limites, TTL, workers,
download e descarte não foram alterados. Nenhum frontend ou endpoint novo.

## D. Reconciliação privada em 09/11/2026

Mesmos arquivos e hashes de fonte, mesma data e modos A/B. O serviço BPQ-02 foi
carregado do commit aprovado, e comparado ao serviço novo. Extração geométrica
real do PDF validada uma vez e reutilizada, apenas no harness privado e para
os mesmos bytes exatos. Não foi instalado cache no produto nem criada
persistência de dados cadastrais. Temporários foram descartados em todos os
quatro ciclos; somente agregados anonimizados são entregues.

| Indicador | BPQ-02 | BPQ-03 |
| --- | ---: | ---: |
| Recibos originais | 1.010 | 1.010 |
| Elegíveis A e financeiros B | 850 | 850 |
| Original elegível | R$ 603.477,71 | R$ 603.477,71 |
| Não elegíveis | 160 | 160 |
| Unidades com não elegíveis | 159 | 159 |
| Cadastrais adicionais B | 159 | 159 |
| Total modo B | 1.009 | 1.009 |
| Documentos nas dívidas | 747 | 747 |
| Retenções A1 elegíveis | 103 | 103 |
| Retenções A1 totais | 115 | 115 |
| Colunas | 30 | 30 |
| Divergências financeiras antes/depois | 0 | 0 |

Modo A idêntico, inclusive nos bytes do XLSX. Boletos canônicos idênticos nas
quatro execuções. Todas as linhas financeiras B são idênticas às de A, antes
e depois. Nas cadastrais, só CPF e os 13 campos de telefone/e-mail podiam variar;
147 linhas mudaram. Todos os demais campos foram comparados posição a posição
sem alteração, incluindo nome, endereço e identificadores. Não se inventou
valor, vencimento, descrição ou parcela; 159 unidades não viraram 160 recibos
nem se acrescentaram as 622 fichas do PDF como linhas novas.

### Motivos exclusivos nas 159 linhas cadastrais

| Decisão B1 | Linhas |
| --- | ---: |
| `BPQ_B1_ASSOCIACAO_COMPROVADA` | 147 |
| `BPQ_B1_DOCUMENTO_TITULAR_AUSENTE` | 1 |
| `BPQ_B1_NOME_DIVERGENTE` | 10 |
| `BPQ_B1_RESPONSAVEIS_MULTIPLOS` | 1 |
| **Total** | **159** |

147 aprovações e 12 retenções: dez nomes divergentes, um documento do titular
ausente e uma multiplicidade. Conflito documental, ausência total de cadastro
e outra insuficiência tiveram zero nesta amostra; permanecem cobertos por
regressões. Não somar essas 12 linhas às 115 retenções A1 por lançamento: são
universos diferentes e a A1 existente não mudou.

A triagem reproduziu 148 coincidências nominais com documento válido. Uma tem
nome conjunto e documento único sem individualização suficiente; a A1 e a B1
retêm essa associação. Portanto, triagem 148 não equivale a 148 aprovações.
Não se alterou regra ou documento para atingir uma contagem preliminar.

### Preenchimento e sobreposições

| Campo/conjunção | Linhas |
| --- | ---: |
| CPF/CNPJ | 147 |
| Pelo menos um telefone | 143 |
| Pelo menos um e-mail | 144 |
| CPF/CNPJ e telefone | 143 |
| CPF/CNPJ e e-mail | 144 |
| CPF/CNPJ, telefone e e-mail | 142 |
| Todos os contatos disponíveis, validados e comprovados dentro dos limites | 147 |

A última linha não significa que 147 tenham telefone e e-mail. Duas só têm
documento, sem contatos disponíveis validados; as demais preservam todos os
contatos aprovados pela BPQ-02, dentro de cinco telefones/três e-mails. Campos
com anotação desconhecida/terceiro e excedentes permanecem na evidência privada.

Contagem exclusiva: 142 com documento+telefone+e-mail; uma com documento+telefone;
duas com documento+e-mail; duas somente com documento; 12 sem dados pessoais.
Soma 159. As linhas de conjunção da tabela anterior são sobrepostas e não devem
ser somadas como se fossem pessoas ou unidades distintas.

Cada um dos 147 documentos foi confrontado automaticamente, linha a linha,
com o documento válido do titular da ficha PDF e a identidade financeira,
incluindo nome normalizado e unidade. Telefones/e-mails foram comparados com
os contatos do mesmo titular; nenhum pagador ou locatário foi promovido.
Documentos permanecem texto com zeros e formato @. Macros, fórmulas e referências
externas foram procuradas no workbook e no ZIP XLSX: ausentes.

## E. Regressões e navegador

| Execução | Aprovados | Falhas/erros/skips |
| --- | ---: | --- |
| Novas BPQ-B1 | 39 | 0/0/0 |
| beach_parque | 162 | 0/0/0 |
| int02 | 108 | 0/0/0 |
| ux01_int01 | 100 | 0/0/0 |
| linux | 2598 | 0/0/0 |

Total anterior 2.559; atual 2.598 = 2.559 + 39 testes novos. Contagens das suítes
separadas se sobrepõem e não devem ser somadas. Linux/Python 3.12.14, um warning
preexistente Starlette/AnyIO na suíte completa. Nenhum teste existente foi
modificado, removido, ignorado ou marcado como xfail.

Positivos: CPF/CNPJ, zeros, pessoa jurídica com E, contato simples e anotado,
DDD vazio, vários contatos, vários não elegíveis, unidade mista, uma só linha,
determinismo, origem e coerência resultado/manifesto/auditoria. Negativos:
nome divergente, múltiplos titulares/responsáveis, documento ausente/inválido,
conflito, A1 retida, fonte documental/pessoal insuficiente, pessoa de outro
boleto/unidade, cadastro cruzado, ressalva crítica local/global,
contato terceiro/ambíguo, template como única evidência, ausência de cadastro,
nenhum não elegível e proibição de aproveitar Pessoa de uma dívida elegível.
29/30/31 dias permanecem cobertos sem mudar a política provisória.

Comparação separada dos cinco perfis nas duas versões: dez saídas A/B, com
mesmos bytes de fixture/data/parâmetros, arquivos XLSX binários e dados
financeiros/IDs/decisões/políticas/resumos idênticos. Registros de igualdade
anonimizados acompanham o pacote. Nenhuma regra universal foi alterada.

Chromium real: upload/identificação, cadastro anotado, conversão A e B, prévia
30 colunas e download com CPF/contato B1 somente na linha autorizada. Duas
capturas inteiramente sintéticas. Segunda sessão inicializada com autenticação
e CSRF válidos recebeu 404; exportação operacional recebeu 409. Download servido
foi descartado, nova tentativa recebeu 404; área sem arquivos após o ciclo e
completamente vazia após shutdown normal; zero erros JavaScript.
O harness inicial foi corrigido para usar CSRF também em GET /excel e distinguir
a raiz temporária viva de resíduos de arquivos; não se alterou a proteção do
produto para acomodar o teste. A descoberta real do payload omitido gerou a
correção mínima de transporte e duas regressões HTTP, incluídas nos 39 testes.

`pip check`, `compileall`, whitespace e inspeção de não rastreados aprovados.
Windows não executado; Chromium/Linux não certificam Windows. Não há garantia
nova de RSS global, cancelamento imediato, prazo máximo de worker, limpeza após
SIGKILL/queda de energia ou apagamento forense; as limitações do MVP permanecem.

## F. Segurança, privacidade e escopo

O leitor BPQ-02 permanece byte a byte idêntico à base aprovada; sua recuperação
de contatos e as retenções ambíguas não foram reimplementadas. A1 original,
financeiro, modelos canônicos, exportador, perfis, endereço, regras dos outros
condomínios, HMAC, recibos, hashes e Windows ACL permanecem preservados.
B1 não escreve cadastro permanente nem consulta inventários de sessões anteriores.

As restrições de litígio e comunicação permanecem alertas; nenhuma cobrança,
comunicação, importação easyCollector, exportação operacional ou integração
foi habilitada. Não se publicou dado real. Nenhuma fonte real, contato, nome,
documento, endereço, observação jurídica, credencial ou identificador privado
integra este diff, o relatório ou as capturas entregues.

## G. Arquivos e Git

- `src/conversor/application/beach_parque_cadastro.py`: resolvedor B1 novo;
  função associar A1 intacta.
- `src/conversor/web/service.py`: base cadastral separada e decisões B1;
  seleção e ramos financeiros intactos.
- `src/conversor/web/ephemeral.py`: duas linhas de transporte condicional da
  auditoria para detalhes autenticados, antes do limite de cache existente.
- `tests/beach_parque/test_modo_b_cadastral.py`: 39 testes sintéticos.
- `docs/BPQ_03_MODO_B_CADASTRAL.md`: este relatório.

Ao encerrar a implementação local, staging vazio e HEAD na base, com referências
e worktrees anteriores preservados. A publicação posterior BPQ-03-B limita-se
a estes cinco arquivos, em um único commit sobre a BPQ-02. O diff completo
incluiu também os dois arquivos novos, conferidos com index externo temporário.
Nenhum patch, ZIP, fonte ou relatório privado será adicionado ao Git.

## H. Pendências

As 12 linhas retidas exigem prova adicional, não relaxamento de política.
A ficha de 22/01/2025 não comprova titularidade ou vigência em novembro/2026;
a aprovação B1 é documental e diagnóstica. As 148 coincidências não constituem
autorização pessoal ou operacional. Windows real e homologação operacional
continuam pendentes. Somente a publicação isolada para auditoria está autorizada
na BPQ-03-B; nenhum novo comportamento ou trabalho adicional está autorizado.

## Execução local

```bash
cd /workspace/Improvement-bpq03-modo-b
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web --port 8043
```

Abrir http://127.0.0.1:8043, escolher fonte/cadastro compatíveis e modo B, conferir
a prévia e baixar o diagnóstico. Não importar no CRM. Aguardar revisão externa.

## Conferência Git anterior ao staging de publicação

```text
$ git branch --show-current
feat/bpq03-modo-b-cadastral-int02
$ git rev-parse HEAD
46dc86da94b93bb6242ee6e73f4431c1e1fc09c5
$ git status --short
 M src/conversor/application/beach_parque_cadastro.py
 M src/conversor/web/ephemeral.py
 M src/conversor/web/service.py
?? docs/BPQ_03_MODO_B_CADASTRAL.md
?? tests/beach_parque/test_modo_b_cadastral.py
$ git diff --stat
 src/conversor/application/beach_parque_cadastro.py | 82 ++++++++++++++++++++++
 src/conversor/web/ephemeral.py                     |  2 +
 src/conversor/web/service.py                       | 22 +++++-
 3 files changed, 103 insertions(+), 3 deletions(-)
$ git diff --check
[sem saída; exit 0]
$ git diff --cached --name-only
[sem saída; staging vazio]
```

O stat convencional cobre os três arquivos rastreados. O patch completo também
inclui relatório e testes novos, verificados separadamente para whitespace,
sem adicioná-los ao staging. Nenhum arquivo privado integra o diff.

## Reexecução BPQ-03-B antes da publicação

Em 09/11/2026, foram repetidos Beach Parque (162), INT-02 (108),
UX-01/INT-01 (100) e a suíte Linux completa (2.598): todos aprovados,
sem falhas, erros ou skips. O warning preexistente Starlette/AnyIO permanece.
Chromium real A/B voltou a comprovar isolamento, descarte e bloqueio operacional.
O confronto privado antes/depois e as dez saídas sintéticas dos outros cinco
perfis repetiram os resultados acima. Dependências, sintaxe e whitespace
aprovados. Código e testes são os mesmos apresentados à revisão BPQ-03;
somente este documento recebeu o contexto da publicação controlada.
