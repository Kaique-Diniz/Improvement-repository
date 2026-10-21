# Fase 3 — Integração dos leitores e preparação da validação privada

## Situação da entrega

Base: `origin/main` em `410f7d6`, após o merge do PR #2 no GitHub. A `main`
local foi atualizada a partir dessa referência e a branch de trabalho criada
como `feature/fase-3-leitores`. Nenhum merge foi realizado nesta tarefa.

O contrato comum e a preparação da validação foram implementados. **O aceite
da Fase 3 permanece pendente:** o usuário confirmou que ainda não existe caminho
autorizado com PDFs reais e gabaritos revisados neste ambiente. Nenhum documento
real foi lido ou copiado e nenhuma incompatibilidade de layout real foi avaliada.
A Fase 2 continua sendo a última fase declarada concluída.

Não houve implementação de regras da Fase 4. A validação privada não importa o
motor de cobrança, os módulos de exportação ou o laboratório que executa regras.
Os leitores e o sistema continuam **não homologados para produção**.

## Implementação e lacunas técnicas corrigidas

| Módulo | Alteração |
|---|---|
| `readers/contracts.py` | Preserva `Leitor.ler(FonteProtegida, formato_id=..., condominio_id=...) -> LoteCanonico`; acrescenta portas de fontes e resolução de contexto. |
| `readers/operational.py` | Adapta as três gramáticas existentes ao mesmo protocolo; registro por `leitor_id` e versão, sem criar leitor por condomínio. |
| `readers/cadastro.py` | Declara o identificador da gramática existente; o adapter converte o dicionário legado em unidades/pessoas canônicas, com `boletos=()`. |
| `readers/text_support.py` | Campo opcional de versão do leitor no contexto; chamadas anteriores preservam o comportamento e a proveniência originais. |
| `adapters/protected_sources.py` | Arquivo identificado por ID opaco e SHA-256; leitura limitada, bloqueio de traversal, links, ausência e alteração de fonte. |
| `application/reading.py` | Liga reconhecimento a extração, verifica snapshot/arquivo/identidade, devolve modelo e alertas de CPF sem decidir cobrança. |
| `validacao_leitores.py` | CLI de validação privada com manifesto, hashes, comparação canônica e relatório sem valores sensíveis. |
| `adapters/private_json.py` | Escrita atômica de JSON 0600, compartilhada com o laboratório para evitar importar cobrança/exportação na Fase 3. |

As incompatibilidades corrigidas são de integração comprovada no código:
assinaturas divergentes entre protocolo e leitores, retorno específico do Cadastro,
ausência de fonte protegida na fronteira comum e falta de vínculo verificável entre
reconhecimento e leitura. As gramáticas dos PDFs **não foram ampliadas por hipótese**.
Os IDs continuam contendo `sintetico_v1`, pois ainda identificam gramáticas obtidas
de documentos recriados; não foram renomeados como formatos reais homologados.

## Contrato e bloqueios

O registro possui três adapters, um por leitor/versão. A mesma instância de adapter
atende vários condomínios, com contexto obtido do catálogo. `formato_id` é distinto
de `leitor_id`: diferentes IDs de catálogo não exigem duplicação de parser. Versão
ou leitor não registrado gera erro explícito, sem importação dinâmica/fallback.

`LerDocumento` exige resultado apto da Fase 2, hash/ID do arquivo correspondentes
e o mesmo hash/revisão do catálogo. Também confere o hash/versão das assinaturas
atuais, evitando reutilizar uma seleção após alteração ou revogação de assinatura.
Preserva todos os bloqueios do reconhecimento, inclusive perfil/regra pendentes,
sem avaliar ou aprovar regras.
O contexto considera a administradora vigente na data de referência e verifica
as associações de condomínio/formato. O adapter confere a assinatura estrutural,
o SHA-256 e a proveniência de unidades, pessoas e todos os componentes financeiros.

Formato desconhecido, ambíguo ou divergente, PDF sem texto/misto/incompleto,
contexto incompatível, soma inconsistente, continuidade incompleta, duplicidade
e fonte alterada continuam bloqueantes. Não há OCR nem LLM para estimar valores.
Os leitores preservam composição, multa/juros e saldo acumulado separadamente;
o contrato não converte saldo da unidade em valor individual de boleto.

