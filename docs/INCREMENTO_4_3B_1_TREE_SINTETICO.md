# Incremento 4.3B.1 — comportamento TREE exclusivamente sintético

## Escopo e resultado

Implementadas as cinco condições de negócio autorizadas usando o motor
determinístico 4.2 existente. Nenhum segundo motor foi criado. A projeção universal
A/B produz decisões estruturadas, sem materializar XLSX, executar cobrança ou
importar no easyCollector. O sistema permanece **não homologado para produção**.

A base aceita de 943 testes continua aprovada. Foram adicionados 84 casos:
**967 regulares + 60 explícitos = 1.027 aprovados**. Os sete geradores de schemas
passam em `--check`. Nesta tarefa não foram lidos documentos privados nem
executadas regras sobre os 769 boletos reais; a cobertura real anterior é
evidência histórica, não um novo resultado desta implementação.

## Arquivos e contratos

| Arquivo | Responsabilidade |
|---|---|
| `src/conversor/domain/synthetic_processing.py` | Solicitação sintética com modo A/B obrigatório; candidatos exclusivamente cadastrais; retenções; projeção auditável |
| `src/conversor/application/synthetic_processing.py` | Revalida contratos, aplica a política de revisão de identidade deste incremento, chama `SimularCobranca` e projeta A/B |
| `src/conversor/synthetic_processing_schemas.py` | Geração e conferência dos dois novos schemas, em namespace próprio |
| `schemas/processamento-sintetico/1.0/solicitacao.schema.json` | Contrato de entrada: ambiente somente sintético, modo obrigatório, referência e identidade do plano |
| `schemas/processamento-sintetico/1.0/projecao.schema.json` | Contrato de saída: relatório do motor, hash, decisões de dívida/cadastro e flags operacionais sempre falsas |
| `examples/fase4/tree_43b1.sintetico.json` | Plano demonstrativo, condomínio e fontes inventados, sem aprovação embutida |
| `tests/synthetic_processing/conftest.py` | Repositório/autoridade e dados inteiramente sintéticos em `tmp_path` |
| `tests/synthetic_processing/test_tree_conditions.py` | 50 casos de condições, datas, proveniência, estados e bloqueios |
| `tests/synthetic_processing/test_projection_and_identity.py` | 34 casos de A/B, identidade, integração com PDF inventado e integridade da projeção |

README, plano de etapas, especificação, modelo de dados, pendências, prontidão
documental e índice dos exemplos receberam referências a esta entrega.
Não foram alterados leitores, contratos canônicos, predicados ou algoritmo do
motor 4.2, repositório de aprovação, schemas históricos, template ou exportadores.
Arquivos de cobertura/mapeamento TREE e fichas que já estavam no checkout foram
preservados; não são todos criações deste incremento.

`SolicitacaoProcessamentoSintetico` estende o contrato de simulação existente,
sem migrá-lo: exige `ambiente="sintetico"`, `modo_cadastro="A"|"B"` e a
`data_ref` herdada obrigatória. `ProjecaoProcessamentoSintetico` contém o relatório
integral, seu hash, versão da projeção, modo e IDs dos boletos elegíveis.
`autoriza_cobranca` e `permite_exportacao_operacional` admitem somente `false`.
Modelos Python também verificam correspondência entre dívida, cadastro e decisões
do relatório; JSON Schema sozinho não substitui essas verificações relacionais.

## Cinco regras e seis cláusulas técnicas

| Regra de negócio | Condição no plano sintético | Escopo e ação |
|---|---|---|
| `tree_centavo` | `valor_original eq "0.01"` → `Boleto.composicao.total_original` | Excluir somente a cota e seus componentes, qualquer vencimento |
| `tree_apontamento_a` | `apontamento`, código exatamente `A`, namespace validado do contexto sintético | Excluir somente a cota e seus componentes |
| `tree_apontamento_aj` | Mesmo campo e namespace, código exatamente `AJ` | Excluir somente a cota e seus componentes |
| `tree_apontamento_j` | Mesmo campo e namespace, código exatamente `J` | Excluir somente a cota e seus componentes |
| `tree_prazo_30` | Dias corridos `> 30` **e nenhuma das quatro exclusões** | Elegível na simulação, sujeito aos controles administrativos, evidências e bloqueios |

