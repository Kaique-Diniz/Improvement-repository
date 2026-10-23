# Cobertura exaustiva dos apontamentos e fichas TREE — preparação do 4.3B

O responsável aceitou o mapeamento preparatório com **915 testes** e autorizou
esta conferência técnica/fichas, sem aprovação, assinatura ou ativação de planos
reais. Fonte TREE inspecionada exclusivamente na área privada autorizada.
**Não houve simulação financeira real, exportação de dívida ou início da Fase 5.**
Sistema não homologado para produção.

## Resultado dos 769 boletos

| Estado do campo | Boletos únicos | Significado |
|---|---:|---|
| Vazio validado tecnicamente | **628** | Linha e limites do campo comprovados, intervalo sem conteúdo textual, concordante com canônico e continuidades |
| Preenchido validado tecnicamente | **141** | Código exato A/AJ/J no campo próprio, ligado ao boleto, namespace e origem corretos |
| Inconclusivo | **0** | Nenhum caso na conferência final deste arquivo; se surgir, permanece em revisão e bloqueado para dívida |
| Total | **769** | Inventário completo, sem tratar boleto ausente como campo vazio |

Entre os preenchidos: **A = 15, AJ = 9 e J = 117**. Foram conferidos **802
cabeçalhos**, incluindo **33 repetições por continuidade em 33 boletos**, sem
contradição de código. Os 447 códigos isolados fora da posição financeira,
inventariados na etapa anterior, não viraram apontamentos dos boletos.
Os cinco anexos autorizados tiveram seus hashes reconferidos. Não foi executado
qualquer critério de inclusão/exclusão de dívida; estas são contagens de campos.

## Como se comprova presença, vazio e inconclusão

O módulo aditivo `src/conversor/readers/habita_point_coverage.py` confere o PDF e
as origens do canônico, sem modificar o leitor ou o motor. A fonte precisa
corresponder ao arquivo/hash/versão declarados e ao condomínio/administradora.
Cabeçalho adicional fora do inventário é rejeitado; cabeçalho esperado não
localizado gera inconclusão, nunca ausência presumida.

A conferência usa os rótulos Boleto, Vencimento e Emissão da própria página,
confirmando também os rótulos financeiros. Identifica a linha por número/data;
a data pode estar recuada dentro da coluna, não precisa começar no mesmo x do
rótulo. O campo de apontamento fica entre o número e a coluna de vencimento.
Não se usa x=69,02 como constante universal: essa foi a posição observada neste
PDF, cuja estrutura foi validada anteriormente.

| Situação observada | Resultado técnico |
|---|---|
| Intervalo comprovado e vazio, coerente com todos os cabeçalhos/origens do boleto | `vazio_validado` |
| Um código exato A/AJ/J no intervalo, coerente com canônico/namespace e continuidades | `preenchido_validado` |
| Falta/duplicidade de âncoras ou linha, conteúdo desconhecido/parcial, códigos múltiplos, divergência texto/geometria/canônico/namespace | `inconclusivo` |
| Código em legenda, observação ou descrição fora do campo | Não é apontamento. Se o próprio campo não puder ser comprovado, continua inconclusivo |
| Fonte/hash/contexto incompatível ou inventário com cabeçalhos adicionais | Erro explícito; não se produz conferência completa/autorizativa |

Cada registro guarda boleto/unidade, namespace, estado, motivo e origens de
**todos** os cabeçalhos, incluindo repetição na página seguinte. AJ não casa
parcialmente com A ou J. Não há escolha automática de evidência conflitante.

Inconclusão gera `APONTAMENTO_LEITURA_INCONCLUSIVA`, ocorrência **crítica por
boleto**, com origem, mediante `ocorrencias_revisao`. O contrato existente impede
resultado de inclusão com essa ocorrência. A conferência sempre declara
`autoriza_exportacao_divida=false`, inclusive se todos os campos estiverem claros.
Não remove bloqueios anteriores nem altera boletos, pessoas ou valores.

