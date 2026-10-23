# Decisões e pendências antes dos planos reais

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

**Consolidação atual para o 4.3B.2B:** as respostas de negócio abaixo são
preservadas, sem reapresentá-las como perguntas não respondidas. Consulte
[aprovações formais restantes e checklist](preparacao_4_3B_2B/PRONTIDAO_E_CHECKLIST.md).
Q25 tem agora autorização exclusivamente para preparar essas aprovações, sem
executar documentos reais ou ativar planos. Q02/Q04 e a parte formal de Q06
continuam exigindo conferência humana do vínculo da fonte/versionamento já
identificados, fundamento/validação da aplicabilidade anterior à fonte e aprovação formal do conteúdo final; prioridades de negócio já confirmadas; identidade, atestos e autorização da simulação são atos independentes.
Os incrementos sintéticos aceitos não aprovam planos reais. As 26 questões
originais abaixo mantêm numeração e contexto histórico.

Revisão de 22/10/2026 com as respostas expressas do responsável. Preservadas as
26 perguntas originais e sua numeração, inclusive hipóteses agora rejeitadas.
**Definido** significa requisito de negócio esclarecido, não aprovação formal
de plano, atesto de fonte ou autorização para iniciar o 4.3B.

**Atualização específica TREE:** escopo/ação de A/AJ/J, regra do centavo e prazo
foram confirmados pelo responsável. As pendências remanescentes são de validação
documental/técnica e atos formais; não repetir esses efeitos como decisões de
negócio ainda não respondidas. Não houve validação de PDFs ou execução real.

“Bloqueante” significa informação necessária à configuração/homologação do escopo
indicado; não reclassifica ocorrências operacionais da Fase 3. Prioridades e
vigências reais continuam sem valores presumidos. Fichas preenchidas, identidade
autorizada e evidências sensíveis ficam exclusivamente na área privada.

## Governança, fontes e critérios comuns

| ID | Pergunta original | Resposta incorporada / pendência | Bloqueante e alcance |
|---|---|---|---|
| Q01 | Quem conferirá cada fonte, consolidará o atesto do conjunto e aprovará as regras? Quem decide titularidade? | Responsável pelo projeto acumula Administrador, Revisor e Operador. Uma identidade autorizada pode assumir os três, com registros independentes. Identificação privada, atestos, aprovações e decisões fundamentadas de titularidade ainda precisam de registro; nenhum é automático | Sim, para atos formais e liberação do cadastro afetado; acúmulo de papéis não é impedimento |
| Q02 | Qual é a versão vigente da régua aplicável a cada condomínio e onde está o extrato autorizado para revisão? | Identificação técnica concluída: original de rótulo 20/10/2026, 712.353 bytes, SHA-256 esperado exato no inventário privado; aba RÉGUA DE COBRANÇA, TREE linha 366 e PLAZA linha 329, oito IDs vinculados. Pendentes: conferência humana da aplicabilidade/vínculo, fundamento/validação formal da aplicabilidade desde 10/09/2026 e responsável autenticado. Sem credenciais/régua bruta no Git; não presumir vigência pelo nome | Sim, conferência humana e vínculo operacional de cada plano; localização/hash resolvidos |
| Q03 | Qual data de referência exata será usada e como se conta o prazo em cada condomínio? | Definidos: referência explícita e dias corridos; para régua extrajudicial de 30, `> 30`, a partir do dia 31. Data concreta pendente por processamento, sem “hoje” por omissão | Sim, data concreta antes de avaliar; contagem definida |
| Q04 | A partir de quando e até quando cada regra/plano vale? | **Decisão de negócio confirmada para ambos:** `vigente_de: 2026-09-10`, início inclusivo; `vigente_ate: null`, fim aberto expresso até substituição/revogação expressa. Referência do processamento independente. Pendentes fundamento/evidência e validação formal da aplicabilidade anterior ao rótulo da fonte de 20/10/2026, além de versão/hash e aprovação formal do plano; não alterar versões assinadas | Datas e fim aberto definidos; bloqueante é fundamento/validação formal e aprovação de cada plano |
| Q05 | Qual campo financeiro cada condição deve comparar e o que explica o valor da referência? | Campo Valor mapeado tecnicamente no PDF autorizado: por componente em composicao.itens[].valor e integral em **Boleto.composicao.total_original**, conferido com fechamento quando presente. Multa/correcao/juros separados; Total atualizado não substitui original. Predicado valor_original usa o integral, sem comparar componente isolado. Conferência automática, não atesto ou aprovação | Mapeamento deste PDF conferido; atesto, vínculo a régua e aprovação formal pendentes; validar novos layouts separadamente |
| Q06 | Qual é o alcance, a ação e a prioridade numérica de cada uma das oito regras? Como interagem? | TREE: centavo, A, AJ ou J, qualquer um isoladamente, exclui só a cota inteira/componentes, independentemente do vencimento; não afeta automaticamente outras cotas. Prazo TREE é >30 dias corridos e não anula exclusões. Judicial fora do seletor; cadastro universal A/B mantido. **Prioridades de negócio confirmadas:** centavo/A/AJ/J TREE 1, prazo TREE 0, prazo PLAZA 0. Datas também definidas; fundamento/validação da aplicabilidade anterior à fonte e aprovação formal dos planos pendentes | Escopo/ações/prioridades de negócio confirmados; bloqueantes são validação documental e aprovação formal do conteúdo final, sem reabrir os números |
| Q07 | Quais evidências comprovam apontamento, situação jurídica, garantidora ou outra exceção? | A/AJ/J conferidos no campo entre número e vencimento; codigo_original, namespace_formato do contexto e origem ligados ao boleto. Legendas não viraram apontamentos. Efeito TREE confirmado: excluir cota/componentes, sem filtro judicial/garantidora autonomo. Ausencia exige cobertura explicita | Campos e vínculos conferidos tecnicamente neste PDF; atesto e formalizacao do plano pendentes |
| Q08 | Quais fatos/campos são necessários para cada decisão e onde obtê-los quando não constam nos PDFs? | Valor do boleto validado e vinculado à cota; A/AJ/J comprovados em campos próprios e associados à cota; vencimento/referência explícita; inventário/bloqueios completos; modo A/B explícito. Lacunas/contradições relevantes exigem revisão, sem presumir apontamento ou ausência | Sim, fatos necessários a cada decisão e preparação completa |
| Q09 | Quais documentos e vigências fundamentarão a revisão das titularidades e dos conflitos documentais FL? | Pendente: fontes, vínculo ao titular, vigência e fundamento por caso. Sem prioridade automática do Cadastro ou escolha automática de documentos; registrar decisão própria | Sim, cadastros/unidades afetados; aprovação da régua não resolve |
| Q10 | A futura comparação exige competência para Habita? Há fonte adicional comprovada que a forneça? | Manter as 769 competências ausentes. Necessidade/fonte adicional pendentes se comparação/saída as exigir; não inferir de vencimento, emissão ou descrição | Condicional à comparação/saída; não inventar competência para atender prazo |

