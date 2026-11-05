# Perfil PASSAREDO / AUTO GESTÃO

Perfil exclusivamente diagnóstico do MVP efêmero. Não autoriza cobrança, CRM, exportação operacional ou integração ACL. Não altera o contrato financeiro dos demais perfis.

## Regra financeira e saída

A condição é `(data_ref - vencimento).days > 60`, em dias corridos. Os dias 59 e 60 ficam fora; o dia 61 é incluído. O campo DIAS da fonte não decide a seleção. A regra usa a decisão expressa do responsável e a referência documental da régua, aba `RÉGUA DE COBRANÇA`, E193; nenhuma vigência operacional é presumida.

O valor exportado vem de VALOR, nunca de ATUAL. Juros, multa, correção e honorários são preservados como dados da fonte e conferidos na composição, sem serem recalculados para atualizar o original. Judicial e acordo não criam novas condições de cálculo ou exclusão. A descrição original é mantida, sem inventar competência mensal. As parcelas finais numeram somente as dívidas efetivamente incluídas, por unidade e vencimento, com desempate estável.

O destino 1030 está configurado com evidência do template: sufixo em `Dados!B2:B2155`, contrato em Y e complemento em G. O cedente e o produto têm localizadores em A e Z. O SHA-256 real da evidência está no perfil de saída. Não se obtém esse código do nome 1028 dos arquivos. A apresentação de quatro dígitos não muda a unidade original ou seu hash de proveniência. Não se presume bloco 0.

A saída mantém a aba Dados, exatamente 30 colunas, cabeçalhos literais, tipos e validação pós-escrita do contrato existente. Nenhuma aba ou coluna adicional foi criada. CPF/CNPJ válido é textual, com zeros preservados; ausência/invalidade não fabrica documento.

A coluna AA mantém o literal `NM_DIVIDA_CEDENTE`, sem espaço final. O template histórico apresenta `NM_DIVIDA_CEDENTE ` com espaço final. O responsável confirmou expressamente a preservação do contrato atual do MVP e o registro dessa diferença histórica; não se declara identidade byte a byte entre esses dois cabeçalhos.

## Identificação e validação

As colunas reconhecem o layout XLSX, mas não comprovam o condomínio. Sem identificação interna, selecionar explicitamente **AUTO GESTÃO · CONDOMÍNIO PASSAREDO** é obrigatório, inclusive para arquivos com hash conhecido. O hash registra a evidência; não substitui a seleção.

A seleção também não substitui a validação do arquivo. A aba Sheet1, os cabeçalhos, a contagem de itens, o fechamento Gerado em e a ausência de fórmulas/abas inesperadas continuam obrigatórios. O sondador mantém limites e rejeição de documentos inseguros, macros e links externos. Não há reconhecimento baseado no nome de arquivo.

## Associação cadastral por lançamento

Cadastro XLSX é opcional e não cria lançamentos, unidades financeiras ou elegibilidade. Cada dívida mantém o responsável da inadimplência. Documento e contatos cadastrais só podem ser aproveitados após conferência da mesma unidade textual e concordância do nome completo.

A comparação nominal aplica NFKD, casefold, remoção de marcas combinantes e colapso de espaços. Ela não faz correspondência aproximada, associação por sobrenome ou remoção de palavras para forçar igualdade. A normalização não transforma a conferência documental em prova jurídica de titularidade.

As retenções são avaliadas nesta ordem:

1. Nome financeiro vazio ou diferente do cadastral após a normalização: reter a associação.
2. Nomes concordantes com indicação de multiplicidade: reter a associação quando o vínculo documental não identifica inequivocamente uma única entidade. CPF individual não resolve dois responsáveis. CNPJ válido também não resolve uma lista de pessoas por si só; a exceção empresarial diagnóstica está descrita abaixo.
3. Resolução documental bloqueante, como documentos válidos conflitantes ou vínculo documental não confirmado: reter a associação.

