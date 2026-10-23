# Laboratório do pacote fornecido — 21/10/2026

**Revisão posterior à aprovação da etapa sintética:** as 21 células foram
conferidas individualmente. Resultado: 17 inconsistências do gabarito pendentes
e quatro diferenças de representação de datas esclarecidas; nenhum erro de
extração/normalização comprovado. Não foram alterados leitores ou regras.
Veja [a análise por célula, evidências e novos testes](REVISAO_DIVERGENCIAS_SINTETICAS.md).

O pacote `Homologacao_Sanitizada_Conversor` foi instalado em
`tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor/`. Foram lidos o README,
`esperado/resultado_esperado.json` e `documentacao/PROMPT_PARA_CODEX.md`. O prompt
anexo é documentação do cenário; a solicitação e as decisões explícitas do usuário
definem o escopo autorizado. Nenhum documento original foi utilizado.

Os nove arquivos do pacote permanecem idênticos por SHA-256. Não foram comitados.
SHA-256 do ZIP recebido: `e24de2eefb7f664de16828255536719cb5e2d37f5e999bef3578ae69472d60f2`.
Os nove arquivos locais também foram conferidos byte a byte com esse ZIP.
As fontes são documentos **recriados do zero**, não cópias sanitizadas que comprovem
compatibilidade com os PDFs originais. Os dois formatos continuam rascunhos.

## Resultados com data fixa 20/10/2026

| Caso | Unidades | Boletos únicos | Dívidas exportadas | Cadastrais | Total exportado |
|---|---:|---:|---:|---:|---:|
| Habita | 4 | 6 | 2 | 0 | R$ 910,00 |
| FL | 4 | 5 | 2 | 3 | R$ 1.880,00 |

As 14 verificações do JSON esperado conferem. A conferência independente do resumo
FL também confere para os cinco boletos: torre/unidade, identificador, vencimento,
competência e subtotal. Nenhum saldo acumulado foi exportado como valor individual.

| Boleto sintético incluído | Valor original | Continuidade |
|---|---:|---|
| 80000101 | R$ 570,00 | Página 1 |
| 80000105 | R$ 340,00 | Páginas 2–3, um único boleto |
| 900101 | R$ 1.200,00 | Página 1 |
| 900104 | R$ 680,00 | Páginas 1–2, um único boleto |

Habita exclui integralmente as unidades `1/000094` (boleto de R$ 0,01) e
`2/000015` (apontamento AJ); o boleto recente da outra unidade é adiado. Isso
aplica exclusivamente a regra de teste fornecida, sem interpretar a régua real.
FL adia três boletos e gera uma linha cadastral por unidade com algum boleto
adiado: `A/0041`, `B/0012`, `A/0142`. A unidade do boleto 900104 no documento é
`G/0072`; a menção anterior a G/0093 na pergunta não corresponde à fonte.

CPF ausente/invalidado permanece vazio: quatro alertas por unidade na FL,
mesmo havendo cinco linhas; dois alertas na saída Habita. A restrição histórica a CPF foi substituída pela atualização geral de 21/10/2026: CPF/CNPJ válido como texto na coluna CPF. As fixtures originais continuam sem documento válido.

## Divergências encontradas, sem ocultação

As 30 colunas foram comparadas, célula a célula, nos dois Excel. Há **17 células
com conteúdo divergente**, todas de contato; nenhuma em valor, vencimento,
elegibilidade, titular final ou codificação configurada neste cenário.

| Caso | DDD1 | FONE1 | EMAIL1 | Total |
|---|---:|---:|---:|---:|
| Habita | 1 | 1 | 2 | 4 |
| FL | 4 | 4 | 5 | 13 |

- Os gabaritos deixam telefones vazios, embora os PDFs contenham contatos. A
  saída conserva os contatos comprovados: duas células Habita e oito FL divergem.
- Sete células de e-mail diferem da fonte, incluindo e-mails preenchidos no
  gabarito quando a fonte não fornece esse dado. A saída conserva o conteúdo
  documental ou a célula vazia, sem copiar o gabarito como fonte cadastral.
- Há ainda **quatro diferenças de representação**, separadas das 17 anteriores:
  `VENCIMENTO` é data nativa no Excel gerado e texto ISO no gabarito, com o mesmo
  dia. O contrato do repositório exige data nativa; falta validar o importador.

Detalhamento sem valores pessoais, com coluna, boleto, arquivo lógico, página,
linha de origem e hashes dos valores, fica em `relatorio_divergencias.json`.
Localização das diferenças de contato nesta cópia:

| Caso | Linha Excel | Campos | Fonte e localização |
|---|---:|---|---|
| Habita | 2 | DDD1, FONE1, EMAIL1 | Inadimplência, p. 1, linha 5 |
| Habita | 3 | EMAIL1 | Inadimplência, p. 2, linha 4 (titular sem e-mail) |
| FL | 2 e 3 | EMAIL1 | Cadastro, p. 1, linha 6 |
| FL | 2 e 3 | DDD1, FONE1 | Cadastro, p. 1, linha 7 |
| FL | 4 | EMAIL1 | Cadastro, p. 1, linha 8 |
| FL | 4 | DDD1, FONE1 | Cadastro, p. 1, linha 9 |
| FL | 5 | EMAIL1 | Cadastro, p. 1, linha 10 |
| FL | 5 | DDD1, FONE1 | Cadastro, p. 1, linha 11 |
| FL | 6 | EMAIL1 | Cadastro, p. 1, linha 12 (titular sem e-mail) |

Não se deve alterar fontes nem fabricar contatos para eliminar essas diferenças.
O gabarito cadastral precisa ser revisto pelo responsável pelos exemplos.

