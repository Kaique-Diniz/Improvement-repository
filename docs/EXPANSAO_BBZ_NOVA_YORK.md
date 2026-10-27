# Expansão BBZ — NOVA YORK PENTHOUSES

## Entrega e limites

Primeira extensão pós-MVP, autorizada em 27/10/2026 e implementada somente para
NOVA YORK PENTHOUSES. O leitor pertence à família documental BBZ XLSX, não a um
condomínio específico. Apenas o perfil NOVA YORK foi habilitado na interface.
TREE/Habita e PLAZA/FL mantêm suas gramáticas, regras e contratos anteriores.

**Uso exclusivamente diagnóstico, não homologado para produção.** Nenhum plano
operacional foi aprovado/ativado, nenhuma cobrança é enviada e a rota de
exportação operacional continua retornando HTTP 409. Os demais quatro
condomínios permanecem fora do processamento automático.

As primeiras revisões deste documento registraram fontes ausentes. Posteriormente
foram recebidos os 15 originais. Tamanhos, SHA-256 e cópias íntegras foram
inventariados fora do Git, com permissões restritas. Relatórios nominais,
financeiros e fiscais detalhados ficam exclusivamente nessa área privada.

| Fonte NOVA YORK recebida | Uso nesta etapa |
|---|---|
| `884 - NOVA YORK PENTHOUSES -Inadimplentes.xlsx` | Reconhecimento, leitura, origem por célula e reconciliação. |
| `884 - NOVA YORK PENTHOUSES - Cadastro.pdf` | Conferência privada de identidade fiscal; **não** extração cadastral completa. |
| `884 - NOVA YORK PENTHOUSES - Template.xlsx` | Referência histórica, sem substituir dados extraídos ou definir elegibilidade. |
| `REGUA DE COBRANÇA -26.10.2026.xlsx` | Vinculação documental do requisito extrajudicial, sem importar acessos ou condições administrativas. |

O nome efetivamente recebido da régua difere do nome inicialmente solicitado
com o sufixo `ATUAL`. Seu hash próprio foi calculado; não se presume identidade
com outra versão. O requisito NOVA YORK está na aba `RÉGUA DE COBRANÇA`, célula
E312. Conteúdo administrativo de outras células não foi transformado em regra.

## Arquitetura efetivamente reutilizada

| Componente | Implementação |
|---|---|
| Sondagem | `SondadorLocal`: limites de arquivo/ZIP/XML, proteção contra macros e vínculos externos, sem executar fórmulas. |
| Leitor | `readers/bbz_xlsx.py`: família `bbz_inadimplencia_xlsx_v1`, sem prazo de cobrança ou nome de condomínio embutidos. |
| Contrato operacional | `Leitor`, `FonteProtegida`, `ContextosCatalogo`, `RegistroLeitores` e caso de uso de leitura existentes; adaptador XLSX separado da validação PDF. |
| Domínio | `Unidade`, `Pessoa`, `Boleto`, `Composicao`, `Apontamento`, `Origem` e ressalvas existentes, sem alteração dos schemas históricos. |
| Motor | Mesmo avaliador determinístico; configuração diagnóstica versionada em `web/perfis.json`. Não cria outro motor ou aprovação formal. |
| Saída | Comparador, projeção A/B, `LinhaExportacao` e escritor universal existentes. |
| Interface | Upload comum aceita PDF textual ou XLSX, identificação por conteúdo e cadastro privado de endereço por administradora/condomínio. |

O registro atual recebe um adaptador adicional, sem criar um framework genérico
de plugins nesta etapa. A futura extensão por família pode registrar sondador,
reconhecedor, leitor financeiro, leitor cadastral opcional, identidade,
fechamento e comparador independentes. PDF, XLSX e futuros XLS precisam de seus
próprios adaptadores; o núcleo de cobrança e o contrato de saída são comuns.

## Assinatura, identidade e proveniência

A família exige uma única aba financeira, A1 com período completo válido, A2 com
`Condomínio: código - nome`, agrupamentos `Bloco: ... Unidade: ... nome`,
cabeçalhos posicionais de 12 colunas e fechamentos completos.

