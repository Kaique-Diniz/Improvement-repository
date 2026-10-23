# 02 — Especificação funcional e arquitetural

## 1. Problema
Administradoras fornecem relatórios heterogêneos. Uma conversão ingênua poderia confundir saldos acumulados com valor do boleto, duplicar lançamentos entre páginas, associar unidade a bloco errado ou descumprir exceções da régua.

O conversor seleciona cotas elegíveis pela régua **extrajudicial**, organiza os
dados e gera Excel para importação no easyCollector. A análise posterior das
medidas de cobrança cabe ao CRM. Prazos judiciais não são filtros adicionais
de seleção. Requisitos revistos em 22/10/2026, somente na documentação; veja
[decisões e limites](docs/ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md).

## 2. Entidades e cardinalidades
- **Administradora (1:N Condomínios):** um condomínio pertence a exatamente uma administradora ativa em cada instante. Planejar histórico de mudanças de administradora sem violar associação única atual.
- **Formato (reutilizável):** assinatura de um layout e versão; poderá ter muitas administradoras relacionadas e vários condomínios compatíveis.
- **Condomínio:** unidade lógica de configuração: administradora atual, código interno, cedente, endereço, formatos aceitos, regra e template de exportação. Cadastro antecipado é opção universal do processamento, não política exclusiva do condomínio.
- **Régua/Regra:** a planilha geral é fonte textual; uma regra estruturada, versionada e **aprovada** governa o processamento. Não aplicar interpretação livre automaticamente em produção.
- **Template:** saída com 30 colunas fixas, independentemente da administradora de origem.
- **Processamento:** arquivo(s), versões de configuração, data de referência explícita, modo A/B de cadastro antecipado, alertas, resultados e trilha de auditoria. Registro do novo modo é requisito para implementação posterior.

## 3. Reconhecimento automático
1. Detectar tipo (PDF com texto, PDF escaneado, XLSX, CSV quando suportado).
2. Extrair assinaturas: cabeçalho, marcadores, nomes de campos, padrões de tabela, códigos e CNPJ do condomínio quando presente.
3. Identificar *formato/versão* por regras determinísticas e pontuação de correspondência. NÃO presumir que logotipo basta.
4. Identificar administradora e condomínio com identificadores fortes; se houver ambiguidade, bloqueio até resolução.
5. Carregar versões do perfil, da régua e do template.
6. Executar extração + validação preliminar: confiança de reconhecimento não substitui consistência financeira.
7. Se reconhecido e aprovado, **processar automaticamente sem pedir confirmação humana**. Se não, exigir resolução/configuração.

## 4. Leitura e modelo canônico
Suportar múltiplas fontes de um mesmo processamento, por exemplo: PDF de inadimplência + Cadastro Geral + XLSX por blocos. Cada adaptador retorna objetos do mesmo modelo canônico:
- condominium_id, adm_id, fonte, página/linha/posição, bloco/torre, unidade original, chave normalizada de unidade;
- pessoa/nome/documento (CPF ou CNPJ válido na coluna literal CPF), contatos/endereço, relação do cliente à unidade;
- boleto (número/código, vencimento, competência, emissão, status/apontamento, valores), composição e itens com sinal correto;
- totals por boleto, unidade, original sem acréscimos, multa, juros, correção, quando disponíveis;
- marcadores de continuidade entre páginas e justificativas de reconstrução.

Campos ausentes não são inferidos: competência pode permanecer ausente no canônico; token de emissão e descrições são preservados, com origem. A exportação bloqueia dívida cuja competência exigida não tenha fonte aprovada. Ressalvas críticas de leitura/cadastro impedem exportação automática e preservam valores brutos em auditoria privada.

Não transformar valores monetários por float binário; usar Decimal/centavos. Preservar dados brutos e referência de origem para fins de auditoria.

## 5. Regras de cobrança
Atualização aprovada para 4.1: exclusões/bloqueios de unidade prevalecem sobre os
boletos correspondentes; permissões genéricas da unidade não liberam boletos
individualmente inelegíveis. Prioridade não supera bloqueio crítico ou integridade
documental. A ativação de configuração exige aprovação autorizada da versão/hash,
não apenas um campo JSON. Os contratos e a persistência estão em
[Incremento 4.1](docs/INCREMENTO_4_1_PLANOS_E_APROVACOES.md). O
[incremento 4.2](docs/INCREMENTO_4_2_AVALIADOR_DETERMINISTICO.md) implementa avaliação
somente de simulação, com plano/versão/hash/aprovação/vigência verificados e todos
os bloqueios críticos preservados. Não autoriza cobrança nem exportação. Regras
operacionais específicas continuam dependendo de aprovação própria.

