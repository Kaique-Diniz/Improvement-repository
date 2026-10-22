# Prontidão documental para revisão do incremento 4.3B

## Situação posterior — 4.3B.2A exclusivamente sintético

O [relatório do incremento integrado](INCREMENTO_4_3B_2A_INTEGRACAO_SINTETICA.md)
registra integração entre inventário, aprovação, motor, A/B e persistência,
com 1.111 testes e oito verificações de schemas aprovados. Não houve atestos
humanos, planos reais aprovados/ativados, simulação sobre documentos privados
ou liberação de bloqueios. O 4.3B.2B depende dos atos humanos listados no relatório
e de nova autorização. Fase 5 não iniciada; sem homologação de produção.
As declarações preparatórias abaixo preservam seu contexto histórico.

## Atualização posterior — implementação sintética 4.3B.1

O responsável autorizou exclusivamente o incremento técnico sintético 4.3B.1,
implementado com **1.027 testes aprovados**. Consulte o
[relatório de implementação e restrições](INCREMENTO_4_3B_1_TREE_SINTETICO.md).
As declarações de não início nas etapas documentais abaixo registram o estado
histórico dessas etapas. Nenhum plano real foi aprovado/ativado, nenhum atesto
humano foi emitido e nenhuma regra foi simulada sobre documentos privados nesta
tarefa. O 4.3B.2 requer autorização própria e as decisões/atestados pendentes.
Bloqueios Habita/VG, titularidade FL e documentos conflitantes permanecem ativos.
Fase 5 não iniciada; sistema não homologado para produção.

**22/10/2026 — America/Sao_Paulo.** A correção do 4.3A foi aceita tecnicamente
pelo responsável com 872 testes. Foi autorizada exclusivamente esta preparação
documental. **O 4.3B efetivo não foi iniciado e o sistema não está homologado
para produção.**

**Revisão posterior de requisitos:** o responsável definiu seleção extrajudicial,
centavo por cota/componentes, corte estrito em dias corridos, ausência de filtros
judiciais e de exclusão autônoma por garantidora, cadastro universal A/B e papéis
acumuláveis com atos separados. Essas decisões foram incorporadas **somente à
documentação e proposta**, sem implementação do 4.3B. Não substituem aprovação
formal dos planos nem atestos humanos. Veja o
[registro da atualização](ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md).

**Confirmação específica TREE:** A/AJ/J, assim como centavo, excluem a cota inteira
e componentes, independentemente do vencimento. Uma condição basta; outras cotas
continuam avaliadas. O prazo TREE é >30 dias corridos, referência explícita, sem
superar exclusões/bloqueios. `Valor` foi confirmado como referência do boleto;
seu mapeamento e os campos próprios dos apontamentos ainda exigem validação nos
documentos. Esta revisão apenas registra decisões; não lê PDFs nem assina planos.

**Etapa técnica preparatória posterior:** o
[mapeamento de Valor e apontamentos TREE](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md)
foi conferido no PDF autorizado, com preservação do canônico e dos bloqueios.
Foram adicionados testes sintéticos, sem modificar leitores/avaliador ou executar
planos reais. As afirmações de escopo exclusivamente documental acima descrevem
a etapa anterior; o atesto humano e a aprovação de plano continuam pendentes.

## Entregáveis de revisão

| Documento | Uso pelo responsável |
|---|---|
| [Checklist de atesto humano por fonte](ATESTO_HUMANO_FONTES_FASE4_3B.md) | Conferir fontes, versões, hashes, cobertura, ausências, bloqueios e responsáveis; campos humanos permanecem em branco |
| [Matriz revisada com os oito IDs](MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md) | Distinguir decisões TREE confirmadas de validação dos campos/aprovações pendentes; filtro judicial retirado, cadastro universal e prioridades/vigências não presumidas |
| [Perguntas e ficha de decisões](DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md) | Consultar respostas preliminares Q01–Q26 atualizadas e completar somente pendências remanescentes |
| [Proposta documental não executável](../examples/fase4/proposta_configuracao_4_3B.revisada.json) | Representar os requisitos definidos e lacunas, sem criar plano ou escolher modo de execução |
| [Mapeamento técnico TREE](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md) | Conferência posterior no PDF privado e testes sintéticos; escopo desta amostra, sem atesto/aprovação/ativação de planos |
| Este relatório | Distinguir integridade técnica conferida, atestos/decisões pendentes e condições para autorização posterior |

