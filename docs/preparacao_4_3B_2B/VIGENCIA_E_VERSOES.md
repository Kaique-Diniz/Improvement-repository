# Versões e vigência — vínculo documental e lacunas para aprovação

**Decisão de negócio confirmada de vigência — ainda sem aprovação formal:**
para TREE MORUMBI e PLAZA MAYOR IPIRANGA, `vigente_de: 2026-09-10` (inclusivo),
`vigente_ate: null`, com fim aberto expressamente definido até substituição ou
revogação expressa. A referência do processamento continua independente e não
foi escolhida. **Ressalva obrigatória:** 10/09/2026 antecede o rótulo documental
20/10/2026; o fundamento dessa aplicabilidade anterior deve ser validado
formalmente antes da liberação operacional. Essa validação continua pendente.
Registrar o negócio não aprova plano, atesta fonte, assina ou ativa regras.

## Original incorporado após a disponibilização do anexo

**`REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx` identificado e conferido:**
712.353 bytes e correspondência exata com o SHA-256 informado pelo responsável.
Fingerprint de localização: `c56349e33b54…`; o SHA-256 completo, tamanho esperado,
caminho e evidências por célula estão exclusivamente no inventário privado.

Cópia: `/workspace/validacao-privada-fase3/REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx`,
fora do Git, arquivo `0600` em raiz `0700`. Original do anexo não modificado.
Somente esta régua foi inspecionada nesta incorporação; os cinco PDFs/Excel de
inadimplência/cadastro/referência não foram reabertos.

O complemento privado existente foi atualizado:
`resultados/verificacao_final_aprovacoes_4_3B_2B/METADADOS_CONFERENCIA_FINAL.json`,
com hashes dos bytes, células e linhas pertinentes. O Markdown adjacente explica
as referências. As versões anteriores desses dois rascunhos foram preservadas
integralmente em `_historico/`, com nomes vinculados a seus hashes anteriores.
Os inventários 001/007, contratos 1.0/1.1 e pacotes assinados não foram alterados.
A régua é fonte documental adicional, sem inclusão automática em pacote assinado
ou substituição das cinco fontes operacionais históricas.

## Oito IDs vinculados à fonte exata — não são oito regras a ativar

Todas as coordenadas abaixo pertencem à aba **`RÉGUA DE COBRANÇA`** dessa versão
documental. Linha interna significa `str(valor_celula).splitlines()`, contando
linhas vazias, com início em 1. Não há transcrição das células mistas.

| ID | Origem documental | Vínculo e ressalva |
|---|---|---|
| `tree_centavo` | C366 identifica condomínio; E366, linha interna 4 | Condição monetária contextualizada na régua. O original integral canônico e o alcance por cota decorrem do mapeamento técnico e das decisões posteriores, não de interpretação automática |
| `tree_apontamento_a` | E366, linha interna 4 | Código A na régua; reconhecimento somente pelo campo/namespace de apontamento validado do boleto |
| `tree_apontamento_aj` | E366, linha interna 4 | Código AJ exato; não correspondência parcial |
| `tree_apontamento_j` | E366, linha interna 4 | Código J exato; não criar filtro judicial |
| `tree_prazo_30` | E366, linha interna 1 | Prazo de 30 dias; operador estrito `>30`, dias corridos e referência explícita definidos pelo responsável |
| `plaza_prazo_30` | C329 identifica condomínio; E329, linha interna 2 | Prazo de 30 dias, com a mesma semântica confirmada, sem condições TREE presumidas |
| `plaza_juridico_60` | E329, linha interna 3 | Menção judicial de 60 dias comprovada, mas **retirada do seletor** por decisão posterior; não configurar |
| `plaza_cadastro_antecipado` | E329, linhas internas 5 e 9, somente contexto cadastral | **Substituído pela opção universal A/B**. Os trechos não comprovam toda a política universal, cuja origem é a decisão posterior do responsável |

### Divergências documentais explicitadas, sem reabrir decisões confirmadas

- A redação E366 menciona **unidades** nas exclusões e agrupa condições;
  as decisões posteriores confirmadas fixam **cota/componentes**, centavo **OU**
  A **OU** AJ **OU** J, sem atingir outras cotas. Registrar essa precedência
  normativa no futuro plano; não voltar à exclusão integral da unidade.
- Há menções judiciais de 90 dias TREE (E366, linha interna 2) e 60 dias PLAZA.
  Nenhuma é filtro adicional do Excel. Garantidora contextual também não exclui.
