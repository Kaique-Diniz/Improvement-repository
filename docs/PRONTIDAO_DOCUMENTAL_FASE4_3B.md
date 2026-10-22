# Prontidão documental para revisão do incremento 4.3B

**22/10/2026 — America/Sao_Paulo.** A correção do 4.3A foi aceita tecnicamente
pelo responsável com 872 testes. Foi autorizada exclusivamente esta preparação
documental. **O 4.3B efetivo não foi iniciado e o sistema não está homologado
para produção.**

## Entregáveis de revisão

| Documento | Uso pelo responsável |
|---|---|
| [Checklist de atesto humano por fonte](ATESTO_HUMANO_FONTES_FASE4_3B.md) | Conferir fontes, versões, hashes, cobertura, ausências, bloqueios e responsáveis; campos humanos permanecem em branco |
| [Matriz de negócio com as oito regras](MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md) | Entender propostas, escopos/ações pendentes, prioridade sem número presumido, vigência e decisões por condomínio |
| [Perguntas e ficha de decisões](DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md) | Responder Q01–Q26 e fundamentar cada regra antes de qualquer configuração real |
| Este relatório | Distinguir integridade técnica conferida, atestos/decisões pendentes e condições para autorização posterior |

Não foram alterados código, contratos, schemas, a matriz JSON ou exemplos de
configuração. Não foram criados/aprovados/ativados planos reais. A execução
privada desta tarefa apenas leu e conferiu fontes, inventários, vínculos e
assinaturas; não chamou execução nem replay de simulação financeira real.

## Conferência privada realizada agora

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
| Checklist e procedimento humano | Preparados; nenhum atesto emitido | Designar responsáveis e concluir as revisões por fonte/conjunto |
| Oito propostas de negócio | Documentadas; todas pendentes | Responder perguntas, vincular fontes e aprovar parâmetros e vigências |
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
A revisão de privacidade conferiu 209 arquivos versionáveis, sem cópias idênticas
dos anexos nem correspondências com os identificadores pessoais verificados no
canônico privado. Essa revisão complementa os controles, sem provar detecção
universal de qualquer dado sensível.

## Recomendação e condição de passagem

**Pronto para revisão humana documental; ainda pendente para iniciar o 4.3B.**
Recomenda-se usar o checklist e a ficha de decisões para obter manifestações
fundamentadas dos responsáveis. Antes da configuração e da homologação reais,
devem estar definidos os atestos dos conjuntos, a fonte operacional e as oito
decisões completas, inclusive semântica jurídica, prioridade, vigência e cadastro
antecipado. Os bloqueios críticos devem continuar representados e preservados.

Depois disso, solicitar autorização expressa e delimitada para o próximo trabalho.
Completar formulários ou aceitar este relatório não inicia o incremento
automaticamente. Não houve implementação do 4.3B, Fase 5, cobrança real ou
homologação para produção.

## Registro da preparação

Documentação preparada sobre a base `919abf7`, na branch
`feature/fase-4-motor-cobranca`. Somente arquivos Markdown públicos sem dados
pessoais foram alterados/adicionados no checkout. Ficha preenchível com hashes
reais e evidência técnica ficaram na área privada, fora do Git. Nenhum formulário
humano foi preenchido/aprovado, nem criado evento administrativo de plano.

Não houve atualização de main, push, merge ou publicação dos artefatos privados.