```text
A Recibo | B Vencimento | C Emissão | D Conta | E Histórico | F Moeda
G Valor Original | H Valor Principal | I Multa | J Correção | K Juros | L Total
```

Cada recibo termina em `Total do Recibo:`, a unidade em `Total Geral da Unidade:`
e o relatório em contagem de unidades mais `Total do condomínio :`. A moeda é
verificada. Fórmulas, colunas extras preenchidas, múltiplas abas, cabeçalhos
ambíguos, duplicidades ou fechamentos inconsistentes impedem o processamento.
Não há reconhecimento por nome do arquivo, nome da aba ou palavras isoladas.

A identidade NOVA YORK exige nome interno compatível e código administrativo
**287**, preservado como atributo auxiliar do sistema de origem. O código
**easyCollector 884**, confirmado pelo responsável e coerente com os
identificadores da referência histórica, é a identidade prioritária de integração
do condomínio. Código de origem, código easyCollector, unidade e recibo são
identificadores distintos. A administradora BBZ e o CNPJ do condomínio foram
vinculados documentalmente no dossiê privado; o CNPJ foi confrontado entre régua
e cabeçalho cadastral. Esse documento fiscal do edifício não ocupa o CPF do
contato da unidade. Nenhum código de outro condomínio foi mapeado automaticamente.

As origens XLSX guardam hash, leitor/versão, linha e identificador como
`xlsx_aba1_r7_G`. Não há página PDF fictícia. As ressalvas privadas conservam
nome original da aba, células, cabeçalhos, recibo bruto, conta, descrição, seis
valores, formatos numéricos e os fechamentos. A interface apresenta aba/linha/
células. Arquivos com erro continuam privados e a ocorrência informa código e
localização disponível, sem imprimir valores ou nomes em logs.

## Identidade persistente e unidades alfanuméricas

`domain/integration_identity.py` define o catálogo tipado e versionado. O JSON
persistente `web/identidades_integracao.json` relaciona os códigos easyCollector
363/567/696/788/884 a administradora, condomínio, nomes documentais e códigos
auxiliares conhecidos. Esses registros **não habilitam leitores ou regras**.
Somente NOVA YORK possui perfil financeiro nesta rodada.

A porta `RepositorioIdentidadesIntegracao` separa a consulta do armazenamento;
o adaptador JSON reutiliza o decodificador estrito existente, rejeita chaves
repetidas e valida unicidade de código destino e vínculo administradora/condomínio.
Código auxiliar pode repetir entre identidades: ele não é chave global do
destino. Esses atributos identificam o condomínio no sistema de origem; não se
confundem com unidade, conta, código do cliente ou número de recibo. Associação exige conteúdo compatível e não escolhe automaticamente
entre candidatos ambíguos. Mudança/conflito do código auxiliar conhecido exige
revisão; nome do arquivo nunca decide o código easyCollector.

O reconhecimento captura um snapshot do vínculo com versão/hash do catálogo,
código easyCollector e código de origem observado. Isso aparece na auditoria,
manifesto e contexto da interface. A relação sobrevive a reinício porque vem da
configuração persistida, não é reconstruída a partir do nome do upload. JSON é
a implementação atual da porta; outro repositório pode fornecer o mesmo contrato.

O codificador compartilhado `bloco_unidade_textual`, ainda não atribuído a
qualquer outro condomínio ativo, prepara a forma literal
`Bloc{BLOCO}-Uni{UNIDADE}`. Aceita bloco numérico ou alfabético e unidades
numéricas, alfanuméricas ou palavras. Usa campos originais, preserva zeros e
capitalização, sem conversão obrigatória para inteiro. Exemplos de contrato:
`Bloc0-UniBOXE`, `BlocA-Uni0017` e `BlocB-Uni00X1`. O mesmo código serve de
CEDENTE e contrato; complemento permanece individual.

