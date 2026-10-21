# Arquitetura da Fase 1

Implementação limitada à fundação de `01_PLANO_ETAPAS.md`. Python 3.12+, Pydantic,
pytest e filelock. Não há PDF/OCR/LLM, classificador, interpretação de régua,
escritor XLSX, API, interface ou contato com devedores.

```text
src/conversor/
  domain/
    base.py          IDs, dinheiro Decimal, modelo fechado
    canonical.py     Unidade, Pessoa/Contato, Boleto, Composicao,
                     Apontamento, Origem, ResultadoCobranca, Ocorrencia
    catalog.py       administradoras, condomínios, formatos, perfis,
                     réguas, processamentos e integridade entre coleções
    template.py      entidade Template e nomes exatos das 30 colunas
  application/
    ports.py         Repositorio, Estado e erro seguro
    configuration.py CRUD transacional e consultas de configuração
  adapters/
    json_repository.py snapshots, lock, checksums, revisão e commit atômico
  readers/
    contracts.py     porta Leitor e estados explícitos de classificação
  export/
    contract.py      template e DTO de 30 células; não escreve XLSX
  cli.py             manutenção e validação de configurações
  schemas.py         geração verificável dos JSON Schemas
examples/fase1/      catálogo novo, inteiramente sintético, só rascunhos
schemas/1.0/         contratos JSON gerados
tests/              fixtures sem fontes reais; todos os testes são locais
```

## Dependências e extensão

O domínio não conhece arquivos nem Ruflo. Os casos de uso recebem a porta
`Repositorio`; só a CLI instancia o adapter JSON. Um adapter PostgreSQL deverá
implementar `carregar` e `salvar(..., revisao_esperada=...)` com a mesma transação,
integridade, preservação de histórico e concorrência otimista. A estratégia de
snapshot é o contrato inicial de unidade de trabalho; consultas e paginação
poderão ser otimizadas mantendo os casos de uso. PostgreSQL não foi implementado
nem validado nesta fase.

`application/ports.py` também define portas específicas para administradoras,
condomínios, formatos, perfis, regras, templates e histórico. A fachada tipada
`Configuracao` implementa essas consultas sobre a unidade de trabalho comum e
oferece escrita transacional/histórico sem amarrar consumidores ao backend JSON.
Consulta de formatos por administradora lista o catálogo; não classifica documentos.

Um formato versionado tem `leitor_id` e associações N:N com administradoras.
Condomínios selecionam formatos e uma versão de perfil. Perfil referencia regra
e template separados. Assim, centenas de formatos podem usar leitores por família
de layout sem criar um leitor por condomínio. Não há heurística de reconhecimento
nesta fase: o DTO apenas obriga a distinguir os três estados, com evidências.
`conhecido_validado` é declaração contratual do futuro reconhecedor; somente
registros de formato com evidência de homologação podem concluir processamentos.

IDs identificam registros estáveis. Uma nova versão tem novo ID e `versao`
explícita; referências históricas mantêm o ID da versão anterior. Formato validado,
perfil aprovado, regra aprovada e template persistido são imutáveis. Mudança exige
novo registro. Não são criadas aprovações nos exemplos executáveis. As aprovações
em testes são artificiais e não aprovam regras reais.

## JSON e atomicidade

```text
<diretório protegido>/
  .write.lock
  current.json                      manifesto ativo, schema e revisão
  generations/<id aleatório>/
    manifest.json                   cópia do manifesto para recuperação
    administradoras.json
    condominios.json
    formatos.json
    perfis_condominio.json
    regras_cobranca.json
    templates.json
    processamentos.json
    ocorrencias.json
```

Cada coleção usa `{"schema_version":"1.0", "<colecao>":[...]}`. O arquivo único
de importação da CLI é um `Catalogo`, contendo as oito coleções. O catálogo inteiro
é validado antes de escrever, inclusive referências circulares perfil/condomínio.
Para criar essas relações, importar o conjunto completo em uma transação.

