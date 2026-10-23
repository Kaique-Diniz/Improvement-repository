# Correções estruturais dos leitores reais — Fase 3

Este registro descreve a entrega anterior (432 testes). A revisão posterior está
em [Aceite técnico da Fase 3](ACEITE_TECNICO_FASE3.md), com 458 testes e investigação
individual das pendências. As contagens anteriores são mantidas como histórico.

Implementação técnica em 21/10/2026, após autorização do usuário. **Não homologado
para produção.** A régua não foi modificada ou executada; não se iniciou a Fase 4.
Os dados e relatórios individuais continuam exclusivamente na área privada.

## Leitores registrados

| Leitor | Versão | Estrutura |
|---|---|---|
| `habita_composicao_real_v1` | `1` | Cabeçalho numérico de condomínio, bloco/unidade com `•`, composição de cinco valores |
| `fl_composicao_real_v1` | `1` | Cabeçalho W002A com código entre parênteses; componentes, descontos e saldo por unidade |
| `cadastro_fl_real_v1` | `1` | Cabeçalho W045A com código, tabela por coordenadas e registros entre páginas |

As três versões sintéticas anteriores continuam registradas e testadas. Os
leitores são por layout, reutilizáveis em outros condomínios mediante configuração
de identidade. Não há condições pelo nome TREE/Plaza ou códigos reais no código.
Assinaturas separam as versões pela estrutura; formato desconhecido, concorrência
de famílias, revisão misturada ou condomínio divergente bloqueiam a leitura.

`RegistroLeitores` entrega o mesmo `LoteCanonico`. O adapter valida arquivo, hash,
versão e todas as referências tipadas de origem. O caso de uso `LerDocumento`
continua exigindo reconhecimento aprovado, catálogo e assinaturas atuais; os
novos leitores não aprovam formatos, perfis ou regras automaticamente. Os testes
de integração desse caminho usam aprovações **artificiais e exclusivamente
sintéticas**, sem ativar regras de produção.

## Continuidade e reconciliação

Habita: um boleto pode continuar na página seguinte com o mesmo identificador e
unidade. Metadados devem coincidir; repetição fora da continuidade permitida
bloqueia. Subtotais nunca viram componentes. São conferidos original + multa +
atualização monetária + juros = total, totais de boleto/unidade, total geral e
contagem explícita. Subtotal de bloco divergente fica crítico e auditado, mesmo
se o total geral fechar: a fonte não é alterada para resolver o conflito.

FL: `Saldo` é apenas controle incremental da unidade. O valor do boleto resulta
da soma de componentes assinados. Descontos entre parênteses continuam negativos.
Descrições podem atravessar linhas/páginas antes ou depois dos valores. Rodapés
são separados pela posição, e a paginação deve estar completa. Leituras de
consumo na coluna Descrição não viram dinheiro do boleto. Notas administrativas
em tabela identificada são preservadas sem integrar dívida; par financeiro
ambíguo nesse contexto bloqueia. O fechamento confere quantidade de unidades,
soma dos componentes e soma dos saldos finais.

Cadastro: valida as posições dos cabeçalhos de coluna. Número e torre separados
entre fragmentos, e contatos/endereço entre páginas, mantêm contexto. Rodapés da
administradora ficam fora dos dados do titular. Chaves repetidas, torre ausente,
colunas incompatíveis ou páginas faltantes bloqueiam. Contatos excedentes e
endereços não segmentados ficam preservados em auditoria, sem completar DDD ou
selecionar um titular arbitrariamente.

## Contratos e decisões de ausência de informação

- `ItemComposicao.descricao_original` conserva o texto da composição.
- `Boleto.emissao_original` conserva o token literal da coluna Emissão; o formato
  abreviado da Habita não foi reinterpretado como competência ou data aprovada.
- `Boleto.competencia` aceita `None` quando não informada. A leitura não deriva
  competência do vencimento nem do token de emissão. Essa extensão permite
  representar ausência real sem inventar conteúdo; JSON anterior com competência
  explícita continua legível. O exportador bloqueia uma linha de dívida que
  precise de competência não informada (`COMPETENCIA_NAO_INFORMADA`).
- Multa/juros/correção não separados na FL permanecem `None`, não zero presumido.
- `LoteCanonico.ressalvas` preserva código, severidade, origem e valores brutos
  protegidos. Informações preservadas não são tratadas como erro; ambiguidades
  financeiras/cadastrais são críticas. Schemas foram regenerados.

