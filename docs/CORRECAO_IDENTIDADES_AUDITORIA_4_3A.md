# Correção de identidades de auditoria — incremento 4.3A

Etapa corretiva restrita às duas colisões FL. Sem execução de regras reais,
alteração financeira, escolha de documento/titular, 4.3B ou homologação para produção.

## Causa comprovada

A função `ocorrencias_documentais`, em `src/conversor/application/documents.py`,
gerava no commit `2b6c96c`:

```python
id = 'documento:' + sha256(f'{processamento_id}:{unidade_id}:{codigo}'.encode()).hexdigest()
```

O script privado `revisao_final_fase3_004/reavaliar_referencias.py`, linha 38,
chama essa função para cada comparação com Excel, com o mesmo processamento.
Duas linhas de referência da mesma unidade acionaram os mesmos dois códigos.
A fórmula acima foi reproduzida e confirmou os dois IDs legados repetidos.

| Código | Registros históricos | Comparação individual |
|---|---:|---|
| `DOCUMENTOS_CONFLITANTES` | 2 | Mesmo processamento, unidade, escopo, gravidade e origem principal; evidências com linha/identificador de Excel diferentes |
| `DOCUMENTO_TITULAR_NAO_CONFIRMADO` | 2 | Mesma causa e diferença de proveniência; retenção preservada em ambos os registros |

Nos dois casos, o campo diferente do registro é `evidencias_documentais`. A primeira
evidência cadastral coincide integralmente. A segunda contém os mesmos valores de
documento, arquivo e SHA, porém aponta para células diferentes: linha e identificador
de origem diferem. As versões de leitura registradas coincidem
(`cadastro_fl_real_v1@1` e `comparacao_xlsx_1`). Os hashes dos registros completos
diferem; a origem primária, o tipo e a fórmula de ID são os mesmos. IDs, hashes,
ponteiros, versões e registros integrais estão no relatório privado.

Portanto, é uma **chave insuficiente, sem vínculo com conteúdo/proveniência**, e
não uma colisão criptográfica de SHA-256, corrupção do CPF ou diferença financeira.
A consolidação posterior apenas revelou o problema. Não foi causada pelo
reprocessamento idempotente nem por mistura dos 390 cadastros com o lote de 50.

**Retificação do relatório anterior:** as colisões são internas aos dois casos do
próprio dossiê documental. Nenhuma das 201 ocorrências operacionais participa
desses pares. A descrição inicial de conflito entre dossiê e registros operacionais
era imprecisa; o bloqueio preventivo da preparação estava correto.

## Esquema implementado

1. **Ocorrências documentais novas:** `documento:v2:<sha256>`, com serialização JSON
   canônica da versão de identificação, pessoa e ocorrência completa: processamento,
   unidade, código, gravidade, escopo, origem e todas as evidências. Valores e origens
   diferentes produzem outra identidade; conteúdo idêntico reproduz o mesmo ID.
   Não há concatenação ambígua de componentes. A função `id_documental_legado`
   conserva a fórmula v1 para rastreamento; não regrava arquivos históricos.
2. **Importações históricas:** `auditoria:v1:<sha256>`, vinculado ao namespace
   `operacional`/`documental`, produtor/versão declarados, ID/SHA do arquivo,
   ponteiro JSON e ocorrência original completa. Se uma versão de produtor não
   consta no legado, registra-se explicitamente essa ausência, sem inventá-la.
3. **Mapeamento reversível:** cada vínculo guarda `id_legado`, `id_interno`, hash do
   original tipado, hash do registro JSON bruto, localização e objeto original
   integral. A projeção da entrada troca exclusivamente o ID. Origem, processamento,
   gravidade, código, escopo, registro afetado e evidências permanecem iguais.

O SHA do arquivo e o ponteiro permitem recuperar o registro bruto e todo o seu
contexto histórico. Repetir a importação das mesmas fontes é determinístico.
Registros em posições, arquivos ou namespaces diferentes permanecem separados,
mesmo com valores/documentos iguais. Não há deduplicação por CPF, nome ou ID legado,
nem união de listas de evidências para fazer desaparecer o conflito.

