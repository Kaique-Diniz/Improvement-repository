# Procedimento e checklist de atesto humano das fontes

Preparação documental autorizada em 22/10/2026. **Todos os itens humanos estão
pendentes.** A conferência automática, a assinatura técnica e o aceite técnico do
4.3A não preenchem este checklist. Nenhuma regra real é aprovada por este documento.

Os [esclarecimentos de negócio posteriores](ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md)
permitem ao responsável pelo projeto acumular Administrador, Revisor e Operador
na mesma identidade autorizada. Continuam obrigatórios registros independentes
de cada ação, aprovação, atesto e decisão humana. Nenhuma caixa abaixo está
preenchida pelo acúmulo de papéis ou pela definição dos requisitos.

O [mapeamento técnico posterior TREE](MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md)
conferiu Valor integral/componentes/encargos e A/AJ/J no PDF autorizado. É evidência
para apoiar o responsável, não atesto: todos os itens humanos abaixo continuam
pendentes e os bloqueios continuam obrigatórios.

Evidência técnica adicional: os 769 campos TREE foram
[conferidos exaustivamente](COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md), com 628
vazios validados, 141 preenchidos e zero inconclusivos. Conferir privadamente a
revisão 002 do dossiê 009, incluindo todos os cabeçalhos/continuidades; não marcar
esta ficha por execução automática. O
[resumo de atestos e decisões](RESUMO_ATESTOS_DECISOES_4_3B.md) organiza as fontes
TREE/PLAZA e os atos que ainda precisam de manifestação humana.

Usar uma ficha privada por fonte e uma conclusão por conjunto/condomínio. Fichas
preenchidas, hashes reais, identificadores, nomes, documentos e evidências ficam
exclusivamente no ambiente privado. Este arquivo é um modelo sem dados pessoais.
A ficha com os hashes completos já conferidos está em
`/workspace/validacao-privada-fase3/resultados/preparacao_documental_4_3B_007/FICHA_PRIVADA_CONFERENCIA_HUMANA.md`.

## Identificação a preencher em cada ficha privada

| Campo | Preenchimento humano exigido |
|---|---|
| Condomínio e finalidade | Identificar o conjunto e o papel da fonte: inadimplência, cadastro, referência ou requisitos |
| Fonte e versão | Nome, ID do arquivo, período declarado e versão; não usar o nome do arquivo como prova suficiente |
| Integridade | SHA-256 completo, tamanho e localização privada, confrontados com o inventário conferido |
| Extração e auditoria | Versões registradas dos leitores, formato/versão identificado, inventário e reconciliação aplicáveis |
| Completude | Páginas/abas esperadas, unidades, boletos, campos ausentes, continuidade e dossiês complementares |
| Referência temporal | Data de referência exata do conjunto e datas/vigência das fontes e fatos quando comprovadas |
| Responsável | Responsável pelo projeto acumula os três papéis; identificar privadamente a identidade autorizada e o papel em cada manifestação, sem dados pessoais neste modelo |
| Evidência | ID e localização de relatório privado, páginas/linhas verificadas e fundamento da conclusão |
| Resultado | Pendente, recusado ou conferido, com lacunas e bloqueios explicitados |
| Registro | Data/hora com fuso, identificação do revisor e evidência de sua manifestação |

Versão de produtor ausente no histórico deve continuar como **não declarada**.
Não substituí-la pela versão atual. Registrar impacto e evidência disponível;
versões de leitura existentes, hashes e registros originais continuam preservados.

## Procedimento comum

1. Identificar o responsável por cada fonte e quem consolidará a conclusão do
   conjunto. A pessoa que conferiu o cadastro pode precisar de apoio do responsável
   pela titularidade; nenhuma associação é presumida pelo cargo ou pela fonte.
2. Abrir os originais somente na área privada e confrontar SHA/tamanho com a ficha.
   Divergência, arquivo faltante ou carga parcial impede concluir o atesto.
