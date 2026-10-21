# Fase 2 — reconhecimento e preparação de homologação

Somente Fase 2, autorizada após a fundação. Implementação validada com documentos
sintéticos; **Habita/TREE e FL/Plaza reais continuam não homologados**. Conforme a
orientação do usuário, os originais não foram abertos nem adicionados ao repositório.

## Fluxo e responsabilidades

```text
Arquivo local protegido
  -> SondadorLocal (conteúdo, tipos, limites, texto transitório por página/aba)
  -> ReconhecerDocumento
       catálogo JSON: uma revisão consistente
       catálogo de assinaturas: uma versão, com referências e aprovação
       assinaturas por família/versão + campos fortes de identidade
       verificação de vínculos, formatos aceitos e versões de perfil/regra/template
  -> ResultadoReconhecimento (IDs, hashes, evidências e bloqueios)
```

- `domain/recognition.py`: contratos e invariantes, sem parser ou I/O.
- `adapters/document_probe.py`: sondagem de conteúdo; não retorna entidades financeiras.
- `application/recognition.py`: decisões determinísticas, por portas de repositório.
- `adapters/signature_repository.py`: leitura de JSON versionado; não altera aprovações.
- `recognition_schemas.py` e `schemas/reconhecimento/1.0/`: contratos próprios da Fase 2.
- `examples/fase2/`: assinaturas Habita e FL separadas, três documentos sintéticos e
  gerador de PDFs/configuração para demonstração. Tudo continua em rascunho.
- `tests/recognition/`: regressão sintética de reconhecimento e segurança.
- `tests/homologacao/runner.py`: comparação independente contra gabaritos revisados.

O `Leitor` financeiro da Fase 1 permanece uma porta. Não foram criados leitores
financeiros fictícios. Habita e FL têm assinaturas e `leitor_id`s distintos, sem
chavear o futuro extrator pelo condomínio. A mesma assinatura/versão pode atender
outros condomínios e administradoras relacionadas, desde que a identidade e o vínculo
estejam explícitos. Há testes para ambos os tipos de reutilização.

## Catálogo e compatibilidade

O JSON de assinaturas tem schema próprio `1.0`, `versao`, estado
`rascunho`/`homologado` e `Aprovacao` do conjunto, incluindo identidades. Referencia
IDs estáveis de formatos, administradoras e condomínios já existentes. Não mudamos
nem migramos os snapshots/schema `1.0` da Fase 1. `Formato.marcadores` continua um
campo descritivo legado; as assinaturas estruturadas são a fonte da classificação.

Cada catálogo fornece uma assinatura ativa por versão de formato. Para testar nova
assinatura mantendo reprodução, fornecer nova versão do conjunto e preservar o
arquivo anterior em armazenamento protegido. O runtime só lê; não modifica esses
arquivos nem gera aprovações. Publicação de configuração deve substituir o arquivo
inteiro atomicamente, com revisão/autorização externa. Não é um sistema de ACL.

O resultado identifica o hash semântico do snapshot de catálogo e do conjunto de
assinaturas, a revisão, a versão de cada assinatura escolhida, motor/sondador e data
de referência. Hash semântico significa JSON do modelo completo, com chaves ordenadas;
inclui defaults e preserva a ordem das listas, sem depender de indentação do arquivo.
A fonte tem SHA-256 dos bytes completos. Retenha as entradas/versionamentos para
reproduzir uma decisão; hashes não recuperam configurações que foram descartadas.

## Seleção conservadora e pontuação

1. Tipo vem do conteúdo; extensão e nome do arquivo não selecionam tipo ou identidade.
2. Normalização de assinatura remove acentos, uniformiza caixa e espaços. Não modifica
   código original, não remove zeros e não normaliza valores financeiros.
3. Cada assinatura exige ao menos dois marcadores obrigatórios distintos, mais um
   limiar inteiro de pontos. Os exemplos exigem os quatro marcadores. Pesos opcionais
   podem compor a cobertura, mas não dispensam marcadores obrigatórios.
