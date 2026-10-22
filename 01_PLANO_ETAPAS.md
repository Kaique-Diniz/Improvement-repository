# 01 — Plano do projeto e fases

## Situação posterior — incremento 4.3B.1

Implementação autorizada exclusivamente com dados sintéticos: cinco condições
TREE usando o motor 4.2 existente e projeção universal A/B sem XLSX.
Regressão: **1.027 aprovados**, incluindo os 943 anteriores. O
[relatório do incremento](docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md) registra os
contratos aditivos, a restrição de identidade e as pendências do 4.3B.2.
Os registros abaixo de etapas preparatórias são históricos. Nenhum plano real
foi aprovado, assinado ou ativado; bloqueios continuam obrigatórios. Não houve
simulação financeira real, início da Fase 5 ou homologação para produção.

## Visão geral

**Produto:** aplicação para importação padronizada de inadimplência condominial.  
**MVP:** reconhecer e converter com segurança os padrões iniciais Habita/TREE MORUMBI e FL/PLAZA MAYOR IPIRANGA, mantendo capacidade de expansão para centenas de administradoras e formatos.  
**Armazenamento inicial:** JSON para catálogos/configuração e histórico controlado; migração futura a PostgreSQL.  
**Modelo único de saída:** arquivo XLSX com aba `Dados` e 30 colunas fixas do template Plaza Mayor.

## Marcos / fases

| Fase | Escopo | Entregáveis verificáveis | Critério para avançar |
|---|---|---|---|
| 0 — Preparação | Validar especificação, acesso seguro às fontes, prioridades e decisões em aberto | Repositório privado, documentação, exemplos sintéticos, plano de testes | Nenhum dado sensível comitado; questões bloqueantes identificadas |
| 1 — Fundação | Domínio, JSON, schemas, versionamento, testes, CLI inicial | Módulos independentes para administradora, formato, condomínio, regra, template e execução; CRUD/configs básicas; suíte pytest | Testes de contratos e relações aprovados |
| 2 — Reconhecimento | Classificar tipo, administradora, layout e condomínio; avaliar confiança e ambiguidades | Serviço de reconhecimento; catálogo de assinaturas de layout; fallback de formato desconhecido | Nunca selecionar formato incorreto silenciosamente |
| 3 — Leitores | Adaptadores de documento e normalização para Habita, FL e Cadastro Geral; XLSX por bloco opcional | Extratores independentes; objetos canônicos; localização de origem por arquivo/página/linha | Quebras de página e somatórios verificados em amostras reais |
| 4 — Motor de cobrança | Regras por condomínio, versões, prioridade, ação por unidade/boleto; data de referência | Validador de regras; condições estruturadas; rejeição/alerta; modo simulação | Testes da régua aprovados; decisões críticas não inferidas de texto livre |
| 5 — Excel e auditoria | Exportador universal XLSX + arquivos de auditoria | Aba `Dados` com 30 colunas; linhas com/sem dívida; relatórios de exclusões e alertas | Arquivo aceito pelo importador de destino em testes controlados |
| 6 — Interface e workflow | Upload, reconhecimento, execução automática, download e dashboard | Interface web ou equivalente; estados de trabalho; relatório de falhas | Fluxo ponta a ponta aprovado, sem confirmação nos casos confiáveis |
| 7 — Ampliação | Novo formato, novos condomínios, reconhecimento melhorado e monitoramento | Cadastro de formatos, testes de regressão, métricas de qualidade | Crescimento sem modificar o núcleo de regras a cada condomínio |
| 8 — Evolução | PostgreSQL, lotes multi-condomínio, observabilidade e robustez | Camada de repositório SQL, migrações, performance, backups | Migração sem mudar contrato nem decisões de negócio |

## Entrega incremental ao Codex

### Estado autorizado após o aceite dos leitores

Fase 3 tecnicamente encerrada pelo responsável, com 458 testes aprovados, 884
boletos reconciliados e 132 correspondências financeiras. As ressalvas e os
bloqueios operacionais de lote/unidade/cadastro continuam obrigatórios; não há
homologação para produção. Ver [aceite técnico](docs/ACEITE_TECNICO_FASE3.md).
O incremento 4.1 da Fase 4 foi aprovado e implementado: contratos, schemas e
persistência de planos/aprovações, sem avaliação de boletos. Consulte o
[relatório do incremento](docs/INCREMENTO_4_1_PLANOS_E_APROVACOES.md).
Após o aceite técnico do 4.1 (595 testes), o incremento 4.2 foi autorizado e
implementado para revisão: avaliação determinística e relatórios somente de
simulação. Ver [entrega e limites](docs/INCREMENTO_4_2_AVALIADOR_DETERMINISTICO.md).
O 4.2 foi aceito tecnicamente com 716 testes. Foi autorizado exclusivamente o
4.3A: preparação da homologação, com inventário de entradas/bloqueios, persistência
privada, reprodução e comparação, sem regras reais. Veja a
[entrega e matriz preliminar](docs/INCREMENTO_4_3A_PREPARACAO_HOMOLOGACAO.md).
A etapa corretiva das duas colisões FL preserva os IDs históricos e acrescenta
reconciliação de auditoria, identificação documental v2 e preparação técnica
assinada. Veja [causa e evidências de preservação](docs/CORRECAO_IDENTIDADES_AUDITORIA_4_3A.md).
O 4.3B depende de autorização própria e das decisões documentadas. Sem Fase 5
e sem homologação para produção.

