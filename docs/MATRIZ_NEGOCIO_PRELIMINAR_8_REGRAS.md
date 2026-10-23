# Matriz revisada de decisões — preparação do 4.3B

**Prioridades confirmadas como decisões de negócio, sem aprovação de plano:**
TREE: `tree_centavo`, `tree_apontamento_a`, `tree_apontamento_aj` e
`tree_apontamento_j` = **1**; `tree_prazo_30` = **0**.
PLAZA: `plaza_prazo_30` = **0**. Os números não precisam de nova confirmação
de negócio. Exclusões afetam só a cota/componentes, com todas as justificativas
simultâneas preservadas. Indeterminações relevantes exigem revisão e críticos
prevalecem sobre prioridades financeiras. A/B é independente. Vigência de negócio
mantida: início inclusivo **2026-09-10**, fim aberto até substituição/revogação
expressa. Continuam pendentes a validação da aplicabilidade anterior à fonte de
rótulo 20/10/2026, a divergência TREE unidade/cota, atestos e aprovação formal do
conteúdo final dos planos. Não há assinatura, ativação ou autorização de simulação.

**Decisão de negócio confirmada de vigência — ainda sem aprovação formal:**
para TREE MORUMBI e PLAZA MAYOR IPIRANGA, `vigente_de: 2026-09-10` (inclusivo),
`vigente_ate: null`, com fim aberto expressamente definido até substituição ou
revogação expressa. A referência do processamento continua independente e não
foi escolhida. **Ressalva obrigatória:** 10/09/2026 antecede o rótulo documental
20/10/2026; o fundamento dessa aplicabilidade anterior deve ser validado
formalmente antes da liberação operacional. Essa validação continua pendente.
Registrar o negócio não aprova plano, atesta fonte, assina ou ativa regras.

**Revisão para aprovação formal do 4.3B.2B:** consulte as
[fichas consolidadas TREE/PLAZA](preparacao_4_3B_2B/PRONTIDAO_E_CHECKLIST.md) e a
[prioridades e controles de precedência](preparacao_4_3B_2B/PRECEDENCIAS_PROPOSTAS.md).
Os números das seis regras estão confirmados como negócio, sem aplicação
operacional ou aprovação formal dos planos. “Pendente” na
matriz histórica abaixo significa falta de aprovação formal, não ausência de
resposta aos efeitos empresariais já confirmados. **Atualização documental:**
original da régua incorporado, 712.353 bytes e SHA-256 esperado exato, fingerprint
`c56349e33b54…`. Os [oito vínculos à fonte e suas ressalvas](preparacao_4_3B_2B/VIGENCIA_E_VERSOES.md)
estão registrados; fundamento/validação formal da aplicabilidade anterior à
fonte e aprovação dos planos continuam pendentes. Vigência de negócio já definida. A fonte usa unidades nas exclusões TREE; a decisão
posterior confirmada fixa cota/componentes, preservada sem reinterpretação.

Revisão de requisitos de 22/10/2026, conforme decisão expressa do responsável.
**Requisito de negócio definido não equivale a plano aprovado, atesto de fonte
ou autorização de implementação.** Nenhum plano real foi configurado ou ativado.
O sistema permanece não homologado para produção.

**Decisão de negócio TREE confirmada posteriormente pelo responsável:** centavo,
A, AJ e J são exclusões da **cota e seus componentes**, nunca automaticamente
da unidade inteira. Basta uma condição, independentemente do vencimento. Esta
confirmação substitui as pendências de escopo/ação anteriores; não valida por si
o mapeamento dos campos nos PDFs nem aprova, assina ou ativa um plano.

**Validação técnica preparatória posterior:** o
[relatório de mapeamento Habita](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md)
confirma os campos no PDF privado autorizado: `Valor` de cada componente,
`Boleto.composicao.total_original` integral e A/AJ/J no campo entre número e
vencimento. Inventário, valores e apontamentos conferem para os 769 boletos.
É evidência de leitura deste arquivo, não atesto humano ou aprovação de plano.

