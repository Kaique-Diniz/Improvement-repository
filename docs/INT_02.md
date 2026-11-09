# INT-02 — Integração local dos seis condomínios

Versão para auditoria técnica local. Branch `feat/int02-seis-condominios-efemero`,
worktree `/workspace/Improvement-int02-seis-condominios`, HEAD/base exata
`2b7d6347d23e0ea79e16216c10042b5a20674344`.
Preparação local concluída com staging vazio. Publicação controlada autorizada
em um único commit nesta branch, sem PR ou merge. Windows não executado.
Não há homologação operacional nem nova administradora nesta entrega.

## A. Incorporação e preservação

Ordem efetiva, após conferir que cada commit possui como pai único a base:

1. Vero Encanto: `c84c7411762149871410b3b32181d23c06612d51`.
2. Itajubá: `44b2173827987b16fb9448cba5701db823bd33b5`.
3. Terraço Beach Parque: `35a22c9b5fbfbbccca62b6a099b90f795fbc2f0d`.

Vero foi aplicado como patch limpo. Itajubá e BPQ foram incorporados com merge
textual de três vias, usando a base comum, sem criar commits ou modificar index.
Cada conflito foi resolvido por composição explícita de responsabilidades, nunca
pela escolha integral do último lado. Os arquivos novos dos três commits
permanecem byte a byte iguais aos publicados: nove Vero, nove Itajubá e doze BPQ,
incluindo todos os leitores, políticas, domínios, documentos e testes aprovados.
O motor, a A1 compartilhada, schemas, exportador universal, hashes/HMAC, regras
financeiras e infraestrutura de segurança não foram reescritos.

Validação antes de avançar: Vero + base teve 412 aprovados; após Itajubá, 470;
após BPQ, 533. Houve inicialmente um caminho de teste escrito como
`tests/vero_encanto`; foi corrigido para o diretório real `tests/vero`, sem
alteração ou omissão de testes. Na elaboração da suíte nova, a expectativa de
contexto antigo foi alinhada ao contrato existente HTTP 409 e código
DOCUMENTO_ALTERADO_IDENTIFIQUE_NOVAMENTE, e o relógio sintético usa Clock.now.
Não se alterou o servidor para fazer essas verificações passarem.

### Conflitos compartilhados e resoluções

| Arquivo | Itajubá sobre Vero | BPQ sobre os dois | Decisão preservada e evidência |
| --- | --- | --- | --- |
| `service.py` | Conflito | Conflito | União de imports, literais e famílias; cada despacho valida o seu formato e retorna antes do próximo; associações e dados originais separados; rótulos Itajubá/BPQ em ramos exclusivos; cadastro Vero original temporário preservado. Suítes individuais, 30 cruzamentos, equivalência A/B e reconciliação real. |
| `ephemeral.py` | Conflito | Conflito | Seis resumos `cadastro_<perfil>` e revisões; exceções/mensagens próprias; preservada exigência de hash do cadastro Itajubá. Sessão, limites, worker e limpeza intactos. HTTP e Chromium para seis perfis. |
| `identifiers.py` | Conflito | Conflito | Três codificadores independentes, cada qual com guarda exata e retorno próprio; sem alias de torre ou largura novo. Codificação individual e equivalência das 30 colunas. |
| `perfis.json` | Conflito | Conflito | Objetos completos dos três commits acrescentados à base; todos os campos de cada perfil conferem com a origem. Sem mudança de prazo, hash ou regra operacional. |
| `perfis_saida.json` | Conflito | Conflito | Perfis documentais completos preservados, sem endereços/copiar dados privados. Sem alteração das configurações anteriores. |
| `static/classico.js` | Merge sem conflito | Conflito | Preservados documento original Itajubá e recibo literal BPQ na lista; mensagens Vero e BPQ unidas; painel dinâmico por perfil e alertas legíveis de restrição. Chromium sem erros JS. |
| `static/efemero.js` | Conflito | Conflito | Resumo/revisão passam a usar `current['cadastro_'+current.perfil]` e a chave correspondente de revisão, cobrindo os seis em vez de uma cadeia incompleta. Sem mudança de autenticação. |