O lock serializa escritores. A revisão esperada impede atualização perdida;
conflito retorna erro e exige reler o estado, sem retry cego. Todos os arquivos
novos e o manifesto são gravados e sincronizados antes de `os.replace` publicar
o ponteiro. Leitores capturam o ponteiro uma vez e leem uma geração imutável;
jamais combinam coleções de duas revisões. Gerações anteriores ficam retidas como
backups locais e suporte de auditoria. Falhas antes da troca preservam o estado
anterior; gerações órfãs não são consumidas automaticamente. Uma falha de I/O
depois da troca pode indicar commit já realizado: releia o manifesto antes de
tentar novamente.

Os oito hashes SHA-256 detectam corrupção acidental, não substituem assinatura,
autorização ou criptografia. Versão futura, chaves JSON duplicadas, NaN, manifesto
inválido, arquivo ausente, checksum divergente e referência inexistente geram erro
explícito; não há recuperação silenciosa para vazio. Falta de catálogo requer
`init` ou importação inicial explícita com revisão zero.

POSIX: arquivos privados `0600`, novas pastas `0700`, fsync de arquivos e diretórios.
Pastas preexistentes não têm permissões alteradas. Windows: filelock, flush de
arquivos e os.replace; não executamos validação nesta plataforma. Lock e rename
exigem filesystem local compatível; NFS/object storage não foram homologados.

Para recuperação manual: interromper escritores, copiar todo o diretório para
backup seguro, selecionar uma geração anterior, restaurar seu `manifest.json`
como `current.json` por troca atômica e executar `validar`. Não editar coleções ou
checksums para fazer uma validação passar. Não há coleta automática de backups,
criptografia, ACL multiusuário ou política de retenção: P09 bloqueia produção.

## Contratos financeiros e proveniência

Dinheiro usa Decimal de centavos exatos, serializado como texto no JSON. Float,
não finito e precisão que exigiria arredondamento são rejeitados. Composição aceita
créditos negativos e exige soma exata do original; multa, juros, correção e saldo
acumulado ficam separados. Isso não calcula qual valor será elegível pela régua.

Origem guarda ID opaco de arquivo, hash, versão do leitor, identificador e localização
quando disponível. Não guarda PDF, caminho com nome de cliente nem texto bruto.
Bloco/unidade originais e chave normalizada permanecem separados; não inventamos
codificador. Identidade estável do boleto é fornecida pelo futuro leitor. A chave
de idempotência combina condomínio, unidade e essa identidade, sem página; lote
rejeita duplicação não reconciliada. A reconstrução real de continuações é Fase 3.

Apontamento preserva namespace do formato: `J` não é convertido em `Jurídico`.
Regras têm condições estruturadas, vigência e aprovação, mas nenhum operador é
executado. A Fase 1 verifica integridade e requisitos de aprovação, não atesta a
semântica financeira de uma régua nem autentica a autoridade do aprovador.

## Exportação

`COLUNAS` segue literalmente o documento 04, com teste que o compara à tabela.
`Template.cabecalhos_fisicos` preserva o espaço final da coluna AA por padrão;
`colunas_logicas` usa o nome sem espaço. A opção é explícita/versionada. P06
continua aberta; nenhum cabeçalho foi homologado no importador de destino.

`LinhaExportacao` é DTO: `cadastral` proíbe dívida; `divida` exige seus seis campos.
`materializar` produz exatamente 30 posições. CPF é normalizado e validado por
dígitos verificadores; ausência, invalidade ou documento CNPJ produz texto vazio
e ocorrência de alerta. Não atesta titularidade ou situação cadastral. Telefones
(máximo cinco) e e-mails (máximo três) não são truncados silenciosamente. Campos
desconhecidos permanecem vazios. CEDENTE, produto e complemento são independentes.
Dates/Decimal são preservados como tipos Python para o futuro escritor XLSX.
O DTO não aplica cadastro antecipado, não escolhe titular e não declara elegibilidade.

## Privacidade

CLI imprime só códigos fixos, revisão e IDs opacos. Não imprime ValidationError,
conteúdo de documento, nomes ou credenciais. Nenhuma dependência envia dados para
serviços durante os testes. Dados operacionais e runtime do Ruflo ficam ignorados
pelo Git. Gitignore não é controle de acesso e não impede `git add -f`: revisão
de conteúdo continua obrigatória. Testes usam fontes e identidades sintéticas;
CPF válido para teste é calculado no teste, nunca copiado de cadastro real.
