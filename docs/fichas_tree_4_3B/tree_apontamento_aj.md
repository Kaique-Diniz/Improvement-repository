# Ficha individual — tree_apontamento_aj

**TREE MORUMBI — Apontamento AJ da cota. Estado: pronta para decisão humana, não aprovada.**
Decisão de negócio já confirmada; esta ficha não é plano executável nem evento
formal de aprovação. Não existe assinatura/ativação ou autorização de cobrança.

| Campo | Conteúdo preparado / pendência |
|---|---|
| Regra | `tree_apontamento_aj` |
| Condomínio | TREE MORUMBI; identificação técnica do plano/catálogo a vincular na área privada |
| Condição e campo canônico | `Boleto.apontamentos[]`: código original exatamente `AJ`, no namespace do formato Habita do contexto e associado à cota por origem. Campo entre número e vencimento. |
| Operador lógico | `apontamento`, comparação exata de código `AJ` e namespace; não equivale a A por correspondência parcial. Ausência exige cobertura; inconclusão exige revisão. |
| Escopo | **Cota/boleto e seus componentes**, nunca exclusão automática da unidade inteira |
| Ação | Excluir a cota inteira e todos os componentes como dívida, independentemente do vencimento. |
| Interações e precedências | **Centavo OU A OU AJ OU J**: uma condição comprovada basta. As quatro exclusões prevalecem sobre satisfação do prazo. Permissão de prazo nunca recupera cota excluída. Bloqueios críticos prevalecem sobre tudo |
| Outras cotas da unidade | Continuam avaliadas normalmente; não herdam exclusão, valor ou apontamento desta cota |
| Prioridade numérica | **Pendente de aprovação**, sem número proposto. A configuração futura deve demonstrar a precedência acima; não basta aprovar números que a contradigam |
| Data de referência do processamento | **Pendente: AAAA-MM-DD**, escolhida explicitamente por execução. Não assumir hoje, data do PDF ou do Excel. Mesmo nas exclusões independentes de vencimento, o processamento registra a referência |
| Vigência proposta | **Pendente**, início e fim ou fim aberto a decidir expressamente; não inferir de documento ou desta ficha |
| Fonte e versão da régua | **Pendentes de identificação/conferência**: extrato autorizado, versão, vigência documental, trecho pertinente, hash e localização privada. Nome histórico da régua não comprova aplicabilidade atual |
| Evidência técnica | 9 boletos únicos com AJ, 10 linhas incluindo continuidades; código, namespace e origens preservados. Ver [mapeamento aceito](../MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md) e [cobertura exaustiva](../COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md). Hashes, páginas e linhas completas no dossiê privado |
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
| Prioridade e vigência escolhidas | Registrar antes de configurar versão final; não há defaults |
| Fonte/versão/hash/trecho da régua revisada | Registrar na ficha privada |
| Responsável e identidade autorizada | Responsável pelo projeto; identificar privadamente |
| Papel exercido neste ato | Administrador, Revisor ou Operador, conforme ação; mesma identidade pode acumular papéis |
| Instante e fundamento | Data/hora com fuso e justificativa da manifestação |
| Evidência e vínculo à versão/hash | Referência privada; se plano ainda não existe, não declarar aprovação formal dele |

Atesto de fontes, decisão desta ficha, aprovação de plano e eventual ativação são
atos **independentes**. Acumular papéis ou preencher este modelo não pratica esses
atos automaticamente. Nenhum dado pessoal, credencial ou valor de cliente deve
ser colocado no Git. **Sistema não homologado para produção.**