Ausência/invalidez de CPF ou existência apenas de CNPJ produz alerta
`CPF_AUSENTE_OU_INVALIDO`, sem impedir a leitura. O dado documental é preservado
no modelo privado; a política de CPF vazio na exportação permanece intacta.
O adapter cadastral não escolhe titular nem aplica a prioridade de Cadastro
aprovada somente para o laboratório anterior. Conflitos reais e datas de cadastro
permanecem para decisão/homologação; o enriquecimento existente bloqueia conflitos
por padrão.

## Área privada preparada

Foi criada a pasta **fora do repositório e de checkouts Git**:

```text
/workspace/validacao-privada-fase3/
  LEIA-ME.txt
  manifesto.exemplo.json
  fontes/       # vazio: aguardando autorização e disponibilização
  gabaritos/    # vazio: aguardando revisão independente
  resultados/   # destinos de execução privados
```

Diretórios foram criados com modo 0700 e arquivos de preparação com 0600. Isso
descreve as permissões Linux locais; controles de acesso, retenção e descarte
operacionais ainda precisam ser definidos. Não criar um repositório Git nessa
pasta nem transferir seus arquivos a tickets/PRs públicos.

O exemplo versionado `config_exemplos/fase3_validacao_privada.exemplo.json` contém
apenas nomes e IDs fictícios, hashes zerados e natureza `sintetica`. Sua cópia local
não é um manifesto operacional nem autorização para acessar dados reais.

## Procedimento futuro, após autorização do usuário

1. Confirmar o caminho e a autorização dos arquivos reais, o responsável pelos
   gabaritos e a política de acesso/retenção. Somente então copiar os documentos
   autorizados para a área privada.
2. Copiar `manifesto.exemplo.json` para `manifesto.local.json`. Preencher IDs
   opacos, caminhos relativos internos, hashes SHA-256 de PDFs/gabaritos, data de
   referência e o identificador da autorização. Para documentos reais autorizados,
   declarar `natureza: real_autorizada`; essa declaração não aprova o formato.
3. Preparar gabaritos `LoteCanonico` independentemente da saída do leitor. Valores
   monetários devem ser strings decimais exatas; incluir sinais, datas ISO,
   apontamentos e origens por página/linha/hash. Cadastro retorna unidades e
   pessoas com `boletos: []`. Fonte e gabarito precisam usar os mesmos IDs de
   contexto e a versão efetiva `leitor_id@1` na proveniência.
4. Executar a comparação em destino novo. A seleção técnica é explicitamente
   declarada no manifesto e validada contra as gramáticas registradas; não é
   reconhecimento operacional aprovado e não executa importação/cobrança.

```bash
.venv/bin/python -m conversor.validacao_leitores \
  --raiz /workspace/validacao-privada-fase3 \
  --manifesto /workspace/validacao-privada-fase3/manifesto.local.json \
  --saida /workspace/validacao-privada-fase3/resultados/execucao_001
```

O comando exige fontes/resultados fora de Git, não sobrescreve saídas, verifica
hashes antes/depois da leitura e compara todos os campos canônicos. O terminal
mostra apenas contagens/estados. O relatório privado contém hashes, versões,
contagens, códigos e caminhos JSON dos campos divergentes, com página/linha quando
disponível; não contém nomes, CPFs, contatos, valores ou números de boletos.
Detalhamento é limitado aos primeiros 100 campos, com contagem total preservada.

Por padrão, o modelo extraído não é gravado. Para investigação local autorizada,
`--salvar-canonicos` grava modelos completos **somente na saída privada**, em 0600.
Eles podem conter dados pessoais e financeiros: não transportar ao repositório.
O relatório e todos os resultados marcam `homologado_producao: false`.

Status: **0** comparação confere para os casos fornecidos; **1** divergência de
campos; **2** fonte/gabarito inválido, incompatibilidade ou bloqueio. Status 0 não
aprova formato, assinatura, perfil, régua ou liberação de produção. Se o layout
real não corresponder à gramática sintética atual, registrar o bloqueio e corrigir
o parser apenas após análise privada da evidência — não editar o PDF para encaixar.

## Checklist para finalizar o aceite da Fase 3

