# Expansão BBZ — preparação do NOVA YORK PENTHOUSES

## Escopo e estado verificável

Pedido de 27/10/2026: primeira extensão funcional somente para NOVA YORK
PENTHOUSES. O MVP TREE/Habita e PLAZA/FL foi declarado concluído pelo responsável;
isso não homologa produção nem habilita importação no easyCollector. Os quatro
outros condomínios BBZ ficam exclusivamente no levantamento de pendências.

**Estado desta entrega: preparação; implementação BBZ bloqueada pelas fontes.**
Foram conferidos os nomes dos documentos disponíveis na área privada de
validação e no workspace, inclusive nomes codificados em URL. Os quatro
originais solicitados não foram localizados. O arquivo recebido contém o pedido,
sem os relatórios financeiros, cadastro, template ou régua atualizada.
Não foi registrada assinatura de formato, perfil de identidade validado ou
regra executável BBZ. Nenhum arquivo com nome parecido será presumido equivalente.

| Fonte solicitada | Situação | Efeito da ausência |
|---|---|---|
| `884 - NOVA YORK PENTHOUSES -Inadimplentes.xlsx` | Ausente | Impede mapear células, reconhecer assinatura e reconciliar recibos/componentes. |
| `884 - NOVA YORK PENTHOUSES - Cadastro.pdf` | Ausente | Cadastro completo é opcional nesta etapa; falta conferir a identidade e os dados da fonte, quando necessários. |
| `884 - NOVA YORK PENTHOUSES - Template.xlsx` | Ausente | Impede verificar a correspondência das 26 dívidas e as duplicações cadastrais históricas. |
| `REGUA DE COBRANÇA -26.10.2026 ATUAL.xlsx` | Ausente | Impede vincular requisitos ao hash, versão e localização documental da régua. |

Os originais deverão ficar fora do Git, com tamanho, SHA-256 dos bytes,
papel documental e localizadores privados. Valores financeiros de referência,
quando fornecidos no pedido, permanecem somente no inventário privado e são
classificados como **informados, ainda não conferidos**. Não são evidência de
reconciliação pelo sistema.

## Pontos existentes e extensão mínima proposta

Esta seção é uma proposta de implementação, não um cadastro de plugins ativos.

| Responsabilidade | Reuso existente | Extensão necessária após receber as fontes |
|---|---|---|
| Sondagem segura | `adapters/document_probe.py`: XLSX, limites ZIP/XML, bloqueio de macros/links externos e detecção de fórmulas | Manter o sondador e inspecionar estrutura/células reais; não identificar pelo nome da aba ou do arquivo. |
| Reconhecimento | `application/recognition.py`, contratos de classificação e catálogo de assinaturas | Assinatura BBZ composta por cabeçalhos, relações de colunas e estrutura de agrupamentos comprovados. Conhecido validado, desconhecido e ambíguo continuam distintos. |
| Identidade | Catálogo separa administradora, condomínio, formato e vínculos | Perfil NOVA YORK baseado nas evidências internas. `884` é o código informado do arquivo; `287` é o código administrativo informado. CNPJ, cliente, bloco, unidade e recibo são identificadores separados. Não inferir códigos dos outros quatro condomínios. |
| Leitura | Protocolo `Leitor`, `FonteProtegida`, repositório de fontes e `LoteCanonico` | Adaptador XLSX por família BBZ, registrado por leitor/versão, sem copiar leitores PDF nem criar um motor financeiro. |
| Contexto operacional | `readers/operational.py` e `application/reading.py` | Acrescentar caminho específico XLSX: os caminhos atuais exigem PDF textual e origem com página. Não afrouxar essas verificações dos PDFs. |
| Proveniência | `Origem`, hash, linha, identificador e ressalvas | XLSX com aba, linha, célula e valores originais no dossiê privado. Usar identificadores de localização estáveis; não inventar página PDF para planilha. Verificar compatibilidade sem reescrever contratos históricos. |
| Reconciliação | `Composicao` exige soma exata dos itens; `Boleto` separa multa, juros e correção | Conferir componentes, original/atualizado do recibo, unidade e relatório separadamente. Registrar total atualizado na auditoria sem trocar o original exportável. |
| Regras | Motor determinístico existente, planos versionados e fatos tipados | Configuração específica NOVA YORK, somente diagnóstica. Nenhuma regra de centavo/A/AJ/J do TREE é herdada. Judicial não vira condição adicional de seleção. |
| Comparação e saída | Comparador, projeção A/B, escritor universal e numeração existentes | Um recibo corresponde a uma dívida; confrontar unidade, vencimento e original. Preservar `Dados`, 30 cabeçalhos sem espaços finais, textos com zeros e parcelas por contrato. |
| Endereço e interface | Cadastro privado autenticado por administradora + condomínio | Incorporar apenas o novo perfil comprovado; endereço cadastrado tem prioridade em todas as linhas e complemento continua individual. Upload XLSX será habilitado somente com reconhecimento e leitor seguros. |