Código, contratos, schemas e exemplos históricos permanecem inalterados. Foi
adicionada proposta JSON documental separada, sem formato de plano ativável.
Não foram criados/aprovados/ativados planos reais. A conferência privada abaixo
é evidência da preparação documental anterior, não nova execução nesta revisão
de requisitos. Não houve nova preparação, simulação ou replay financeiro real.

## Conferência privada da preparação documental anterior — evidência preservada

Conferidos por leitura os quatro artefatos assinados da correção 006: reconciliação
e preparação técnica de cada condomínio. O adapter existente verificou recibos,
assinaturas, políticas históricas, hashes/tamanhos das fontes, reconstrução dos
registros, correspondência com a entrada e hash do inventário/reconciliação.

| Evidência conferida | Habita/TREE | FL/Plaza |
|---|---:|---:|
| Unidades / boletos no canônico | 112 / 769 | 50 / 115 |
| Registros originais vinculados | 904 | 205 |
| Operacionais / documentais externos | 904 / 0 | 201 / 4 |
| Ocorrências críticas externas preservadas | 1 | 83 |
| Unidades retidas pelos bloqueios existentes | 112 | 34 |
| Competências ausentes preservadas | 769 | 0 |
| Reconciliação e preparação técnica assinadas | Verificadas | Verificadas |
| Atesto humano de completude | Pendente | Pendente |

Os cinco anexos mantêm SHA e tamanho dos arquivos autorizados. Foram conferidos
82 arquivos anteriores, incluindo anexos, inventários, dossiês e recibos, sem
alteração de conteúdo. A preparação histórica Habita 1.0 também foi lida sem
migração. Nenhum pacote com atesto humano foi encontrado no repositório privado
específico da correção 006; há preparações técnicas assinadas, que não o substituem.
Essa constatação se limita a esse conjunto, não é busca em outros ambientes.

O detalhamento com hashes completos e versões registradas está exclusivamente em
`/workspace/validacao-privada-fase3/resultados/preparacao_documental_4_3B_007/`:

- `conferencia_automatica_privada.json`: evidência desta conferência técnica,
  expressamente sem atesto humano, aprovação de regra ou simulação real;
- `FICHA_PRIVADA_CONFERENCIA_HUMANA.md`: identificação das cinco fontes e dos
  conjuntos, com campos de revisão/responsável ainda não preenchidos.

Não foi fornecido, por esta conferência, novo extrato autorizado da régua ou
documento que resolva os impedimentos de titularidade/VG. Sua identificação e
vinculação continuam na lista de decisões. O fato de os anexos estarem íntegros
não prova que uma regra textual ou uma informação pessoal esteja aprovada.

## Rastreabilidade e versões que devem ser preservadas

| Identificação/contrato | Significado e estado |
|---|---|
| Registro original e `id_legado` | Conteúdo integral e ID histórico preservados, com hash do original e do JSON bruto |
| `auditoria:v1:<hash>` | ID interno de importação vinculado a namespace, produtor/versão declarada, arquivo/SHA, ponteiro JSON e registro completo |
| `documento:v2:<hash>` | Identificação documental nova corrigida no gerador; inclui pessoa, conteúdo e proveniência, sem reescrever o histórico |
| Candidato/pacote privado 1.0 | Contrato histórico preservado; leitura não adiciona reconciliação nem troca hash/recibo |
| Candidato/pacote reconciliado 1.1 | Reconciliação obrigatória e hash no inventário; a entrada contém exatamente os registros projetados |
| Preparação técnica assinada | Integridade conferida; modo sem atesto humano e sem autorização operacional |

Portanto, **“v2” não é a versão de todos os IDs internos**: os 904 + 205 registros
importados usam `auditoria:v1`; o gerador documental novo usa `documento:v2`.
Não houve conversão automática de IDs legados para v2 nesta tarefa.

Para cada vínculo foi conferida a igualdade do registro original com a projeção,
exceto pelo ID interno, e sua associação ao inventário. As duas colisões legadas
FL continuam com seus quatro registros documentais separados; células de origem
distintas não foram fundidas, mesmo contendo os mesmos documentos.

Reprodução histórica exige o pacote/schema original, fontes completas, regras e
evidências originais, data de referência, snapshot/provas administrativos,
autoridade/políticas/recibos e o código/runtime correspondente ao pin registrado.
O contexto atual não substitui o contexto antigo; divergência de implementação
impede replay em vez de reescrever a história. Esta tarefa conferiu integridade e
os testes sintéticos de regressão; não executou replay financeiro real.