## Decisões confirmadas e limites de interpretação

1. **Somente laboratório:** uma linha cadastral por unidade com algum boleto
   ainda fora do prazo. Pode coexistir com dívida elegível na mesma unidade.
2. **Somente laboratório:** priorizar Cadastro Geral no conflito de titular de
   `B/0012`, emitindo `TITULAR_DIVERGENTE_RESOLVIDO_NO_LAB`. A auditoria salva o
   modelo original antes do enriquecimento, o modelo final e a origem da decisão.
   O comportamento padrão da função de enriquecimento permanece bloqueante.
3. Endereço didático, mapeamento de torres, parcela 1, nomes de produto/cedente e
   sufixo TREE estão explicitamente em `config_exemplos/laboratorio_pacote.json`.
   São perfis montados para reproduzir o exemplo, inclusive com metadados do
   gabarito; sua concordância **não é validação independente desses cadastros**.
4. A coluna Habita chamada `Emissao` contém `YYYYMM`: somente neste cenário é
   conservada como competência. Não foi inventada data diária de emissão. É
   necessária confirmação da semântica na fonte operacional.
5. `W002A` e `W045A` identificam relatórios, não condomínios distintos. Habita
   não informa administradora documentalmente; FL não fornece código/CNPJ forte
   de condomínio. O contexto de identidade é configurado explicitamente no lab.

O reconhecimento identifica automaticamente um único layout elegível por
conteúdo, independentemente do nome do arquivo. Leitores Habita e FL são separados
e reutilizáveis com contexto configurado. A seleção operacional permanece
**desconhecida/bloqueada por ausência de homologação**; nenhum catálogo, assinatura
ou regra foi promovido a aprovado. O comando de laboratório permite a simulação
explicitamente solicitada, sem liberar o fluxo operacional.

## Código e verificações

- `readers/{habita,fl,cadastro,text_support}.py`: gramáticas determinísticas,
  validação de totais/saldos, continuidade explícita e proveniência.
- `application/enrichment.py`: associação pela chave condomínio/bloco/unidade,
  resolução explícita de titular e alerta auditável.
- `rules/laboratory.py`: apenas regras sintéticas, valores Decimal, corte estrito
  de prazo e namespace de apontamentos.
- `export/{build_lines,xlsx}.py`: composição das linhas e XLSX atômico com tipos
  nativos, 30 colunas, texto literal contra fórmulas e verificação dos centavos.
- `laboratorio/`: configuração, execução isolada, comparação de todas as células,
  conferência do resumo e relatórios sem valores de contato.
- `tests/test_laboratory_*.py`: 46 testes pequenos independentes do anexo.
- `tests/homologacao/pacote_suite.py`: 25 testes explícitos do pacote local.

```bash
.venv/bin/python -m pytest -q
# 222 aprovados, incluindo os 46 novos testes independentes do anexo
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py
# 25 aprovados, incluindo detecção das divergências existentes
.venv/bin/python -m pytest -q tests/homologacao/revisao_suite.py
# 28 aprovados na revisão individual posterior
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

Foram testados também erro de soma, desconto negativo, duplicação de componente,
continuidade incompleta/divergente, idade 29/30/31 dias, namespace A/AJ/J,
documentos ausentes/inválidos (inclusive CNPJ inválido), precisão incompatível com Excel e proteção contra sobrescrever
fixtures. Na integração, foram usados gabaritos e resumos alterados **em cópias
temporárias**, confirmando que diferenças são detectadas e que valores esperados
não alimentam o cálculo. Fontes desconhecidas, assinaturas ambíguas e identidade
incompatível bloqueiam a geração do respectivo Excel. Repetir o pacote com mesma
configuração e data produz os mesmos bytes nos artefatos.

## Reproduzir e encontrar a saída

```bash
.venv/bin/python -m conversor.laboratorio \
  --pacote tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor \
  --saida dados/homologacao_pacote_nova_execucao
```

Saída final desta entrega: `dados/homologacao_pacote_final/`. Contém
`habita_resultado_laboratorio.xlsx`, `fl_resultado_laboratorio.xlsx`,
`RELATORIO.md`, `relatorio_divergencias.json` e auditorias JSON por caso.
O comando retorna **1**, pois as 17 divergências de contato continuam abertas.
Testes verdes comprovam a detecção correta, não uma comparação integral sem falhas.
Os arquivos de dados e auditoria ficam locais, ignorados pelo Git. Não houve push.

## Próximos ajustes e homologação pendente

- Revisar os sete e-mails e a omissão dos telefones nos gabaritos; fornecer nova
  versão revisada sem substituir silenciosamente as fixtures recebidas.
- Confirmar perfis reais, regras versionadas e semântica de datas/apontamentos;
  as duas decisões deste laboratório não valem automaticamente para produção.
- Fornecer PDFs representativos sanitizados preservando estrutura do original:
  Habita/TREE e FL/Plaza completos, com continuações, mais Cadastro Geral FL e
  planilhas por blocos A–G coerentes. Incluir versões distintas e outro condomínio
  de cada administradora para verificar reutilização de formato.
- Fornecer gabaritos canônicos revisados, com origem por boleto/componente,
  assinatura e identidade documental confiáveis; datas dos cadastros precisam
  permitir decidir conflitos temporais.
- Homologar importação controlada no destino: CPF vazio, linhas cadastrais,
  zeros, datas/valores nativos e espaço final em `NM_DIVIDA_CEDENTE `.

Não houve validação de PDF rasterizado, OCR, layouts reais ou variações fora das
gramáticas sintéticas. Não há interface de cobrança, envio, importação no destino
ou aprovação para produção. O trabalho encerra este laboratório; novas fases
operacionais dependem de autorização posterior.
