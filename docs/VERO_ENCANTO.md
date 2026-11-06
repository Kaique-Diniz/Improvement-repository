# VEC-01 — Vero Encanto / LELLO_2

Implementação diagnóstica local, na branch `feat/vero-encanto-lello-efemero`,
baseada em `2b7d6347d23e0ea79e16216c10042b5a20674344`. Não inclui Itajubá,
infraestrutura ACL Windows, cobrança, judicial, acordos ou importação CRM.
Não representa homologação operacional.

## Identidade e reconhecimento

O perfil próprio `vero_encanto` tem leitores específicos para o XLSX financeiro
e o PDF cadastral. Os leitores BBZ, OMA e AUTO GESTÃO não recebem esses documentos.
Reutilizam-se apenas conversores técnicos e validadores já existentes.

O XLSX identifica `10888 - VERO ENCANTO`; o cadastro identifica `10888-10` e o
nome documental do empreendimento. O prefixo de arquivo `3286` não comprova
identidade nem código de integração. Nenhum desses números é convertido em
código de destino.

Reconhecimento automático requer identidade, estrutura válida e hash homologado
do papel correto. Bytes novos compatíveis exigem confirmação explícita. Hash ou
seleção manual não dispensam a leitura estrutural nem aceitam outro condomínio.
Os SHA-256 continuam calculados sobre os bytes integrais reais, sem normalização.

## Financeiro e prazo diagnóstico

A aba `Planilha1` tem seis colunas. Cada grupo contém Empresa, Referência,
Unidade e Multicontas. O cabeçalho de recibo tem Código, Vencimento, Valor Original,
Valor Multa, Correção/Juros e Total; os componentes usam Conta, Histórico e Valor.
Cada código representa uma dívida, não uma dívida por componente.

O leitor confere cabeçalhos, estados, unidades, códigos duplicados, datas,
fórmulas, soma dos componentes, original + multa + correção/juros e fechamento
geral. Os códigos de conta repetidos permanecem distintos por ordem de origem.
Componentes sem valor ficam na evidência original, com valor nulo, sem criar itens
monetários fictícios. Históricos, ordem, linha e hash são preservados.

Correção/Juros permanece um montante conjunto na evidência original. Não é
decomposto nem atribuído integralmente a um campo de juros ou correção separado.
Não se recalculam encargos; o Excel recebe o original do recibo.

A linha 586 da régua de 04/11/2026 fundamenta os 31 dias extrajudiciais e os
90 judiciais. A hipótese diagnóstica autorizada é:

```text
(data_ref - vencimento).days > 30
```

31 dias completos são elegíveis; 30 não são. Judicial não cria filtro adicional.
Inclusividade e vigência operacional continuam pendentes. A referência
06/11/2026 é parâmetro de seleção, não data de extração comprovada.

## Cadastro e associação conservadora A1

O leitor mantém participantes separados, inclusive entre páginas. Cada pessoa
tem nome, tipo, documento, origem e evidência próprios. Participação percentual
é preservada, sem servir de critério de escolha do titular da dívida.

A transferência de documento/contatos exige torre/unidade exatas, um único
participante nominalmente concordante, validade fiscal e ausência de conflitos.
Não se escolhe o primeiro proprietário. Dois participantes com nomes diferentes
e o mesmo documento constituem conflito. Documento inválido ou malformado não é
atribuído; o texto original permanece na evidência temporária.

Os validadores fiscais e o tratamento A1 da multiplicidade são reutilizados sem
alterações. Uma razão social com “E” e CNPJ comprovado não é automaticamente
retida quando satisfaz o contrato empresarial A1. Nome ambíguo ou divergente
retém CPF e contatos, preservando o nome financeiro e a dívida.

Telefones completos podem ter DDD vazio; nenhum DDD é inferido. Somente contatos
do participante selecionado são transferidos. Campos aos cuidados de e contatos
de terceiros permanecem na evidência, sem atribuição ao titular.

## Reconciliação privada anonimizada

Nenhuma fonte privada é necessária para executar os testes sintéticos.
As contagens abaixo são resultados da leitura, não constantes dos leitores.

| Verificação em 06/11/2026 | Resultado |
| --- | ---: |
| Recibos / unidades financeiras | 604 / 188 |
| Componentes com valor / sem valor | 2.608 / 252 |
| Soma original integral | R$ 230.934,44 |
| Elegíveis / não elegíveis | 445 / 159 |
| Unidades elegíveis | 147 |
| Soma original elegível | R$ 161.001,95 |
| Divergências de multiconjunto contra o template | 0 |
| Modo A | 445 financeiras |
| Modo B | 445 financeiras + 159 cadastrais = 604 |

O confronto utiliza multiconjuntos de complemento documental da torre/unidade,
vencimento e valor original, preservando multiplicidades. Não usa CPF, nome,
contatos ou o template para completar informações nem autorizar associação.
As 159 linhas cadastrais resultam do motor universal, no máximo uma por unidade;
incluem unidades sem dívida elegível e não são forçadas para atingir uma contagem.

| Motivo de retenção | Total | Elegíveis | Não elegíveis | Unidades |
| --- | ---: | ---: | ---: | ---: |
| `VERO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 41 | 32 | 9 | 16 |
| `VERO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 2 | 1 | 1 | 1 |
| **Total** | **43** | **33** | **10** | **17** |

561 associações passaram pelas condições de identidade e documento válido.
Nenhuma dívida foi excluída pelas 43 retenções cadastrais.

### Contagem cadastral e isolamento do registro especial