Não se implementa agora um framework genérico de plugins. O desenho permite
acrescentar famílias de PDF, XLSX e futuros XLS por adaptadores, preservando os
contratos e o núcleo de regras. Nem palavras soltas, nome de arquivo, nome de aba
ou pontuação de confiança isolada bastam para liberar o diagnóstico.

## Mapeamento e condições que faltam comprovar

1. Obter e preservar os quatro originais; inventariar hashes/tamanhos antes de ler.
2. Localizar identificação administrativa e fiscal, período de emissão,
   agrupamentos bloco/unidade, cabeçalhos de recibo e totalizações.
3. Comprovar quais células representam valor original, principal, multa,
   correção, juros e total atualizado. Não tratar rótulos como sinônimos sem
   reconciliação. Não somar novamente subtotais ou saldos acumulados.
4. Usar Decimal com centavos exatos. A representação numérica do XLSX deve ser
   validada antes de entrar no domínio; não fazer aritmética financeira com
   float nem corrigir diferenças por arredondamento silencioso. Fórmulas e
   caches insuficientes exigem tratamento explícito, sem executar fórmulas.
5. Preservar componentes negativos, zero e centavo. Recibo, componentes e
   marcadores têm localizadores separados, estáveis e auditáveis. Recibo
   repetido ou cabeçalho ambíguo exige revisão, não fusão automática.
6. Preservar A/AJ/J/AE em namespace BBZ, nos campos apropriados. Legendas,
   nomes, observações e restrições de outro jurídico não viram filtros por
   aproximação. Não inferir competência ausente.
7. Confirmar a fronteira dos 60 dias: `> 60` ou `>= 60`. Até essa decisão,
   o prazo está incompleto e não pode autorizar seleção. Data de referência
   do teste: **2026-10-26**, explícita e independente da data atual.
8. Conferir a versão/hash da régua e sua aplicabilidade/vigência. A data nominal
   26/10/2026 não será assumida como início de vigência. Não produzir aprovação,
   atesto, assinatura ou ativação automática.

As quantidades abaixo são expectativas fornecidas pelo responsável, ainda não
medidas nesta execução: sete unidades, 29 recibos e 26 correspondências
financeiras com o template. Os três adicionais, seus vencimentos e seus totais
precisam ser conferidos célula a célula. Coerência aritmética dos números do
pedido não substitui reconciliação documental.

Modo A: uma linha por recibo elegível. Modo B: as mesmas dívidas e no máximo uma
linha cadastral por unidade com recibo não elegível, com Y:AD vazias e bloqueios
preservados. As sete linhas cadastrais históricas em cinco unidades, incluindo
repetição de uma unidade, não serão copiadas automaticamente. Se as fontes
confirmarem apenas duas unidades com recibos fora do prazo, essa será a base da
projeção B; não haverá ajuste para forçar 33 linhas.

## Levantamento dos demais condomínios — não implementado

Dados e prazos informados no pedido, sem conferência dos originais. Os códigos
abaixo são referências dos arquivos, não mapeamentos administrativos aprovados.
Limites de prazo permanecem sem operador inclusivo/exclusivo presumido. Os
prazos judiciais são informação documental, não autorização ou filtro extra.