Essas são decisões de representação de ausência e auditoria, não novas regras de
cobrança. Competência, segmentação de endereço e resolução de titularidade ainda
precisam de validação de origem/perfil para uma exportação real completa.

## Cruzamento de cadastros e CPF/CNPJ

`application/cadastro.py::cruzar_cadastro` usa condomínio + torre/bloco + unidade
normalizada, valida administradora e preserva os boletos integralmente. Falta de
cadastro gera alerta. Titular divergente ou múltiplo fica em revisão, com nomes,
documentos e fontes preservados; a prioridade antiga do laboratório não é usada.

A coluna literal `CPF` mantém CPF/CNPJ válido como texto, com zeros e dígitos
verificadores. Conflitos válidos ou titularidade não confirmada continuam
bloqueantes. `construir_linhas` também recusa ressalvas críticas do lote, mesmo
sem o chamador passar ocorrências extras. A aba `Dados` e as 30 colunas não foram
alteradas. O easyCollector aceita os dois documentos nessa coluna, conforme
confirmação do responsável; a importação integral segue sem homologação.

## Resultado privado antes/depois

| Fonte | Antes: leitor operacional | Depois: leitura operacional |
|---|---|---|
| Habita | `CONTATO_SEM_UNIDADE` | 112 unidades, 769 boletos, 2.082 componentes |
| FL | `CONDOMINIO_DIVERGENTE` | 50 unidades, 115 boletos, 985 componentes |
| Cadastro FL | `CADASTRO_CONDOMINIO_DIVERGENTE` | 390 unidades, documentos e fontes preservados |

Comparação de chaves, vencimentos, componentes, originais, acréscimos Habita e
saldos FL: **zero divergências financeiras** contra o inventário investigativo.
As 33 continuidades financeiras Habita e 17 FL coincidem. A FL registra ainda
três boletos com continuação exclusivamente descritiva: 20 com origem em mais de
uma página, sem criar boletos ou alterar valores. Contagem anterior de 17
considerava apenas as páginas de componentes financeiros.

Correção comprovada na investigação anterior: 25 nomes cadastrais continham
fragmentos de rodapé da administradora; foram removidos pela geometria, sem
alterar documentos. Todas as 50 unidades FL encontraram cadastro, mas 34 têm
titularidade/nome pendente de revisão. O subtotal de bloco da Habita continua
crítico. Os dois conflitos de CPF da comparação com a referência permanecem
bloqueados, e os quatro zeros estão presentes nas fontes; isso não remove
eventual pendência de titularidade desses cadastros.

## Testes e reprodução

```sh
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
.venv/bin/python -m pytest -q
# 372 passed: 322 anteriores + 50 novos
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
# 60 passed
```

**432 testes aprovados**, incluindo os 382 anteriores. Fixtures em
`examples/fase3/layouts_sinteticos.py` foram criadas do zero, com PDF posicionado,
sem novas dependências. Os 50 testes novos cobrem os três layouts, paginação,
reconciliação, omissão/duplicação, consumo e notas, geometria cadastral, cruzamento,
conflitos e o caso de uso com catálogo/assinaturas aprovados artificialmente.

O manifesto da validação privada aceita os seis IDs, com `natureza=real_autorizada`
somente na área autorizada fora do Git. Deve declarar códigos/identidades
esperados e hashes revisados; não gerar aprovações a partir do próprio arquivo.
O contrato comum da validação pode comparar JSON canônico revisado. A comparação
contra o inventário investigativo aqui foi mantida em scripts privados separados;
o inventário e o Excel **não alimentam os leitores**.

Área desta execução:
`/workspace/validacao-privada-fase3/resultados/correcao_estrutural_003/`.
Contém canônicos, auditorias, comparação por unidade/boleto e relatório completo.
Arquivos reais/relatórios individuais não devem ser colocados em fixtures ou Git.

## Pendências para revisão

1. Resolver a inconsistência de rótulo do subtotal de bloco na fonte Habita.
2. Aprovar vínculos e fonte correta para titulares múltiplos/divergentes e os dois
   conflitos documentais. Não selecionar CPF/CNPJ por prioridade implícita.
3. Definir fontes explícitas de competência e segmentação/contatos para saída
   completa; conservar os campos brutos até a decisão.
4. Rever amostras representativas adicionais e as assinaturas/catálogos de
   identidade antes de promover formatos a validados para operação.
5. Concluir critérios de aceite da Fase 3 e homologação integral no destino antes
   de liberar produção. A próxima fase continua aguardando revisão do usuário.