3. Conferir a relação completa de páginas/abas, registros, continuidades e anexos
   contra o inventário. Registrar o alcance da revisão; uma inspeção amostral não
   pode ser descrita como conferência integral de itens não examinados.
4. Confrontar campos disponíveis e ausentes, origens e bloqueios. Confirmar que a
   ausência é fiel à fonte, sem completar dados nem escolher evidência conflitante.
5. Conferir os dossiês externos: leitura, auditoria de lote, titularidade e
   documentos. Catálogo vazio precisa de conferência explícita; falha de carga não
   é evidência de ausência de impedimentos.
6. Registrar a conclusão humana por fonte e depois por conjunto. Se algo não puder
   ser comprovado, registrar pendência/recusa. Não marcar todos os itens como
   conferidos para permitir o processamento.
7. Somente após revisão completa e autorização própria, registrar o atesto pelo
   procedimento técnico existente. Esta tarefa não registra esse atesto nem cria
   pacote humano aprovado.

Conferir a completude de uma fonte **não remove seus bloqueios**. É possível
documentar que o PDF está integralmente representado e que contém uma
inconsistência crítica; o bloqueio continua obrigatório. Dados opcionais ausentes
podem permanecer vazios com alerta, mas não se convertem em fatos comprovados.

## Habita / TREE — fonte de inadimplência

Documento disponível: `Inadimplencia_Tree.pdf`. Evidência técnica anterior:
149 páginas, 112 unidades, 769 boletos e 2.082 itens de composição. Esses números
são pontos de confronto deste conjunto, não metas universais para outros períodos.

- [ ] Confirmar arquivo, condomínio, período, SHA/tamanho e versão do leitor/formato.
- [ ] Conferir todas as páginas e a relação de unidades/boletos do inventário.
- [ ] Conferir continuidade entre páginas sem omissão ou duplicação de lançamento.
- [ ] Conferir origens dos valores, sinais, atualização monetária e apontamentos;
      não converter saldo acumulado em valor individual nem alterar composições.
- [ ] Documentar o campo literal `Valor` validado e sua associação à cota e aos
      componentes, com página/linha e campo canônico comprovados. Centavo exclui
      apenas essa cota/componentes, independentemente do vencimento; não aprovar
      exclusão da unidade nem assumir componente/total como campo de comparação.
- [ ] Conferir os 141 apontamentos inventariados e suas origens. Efeito de A/AJ/J
      confirmado pelo negócio: qualquer um exclui só a cota inteira/componentes,
      independentemente do vencimento, sem afetar outras cotas. Validar campo
      próprio, namespace e associação à cota; não tratar letras em legendas,
      observações ou descrições como gatilhos. Preservar todas as evidências.
- [ ] Confirmar as 769 competências ausentes; manter nulo, sem derivar do vencimento,
      emissão ou descrição. Necessidade posterior de competência exige fonte/critério aprovado.
- [ ] Conferir a ocorrência crítica do subtotal Habita/VG e registrar que o lote
      inteiro permanece bloqueado, inclusive após eventual atesto de completude.
- [ ] Conferir os 904 registros de auditoria, seus IDs legados e vínculos internos.
- [ ] Conferir contatos/documentos disponíveis e ausentes; ausência/invalidade gera
      alerta, enquanto conflito ou associação não comprovada permanece crítico.
- [ ] Indicar se é necessária fonte cadastral adicional para algum dado. Cadastro
      Geral Habita não faz parte dos cinco anexos inventariados; não presumir sua existência.
- [ ] Registrar responsável, data de referência, conclusão, fundamento e evidência privada.

## FL / Plaza — fonte de inadimplência

Documento disponível: `Inadimplencia_PlazaMayor.pdf`. Evidência técnica anterior:
24 páginas, 50 unidades, 115 boletos e 985 itens de composição.