| Condomínio / referência | Extrajudicial / judicial informados | Pendências futuras |
|---|---|---|
| 363 — INNOVA BLUE | 31 / 90 dias | 108 unidades, 645 recibos; histórico com 639 dívidas e seis cadastros; seis recibos com original zero; bloco INAT versus 0 na unidade alfanumérica citada no pedido, afetando dois recibos; A/AJ/J/AE e componentes negativos. Não escolher correspondência de bloco automaticamente. |
| 567 — EDIFÍCIO WIN | 31 / 61 dias | 45 unidades, 672 recibos; históricos desde 2016; centavos, restrições de outro jurídico e vagas; template XLS legado ainda não validado. |
| 696 — NOVA REBOUÇAS | 30 / 90 dias | 12 unidades, 102 recibos; cadastro de 2025; distinguir proprietário, locatário e pagador; marcadores J/A; template XLS legado. |
| 788 — JARDINS DO BRASIL ABROLHOS | 60 / 90 dias | 90 unidades, 216 recibos; histórico com 103 dívidas e 25 contratos; auditar não selecionados; o arquivo chamado Cadastro.xlsx teria estrutura financeira; reconhecer o subconjunto ABROLHOS por conteúdo, sem misturar outros JARDINS DO BRASIL. |
| 884 — NOVA YORK PENTHOUSES | 60 / 90 dias | Cadastro anterior ao financeiro; divergência na quantidade total de unidades entre cadastro e régua; duplicação cadastral no histórico; identidade fiscal e códigos pendentes de comprovação. |

Não incluir credenciais, contatos internos nem observações administrativas da
régua em configuração pública. Fontes reais e relatórios de comparação nominal
ou financeira permanecem privados.

## Sequência de implementação e aceite ainda pendente

1. **Fontes/assinatura:** inventário, identidade, mapeamento e convenção dos 60
   dias; assinatura forte com rejeição de administradora/condomínio incorretos.
2. **Leitor BBZ financeiro:** unidades → recibos → componentes, marcadores,
   datas e origens; reconciliação exata em todos os níveis disponíveis.
3. **Integração diagnóstica NOVA YORK:** configuração e motor existentes;
   comparação das 26 dívidas, auditoria dos três excluídos e projeção A/B.
4. **Testes sintéticos derivados da estrutura comprovada:** múltiplos
   componentes, negativos/zeros/centavos, A/AJ/J/AE, unidades alfanuméricas,
   duplicidades, cabeçalhos ambíguos, subtotais, datas antigas e atuais,
   condomínio desconhecido, bloqueios e formatos inválidos. Testar as duas
   bordas do prazo aprovado e impedir propagação de regras TREE/PLAZA.
5. **Validação privada:** confrontar sete unidades/29 recibos, todos os totais,
   26 correspondências, as diferenças históricas de B e a saída textual de
   CPF/CNPJ, CEP, DDD e FONE. Não preencher ausências com dados inventados.
6. **Regressão e revisão:** preservar TREE/PLAZA, cadastros persistentes,
   privacidade, auditoria e bloqueio de exportação operacional. Sem push/merge
   até autorização própria.

### Etapa seguinte proposta — Cadastro Geral PDF

Somente após autorização posterior: inspecionar assinatura, colunas e continuidade
do cadastro BBZ; separar papéis e nomes; validar CPF/CNPJ e contatos opcionais;
cruzar administradora + condomínio + bloco + unidade; registrar data da fonte,
divergências e conflitos válidos sem escolher titular silenciosamente. Confirmar
quantidade de unidades versus régua e acoplar pelo enriquecimento existente.
Adicionar testes sintéticos e privados, sem implementar os outros condomínios.

Os critérios funcionais NOVA YORK continuam **não executados**, por falta dos
originais. Testes da base atual atestam somente preservação do MVP, não
reconhecimento BBZ ou homologação do novo formato. A etapa seguinte não foi
iniciada, e o sistema permanece exclusivamente diagnóstico e não homologado para
produção.

Regressão executada nesta preparação: **1.369 testes aprovados** (1.309 regulares
+ 60 das suítes explícitas), oito verificações de schemas aprovadas. Nenhum teste
BBZ foi criado a partir de um layout presumido. Código, catálogos e regras
executáveis permanecem intactos.