O namespace do exemplo é `fmt_habita_sintetico_mapeamento`, associado ao contexto
de testes do leitor existente; não se transfere cobertura entre namespaces.
O original integral é comparado com `Decimal("0.01")` pelo predicado existente.
Um componente isolado de um centavo em cota maior não aciona a exclusão.
Multa, juros, atualização e total atualizado não substituem o original.
Nenhum valor é recalculado ou modificado pelo novo fluxo.

A inclusão contém explicitamente `prazo > 30 AND NOT(centavo OR A OR AJ OR J)`.
Assim, a exclusão prevalece sem alterar o algoritmo genérico de prioridades e
sem escolher prioridades numéricas reais. O teste que aumenta a prioridade
sintética da inclusão demonstra que a guarda continua impedindo essa inclusão.
Uma cota excluída não propaga exclusão às demais da unidade.

A sexta cláusula, `tree_prazo_30_nao_atingido`, é o ramo complementar da quinta
regra: `dias_atraso <= 30`, ação `excluir`, com a mesma `fonte_id` de
`tree_prazo_30`. Documenta a inelegibilidade **na data de referência**, inclusive
cota ainda não vencida. Não cria sexta decisão empresarial nem exclusão
permanente. É necessária para distinguir inelegibilidade comprovada de revisão:
no motor genérico, nenhuma regra aplicável resulta em revisão, que não deve virar
cadastro antecipado por aproximação.

Todas as prioridades `0`, datas de vigência e referências de fonte do exemplo são
**inventadas exclusivamente para a fixture sintética**. Não são proposta de
prioridade ou vigência de plano real. A proposta documental real permanece com
campos pendentes; não recebe esses valores nem eventos de aprovação.

## Evidência, identidade e segurança

- Campo vazio com cobertura comprovada permite concluir ausência dos códigos.
  Sem cobertura, o resultado é indeterminado/revisão; não se presume ausência.
- Códigos usam igualdade exata, sem procurar letras em descrições/legendas.
  O teste integrado passa um PDF inventado pelo leitor operacional existente,
  confere o campo e sua continuidade e só então fornece cobertura sintética.
  Leitura inconclusiva permanece crítica, sem dívida/cadastro alternativo.
- Cada decisão conserva regras avaliadas, condições, motivos, fonte, origens,
  versão e hash do plano. Excluir não apaga boleto, componentes ou evidências.
- Conforme esclarecimento explícito do responsável, **CPF/CNPJ inválido exige
  revisão neste incremento**. O novo fluxo acrescenta ocorrência crítica da
  unidade, preserva o alerta histórico e o documento bruto, sem alterar a entrada.
  Documento ausente permanece alerta não bloqueante. CPF/CNPJ válidos preservam
  tipo e zeros. Conflitos válidos ou titularidade ambígua continuam bloqueados.
- Essa restrição de invalidade pertence ao novo fluxo sintético; não reescreve
  a política geral histórica de célula vazia + alerta nem os leitores/exportadores.
  Nome/titular obrigatório ausente ou ambíguo também retém a unidade para revisão.
- Ocorrências adicionais têm identidade determinística por processamento,
  unidade e motivo. Colisão com conteúdo anterior diferente é rejeitada; nenhum
  registro histórico é sobrescrito.
- A solicitação rejeita ambiente privado antes de consultar o repositório.
  O motor existente exige acervo/plano de natureza sintética, aprovação válida,
  versão/hash correspondentes, assinatura, estado administrativo e vigência.
  Campo `ativo` isolado continua insuficiente. Estados inadequados, revogação e
  hash divergente são recusados.
- Os eventos de criar/submeter/aprovar/ativar usados nos testes existem apenas
  para planos inventados no repositório temporário da fixture. O novo serviço
  não cria esses eventos, atestos, assinaturas ou mudanças de estado; a igualdade
  do acervo antes/depois é testada. Não houve aprovação/ativação de plano real.
- Ressalvas e ocorrências críticas de lote, unidade e cadastro prevalecem sobre
  regras financeiras: Habita/VG, titularidade FL e documentos conflitantes
  permanecem retidos. Nenhuma liberação operacional foi realizada.

