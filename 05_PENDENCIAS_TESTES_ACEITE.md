# 05 — Pendências, decisões e plano de testes

**Situação atual — 4.3B.1:** implementado exclusivamente com dados sintéticos,
com **1.027 testes aprovados** (943 anteriores + 84 novos), sete conferências de
schemas e nenhuma execução sobre dados privados. Cinco condições TREE reutilizam
o motor existente; A/B permanece no nível de decisões estruturadas. CPF/CNPJ
inválido exige revisão nesse novo fluxo, mantendo ausência como alerta. Veja
[testes, bloqueios e pendências](docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md).
Planos reais, atestos, prioridades/vigências reais e autorização do 4.3B.2
continuam pendentes. Bloqueios de lote/unidade/cadastro preservados. Sem Fase 5
ou homologação de produção. Os parágrafos de preparação abaixo são históricos.

**Preparação de 22/10/2026:** a correção do 4.3A foi aceita tecnicamente com
872 testes. A etapa atual é exclusivamente documental: confira o
[checklist de atesto humano](docs/ATESTO_HUMANO_FONTES_FASE4_3B.md), a
[matriz das oito propostas](docs/MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md) e as
[perguntas para decisão](docs/DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md).
Os cenários particulares de regra abaixo são material de levantamento/teste,
sem plano real aprovado por essa descrição. A identificação de uma fonte de régua
não equivale à aprovação de todas as interpretações do seu conteúdo. Atestos,
prioridades e vigências reais continuam pendentes; à época o 4.3B não havia iniciado.

Os [esclarecimentos extrajudiciais posteriores](docs/ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md)
definiram centavo por cota, contagem estrita em dias corridos, ausência de filtros
judiciais/garantidora e modo universal A/B. São requisitos documentados, ainda
sem implementação nova, plano real aprovado ou atesto emitido.

A [validação técnica preparatória TREE posterior](docs/MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md)
conferiu o mapeamento de Valor e A/AJ/J no PDF autorizado e adicionou testes
sintéticos de leitor/predicados. Não executou regras reais nem modificou o motor.
Atestos e aprovação de planos continuam pendentes; subtotal VG permanece crítico.

## Decisões aprovadas

- JSON agora, PostgreSQL depois.
- Administradora -> muitos condomínios; condomínio -> uma administradora atual.
- Reconhecimento e processamento automático para formato conhecido **sem confirmação**.
- Segurança bloqueia inconsistências críticas; alertas não bloqueantes para CPF ausente.
- A coluna literal CPF aceita CPF/CNPJ válido do titular, como texto. Dois documentos válidos distintos ou associação não confirmada exigem revisão humana, com bloqueio e evidências preservadas.
- Template universal Plaza Mayor de 30 colunas; linhas cadastrais sem contrato/dívida.
- Régua de cobrança geral: referência histórica `REGUA DE COBRANÇA -20.10.2026 ATUALIZADA.xlsx`; identificar e atestar versão aplicável por condomínio antes de aprovar o plano real.
- Cadastro antecipado universal por processamento, modos A/B explícitos, sem default; histórico/auditoria registram a escolha. Não é política exclusiva do condomínio.
- Prazo extrajudicial aprovado de 30 significa `> 30` dias corridos, referência explícita; outros prazos dependem de cada plano. Prazos judiciais de 60/90 não filtram o Excel.
- Centavo, quando previsto na régua, usa Valor validado e exclui só cota/componentes independentemente do vencimento; sem exclusão autônoma por garantidora.
- Mesma identidade autorizada pode acumular Administrador, Revisor e Operador; atos, aprovações e atestos separados, nunca automáticos.
- Mudanças de regra somente em versão revisada/aprovada.

## Pendências que podem ser decididas sem impedir Fase 1

