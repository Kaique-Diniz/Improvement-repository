# Dossiê de transferência ao Codex — Conversor Inteligente de Inadimplência

**Status:** Fases 1 e 2 implementadas e testadas com sintéticos. Homologação com amostras sanitizadas pendente; nenhum formato real homologado.
**Atualização:** 20/10/2026.  
**Idioma do projeto:** português brasileiro.

## Objetivo
Converter relatórios de inadimplência (PDF, XLSX e arquivos complementares) de múltiplas administradoras em um único modelo Excel com 30 colunas, aplicando a régua de cobrança de cada condomínio, com detecção automática de layout, alertas, bloqueios de segurança e auditoria.

## O que compõe este pacote

- `01_PLANO_ETAPAS.md`: fases, dependências, entregáveis e pontos de controle.
- `02_ESPECIFICACAO_PRODUTO.md`: requisitos e comportamento do produto.
- `03_MODELO_DADOS_JSON.md`: entidades, relacionamentos e persistência inicial.
- `04_DICIONARIO_TEMPLATE.md`: contrato de saída, 30 campos e tratamento de linhas.
- `05_PENDENCIAS_TESTES_ACEITE.md`: decisões em aberto, cenários de testes e condições de liberação.
- `06_PROMPT_INICIAL_CODEX.md`: instruções prontas para iniciar a primeira tarefa.
- `AGENTS.md`: guia de implementação, segurança e testes para uso no repositório.
- `FONTES_E_IMPORTACAO.md`: documentos de origem e processo recomendado para entregá-los com segurança.
- `config_exemplos/*.json`: exemplos **não operacionais** de configuração. Não contém CPF, senhas ou clientes reais.

## Como usar

1. Leia `01_PLANO_ETAPAS.md`, depois `02_ESPECIFICACAO_PRODUTO.md` e `05_PENDENCIAS_TESTES_ACEITE.md`.
2. Coloque os documentos `.md`, `AGENTS.md` e `config_exemplos/` em um repositório **privado** para o Codex.
3. Não faça commit de relatórios reais, da régua completa ou de cadastros com dados pessoais/credenciais.
4. Disponibilize arquivos reais ao ambiente autorizado de teste por um caminho seguro e privado, somente quando necessário.
5. Envie a tarefa do arquivo `06_PROMPT_INICIAL_CODEX.md` ao Codex, **implementando apenas a Fase 1**.
6. Revise testes e entregas de cada fase antes de pedir a próxima.

Este pacote substitui a necessidade de colar o histórico integral de conversa no prompt. O PDF com a conversa do Claude é uma referência adicional, não a fonte normativa quando divergir destas decisões posteriores.

## Executar a Fase 1 localmente