O mecanismo mantém o nome financeiro e não transfere CPF, telefone ou e-mail nas associações retidas. A linha financeira elegível permanece. Ausência de cadastro também não altera a seleção. Localizadores das colunas documentais são preservados, inclusive para CPF secundário ou alias de cabeçalho. O limite do contrato permanece cinco telefones e três e-mails; excedentes ficam ressalvados na auditoria temporária.

### Baseline auditado: contagens agrupadas no commit 213a5f9

As contagens a seguir são somente agregados de classificação cadastral, sem nomes, documentos, contatos, unidades individuais ou valores financeiros:

| Critério observado | Código | Associações retidas | Unidades |
| --- | --- | ---: | ---: |
| Nomes divergentes após normalização | PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO | 236 | 8 |
| Responsável com marcador de multiplicidade e CPF individual | PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO | 29 | 2 |
| Resolução documental bloqueante adicional | PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO | 0 | 0 |
| Total observado | — | 265 | 10 |

São associações de lançamentos analisados, não dívidas excluídas. Nenhuma linha financeira elegível é removida por esses motivos cadastrais. A classificação conserva o primeiro motivo aplicável; os grupos não devem ser interpretados como todos os possíveis problemas de cada registro.

## Ciclo efêmero e revisão

A tela mostra, sob autenticação e isolamento de sessão, a unidade e os responsáveis das duas fontes para revisão. Essa lista reduzida não inclui CPF, telefone ou e-mail. Ela acompanha o ciclo do resultado em memória, com prazo de 15 minutos, descarte/logout e liberação após respostas ativas. A tela limpa a lista ao baixar, descartar, sair ou substituir a conversão.

Os intermediários são gerados em diretório temporário isolado e removidos antes de disponibilizar o resultado; falha de limpeza não declara sucesso. Não se cria histórico documental permanente. Permanecem configurações do software: perfis, layouts, regras autorizadas e hashes/localizadores de evidência. Nenhum original privado, credencial ou relatório de homologação integra este documento ou as fixtures.

## Testes e limitações

As fixtures em `tests/passaredo` são inteiramente fictícias, independentes dos arquivos privados. Exercitam 59/60/61 dias, DIAS divergente, valor original versus encargos, 30 colunas e tipos, parcelas, seleção explícita, validação estrutural, cadastro opcional, documentos conflitantes, responsáveis divergentes, localizadores documentais, determinismo, autenticação e descarte.

Continuam pendentes as limitações da base: ausência de limite global de RSS, resíduos após encerramento forçado sem recolhimento automático e workers já iniciados que concluem após cancelamento. Cópias do navegador e apagamento forense não são garantidos. Windows deste perfil permanece sujeito à validação própria; nenhuma infraestrutura ACL foi incorporada. Publicação para auditoria não equivale a aprovação operacional.

## Ajustes cadastrais A1 — auditoria

A política cadastral passa a `passaredo_nome_e_unidade_por_lancamento@1.1`. Leitor financeiro, régua de dias, configuração dos perfis, identificadores e exportação universal permanecem inalterados. Não há aprovação de uso operacional.

### Documentos ausentes, inválidos e malformados

Ausência é campo vazio/whitespace ou None. Documentos não vazios só são normalizados quando a representação inteira é um CPF de 11 dígitos ou sua máscara padrão, ou um CNPJ de 14 dígitos ou sua máscara padrão. Os verificadores fiscais existentes continuam obrigatórios. Letras, rótulos arbitrários, separadores fora da máscara e dígitos verificadores inválidos não são corrigidos pela remoção de caracteres. Nenhum zero é criado para completar um documento; os zeros existentes de um documento válido são mantidos.

Documento rejeitado não vira documento principal nem evidência atribuída a um responsável. O valor recebido, sua coluna e linha são preservados como ressalva na evidência cadastral original temporária. A conversão das demais linhas continua e o Excel deixa o documento vazio quando não houver outra evidência válida. Uma evidência válida em outra coluna pode ser aproveitada, mantendo o alerta da rejeitada; dois documentos válidos conflitantes continuam retidos. A associação também revalida documentos recebidos em canônicos, sem confiar apenas no tipo declarado.

