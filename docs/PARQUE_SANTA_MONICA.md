# PSM-01 — Parque Santa Mônica / OMA

Implementação na branch `feat/parque-santa-monica-oma-efemero`, baseada na INT-01 publicada `efe521ea1ad4254c746b56c37690c8b5d139785f`. Publicação controlada autorizada exclusivamente para auditoria externa e testes locais, sem merge ou homologação operacional.

## Identidade e contratos

O perfil `parque_santa_monica` pertence à administradora `oma`. A identificação financeira exige o cabeçalho interno `Condomínio: PARQUE SANTA MONICA`, além da gramática completa. O PDF usa o alias controlado `COND. EDIF. PQ RESIDENCIAL SANTA MONICA` e o código interno de origem `0566`. O nome de arquivo `3067` não é utilizado como identidade nem como código de destino. O vínculo entre esses documentos é específico deste perfil, sem tornar os códigos intercambiáveis.

Hashes homologados são calculados sobre os bytes reais, após validar a estrutura. Arquivos novos compatíveis exigem confirmação do condomínio. Identidade contraditória bloqueia o fluxo; não há fallback para Passaredo ou Forest Hill. O cadastro é validado independentemente.

## Leitor financeiro próprio

`readers/oma_xlsx.py` interpreta a aba única `Sheet`, as 12 colunas, o cabeçalho de posição, a unidade com bloco/responsável, os componentes, o fechamento de cada recibo e os totais unitários e acumulados. Cada recibo gera um boleto; componentes, subtotais e cópias de resumo não geram dívidas. A fonte também repete, após o acumulado, uma sequência de totais unitários e outro acumulado. Essa cauda é conferida integralmente contra os totais já lidos, sem duplicar os lançamentos.

Os seis valores monetários são preservados separadamente: original, principal, multa, atualização, juros e atualizado. Comparações usam Decimal exato; não há arredondamento para encobrir diferenças ou recálculo de encargos. Componentes negativos em formato brasileiro permanecem negativos. O total original do recibo fornece `VL_PARCELA`; soma dos componentes, fechamento de recibo/unidade/acumulado e resumo precisam coincidir. Não se fixam no leitor as contagens da homologação.

Recibo com sufixo alfabético é preservado integralmente como evidência. O contrato canônico de identificadores não permite espaços: o separador do recibo é representado tecnicamente por ponto (`número A` → `número.A`), de forma reversível e sem truncar o sufixo; o token literal permanece em `OMA_RECIBO_ORIGINAL`. IDs distintos continuam distintos. O campo Emissão bruto é auditado e não substitui o vencimento. Não se atribui competência a partir da descrição ou da data.

## Regra e exportação

A linha 242 da régua documenta prazo extrajudicial de 60 dias e judicial de 90. A hipótese autorizada para diagnóstico é `(data_ref - vencimento).days > 60`. O prazo judicial não acrescenta filtro. Exatamente 60 dias permanece fora até confirmação específica de inclusividade e vigência; a fonte histórica não possui esse caso na referência de 13/10/2026.

A saída tem 30 colunas, AA literal `NM_DIVIDA_CEDENTE`, sem o espaço do template histórico. A administradora é `OMA`; produto e sufixo são `PARQUE SANTA MONICA`. Bloco `01`/unidade `000001` produz `BL01-UNI0001`; `00017S` produz `BL01-UNI017S`. O canônico conserva zeros e representação originais. A equivalência s/S está limitada ao sufixo documental observado; não autoriza outras letras ou vínculos de bloco. Colisões bloqueiam a saída.

`CEDENTE` e `NM_CONTRATO_CEDENTE` recebem o complemento com sufixo; `COMPLEMENTO` recebe apenas a parte da unidade. O rótulo `COTA MM/AAAA - N` apresenta o mês/ano do vencimento, não competência presumida. A numeração considera somente recibos elegíveis, por unidade, em vencimento crescente e identificador estável. O modo B mantém no máximo um cadastro adicional por unidade com recibo não elegível; não copia duplicações históricas.

## Cadastro PDF e associação

`readers/oma_cadastro.py` tem parser próprio de seções, continuidade e papéis, reutilizando a extração geométrica e contratos de evidência existentes. Valida identidade, paginação, quantidade declarada e data de emissão. Cabeçalhos repetidos apenas continuam a mesma ficha quando cliente, nome, unidade e posição da continuidade concordam. Um campo de locatário explicitamente vazio não cria pessoa nem transfere identidade. O registro administrativo não é associado a unidades financeiras.