O importador verifica tamanho/SHA das fontes e lê integralmente dois contratos
JSON explícitos: lista de ocorrências ou todos os `casos[*].ocorrencias` do dossiê.
Coleção ausente, caso incompleto, registro inválido, vínculo omitido/adulterado ou
fonte parcial é erro. A reconstrução deve coincidir integralmente com o mapa;
recalcular apenas um hash não substitui as fontes nem o recibo assinado.

## Contratos e compatibilidade

| Arquivo em `src/conversor/` | Alteração |
|---|---|
| `application/documents.py` | Identificação documental v2 e reprodução explícita da fórmula legada |
| `domain/audit_identity.py` | Fontes/localização, vínculos, reconciliação, candidato/pacote 1.1 e preparação técnica |
| `adapters/audit_history.py` | Importação completa e reconstrução verificável dos históricos privados |
| `application/simulation_inventory.py` | Inventário opcional da reconciliação e conferência exata das ocorrências projetadas |
| `adapters/private_simulation_json.py` | Leitura explícita de pacotes 1.0/1.1; recibos de reconciliação/preparação técnica |
| `application/private_simulation_ports.py` | Portas aditivas para os artefatos técnicos e pacote 1.1 |
| `application/private_simulation.py` | Pin de implementação inclui o novo contrato de identidade |
| `audit_schemas.py` | Sete schemas aditivos: cinco de auditoria 1.0 e candidato/pacote privados 1.1 |

O contrato canônico `Ocorrencia` mantém os mesmos campos e aceita os IDs históricos.
Planos/aprovações 4.1, boletos, leitores, decisões financeiras, CPF/CNPJ e as 30
colunas não mudam. Schemas publicados anteriormente continuam byte a byte iguais.

Pacotes privados **1.0 permanecem 1.0**: leitura não adiciona campos, migra dados,
troca seus hashes ou regrava recibos. Pacotes **1.1** exigem reconciliação completa
e hash correspondente no inventário; a entrada deve conter exatamente a projeção
de todos os vínculos. A seleção é pelo schema explícito; contrato desconhecido
é recusado. Atualização não silenciosa: novo pacote precisa de outro ID e revisão.

O algoritmo novo muda o contexto de implementação. Replay de uma execução antiga
continua exigindo o código/runtime original registrado pelo pin 4.3A; o sistema
não falsifica igualdade de contextos nem reescreve o relatório antigo. Reprodução
de entradas reconciliadas no mesmo contexto foi testada integralmente.

## Assinatura técnica e preservação

Criou-se `PreparacaoTecnica`, com modo literal
`integridade_tecnica_sem_atesto_humano`, distinto do pacote com atesto humano.
O recibo assinado cobre canônico, inventário e mapa completos. A assinatura da
reconciliação cobre também fontes, IDs legados e evidências. Ambos são imutáveis,
com âncoras externas e conferência das políticas históricas de autorização.

Na validação real foi provisionada autoridade **local exclusiva desta correção**,
com ator automático `servico_reconciliacao_4_3A`, permissão somente `submeter`,
somente os dois condomínios e ambiente privado. Não recebeu permissão de aprovar,
ativar ou revogar planos. Chave e credencial técnica permanecem fora do Git,
com permissões restritas; não são credenciais de administradora ou da régua.

Essa assinatura comprova a integridade técnica da reconciliação realizada.
**Não representa aprovação humana de completude, aprovação de plano ou autorização
para simular regras reais.** `carregar_pacote` não aceita uma preparação técnica.
Todos os envelopes conservam cobrança/exportação operacional como `false`.

## Resultado privado FL e Habita

Área exclusiva: `/workspace/validacao-privada-fase3/resultados/correcao_identidades_4_3A_006/`.
Script reprodutível privado: `/workspace/validacao-privada-fase3/corrigir_identidades_4_3A.py`.
Contém mapas integrais assinados, candidatos em preparações técnicas assinadas,
análise individual das colisões e resumo. Não há publicação desses artefatos.