A saída é **evidência técnica candidata**, não `CoberturaApontamentos` aprovada,
atesto humano ou pacote assinado. O fluxo futuro deverá vincular essa evidência
à revisão humana e transportar também todas as ocorrências críticas para o
pacote completo. Essa integração operacional não foi iniciada aqui. Sem cobertura
aceita no fluxo próprio, o avaliador continua tratando ausência como indeterminada.

## Evidência privada e preservação

Resultado final e manifesto em:
`/workspace/validacao-privada-fase3/resultados/cobertura_apontamentos_tree_009/revisao_002/`.

- `conferencia_por_boleto_privada.json`: os 769 estados, namespaces e origens;
  não contém decisão de elegibilidade nem alteração do canônico.
- `ocorrencias_revisao_privadas.json`: vazio nesta conferência final; não substitui
  os catálogos de bloqueios anteriores, que continuam ativos.
- `resumo_sem_dados_pessoais.json`: contagens e controles não autorizativos.
- `manifesto_preservacao_privado.json`: fontes/hashes, versões e prova de que
  **132 arquivos privados anteriores permaneceram inalterados**.
- `conferir_cobertura_privada.py` e cópia privada do código conferidor: reprodução
  da inspeção; não chamam motor, repositório de planos, assinatura ou exportador.

Diretórios 0700 e arquivos 0600; fonte original e dossiês fora do Git. A primeira
inspeção de desenvolvimento foi conservadora e classificou as linhas como
inconclusivas por exigir alinhamento idêntico entre data e rótulo. Seus registros
foram preservados no diretório superior; **não são a conclusão final**. A revisão
002 usa o intervalo documental Vencimento–Emissão, tem código identificado por
hash no manifesto e concluiu presença/vazio para todos os boletos. Não houve
relaxamento de condição financeira ou descarte de evidência para obter o resultado.

O bloqueio de lote **Habita/VG** permanece ativo; nenhum atesto ou ficha permissiva
o libera. Os bloqueios cadastrais/documentais FL permanecem ativos, com seus
escopos anteriores. Foram preservados os contratos históricos 1.0/1.1, IDs,
recibos, arquivos-fonte e dossiês anteriores.

## Cinco fichas individuais

| Ficha pronta para decisão | Condição / operador | Escopo / ação | Prioridade e vigência |
|---|---|---|---|
| [tree_centavo](fichas_tree_4_3B/tree_centavo.md) | Original integral `composicao.total_original eq 0.01`, não componente isolado | Excluir cota e componentes, independente do vencimento | Pendentes, sem números/datas presumidos |
| [tree_apontamento_a](fichas_tree_4_3B/tree_apontamento_a.md) | Código A exato + namespace comprovado | Excluir cota e componentes, independente do vencimento | Pendentes |
| [tree_apontamento_aj](fichas_tree_4_3B/tree_apontamento_aj.md) | Código AJ exato + namespace comprovado | Excluir cota e componentes, independente do vencimento | Pendentes |
| [tree_apontamento_j](fichas_tree_4_3B/tree_apontamento_j.md) | Código J exato + namespace comprovado | Excluir cota e componentes, independente do vencimento | Pendentes |
| [tree_prazo_30](fichas_tree_4_3B/tree_prazo_30.md) | `data_ref - vencimento > 30` dias corridos | Incluir apenas cota sem exclusões/impedimentos; dia 31 satisfaz somente o prazo | Pendentes |

Uma exclusão já basta: **centavo OU A OU AJ OU J**, sem afetar automaticamente
outras cotas da unidade. Essas exclusões sempre prevalecem sobre satisfação do
prazo. Não foram criados planos com prioridades arbitrárias. Cada ficha registra
condição, campo, ação, precedência, referência pendente, vigência pendente,
fonte/versão da régua pendentes, evidência e estado de aprovação pendente.
Completar/concordar com uma ficha não aprova automaticamente uma versão/hash
inexistente de plano nem emite evento administrativo.

