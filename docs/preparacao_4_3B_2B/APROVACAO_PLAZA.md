# Ficha consolidada — PLAZA MAYOR IPIRANGA

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
Fonte privada vinculada à aba `RÉGUA DE COBRANÇA`, linha **329**.
Ver [versão, coordenadas e ressalvas](VIGENCIA_E_VERSOES.md).
O hash completo está no inventário privado; a conferência humana do vínculo,
fundamento da aplicabilidade anterior à fonte e aprovação formal continuam
pendentes; as prioridades já são decisões de negócio confirmadas; as datas de vigência já são decisão de negócio.
Nenhum plano real foi gerado, aprovado, assinado ou ativado.

Preparação documental de 22/10/2026 (America/Sao_Paulo). Decisões de negócio já
confirmadas; **sem plano real criado, aprovado, assinado ou ativado**.

## Conteúdo confirmado, sem condições adicionais presumidas

| Item | Condição/alcance/efeito | Situação |
|---|---|---|
| `plaza_prazo_30` | Por cota, dias corridos entre referência explícita e vencimento **`>30`**; dia 30 não satisfaz, dia 31 satisfaz apenas o prazo, sujeito aos bloqueios | Prazo e prioridade **0 confirmados como negócio**; plano não aprovado/ativado |
| Ramo complementar do prazo | `<=30` documenta cota ainda fora do corte na referência, sem inclusão como dívida; mesma fonte/mesma política do prazo | Proposta técnica de representação, não nova regra de negócio; prioridade **0 proposta** |
| `plaza_juridico_60` histórico | **Fora da seleção**. Não configurar prazos judiciais de 60/90 dias como filtros do resultado | Resolvido; medidas posteriores cabem ao CRM |
| Cadastro antecipado histórico | Substituído pelo modo universal A/B escolhido por processamento | Não criar regra financeira particular `plaza_cadastro_antecipado` |
| Garantidora | Associação isolada não altera elegibilidade | Não criar exclusão autônoma |

**Não importar as exclusões TREE por centavo ou A/AJ/J para PLAZA.** Não
presumir outras condições jurídicas, cadastrais ou financeiras particulares.
Bloqueios de segurança já existentes continuam obrigatórios e não são uma
interpretação nova da régua.

O ramo complementar proposto permite distinguir inelegibilidade temporal
comprovada de ausência de regra aplicável, que o motor encaminha à revisão.
Não significa perdão/exclusão permanente da dívida. O detalhe aguarda confirmação
da proposta técnica, sem reabrir a decisão empresarial sobre o prazo.

## Evidência existente, sem nova leitura das fontes

- F03: PDF FL, 24 páginas, 50 unidades, 115 boletos e 985 componentes.
- Continuidade financeira anterior de 17 boletos; outros três têm continuidade
  somente descritiva. Não há novos boletos por quebra de página.
- F04: Cadastro Geral, 25 páginas e 390 registros. Cruzamento somente por
  **condomínio + torre/bloco + unidade**; as 50 unidades da inadimplência
  permanecem separadas dos demais cadastros.
- 205 registros externos únicos após reconciliação: 201 operacionais e quatro
  documentais. Colisões legadas não foram eliminadas por fusão de evidências.
- F05: 69 correspondências financeiras anteriormente reconciliadas com o Excel;
  referência esperada, não gabarito absoluto nem fonte para inventar cadastro.

## Segurança e modos universais

As **34 unidades FL retidas**, os 83 registros críticos externos e os conflitos
documentais permanecem no inventário. Dois conflitos de documentos válidos,
registrados em duas linhas de uma unidade, exigem revisão humana com vínculo,
fonte e vigência; não escolher automaticamente o Cadastro, a referência ou a fonte
mais recente. Aprovar o plano não resolve titularidade.

A: somente dívidas elegíveis. B: também no máximo um cadastro adicional por
unidade da inadimplência com cota comprovadamente não elegível, podendo coexistir
com dívida elegível. No futuro XLSX, **Y:AD vazias** nas linhas cadastrais.
Não incluir automaticamente os 390 registros. Crítico/revisão retém o cadastro
do escopo conforme o fluxo conservador existente; não transformar dúvida em
inelegibilidade comprovada. CPF/CNPJ ausente não é inventado e mantém alerta;
conflitos críticos não são contornados por qualquer modo.

## Somente campos formais ainda pendentes

| Campo | Estado atual |
|---|---|
| IDs técnicos de condomínio/administradora | Conferência privada no catálogo e no inventário |
| Extrato da régua aplicável, versão, hash e trecho do prazo | Original de rótulo 20/10/2026 incorporado; E329 linha interna 2 (prazo), SHA completo privado. Judicial na linha interna 3 não é filtro; contexto cadastral nas linhas 5/9 não substitui a decisão universal A/B. Conferência humana do vínculo pendente |
| Prioridade — decisão de negócio confirmada | `plaza_prazo_30` **0**. Ramo complementar permanece representação técnica a validar no conteúdo final, sem criar condição adicional; plano não aprovado/ativado |
| Início da vigência (`vigente_de`) | **2026-09-10, inclusivo — decisão de negócio confirmada**, ainda não incorporada a plano formalmente aprovado |
| Fim da vigência (`vigente_ate`) ou fim aberto expresso | **null — fim aberto expressamente definido**, até substituição ou revogação expressa; aprovação formal do plano pendente |
| Fundamento da aplicabilidade anterior à fonte de rótulo 20/10/2026 | **Pendente de informação/evidência e validação formal**; a data escolhida não prova vigência documental retrospectiva |
| Data/hora da aprovação humana | **Em branco**, com fuso a registrar no ato efetivo |
| Data de referência do processamento | **Em branco**, escolhida explicitamente em cada execução |
| ID/versão/hash do plano final | **Não gerados**; não se está aprovando um JSON ativável |
| Identidade autenticada, função, instante, fundamento e evidência da aprovação | **Não preenchidos** |
| Atestos de F03/F04/F05 e conjunto | **Não emitidos**; não liberam os críticos |

## Registro humano — preencher somente fora do Git

- Manifestação formal sobre o conteúdo final do plano identificado por versão/hash: __________.
  Prioridades e vigência de negócio já estão definidas; nenhum evento de aprovação é emitido por esta ficha.
- Prioridade de negócio já confirmada: prazo **0**. Representação do ramo complementar sujeita à aprovação do conteúdo final, sem reabrir o número da regra.
- Fonte/versão/hash/trecho da régua: ____________________.
- Vigência de negócio confirmada: início inclusivo `2026-09-10`; fim `null`,
  aberto até substituição/revogação expressa; **não é aprovação formal do plano**.
- Fundamento/evidência da aplicabilidade anterior ao rótulo da fonte e validação formal: __________.
- Plano/versão/hash final: ____________________.
- Identidade autenticada/função/instante com fuso: ____________________.
- Fundamento e evidência privada: ____________________.

Nenhuma opção foi preenchida. [Precedências](PRECEDENCIAS_PROPOSTAS.md),
[atestação das fontes](ATESTOS_CINCO_FONTES.md) e
[limites para primeira simulação](PRONTIDAO_E_CHECKLIST.md).