| Evidência | FL/Plaza | Habita/TREE |
|---|---:|---:|
| Unidades / boletos preservados | 50 / 115 | 112 / 769 |
| Itens de composição preservados | 985 | 2.082 |
| Registros históricos / IDs internos únicos | 205 / 205 | 904 / 904 |
| Namespace operacional / documental | 201 / 4 | 904 / 0 |
| Colisões internas após correção | 0 | 0 |
| Pares legados com evidências distintas, ambos preservados | 2 | 0 |
| Ocorrências críticas externas preservadas | 83 | 1 |
| Unidades retidas pela segurança, sem executar regras | 34 | 112 |
| Competências ausentes, sem inferência | 0 | 769 |

Foram conferidos 64 arquivos históricos dos dossiês anteriores, inclusive a
preparação 005, **byte a byte inalterados**. Os cinco anexos continuam com os
SHA/tamanhos originais. Todos os registros canônicos coincidem por identidade e
conteúdo; a ordenação de coleções já realizada pelo normalizador 4.2 não constitui
alteração de um registro. O inventário Habita antigo também foi confrontado.

As quatro assinaturas técnicas (mapa e preparação, para cada condomínio) foram
verificadas contra a autoridade. Uma segunda execução reconstruiu os mesmos
artefatos e preservou os oito objetos/recibos assinados, sem regravação. As 132
correspondências financeiras continuam evidência anterior intacta; não houve
nova comparação por regras reais, cobrança, exportação ou alteração de documentos.

## Testes e reprodução

Novos testes em `tests/private_simulation/test_document_identity_v2.py` e
`tests/private_simulation/test_audit_reconciliation.py`: causa legada, evidências
distintas, separador ambíguo, fonte/versão/namespace, idempotência, preservação do
original, importação completa, assinatura/adulteração, pacote 1.0 imutável,
pacote 1.1, bloqueios e replay. Todas as fixtures são sintéticas.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m conversor.billing_schemas --check
.venv/bin/python -m conversor.evaluation_schemas --check
.venv/bin/python -m conversor.private_simulation_schemas --check
.venv/bin/python -m conversor.audit_schemas --check
```

Resultado: **812 regulares + 60 explícitos = 872 testes aprovados**, sem falhas
ou skips nesta execução Linux. Os 830 anteriores foram preservados e os 42 novos
passaram. Os seis comandos de conferência de schemas passaram; nenhum schema
publicado anteriormente foi modificado. As suítes públicas não dependem dos
documentos reais, de seus dados pessoais ou da autoridade privada.

A conferência de privacidade revisou 205 arquivos versionáveis: nenhuma cópia
dos anexos nem correspondência com os identificadores pessoais conferidos no
canônico privado. Não houve dados/relatórios privados nos commits, push ou merge.
Essa conferência complementa a revisão, sem constituir detecção universal de
qualquer dado sensível.

## Pendências e recomendação de avanço

A ressalva técnica das duas colisões está resolvida com preservação integral e
reconciliação rastreável. Recomenda-se aceitar esta etapa corretiva. A infraestrutura
pode apoiar a próxima revisão do 4.3B, mas **não há autorização para iniciá-lo**.

Continuam necessários: revisão/atesto humano dos pacotes completos, confirmação
da data de referência, aprovação das condições/ações/prioridades/vigências reais,
semântica dos 60 dias jurídicos e do cadastro antecipado, e vínculos revisados
com as referências. As versões de produtor não declaradas no legado permanecem
explicitamente desconhecidas; fontes, hashes e versões de leitura existentes são
preservados, sem atestar retrospectivamente uma versão não registrada.

Habita/VG continua bloqueante do lote. As 34 unidades FL e os conflitos de
documentos/titularidade continuam retidos para decisão humana fundamentada.
Pacotes incompletos/adulterados e candidatos sem atesto continuam bloqueados.
Não houve alteração de regras, valores, decisões da Fase 3 ou status de produção.

## Registro da entrega

Branch `feature/fase-4-motor-cobranca`; implementação, contratos, schemas e testes
no commit `2e35192`. Documentação em commit separado. Os commits anteriores e
todos os artefatos privados históricos permanecem preservados. Não houve push,
merge, alteração de main ou publicação dos documentos/relatórios sensíveis.
