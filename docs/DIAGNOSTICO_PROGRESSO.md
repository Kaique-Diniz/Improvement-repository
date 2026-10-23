# Diagnóstico de progresso por fase — 21/10/2026

**Estado posterior autorizado:** Fase 3 encerrada tecnicamente pelo responsável,
com 458 testes, 884 boletos reconciliados e 132 correspondências financeiras.
Ressalvas/bloqueios continuam obrigatórios; sem homologação para produção. A
Fase 4 está em preparação, com [proposta para aprovação](ARQUITETURA_MOTOR_FASE4.md).
O inventário de 275/432 testes abaixo é histórico, anterior ao aceite final.

**Atualização posterior, Fase 3:** a branch `feature/fase-3-leitores`, criada de
`main` em `410f7d6`, integra os leitores ao contrato comum e prepara a validação
privada. São 432 testes no conjunto atualizado; os 275 abaixo são o inventário
histórico anterior. O aceite com amostras reais continua pendente. Consulte
[LEITORES_FASE3.md](LEITORES_FASE3.md) para a implementação atual e os bloqueios.

Fontes revistas: `AGENTS.md`, `01_PLANO_ETAPAS.md` e
`02_ESPECIFICACAO_PRODUTO.md`. Este diagnóstico confronta o plano com o código
existente, os testes e os critérios de aceite; não implementa funcionalidades.

**A última fase declarada concluída continua sendo a Fase 2.** A Fase 1 possui
a fundação implementada, e a Fase 2 possui o reconhecimento implementado e
testado com sintéticos. O laboratório adicional exercita partes das Fases 3,
4 e 5, mas não conclui essas fases nem homologa leitores para produção.

Estados: **implementada** significa que a funcionalidade descrita existe e
possui evidência de teste no escopo indicado; **parcial** significa que apenas
parte do requisito foi atendida; **pendente** significa que falta implementação,
validação externa ou decisão requerida. Implementação não equivale a aprovação
para uso com dados reais ou no importador de destino.

## Matriz de funcionalidades

| Fase | Funcionalidade | Estado | Evidência atual | Pendência para aceite operacional |
|---|---|---|---|---|
| 0 | Dossiê, plano, ambiente local e exemplos | Implementada | Documentos normativos, README, dependências fixadas e sintéticos | Manter revisão incremental. |
| 0 | Acesso autorizado às fontes e política de dados | Parcial | Arquivos locais ignorados, documentos originais não usados | Amostras reais em ambiente autorizado, retenção/ACL e verificação de privacidade do repositório; API de metadados indisponível nesta tarefa. |
| 1 | Domínio, entidades separadas e modelo canônico | Implementada | `domain/{base,canonical,catalog,template}.py`; IDs, vínculos, Decimal e origens | Evoluções futuras devem manter os contratos. |
| 1 | Persistência JSON, schema, integridade e gravação atômica | Implementada | `adapters/json_repository.py`; snapshots, lock, revisão, falhas e concorrência testados | PostgreSQL pertence à Fase 8. |
| 1 | CLI de configuração e interfaces de repositório/histórico | Implementada | `application/{configuration,ports}.py`, `cli.py`, schemas | Backend alternativo é contrato/test double, não PostgreSQL pronto. |
| 2 | Sondagem de PDF com texto/rasterizado/misto, XLSX e CSV | Implementada | `adapters/document_probe.py`; limites, formatos inválidos e evidência parcial bloqueados | Sem OCR; sondar planilha não significa extrair boletos dela. |
| 2 | Assinaturas, identidades, conhecido/desconhecido/ambíguo | Implementada | `application/recognition.py`, `domain/recognition.py`, repositório de assinaturas | Compatibilidade de assinaturas/identidades reais ainda precisa ser verificada. |
| 2 | Catálogos e assinaturas operacionais Habita/FL homologados | Pendente | Perfis do laboratório permanecem rascunhos; reconhecimento operacional bloqueia | Evidência documental e aprovação representativa, sem inferir identidade pelo layout. |
| 3 | Leitores separados Habita, FL e Cadastro Geral | Parcial | `readers/{habita,fl,cadastro,text_support}.py`; gramáticas dos PDFs recriados do zero | Validar PDFs reais autorizados e corrigir diferenças estruturais comprovadas. |
| 3 | Continuidade, deduplicação e reconciliação financeira | Parcial | Boletos sintéticos entre páginas, descontos, totais e saldos testados | Critério do plano exige verificação de quebras/somas em amostras reais. |
| 3 | Enriquecimento e conflitos de titular | Parcial | `application/enrichment.py`; chave completa e alerta auditado | Prioridade do Cadastro vale só no laboratório; datas e múltiplos titulares exigem decisão operacional. |
| 3 | Contrato comum de leitores e integração operacional | Parcial | `Leitor` implementado pelos três adapters e ligado a `LerDocumento`; validação privada preparada | Integração contratual pronta; aceite das gramáticas e identidades com fontes reais ainda pendente. |
| 3 | Leitura financeira de XLSX por blocos A–G | Pendente | XLSX do pacote é conferência de resumo em `laboratorio/comparison.py` | Não existe extrator financeiro geral das planilhas por bloco; item opcional do plano. |
| 4 | Prazo, exclusão por unidade e apontamentos | Parcial | `rules/laboratory.py`; corte estrito, R$ 0,01 e A/AJ/J com namespace | Motor geral declarativo com prioridade/operadores e execução de regras aprovadas da régua ainda não entregue. |
| 4 | Judicial, particularidades e versões operacionais | Pendente | Catálogo guarda versões/vigências; laboratório não interpreta a régua real | Homologar semântica judicial e exceções; não transformar 60 dias em exclusão automática. |
| 5 | Contrato universal de 30 colunas, CPF e linha cadastral | Implementada | `export/contract.py`, `domain/template.py`; CPF/CNPJ válido como texto na coluna CPF; documento vazio/inválido com alerta; conflito válido exige revisão humana, Y:AD vazias no cadastro | Esse contrato pronto não conclui o aceite da Fase 5. |
| 5 | Escrita XLSX e auditoria da conversão | Parcial | `export/{build_lines,xlsx}.py`, `laboratorio/`; datas/valores nativos e saída determinística | Perfis didáticos, auditoria/pipeline de laboratório; falta integração operacional e política de dados. |
| 5 | Aceite no importador de destino | Pendente | Nenhuma importação controlada executada | Validar tipos, CPF/CNPJ como texto na coluna CPF, vazio, duplicados, códigos e espaço final da coluna AA. |
| 6 | Upload, dashboard, execução e download no workflow final | Pendente | CLI técnica disponível; `index.html` é apenas uma página Hello world | Sem interface do conversor, API de produto ou workflow ponta a ponta. |
| 7 | Ampliação e monitoramento de formatos | Parcial | Catálogos e reconhecimento reutilizam formatos entre identidades em testes sintéticos | Não há catálogo operacional amplo, gestão assistida ou monitoramento de qualidade implantado. |
| 8 | PostgreSQL, migrações, multi-condomínio e operação | Pendente | Portas de persistência e histórico preservam caminho de migração | Sem adapter SQL, migrações, lotes operacionais, backup/observabilidade/retenção de produção. |