Requer Python 3.12 ou superior. Na raiz do checkout, em Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation --editable .
.venv/bin/python -m pytest -q
.venv/bin/python -m conversor.schemas --check
```

No PowerShell/Windows, crie o venv com `py -3.12 -m venv .venv` e substitua
`.venv/bin/python` por `.venv\Scripts\python.exe` nos comandos. Os testes desta
entrega foram executados em Linux/Python 3.12; Windows ainda não foi homologado.

Exemplo local, sem dados pessoais e sem qualquer conversão/cobrança:

```bash
.venv/bin/python -m conversor.cli --dados ./dados/demo init
.venv/bin/python -m conversor.cli --dados ./dados/demo importar examples/fase1/catalogo.sintetico.json --revisao 1
.venv/bin/python -m conversor.cli --dados ./dados/demo validar
.venv/bin/python -m conversor.cli --dados ./dados/demo listar condominios
```

`init` cria a revisão 1; importação acima cria a revisão 2. Repetir `init` retorna
`CONFLITO_DE_REVISAO`, sem sobrescrever arquivos. Para atualizar um registro, usar
`gravar <colecao> <arquivo.json> --revisao <revisao-atual>`; para remover um registro
sem referências, `excluir <colecao> <id> --revisao <revisao-atual>`. Veja `--help`.
Relações novas e circulares devem entrar em conjunto por `importar`, em catálogo
completo consistente. A CLI retorna status 0 em sucesso e 2 em erros de domínio/I/O,
sem imprimir dados pessoais. Consultas Python retornam objetos tipados via
`Configuracao`, sem expô-los automaticamente no terminal.

Use o diretório `dados/` (ignorado pelo Git) ou um local privado fora do checkout.
Não force commit de fontes reais. O exemplo em `examples/fase1/` é inteiramente
sintético e todas as regras/perfis/formatos estão em rascunho. Os exemplos originais
em `config_exemplos/` foram preservados como material conceitual não operacional;
não são importados nem aprovados automaticamente.

## Arquitetura, contratos e limites

- [Arquitetura e funcionamento do JSON](docs/ARQUITETURA_FASE1.md).
- [Decisões técnicas, testes e pontos de homologação](docs/DECISOES_E_HOMOLOGACAO.md).
- [Apoio local com Ruflo](docs/RUFLO.md).
- [JSON Schemas versionados](schemas/1.0/). Regenerar com `python -m conversor.schemas`.

Os JSON Schemas descrevem a estrutura; os modelos Python também validam somatórios,
referências, vigências, aprovações e relações. A validação de prontidão do catálogo
é feita com `validar`, não só com validação estrutural de JSON Schema.

O contrato de saída tem 30 posições, CPF em branco com alerta quando ausente ou
inválido e linhas cadastrais com Y:AD vazias. Preserva o espaço final físico da
coluna AA por configuração até homologação. Nenhum arquivo XLSX é gerado nesta fase.
Nenhum código aplica a régua, reconhece PDFs ou enriquece com Cadastro Geral.
Retenção, ACL, aprovação real e importação no sistema final permanecem pendentes.

As etapas seguintes exigem aprovação explícita após revisão de cada entrega.

## Fase 2 — reconhecimento automático

O comando `reconhecer` detecta PDF com texto, PDF sem texto/rasterizado/misto,
XLSX e CSV UTF-8. Classifica assinaturas e identifica administradora/condomínio
por campos explícitos. Não extrai boletos, não aplica régua e não gera Excel.
Desconhecidos, ambiguidades e configurações não homologadas bloqueiam o avanço.

Após instalar/atualizar o ambiente pelos comandos acima, crie a demonstração:

```bash
.venv/bin/python examples/fase2/gerar_demo.py --saida dados/demo_fase2
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio init
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio importar dados/demo_fase2/catalogo.json --revisao 1
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio reconhecer dados/demo_fase2/habita_tree.pdf --arquivo-id fonte_sintetica --assinaturas dados/demo_fase2/assinaturas.json --data-ref 2026-10-21
```

A demonstração retorna **status 3**, resultado bloqueante com
`FORMATO_NAO_HOMOLOGADO` e `ASSINATURAS_NAO_HOMOLOGADAS`. Esse é o comportamento
esperado: os exemplos são rascunhos e não podem aprovar formatos reais.
O gerador cria arquivos novos sem sobrescrever diretório já utilizado; use outro
diretório para uma nova demonstração. A data é ilustrativa e sempre deve ser
fornecida explicitamente. A suíte testa caminhos positivos com aprovações artificiais
restritas a fixtures temporárias; não existe etapa de confirmação interativa.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

O reconhecimento retorna status 0 quando apto para próxima etapa, 3 quando bloqueado
e 2 para erros de configuração/acesso. O JSON público contém IDs opacos, hashes,
versões, cobertura das assinaturas, localização de evidências e códigos de bloqueio;
nunca trechos brutos, nomes de arquivos/pessoas ou valores financeiros extraídos.
`pronto_para_proxima_etapa` é prontidão de configuração/reconhecimento, não de cobrança.

- [Arquitetura, decisões e limites da Fase 2](docs/RECONHECIMENTO_FASE2.md).
- [Arquivos sanitizados necessários e como comparar gabaritos](tests/fixtures/sanitized/README.md).
- [Assinaturas sintéticas Habita e FL, não homologadas](examples/fase2/assinaturas.sinteticas.json).

A pasta `tests/fixtures/sanitized/` está preparada e ignora amostras locais no Git.
O comparador de contrato canônico prepara a validação dos futuros leitores sem
implementá-los nesta fase. Amostras representativas e gabaritos revisados são
necessários antes de homologar Habita/TREE ou FL/Plaza. A Fase 3 não foi iniciada.