O registro por bloco de conflito está incluído no pacote de auditoria. Nenhum
teste foi removido, desabilitado ou marcado como skip/xfail. Os seis perfis-alvo
existem uma única vez. Perfis legados já presentes na base e o exemplo UX-01
foram preservados para compatibilidade, sem introduzir um condomínio extra.

## B. Matriz dos seis perfis

| Perfil | Administradora/família | Leitor financeiro | Leitor cadastral | Regra diagnóstica |
| --- | --- | --- | --- | --- |
| `passaredo` | AUTO GESTÃO / `passaredo` | `passaredo_inadimplencia_xlsx_v1` | `passaredo_cadastro_xlsx_v1` | atraso > 60 dias corridos |
| `forest_hill` | AUTO GESTÃO / `forest_hill` | `forest_hill_inadimplencia_xlsx_v1` | `forest_hill_cadastro_xlsx_v1` | atraso > 30 dias corridos |
| `parque_santa_monica` | OMA / `oma` | `oma_inadimplencia_xlsx_v1` | `oma_cadastro_pdf_v1` | atraso > 60 dias corridos |
| `vero_encanto` | LELLO_2 / `lello_vero` | `vero_inadimplencia_xlsx_v1` | `vero_cadastro_pdf_v1` | atraso > 30 dias corridos |
| `itajuba` | BN PLANNER / `bn_planner` | `itajuba_inadimplencia_pdf_v1` | `itajuba_cadastro_xlsx_v1` | atraso > 30 dias corridos |
| `terraco_beach_parque` | HABITACIONAL / `habitacional_beach` | `beach_parque_inadimplencia_xlsx_v1` | `beach_parque_cadastro_pdf_v1` | atraso > 30 dias corridos |

Todos os prazos mantêm suas hipóteses provisórias de inclusividade/vigência;
judicial, marcadores de acordo e observações não acrescentam um fluxo de ação.
Itajubá também preserva a revisão conservadora anterior a dezembro/2023.

| Perfil | Política cadastral reportada | Codificador | Configuração de saída |
| --- | --- | --- | --- |
| `passaredo` | `passaredo_nome_e_unidade_por_lancamento@1.1` | `unidade_sufixo` | `passaredo_unidade_documentada` / 1.0.0 |
| `forest_hill` | `passaredo_nome_e_unidade_por_lancamento@1.1` | `forest_hill_documental` | `forest_hill_unidade_documentada` / 1.0.0 |
| `parque_santa_monica` | `oma_identidade_nominal_documento_valido_A1@1` | `oma_documental` | `oma_parque_santa_monica_documental` / 1.0.0 |
| `vero_encanto` | `vero_participante_nominal_documento_valido_A1@1` | `vero_documental` | `vero_encanto_documental` / 1.0.0 |
| `itajuba` | `itajuba_nome_e_unidade_por_lancamento_A1@1` | `itajuba_documental` | `itajuba_unidade_documentada` / 1.0.0 |
| `terraco_beach_parque` | `beach_parque_titular_nominal_documento_valido_A1@1` | `beach_parque_documental` | `beach_parque_documental` / 1.0.0 |

Não se uniformizou a associação: Vero preserva participantes distintos; OMA e
BPQ exigem documento válido do titular antes de transferir contatos; Passaredo,
Forest Hill e Itajubá preservam suas versões A1. Itajubá rejeita cadastro XLSX
novo sem hash comprovado e ficha duplicada; escolha manual não substitui prova.
Pagador, locatário, correspondência e titular não são papéis intercambiáveis.
SINDPR e DANPRI continuam separados, com as gramáticas próprias.

## C. Evidências funcionais e regressões