A largura numérica só é aplicada mediante configuração explícita
`tratamento_unidade_numerica=largura_comprovada`, com a evidência exigida pelo
perfil. Por exemplo, uma origem `000017` pode ser apresentada como `0017` se a
largura quatro tiver sido comprovada; a origem continua intacta. O padrão literal
preserva `000017`. Palavras não recebem preenchimento numérico, bloco zero ou
mudança de caixa presumidos. Espaços/controles ambíguos são retidos.

Colisões após a codificação são detectadas antes da materialização e impedem o
XLSX. Perfis de outro condomínio/administradora continuam recusados. O piloto
NOVA YORK mantém sua codificação comprovada `BL-UNI....-884`: não se aplica a ele
o estilo de outro condomínio nem o código 287 como CEDENTE.

**INNOVA — divergência de bloco:** fonte e histórico confirmam o conflito em
dois recibos da unidade alfanumérica citada pelo responsável: bloco INAT na
origem e bloco 0 na referência. O dossiê privado registra
hashes/localizações e estado de revisão, sem equivalência autorizada. A forma
literal preservaria INAT. Não há correção automática nem mapeamento INAT→0,
e o leitor financeiro desse condomínio permanece desabilitado. Uma equivalência
exigirá mapeamento explícito autorizado em etapa própria, sem exceção embutida
no leitor ou no motor de cobrança.

## Mapeamento e reconciliação financeira

- G alimenta o original de cada componente; o G do subtotal comprovado alimenta
  `Boleto.composicao.total_original`. H permanece distinto e auditado como
  principal. I/J/K alimentam multa/correção/juros. L é o atualizado, preservado na
  auditoria e nunca usado para substituir silenciosamente o original exportável.
- Para cada componente, H + I + J + K deve coincidir exatamente com L. Para
  cada recibo, suas seis colunas devem coincidir com a soma dos componentes;
  depois se conferem unidade, contagem e total do condomínio nas mesmas colunas.
- Números da planilha são convertidos para Decimal antes de qualquer cálculo.
  Valores não finitos, inválidos ou com frações de centavo são rejeitados, sem
  ajuste por aproximação. Negativos, zeros e centavos continuam nas composições.
- Um recibo com vários componentes gera no máximo uma dívida. ID do recibo,
  bloco/unidade, conta e código easyCollector não são intercambiáveis. Repetição do
  mesmo recibo na mesma unidade é retida; em unidades distintas, mantém IDs
  separados. A repetição na continuação dos componentes é validada explicitamente.
- Emissões numéricas sem convenção comprovada ficam em `emissao_original`, com
  aviso; não se inventa data completa. Competência ausente continua ausente.
  CPF/CNPJ e contatos não extraídos ficam vazios, com os alertas existentes.
- A/AJ/J/AE são tokens exatos do campo Recibo, no namespace BBZ. Descrições,
  legendas e nomes não viram apontamentos. Não se herdam exclusões TREE por
  marcador, centavo, garantidora ou situação jurídica.

## Regra diagnóstica e resultados privados

Decisão expressa de 27/10/2026: NOVA YORK exige **mais de 60 dias corridos**,
operador `gt`. Com referência explícita **2026-10-26**, atraso de 60 dias não
satisfaz o prazo; 61 dias satisfazem, sujeitos aos bloqueios. Não há filtro
judicial adicional. Judicial de 90 dias e observações de negociação são apenas
informação documental, sem autorização para implementar medidas.

Início/fim de vigência operacional continuam não comprovados (`null`), com
ressalva visível. A data nominal da régua não é início de vigência. Trata-se de
configuração **diagnóstica**, não de plano formal aprovado ou ativo.

| Conferência real | Resultado |
|---|---:|
| Unidades financeiras | 7 |
| Recibos | 29 |
| Componentes | 260 |
| Recibos acima de 60 dias / correspondências financeiras únicas | 26 / 26 |
| Recibos fora do prazo | 3, em 2 unidades |
| Modo A | 26 dívidas |
| Modo B | As mesmas 26 dívidas + 2 cadastros |