4. Todos os marcadores obrigatórios devem estar presentes na mesma página/aba;
   não somamos pedaços de layouts distintos para criar uma correspondência.
5. Nenhuma assinatura elegível -> desconhecido. Mais de uma -> ambíguo, inclusive se
   um candidato for rascunho ou tiver menos pontos. Não escolhemos pelo maior score.
6. Assinatura única só pode avançar se o formato for validado e o conjunto de
   assinaturas homologado. Aprovações sintéticas de testes não são entregues como reais.
7. Administradora e condomínio exigem pares rótulo/valor configurados, com valor inteiro
   exato. Usamos campos `Rótulo: valor` ou duas células separadas por tabulação. Todos
   os identificadores configurados de uma identidade devem aparecer na mesma página/aba.
   Não inferimos identidade pelo layout, nome, único cadastro, logotipo ou caminho.
8. Inspecionamos todas as páginas/abas. Identidades conflitantes ou uma identidade
   conhecida acompanhada de valor desconhecido no mesmo rótulo geram bloqueio. Não
   filtramos candidatos pela compatibilidade de formato para esconder o conflito.
9. Código igual em entidades diferentes não é desempatado automaticamente pela
   administradora; configurar identificadores adicionais fortes ou resolver a
   ambiguidade. É uma escolha conservadora, não uma regra financeira nova.
10. O vínculo de administradora é consultado na data de referência explícita. O formato
    precisa ser aceito no condomínio e associado à administradora identificada.

`cobertura_percentual` é pontos encontrados / pontos máximos, com divisão inteira;
**não é probabilidade calibrada nem validação financeira**. Uma assinatura com 100%
em rascunho continua bloqueada. Evidências contêm grupo, IDs e página/aba, sem texto.
Uma correspondência de cabeçalho não prova completude/consistência dos boletos: isso
continua sendo responsabilidade dos leitores e validadores da Fase 3.

O identificador CNPJ só é considerado em rótulo próprio configurado, com 14 dígitos
estruturais e comparação exata, normalizando pontuação. Não consulta cadastro nem
valida situação/titularidade. CNPJ de proprietário não identifica o condomínio por
coincidência; ele nunca é usado no campo CPF de saída.

## Tipos e limites

- **PDF texto:** parser local pypdf 6.21.1, todas as páginas. PDF sem texto com objeto
  raster é `pdf_imagem`; sem texto e sem imagem identificável permanece desconhecido.
  Um PDF com página de texto e outra sem texto é `pdf_misto` e bloqueia, inclusive
  uma página realmente branca: não presumimos que nada importante foi perdido.
  Não existe OCR, renderização, envio para LLM, busca na rede ou desbloqueio por senha.
- **XLSX:** valida ZIP/OOXML, rejeita entidades/DTD, projetos VBA e referências
  a workbooks externos;
  read-only, sem avaliar fórmulas ou usar seus valores em cache como evidência.
  As dimensões declaradas não encerram a leitura prematuramente: lemos todas as linhas
  reais. Nome da aba não é evidência; apenas seu índice sai no relatório. Células
  constantes são texto transitório para reconhecimento, não valores canônicos.
- **CSV:** UTF-8/BOM, separadores `;`, `,` ou tab, ao menos duas linhas/colunas e
  largura consistente. Mais de um separador estruturalmente plausível bloqueia;
  não adivinhamos encoding/dialeto. XLS binário, imagens soltas e demais tipos não
  são suportados. CSV sem assinatura aprovada também fica desconhecido.

