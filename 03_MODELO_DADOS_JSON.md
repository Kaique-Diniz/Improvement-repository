# 03 — Modelo conceitual, JSON e migração futura

## Princípios
- Banco inicial em **arquivos JSON**; entidades independentes por arquivo.
- IDs estáveis e imutáveis, relacionamentos por ID, schemas e versões explícitas.
- Mudança de administradora atualiza vínculo do condomínio, preservando histórico temporal.
- Um **Condomínio** tem **exatamente uma Administradora ativa**; uma Administradora tem vários Condomínios.
- **Formato** é associação N:N com administradoras quando cabível; não copiar leitores por condomínio.
- Separar persistência da lógica de negócio por interface de repositório. Trocar backend JSON por PostgreSQL sem alterar domínio, extratores e regras.

## Tabelas/coleções futuras

| Entidade | Campos principais | Relações |
|---|---|---|
| administradoras | id, nome, identificadores, ativo | 1:N condominios |
| condominios | id, administradora_id, código, perfil_version_id, ativo | N:1 administradoras |
| formatos | id, versão, tipo, assinaturas, mapeamento, status | N:N administradoras, N:N condominios |
| perfis_condominio | id, condomínio_id, codificador_cedente, endereco, template_id | N:1 condominios |
| regras_cobranca | id, condomínio_id, versão, fonte, condições, aprovação, vigência | N:1 condominios |
| templates | id, versão, campos, nomes exatos, aba, estilos | 1:N perfis |
| processamentos | id, status, condomínio_id, data_ref, modo_cadastro_antecipado (A/B), versão da política, versões, resumo, arquivo_hashes | N:1 condominios |
| ocorrencias | id, processamento_id, gravidade, motivo, registro_origem | N:1 processamentos |

## Proposta de arquivos
```
dados/
  administradoras.json
  condominios.json
  formatos.json
  perfis_condominio.json
  regras_cobranca.json
  templates.json
  processamentos.json
  ocorrencias.json
```

- `config_exemplos/` contém apenas exemplos sanitizados, **não versões aprovadas para produção**.
- Em produção, persistência JSON precisa de gravação atômica, lock de escrita para alterações concorrentes, backup e validação por schema.
- Não guardar conteúdo integral dos PDFs em JSON. Guardar referência protegida com expiração ou retenção previamente definida.
- Não guardar credenciais da régua: separar somente texto de regra interpretável, protegendo a fonte original.

## Operações esperadas do repositório
`get_administradora(id)`, `get_condominio(id)`, `find_condominio_por_codigo(adm_id, codigo)`, `find_formatos_compativeis(assinaturas)`, `get_regra_aprovada(condo_id, data_ref)`, `get_template(versao)`, `save_processamento(resumo)`.

## Migração a PostgreSQL
1. Congelar schemas e versionar arquivos.
2. Validar integridade referencial e chaves únicas em JSON.
3. Criar tabelas com chaves estrangeiras e migrations.
4. Importar catálogos preservando IDs, histórico e versões.
5. Rodar mesma suíte de testes contra os dois repositórios.
6. Executar migração em ambiente de homologação antes de trocar produção.

## Exemplos
Veja `config_exemplos/`; os IDs são ilustrativos e devem ser harmonizados no cadastramento real.

### Proposta documental revisada — preparação do 4.3B

O modo universal A/B pertence ao **processamento**, não ao perfil do condomínio;
registrá-lo em histórico/auditoria e contexto de reprodução. Não há default
selecionado. Os campos propostos na tabela acima ainda não foram implementados
ou migrados nesta revisão documental. Booleanos históricos `cadastro_antecipado`
continuam legíveis pelos contratos existentes, sem determinar o modo de uma nova
execução. Não reescrever processamentos anteriores ou schemas 1.0/1.1.

Valor → cota/componentes exige mapeamento revisado antes de configurar centavo;
não assumir equivalência com `Boleto.valor_original`. Requisitos, papéis acumuláveis
e pendências constam na [proposta atual](docs/ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md).
Ela não aprova planos nem modifica as interfaces JSON/PostgreSQL implementadas.

## Documentos e auditoria (atualização geral de 21/10/2026)

Extensão posterior **4.3B.1**, sem migração de contratos históricos:
`SolicitacaoProcessamentoSintetico` exige ambiente sintético e modo A/B explícito;
`ProjecaoProcessamentoSintetico` associa modo, versão da projeção, relatório do
motor e hash a decisões de dívida/cadastro, com autorização operacional sempre
falsa. Schemas aditivos em `schemas/processamento-sintetico/1.0/`. O novo fluxo
retém CPF/CNPJ inválido para revisão conforme decisão específica do responsável;
ausência permanece alerta. A política geral histórica abaixo continua legível.
Persistência operacional assinada da nova projeção não integra esta entrega;
não reescrever históricos 1.0/1.1. Veja os
[contratos e limites](docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md).

`Pessoa.documento` preserva tipo e valor bruto textual; `documento_origem` e
`evidencias_documentais` preservam referências de fonte e vínculo explícito ao
titular. `Ocorrencia.evidencias_documentais` guarda todos os candidatos em
auditoria protegida; não enviar esses valores a logs ou Git. Ausência/invalidade
não bloqueia; conflito entre documentos válidos ou associação não confirmada
bloqueia resolução/exportação automática do cadastro e encaminha à revisão humana.
A coluna literal `CPF` aceita CPF (11) ou CNPJ (14), validado e sempre texto.
Os campos de evidência são aditivos, com defaults vazios para ler JSON anterior.
Schemas 1.0 regenerados; acrescentado `resolucao_documental.schema.json`. Não há
migração do catálogo nem mudança nas interfaces JSON/PostgreSQL. Códigos novos:
`DOCUMENTO_AUSENTE`, `DOCUMENTO_INVALIDO`, `DOCUMENTOS_CONFLITANTES`,
`DOCUMENTO_TITULAR_NAO_CONFIRMADO`. O comparador de laboratório ainda reconhece
o código legado `CPF_AUSENTE_OU_INVALIDO` em resultados históricos.

## Extensão dos leitores reais na Fase 3

`Boleto.competencia` admite ausência (`None`); `emissao_original` e
`ItemComposicao.descricao_original` preservam o conteúdo de origem sem inventar
competência/data. `LoteCanonico.ressalvas` conserva registros críticos ou
informativos com origem e conteúdo bruto protegido. JSON com os campos
anteriores continua legível; consumidores precisam tratar competência ausente
explicitamente. Interfaces de repositório e schemas de catálogo não mudam por
condomínio ou leitor. Ver [leitores reais](docs/CORRECOES_LEITORES_REAIS_FASE3.md).