Os totais originais completo, selecionado e excluído coincidiram exatamente com
as expectativas fornecidas pelo responsável; valores detalhados e recibos
excluídos com localizadores estão somente no relatório privado. Não houve ajuste
de dados para atingir as quantidades ou os valores da referência.

## Referência histórica e divergências preservadas

O template usa nome de aba diferente de `Dados`; apenas para BBZ, o comparador
aceita uma única aba com os 30 cabeçalhos comprovados. A saída continua sendo
`Dados`, com A:AD, cabeçalhos sem espaços finais e dados textuais preservando
zeros. Recibos distintos não são somados para imitar uma linha da referência;
correspondências ambíguas continuam não avaliáveis.

A codificação comprovada nas 26 correspondências é: cedente BBZ, complemento
`BL-UNI` + unidade com quatro dígitos e CEDENTE/contrato com o sufixo `-884`.
O bloco original `0` continua no canônico; a omissão na apresentação é uma
configuração explícita NOVA YORK. Bloco não mapeado ou unidade alfanumérica não
recebem código inventado. Parcelas são sequenciais por contrato.

A referência contém sete cadastros em cinco identificadores, com multiplicidades
1/1/1/1/3. As cinco unidades cadastrais históricas não estão entre as sete
unidades do relatório financeiro atual. Essa política histórica difere do modo
B atual: não se copiam linhas
nem se importam todas as unidades do cadastro complementar. Os dois cadastros do
B atual pertencem às unidades com recibos não elegíveis; Y:AD ficam vazias.

Nomes do cabeçalho financeiro são preservados. A referência tem documentos de
contato que não estão nessa fonte: não são copiados. Rótulos históricos de
`COTA MM/AAAA` ou de reembolso não são convertidos em competência comprovada;
a saída usa o identificador original do recibo quando não há competência.
Endereço só vem do cadastro privado autorizado e prevalece em todas as linhas,
com complemento individual e originais na auditoria. O teste no navegador usou
endereço inteiramente fictício em servidor isolado, sem configurar endereço real
presumido. Perfis privados antigos sem NOVA YORK recebem o perfil integrado por
fallback, sem sobrescrever o arquivo privado nem misturar endereço TREE/PLAZA.

### Classificação do histórico frente ao contrato atual

O comparador mantém o confronto financeiro anterior e acrescenta
`contrato_atual.divergencias`, com linha de origem, campos afetados, categoria,
código e indicação de revisão humana. Nenhum registro ou decisão é alterado.
Os contadores representam ocorrências; uma mesma linha pode ter diferenças de
naturezas distintas.

| Categoria | Tratamento |
|---|---|
| `formato_resolvido` | Aba, cabeçalhos sem espaços, campos textuais, parcelas sequenciais, rótulo atual e cadastros duplicados são tratados pelo contrato universal. Não copiar convenção histórica. |
| `cadastral` | Contatos, nomes, endereços, documentos ou seleção cadastral diferem. Manter fontes atuais e opcionais vazios quando ausentes. |
| `identificador` | Código/unidade não vinculados inequivocamente ou codificação divergente. Não presumir bloco/equivalência; revisão quando necessária para associar. |
| `financeira` | Valor, vencimento ou seleção histórica diferem da fonte/régua atual. Registrar para revisão sem recalcular ou copiar o histórico. |
| `sem_explicacao` | Assinatura inválida, referência não avaliável ou recibo sem vínculo comprovado. Exigir investigação sem aproximação. |

Na validação real NOVA YORK: A tem 38 ocorrências de formato, 33 cadastrais e
sete de identificador; B tem 31, 33 e sete, respectivamente. Não há divergência
financeira nem ocorrência sem explicação. As sete de identificador se referem
às unidades cadastrais históricas fora do relatório atual, não a perda de vínculo
das 26 dívidas, que continuam coincidentes. Revisar uma referência histórica
não equivale a aprovar mudança de fonte ou liberar bloqueio crítico.

## Demais condomínios — levantamento, não habilitação