O responsável aceitou tecnicamente a correção do 4.3A com 872 testes e autorizou
exclusivamente a preparação documental seguinte. O
[relatório de prontidão documental](docs/PRONTIDAO_DOCUMENTAL_FASE4_3B.md) contém
conferência privada, checklist de atesto, matriz das oito propostas e perguntas
de decisão. Não foram configurados, aprovados ou ativados planos reais. O 4.3B
efetivo continua aguardando os atestos, decisões e autorização posterior.

Os [requisitos extrajudiciais esclarecidos posteriormente](docs/ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md)
foram incorporados somente à documentação/matriz/proposta: centavo por cota,
prazo estrito em dias corridos, retirada de filtros judiciais e de exclusão
autônoma por garantidora, cadastro universal A/B e papéis acumuláveis com atos
separados. Não houve implementação do 4.3B, aprovação/ativação de planos nem
atestos automáticos. A decisão específica posterior para TREE confirmou A/AJ/J
como exclusões da cota/componentes, suficientes isoladamente e independentes do
vencimento, sem afetar automaticamente outras cotas. Prioridades, vigências,
mapeamento dos campos e vínculo à régua continuam pendentes de validação técnica
e formalização, preservando todos os bloqueios operacionais.

A validação técnica preparatória posterior conferiu o
[mapeamento no PDF TREE autorizado](docs/MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md),
sem execução de regras reais. Original integral, encargos e apontamentos dos 769
boletos batem com a fonte e o canônico preservado. Isso supera a pendência de
mapeamento técnico **neste arquivo**, sem substituir atesto humano, aprovação de
plano ou autorização para iniciar o motor real/4.3B efetivo. Testes novos são
sintéticos; leitores e bloqueios existentes permanecem inalterados.

O mapeamento foi aceito tecnicamente com 915 testes. A conferência preparatória
seguinte distingue presença, vazio validado e inconclusão para todos os 769
boletos, com evidências privadas e fichas individuais ainda não aprovadas. Ver
[cobertura e prontidão](docs/COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md). Não
implementa planos reais, não gera aprovação/atesto e não inicia o 4.3B efetivo
ou Fase 5; bloqueios anteriores mantidos.

**Primeira tarefa:** desenvolver somente a Fase 1. Não pedir numa única execução: leitor de centenas de layouts + frontend + regra complexa + implantação.  
**Segunda:** reconhecimento (Fase 2) usando PDFs sintéticos e reais previamente sanitizados/autorizados.  
**Terceira:** leitores de Habita e FL (Fase 3).  
**Quarta:** motor de regras (Fase 4).  
**Quinta:** saída Excel e auditoria (Fase 5), seguida de UI (Fase 6).

## Condições para declarar MVP concluído

1. Consegue reconhecer Habita/TREE e FL/Plaza quando padrões são válidos.
2. Formatos não reconhecidos, ambiguidades e erros estruturais são bloqueados sem inventar dados.
3. Consegue cruzar inadimplência e Cadastro Geral por condomínio + torre/bloco + unidade.
4. Reconstrói boletos e unidades em quebras de página, sem duplos lançamentos.
5. Aplica cobrança com data de referência explícita, regras por condomínio e escopo correto.
6. Diferencia registros de dívida de cadastros antecipados.
7. Gera XLSX com exatas 30 colunas e relatório de auditoria.
8. A coluna literal CPF aceita CPF/CNPJ válido do titular como texto; ausência/invalidade -> vazio e alerta; documentos válidos conflitantes exigem revisão humana auditada.
9. Não expõe credenciais da régua, nem logs com dados pessoais desnecessários.
10. Teste de importação no **sistema de destino** aprovado em ambiente de homologação.

## Fora do escopo da primeira versão

- Leitores para todas as administradoras existentes sem exemplos de documentos.
- OCR universal com precisão garantida.
- Automação de login ou acesso às páginas das administradoras.
- Envio real de cobranças, mensagens, notificações ou ações judiciais.
- Integração direta com o sistema de destino (exportar arquivos primeiro).
- PostgreSQL, multi-inquilino complexo, IA autônoma para aprovar regras de cobrança.
