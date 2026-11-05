# Forest Hill — AUTO GESTÃO, diagnóstico efêmero

Implementação sobre `e479d2362df85ee196ed0b0ba472c6fd56278e06`, na branch `feat/forest-hill-auto-gestao-efemero`. Publicação autorizada para auditoria externa, sem merge ou aprovação operacional.

## Identidade e leitura

O perfil `forest_hill` exige seleção explícita. O layout de 11 colunas é compartilhado com o Passaredo e não comprova condomínio. Nome de arquivo e hash conhecido não substituem essa seleção. Tanto a inadimplência quanto o cadastro são submetidos à gramática própria de unidade.

O adapter reutiliza os leitores tabulares e canônicos aprovados do Passaredo, incluindo as validações cadastrais A1, sem modificar esses componentes. Os códigos de evidência `PASSAREDO_*` e o identificador da política A1 permanecem como identificação do componente reutilizado; contexto, condomínio, hashes e unidades são segregados. Os resultados do novo perfil usam `cadastro_forest_hill` e `revisao_cadastral_forest_hill`.

A estrutura exige aba única `Sheet1`, colunas reconhecidas, contagem de itens coincidente e data/hora de geração válida. Fórmulas, abas inesperadas, conteúdo após fechamento e estrutura ambígua são rejeitados. A contagem não é fixada artificialmente em 1.631: o fechamento precisa coincidir com as linhas efetivas de cada arquivo.

`VALOR` é o original exportado. Juros, multa, correção, honorários e atualizado permanecem como evidências separadas, sem recalcular os valores. O hash de proveniência continua calculado sobre os bytes reais de cada entrada.

## Regra provisória autorizada

A régua de 04/11/2026, aba `RÉGUA DE COBRANÇA`, linha 144, documenta prazo extrajudicial de 30 dias e judicial de 60 dias. Somente esses critérios necessários foram extraídos; observações confidenciais e credenciais não foram copiadas.

O diagnóstico usa provisoriamente `(data_ref - vencimento).days > 30`, em dias corridos. Exatamente 30 dias permanece fora da seleção até confirmação do responsável. A inclusividade do limite e a vigência operacional ainda exigem aprovação. O prazo judicial não acrescenta um segundo filtro. O campo DIAS é preservado e confrontado, mas não decide a seleção. Acordos e cobranças especiais não introduzem regras de cálculo ou exclusão.

## Codificação documental

| Unidade textual | Complemento |
| --- | --- |
| `AV.P02 231` | `AVP02-UNI231` |
| `RUA 18 347` | `RUA18-UNI0347` |

A gramática é explícita: `AV.P` + dois dígitos + espaço + três dígitos; ou `RUA` + espaço + dois dígitos + espaço + um a três dígitos. Na segunda forma, a apresentação da unidade é preenchida até quatro dígitos. Não se extrai um número arbitrário de outros textos. A unidade textual permanece no canônico, sem presumir bloco zero. Colisões de codificação entre unidades distintas bloqueiam a saída, em vez de fundir objetos.

CEDENTE e NM_CONTRATO_CEDENTE são o complemento acrescido de `-CONDOMINIO RESIDENCIAL FOREST HILL`. Produto e administradora são documentados pelo template. O número 3181 no nome dos arquivos não é usado como código de integração.

## Parcelas e rótulos

A saída mantém 30 colunas e AA literal `NM_DIVIDA_CEDENTE`, sem espaço final. O template histórico contém esse espaço: a diferença é registrada, sem alterar o contrato universal aprovado.

NU_PARCELA é sequencial por unidade, apenas entre dívidas elegíveis. Permanecem ordenação por vencimento e desempate por identificador estável do motor existente. Repetições de unidade, vencimento e valor não são fundidas: os lançamentos possuem identidades distintas e proveniência individual.

A descrição original fica intacta no canônico. O rótulo de saída é `descrição - parcela`. Nos padrões documentados de acordo sem referência com sufixo de quatro dígitos, taxa de roçagem e multas de infração reconhecidas, acrescenta-se antes da parcela o mês/ano do vencimento. Acordos com referência como `123/2025` conservam o rótulo documental, sem acrescentar outro mês. Isso é apresentação: não atribui competência, não altera valores nem caracteriza autorização de cobrança.

O confronto independente com o template explica 1.541 rótulos sem mês adicional e 84 com mês. A comparação das bases de descrição é separada da comparação dos números de parcela; não se modifica o critério de desempate para imitar a ordem histórica.

## Cadastro e limites de confiança

Documentos precisam ter formato completo e verificadores fiscais válidos. Malformados ficam na evidência original temporária e não são atribuídos; um campo isoladamente inválido não interrompe a conversão. CPF/CNPJ conflitantes continuam retidos. Telefones completos de oito/nove dígitos podem ter DDD vazio; não se infere prefixo nem se extrai um trecho dentro de sequência maior.

Nome e unidade concordantes são exigidos para transferir documento e contatos. Dois responsáveis não recebem um CNPJ único por coincidência de unidade. Empresas com E e evidência empresarial suficiente seguem a exceção A1. Documento válido, sozinho, não comprova titularidade. Ausência de cadastro ou retenção cadastral não exclui dívidas elegíveis.