- [ ] Confirmar arquivo, condomínio, período, SHA/tamanho e versão do leitor/formato.
- [ ] Conferir páginas, unidades, boletos, vencimentos e composições do inventário.
- [ ] Conferir continuidade real entre páginas, inclusive descrições e lançamentos.
- [ ] Conferir descontos/sinais e separar valores de boleto dos saldos acumulados;
      nenhuma regra de composição financeira é aprovada neste checklist.
- [ ] Confirmar as competências presentes e registrar campos ausentes sem preenchimento presumido.
- [ ] Identificar quais dados cadastrais precisam de complemento; ausência no PDF
      de inadimplência não autoriza inventá-los ou usar a planilha de referência para preenchê-los.
- [ ] Conferir as 201 ocorrências operacionais e os quatro registros documentais
      externos, totalizando 205 IDs internos únicos.
- [ ] Conferir os dois pares de IDs legados repetidos: células distintas da
      referência continuam como evidências separadas, sem deduplicação ou fusão.
- [ ] Conferir os 83 registros críticos externos e as 34 unidades retidas;
      a correção de identidade não libera titularidade ou documentos conflitantes.
- [ ] Registrar responsável, data de referência, conclusão, fundamento e evidência privada.

## FL / Plaza — Cadastro Geral complementar

Documento disponível: `Cadastro Geral- PMI.pdf`. Evidência técnica anterior:
25 páginas e 390 registros cadastrais. O conjunto de inadimplência permanece com
50 unidades; os 390 cadastros não se tornam unidades de cobrança.

- [ ] Confirmar identidade do condomínio, período/data comprovada da fonte,
      SHA/tamanho e versão do leitor/formato.
- [ ] Conferir as páginas e a relação completa de 390 registros do Cadastro.
- [ ] Conferir o cruzamento exclusivamente por condomínio + torre/bloco + unidade,
      sem associação por nome aproximado ou documento isolado.
- [ ] Conferir quais registros cadastrais correspondem às 50 unidades da inadimplência
      e manter os demais separados.
- [ ] Conferir nomes, múltiplos titulares, relação com a unidade, CPF/CNPJ e fontes;
      não priorizar Cadastro automaticamente nos conflitos.
- [ ] Conferir telefones, e-mails e endereços segmentados, brutos e campos ausentes;
      não completar DDD ou escolher entre dois endereços sem evidência.
- [ ] Registrar a pendência de um cadastro com dois endereços, mesmo que não pertença
      às 50 unidades deste lote; não transferir essa ambiguidade para outro titular.
- [ ] Conferir os dossiês de titularidade/documentos e registrar que vigência ou
      vínculo não comprovados continuam pendentes de decisão humana própria.
- [ ] Registrar responsável cadastral, apoio necessário para titularidade, conclusão e evidência.

## Excel de referência — uma ficha para cada condomínio

Disponíveis: `TREE MORUMBI_OUTUBRO 2026.xlsx` e
`TEMPLATE - PLAZA_MAYOR_IPIRANGA_outubro_2026.xlsx`. Este último é o nome do
anexo efetivamente inventariado; variantes com sufixos devem ser identificadas
pelo hash e conteúdo, sem presumir equivalência pelo nome.

- [ ] Conferir versão, SHA/tamanho, abas e período de cada arquivo, separadamente.
- [ ] Registrar que é resultado esperado para comparação, não gabarito absoluto.
- [ ] Conferir vínculos explícitos de linha → unidade/boletos/titular e seus hashes.
- [ ] Distinguir diferenças de extração, cadastro, regra e representação; não alterar
      a fonte ou a regra para obter coincidência com a referência.
- [ ] Declarar o significado de agrupamentos e valores, data de referência e
      política de cadastro antecipado usada pelo autor da planilha, se comprovados.
- [ ] Distinguir a política histórica da referência da nova escolha universal A/B;
      modo não escolhido nesta ficha. Não exigir prazo judicial como filtro nem
      alterar a referência para fazê-la concordar com os novos requisitos.
