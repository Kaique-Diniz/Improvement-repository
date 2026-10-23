# Ficha individual — tree_prazo_30

**TREE MORUMBI — Prazo extrajudicial de 30 dias. Estado: pronta para decisão humana, não aprovada.**
Decisão de negócio já confirmada; esta ficha não é plano executável nem evento
formal de aprovação. Não existe assinatura/ativação ou autorização de cobrança.

| Campo | Conteúdo preparado / pendência |
|---|---|
| Regra | `tree_prazo_30` |
| Condomínio | TREE MORUMBI; identificação técnica do plano/catálogo a vincular na área privada |
| Condição e campo canônico | Diferença em dias corridos entre `data_ref` explícita do processamento e `Boleto.vencimento`, estritamente maior que 30. |
| Operador lógico | `dias_atraso`, operador `gt`, inteiro `30`. Dia 30 não satisfaz; dia 31 satisfaz somente o prazo. |
| Escopo | **Cota/boleto e seus componentes**, nunca exclusão automática da unidade inteira |
| Ação | Incluir como dívida somente a cota que satisfaça prazo e demais condições aprovadas, sem exclusões, inconclusão relevante ou bloqueios críticos. |
| Interações e precedências | **Centavo OU A OU AJ OU J**: uma condição comprovada basta. As quatro exclusões prevalecem sobre satisfação do prazo. Permissão de prazo nunca recupera cota excluída. Bloqueios críticos prevalecem sobre tudo |
| Outras cotas da unidade | Continuam avaliadas normalmente; não herdam exclusão, valor ou apontamento desta cota |
| Prioridade numérica | **0 confirmado como decisão de negócio; sem aprovação ou ativação do plano**. O ramo complementar é representação técnica a validar no conteúdo final, não uma regra adicional confirmada. Ver [prioridades confirmadas e aprovação formal pendente](../preparacao_4_3B_2B/PRECEDENCIAS_PROPOSTAS.md); inclusão guardada não supera exclusões, indeterminação ou críticos |
| Data de referência do processamento | **Pendente: AAAA-MM-DD**, escolhida explicitamente por execução. Não assumir hoje, data do PDF ou do Excel. Mesmo nas exclusões independentes de vencimento, o processamento registra a referência |
| Vigência — decisão de negócio confirmada | `vigente_de: 2026-09-10` inclusivo; `vigente_ate: null`, fim aberto até substituição/revogação expressa. **Fundamento/evidência e validação formal da aplicabilidade anterior à fonte de rótulo 20/10/2026 pendentes**; não é aprovação do plano |
| Fonte e versão da régua | Original de rótulo 20/10/2026 incorporado: 712.353 bytes e SHA-256 esperado exato (completo privado), fingerprint `c56349e33b54…`. Aba RÉGUA DE COBRANÇA, E366, linha interna 1. [Vínculo e ressalvas](../preparacao_4_3B_2B/VIGENCIA_E_VERSOES.md). Texto-fonte fala em unidades; decisão posterior define cota/componentes. Conferência humana do vínculo, fundamento/validação da aplicabilidade anterior à fonte e aprovação formal pendentes |
| Evidência técnica | Vencimentos dos 769 boletos reconciliados com a fonte. Testes sintéticos de vencimento futuro, dia zero, 29/30/31 e referência explícita; sem competência inferida. Ver [mapeamento aceito](../MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md) e [cobertura exaustiva](../COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md). Hashes, páginas e linhas completas no dossiê privado |
| Cobertura prévia dos apontamentos | Vazio só com campo/linha/namespace comprovados e cobertura completa. Inconclusão gera revisão e ocorrência crítica por boleto, sem dívida exportável. Evidência ausente não comprova ausência |
| Integridade e auditoria | Preservar todas as origens e componentes, inclusive das cotas excluídas; nenhum dado ou bloqueio é removido para aprovar a regra |
| Bloqueios ativos | Habita/VG impede o lote; documentos, titularidade e outros críticos mantêm seus escopos. Aprovar esta ficha não remove esses impedimentos |
| Cadastro A/B | Universal e escolhido por execução. A: somente dívidas elegíveis. B: também até uma linha cadastral adicional por unidade com cotas comprovadamente não elegíveis; pode coexistir com dívida. **Y:AD vazias**, sem contornar bloqueios nem importar todo Cadastro Geral |
| Plano / versão / hash | **Pendentes**. Aprovação formal futura precisa identificar o conteúdo exato e sua versão/hash; a ficha isolada não o substitui |
| Aprovação humana da ficha | **Pendente**, não registrada nesta tarefa |
| Aprovação técnica/formal do plano | **Pendente**; nenhum evento emitido |
| Assinatura / ativação | **Não realizadas** |

## Registro de decisão — preencher exclusivamente na área privada

| Campo humano | A preencher |
|---|---|
| Decisão sobre o conteúdo da ficha | Aprovar conteúdo / solicitar ajuste / rejeitar, com fundamento; não marcado |
| Pendências/ajustes e alternativas recusadas | Registrar expressamente |
| Prioridade e vigência | Vigência de negócio definida desde 2026-09-10, fim aberto expresso. Prioridade **0** confirmada como negócio. Fundamento da aplicabilidade anterior à fonte e aprovação formal do plano ainda pendentes; preservar versões anteriores |
| Fonte/versão/hash/trecho da régua revisada | Registrar na ficha privada |
| Responsável e identidade autorizada | Responsável pelo projeto; identificar privadamente |
| Papel exercido neste ato | Administrador, Revisor ou Operador, conforme ação; mesma identidade pode acumular papéis |
| Instante e fundamento | Data/hora com fuso e justificativa da manifestação |
| Evidência e vínculo à versão/hash | Referência privada; se plano ainda não existe, não declarar aprovação formal dele |

Atesto de fontes, decisão desta ficha, aprovação de plano e eventual ativação são
atos **independentes**. Acumular papéis ou preencher este modelo não pratica esses
atos automaticamente. Nenhum dado pessoal, credencial ou valor de cliente deve
ser colocado no Git. **Sistema não homologado para produção.**
