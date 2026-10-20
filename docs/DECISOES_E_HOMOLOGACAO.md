# Decisões técnicas e pendências — somente Fase 1

## Decisões técnicas adotadas

- Python/Pydantic/pytest para fundação, conforme proposta do dossiê e exigência de
  suíte pytest; sem decisão de UI/infra. Dependências diretas e ambiente de testes
  fixados e schemas gerados deterministicamente.
- JSON schema `1.0`. `config_exemplos/` original é conceitual, ilustrativo e não
  operacional: faltam versões/IDs harmonizados/vínculos/aprovações. Foi preservado.
  O exemplo novo em `examples/fase1/` atende ao contrato executável sem ativar regras.
- Versionamento por ID da versão; aprovado imutável. Vigências usam intervalos
  técnicos `[início, fim)`, com fim opcional. Isso impede duas versões aplicáveis
  na mesma data e não decide se prazo de atraso é `>30` ou `>=30`.
- Uma associação aberta por condomínio, histórico sem sobreposição, fechado
  imutável. Troca de administradora fecha o vínculo e adiciona outro na mesma
  transação; execuções passadas validam o vínculo na `data_ref` registrada.
- Escrita por gerações e troca de manifesto, em vez de oito substituições
  independentes que poderiam deixar referências inconsistentes em um crash.
- Processamentos e ocorrências persistidos são snapshots imutáveis de auditoria.
  A CLI cadastral não implementa workflow de execução nem transições de estado.
  Esse workflow deverá separar estado em andamento de histórico concluído nas
  fases posteriores; não reescrever eventos passados.
- DTO de exportação conserva data e Decimal; serial Excel e estilo serão definidos
  na Fase 5. Valores de parcela devem ser positivos; créditos são representados
  nos itens da composição, sem gerar linha de cobrança negativa automaticamente.

## Pontos para homologação, sem criar regras de cobrança

| Ponto | Comportamento nesta fase | Impacto/decisão futura |
|---|---|---|
| P01/P02: lote e referência | data explícita por processamento; sem execução | Definir interface e convenção da data antes do motor/UI |
| P04/P05: titular, CNPJ e fontes divergentes | CPF inválido/CNPJ -> vazio + alerta; sem enriquecimento | Aprovar associação de titulares e prioridade temporal das fontes |
| P06: espaço final AA | preservado no cabeçalho físico por opção de template | Testar contra importador; não foi declarado homologado |
| P07: judicial e exceções | contrato de regra, sem avaliação; nenhuma regra real ativada | Aprovar modalidade, alcance, ações e evidências na Fase 4 |
| P08: escopo do bloqueio | cada ocorrência exige escopo; linha crítica é rejeitada | Homologar matriz lote/arquivo/registro; não inferir matriz global |
| P09: retenção e acesso | gerações locais privadas, sem expiração automática | Definir proteção/retencão/backup antes de dados reais/produção |
| P10: gabarito TREE | nenhum gabarito real suposto | Aprovar fixture de aceite autorizada |
| P11: stack UI/infra | nenhuma UI, API, implantação ou banco SQL | Confirmar apenas antes dessas fases |
| P12: importador de destino | somente DTO de saída, sem arquivo XLSX | CPF vazio, tipos, duplicados e datas exigem homologação; produção bloqueada |
| Identidade de boleto | leitor fornecerá ID estável, lote rejeita repetição | Homologar chave por formato/administradora na Fase 3 |
| Ativação de réguas | aprovação explícita e vigência validada; sem autenticação real | Definir autoridade/ACL e agendamento de novas versões na Fase 4 |

Não há interpretação nova de TREE ou Plaza implementada. Nem prazo judicial, nem
ação de exclusão, nem cadastro antecipado viraram defaults de cobrança. As pendências
de negócio já classificadas como não bloqueantes para Fase 1 permanecem abertas.
Nenhum detalhe de cobrança não aprovado foi necessário para implementar a fundação.

## Rastreabilidade dos testes

- `test_catalog.py`: referências, vínculos, homologação, vigência e classificação
  como contrato (não como algoritmo de reconhecimento).
- `test_canonical.py`: Decimal, créditos, somatórios, origem, duplicidade, CPF e
  resultados com bloqueios.
- `test_export.py`: 30 colunas contra documento 04, linha de dívida/cadastral,
  tipos, vazio+alerta, preservação de zeros e cabeçalho físico.
- `test_repository.py`: leitura/escrita, revisão, lock, concorrência, falha antes do
  commit, corrupção, hashes, schema, CRUD e histórico imutável.
- `test_cli_and_schemas.py`: comandos locais, exit status, erro sem vazamento,
  schemas publicados reproduzíveis.

Não executados por estarem fora da fase: reconhecimento de PDF, amostras Habita/FL,
reconstrução real entre páginas, motor da régua, geração XLSX e importação no destino.
Não há testes ignorados ou placeholders para declarar essas capacidades prontas.

## Evidência da entrega (20/10/2026)

Ambiente atual: Linux, Python 3.12.14. Instalação do lock e instalação editável
executadas com sucesso. `pip check` não encontrou dependências incompatíveis.

```bash
.venv/bin/python -m pytest -q
# 96 passed; nenhuma falha, skip ou xfail
.venv/bin/python -m conversor.schemas --check
# status 0; seis schemas reproduzíveis
.venv/bin/python -m conversor.cli --dados ./dados/demo validar
# status ok, revisão 2, schema_version 1.0
```

Também foram executados os comandos de inicialização, importação sintética e
listagem do README. Os dados gerados estão apenas no diretório local ignorado.
O teste de importação via CLI inicia seu próprio repositório temporário e verifica
que repetir `init` falha com conflito, sem apagar o estado. Falhas e concorrência
são simuladas deterministicamente nos testes, sem precisar de serviços externos.

Ruflo 3.59.1 foi usado localmente para registrar a tarefa de implementação. O CLI
criou a tarefa; avisou que não conseguiu escrever um espelho auxiliar na home
somente leitura. Isso não bloqueou os contratos Python, a persistência ou os testes.
Não foram iniciados agentes externos ou aprovadas regras por IA.