| Suíte executada separadamente | Aprovados | Falhas/erros/skips |
| --- | ---: | --- |
| passaredo | 96 | 0/0/0 |
| forest_hill | 51 | 0/0/0 |
| parque_santa_monica | 60 | 0/0/0 |
| vero_encanto | 58 | 0/0/0 |
| itajuba | 58 | 0/0/0 |
| terraco_beach_parque | 63 | 0/0/0 |
| ux01_int01 | 100 | 0/0/0 |
| int02 | 108 | 0/0/0 |
| linux | 2.499 | 0/0/0 |

Contagens reais obtidas dos JUnit; não somar suítes sobrepostas. Python 3.12.14,
Linux, um warning preexistente Starlette/AnyIO de depreciação nas execuções HTTP.
Na conferência anterior, a suíte Linux teve 2.495 aprovados em 126,53 s.
Na preparação da publicação, todas as suítes da tabela foram reexecutadas:
2.499 aprovados no Linux em 128,96 s, zero falhas/erros/skips e o mesmo warning.
A INT-02 passou de 104 para 108 testes por quatro regressões adicionais: dois
cenários Itajubá nos modos A/B, com apartamento A-01 em T-01 e T-02. Um comprova
que documentos e contatos distintos permanecem na unidade correta mesmo com
nomes iguais; outro mantém retenções por lançamento e conta as duas identidades
canônicas, sem atribuir documentos/contatos nem excluir dívidas. Todos os 22
arquivos de produção continuam idênticos ao diff anteriormente auditado;
nenhum leitor, política A1 ou regra financeira foi alterado nesta publicação.
Pip check, compileall, sintaxe JavaScript e whitespace aprovados.
**Windows não executado**; Chromium em Linux não certifica Windows.

### Matriz por perfil

| Perfil | Auto/hash e fonte nova | Cadastro compatível/novo não comprovado | A/B e 30 colunas | Limites e empates | Ausente/inválido/divergente/múltiplo | Expiração/shutdown HTTP | Chromium A/B e download |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `passaredo` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |
| `forest_hill` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |
| `parque_santa_monica` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |
| `vero_encanto` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |
| `itajuba` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |
| `terraco_beach_parque` | aprovado | aprovado; regras específicas preservadas | aprovado | aprovado | aprovado | aprovado | aprovado |

### Matriz entre perfis

| Cenário | Execução e resultado |
| --- | --- |
| 30 pares ordenados de cadastro de perfil diferente | Todos rejeitados; seis pares compatíveis aprovados, nas mesmas condições. |
| Perfil escolhido incompatível | Todas as 30 combinações financeiras incompatíveis rejeitadas. |
| Hash conhecido com conteúdo inválido | Rejeição nos seis; hash não dispensa estrutura. |
| Nome de arquivo enganoso | HTTP usa nome sem identidade/extensão enganosa; conteúdo decide os seis perfis. |
| Mesma sessão, seis perfis em sequência | HTTP e Chromium alternaram sem reiniciar o servidor; contexto anterior provoca 409 sanitizado. |
| Endereço de um perfil versus seguinte | Chromium confirmou ausência de herança e configuração explícita por perfil. |
| Escopo Itajubá versus BPQ | Vencimento anterior a dezembro/2023 exige revisão apenas no Itajubá; não se exporta essa regra para outro perfil. |
| Componentes assinados OMA/Vero/BPQ | Original composto, componente negativo e proveniência preservados em ramos distintos. |
| Continuação PDF e especiais | Novos testes combinam continuação e SINDPR/DANPRI sem contaminar a unidade financeira; testes individuais mantidos. |
| Apartamento igual em torres distintas (Itajubá) | Quatro novos casos A/B: CPF, telefone e e-mail isolados; duas identidades canônicas; retenção por lançamento preservada sem excluir dívidas. |
| Conflito fiscal | Cinco formatos retêm o documento; Itajubá mantém rejeição de duplicidade estrutural e pode converter sem cadastro, sem relaxar seu contrato. |
| Sessões alheias, CSRF, Host e Origin | Download alheio 404; token/origem inválidos 403; Host inválido 400. |
| Restrição de contato/litígio | Testes BPQ preservados e Chromium mostra os três avisos; nenhuma autorização ou exclusão de dívida. |
| Download, expiração e descarte | Doze downloads Chromium, 30 colunas, recusa posterior, áreas temporárias vazias; expiração HTTP nos seis e coletor em inatividade no Chromium. |

