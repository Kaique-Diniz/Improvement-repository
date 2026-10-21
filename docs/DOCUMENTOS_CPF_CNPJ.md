# CPF e CNPJ na coluna literal CPF

Atualização geral aprovada pelo usuário em 21/10/2026, substituindo a restrição
anterior a CPF. Não altera valores financeiros, vencimentos, seleção de boletos
ou regras de cobrança. Fase 3 permanece não homologada para produção.

O contrato continua com aba `Dados`, 30 colunas A:AD na mesma ordem e coluna C
literalmente `CPF`. CPF numérico de 11 dígitos e CNPJ numérico de 14 dígitos são
validados pelo respectivo algoritmo de dígitos verificadores. Zeros repetidos e
dígitos incorretos são rejeitados. Tipo explícito não é trocado para fazer um
valor passar; não há preenchimento de zeros ou dígitos ausentes. Validade fiscal
algorítmica não comprova identidade, titularidade ou situação na Receita.

O escritor grava CPF/CNPJ como string literal com formato `@` e confere valor,
tipo e estilo após reabrir o arquivo. Documento ausente/inválido fica vazio,
com `DOCUMENTO_AUSENTE` ou `DOCUMENTO_INVALIDO`, sem bloquear por esse motivo.
Um documento inválido secundário é preservado e alertado mesmo existindo um
documento válido associado ao titular.

## Conflitos e associação ao titular

`Pessoa.documento` preserva o valor bruto. `documento_origem` registra a fonte
do documento principal, independentemente da origem do contato. Evidências
adicionais contêm documento bruto, `Origem` e `titular_id` explicitamente
associado; vínculo ausente/divergente exige revisão humana.

`resolver_documento` compara documentos válidos normalizados por tipo e valor.
Máscaras diferentes do mesmo documento não criam conflito. Dois documentos
válidos distintos para um titular, inclusive um CPF e um CNPJ, geram
`DOCUMENTOS_CONFLITANTES` crítico; vínculo não confirmado gera
`DOCUMENTO_TITULAR_NAO_CONFIRMADO` crítico. Não há escolha por ordem, tipo,
recência ou preferência implícita pelo Cadastro Geral.

O enriquecimento só preserva vínculo anterior quando ID estável de pessoa e
nome coincidem; igualdade de nome ou unidade isoladamente não basta. Não
associar IDs de pessoa somente pela unidade no futuro adaptador real. Mudanças
de nome/titular exigem revisão. A prioridade histórica do laboratório sintético
não remove bloqueios documentais nem se torna regra para dados reais.

Em conflito, o cadastro retorna sem documento selecionado, com todas as fontes
em `Pessoa.evidencias_documentais`. `resultado_leitura` fornece as ocorrências
críticas e `Ocorrencia.evidencias_documentais` preserva as informações para
revisão. A validação privada retorna `revisao_humana` e código de saída 2, mesmo se o
gabarito coincidir, e grava um arquivo de auditoria documental com permissão
0600 na área privada (mesmo sem optar por salvar o canônico inteiro).
O contrato de exportação rejeita esse cadastro, inclusive DTO construído
sem validação inicial. O escritor recusa um conjunto contendo linha bloqueada;
não descarta cobranças silenciosamente. Este trabalho não cria interface/fila
externa de revisão nem permite concluir manualmente o conflito via um booleano.
A revisão deve estabelecer titular e fonte correta, preservar histórico e
produzir uma nova entrada auditada antes de exportar.

Valores e fontes documentais completos existem somente em arquivos/auditoria
protegidos, nunca em logs, stdout ou Git. `repr` oculta os documentos e as
evidências. Campos novos são opcionais com defaults vazios: JSON canônico antigo
continua legível. Schemas 1.0 regenerados e acrescentado contrato de resolução.
Os códigos antigos de CPF são apenas reconhecidos pelo comparador de resultados
históricos; novas execuções emitem os códigos documentais acima.

## Importador de destino: CRM easyCollector

O responsável pelo processo confirmou nesta conversa, em 21/10/2026, que o
CRM **easyCollector aceita CPF e CNPJ na mesma coluna literal `CPF`**. Essa
compatibilidade documental é requisito geral aprovado, não exceção de laboratório.
A confirmação resolve a pendência de aceitação dos dois tipos nessa coluna.

O roundtrip local confirma texto, zeros e estrutura do XLSX; não foi realizada
importação técnica no easyCollector nesta tarefa. A confirmação do responsável
não equivale à homologação integral do Excel: demais campos, formatos,
cadastros, duplicidades e comportamentos do importador continuam pendentes.
Não há acesso de homologação configurado neste repositório.

Gere um arquivo exclusivamente sintético para o ensaio autorizado, fora do Git:

```sh
PYTHONPATH=src .venv/bin/python examples/documentos/gerar_ensaio_importador.py \
  --saida /workspace/validacao-privada-fase3/ensaio_importador_sintetico.xlsx
```

Contém quatro linhas cadastrais: CPF válido com zeros, CNPJ válido com zeros,
documento ausente e documento inválido (os dois últimos ficam vazios com
alertas). Documentos são vetores de teste algorítmicos, sem identidade real.
Não há dívida ou cobrança. Não importar em produção.

No ambiente autorizado, registrar versão do importador, data/responsável,
hash do ensaio, confirmação dos 30 cabeçalhos e campo `CPF`, tipos aceitos e
reexportação/leitura mostrando 11/14 dígitos sem perda de zeros. Verificar
cadastros com documento vazio. Confirmar se o espaço final de AA é exigido.
Guardar evidência do aceite fora do Git quando contiver identificadores.
Se o destino rejeitar CNPJ, manter pendência explícita; não convertê-lo para
número, truncar, renomear a coluna ou omitir documento válido para contornar.

## Diagnóstico real FL

Os documentos reais e o relatório atualizado ficam exclusivamente em
`/workspace/validacao-privada-fase3/resultados/diagnostico_documental_002/`.
A reavaliação usa as fontes autorizadas e os validadores novos, sem alterar
os Excel originais ou executar regras financeiras. As quatro representações
com zeros perdidos devem usar informação completa da fonte; as três ocorrências
de CNPJ devem ser reclassificadas pela validade e associação, e os dois
conflitos de CPF permanecem bloqueados para revisão, sem preferência automática.

## Verificação local

```sh
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

`tests/test_documents.py` cobre validação, zeros, tipos, máscaras, ausência,
invalidade, conflito CPF/CPF e CPF/CNPJ, associação, enriquecimento, auditoria
protegida, bloqueio do escritor e leitores sintéticos. O ensaio do importador
não substitui a suíte nem a homologação com fontes reais.

Resultado final desta atualização: **322 testes regulares + 60 de integração
sintética = 382 aprovados**, incluindo 52 casos em `test_documents.py` e um
novo caso de encaminhamento/auditoria na validação privada. Os dois geradores
de schema passaram em `--check`. O reteste privado dos PDFs reais preservou
os três bloqueios estruturais existentes; não se declara a Fase 3 concluída.

Atualização estrutural posterior: os bloqueios de layout descritos acima foram
corrigidos; os três PDFs já foram processados. Permanecem bloqueios de dados
críticos, não de reconhecimento estrutural. Ver [resultado atual](CORRECOES_LEITORES_REAIS_FASE3.md).