Dados pessoais, pagador, locatário, correspondência e contatos da unidade permanecem separados na evidência. Somente documentos e contatos do titular podem participar da associação nominal; contatos da unidade ou do pagador não são promovidos a contatos pessoais. CPF/CNPJ exige formato completo e verificadores fiscais. Malformados ficam na evidência temporária e não interrompem o lote inteiro. Telefones completos de oito/nove dígitos podem ter DDD vazio; não se completam prefixos nem se extraem fragmentos de sequências maiores.

A associação reutiliza a política A1 com suas comparações originais como padrão dos perfis anteriores. Os dois parâmetros internos adicionais permitem fornecer a proveniência OMA e sua equivalência documental restrita de unidade. Não há alteração das regras padrão Passaredo/Forest Hill.

Para OMA, nome e unidade concordantes, documento válido e ausência de conflito são necessários antes de transferir documentos e contatos. Nome divergente, múltiplos responsáveis sem vínculo suficiente, documentos conflitantes ou ausentes retêm a associação; o nome financeiro e a dívida elegível permanecem. Empresas legítimas com E e evidência empresarial seguem a validação A1. Pendências OMA são agrupadas por bloco e unidade, sem fundir números iguais de blocos distintos. A data documental do cadastro é mostrada na interface.

O PDF privado tem proteção de abertura com senha vazia e permissão de extração. O backend admite somente esse caso, exclusivamente no papel de cadastro OMA, com identidade financeira comprovada/confirmada e identidade cadastral validada. A extração nativa já verifica EXTRACT e limites de páginas/streams/caracteres. Senha não vazia, extração proibida ou outro perfil continuam rejeitados. Não se remove a proteção nem se grava cópia descriptografada.

## Endereço, modo B e diferenças históricas

Os seis campos padronizados do template são constantes. O logradouro/número têm origem corroborável no cabeçalho documental; os demais campos são evidência do template. Não se copiam valores reais para o perfil versionado. O operador pode conferir e informar o padrão na UX-01, em memória durante a sessão, sem usá-lo como prova de residência ou titularidade. O complemento permanece individual. Cabeçalhos e endereços individuais da fonte continuam na evidência temporária; não substituem automaticamente o padrão. Sem configuração, campos não comprovados ficam vazios.

Na homologação privada, o padrão foi fornecido explicitamente em memória e houve conferência dos seis campos. Na saída padrão sem essa configuração, esses campos podem permanecer vazios, de forma intencional. Documentos/contatos históricos sem prova não são copiados. Linhas cadastrais B deixam Y:AD vazias, conforme contrato universal.

O template contém 2.338 dívidas e 302 linhas sem dívida, distribuídas por 207 unidades. O contrato atual produz 207 cadastros adicionais, totalizando 2.545 linhas B: diferença de 95 repetições históricas, sem perda de dívidas ou alteração da regra global.

## Executar localmente

```sh
cd /workspace/Improvement-parque-santa-monica
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web
```

Abrir `http://127.0.0.1:8000`, sem senha manual. Enviar inadimplência, confirmar quando solicitado, cadastro PDF opcional, referência e modo A/B. Configurar endereço somente após conferir a identidade.

Permanecem sessão técnica, CSRF, Host/Origin, isolamento, limites de upload/cache e descarte. Intermediários são removidos após processamento. Prévia/Excel duram até 15 minutos, respeitando respostas/downloads ativos, e são descartados após consumo ou solicitação. Sem histórico financeiro permanente, cobrança, CRM, exportação operacional ou infraestrutura ACL experimental.

## Pendências

Confirmar inclusividade dos 60 dias e vigência operacional; revisar associações cadastrais/documentos históricos sem evidência; conferir o endereço padrão antes de configurá-lo; validar em Windows real quando disponível. Persistem limites anteriores: sem teto global de RSS, workers que podem concluir após cancelamento e resíduos possíveis após encerramento forçado sem recolhimento automático. Não há garantia de limpeza forense nem de exclusão de cópias baixadas.

Fontes privadas não integram o repositório, fixtures, logs ou capturas. Testes usam somente documentos fictícios. A entrega inclui relatório de testes e reconciliação anonimizada, sem nomes, documentos, contatos ou valores financeiros privados.

## Esclarecimento cadastral da auditoria

A comparação de 142/30 usa somente o titular do PDF e a representação original da célula Excel. A métrica 92/15 é reproduzida com normalização, zeros e principal técnico que pode recorrer ao pagador; isso não autoriza associação pessoal. A referência preliminar 267/38 foi retirada dos critérios de aceite pela revisão externa. A decomposição das 530 retenções e os universos completos estão em [PSM_01_ESCLARECIMENTO_CADASTRAL.md](PSM_01_ESCLARECIMENTO_CADASTRAL.md). Parser e política A1 permanecem inalterados.