| ID | Pergunta | Proposta para MVP | Quando decidir |
|---|---|---|---|
| P01 | Uma execução aceita vários condomínios? | Um por execução; múltiplos anexos do mesmo condomínio | Antes da interface |
| P02 | Data de referência para prazo da régua? | Explícita por execução, sem assumir data atual; dias corridos, `>30` quando a régua determinar 30; valor concreto pendente | Antes de cada avaliação |
| P03 | Novos formatos podem ser criados pela operação? | Inicialmente técnico/config JSON; futuro assistente visual | Antes da fase 7 |
| P04 | CPF de empresa/único CNPJ, proprietário múltiplo, titular divergente? | CPF/CNPJ válido como texto; ausência/invalidade -> vazio + alerta; conflito/vínculo pendente -> revisão humana auditada | Antes da homologação de cadastros |
| P05 | Alterações entre cadastro geral e inadimplência com datas distintas? | Gerar ocorrência, não substituir automaticamente titular | Antes da fase 3 |
| P06 | Cabeçalho `NM_DIVIDA_CEDENTE ` com espaço final? | Compatibilidade fiel ao arquivo-base até teste contra importador | Antes da fase 5 |
| P07 | Modalidade judicial e exceções específicas: importação vs negociação? | Definido: prazos judiciais não filtram o Excel; medidas posteriores cabem ao CRM. TREE: A/AJ/J excluem cota/componentes independentemente do vencimento, sem excluir outras cotas | Não exigir marcos de 60/90; validar campos próprios e vínculo à cota antes de configurar |
| P08 | Quais casos devem bloquear lote todo vs somente registro? | Matriz explícita com tipo/severidade/escopo | Antes da fase 4 |
| P09 | Política de retenção e acesso a PDFs/CPFs? | Pasta temporária protegida com prazo definido, sem salvar conteúdo em logs | Antes da produção |
| P10 | Saída TREE MORUMBI de referência? | Criar fixture/gabarito aprovado com resultados esperados a partir do PDF; sem XLSX dourado confirmado na conversa | Antes dos testes finais |
| P11 | Qual stack e ambiente? | Python + testes; FastAPI/React opcionais a validar | Antes da UI |
| P12 | easyCollector: demais campos, vazios, duplicados, valores e datas em quais tipos? | CPF/CNPJ na coluna CPF confirmado pelo responsável em 21/10/2026; homologar importação integral controlada | **Bloqueante para produção** |

## Matriz mínima de testes

### Reconhecimento
- Habita/TREE reconhecido pelo conteúdo e layout; FL/PMI reconhecido por assinatura; rejeitar documento sem correspondência segura.
- Mesmo formato em outro condomínio não usar perfil errado.
- Formato desconhecido não é silenciosamente processado.

### Leitura
- Habita: 149 páginas, campos no cabeçalho, composição; apontamento no boleto; reconciliação de unidade.
- FL: 24 páginas, unidades TORRE A–G, 'Valor' por linha de composição e 'Saldo' cumulativo; notas entre boletos.
- Várias páginas: boleto e unidade continuam na página seguinte; **não duplicar**.
- Caso `BLDEP-UNI0040`: continuação de página não deve ser contada como novo boleto (histórico da conversa indicou 22, não 23).
- Comparar extração com XLSX blocos A–G, quando aplicável.