Apenas estrutura/metadados foram inspecionados, sem executar suas réguas ou
implementar seus leitores operacionais. Prazos abaixo são os informados no
pedido; seus operadores e vigências não foram presumidos. Judicial não é filtro
extra de seleção.

| Referência | Extrajudicial / judicial informados | Pendências |
|---|---|---|
| 363 — INNOVA BLUE | 31 / 90 dias | Conferidos 108 cabeçalhos de unidade, 645 subtotais de recibo, seis originais zero, 14 componentes negativos; histórico com 639 dívidas e seis cadastros. Marcadores A/AJ/J/AE presentes. Vínculo INAT versus 0 e os dois recibos citados continuam pendentes, sem correspondência presumida. |
| 567 — EDIFÍCIO WIN | 31 / 61 dias | Conferidos 45 unidades e 672 recibos, componentes negativos e A/J. Datas históricas, centavos em campos financeiros, restrições de outro jurídico/vagas e template XLS exigem análise própria. Não presumir que um componente/encargo de centavo seja o original integral do recibo. |
| 696 — NOVA REBOUÇAS | 30 / 90 dias | Conferidos 12 unidades e 102 recibos, A/J; cadastro anterior, papéis de proprietário/locatário/pagador e template XLS permanecem para etapa própria. |
| 788 — JARDINS DO BRASIL ABROLHOS | 60 / 90 dias | Conferidos 90 unidades e 216 recibos; histórico com 103 dívidas. O arquivo chamado Cadastro.xlsx possui estrutura financeira. Identidade do subconjunto ABROLHOS e não selecionados exigem validação antes de habilitar. |

Os XLS legados foram preservados e não lidos por openpyxl. Informações
administrativas, credenciais e contatos internos da régua não foram incorporados
a perfis, fixtures ou documentação versionada.

## Testes e próxima etapa

**1.499 testes aprovados**: 1.439 regulares + 60 suítes explícitas, incluindo
73 casos da extensão inicial e 57 novos desta atualização de identificadores. Oito verificações de schemas aprovadas. Cobertura sintética:
múltiplos componentes, negativos/zero/centavos, marcadores e namespace, datas
históricas/atuais, fronteiras 60/61, duplicidades, cabeçalhos ambíguos, fórmulas,
subtotais, hash, contexto de catálogo, origem XLSX, isolamento, críticos, A/B,
endereço persistente, perfil privado antigo e comparação por recibo.

O navegador foi validado com upload real NOVA YORK A/B, referência, downloads,
endereço fictício, dados textuais e bloqueio operacional. Regressores reais
TREE/PLAZA confrontam canônicos e XLSX com as versões anteriores; detalhes ficam
na área privada. Nenhum arquivo de cliente compõe as fixtures públicas.

### Etapa seguinte proposta — Cadastro Geral PDF BBZ

Somente com autorização posterior:
1. Inventariar assinatura, identificação fiscal, data, número de unidades,
   colunas, continuidade/paginação e possíveis variações do Cadastro BBZ.
2. Separar proprietário, locatário, pagador e nomes múltiplos; um documento
   válido no registro da unidade não exige atribuição individual a um nome.
3. Extrair CPF/CNPJ e contatos opcionais com seus valores brutos e origens;
   validar documentos sem inventar, corrigir ou escolher conflitos válidos.
4. Cruzar administradora + condomínio + bloco + unidade pelo enriquecimento
   existente, preservando dados financeiros e prioridade do endereço cadastrado.
5. Conferir data cadastral anterior e divergência de quantidade total de
   unidades entre régua/cadastro, sem trocar automaticamente a fonte preferida.
6. Acrescentar fixtures sintéticas, confrontos privados e regressão completa.
   Não habilitar automaticamente os outros quatro condomínios.

Nesta entrega, selecionar um Cadastro PDF BBZ no fluxo financeiro gera aviso de
erro explícito: remover o complemento e processar o XLSX sem ele. Não é ignorado
silenciosamente. A etapa cadastral completa não foi iniciada. Sem push/merge até
autorização, sem cobrança, exportação operacional ou homologação de produção.