Versões de leitura presentes nas origens permanecem registradas na ficha privada.
A versão histórica de alguns produtores não foi declarada e continua como tal,
sem usar o código atual como se tivesse produzido o passado.

## Prontidão e impedimentos

| Item | Situação atual | Tratamento necessário |
|---|---|---|
| Fundação técnica e correção de IDs | Aceitas tecnicamente; integridade privada reconferida | Preservar contratos e retenção dos artefatos |
| Checklist e procedimento humano | Preparados; responsável pelo projeto acumula três papéis, sem atestos emitidos | Vincular identidade autorizada e concluir manifestações independentes por fonte/conjunto |
| Matriz dos oito IDs históricos | Decisões TREE confirmadas e mapeamento de campos conferido tecnicamente neste PDF; judicial retirado e cadastro universal preservado | Atestos humanos, vínculo à régua, prioridades/vigências e aprovação dos planos ainda pendentes; não ativar nesta tarefa |
| Cadastro antecipado A/B | Requisito universal definido, sem modo selecionado | Implementação posterior; escolha por execução em histórico/auditoria, nunca contornando bloqueios |
| Prioridades e vigências | Sem valores atribuídos nesta preparação | Aprovação expressa por regra/condomínio; não inferir de período ou data atual |
| Fonte operacional da régua | Identificação/versionamento do extrato ainda necessários neste conjunto | Disponibilizar extrato autorizado pertinente, sem credenciais, para revisão humana |
| Habita/VG | Bloqueante do lote | Esclarecimento/retificação e decisão própria; atesto ou regra permissiva não liberam o lote |
| Titularidade/documentos FL | 34 unidades retidas e conflitos documentais preservados | Evidência e decisão humana fundamentadas, sem escolha automática de fonte |
| Outros críticos, campos ausentes e competência | Preservados com seus escopos/efeitos | Conferir inventário; não inferir campos nem relaxar bloqueios |
| Referências Excel | Fontes íntegras; não são gabaritos absolutos | Revisar vínculos, agrupamentos, políticas e resultados esperados |
| Planos reais e simulação financeira real | Não configurados/executados por esta tarefa | Autorização posterior e requisitos administrativos/comerciais atendidos |
| Exportação/easyCollector | Fase 5 não iniciada | Homologação integral futura; CPF/CNPJ na coluna CPF já é requisito confirmado |

O atesto de completude e a aprovação das regras são decisões diferentes. Ambos
continuam pendentes, e nenhum remove por si só um impedimento crítico. A correção
de identidade aceita também não representa aprovação de titular ou documento.

