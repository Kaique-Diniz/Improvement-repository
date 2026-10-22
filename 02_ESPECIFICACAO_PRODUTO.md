# 02 — Especificação funcional e arquitetural

## 1. Problema
Administradoras fornecem relatórios heterogêneos. Uma conversão ingênua poderia confundir saldos acumulados com valor do boleto, duplicar lançamentos entre páginas, associar unidade a bloco errado ou descumprir exceções da régua.

## 2. Entidades e cardinalidades
- **Administradora (1:N Condomínios):** um condomínio pertence a exatamente uma administradora ativa em cada instante. Planejar histórico de mudanças de administradora sem violar associação única atual.
- **Formato (reutilizável):** assinatura de um layout e versão; poderá ter muitas administradoras relacionadas e vários condomínios compatíveis.
- **Condomínio:** unidade lógica de configuração: administradora atual, código interno, cedente, endereço, política de cadastro antecipado, formatos aceitos, regra e template de exportação.
- **Régua/Regra:** a planilha geral é fonte textual; uma regra estruturada, versionada e **aprovada** governa o processamento. Não aplicar interpretação livre automaticamente em produção.
- **Template:** saída com 30 colunas fixas, independentemente da administradora de origem.
- **Processamento:** arquivo(s), versões de configuração, data de referência, alertas, resultados e trilha de auditoria.

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

Os casos iniciais abaixo são material de levantamento histórico, não planos reais
aprovados/ativados. No 4.3A, os oito itens da matriz preliminar continuam sujeitos
à confirmação de semântica, escopo, ação, prioridade, vigência e evidência própria;
nenhuma observação administrativa ou credencial pode virar condição financeira.

### Caso inicial TREE MORUMBI (conforme histórico da conversa, sujeito a fixture de aceite)
- Cobrança extra de boletos com **mais de 30 dias** de vencimento à data de referência.
- Se a unidade contém qualquer boleto de R$ 0,01, **excluir a unidade inteira** da importação, inclusive boletos de valor maior.
- Se a unidade possui qualquer boleto com apontamento A, AJ ou J, **excluir a unidade inteira**.
- O dado financeiro de exportação é o valor original totalizado do boleto (composição), sem adicionar multa/juros/correção, salvo outra regra aprovada.
- No histórico da conversa, uma contagem duplicada em `BLDEP-UNI0040` foi causada por boleto dividido entre páginas; o boleto é único.
- Registro de unidade específica em outro jurídico deve existir no perfil mesmo que não esteja presente no PDF do período, desde que confirmado na régua.

### Caso inicial PLAZA MAYOR IPIRANGA
- Régua geral de 20/10/2026: cobrança extra 30 dias; judicial 60 dias. **Prazo judicial não significa exclusão automática**; modalidade e ação devem ser especificadas/validadas.
- PDF da FL traz composição e saldos **acumulados**. Somar componentes pertencentes ao boleto; não usar `Saldo` global da unidade como valor do boleto.
- PDF de inadimplência não traz todas as informações pessoais. Buscar no Cadastro Geral por condominium + torre + unidade, respeitando a data de origem.
- Linhas cadastrais sem dívida são permitidas segundo configuração do condomínio; podem coexistir com linhas de dívidas.
- Ausência de algumas unidades na referência manual não torna o arquivo automaticamente errado se só há parcelas fora do prazo e o cadastro antecipado é opcional.

## 6. CPF e contato
- A **coluna literal `CPF` aceita CPF válido de 11 dígitos ou CNPJ válido de 14 dígitos**, conforme atualização geral aprovada em 21/10/2026. Validar os dígitos verificadores de acordo com o tipo; não retipar documento explícito para forçar validade.
- Documento ausente ou inválido: exportar célula em branco e emitir alerta não bloqueante. Preservar valor bruto e fonte na auditoria protegida; não completar dígitos ou zeros que não constem na fonte.
- Preservar zeros à esquerda de CPF e CNPJ usando texto literal e formato `@` no Excel; nunca números. Normalizar somente pontuação permitida antes da validação.
- Telefones/e-mails opcionais. Até 5 pares DDD/FONE e 3 e-mails; não inventar.
- Identificações de vários titulares/corresponsáveis exigem regras claras de identificação por unidade. Unidade ou nome isolado não prova associação de documento ao titular. Não substituir automaticamente CPF por CNPJ ou vice-versa. Dois documentos válidos distintos para o mesmo titular bloqueiam resolução automática e exportação desse cadastro; encaminhar à revisão humana, com todas as evidências e fontes. Associação não confirmada também bloqueia. Não escolher fonte mais recente ou Cadastro como prioridade implícita.

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
- Cadastro antecipado é política por condomínio, não regra global. Mesmo unidade pode ter dívida elegível e linha cadastral sem dívida, caso haja requisito de destino.
- `VL_PARCELA` é valor numérico e `VENCIMENTO` é data reconhecida pelo Excel; validar com importador de destino.

## 9. Validação e bloqueios
**Informativo:** telefone ausente, e-mail ausente.  
**Alerta não bloqueante:** documento vazio/invalidado, campos cadastrais opcionais sem origem.
**Crítico, bloquear registro ou arquivo conforme contaminação:** documentos válidos conflitantes, titularidade documental não confirmada, formato desconhecido, condomínio ambíguo, unidade ambígua, linha incompleta de boleto, soma inconsistente, duplicidade não reconciliada, campo requerido pelo destino incompatível, regra não validada.

Não deve existir exportação de cobranças com valor presumido. Dados não verificáveis permanecem pendentes e rastreados.

## 10. Auditoria
Registrar ID da execução, horário, data de referência, hashes dos arquivos, fontes, versão do leitor, regra/perfil/template, total de unidades/boletos/linhas, incluídos/excluídos/adiados, motivo específico, documento faltante/inválido/conflitante, e origem (página/linha) da decisão. Logs operacionais não incluem credenciais; anonimizar documentos pessoais quando possível.

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