A aprovação da conclusão do **laboratório sintético** é preservada. Permanecem
17 inconsistências do gabarito e quatro diferenças de datas esclarecidas quanto
ao tipo. Isso não constitui evidência para aprovar as Fases 3–5 em produção.

## Confirmação histórica dos 275 testes, antes da integração da Fase 3

Execução única nesta revisão: **275 aprovados, zero falhas e zero pulados**.
Os testes parametrizados contam como casos individuais. A divisão é:

| Grupo | Casos |
|---|---:|
| Fundação, contratos, JSON e CLI | 96 |
| Reconhecimento e comparador de homologação | 80 |
| Leitores/regras/exportação de laboratório, sem depender do anexo | 46 |
| Integração com o pacote sintético local | 25 |
| Revisão individual de diferenças e regressões do diagnóstico | 28 |
| **Total** | **275** |

Comandos para reproduzir sem instrumentação:

```bash
.venv/bin/python -m pytest -q
# 222 aprovados
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py
# 53 aprovados
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

As 53 integrações exigem o pacote local autorizado, que não acompanha o Git.
Uma cópia nova do repositório executa os 222 testes regulares; as suítes explícitas
falham com mensagem de pacote ausente se forem invocadas sem ele, não o pulam.

## Módulos exatamente exercitados

O inventário abaixo usa chamadas Python observadas por `sys.setprofile` durante
setup, execução e teardown, agrupadas por arquivo de teste. O registro local é
`dados/diagnostico_progresso/testes_e_modulos.json`. Não é porcentagem de cobertura
de linhas ou branches, nem prova de que todos os ramos dos módulos foram testados.
Subprocessos e threads independentes não foram instrumentados. Dependências
chamadas por fixtures também constam na tabela; presença nela não significa teste
direto de cada função da dependência. O prefixo dos módulos é `conversor.`.

| Arquivo de teste | Casos | Módulos com funções chamadas |
|---|---:|---|
| `tests/homologacao/pacote_suite.py` | 25 | `adapters.document_probe`, `application.enrichment`, `application.recognition`, `domain.base`, `domain.canonical`, `domain.catalog`, `domain.recognition`, `domain.template`, `export.build_lines`, `export.contract`, `export.xlsx`, `laboratorio.comparison`, `laboratorio.config`, `laboratorio.run`, `readers.cadastro`, `readers.fl`, `readers.habita`, `readers.text_support`, `rules.laboratory` |
| `tests/homologacao/revisao_suite.py` | 28 | `adapters.document_probe`, `application.enrichment`, `application.recognition`, `domain.base`, `domain.canonical`, `domain.catalog`, `domain.recognition`, `domain.template`, `export.build_lines`, `export.contract`, `export.xlsx`, `laboratorio.comparison`, `laboratorio.config`, `laboratorio.review`, `laboratorio.run`, `readers.cadastro`, `readers.fl`, `readers.habita`, `readers.text_support`, `rules.laboratory` |
| `tests/recognition/test_contracts_and_cli.py` | 13 | `adapters.document_probe`, `adapters.json_repository`, `adapters.signature_repository`, `application.configuration`, `application.recognition`, `cli`, `domain.base`, `domain.catalog`, `domain.recognition`, `domain.template`, `recognition_schemas` |
| `tests/recognition/test_homologation_harness.py` | 8 | `adapters.document_probe`, `adapters.json_repository`, `adapters.signature_repository`, `application.recognition`, `domain.base`, `domain.canonical`, `domain.catalog`, `domain.recognition`, `domain.template` |
| `tests/recognition/test_probe.py` | 29 | `adapters.document_probe`, `adapters.json_repository`, `adapters.signature_repository`, `application.recognition`, `domain.base`, `domain.catalog`, `domain.recognition`, `domain.template` |
| `tests/recognition/test_service.py` | 30 | `adapters.document_probe`, `adapters.json_repository`, `adapters.signature_repository`, `application.recognition`, `domain.base`, `domain.catalog`, `domain.recognition`, `domain.template` |
| `tests/test_canonical.py` | 28 | `domain.base`, `domain.canonical` |
| `tests/test_catalog.py` | 25 | `domain.base`, `domain.catalog`, `domain.template`, `readers.contracts` |
| `tests/test_cli_and_schemas.py` | 4 | `adapters.json_repository`, `application.configuration`, `cli`, `domain.base`, `domain.catalog`, `domain.template`, `schemas` |
| `tests/test_export.py` | 16 | `domain.base`, `domain.canonical`, `domain.template`, `export.contract` |
| `tests/test_laboratory_readers.py` | 24 | `adapters.document_probe`, `application.enrichment`, `domain.base`, `domain.canonical`, `readers.cadastro`, `readers.fl`, `readers.habita`, `readers.text_support` |
| `tests/test_laboratory_rules_export.py` | 22 | `domain.base`, `domain.canonical`, `domain.template`, `export.build_lines`, `export.contract`, `export.xlsx`, `readers.text_support`, `rules.laboratory` |
| `tests/test_repository.py` | 23 | `adapters.json_repository`, `application.configuration`, `domain.base`, `domain.catalog`, `domain.template`, `readers.contracts` |

Os módulos `application.ports` e `application.recognition_ports` são contratos
declarativos usados pelas implementações e fixtures; não apresentaram chamadas
Python próprias nessa medição. Arquivos `__init__.py` não representam
funcionalidades testáveis separadas. `laboratorio.__main__.main` e
`laboratorio.review.main` não têm teste automatizado específico do parser/entrypoint
entre estes 275 casos; as funções de execução e revisão são cobertas pela integração.
`tests/homologacao/runner.py` também é exercitado pelos oito testes de harness,
embora não pertença ao pacote `conversor`. Os dois comandos `--check` de schemas
são validações adicionais e não aumentam a contagem de testes.

## Próxima fase e publicação

**A próxima fase pendente é a Fase 3.** A sequência indicada pelo usuário permanece:
validar inicialmente Habita/FL em ambiente autorizado com fontes reais, corrigir
problemas estruturais comprovados, concluir o aceite dos leitores e então seguir
para a Fase 4. Cada fase requer testes/regressão e revisão; homologação completa
precede qualquer liberação de produção. Nenhuma dessas ações foi iniciada aqui.

A branch `review/homologacao-sintetica` reúne o trabalho anterior das Fases 1 e 2,
o laboratório e sua revisão; o diff contra main inclui esses trabalhos anteriores.
A alteração da tarefa deste inventário foi apenas documental; a integração
posterior está descrita no relatório da Fase 3. Os commits anteriores não foram
reescritos. A situação efetiva de publicação é registrada em
[ENVIO_GITHUB.md](ENVIO_GITHUB.md). Não existe autorização para merge automático.

Atualização documental de 21/10/2026: aceitação de CPF/CNPJ na coluna literal
CPF do CRM easyCollector confirmada pelo responsável pelo processo. Texto,
zeros, conflitos e auditoria têm testes locais; demais comportamentos de
importação exigem homologação integral. Ver [contrato documental](DOCUMENTOS_CPF_CNPJ.md).

Correções estruturais da Fase 3: três PDFs reais processados, inventário
financeiro confrontado sem divergências, bloqueios cadastrais e subtotal
inconsistente preservados. Os 432 testes não concluem o aceite/homologação.
Ver [atualização dos leitores reais](CORRECOES_LEITORES_REAIS_FASE3.md).