## Testes de regressão

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m conversor.billing_schemas --check
.venv/bin/python -m conversor.evaluation_schemas --check
.venv/bin/python -m conversor.private_simulation_schemas --check
.venv/bin/python -m conversor.audit_schemas --check
```

As duas suítes passaram novamente: **812 regulares + 60 explícitos = 872 testes**,
sem falhas ou skips. Não se adicionaram testes que apenas reproduzissem o texto
dos documentos; a implementação foi mantida integralmente. Os seis comandos de
conferência de schemas passaram, sem alteração de contratos históricos 1.0/1.1.
A revisão de privacidade da preparação anterior conferiu 209 arquivos versionáveis, sem cópias idênticas
dos anexos nem correspondências com os identificadores pessoais verificados no
canônico privado. Essa revisão complementa os controles, sem provar detecção
universal de qualquer dado sensível.

Na atualização documental de requisitos, as mesmas suítes foram reexecutadas:
**812 + 60 = 872 aprovados**, sem falhas ou skips; as seis conferências de
schemas passaram novamente. Também foram conferidos sintaxe do novo JSON,
preservação literal de Q01–Q26 e dos oito IDs, ordem dos 30 cabeçalhos, links
locais e escopo de alterações restrito a Markdown/proposta documental. Não são
novos testes de implementação dos requisitos, que continuam pendentes.

A conferência atual de privacidade examinou **213 arquivos versionáveis**, sem
cópias idênticas das fontes reais, correspondências identificáveis verificadas
ou permissões privadas divergentes. Fontes e dossiês privados não foram alterados
ou publicados. A conferência é complementar, sem garantia de detecção universal.

## Recomendação e condição de passagem

**Pronto para revisão humana documental; ainda pendente para iniciar o 4.3B.**
Recomenda-se usar o checklist e a ficha de decisões para obter manifestações
fundamentadas dos responsáveis. Antes da configuração e da homologação reais,
devem estar definidos os atestos dos conjuntos, a fonte operacional, o mapeamento
Valor → cota/componentes, os campos próprios/namespace e vínculos de A/AJ/J,
prioridades numéricas e vigências das regras aplicáveis. Escopo e efeito de
A/AJ/J no TREE já estão confirmados pelo negócio, não são mais decisões em aberto.
As decisões de cadastro universal e contagem já estão definidas, mas implementação
e escolhas por execução permanecem pendentes. **Não exigir semântica de 60/90 dias
judiciais para configurar o seletor extrajudicial.** Bloqueios críticos devem
continuar representados e preservados; nenhuma regra ou modo A/B os libera.

Depois disso, solicitar autorização expressa e delimitada para o próximo trabalho.
Completar formulários ou aceitar este relatório não inicia o incremento
automaticamente. Não houve implementação do 4.3B, Fase 5, cobrança real ou
homologação para produção.

## Registro da preparação

Preparação documental original sobre a base `919abf7`, revista sobre `3b2c769`,
na branch `feature/fase-4-motor-cobranca`. Esta atualização altera somente Markdown
e acrescenta uma proposta JSON documental sem dados pessoais. Fichas e evidências
privadas anteriores ficam fora do Git e não foram modificadas. Nenhum formulário
humano foi preenchido/aprovado nem criado evento administrativo de plano.

Não houve atualização de main, push, merge ou publicação dos artefatos privados.

## Registro da validação técnica preparatória posterior

A etapa autorizada depois das revisões documentais conferiu o PDF TREE na área
privada, com 769 boletos/2.082 componentes e zero divergências de mapeamento.
Detalhes, hashes e valores individuais ficam no dossiê privado 008, distinto dos
pacotes anteriores; nenhuma evidência histórica foi sobrescrita. O original
integral da cota usa `Boleto.composicao.total_original`, e A/AJ/J permanecem
vinculados ao campo e boleto corretos.

Reexecutados **855 testes regulares + 60 explícitos = 915 aprovados**, incluindo
**43 novos testes sintéticos**; seis conferências de schemas aprovadas. Os 872
testes citados nas seções anteriores registram a base documental anterior.
Novos arquivos de teste/fixture/gerador sintético e relatório público foram
acrescentados, sem alterar código de produção, schemas, regras, valores ou
documentos reais. A matriz/proposta documental está na revisão 2.2 e distingue
mapeamento técnico conferido de aprovação formal pendente.

O mapeamento deste arquivo está tecnicamente esclarecido; atestos humanos,
vínculo à régua, prioridades, vigências e plano aprovado continuam necessários.
Cobertura negativa de apontamentos não é presumida pela lista vazia. Habita/VG
e demais críticos permanecem bloqueados. Não houve implementação do motor real,
simulação de régua real ou Fase 5. Branch mantida, sem novo commit ou publicação.

## Cobertura concluída e fichas para decisão — etapa posterior

Após aceite técnico do mapeamento com 915 testes, o responsável autorizou a
conferência exaustiva dos apontamentos e preparação das fichas. O
[relatório de cobertura](COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md) contém os
769 resultados técnicos: 628 vazios validados, 141 preenchidos (A=15, AJ=9,
J=117), zero inconclusivos, 802 cabeçalhos e as 33 continuidades conferidas.

As cinco fichas estão preparadas individualmente, com estado pendente. O
[resumo de atestos restantes](RESUMO_ATESTOS_DECISOES_4_3B.md) organiza as cinco
fontes e a régua esperada, sem preencher manifestações humanas. A/B e as seis
colunas Y:AD vazias em linhas cadastrais permanecem requisitos; nenhum bloqueio
de lote, unidade ou cadastro foi liberado.

Prontidão: técnica suficiente para revisão das fichas e para delimitar autorização
posterior de implementação/configuração do 4.3B. Não autoriza execução real:
atestos, fonte/versão da régua, prioridades, vigências e aprovação da versão/hash
continuam pendentes. A conferência aditiva não está integrada automaticamente ao
motor ou à exportação; gera evidência candidata e críticos para inconclusões,
mantendo revisão até a incorporação autorizada no pacote completo.

Regressão desta etapa: **883 regulares + 60 explícitos = 943 aprovados**, incluindo
28 testes novos de campo vazio/presença/ambiguidade. Seis conferências de schemas
passaram; contratos históricos preservados. Fonte original e dossiês privados
continuam fora do Git. Nenhum evento de aprovação, assinatura ou ativação de
plano real foi emitido.