Chromium real validou a CLI padrão sem senha, 12 conversões A/B com cadastro,
prévia, endereços, download isolado e rejeição de cadastro cruzado; houve zero
erros JavaScript. Doze capturas inteiramente fictícias estão fora do Git.
Encerramento normal removeu a área do servidor de teste.

Uma conferência adicional executou os mesmos bytes sintéticos, datas e modos
nas versões isoladas publicadas e na integração: as 30 colunas, boletos
canônicos, política, resumo cadastral e resumo financeiro foram idênticos nos
seis perfis, em A/B. Metadados globais de hash da configuração podem mudar com
novos registros; não se usaram esses metadados para forçar igualdade.

## D. Reconciliação histórica privada anonimizada

Todas as fontes homologadas necessárias estavam disponíveis e seus hashes
conferiram. Cada perfil foi executado pelo serviço integrado nos dois modos,
com cadastro, na respectiva data histórica, usando diretórios temporários.
As comparações financeiras usam multiconjunto de complemento documental,
vencimento e original; nenhuma ocorrência legítima foi deduplicada.

| Perfil | Referência | Financeiras A/B | Unidades elegíveis | Original elegível | Adicionais B | Total B | Divergências financeiras |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| passaredo | 2026-10-07 | 2154 | 126 | R$ 1053547.20 | 174 | 2328 | 0 |
| forest_hill | 2026-10-07 | 1625 | 98 | R$ 1005766.76 | 6 | 1631 | 0 |
| parque_santa_monica | 2026-10-13 | 2338 | 117 | R$ 850766.75 | 207 | 2545 | 0 |
| vero_encanto | 2026-11-06 | 445 | 147 | R$ 161001.95 | 159 | 604 | 0 |
| itajuba | 2026-10-20 | 3784 | 119 | R$ 1044815.15 | 0 | 3784 | 0 |
| terraco_beach_parque | 2026-10-16 | 850 | 111 | R$ 603477.71 | 159 | 1009 | 0 |

Todas as saídas possuem exatamente 30 colunas, AA `NM_DIVIDA_CEDENTE` sem espaço
final, nomes financeiros e valores originais preservados, documentos como texto
e zeros mantidos. Não se aplicou o endereço do template como residência pessoal;
endereço exige configuração autorizada da sessão. As fontes permaneceram iguais;
intermediários privados foram descartados. Nenhum relatório individual é entregue.

### Retenções por motivo (universo integral de cada fonte)