### Regras — critérios revisados para implementação/homologação posterior
- TREE: centavo no campo Valor validado **OU A OU AJ OU J** comprovado em campo próprio exclui só a cota inteira/componentes, independentemente do vencimento; uma condição basta e outras cotas seguem avaliação normal. Escopo/efeito confirmados pelo negócio, sem ativação. Valores e todas as evidências preservados.
- Validar mapeamento do Valor confirmado como valor do boleto, distinguindo componentes, multas, juros e totais. Testar cada exclusão isolada, coexistência de gatilhos, cotas futuras, dia 30/31 e preservação das demais cotas; rejeitar ocorrências de A/AJ/J somente em legendas, observações ou descrições. São critérios documentais para testes de implementação futura, sem leitura real nesta tarefa.
- TREE/FL: quando a régua extrajudicial determinar 30, dias 29/30 não satisfazem e 31 satisfaz apenas o prazo, em dias corridos sob referência explícita; não criar padrão global para outros condomínios.
- Sem filtros judiciais de 60/90 e sem exclusão autônoma por garantidora; associação isolada não muda elegibilidade.
- Universal A/B: uma linha cadastral adicional no máximo por unidade com cota não elegível no modo B, coexistência com dívida elegível permitida, Y:AD vazias, sem importar todo Cadastro Geral ou contornar críticos; modo registrado em histórico/auditoria.
- Mesma identidade em três papéis: manifestações independentes; nunca aprovação/atesto automáticos. Os testes destes novos comportamentos dependerão da implementação autorizada posteriormente.
- Apontamento J em Habita não é automaticamente o mesmo que anotação 'Jurídico' em FL.
- Toda exclusão deve registrar condição, regra/versionamento e evidência.

### Contrato de saída
- 30 cabeçalhos exatos, ordem A:AD, aba Dados.
- CPF/CNPJ válido -> texto com zeros na coluna CPF; ausente/inválido -> vazio e alerta. Conflito de documentos válidos ou titular não confirmado -> bloqueio do cadastro e revisão humana; fontes na auditoria protegida.
- Linhas cadastrais com Y:AD vazias; linhas de cobrança com data/valor corretos.
- Zeros iniciais preservados em CPF/CNPJ/CEP/códigos quando presentes. CPF/CNPJ nunca numéricos; validar roundtrip e importador autorizado.
- Reprocessar mesmas fontes/config/data produz saída determinística, sem duplicação.
- Plaza Mayor: 112 linhas de referência (69 com dívida, 43 cadastrais, 47 cedentes distintos) **somente como gabarito de comparação condicionado à mesma data/política/versões**; não copiar números para todas as execuções.

### Segurança
- Nenhuma senha/token/login da régua aparece no código, fixtures, relatório de saída ou log.
- Não incluir CPFs reais em repositório público.
- Possibilidade de auditar processamento sem expor o documento integral.

## Critério de aceite por fase
Teste automatizado verde + comparação amostral manual com fonte e registros de exceção + documentação de riscos/pontos não atendidos. Cada fase deve ter demonstrativo curto de como executá-la.

## Revisão técnica dos leitores reais — 21/10/2026

As três leituras operacionais passaram e o inventário financeiro foi confrontado
sem divergências. Permanecem pendentes subtotal de bloco inconsistente da Habita,
titularidade múltipla/divergente, dois conflitos de CPF contra referência e
completude de competência/endereço para futura exportação. A nova aceitação de
CPF/CNPJ como texto continua vigente. Os 382 testes anteriores e 50 novos
passaram (432 ao todo); isso não equivale à homologação para produção.

### Revisão final das pendências

Os 432 testes anteriores e 26 novos passaram (458). Foram preservados os 884
boletos e as 132 correspondências financeiras. O subtotal VG repete o total geral
na própria fonte: bloqueio do lote mantido. As 34 unidades FL foram analisadas
individualmente, sem troca automática de titular; os dois conflitos de CPF (duas
ocorrências em uma unidade) seguem retidos, sem vigência documental comprovada.
Foram segmentados 389 endereços; um cadastro com dois endereços permanece bloqueado.
Competências Habita continuam ausentes, com alerta e impedimento de exportação
quando exigidas; não houve inferência pelo vencimento. Consulte a classificação
completa e a recomendação de encerramento técnico, com bloqueios preservados,
em [Aceite técnico da Fase 3](docs/ACEITE_TECNICO_FASE3.md).
Na época da revisão final da Fase 3, a Fase 4 ainda não havia sido iniciada.
O estado posterior está na atualização no início deste documento; o sistema
continua sem homologação para produção.
