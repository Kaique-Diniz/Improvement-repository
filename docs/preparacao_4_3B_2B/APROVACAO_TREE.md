# Ficha consolidada — TREE MORUMBI

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

**Incorporação documental posterior:** original da régua conferido com
712.353 bytes e SHA-256 esperado exato, fingerprint `c56349e33b54…`.
Fonte privada vinculada à aba `RÉGUA DE COBRANÇA`, linha **366**.
Ver [versão, coordenadas e ressalvas](VIGENCIA_E_VERSOES.md).
O hash completo está no inventário privado; a conferência humana do vínculo,
fundamento da aplicabilidade anterior à fonte e aprovação formal continuam
pendentes; as prioridades já são decisões de negócio confirmadas; as datas de vigência já são decisão de negócio.
Nenhum plano real foi gerado, aprovado, assinado ou ativado.

Preparação documental de 22/10/2026 (America/Sao_Paulo). **Nenhum plano real foi
criado, aprovado, assinado ou ativado.** As decisões abaixo já foram confirmadas
pelo responsável; não precisam ser respondidas novamente. A ficha organiza o
vínculo dessas decisões ao futuro conteúdo exato do plano.

## Conteúdo de negócio confirmado

| Regra | Campo/condição | Escopo e efeito | Prioridade de negócio confirmada; plano não aprovado |
|---|---|---|---|
| `tree_centavo` | Predicado `valor_original eq "0.01"`, consultando **`Boleto.composicao.total_original`**, decimal exato | Excluir apenas a cota inteira e seus componentes, qualquer vencimento; componente isolado de centavo numa cota maior não satisfaz | Camada de exclusão; número **1 confirmado como negócio** |
| `tree_apontamento_a` | Código original exatamente `A` em `Boleto.apontamentos[]`, namespace real validado e origem ligada ao boleto | Mesma exclusão por cota, sem procurar letras em descrições/observações/legendas | Mesma camada; **1 confirmado como negócio** |
| `tree_apontamento_aj` | Igualdade exata `AJ`, mesmo campo e namespace comprovados; sem correspondência parcial com `A` | Mesma exclusão por cota | Mesma camada; **1 confirmado como negócio** |
| `tree_apontamento_j` | Igualdade exata `J`, mesmo campo e namespace comprovados | Mesma exclusão por cota, sem criar filtro judicial | Mesma camada; **1 confirmado como negócio** |
| `tree_prazo_30` | Dias corridos entre `data_ref` explícita e `Boleto.vencimento`: **`>30`**, junto da ausência comprovada das quatro exclusões | Elegibilidade somente no dia 31 ou posterior; jamais supera exclusão, revisão ou bloqueio | Camada de prazo; **0 confirmado como negócio** |

Uma condição de exclusão basta para impedir dívida da cota; outras cotas da
unidade continuam sendo avaliadas. Duas exclusões não duplicam a decisão nem
apagam justificativas. Valores, encargos, composição e evidências não são
recalculados. Associação isolada à garantidora não exclui cotas.

A inclusão deverá conservar a guarda lógica
`prazo >30 AND NOT(centavo OR A OR AJ OR J)`. O ramo complementar `<=30` apenas
documenta a não elegibilidade temporal; não é uma sexta regra de negócio.
Sua representação técnica na camada **0** continua vinculada à regra de
prazo; é detalhe do conteúdo final a validar formalmente, não uma sexta regra
confirmada ou ativada automaticamente.
Ver [compatibilidade com o motor e indeterminação](PRECEDENCIAS_PROPOSTAS.md).

## Evidência já existente, sem nova leitura do PDF

- Fonte F01: 149 páginas, 112 unidades, 769 boletos, 2.082 componentes.
- Mapeamento de original integral, componentes e encargos aceito tecnicamente;
  [relatório preparatório](../MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md).
- 769 campos de apontamento conferidos anteriormente: 628 vazios validados e
  141 preenchidos, sendo A=15, AJ=9, J=117; zero inconclusivos nesta amostra,
  incluindo 33 continuidades. [Evidência de cobertura](../COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md).
- 769 competências ausentes continuam nulas; não inferir de vencimento,
  emissão ou descrição. Testes sintéticos não são nova homologação real.
- 904 registros externos de auditoria preservados, com vínculo legado e
  `auditoria:v1`; `documento:v2` é a identidade documental nova, não migração
  de todos os registros históricos.