| Perfil | Código do motivo | Lançamentos retidos | Unidades canônicas distintas |
| --- | --- | ---: | ---: |
| passaredo | `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 236 | 8 |
| passaredo | `PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 30 | 3 |
| forest_hill | `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 167 | 10 |
| forest_hill | `PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 11 | 2 |
| parque_santa_monica | `PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 8 | 6 |
| parque_santa_monica | `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 10 | 6 |
| parque_santa_monica | `OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA` | 512 | 7 |
| vero_encanto | `VERO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 2 | 1 |
| vero_encanto | `VERO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 41 | 16 |
| itajuba | `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 864 | 29 |
| terraco_beach_parque | `BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA` | 33 | 2 |
| terraco_beach_parque | `PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO` | 65 | 13 |
| terraco_beach_parque | `PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO` | 17 | 1 |

As unidades por motivo são contadas pelo `unidade_id` do canônico, ligado ao
lançamento retido, e não apenas pelo rótulo textual de apresentação. No
Itajubá, o mesmo número aparece em blocos diferentes: a contagem preliminar de
23 rótulos distintos correspondia a 29 unidades canônicas. Esta correção é
exclusivamente metodológica do relatório; mantém as 864 retenções e não altera
o parser, a associação A1 ou o painel publicado. Os totais por motivo conferem
entre as ressalvas por lançamento e o relatório de revisão. Unidades presentes
em mais de um motivo não devem ser somadas como se fossem distintas.

Mantidos os totais históricos: Passaredo A1 266; Forest Hill 178; OMA 530;
Vero 43; Itajubá 864; BPQ 115 (103 entre elegíveis). No Itajubá, a estatística
separada de seis lançamentos sem cadastro também permanece; não se preenchem
contatos ou documentos presumidos. Retenção cadastral não elimina dívida.
A referência preliminar OMA 267/38 continua retirada; as métricas 142/30 e 92/15
não são tratadas como equivalentes e sua metodologia publicada permanece intacta.

### Apresentação histórica, fora da conciliação financeira

Comparação separada por chave financeira/ocorrência, conservando a ordem em
cada grupo e removendo apenas o sufixo final ` - N` para a métrica de base.
Não se usa essa comparação para vincular uma pessoa ou ajustar o resultado.
O template não contém todos os identificadores originais; em chaves financeiras
repetidas, o pareamento por ocorrência não prova correspondência individual.

| Perfil | Base descritiva diferente | Rótulo completo diferente | Coluna de parcela diferente |
| --- | ---: | ---: | ---: |
| passaredo | 44 | 2154 | 250 |
| forest_hill | 3 | 10 | 7 |
| parque_santa_monica | 0 | 0 | 0 |
| vero_encanto | 3 | 3 | 0 |
| itajuba | 4 | 66 | 65 |
| terraco_beach_parque | 0 | 2 | 2 |

Essas métricas são distintas e não aditivas. Passaredo mantém sua descrição
literal da origem, enquanto o template acrescenta parcela ao rótulo: por isso
os 2.154 rótulos completos não são iguais. As 44 diferenças de base e as 250
comparações posicionais de parcela não motivaram alteração do contrato aprovado.
Forest Hill preserva as dez diferenças de rótulo histórico; Vero mantém três
rótulos históricos diferentes; OMA não teve diferenças nesses campos.
Itajubá mantém quatro classificações documentais históricas divergentes e 65
parcelas diferentes (66 rótulos completos, com sobreposição entre causas).
BPQ mantém duas diferenças de parcela/rótulo e nenhuma de conteúdo-base.
Não se alterou a ordem global para reproduzir nenhum template.

Itajubá: 119 unidades, 3.784 ocorrências, cinco grupos financeiros repetidos
preservados; 112 subtotais unitários mais o geral conferidos, sete avisos
`ITAJUBA_SUBTOTAL_NAO_IMPRESSO`, sem subtotal fictício. A contagem usa o código
exato do leitor, não uma busca textual por AUSENTE. O escopo de dezembro/2023
permanece conservador e coberto pelos testes individuais e cruzados.

BPQ: 1.010 recibos e 7.365 componentes na origem; 850 elegíveis; alertas do
cadastro completo permanecem um litígio, nove bloqueios de reenvio e duas
restrições a carta. Esses conjuntos se sobrepõem; no lote, os alertas só
alcançam a unidade correspondente. Pagador/locatário não substituem titular.
Nenhuma indicação antiga inicia contato, acordo, cobrança ou processo judicial.

## E. Privacidade, isolamento e pendências

Na preparação local, o worktree permaneceu sobre a base, com alterações locais
e staging vazio. Referências das branches originais e seus estados de trabalho
foram comparados com o início; inclusive os experimentos Windows não commitados
foram preservados integralmente. Não houve publicação durante a integração.
Somente a branch INT-02 recebeu autorização posterior de commit e push para
auditoria técnica, sem PR ou merge e sem homologação operacional.
Nenhum módulo da frente ACL experimental foi transportado.

O fluxo mantém bind 127.0.0.1, sessão automática HttpOnly/SameSite, CSRF,
Host/Origin, limites de upload/concorrência/cache, isolamento de download,
TTL, descarte após respostas e encerramento normal, sem histórico pessoal
permanente. Perfis e regras continuam configuração do software.
A integração não ampliou privilégios, exposição de rede ou funcionalidades.

Pendências explícitas:

- Windows não executado; Linux/Chromium não constituem homologação Windows.
- Inclusividade/vigência operacional dos prazos e atualidade dos vínculos
  documentais históricos exigem aprovação própria; não se atualizaram prazos.
- Memória: limite de cache não é orçamento global de RSS. Sem isolamento de
  processo e prazo máximo de CPU para parsers.
- Cancelamento pode aguardar worker; resultado sem destinatário pode expirar
  em memória. Shutdown normal aguarda workers sem prazo máximo.
- SIGKILL/queda de energia podem deixar resíduos; não há coleta segura de
  resíduos de execução anterior na inicialização. Sem garantia de apagamento
  forense, swap/dumps ou cópias no navegador/usuário.
- Diferenças históricas de classificação, descrição e parcela permanecem
  documentadas, sem ajuste financeiro ou atribuição cadastral para imitá-las.
- Fontes, dumps privados, logs, capturas e planilhas reais permanecem fora do
  Git. O pacote inclui somente agregados e imagens fictícias.

## Execução local

```bash
cd /workspace/Improvement-int02-seis-condominios
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web --port 8040
```

Abrir `http://127.0.0.1:8040`. Escolher a fonte, confirmar somente quando
compatível, fornecer cadastro opcional, data de referência e modo, conferir
pendências e baixar o diagnóstico. Não há autorização operacional.