- [ ] Preservar como evidências separadas as células que originaram os conflitos FL.
- [ ] Conferir as 30 colunas na ordem original e o cabeçalho literal `CPF`, aceitando
      CPF/CNPJ válido como texto com zeros; não aprovar aqui a importação integral.
- [ ] Registrar responsável pela referência, limitações e evidência privada.

## Régua e evidências complementares esperadas

O extrato autorizado vigente da Régua de Cobrança ainda precisa ser identificado
e vinculado nesta preparação. A referência histórica a uma régua de 20/10/2026
não comprova que sua versão atual foi disponibilizada e homologada neste conjunto.

- [ ] Indicar a versão aplicável a cada condomínio, hash, vigência documental,
      responsável e localização privada do extrato autorizado.
- [ ] Separar requisitos financeiros de acesso, credenciais e observações administrativas;
      não copiar a régua bruta para o Git nem interpretar seu texto automaticamente.
- [ ] Vincular as condições extrajudiciais aplicáveis à régua revisada e às respostas
      do responsável; prioridades/vigências reais continuam pendentes. Preservar
      os oito IDs históricos, registrando a retirada do filtro judicial e a
      substituição do cadastro particular pela opção universal do processamento.
- [ ] Validar documentalmente o reconhecimento de A/AJ/J no campo próprio TREE,
      cujo efeito de exclusão da cota/componentes já foi confirmado pelo negócio.
      Esta ficha não aprova tecnicamente planos nem atesta automaticamente fontes. Não exigir
      documentos de garantidora/status jurídico como pré-requisitos autônomos do
      seletor; não criar filtro judicial de 60/90 dias ou exclusão por garantidora.
      Preservar evidências históricas e bloqueios críticos sem apagá-los.
- [ ] Identificar eventual esclarecimento/retificação Habita/VG e provas de
      titularidade/documentos FL. Apenas disponibilizá-los não retira os bloqueios.

## Conclusão por conjunto e relação com o contrato existente

| Campo do atesto existente | Evidência humana necessária antes de registrar |
|---|---|
| `em` | Instante explícito, com fuso, da manifestação responsável |
| `data_ref` | Data de referência escolhida expressamente para o conjunto; nunca usar a data atual por omissão |
| `fundamento` / `evidencia_id` | Conclusão e vínculo ao dossiê privado com as fichas e limitações |
| `inventario_conferido` | Conferência dos registros e vínculos que compõem o candidato exato |
| `fontes_e_paginas_conferidas` | Conferência das fontes, versões, hashes e sua cobertura |
| `catalogos_externos_completos` | Conferência dos quatro catálogos e demais impedimentos conhecidos |
| `ausencias_conferidas` | Conferência explícita de campos ausentes, sem supri-los ou ignorar seus efeitos |

Não há valores preenchidos/aprovados neste modelo. Os quatro indicadores do
contrato só podem ser afirmativos depois da revisão humana que os fundamenta.
O responsável efetivo do registro vem da credencial autorizada e da política
auditável, não de um nome livre inserido no JSON. O vínculo da identidade do
responsável à política autorizada precisa ser registrado; o ator automático da
assinatura técnica não é o aprovador humano. O responsável pelo projeto pode exercer os três papéis,
mas deve registrar cada manifestação independente com fundamento e data/hora.
O modo A/B futuro deve constar no histórico/auditoria do processamento; esta
revisão não adiciona esse campo ao contrato histórico do atesto nem emite atestos.

Registrar nova versão/ID do pacote conforme o fluxo existente, sem sobrescrever
1.0 ou 1.1 anteriores. Qualquer mudança de fonte, inventário, evidência ou data de
referência exige reconferência e novo vínculo. Isso não autoriza aprovar planos,
ativá-los, simular regras reais ou exportar cobranças nesta tarefa.