As divergências de documento do template são confrontadas com as colunas principal e secundária do cadastro, sem copiar dados pessoais históricos nem presumir outro vínculo. Uma referência de comparação não substitui a evidência atual.

## Fluxo e execução local

```sh
PYTHONPATH=src CONVERSOR_CHAVE_LOCAL='<chave-local-definida-pelo-operador>' python -m conversor.web --port 8765
```

Abrir `http://127.0.0.1:8765`, autenticar, selecionar Forest Hill, informar a referência e enviar inadimplência e cadastro opcional. O servidor permanece local. Excel é diagnóstico, não autorizado para importação operacional.

Os intermediários são gerados em área temporária isolada e removidos antes de devolver o resultado. Excel permanece em memória por até 15 minutos ou enquanto uma resposta/download autorizado ainda o utiliza; servir o download, descartar ou encerrar sessão aciona seu descarte. Logs e erros não devem conter documentos, conteúdo financeiro ou chaves. Somente perfis, layouts, regras e hashes documentais necessários permanecem como configuração.

Continuam as limitações preexistentes do MVP: sem teto global de RSS, possíveis resíduos após encerramento forçado sem recolhimento automático e workers já iniciados que concluem após cancelamento. Cópias baixadas e apagamento forense não são garantidos. Nenhuma infraestrutura Windows experimental ou vínculo documental permanente foi incorporado.

## Validação

As fixtures em `tests/passaredo/test_forest_hill.py` são fictícias e reutilizam apenas os construtores sintéticos do componente tabular. Cobrem 29/30/31 dias, judicial sem filtro adicional, DIAS divergente, encargos separados, unidade/gramática, colisões, fórmulas e fechamento, 30 colunas, parcelas, duplicidades, rótulos, documentos A1, telefones sem DDD, cadastro contraditório, template sem autoridade de identidade, determinismo, autenticação, isolamento e descarte.

Os resultados finais e as pendências da reconciliação privada serão registrados no relatório de entrega anonimizado, separando a seleção financeira de rótulos, parcelas e campos cadastrais.

### Resultados locais para auditoria

Referência privada: 07/10/2026, modo A. Foram reconciliados 1.631 lançamentos de origem e 1.625 elegíveis, em 98 unidades; todas essas unidades constam no cadastro de 583 registros. Com e sem cadastro, a saída tem 1.625 linhas e nenhuma divergência de unidade, vencimento ou valor original. As duas repetições da combinação unidade/vencimento/valor permanecem contabilizadas como lançamentos distintos. Hashes reais, soma do original, nomes financeiros e parcelas contíguas foram preservados. A área temporária de homologação foi descartada e as fontes permaneceram inalteradas.

As bases dos 1.625 rótulos coincidem com o template. Persistem dez diferenças na associação entre parcela e rótulo em quatro unidades, todas em empates de vencimento. O motor mantém o desempate por identificador estável; não foi alterado para reproduzir a ordem histórica. Essa diferença de apresentação requer revisão, sem comprometer a reconciliação financeira.

Entre elegíveis, há 166 retenções cadastrais por divergência de nomes em dez unidades e onze por multiplicidade sem vínculo suficiente em duas outras unidades: 177 associações em doze unidades. O resumo do lote completo informa 178 porque também abrange uma associação de lançamento não elegível. Essas contagens não são exclusões financeiras.

O template tem 72 documentos não vazios diferentes do principal do cadastro e mais uma célula vazia onde há principal válido. Nenhum dos 72 encontra correspondência comprovada na coluna secundária CPF das mesmas unidades. A saída preserva a política A1, sem copiar esses documentos históricos: na comparação com o template, 1.443 documentos coincidem, 176 ficam retidos/ausentes e seis diferem com evidência da fonte atual. Esses agregados não incluem documentos, nomes ou unidades individuais reais.

Validação final: 51 casos sintéticos Forest Hill, incluídos nas 224 regressões direcionadas aprovadas; suíte Linux/Python 3.12 com 2.082 aprovados, zero falhas/erros/skips e um warning de depreciação Starlette/AnyIO. `pip check`, `compileall`, sintaxe JavaScript e whitespace passaram. Chromium real com dados fictícios aprovou conversão, limites de prazo, documentos A1, telefones sem DDD, retenções, 30 colunas, autenticação, isolamento, bloqueio operacional, download e descarte.

Pendentes: confirmação do limite exato de 30 dias, revisão das dez diferenças de apresentação e das associações cadastrais sem prova, validação externa da implementação. A publicação para auditoria não constitui aprovação operacional.

A comparação cadastral inclui contatos e endereço, sem alterar a saída para imitar o histórico. Telefones: 1.573 linhas coincidentes, 39 com associação retida, sete sem atribuição na leitura atual e seis divergentes com evidência da fonte. E-mails: 1.498 coincidentes, 48 com associação retida, 69 com ordem diferente e dez divergentes com evidência da fonte. Na comparação estrita de endereço, 177 associações ficam retidas e 1.448 logradouros diferem do template; nestas últimas, número, CEP, cidade e UF coincidem, e bairro difere apenas em apresentação. Não há substituição automática de logradouro: a fonte atual permanece preservada, e um eventual endereço padrão documentado exige revisão da evidência. Essas divergências são pendências cadastrais, não exclusões financeiras.