- [ ] Caminho privado e arquivos reais explicitamente autorizados pelo usuário.
- [ ] PDF textual completo Habita/TREE MORUMBI, com cabeçalhos, composição,
  totais por boleto/unidade, unidades/blocos/DEP e apontamentos documentais.
- [ ] PDF textual completo FL/Plaza Mayor Ipiranga, com componentes, descontos,
  saldos cumulativos, torres/unidades, notas e cabeçalhos/rodapés reais.
- [ ] Cadastro Geral FL correspondente, preservando chaves e datas do período,
  contatos opcionais, CPF ausente/CNPJ e casos de titular divergente.
- [ ] Pelo menos duas páginas adjacentes de cada família com um boleto continuado
  e outro boleto distinto; incluir casos sem os marcadores artificiais dos PDFs
  recriados. O caso DEP deve possuir identificação e contagem revisadas.
- [ ] Gabaritos canônicos separados e revisados para Habita, FL e Cadastro,
  conferidos manualmente com quantidade de unidades/boletos, composição assinada,
  valor original, vencimento/competência/emissão e origens de cada componente.
- [ ] Identidades e parâmetros de cabeçalho consistentes com documentos reais;
  códigos de relatório como W002A/W045A não são IDs de condomínio.
- [ ] Planilhas por blocos A–G coerentes, caso utilizadas como conferência. O
  extrator financeiro de XLSX por bloco continua opcional e não foi implementado.
- [ ] Representatividade: versões/períodos distintos e outro condomínio da mesma
  família, para verificar reutilização do leitor e evitar adaptação a um só arquivo.
- [ ] Incompatibilidades observadas corrigidas com regressão sintética específica,
  sem copiar texto, contatos ou valores de clientes para os testes versionados.
- [ ] Somas e continuidade verificadas nas amostras reais, revisão de exceções
  documentada e aceite explícito da Fase 3 antes de avançar à Fase 4.

A semântica da coluna Habita `Emissao` com conteúdo YYYYMM, as assinaturas com
identidade forte, o preenchimento temporal do Cadastro e as diferenças de
layout/fontes dos PDFs originais permanecem pendentes. Nenhuma interpretação
provisória do laboratório passa a ser regra operacional nesta entrega.

## Testes executados

```bash
.venv/bin/python -m pytest -q
# 269 testes regulares aprovados: 222 anteriores + 47 da Fase 3
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
# 60 aprovados: 53 anteriores + 7 do contrato comum com o pacote sintético
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

Total: **329 testes aprovados**, sem pular casos por falta de amostras reais.
Os testes regulares geram documentos sintéticos pequenos. As integrações explícitas
dependem do pacote sintético local e não são teste real disfarçado.

Os novos testes cobrem os três adapters com a mesma assinatura, Cadastro/FL com a
mesma identidade de unidade, continuidade Habita/FL, valores sem duplicar saldo,
CPF como alerta, hash/versão/contexto, proveniência corrompida, reutilização do
mesmo adapter em outro condomínio, vínculo histórico, reconhecimento real da
Fase 2 em fixture artificial e rejeição de reconhecimento obsoleto/bloqueado.
Também verificam a comparação privada, gabarito financeiro divergente sem alterar
extração, travessia/links/arquivos alterados, área Git proibida, JSON inválido,
saída protegida e ausência de importação do motor de cobrança/exportação na CLI.

As regressões antigas continuam verificando as 17 inconsistências do gabarito
de contatos e as quatro datas equivalentes do laboratório; não foram forçadas a
desaparecer nem usadas para aprovar fontes reais.

## Publicar a branch, quando solicitado

Esta tarefa deixa commits locais na branch de Fase 3; não executa push ou merge.
Depois de revisar os commits e confirmar os testes:

```bash
git switch feature/fase-3-leitores
git fetch origin
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
git push -u origin feature/fase-3-leitores
```

Abrir Pull Request de `feature/fase-3-leitores` para `main`, descrevendo o contrato
integrado e o aceite real pendente. Não habilitar merge automático e não anexar
documentos/gabaritos reais. Se a API `gh` continuar bloqueada no ambiente, usar
o formulário de comparação no GitHub após o push:

`https://github.com/Kaique-Diniz/Improvement-repository/compare/main...feature/fase-3-leitores?expand=1`