## Atestos, modo A/B e decisão de avanço

O [resumo de atestos e decisões](RESUMO_ATESTOS_DECISOES_4_3B.md) distingue as cinco
fontes disponíveis, integridade técnica, conferências humanas e bloqueios.
A identificação do extrato/versionamento aplicável da régua ainda é necessária.
O responsável pode acumular Administrador, Revisor e Operador; cada atesto,
aprovação e decisão tem registro independente, mesmo com a mesma identidade.

Modos universais preservados, sem default escolhido:

- **A:** somente dívidas elegíveis.
- **B:** dívidas elegíveis e até uma linha cadastral adicional por unidade com
  cotas comprovadamente não elegíveis, inclusive coexistindo com dívida elegível.
  **Y:AD permanecem vazias** na linha exclusivamente cadastral. Não incluir todo
  Cadastro Geral nem contornar críticos ou usar inconclusão como cadastro alternativo.

**Recomendação:** reconhecimento dos apontamentos deste PDF tecnicamente pronto
para revisão humana e para delimitar uma autorização posterior de implementação
4.3B. Não está pronto para ativação/execução real: faltam atestos por fonte/conjunto,
fonte/versão da régua, prioridades/vigências, conteúdo final/versão/hash e aprovação
válida do plano. Data de referência e modo A/B devem ser escolhidos por execução.
Habita/VG e bloqueios FL continuam impedindo operações nos escopos afetados.

A validação refere-se à camada textual do PDF identificado por hash. Não prova
sozinha que toda informação externa existe ou foi entregue, não substitui exame
humano e não homologa outros layouts/PDFs rasterizados. Nenhum OCR foi usado
como fonte financeira. Não se declarou homologação de regras ou de produção.

## Testes, schemas e situação do trabalho

```bash
.venv/bin/python -m pytest -q tests/phase3/test_habita_point_coverage.py
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

**28 novos testes aprovados; regressão completa de 883 regulares + 60 explícitos
= 943 aprovados**, sem falhas ou skips. Os 915 anteriores foram preservados.
Os novos testes limitam-se à presença/ausência/inconclusão do campo, âncoras,
recuo da data dentro da coluna, códigos desconhecidos/parciais/múltiplos, legendas,
continuidade coerente/divergente, omissão de boleto/código, namespace/hash e
ocorrência crítica que impede inclusão. Usam PDFs inteiramente inventados.

Os seis comandos de schemas existentes (`schemas`, `recognition_schemas`,
`billing_schemas`, `evaluation_schemas`, `private_simulation_schemas`,
`audit_schemas`, todos com `--check`) passaram. Os dois modelos diagnósticos novos
também geram JSON Schema; nenhum contrato/schema histórico foi alterado ou migrado.
Diagnósticos privados estão vinculados à cópia/hash do código conferidor e fontes.

Conferência complementar de privacidade: **226 arquivos versionáveis**, sem
cópias dos anexos reais ou correspondências identificáveis verificadas; não é
prova universal de ausência de dados sensíveis. O resultado atual ficou no dossiê
009. Como a ferramenta legada regravou seu próprio diagnóstico anterior, os
bytes históricos foram restaurados somente após comprovação por hash; tanto o
resultado atual como a evidência da restauração foram preservados separadamente.
Ao final, todos os 132 hashes anteriores conferiram. Fontes, canônicos, pacotes,
IDs, recibos e decisões permaneceram inalterados.

Adicionados um conferidor preparatório, sua suíte, cinco fichas e dois relatórios;
atualizados índices, matriz e proposta documental 2.3. Leitores operacionais,
motor financeiro, exportador e valores não foram alterados. Branch
`feature/fase-4-motor-cobranca` mantida; sem novo commit, push ou merge nesta tarefa.