- As expressões de prazo na planilha não definem sozinhas operador estrito,
  contagem ou vigência; `>30` dias corridos foi definido pelo responsável.
- A/B é requisito universal posterior, não condição financeira particular
  extraída do contexto cadastral PLAZA. Não configurar outras particularidades
  de acordos, honorários, envio ou administração a partir desses textos.
- E366/E329 contêm informações mistas de acesso/administração. Somente
  coordenadas, resumos sem dados sensíveis e hashes privados foram vinculados;
  células integrais, credenciais e contatos não foram copiados para relatórios.

## Campos separados para a decisão futura

| Campo | TREE MORUMBI | PLAZA MAYOR IPIRANGA |
|---|---|---|
| Versão documental da fonte | Arquivo original de rótulo 20/10/2026, hash privado conferido | Mesma fonte, com trecho próprio na linha 329 |
| Aplicabilidade operacional/vigência da fonte | Atesto humano pendente; rótulo nominal não prova início/fim | Atesto humano pendente; mesma restrição |
| Prioridades de negócio confirmadas | Exclusões centavo/A/AJ/J **1**, prazo **0**; plano não aprovado | Prazo **0**; plano não aprovado |
| `vigente_de` do plano — negócio confirmado | **2026-09-10, inclusivo** | **2026-09-10, inclusivo** |
| `vigente_ate` do plano — negócio confirmado | **null**, fim aberto expresso | **null**, fim aberto expresso |
| Decisão expressa de fim aberto | **Confirmada como negócio**, até substituição/revogação expressa | **Confirmada como negócio**, até substituição/revogação expressa |
| Fundamento de aplicabilidade anterior ao rótulo 20/10/2026 | **Pendente de informação/evidência e validação formal** | **Pendente de informação/evidência e validação formal** |
| ID/versão/hash final do plano | **Não gerados** | **Não gerados** |
| Aprovação humana: identidade/função/instante/fundamento | **Em branco** | **Em branco** |
| Data de referência do processamento | **Em branco**, escolha explícita por execução | **Em branco**, escolha explícita por execução |

O contrato temporal permanece **`[vigente_de, vigente_ate)`**, início inclusivo
e fim exclusivo. Se houver fim, deve ser posterior ao início. Para estes dois
condomínios o fim aberto foi expressamente definido como negócio, sem aprovação
formal do plano. A substituição/revogação exigirá ato próprio auditável, sem
alterar conteúdos assinados ou sobrescrever versões históricas. **20/10/2026 é rótulo documental, não início de vigência**.
Datas técnicas de criação/modificação do XLSX não são vigência aprovada.
Vencimento do boleto, vigência do plano, instante da aprovação e referência do
processamento são dados distintos. Não usar hoje ou o mês dos Excel por omissão.

## Atos que continuam pendentes

- Conferência humana da fonte e do vínculo documental a cada proposta, incluindo
  as decisões posteriores que esclareceram o texto original.
- Incorporar as [prioridades de negócio já confirmadas](PRECEDENCIAS_PROPOSTAS.md)
  ao futuro conteúdo versionado para aprovação formal, sem pedir os números novamente.
- Informar o fundamento/evidência e validar formalmente a aplicabilidade desde
  10/09/2026, anterior ao rótulo 20/10/2026 da fonte. Início e fim aberto já
  definidos como negócio não são perguntas ainda abertas.
- Atestos das cinco fontes e do conjunto; identidade autenticada/autorizada em
  cada ato independente, ainda que acumule Administrador, Revisor e Operador.
- Fechamento do conteúdo final/versionamento/hash e aprovação válida de cada
  plano; autorização posterior específica de integração e simulação privada.

A dependência técnica de localizar/hashar a régua foi resolvida. **Aprovação,
atestos, assinatura e ativação não foram realizados.** Habita/VG, retenções FL,
titularidade e documentos conflitantes continuam obrigatoriamente bloqueados.
Sem simulação real, cobrança, XLSX operacional, push ou merge. Fase 5 não iniciada;
sistema não homologado para produção.

## Histórico anterior ao recebimento deste anexo

A busca nominal anterior não encontrou a régua na área autorizada. Esse resultado
é histórico e está preservado no snapshot privado do complemento; deixou de
representar o estado atual após o recebimento e a conferência deste original.
Os inventários históricos dos cinco anexos continuam válidos para seu escopo,
sem serem reescritos para aparentar que já continham esta sexta fonte documental.