O [incremento 4.3A](docs/INCREMENTO_4_3A_PREPARACAO_HOMOLOGACAO.md) prepara
inventários revisados, catálogos completos de impedimentos, armazenamento privado
assinado, reprodução histórica e comparação diagnóstica. A ausência/carga parcial
de fonte ou bloqueio impede simular pelo fluxo privado. Um candidato ainda não
atestado não é pacote autorizado; a revisão técnica do inventário não aprova
regras financeiras. Replay histórico não equivale à validade administrativa atual.
Na [correção de integridade do 4.3A](docs/CORRECAO_IDENTIDADES_AUDITORIA_4_3A.md),
IDs internos de importação são separados por namespace/fonte/conteúdo, com vínculo
integral ao identificador e registro legados. Evidências distintas não são fundidas
ou deduplicadas pelo ID antigo. Assinatura de preparação técnica não substitui
atesto humano de completude nem aprovação de plano; contratos privados 1.0 são
preservados e pacotes reconciliados usam schema 1.1 explícito.
Após o aceite técnico dessa correção, foi preparada somente a
[documentação de revisão humana do 4.3B](docs/PRONTIDAO_DOCUMENTAL_FASE4_3B.md).
O checklist de fontes e a matriz em linguagem de negócio não emitem atestos nem
aprovam regras. Continuam necessários responsáveis, evidências e aprovação
expressa das condições, ações, prioridades e vigências antes dos planos reais.

Motor declarativo com operador (igual, contém, maior que, dias atraso), alcance (boleto, unidade, condomínio), ação (incluir, excluir, adiar, alerta, bloquear) e prioridade. Regras especiais por unidade não se limitam às políticas comuns. A contagem deve especificar se é `> N` ou `>= N` dias conforme condomínio.

Os casos abaixo incorporam os esclarecimentos do responsável na preparação do
4.3B. Requisito definido não é aprovação formal de plano. Prioridades, vigências,
vínculo à régua e atestos continuam pendentes. A atualização específica TREE
confirma A/AJ/J como exclusões da cota e componentes, sem aprovação técnica ou ativação.
Nenhuma observação administrativa ou credencial pode virar condição financeira.
As oito entradas históricas e seus novos estados estão na
[matriz revisada](docs/MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md).

### TREE MORUMBI — requisitos e pendências atuais

O [incremento técnico 4.3B.1](docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md) implementa
essas condições somente em plano demonstrativo sintético, reutilizando o motor
4.2, sem ativar planos reais. O modo universal A/B é projetado como decisões
estruturadas, sem antecipar o exportador da Fase 5. Datas/prioridades das fixtures
não constituem decisões para planos reais.

O [incremento 4.3B.2A](docs/INCREMENTO_4_3B_2A_INTEGRACAO_SINTETICA.md) integra
essas decisões sintéticas com preparação reconciliada, fonte/versão da régua,
controles de aprovação e persistência auditável. Modo e data são obrigatórios;
o ato autenticado de operador é distinto das aprovações e não emite atesto humano.
Não habilita dados reais, XLSX ou autorização operacional.