## Modos universais A/B e reprodução

O modo A retorna somente IDs de dívida elegível na simulação. No modo B, cada
unidade com cota explicitamente excluída pode gerar **um único** candidato
exclusivamente cadastral, coexistindo com outras cotas elegíveis da unidade.
Unidades só do Cadastro Geral, sem boletos na entrada, não entram nessa seleção.

O candidato usa `divida=None`: não produz os seis campos financeiros Y:AD nem
qualquer linha XLSX. A futura materialização desses campos vazios permanece na
Fase 5. A estrutura não permite confundir candidato cadastral com dívida.

Conservadoramente, qualquer boleto bloqueado ou em revisão na unidade retém
o candidato cadastral e gera justificativa em `retencoes_cadastrais`; uma dúvida
não vira prova de inelegibilidade. Isso não propaga exclusão financeira a cotas
distintas que tenham decisão elegível sem bloqueio de unidade/lote.

Mesma entrada, plano, evidências, versão, modo e data produzem os mesmos objetos
e hashes. `hash_relatorio_motor` referencia o relatório original, e
`hash_auditoria` da projeção inclui modo A/B e versão `4.3B.1`. Datas distintas
podem produzir seleção distinta e ficam registradas; não se usa a data atual.
O modo obrigatório faz parte do contrato de auditoria/reprodução. Este incremento
não grava histórico operacional nem pacote privado assinado; a integração futura
com a persistência privada deverá registrar a projeção completa e seu modo,
preservando os contratos históricos e o manifesto correspondente.

## Verificação reproduzível

Na raiz do checkout, com o ambiente de desenvolvimento já instalado:

```bash
.venv/bin/python -m pytest -q tests/synthetic_processing
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m conversor.billing_schemas --check
.venv/bin/python -m conversor.evaluation_schemas --check
.venv/bin/python -m conversor.private_simulation_schemas --check
.venv/bin/python -m conversor.audit_schemas --check
.venv/bin/python -m conversor.synthetic_processing_schemas --check
```

Resultados: 84 novos casos em 2,14 s; 967 regulares em 15,65 s; 60 explícitos em
1,13 s. Os 84 já estão nos 967; o total sem dupla contagem é **1.027**.
Os cenários incluem 30/31 dias, centavo com/sem encargos e componente isolado,
A/AJ/J, gatilhos combinados, múltiplas cotas, vazio/inconclusivo, namespace,
legendas, referência ausente/inválida, bloqueios, CPF/CNPJ e modos A/B.

Os testes explícitos usam o laboratório sintético existente, não os PDFs reais.
A tarefa não acessou arquivos privados nem executou simulações financeiras reais.
Novos exemplos/fontes de teste são inventados; nenhum PDF, XLSX, dado pessoal,
credencial ou relatório financeiro privado foi adicionado à entrega.

## Pendências para autorização específica do 4.3B.2

1. Atestos humanos de completude e validade das fontes, independentes da
   conferência automática; vincular a régua aplicável e sua versão/hash.
2. Aprovação formal do conteúdo de cada plano real e sua versão/hash; decidir
   prioridades e vigências reais sem copiar valores das fixtures.
3. Confirmar a integração do namespace real e dos comprovantes de cobertura,
   incluindo ausência comprovada e tratamento de inconclusivos no pacote privado.
4. Resolver por decisão humana fundamentada os bloqueios de cadastro/documento
   aplicáveis; Habita/VG e demais críticos continuam preservados enquanto pendentes.
5. Autorizar separadamente a integração do novo contexto A/B com persistência
   privada assinada e respectivos manifestos/reprodução; não alterar pacotes
   históricos 1.0/1.1 para acomodar a projeção.
6. Definir em cada futuro processamento data de referência e modo A/B explícitos,
   e somente então autorizar o escopo de simulação privada correspondente.

Recomendação: incremento 4.3B.1 tecnicamente pronto para revisão. Não autoriza
automaticamente o 4.3B.2, ativação real, liberação de bloqueios ou Fase 5.
Branch `feature/fase-4-motor-cobranca`; alterações locais, sem novo commit,
push ou merge nesta tarefa. Homologação de produção continua pendente.