## Condições universais preservadas

Modo A/B e data de referência são escolhidos **por processamento**, sem default
e sem virar regra particular do TREE. No modo B, no máximo um cadastro adicional
por unidade da inadimplência com cota comprovadamente não elegível, podendo
coexistir com dívida elegível. Cadastral não é dívida: **Y:AD vazias** nas futuras
linhas. Não incluir todo Cadastro Geral ou contornar críticos.

**Habita/VG permanece bloqueante do lote inteiro**, inclusive após atesto ou
aprovação deste plano. Nenhuma linha de dívida ou cadastral contorna esse bloqueio.
Falta de prova sobre apontamentos, identidade ou fonte exige revisão/retenção,
sem autorização presumida. Documento ausente mantém alerta, sem preenchimento
inventado; conflitos válidos permanecem bloqueantes.

## Somente campos formais ainda pendentes

| Campo a vincular no ambiente privado | Estado atual |
|---|---|
| ID técnico do condomínio e administradora aplicáveis | Confrontar com catálogo e inventário; não inventar IDs reais |
| Fonte autorizada da régua, versão, hash e trechos pertinentes | Original de rótulo 20/10/2026 incorporado; E366 linha interna 4 (quatro exclusões) e 1 (prazo), SHA completo privado. Fonte fala em unidades; decisão posterior confirmada fixa cota. Conferência humana do vínculo pendente |
| Prioridades — decisão de negócio confirmada | Centavo/A/AJ/J **1** e prazo **0**. Conteúdo formal/versionado e representação do ramo complementar ainda sujeitos à aprovação do plano; nada ativado |
| Início da vigência (`vigente_de`) | **2026-09-10, inclusivo — decisão de negócio confirmada**, ainda não incorporada a plano formalmente aprovado |
| Fim da vigência (`vigente_ate`) ou fim aberto expresso | **null — fim aberto expressamente definido**, até substituição ou revogação expressa; aprovação formal do plano pendente |
| Fundamento da aplicabilidade anterior à fonte de rótulo 20/10/2026 | **Pendente de informação/evidência e validação formal**; a data escolhida não prova vigência documental retrospectiva |
| Data/hora da aprovação humana | **Em branco**, com fuso a registrar no ato efetivo |
| Data de referência do processamento | **Em branco**, escolhida explicitamente em cada execução |
| Namespace real e evidência de cobertura vinculados ao pacote | Conferência humana da evidência técnica existente; não copiar namespace sintético |
| Identificador/versão final do plano e hash do conteúdo | **Não gerados**; não há conteúdo real pronto para assinatura |
| Responsável autenticado, função, instante com fuso, fundamento e evidência | **Não preenchidos**; atos separados de atesto e ativação |
| Evento de aprovação vinculado a versão/hash | **Não emitido**; aprovação da ficha textual não substitui o evento do plano |

Não se solicita reconfirmar centavo, escopo por cota, A/AJ/J, corte de 30 dias,
garantidora ou modos A/B. Prioridades e vigência também não exigem nova pergunta de negócio. Restam
a validação da divergência unidade/cota, o fundamento da aplicabilidade anterior
à fonte, os atestos e a aprovação formal do futuro plano exato.

## Registro humano — preencher somente fora do Git

- Manifestação formal sobre o conteúdo final do plano identificado por versão/hash: __________.
  Prioridades e vigência de negócio já estão definidas; nenhum evento de aprovação é emitido por esta ficha.
- Prioridades de negócio já confirmadas: centavo/A/AJ/J **1**, prazo **0**; sem evento de aprovação/ativação do plano.
- Fonte/versão/hash/trechos da régua: ____________________.
- Vigência de negócio confirmada: início inclusivo `2026-09-10`; fim `null`,
  aberto até substituição/revogação expressa; **não é aprovação formal do plano**.
- Fundamento/evidência da aplicabilidade anterior ao rótulo da fonte e validação formal: __________.
- Plano/versão/hash final: ____________________.
- Identidade autenticada/função exercida: ____________________.
- Instante com fuso, fundamento e evidência privada: ____________________.

Nenhuma opção está marcada. Não preenche atesto, aprovação formal, assinatura,
ativação ou autorização de simulação. [Prontidão e checklist](PRONTIDAO_E_CHECKLIST.md).