## TREE MORUMBI — centavo e apontamentos

| ID | Pergunta original | Resposta incorporada / pendência | Bloqueante e alcance |
|---|---|---|---|
| Q11 | Para o boleto de R$ 0,01, qual campo comprova a igualdade exata e quais boletos entram na busca? Inclui futuros, fora do prazo ou com situação especial? | Igualdade exata a R$ 0,01 deve consultar **Boleto.composicao.total_original**, soma dos valores dos componentes da cota, conferida com fechamento quando existente. Independente do vencimento. Componente isolado de centavo numa cota maior não satisfaz o predicado; contraprova sintética testada | Conferência técnica concluida neste arquivo; atesto e aprovação formal continuam pendentes |
| Q12 | A presença desse boleto deve excluir a unidade inteira, todos os seus boletos e também eventual cadastro sem dívida? | **Não.** Para centavo, A, AJ ou J, excluir somente a cota correspondente e todos os componentes; outras cotas continuam avaliadas normalmente. Não apagar evidências. Linha cadastral segue modo universal A/B e bloqueios, sem exclusão terminal automática da unidade | Escopo confirmado; mapeamento, atestos e aprovação técnica/formal continuam pendentes |
| Q13 | O que significa A, em qual campo/namespace é comprovado, e qual efeito deve produzir? | A no campo entre número e vencimento, ligado a cota por chave e origem; 15 boletos únicos conferidos. Codigo e namespace preservados; ocorrencia em legenda/observação/descrição não e apontamento. Exclusao da cota/componentes independente do vencimento ja definida pelo negocio, sem executa-la | Mapeamento conferido; atesto humano, vínculo formal a régua e aprovação do plano pendentes |
| Q14 | O que significa AJ e como tratá-lo quando coexistir com A ou J? | AJ no mesmo campo proprio, comparacao exata; 9 boletos únicos conferidos, sem equivalência parcial com A. Continuidades preservam um apontamento por boleto e todas as origens. Uma condicao basta pela decisao de negocio; vários códigos na mesma célula não foram homologados por esta amostra | Mapeamento conferido; atesto, fundamento/validação da aplicabilidade anterior à fonte e aprovação formal pendentes; prioridade 1 já confirmada como negócio |
| Q15 | O que significa J e há evidência de que deva afetar toda a unidade ou somente um boleto? | J no campo entre número e vencimento; 117 boletos únicos conferidos e associados a cota correta. Legendas não sao evidencias positivas. Efeito e exclusao da cota/componentes, sem excluir outras cotas ou criar prazo judicial; não foi executada regra real | Mapeamento conferido; atesto humano, vínculo a régua e aprovação técnica/formal do plano pendentes |
| Q16 | Confirmam-se o corte candidato estrito `> 30` e sua contagem? Qual ação/escopo ocorre antes, no dia 30 e após o corte? | **Confirmado para TREE:** por cota, atraso >30 dias corridos, referência explícita. Dias 29/30 não satisfazem; dia 31 satisfaz só o prazo. Centavo OU A OU AJ OU J exclui a cota mesmo no dia 31 ou fora do prazo; demais condições e bloqueios prevalecem | Negócio confirmado; fonte, data concreta, fundamento/validação da aplicabilidade anterior à fonte e aprovação formal pendentes; prioridade 0 confirmada como negócio |