## Arquivos do diff

- `docs/BEACH_PARQUE.md`.
- `docs/BPQ_01_ESCLARECIMENTO_CADASTRAL.md`.
- `docs/INT_02.md`.
- `docs/ITAJUBA.md`.
- `docs/VERO_ENCANTO.md`.
- `src/conversor/application/beach_parque_cadastro.py`.
- `src/conversor/application/itajuba.py`.
- `src/conversor/application/vero_cadastro.py`.
- `src/conversor/domain/beach_parque.py`.
- `src/conversor/domain/itajuba.py`.
- `src/conversor/domain/vero_encanto.py`.
- `src/conversor/export/identifiers.py`.
- `src/conversor/readers/beach_parque_cadastro.py`.
- `src/conversor/readers/beach_parque_identity.py`.
- `src/conversor/readers/beach_parque_xlsx.py`.
- `src/conversor/readers/itajuba_cadastro.py`.
- `src/conversor/readers/itajuba_identity.py`.
- `src/conversor/readers/itajuba_pdf.py`.
- `src/conversor/readers/vero_cadastro.py`.
- `src/conversor/readers/vero_identity.py`.
- `src/conversor/readers/vero_xlsx.py`.
- `src/conversor/web/ephemeral.py`.
- `src/conversor/web/perfis.json`.
- `src/conversor/web/perfis_saida.json`.
- `src/conversor/web/service.py`.
- `src/conversor/web/static/classico.js`.
- `src/conversor/web/static/efemero.js`.
- `tests/beach_parque/__init__.py`.
- `tests/beach_parque/fixtures.py`.
- `tests/beach_parque/test_beach_parque.py`.
- `tests/beach_parque/test_cadastral_clarification.py`.
- `tests/beach_parque/test_web.py`.
- `tests/int02/__init__.py`.
- `tests/int02/fixtures.py`.
- `tests/int02/test_integracao.py`.
- `tests/itajuba/__init__.py`.
- `tests/itajuba/fixtures.py`.
- `tests/itajuba/test_itajuba.py`.
- `tests/vero/__init__.py`.
- `tests/vero/fixtures.py`.
- `tests/vero/test_vero.py`.
