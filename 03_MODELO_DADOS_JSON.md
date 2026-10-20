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
| perfis_condominio | id, condomínio_id, codificador_cedente, cadastro_antecipado, endereco, template_id | N:1 condominios |
| regras_cobranca | id, condomínio_id, versão, fonte, condições, aprovação, vigência | N:1 condominios |
| templates | id, versão, campos, nomes exatos, aba, estilos | 1:N perfis |
| processamentos | id, status, condomínio_id, data_ref, versões, resumo, arquivo_hashes | N:1 condominios |
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