O subtotal Habita/VG permanece bloqueante do lote, separado de Q11–Q16.
Nenhuma resposta ou atesto de completude o libera.

## PLAZA MAYOR IPIRANGA — prazo extrajudicial e retirada do filtro judicial

| ID | Pergunta original | Resposta incorporada / pendência | Bloqueante e alcance |
|---|---|---|---|
| Q17 | Confirmam-se o corte candidato estrito `> 30` e a contagem? A elegibilidade é por boleto ou depende do conjunto da unidade? | Mesmo critério extrajudicial: por cota, `> 30` dias corridos, referência explícita; dia 31 satisfaz só o prazo. Sem padrão universal de 30 nem prazo judicial adicional | Semântica definida; vínculo formal da fonte, fundamento/validação da aplicabilidade anterior à fonte, data de referência e aprovação formal pendentes; prioridade 0 confirmada como negócio |
| Q18 | O prazo de 60 dias jurídico serve para qual operação: elegibilidade, modalidade, negociação, encaminhamento ou outra? | Medidas posteriores cabem ao CRM. **Não usar 60 ou 90 dias judiciais como filtros adicionais do Excel**; retirar `plaza_juridico_60` da proposta de elegibilidade | Não bloqueia seletor extrajudicial; não configurar esse filtro |
| Q19 | De qual evento começam os 60 dias, qual operador é aplicável e como comprovar o status jurídico e sua vigência? | Questão histórica, fora da seleção extrajudicial. Não escolher marco/operador nem criar filtro residual; eventual operação no CRM está fora do escopo | Não bloqueante para configurar o seletor |
| Q20 | Qual regra decide quando o caso jurídico também satisfaz o prazo de 30 dias? | Sem sobreposição entre prazo extrajudicial e judicial no seletor. Aplicar critérios extrajudiciais aprovados e bloqueios. A atualização específica TREE define A/AJ/J como exclusões da cota, sem criar prazo judicial nem aplicar automaticamente esses códigos à FL | Resolvido quanto ao filtro judicial; demais parâmetros formais do plano pendentes |

## Cadastro antecipado — respostas universais, além do caso Plaza original

| ID | Pergunta original | Resposta incorporada / pendência | Bloqueante e alcance |
|---|---|---|---|
| Q21 | Cadastro antecipado estará habilitado para Plaza? Qual é seu gatilho e que unidades podem participar? | Opção **universal por processamento**. A: só cotas elegíveis. B: também linha cadastral para unidade da inadimplência com cota não elegível. Não incluir todo Cadastro Geral; preservar bloqueios; nenhum modo padrão escolhido | Requisito definido; escolher A/B antes de execução futura e registrar em histórico/auditoria |
| Q22 | Quantas linhas cadastrais por unidade/titular são desejadas e quais campos são indispensáveis? Podem coexistir com dívida? | No máximo **uma linha cadastral adicional por unidade** com cota não elegível, inclusive coexistindo com dívida elegível. Nunca dívida não elegível; Y:AD vazias; ausentes não inventados, CPF/CNPJ e bloqueios mantidos. Demais exigências do importador na Fase 5 | Cardinalidade/coexistência definidas; implementação e homologação integral da saída pendentes |