- Para TREE, o prazo extrajudicial de 30 dias está confirmado: selecionar cotas com atraso **estritamente superior a 30 dias corridos**, a partir do dia 31, em relação à data explícita. O prazo sozinho não supera centavo, A, AJ, J ou bloqueios; não há prazo universal para todos os condomínios.
- Quando existir na régua a condição de R$ 0,01, comparar exatamente o campo **Valor identificado e validado na fonte**. Excluir **somente a cota correspondente e seus componentes**, independentemente do vencimento, sem afetar automaticamente outras cotas da unidade. Documentar Valor → cota/componentes/campo canônico antes de ativar; não presumir componente, saldo ou total.
- Associação à garantidora não altera isoladamente a elegibilidade; não implementar exclusão autônoma nem duplicar a regra monetária.
- **A, AJ ou J**, comprovado em campo apropriado do relatório e associado à cota, exclui **a cota inteira e todos os componentes**, independentemente do vencimento. Uma única condição, inclusive o centavo, basta; outras cotas da unidade seguem avaliação normal. Não reconhecer apontamentos por letras em legendas, observações ou descrições nem apagar evidências da auditoria. Efeito/escopo confirmados pelo negócio; validar campo/namespace e associação nos documentos antes da configuração técnica.
- Campo **Valor confirmado como referência do valor do boleto**. O mapeamento técnico no PDF autorizado foi conferido na preparação posterior, distinguindo componentes, original integral, multas, juros, atualização e totais. Isso não altera valores nem aprova planos; novas fontes/layouts precisam de validação própria e atesto.
- Validação técnica preparatória posterior: no PDF autorizado, `Valor` por componente mapeia para `composicao.itens[].valor`; o original **integral** da cota é `Boleto.composicao.total_original`, conferido com fechamento explícito quando presente. A/AJ/J estão entre número e vencimento e usam namespace do formato do contexto. Ver [evidências e limites](docs/MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md). Essa conferência técnica não é atesto nem aprovação do plano; fontes/layouts distintos exigem nova validação. Encargos/total atualizado não substituem o original.
- O dado financeiro de exportação é o valor original totalizado do boleto (composição), sem adicionar multa/juros/correção, salvo outra regra aprovada.
- No histórico da conversa, uma contagem duplicada em `BLDEP-UNI0040` foi causada por boleto dividido entre páginas; o boleto é único.
- Registro de unidade específica em outro jurídico deve existir no perfil mesmo que não esteja presente no PDF do período, desde que confirmado na régua.

### PLAZA MAYOR IPIRANGA — requisitos e pendências atuais
- Aplicar prazo extrajudicial de 30 dias quando previsto na régua aprovada: `> 30` dias corridos, por cota, com referência explícita. **Não usar prazos judiciais de 60 ou 90 dias como filtros adicionais do Excel**; medidas posteriores cabem ao CRM.
- PDF da FL traz composição e saldos **acumulados**. Somar componentes pertencentes ao boleto; não usar `Saldo` global da unidade como valor do boleto.
- PDF de inadimplência não traz todas as informações pessoais. Buscar no Cadastro Geral por condominium + torre + unidade, respeitando a data de origem.
- Linhas cadastrais sem dívida seguem o modo universal A/B escolhido no processamento; podem coexistir com dívida elegível conforme a seção 8.
- Ausência de algumas unidades na referência manual não torna o arquivo automaticamente errado se só há parcelas fora do prazo e o cadastro antecipado é opcional.

## 6. CPF e contato
- A **coluna literal `CPF` aceita CPF válido de 11 dígitos ou CNPJ válido de 14 dígitos**, conforme atualização geral aprovada em 21/10/2026. Validar os dígitos verificadores de acordo com o tipo; não retipar documento explícito para forçar validade.
- Documento ausente ou inválido: exportar célula em branco e emitir alerta não bloqueante. Preservar valor bruto e fonte na auditoria protegida; não completar dígitos ou zeros que não constem na fonte.
- A correção funcional do MVP substitui a restrição anterior do incremento 4.3B.1: CPF/CNPJ ausente ou inválido não bloqueia a análise financeira nem o cadastro. Ausência produz aviso informativo e invalidade produz alerta, ambos com célula vazia.
- Preservar zeros à esquerda de CPF e CNPJ usando texto literal e formato `@` no Excel; nunca números. Normalizar somente pontuação permitida antes da validação.
- Telefones/e-mails opcionais. Até 5 pares DDD/FONE e 3 e-mails; não inventar.
- Cadastro por unidade pode conter vários nomes e um único CPF/CNPJ válido. Preservar os nomes no campo NOME, sem criar pessoas ou dívidas adicionais; o documento pertence ao registro da unidade, sem atribuição individual. `/` não é conflito. Dois documentos válidos distintos e conflitantes para a mesma unidade exigem revisão. Divergências de nomes entre fontes continuam em revisão quando não forem apenas nomes completos adicionais explicitamente apresentados no registro; não escolher titular silenciosamente. Cruzar sempre condomínio + torre/bloco + unidade, sem transportar documentos entre unidades.

## 7. CEDENTE e codificação de unidade
- `CEDENTE` e `NM_CONTRATO_CEDENTE` podem ter padrões específicos por condomínio; não impor universalmente `BL00-UNI0000-NOME`.
- Suportar `TORRE A`, `Bloco: DEP`, vagas e IDs alfanuméricos.
- Permitir sufixos próprios e preservar a identidade cadastral existente.
- Separar `CEDENTE`, `COMPLEMENTO` e `PRODUTO_CEDENTE` no modelo; não repetir automaticamente sufixo de cedente no complemento.
- Normalização deve ser reversível e auditável; tratar divergência de identificador como bloqueio se não for resolvível.