A tela informa a quantidade de documentos rejeitados no **cadastro recebido**, sem exibir seus valores no resumo. Esse total não significa que todos correspondam a unidades financeiras desta conversão.

### Telefones completos sem DDD

Nas colunas FONE/CELULAR, um token completo de oito ou nove dígitos é aceito com DDD vazio, incluindo zeros iniciais. Dez/onze dígitos ou DDD explicitamente separado mantêm o DDD recebido. O prefixo +55 só é aceito com o restante completo e DDD presente. Não se herda o DDD de outro token, telefone, coluna ou pessoa.

Tokens são separados por vírgula, ponto e vírgula, barra ou quebra de linha. Cada token precisa casar integralmente com o formato admitido. Não se procura um sufixo válido dentro de uma sequência maior, nem se removem letras arbitrárias para fabricar telefone. Valores não interpretados continuam na evidência original; a ausência de extração não cria um número substituto. Os limites de cinco telefones e três e-mails da saída continuam os mesmos.

### Empresa com E versus responsáveis múltiplos

E não é, sozinho, prova de duas pessoas. Para aceitar o CNPJ de um nome empresarial contendo E, são exigidos: mesma unidade textual, nome completo concordante nas duas fontes, somente evidências CNPJ fiscalmente válidas e designador empresarial explícito ao final (`LTDA`, `LIMITADA`, `EIRELI`, `S/A`, `S.A.`, `ME` ou `EPP`), sem separadores de uma lista. Conflitos documentais continuam bloqueando a associação. O designador S/A não é interpretado como separação de pessoas.

Uma lista explícita com `/`, `;` ou quebra de linha não recebe CNPJ individualmente só porque o número é válido. Nome com E sem prova empresarial suficiente também fica em revisão. A regra não classifica juridicamente as pessoas nem consulta cadastro empresarial externo: casos não demonstrados por esse recorte documental exigem conferência humana. A retenção é da associação cadastral; nenhuma empresa ou pessoa perde uma dívida elegível por esse motivo.

### Diferença demonstrada em relação ao baseline

Os 265 casos anteriores permanecem retidos. Uma associação adicional foi conservadoramente retida: nome concordante entre fontes, CNPJ fiscalmente válido, mas separador de multiplicidade sem prova suficiente de vínculo empresarial único. Essa associação era liberada pelo código anterior porque o teste de multiplicidade só considerava CPF. Não se afirma que a fonte prove dois indivíduos; registra-se a falta de comprovação para transferir documento/contatos.

| Motivo | Baseline | A1 | Unidades A1 |
| --- | ---: | ---: | ---: |
| Nomes divergentes após normalização | 236 | 236 | 8 |
| Multiplicidade sem vínculo documental suficiente | 29 | 30 | 3 |
| Total cadastral retido | 265 | 266 | 11 |

A comparação foi reexecutada sobre as mesmas fontes, sem expor nomes, documentos, contatos ou unidades individuais. Dois documentos do cadastro completo foram rejeitados e preservados; suas unidades não fazem parte do lote financeiro. Essa correção não reduz o conjunto financeiro nem altera a regra dos 60 dias.

### Validação local A1

- 173 regressões direcionadas aprovadas (Passaredo/A1, fluxo efêmero e XLSX/Win).
- Suíte Linux/Python 3.12: **2.031 aprovados**, zero falhas, erros ou skips; um warning de depreciação Starlette/AnyIO. Nenhum teste desabilitado.
- Chromium real, com dados inteiramente fictícios: documento malformado sem falha global, aviso sem expor o valor rejeitado, telefone sem DDD/zero inicial, empresa com E e CNPJ concordante, CNPJ retido para lista de responsáveis, 30 colunas/AA literal, download protegido e descarte aprovados.
- Homologação privada temporária: **2.154 linhas elegíveis com e sem cadastro**, sem divergências de unidade, vencimento ou valor; nomes financeiros, soma do original, parcelas e hashes reais preservados. A área temporária foi descartada. Os agregados não incluem dados pessoais.
- Publicação autorizada exclusivamente para auditoria externa; aprovação técnica final e merge permanecem pendentes.
