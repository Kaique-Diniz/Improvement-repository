# Apoio local com Ruflo

Ruflo foi inicializado anteriormente pelo wizard; seus arquivos locais não são
parte dos contratos do produto. A versão usada nesta tarefa é `3.59.1`. Serve para
acompanhar a tarefa de desenvolvimento, sem acesso a documentos reais ou segredos.
O conversor e sua suíte pytest não dependem de Ruflo, LLM, embeddings ou da rede.

```bash
npm_config_cache=/tmp/ruflo-npm-cache npx --yes ruflo@3.59.1 --version
npm_config_cache=/tmp/ruflo-npm-cache npx --yes ruflo@3.59.1 task create \
  --type implementation \
  --description 'Fase 1: contratos, persistencia JSON e testes sinteticos; sem leitores, motor financeiro ou XLSX' \
  --tags fase1,fundacao
```

O comando usa cache gravável fora da home restrita deste ambiente. Em Windows,
usar a sintaxe de variável do shell correspondente ou o cache padrão gravável.
Não é necessário inicializar agentes nem instalar Claude Code para executar os
testes Python. Não enviar dados cadastrais, régua bruta ou credenciais à memória
do Ruflo. Mudanças em arquivos auxiliares gerados pelo próprio Ruflo ficam locais.

No laboratório do pacote sintético, Ruflo também foi usado para registrar a tarefa
de testes (`task-1792588750647-k6yscg`). O acompanhamento contém apenas descrição
genérica do desenvolvimento; arquivos-fonte, valores e cadastros não são enviados.
O resultado verificável continua sendo a suíte pytest e o relatório do laboratório.