Após o aceite desse mapeamento pelo responsável, a
[conferência exaustiva do campo](COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md)
registrou 628 boletos com vazio validado, 141 preenchidos e zero inconclusivos,
incluindo as 33 continuidades. As
[cinco fichas individuais](COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md#cinco-fichas-individuais)
estão prontas para decisão, sem prioridades numéricas/vigências presumidas. Isso
não emite cobertura operacional, atesto humano, aprovação, assinatura ou ativação.

Os oito IDs do levantamento são mantidos para rastreabilidade. Não representam
oito regras financeiras a ativar: uma proposta saiu da seleção e outra passou a
ser uma opção universal do processamento. O
[`matriz_preliminar_4_3A.json`](../examples/fase4/matriz_preliminar_4_3A.json)
permanece como contrato histórico, superado quanto às hipóteses de negócio abaixo.
A proposta documental atual é
[`proposta_configuracao_4_3B.revisada.json`](../examples/fase4/proposta_configuracao_4_3B.revisada.json).
Ela não é plano executável nem extensão já implementada dos schemas.

## TREE MORUMBI

| ID | Condição / operador | Escopo e ação revisados | Prioridade | Vigência | Evidência disponível / pendência |
|---|---|---|---|---|---|
| `tree_centavo` | Original integral do boleto/cota, exatamente R$ 0,01; `Valor` dos componentes somado e conferido com fechamento quando presente; independente do vencimento | **Confirmado:** excluir somente a cota e todos os seus componentes. Outras cotas da unidade continuam avaliadas normalmente | 1 confirmada como negócio; plano pendente. Exclusão não pode ser anulada pelo prazo | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E366, linha interna 4**. Mapeamento técnico conferido: `Boleto.composicao.total_original`, sem confundir componente, encargos ou total atualizado. Não há plano aprovado/assinado/ativado; atesto e vínculo formal à régua pendentes. Q05, Q11–Q12 |
| `tree_apontamento_a` | Código A **entre número e vencimento**, associado à cota; igualdade, independente do vencimento; não procurar em texto livre | **Confirmado:** excluir cota inteira e componentes; preservar outras cotas da mesma unidade | 1 confirmada como negócio; plano pendente. Uma exclusão já basta; prazo não a anula | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E366, linha interna 4**. 15 boletos com A conferidos; namespace canônico é o formato do contexto e origem é a primeira linha do boleto. Atesto, vínculo à régua e aprovação do plano pendentes. Q13 |
| `tree_apontamento_aj` | Código AJ **entre número e vencimento**, associado à cota; igualdade exata, independente do vencimento | **Confirmado:** excluir cota inteira e componentes. AJ sozinho basta, inclusive se coexistir com A/J; não excluir outras cotas | 1 confirmada como negócio; plano pendente. Não exige combinar condições | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E366, linha interna 4**. 9 boletos com AJ conferidos; AJ não equivale a A por correspondência parcial. Continuidade preserva o código e todas as origens. Atesto e aprovação técnica/formal do plano pendentes. Q14 |
| `tree_apontamento_j` | Código J **entre número e vencimento**, associado à cota; igualdade, independente do vencimento | **Confirmado:** excluir cota inteira e componentes, sem exclusão automática de outras cotas e sem criar filtro judicial | 1 confirmada como negócio; plano pendente. Exclusão não pode ser anulada pelo prazo | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E366, linha interna 4**. 117 boletos com J conferidos, com namespace e origens; códigos em legendas não foram associados. Sem inferir semântica jurídica. Atesto e aprovação técnica/formal do plano pendentes. Q15 |
| `tree_prazo_30` | **TREE confirmado:** atraso estritamente **> 30 dias corridos**, referência explícita; inclusão somente a partir do 31º dia | Cota individual: dia 30 não satisfaz; dia 31 satisfaz apenas o prazo, **se não houver centavo, A, AJ, J ou outro impedimento aplicável** | 0 confirmada como negócio; plano pendente; não supera nenhuma das quatro exclusões nem bloqueios críticos | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E366, linha interna 1**. Prazo e alcance confirmados pelo responsável para TREE. Conferência humana do vínculo à régua, data concreta, fundamento de aplicabilidade anterior à fonte e aprovação da versão/hash pendentes; prioridade 0 confirmada como negócio. Q16 |

O lote Habita/VG continua bloqueado. As 769 competências ausentes permanecem
ausentes: não derivar de vencimento, emissão ou descrição. “Cota” é o objeto de
negócio; sua correspondência com `Boleto` e `Composicao` precisa ser documentada
antes de configurar a condição monetária. O mapeamento técnico foi documentado
para o PDF autorizado: cada item recebe seu `Valor`, e a cota integral usa
`Boleto.composicao.total_original`. O predicado tipado `valor_original` consulta
esse total, não um componente isolado. Multas, juros e atualização são separados;
`Total` é atualizado e não substitui o original. Validar novamente fontes/layouts
diferentes; esta conferência não substitui atesto humano ou plano aprovado.

Para cada cota TREE, a condição de exclusão é **centavo OU A OU AJ OU J**: uma
única condição comprovada basta para tornar a cota inteira inelegível como dívida,
mesmo fora do prazo ou com vencimento futuro. Outras cotas da unidade seguem
avaliação normal. Isso não remove os registros ou componentes do canônico/auditoria:
preservar todas as evidências, fontes e gatilhos, inclusive quando coexistirem.

O reconhecimento de A/AJ/J deverá usar exclusivamente os campos apropriados do
relatório, com associação comprovada à cota e proveniência. Legendas, observações
e textos descritivos não são gatilhos por mera ocorrência das letras. Campo ou
vínculo ambíguo exige revisão; não presumir ausência nem presença do apontamento.
Houve conferência técnica do PDF nesta etapa preparatória, sem avaliar regras
reais. Para afirmar ausência de apontamento no avaliador, manter a exigência de
cobertura explícita do campo/namespace; lista vazia isolada não basta.

## PLAZA MAYOR IPIRANGA

| ID histórico | Condição / operador | Escopo e ação revisados | Prioridade | Vigência | Evidência disponível / pendência |
|---|---|---|---|---|---|
| `plaza_prazo_30` | Quando previsto na régua extrajudicial: atraso **> 30 dias corridos**, referência explícita | Cota individual; dia 31 satisfaz o prazo, sem filtro judicial adicional e sem liberar bloqueios | 0 confirmada como negócio; plano pendente | **Negócio confirmado:** de `2026-09-10` inclusivo até `null` (fim aberto); fundamento/aprovação formal pendentes | **Origem: aba RÉGUA DE COBRANÇA, E329, linha interna 2**. Semântica definida pelo responsável. Conferência humana de aplicabilidade/vigência da fonte, parâmetros do plano, data concreta e aprovação formal pendentes. Q17 |
| `plaza_juridico_60` | **Retirado da proposta de elegibilidade do Excel** | Não configurar prazo judicial de 60 ou 90 dias como filtro adicional; análise posterior das medidas cabe ao CRM | Não se aplica ao seletor | Não se aplica ao seletor | **Origem: aba RÉGUA DE COBRANÇA, E329, linha interna 3; histórico, não configurar**. Decisão expressa do responsável. Q18–Q20 respondidas quanto à finalidade; marcos judiciais não são pré-requisito do seletor extrajudicial |
| `plaza_cadastro_antecipado` | **Substituído por opção universal A/B do processamento**, independente da FL | A: somente cotas elegíveis. B: também no máximo uma linha cadastral adicional por unidade com cotas não elegíveis; pode coexistir com dívida elegível | Não é prioridade financeira; nunca supera bloqueios | Não é vigência de regra condominial; registrar versão da política e modo na execução | **Origem: aba RÉGUA DE COBRANÇA, E329, linhas internas 5/9; contexto cadastral, não comprova toda a política A/B**. Universalidade/gatilho/cardinalidade definidos pelo responsável. Escolher modo por execução, sem default; implementação futura e homologação da saída pendentes. Q21–Q22 |

As 34 unidades FL retidas, os conflitos documentais e os demais críticos continuam
bloqueados, também para linhas cadastrais. Cadastro Geral complementa as unidades
da inadimplência por condomínio + torre/bloco + unidade; seus 390 registros não
se tornam automaticamente unidades para exportação.

## Requisitos gerais definidos

| Tema | Decisão incorporada | Pendência remanescente |
|---|---|---|
| Finalidade | Seleção de cotas extrajudiciais, organização e Excel easyCollector; medidas posteriores cabem ao CRM | Aprovar planos e homologar saída; não executar cobrança |
| Prazos | Referência explícita, dias corridos; quando o prazo aprovado for 30, operador `>` e início no 31º dia | Data concreta por execução; outros prazos somente por plano aprovado, sem padrão global de 30 dias |
| Garantidora | Associação isolada não modifica elegibilidade; **sem exclusão autônoma**, sem duplicar centavo | Nenhum filtro de garantidora a configurar; preservar dados de origem sem criar condição |
| Cadastro antecipado | Opção universal A/B por processamento, independente de administradora/condomínio | Implementação posterior e escolha explícita, registrada em histórico/auditoria |
| Autoridade | Responsável pelo projeto pode acumular Administrador, Revisor e Operador na mesma identidade autorizada | Vincular identidade na área privada; registros independentes de ações, aprovações, atestos e decisões. Cargo não aprova automaticamente |
| Aprovação e integridade | Plano versionado e aprovado com hash, vigência e controles administrativos; atesto humano separado | Fundamento/validação da aplicabilidade anterior à fonte e manifestações formais pendentes; prioridades e datas de negócio definidas |
| Segurança | Bloqueios críticos prevalecem sobre regras e A/B; ausência/contradição relevante não vira permissão | Decisões próprias sobre VG, titularidade e documentos; esta revisão não libera impedimentos |
| Dados e template | Valores preservados, competência não inferida, 30 colunas originais, CPF/CNPJ válido textual na coluna literal `CPF` | Homologação integral easyCollector posterior; ausentes/inválidos vazios + alerta, conflitos retidos |

### Comportamento proposto dos modos — sem implementação nesta tarefa

| Situação da unidade, sem bloqueios críticos | Modo A | Modo B |
|---|---|---|
| Somente cotas elegíveis | Dívidas elegíveis | Dívidas elegíveis, sem cadastro adicional |
| Somente cotas comprovadamente não elegíveis | Sem dívida nem cadastro | No máximo uma linha exclusivamente cadastral |
| Cotas elegíveis e não elegíveis | Somente dívidas elegíveis | Dívidas elegíveis + no máximo uma linha cadastral |
| Registro só no Cadastro Geral, fora da inadimplência | Sem inclusão automática | Sem inclusão automática |
| Bloqueio crítico de lote/unidade/titular/documento | Preservar impedimento do escopo | Mesmo impedimento; cadastro não contorna bloqueio |
| Elegibilidade indeterminada ou evidência incompleta | Revisão, sem autorização presumida | Revisão; não reclassificar como “não elegível” apenas para gerar cadastro |

Nas linhas cadastrais, **Y:AD permanecem vazias**: contrato, produto, dívida,
parcela, vencimento e valor. Preservar as outras 24 colunas e CPF/CNPJ como texto.
O modo integrará histórico e auditoria do processamento. Nenhum modo foi escolhido
para uma execução nesta tarefa.

## Pendências para a próxima autorização

- Atestos humanos por fonte/conjunto, versão/hash da régua e vínculo às condições.
- Atestar humanamente o mapeamento técnico conferido de Valor e A/AJ/J neste PDF; fontes/layouts diferentes exigem validação própria, sem presumir cobertura negativa dos apontamentos.
- Formalizar o vínculo à régua e o fundamento da aplicabilidade desde 10/09/2026, anterior à fonte de rótulo 20/10/2026; incorporar as prioridades de negócio confirmadas somente ao futuro conteúdo versionado aprovado; efeitos/escopo TREE já confirmados e campos tecnicamente conferidos, sem aprovação do plano.
- Identidade autorizada e registros separados dos atos; decisões próprias dos bloqueios.
- Data de referência e modo explícitos por execução; critérios de comparação das referências.
- Revisão de aderência aos contratos e autorização posterior para implementar o 4.3B.

Respostas Q01–Q26 em [Decisões e pendências](DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md).
A preferência por Cadastro em conflito, antes permitida somente no laboratório,
**não** foi promovida a regra geral. Texto livre não ativa planos.