Limites técnicos configuráveis por `LimitesSondagem`: arquivo 20 MiB, 1000 páginas,
5 milhões de caracteres, stream PDF 20 MiB, ZIP 1000 entradas/100 MiB expandidos,
100 abas, 100 mil linhas/200 colunas e 200 mil células. Estouro, erro em página
posterior ou leitura incompleta descarta os fragmentos: não reconhece amostra parcial.
Na leitura de arquivo acima do limite, retornamos erro sem fingir que hash de prefixo
é hash do arquivo. Essas proteções não são sandbox com limite rígido de CPU/RAM;
isolamento/timeout de parsers adversariais e carga com relatórios reais exigem validação
antes de produção. Bibliotecas não recebem caminho de arquivo nem podem propagar logs
de conteúdo ao logger da aplicação. Nenhum texto transitório é serializado.

## Resultado e bloqueios

`estado` diferencia `conhecido_validado`, `desconhecido` e `ambiguo`. Os dois últimos
nunca selecionam configurações. Um reconhecimento conhecido pode continuar bloqueado
por perfil/regra não aprovados ou vigência incompatível. Assim, reconhecer layout
não aprova regra ou cria autorização de cobrança.

`pronto_para_proxima_etapa=true` só existe para resultado único e sem bloqueios de
configuração/reconhecimento. Não significa que houve extração/validação financeira
ou que a régua pode ser executada nesta versão. O comando não grava Processamento,
não dispara pipeline e não pede confirmação em um caso sintético validado.

CLI: status 0 apto; 3 desconhecido/ambíguo/bloqueado com relatório JSON; 2 erro de
configuração, contrato ou acesso, sem caminho/entrada bruta. As réguas de cobrança,
o comportamento CPF e as 30 colunas não foram modificados nesta fase.

## Homologação pendente e testes preparados

Os arquivos exatos e comandos estão em
[`tests/fixtures/sanitized/README.md`](../tests/fixtures/sanitized/README.md).
Foram preparados o diretório protegido por gitignore, manifesto ilustrativo e runner.
O runner de reconhecimento executa a comparação local; a etapa `contrato-canonico`
compara JSON de um futuro leitor ao gabarito. Não extrai PDF nem cria resultados para
fazer o teste passar. Compara campos, origens e composição; valida somatórios e
rejeita duplicidade de boleto continuado. Os testes desse harness usam apenas sintéticos.

Ainda não executados: reconhecimento com PDFs sanitizados representativos, extração
financeira real, continuidade extraída dos originais, cadastro/enriquecimento, régua
ou importação de XLSX. A ausência de amostras não é contabilizada como teste aprovado
ou teste pulado. A homologação exige comparar amostras, revisar assinaturas e só então
aprovar a configuração — nenhuma versão real foi promovida automaticamente.

O Ruflo 3.59.1 foi usado para registrar a tarefa local de desenvolvimento; não recebeu
fontes reais, contatos ou credenciais. O aviso de espelho na home somente leitura não
impediu essa operação. Não são necessários Claude Code, agentes remotos ou embeddings
para executar o reconhecimento e os testes.

## Evidências desta entrega — 21/10/2026

Linux/Python 3.12.14; instalação pelo lock e instalação editável executadas, versão
do pacote `0.2.0`. Parsers fixados: pypdf 6.21.1, openpyxl 3.1.5, defusedxml 0.7.1.

```bash
.venv/bin/python -m pytest -q
# 176 passed; sem falhas, skips ou xfails
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
# status 0 em ambos: contratos da Fase 1 preservados e novos schemas reproduzíveis
.venv/bin/python -m pip check
# No broken requirements found
```

Também executados: gerador sintético, `init`, importação e reconhecimento da CLI do
README. Reconhecimento da demonstração devolveu status 3 com os bloqueios de formato
e assinaturas não homologados; não houve seleção ou alteração de aprovação.
As aprovações usadas para caminhos positivos existem somente nas fixtures de teste.
O diretório sanitizado ainda não contém PDFs ou gabaritos reais. A ferramenta de
homologação foi testada com material sintético e falha explicitamente se faltarem
arquivos; nenhuma extração financeira real foi executada ou declarada aprovada.