## 8. Linhas de saída
- Usar exatamente a estrutura descrita em `04_DICIONARIO_TEMPLATE.md`.
- Linha de dívida: dados cadastrais mais contrato, dívida, parcela, vencimento, valor.
- Linha só cadastral: campos cadastrais preenchidos quando conhecidos; 6 campos finais de contrato/dívida ficam vazios.
- Cadastro antecipado é opção **universal**, independente de administradora/condomínio, escolhida explicitamente por processamento, sem default definido: **A**, somente cotas elegíveis; **B**, cotas elegíveis e no máximo uma linha exclusivamente cadastral adicional por unidade com cotas não elegíveis. Pode coexistir dívida elegível e cadastro da mesma unidade.
- Nunca exportar cota não elegível como dívida, incluir automaticamente todo o Cadastro Geral ou usar linha cadastral para contornar bloqueio crítico de lote, unidade, titularidade ou documentos. Indeterminação relevante exige revisão, não classificação presumida como não elegível.
- Registrar modo escolhido no histórico e auditoria. Estes são requisitos documentais; implementação/projeção operacional dependem de autorização posterior, sem início da Fase 5.
- `VL_PARCELA` é valor numérico e `VENCIMENTO` é data reconhecida pelo Excel; validar com importador de destino.

## 9. Validação e bloqueios
**Informativo:** telefone ausente, e-mail ausente.  
**Alerta não bloqueante:** documento vazio/invalidado, campos cadastrais opcionais sem origem.
**Crítico, bloquear registro ou arquivo conforme contaminação:** documentos válidos conflitantes, vínculo entre registros/fontes não comprovado (múltiplos nomes isoladamente não são conflito), formato desconhecido, condomínio ambíguo, unidade ambígua, linha incompleta de boleto, soma inconsistente, duplicidade não reconciliada, campo requerido pelo destino incompatível, regra não validada.

Não deve existir exportação de cobranças com valor presumido. Dados não verificáveis permanecem pendentes e rastreados.

## 10. Auditoria
Registrar ID da execução, horário, data de referência, hashes dos arquivos, fontes, versão do leitor, regra/perfil/template, total de unidades/boletos/linhas, incluídos/excluídos/adiados, motivo específico, documento faltante/inválido/conflitante, e origem (página/linha) da decisão. Logs operacionais não incluem credenciais; anonimizar documentos pessoais quando possível.

Registrar também o modo A/B selecionado e a versão da política de processamento.
O responsável pelo projeto pode acumular Administrador, Revisor e Operador na
mesma identidade autorizada. Ações, aprovações, atestos e decisões humanas exigem
registros independentes com ator/papel, instante e fundamento. O acúmulo de papéis
não aprova plano nem atesta fontes automaticamente; vínculo da identidade e atos
formais continuam pendentes. Não há concessão de credenciais nesta atualização.

## 11. Tratamento de mudanças
- Novos formatos entram como versão rascunho e precisam de testes/aprovação.
- Atualização da régua gera *diferença* e uma proposta de nova versão por condomínio; nunca modifica silenciosamente conversão passada.
- Executar regra pela data de referência, com padrão de data ainda a confirmar para interface.
- Um condomínio possui uma administradora atual; preservar mudança de vínculo para reproduzir históricos.

## 12. Restrições e segurança
LGPD e minimização de dados; preferir repositórios privados, backups protegidos, arquivos em pasta temporária com expiração, controle de acesso, não expor CPFs completos em logs. A régua contém senhas/logins/tokens no texto de particularidades; **não incluir régua bruta no repositório, fixtures, prompt ou log público**.

## 13. Tecnologia (PROPOSTA, NÃO DECISÃO DO USUÁRIO)
Python, pytest, extratores configuráveis com bibliotecas especializadas PDF/XLSX; API opcional em FastAPI, UI web posterior; abstração de repositório para JSON -> PostgreSQL. Validar stack com usuário antes da implementação de UI/infra.

## 14. Integração documental confirmada

O responsável pelo processo confirmou em 21/10/2026 a aceitação de CPF/CNPJ
na coluna literal `CPF` pelo CRM easyCollector. Essa confirmação é requisito
geral aprovado e não equivale à homologação integral da saída Excel. Demais
campos, formatos e comportamentos de importação continuam sujeitos a ensaio
controlado; nenhuma operação real de cobrança é autorizada por esta confirmação.