A política universal foi definida agora. A antiga preferência pelo Cadastro em
conflito, autorizada só no laboratório, **não** foi promovida a regra geral.

## Comparação, autorização e retenção

| ID | Pergunta original | Resposta incorporada / pendência | Bloqueante e alcance |
|---|---|---|---|
| Q23 | O que cada linha e agrupamento dos Excel pretende representar e quais diferenças o autor reconhece? | Pendente revisar vínculos/base da referência, distinguindo A/B, data explícita, centavo por cota e ausência de filtro judicial. As 132 coincidências são evidência histórica, não meta a forçar | Sim, homologação comparativa; não autoriza mudar valores |
| Q24 | Quais casos e resultados explicáveis serão aceitos na futura homologação privada? | Preparar casos 30/31; centavo e cada A/AJ/J isolado excluindo só cota/componentes independente do vencimento; outras cotas não afetadas; coexistência preserva todas as evidências; rejeitar gatilhos em legendas/observações/descrições; distinguir Valor do boleto de componentes/encargos/totais; preservar A/B, Y:AD, CPF/CNPJ e bloqueios. Sem filtro judicial ou garantidora autônoma. Aceite formal dos casos pendente | Sim, homologação futura; não foram implementados testes de regras reais nesta tarefa documental |
| Q25 | Depois dos atestos e das decisões, qual escopo será expressamente autorizado para iniciar o 4.3B? | Autorização posterior pendente. A atual cobre **somente documentação, matriz e proposta**, não implementação, simulação real, aprovação ou ativação | Sim, início efetivo do 4.3B |
| Q26 | Quem guardará e poderá consultar fontes, fichas, versões, recibos e contexto de reprodução? | Responsável pelo projeto acumula papéis. Identidade, local privado, acessos e retenção precisam de registro próprio; isso não concede credenciais automaticamente | Sim, governança das operações correspondentes |

## Registro formal posterior — somente no ambiente privado

| Campo | Situação exigida |
|---|---|
| ID/condomínio e questões respondidas | Identificar requisitos definidos e pendências, preservando respostas/hipóteses anteriores |
| Fonte, versão, hash, trecho e mapeamento | Conferir vínculo à régua e Valor → cota/componentes; não transcrever credenciais |
| Condição, operador, escopo, ação, prioridades, vigência | Completar lacunas; sem interpretações ou números presumidos |
| Plano, versão e hash aprovado | Aprovação autorizada vinculada ao conteúdo; mudança exige nova versão/aprovação |
| Atesto por fonte e conjunto | Manifestação humana independente; assinatura técnica não substitui |
| Ator, papel, ação, data/hora com fuso, fundamento | Registros independentes mesmo quando a identidade é a mesma |
| Data de referência e modo A/B | Escolha explícita e auditada, sem herança silenciosa do condomínio ou da data atual |
| Situação atual | Requisitos parcialmente definidos; planos e atestos pendentes, sem ativação |

Contratos históricos 1.0/1.1 e vínculos original → ID legado → ID interno
permanecem preservados. Responder perguntas não reescreve evidências nem retira
bloqueios; editar JSON manualmente não aprova planos.

## Evidência técnica preparatória posterior

Conferência de campos no PDF autorizado documentada em [Mapeamento técnico TREE](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md). Não aprova planos, não emite atestos nem executa regras reais. Q05/Q11/Q13–Q15 agora distinguem mapeamento tecnicamente conferido de validação humana/formal ainda pendente.

## Cobertura e fichas após o aceite técnico do mapeamento

O [resultado exaustivo TREE](COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md) distingue
628 campos vazios validados, 141 preenchidos e zero inconclusivos, nos 769 boletos
e suas continuidades. Isso encerra a investigação técnica de presença/vazio
neste PDF, sem substituir atesto humano ou gerar cobertura operacional aceita.
Q07/Q08/Q13–Q15 passam a contar também com essa evidência técnica; fonte/versão
da régua, fundamento/validação da aplicabilidade
anterior à fonte e aprovação formal continuam pendentes. O início em
2026-09-10, o fim aberto e as seis prioridades já estão definidos como negócio.

As cinco fichas individuais estão vinculadas no relatório; cada uma possui
estado de aprovação pendente, referência do processamento a preencher,
campo/operador/escopo/ação e precedência explícitos. Q01/Q02/Q04/Q25/Q26 e demais
atos humanos estão organizados no [resumo de atestos](RESUMO_ATESTOS_DECISOES_4_3B.md).
Nenhuma resposta ou ficha foi transformada automaticamente em evento de aprovação.