O PDF contém 438 registros de bloco/unidade e 485 participantes: 437 unidades
no padrão financeiro (218 A e 219 B) e o registro especial `SINDPR`, na última
página, preservado
sem codificação financeira ou associação presumida. As 188 unidades financeiras
foram encontradas no conjunto regular.

Foram reproduzidos 484 participantes nas 437 unidades regulares, com 47 unidades
de dois participantes. `SINDPR` tem um participante próprio. A revisão externa
esclareceu a referência inicial de 48: ignorar esse último cabeçalho atribui
indevidamente o participante especial à unidade regular anterior.

O parser encerra o participante anterior antes de criar a identidade separada
do registro especial. O participante de `SINDPR` fica vinculado exclusivamente a
essa identidade, com proveniência própria, sem codificação financeira, emissão
de dívida ou linha cadastral no Excel. Seus documentos e contatos não são
transferidos para uma unidade regular, mesmo quando o nome coincide e falta
documento ao participante regular. Uma regressão sintética específica verifica
essa separação na última página, nos modos A e B, incluindo dois participantes
na unidade regular anterior. As 14 unidades com dois participantes entre as
elegíveis permanecem preservadas. A diferença 47/48 está esclarecida e não é mais
uma pendência metodológica.

## Excel e ciclo efêmero

São preservadas as 30 colunas universais, tipos e AA `NM_DIVIDA_CEDENTE` sem
espaço final. `A00004` corresponde a `BLA-UNI0004`, `B01712` a `BLB-UNI1712`.
O cedente/contrato acrescenta `-DI 31 I – VERO ENCANTO`; o complemento não leva
esse sufixo. Nome cedente é `LELLO_2` e produto é
`COND PROJETO IMOBILIARIO DI 31 I – VERO ENCANTO`.

O rótulo `COTA MM/AAAA - N` usa mês/ano do vencimento apenas para apresentação.
A competência contábil continua ausente. Parcelas são numeradas somente entre
dívidas incluídas, com ordenação e desempate estáveis do contrato existente.

O fluxo clássico mantém sessão automática, Host/Origin, CSRF, confirmação de
fontes novas, cadastro opcional, endereço por condomínio e propostas de vínculos
sem aplicação presumida. Exportação operacional continua indisponível.

Uploads multipart permanecem em memória sob os limites existentes. Canônicos,
auditoria, participantes cadastrais e XLSX intermediário existem apenas na área
temporária isolada da conversão, cuja limpeza ocorre no `finally`, inclusive em
erro. Se o filesystem impedir a remoção, o resultado não é devolvido e a limpeza
fica pendente para novas tentativas e o encerramento normal.
O manifesto registra o hash da evidência cadastral temporária. Originais não são
copiados para histórico. Resultados de download/prévia ficam em memória até
download, descarte ou expiração, respeitando respostas ainda ativas. O janitor
também atua em inatividade; o encerramento normal libera os recursos.

Permanecem como configuração do software somente perfis, hashes de homologação,
layout, evidência da régua e codificação. Endereços e propostas fornecidos pela
interface ficam limitados à sessão, sem cadastro pessoal persistente.

## Execução e limites

```bash
cd /workspace/Improvement-vero-encanto
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web
```

Abrir `http://127.0.0.1:8000`. Usar o fluxo efêmero padrão, sem a opção de legado
persistente. Selecionar conscientemente a data de referência e conferir as
pendências antes do download diagnóstico.

Limitações do MVP permanecem explícitas: 20 MiB por upload, duas conversões
simultâneas e cache de resultados de 32 MiB não constituem um limite rígido do RSS
dos parsers. Cancelamento da resposta pode deixar o processamento terminar para
executar a limpeza. Downloads ativos prolongam a retenção necessária. Interrupção
forçada pode deixar resíduos transitórios. Este componente não implementa uma
varredura automática de áreas órfãs na próxima inicialização; identificação e
remoção controladas desses resíduos permanecem pendentes. Não se certifica
apagamento físico de mídia.

Validar operacionalmente prazo/vigência antes de homologar.
Windows requer execução real; resultados Linux e Chromium não certificam Windows.
Não foi iniciada nenhuma integração ou mudança na infraestrutura ACL.

## Validação local desta entrega

- 58 testes Vero inteiramente fictícios: estrutura, somas, componentes sem valor,
  duplicidades, torres, 30/31/32 dias, troca da referência, copropriedade,
  continuação de página, documentos inválidos/conflitantes, cadastro cruzado,
  retenções, modos A/B, isolamento de `SINDPR`, proveniência real, determinismo e download isolado.
- Conjunto direcionado com regressões anteriores: 412 aprovados.
- Suíte Linux completa: 2.270 aprovados, sem falhas, erros ou skips. Um aviso de
  depreciação do Starlette/AnyIO, sem relação com os leitores.
- `pip check`, `compileall`, sintaxe JavaScript e whitespace aprovados.
- Chromium real: interface sem senha manual, confirmação de fonte nova,
  reconhecimento por hash de fixture, cadastro, endereço, proposta não aplicada,
  modos A/B, prévia, Excel de 30 colunas, isolamento e bloqueio operacional.
  Host/Origin e CSRF foram exercitados sem relaxar a aplicação.
- Expiração comprovada em inatividade com o janitor real e relógio de teste
  controlado; intermediários descartados e encerramento normal limpo.

Os hashes do laboratório de navegador são vinculados apenas a arquivos fictícios
no processo de teste. Os hashes privados versionados não foram substituídos por
hashes sintéticos. Capturas e resultados de navegador contêm apenas dados fictícios.
