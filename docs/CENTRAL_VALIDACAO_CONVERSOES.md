# Marco de homologação e Central de Validação de Conversões

## Base homologada em testes locais (28/10/2026)

O usuário realizou testes no Windows com documentos privados da BBZ. O cenário ABROLHOS sem reenvio do template histórico e com aprovações individuais dos vínculos produziu, segundo conferência dos arquivos de saída na conversa:

- **Modo A:** 103 dívidas de 25 unidades; R$ 94.970,42.
- **Modo B:** 103 dívidas + 24 cadastros adicionais = 127 linhas; mesmo total financeiro.
- **Escopo:** 65 unidades sem prova individual permanecem retidas.
- **Pendências:** duas unidades com documentos/contatos conflitantes (9 linhas financeiras), sem liberação dos campos protegidos; 4 descrições `RECIBO` neutras.
- **Equivalência:** arquivos A e B sem template histórico relatados como idênticos aos XLSX de base obtidos com referência. Este documento **registra resultado de homologação humana**, não incorpora arquivos privados no Git nem equivale a homologação de importação/produção.

Persistência dos vínculos, revisão e revogação permanecem em `--private-dir` com histórico íntegro; **não apagar nem copiar chaves, evidências ou arquivos privados para o Git**.

## Continuação da Central — versão 2

Base da continuação: `main` em `14a5621`, incluindo PR #3 e a recuperação de
revogação acidental. Branch `feature/central-validacao-v2`. O início registrou
**1.886 testes regulares** aprovados. Nenhum arquivo local foi removido. As
regras, leitores, identificadores, composição, seleção, vínculos, contrato de 30
colunas e escritor XLSX permanecem os mesmos. A Central observa e retém downloads;
ela não corrige planilhas nem toma decisões financeiras ou cadastrais.

### Auditoria do MVP inicial e correções

| Lacuna demonstrada | Correção |
|---|---|
| Indicadores de dívidas/cadastros repetiam as linhas previstas | Contagens e soma observadas nos bytes do Excel, separadas das previstas |
| Soma esperada vinha somente do próprio planejamento | Comparação adicional com valor original, vencimento e unidade do canônico anterior ao enriquecimento |
| Dimensões XML podiam ocultar linhas/células | Percurso real das linhas, sem confiar no intervalo declarado |
| Dinheiro fracionário além dos centavos era aceito se o planejamento repetisse o erro | Decimal exato e rejeição, sem arredondamento automático |
| Retenções pessoais verificadas apenas quando vinham do cadastro persistente | União das retenções persistentes e da associação cadastral BBZ |
| Arquivo podia ser alterado após o laudo e servido por FileResponse | Hash do XLSX conferido novamente; resposta usa os mesmos bytes lidos, sem reabrir o caminho |
| Ausência/adulteração de XLSX ou laudo gerava falha de arquivo ou conteúdo divergente | Resposta 409 explícita; artefatos preservados para investigação |
| Link de download podia permanecer visualmente associado a seleção anterior | Limpeza do laudo, proteção contra seleção alterada durante o download e mensagem de reprocessamento |
| Painel mostrava apenas quatro números e avisos | Quatro áreas, estados de verificação e filtros por unidade, boleto, categoria e estado |

### O que é conferido

1. Somente aba `Dados`; cabeçalho literal, ordem e exatamente 30 colunas.
2. Linhas ausentes/excedentes/duplicadas; correspondência uma a uma entre dívidas
   previstas e decisões elegíveis, com vínculo à unidade e ao boleto canônico.
3. Tipo textual dos identificadores e campos cadastrais, CPF/CNPJ textual com
   formato `@`, datas válidas sem horário, parcelas inteiras positivas.
4. Valores numéricos positivos com centavos exatos. Comparação individual e soma
   dos boletos efetivamente selecionados, nunca com o bruto do relatório.
5. Cadastros adicionais sem Y:AD, no máximo um por unidade, conforme modo A/B e
   decisões existentes; não substituem dívidas nem contornam retenções.
6. Ausência de fórmulas executáveis, macros, objetos incorporados e relações
   externas. Texto literal parecido com fórmula permanece texto, sem execução.
7. Pertencimento quando exigido; nenhuma linha, inclusive cadastral, pode ser
   atribuída a unidade sem comprovação. Ausência do template não invalida vínculo
   persistente aprovado e íntegro. A Central não cria nem aprova vínculos.
8. CPF/CNPJ e contatos protegidos permanecem vazios mesmo com pertencimento
   aprovado. Documentos e contatos opcionais ausentes não viram bloqueio financeiro.
9. Hash e disponibilidade do arquivo no download; estado do cadastro de vínculos
   comparado ao snapshot da análise sob a trava existente. Decisão concorrente
   exige novo processamento nas próximas requisições. Os bytes enviados são os
   mesmos verificados, evitando troca do caminho entre verificação e envio.

Estrutura ilegível, diferença financeira, registro indevido ou exposição de dado
retido são críticos e impedem download. Exclusões corretas, dados pessoais
corretamente retidos e descrições neutras são ressalvas. Nenhum original é
alterado, removido ou corrigido. Laudo e arquivo original continuam privados.

### Limites de evidência

Cada verificação informa **Conforme**, **Conforme com ressalvas**, **Erro crítico**,
**Não verificável** ou **Não aplicável**. A comparação com o planejamento é
consistência interna. O confronto com o canônico do leitor é outra referência
interna rastreável, anterior ao enriquecimento, não uma extração independente.
A fidelidade integral ao PDF/XLSX de origem é explicitamente marcada como
**Não comprovável com as fontes disponíveis à Central**. Não há atesto humano
ou garantia de leitura integral por simples cópia de dados entre estruturas.

As regras de elegibilidade são consumidas como decisões do motor existente,
sem reexecução ou duplicação do motor. Os hashes das origens canônicas são
confrontados com os arquivos recebidos. O laudo registra referências documentais
sem incluir nomes, documentos, telefones, e-mails ou valores financeiros
individuais. Identificadores de unidade/boleto permitem filtrar a lista privada.

### Laudo JSON `validacao_conversao@2`

Arquivo privado `validacao_conversao.json`, disponível na sessão proprietária em
`GET /api/processamentos/{id}/validacao-conversao.json`. Campos:

| Campo | Conteúdo |
|---|---|
| `versao`, `estado`, `limite` | Versão e estado da conferência diagnóstica, com limites explícitos |
| `contexto` | Condomínio, administradora, referência explícita e modo |
| `arquivo` | SHA-256 dos bytes observados e completude da leitura do XLSX |
| `vinculos` | Revisão/hash do snapshot documental usado na análise |
| `indicadores` | Boletos, seleção financeira, exclusões, revisão, linhas observadas e previstas, totais observados/planejados/canônicos e escopo |
| `verificacoes` | ID, descrição, estado e evidência/limite de cada verificação |
| `registros` | Exclusões e retenções por unidade/boleto, motivo legível e localização documental, sem dados pessoais/valores individuais |
| `erros`, `avisos`, `motivos_retencao` | Falhas e ressalvas; detalhe de erros limitado a 100, com contagem integral separada |
| `contagem_erros`, `total_erros`, `detalhes_limitados` | Contagem integral, sem transformar truncamento em resultado positivo |
| `autoriza_cobranca`, `permite_exportacao_operacional` | Sempre `false` |

O laudo é uma fotografia do momento da análise. Não é uma aprovação atual de
pertencimento ou exportação. O endpoint do XLSX verifica novamente a integridade
e o snapshot de vínculos antes de disponibilizar os bytes. Laudo alterado em
disco é recusado. APIs preservam autenticação, proteção de origem e isolamento
entre sessões; não disponibilizam arquivos de outro usuário.

### Uso e revisão da interface

Após subir o servidor com o **mesmo** `--private-dir`, processar normalmente e
abrir a Central no painel de resultados:

1. **Resumo:** números efetivamente escritos, referência, modo e totais separados.
2. **Verificações:** estado e limite de cada conferência; desconhecido não é conforme.
3. **Inconsistências:** filtros por unidade, boleto, categoria e estado, com motivo
   em português e referência à evidência. Não mostra nomes/CPF/contatos.
4. **Relatório:** laudo JSON autenticado; alteração de seleção invalida links.

Erro crítico bloqueia o XLSX e preserva laudo/artefato. Uma ressalva legítima não
impede diagnóstico de registros aptos. Não há botão de aprovação operacional.
Exportação operacional e integração easyCollector permanecem desabilitadas.

### Regressões privadas e baselines recebidos

Os dois baselines homologados fornecidos pelo usuário foram copiados e
inventariados fora do Git, com permissões restritas e SHA-256. Não foram usados
para aprovar vínculos nem para alterar decisões ou preencher dados.

A reexecução ABROLHOS neste ambiente usa **referência histórica** para delimitar
o escopo, sem criar aprovações humanas. A e B coincidem com os anexos nas 30
colunas, tipos, ordem, identificadores, documentos, contatos, endereços e valores:

| Indicador | A | B |
|---|---:|---:|
| Dívidas | 103 | 103 |
| Cadastros adicionais | 0 | 24 |
| Linhas totais | 103 | 127 |
| Total | R$ 94.970,42 | R$ 94.970,42 |

25 unidades comprovadas; 65 sem prova, fora da saída; 2 unidades com conflitos,
9 linhas com CPF/contatos retidos; 4 descrições neutras. Os membros internos dos
arquivos ZIP são idênticos aos anexos. O SHA-256 global difere por metadados de
plataforma do contêiner ZIP (Windows/Linux); não se declara identidade byte a byte
entre plataformas.

A execução real **sem template com o cadastro aprovado** depende do Windows do
usuário, cuja pasta de vínculos não está acessível aqui. O cadastro não foi
reinicializado, editado, copiado ou substituído. Esse cenário foi exercitado aqui
somente com fixtures e aprovações sintéticas. Não se declara nova homologação
Windows/produção com base nos testes Linux.

### Testes e revisão antes do merge

- Na entrega inicial da V2, **2.006 testes distintos aprovados:** 1.946 regulares
  e 60 históricos explícitos. A Central tinha 67 casos focados (7 anteriores e 60 novos).
  Os 162 casos de Central/vínculos/reabertura também passaram em Python 3.13.5
  no Linux; execuções repetidas não são somadas como casos novos.
- 22 cenários privados: 20 dos seis condomínios anteriores com canônicos/XLSX
  byte a byte idênticos, mais ABROLHOS A/B contra os baselines recebidos.
- Testes sintéticos: corrupção, cabeçalho/abas/colunas, linhas ausentes/duplicadas,
  dinheiro, datas, documentos textuais, cadastros, proteção pessoal, comparação
  canônica, vínculos e downloads concorrentes.
- Chromium: quatro áreas, filtros, laudo e XLSX, retenções pessoais, adulteração,
  nova análise, descarte de links antigos e versão móvel, sem erros JavaScript.
- Python 3.12 e casos focados em Python 3.13.5 no Linux; não substituem Windows.
- Oito verificações históricas de schemas e a verificação dos schemas de vínculos.
- Regressões privadas dos sete condomínios, sem publicar fontes ou relatórios
  confidenciais; resultados agregados na entrega. Artefatos anteriores preservados.

```sh
python -m pytest -q tests/test_conversion_validation.py
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
python -m conversor.document_link_schemas --check
```

**Pendente no Windows:** iniciar com a pasta privada original, reprocessar ABROLHOS
em A/B sem template, confirmar os indicadores acima e presença da unidade
E/A00223 já aprovada pelo responsável, comparar as 30 colunas com os anexos,
confirmar retenções, download/laudo e invalidação após nova decisão de vínculo.
Não alterar manualmente registros, chaves ou checkpoints para executar o teste.
O PR é para revisão; merge e liberação operacional não são automáticos.

### Portabilidade dos testes de symlink — Windows sem privilégios

Na execução Windows 11/Python 3.13 informada pelo responsável, os dois cenários
de link real da Central falharam na preparação com `WinError 1314`; isso não era
falha do bloqueio em produção. Esses cenários agora tentam criar o symlink e usam
`SKIPPED` **somente** quando o `OSError` apresenta `winerror == 1314`, com motivo
explícito. Outros erros são propagados. Não há skip geral para Windows; os testes
reais continuam executando onde a operação é permitida.

Há dois testes adicionais, sem criar links, que sinalizam um caminho como
simbólico e verificam a rejeição pelo validador e pelo endpoint antes de qualquer
leitura do alvo. Testes do helper confirmam o skip específico e a propagação de
outros erros de criação. Nenhum código de produção, contrato, vínculo, regra ou
geração de Excel foi alterado por essa correção.

Reexecutar `python -m pytest -q -rs tests/test_conversion_validation.py` no Windows.
Em ambiente que negue os dois links por 1314, somente esses dois cenários devem
aparecer como skips justificados. A simulação dessa restrição no Linux não
constitui homologação Windows completa nem certifica a portabilidade das outras
suítes, que têm seus próprios testes de sistema de arquivos.

Na regressão completa desta correção foi identificada uma instabilidade no teste
de idempotência WIN: ele recriava o XLSX sintético em cada execução, produzindo
hashes de entrada diferentes; as divergências observadas eram apenas os hashes
de origem. O teste agora reutiliza os mesmos bytes nas duas execuções, mantendo
integralmente as comparações de decisões, canônicos e XLSX. O gerador de fixtures
e o código de produção não foram alterados.

Após a correção: **74 testes focados aprovados, 0 falhas, 0 skips**, em Linux
com Python 3.12 e 3.13.5. Injeção explícita do erro 1314: **72 aprovados, 0 falhas,
2 skips**, apenas os dois cenários de link real. Regressão completa em Python
3.12/Linux: **1.953 regulares + 60 históricos = 2.013 testes distintos aprovados**,
sem falhas ou skips. O warning de depreciação existente permanece. Esses resultados
não equivalem a uma nova execução nativa Windows.

## Correção final — Windows, proteção real e motivos de retenção

Continuação de `0cea106`, na mesma branch; sem merge automático. O responsável
confirmou no Windows 11/Python 3.13 o fluxo ABROLHOS **sem template**, com vínculos
reais previamente aprovados: A 103 dívidas, B 103 + 24 cadastros, R$ 94.970,42,
25 unidades comprovadas, 65 sem pertencimento, nove linhas com dados pessoais
retidos, quatro descrições neutras e a unidade E/A00223 presente. Os XLSX eram
byte a byte idênticos aos baselines naquele Windows. Essa homologação funcional
informada é preservada; não comprova a execução nativa das novas verificações ACL.

### Diagnóstico dos 14 casos relatados

O mapeamento abaixo foi conferido no código; a execução Windows original foi
informada pelo responsável, não reproduzida em uma máquina Windows neste ambiente.

| Grupo | Casos existentes | Causa e tratamento |
|---|---|---|
| Symlinks: 9 | 5 caminhos de vínculos (registro, chave, lock, evidências, checkpoints), 1 ancestral, 1 fonte preservada, 1 fonte Fase 3 e 1 simulação privada | Criação indisponível por WinError 1314. Helper compartilhado omite somente o cenário de link real; outros erros são propagados |
| Permissões: 3 | Canônico privado, auditoria de revisão Fase 3 e auditoria documental | Igualdade com `0600` não comprova ACL NTFS. Asserções continuam POSIX no Linux e conferem DACL nativa no Windows |
| Permissões: 2 | Fonte e raiz de armazenamento de simulações tornadas permissivas | `chmod` não injeta uma concessão NTFS equivalente. No Windows a fixture concede leitura a Everyone e exige rejeição real; não é skip |

A recusa de armazenamento em Git foi separada do teste de ancestral simbólico,
para continuar sendo executada mesmo sem privilégio de criar symlink. Testes
independentes sinalizam symlink/reparse sem criá-lo e exigem recusa antes de
leitura ou criação. Os testes de links reais e de permissões POSIX permanecem.

### Falhas reais de proteção identificadas e correção separada

As leituras de autoridade, simulações e vínculos anteriormente verificavam modo
apenas em POSIX. `chmod` no Windows não provava privacidade. Foi acrescentado
`adapters/private_permissions.py`, com APIs nativas `GetNamedSecurityInfoW`,
`GetAce` e consulta ao token do usuário; sem pywin32, PowerShell no backend,
serviços externos ou privilégios administrativos exigidos pelo programa.

A política local é conservadora: usuário atual, SYSTEM e Administradores são a
fronteira de confiança. Grants a outras identidades, inclusive herdados e de
somente leitura, são rejeitados. DACL nula é insegura. ACE condicional/objeto,
deny ou ausência de controle necessário do usuário não é aprovada por aproximação:
a privacidade fica **não comprovada** e a operação é retida. Não é um calculador
universal de Effective Access nem certificação de configuração corporativa.

- **Linux:** verificações existentes de `0600`/`0700`, recusa de permissividade,
  links, Git e hashes/HMAC preservadas e executadas com objetos reais.
- **Windows:** conferência nativa da DACL em raiz, chaves e arquivos privados;
  objetos novos recebem DACL restrita antes de gravar bytes sensíveis. Diretórios
  novos privados também recebem proteção explícita, inclusive em Python 3.12.
  Pastas e arquivos existentes são conferidos; não têm ACL reescrita silenciosamente.
- As leituras de fontes não resolvem mais uma raiz simbólica antes de conferir o
  redirecionamento. Symlinks/reparse em raiz ou ancestrais são recusados; o teste
  alternativo comprova recusa antes de ler o alvo ou criar artefatos.
- Escrita atômica, conteúdo, versões, assinaturas, chaves e checkpoints históricos
  não mudam. As alterações de proteção não alteram o escritor XLSX nem o motor.

As APIs Windows foram implementadas e a política foi exercitada por injeção de
ACLs conhecidas no Linux. Asserções de plataforma e testes de concessão/rejeição
invocarão o backend nativo quando executados no Windows. **Não se declara que
essas chamadas nativas tenham sido executadas neste ambiente Linux.**

### Auditoria somente de leitura no Windows, sem administrador

Antes de iniciar o servidor atualizado, executar com a conta que usa o MVP:

```powershell
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
```

O comando não lê conteúdo de PDFs, chaves ou cadastros, não altera ACLs e não
aprova vínculos. O resumo não publica nomes de arquivos, SIDs ou dados pessoais.
`politica_local_confere` significa que a política local conferiu nos objetos
percorridos; não é homologação de fontes/produção. Falha, caminho redirecionado,
ACL indisponível ou subdiretório que não possa ser percorrido retorna código 2,
com classificação, sem presumir privacidade de objetos não conferidos.

Se houver falha, preservar backup privado da árvore **e** de suas ACLs e revisar
localmente com `Get-Acl -LiteralPath`/`icacls`. Conferir owner, grants, herança e
as identidades autorizadas. Não publicar essa saída. Não usar `chmod`, reset de
cadastro ou remoção de chaves/checkpoints como solução. A conta proprietária
pode administrar suas ACLs; esta entrega não força elevação nem aplica uma
correção genérica às pastas existentes. Se disponível uma segunda conta de teste
já existente, a tentativa de leitura deve ser negada; essa verificação adicional
não foi executada aqui.

### Indicadores aditivos em `validacao_conversao@2`

`application/contact_retention.py` classifica motivos explícitos da auditoria
cadastral, do escopo e das pendências persistentes. Não deduz conflitos por
diferença de totais. Uma unidade pode pertencer a vários conjuntos; os contadores
não devem ser somados como categorias mutuamente exclusivas.

| Campo | Significado | ABROLHOS |
|---|---|---:|
| `unidades_escopo_comprovado` | Unidades com evidência de pertencimento | 25 |
| `unidades_escopo_pendente` | Unidades explicitamente sem comprovação | 65 |
| `unidades_vinculo_persistente` | Comprovação por vínculo persistente aprovado | 25 no Windows homologado sem referência |
| `unidades_conflito_documental` | Conflito indicado nas evidências documentais | 2 |
| `linhas_financeiras_contatos_retidos` | Dívidas efetivamente escritas com dados protegidos | 9 |
| `unidades_outros_dados_protegidos` | Outros motivos explícitos ou ainda não classificados | 0 |
| `boletos_em_revisao` | Boletos, não unidades, retidos na análise | 71 |
| `descricoes_neutras` | Rótulos neutros observados no XLSX | 4 |

Compatibilidade: `unidades_contato_retido` permanece como **total de unidades
protegidas** (67 neste caso), com descrição neutra; não significa 67 conflitos.
`linhas_com_contato_retido` mantém o valor anterior (9). O novo array
`retencoes_classificadas` contém apenas IDs internos e motivos, sem CPF/CNPJ,
nomes, telefones ou e-mails. Motivo desconhecido permanece não classificado;
proteção é conservada, sem inventar conflito. O painel separa os grupos de
pertencimento e proteção documental e explicita a distinção boletos/unidades.

### Critérios de revisão desta correção

- Reexecutar os seis módulos de testes indicados na tarefa e os novos
  `tests/test_private_permissions.py` e `tests/test_contact_retention.py`.
- Não remover outras falhas por skip. A simulação de erro 1314 valida somente a
  indisponibilidade de criar links, não simula ACL NTFS ou uma execução Windows.
- Os fixtures de permissões usam somente diretórios temporários novos; nenhum
  teste deve apontar para a pasta privada real do responsável.
- No Windows real: conferir a auditoria ACL, rodar as suítes com a conta comum,
  reiniciar com o mesmo `--private-dir` e repetir A/B sem referência e sem novas
  aprovações. Comparar os hashes naquele ambiente e os novos indicadores.
- Não confundir os resultados Linux/sintéticos com homologação completa Windows.

### Evidências finais desta implementação

| Execução neste ambiente | Aprovados | Falhas | Skips |
|---|---:|---:|---:|
| Suíte regular, Linux/Python 3.12 | 1.985 | 0 | 0 |
| Históricos explícitos, Linux/Python 3.12 | 60 | 0 | 0 |
| Módulos focados e novos testes, Linux/Python 3.13.5 | 256 | 0 | 0 |
| Mesmos módulos com injeção de WinError 1314, Linux | 245 | 0 | 11 |

Total distinto: **2.045** (as reexecuções e subconjuntos não são somados).
O único warning de depreciação já existente permanece. Os onze skips da simulação
são os dois cenários da Central mais os nove cenários relatados; não há skip de
permissões nessa simulação. As duas verificações POSIX específicas de autoridade
que já existiam continuam específicas dessa plataforma; há cobertura adicional
portável de permissões de raiz, fontes, chave e auditoria.

As oito verificações históricas de schemas e a de vínculos passaram. Chromium
conferiu os grupos de indicadores, filtros, laudo/download, bloqueio por
adulteração, seleção alterada e viewport móvel, sem erros JavaScript, com dados
sintéticos. Os testes de ACL incluem grants explícitos/herdados amplos, DACL nula,
owner diferente, ACE não interpretável, backend indisponível, proteção antes da
escrita e recusa de reescrever ACL existente, inclusive corrida de criação.

As 20 regressões privadas de TREE, PLAZA, NOVA YORK, INNOVA, NOVA REBOUÇAS e WIN
preservam canônicos e XLSX byte a byte. ABROLHOS A/B foram reprocessados aqui
**com referência**, sem criar aprovações reais, e coincidem nas 30 colunas,
tipos e ordem com os baselines recebidos. Os novos indicadores foram conferidos:
25/65 unidades, 2 conflitos conhecidos, 9 dívidas com contatos retidos, 71 boletos
em revisão, 4 descrições neutras e 0 outras restrições. A: 103 dívidas; B: mesmas
103 + 24 cadastros; R$ 94.970,42. Diferenças de hash entre os anexos Windows e
Linux decorrem dos metadados ZIP de plataforma; não se afirma identidade global
byte a byte entre esses ambientes.

**Pendência de execução, não substituída por simulação:** o novo backend ACL
nativo, a auditoria da pasta original e o fluxo completo sem referência devem ser
reexecutados no Windows do responsável, com a conta comum. As aprovações reais
permanecem apenas naquele computador e não foram reproduzidas artificialmente.
Não há homologação Windows completa desta correção ou liberação para produção.

### Investigação da divergência nativa de ACL (Windows 11)

O teste do responsável no commit `03b0d29` encontrou três ACEs nas duas
leituras, mas uma identidade da leitura Python não aparecia em
`GetAccessRules`. O SID do processo coincidia. Isso demonstra divergência entre
as leituras, **não demonstra que a ACL seja segura nem comprova a causa**.
A inspeção estática confirmou o deslocamento SID=8 de uma ACE allow básica,
DWORD de 32 bits, cabeçalhos ACE/ACL de 4/8 bytes e as assinaturas por ponteiros.
Não foi reproduzido aqui um defeito que explique a terceira identidade.

O reforço do leitor elimina dependência de ponteiros do descritor depois de
`LocalFree`: copia os bytes ainda vivos, valida offsets/tamanhos e decodifica o
SID com limites explícitos. O SID do token também é copiado dentro de seu buffer
`TOKEN_USER` e confrontado com a conversão nativa. A leitura normal exige
concordância entre `GetNamedSecurityInfoW`, `GetFileSecurityW` e `GetAce` aplicado
a um buffer copiado e validado. Duplicatas são preservadas; apenas mudança de
ordem de ACEs não é confundida com mudança das identidades/regras.

Esses controles são preventivos. Um problema anterior de duração/conversão de
ponteiros continua hipótese, não causa comprovada. Diferença de descritor entre
APIs, alteração concorrente da ACL ou projeção parcial pelo .NET também precisam
ser distinguidas no ambiente afetado. Nenhuma terceira identidade é substituída
pelo usuário por suposição. `GetFileSecurityW` é uma segunda leitura nativa; a
comparação adicional com .NET é uma ferramenta diagnóstica, não uma dependência
PowerShell para as operações normais do aplicativo.

#### Repetir sem alterar a pasta privada

Na mesma conta comum do Windows, atualizar **a branch de testes**, não a main:

```powershell
git switch feature/central-validacao-v2
git pull --ff-only origin feature/central-validacao-v2
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado" --comparar-leituras
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
python -X utf8 -m pytest -q tests/test_private_permissions.py tests/test_windows_acl_reader.py tests/test_acl_diagnostics.py
```

`--comparar-leituras` confere somente a raiz indicada, por quatro projeções:
bytes de cada API, GetAce e PowerShell `Get-Acl/GetAccessRules` com
`SecurityIdentifier`. Mostra owner/usuário/regras como HMACs com chave efêmera
compartilhada apenas pelos processos dessa execução. Não imprime SIDs, contas,
caminho privado, descritores ou stderr bruto; não grava a chave nem o relatório.
IDs de duas execuções não podem ser correlacionados. O comando de auditoria
normal, na linha seguinte, percorre a árvore e pode apontar restrições adicionais
nos arquivos. Nenhum dos dois modifica permissões, vínculos ou arquivos privados.

- `leituras_coerentes` + `politica_local=confere`: quatro projeções concordam e
  a política local confere para aquele objeto/instante. Não atesta documentos ou
  vínculos e não libera operação financeira.
- `leituras_divergentes`: conferir a origem que diverge e os campos
  `usuario_igual`, `proprietario_igual`, `regras_iguais`, `ordem_igual` e contagens.
  Diferença somente de ordem é relatada, sem eliminar duplicatas. Não é sucesso.
- `nao_comprovado`: o campo `etapa` identifica onde faltou uma leitura íntegra,
  inclusive API indisponível, ACE inválida ou projeção .NET parcial. Não é sucesso.
- Leituras coerentes com `ACL_PRIVADA_INSEGURA` ou
  `ACL_PRIVADA_NAO_COMPROVADA`: a concordância não torna a ACL adequada.
  Identidades adicionais, owner não permitido, DACL nula/ausente e tipos de ACE
  não suportados continuam impedindo o acesso. Uma divergência nas leituras
  normais vira `ACL_PRIVADA_NAO_VERIFICAVEL`.

Se persistir ACL inadequada, guardar localmente a saída diagnóstica e revisar
com o proprietário/administrador **qual** identidade, grant, owner ou regra de
herança viola a política. Propor uma alteração específica daquela permissão para
aprovação humana, preservando os descritores originais; não executar reset de
ACL, concessão genérica de controle total, remoção de chaves/checkpoints ou
substituição de SID desconhecido. Nenhuma remediação foi executada nesta entrega.

Os testes novos usam um descritor binário sintético independente com três SIDs
de tamanhos diferentes, ponteiros ctypes sobre buffers locais e comparação de
projeções pseudonimizadas. Exercitam libertação envenenando o buffer original,
limites do token/ACE, conversão divergente, diferença de identidade/máscara/
flags, duplicatas, DACL nula/ausente, deny e ACE desconhecida. Esses testes
**não executam as APIs Windows no Linux**. Dois testes de arquivo/diretório
comparam realmente as APIs com PowerShell quando executados no Windows;
somente eles são skipped em sistemas não Windows. As proteções POSIX e a
política de permissões permanecem iguais. Não houve alteração de leitores,
regras, XLSX, vínculos ou histórico.

A resolução da ocorrência original e a homologação Windows permanecem pendentes
da nova comparação nativa na pasta afetada e da auditoria completa. Não se
conclui que o caso relatado foi corrigido apenas com testes Linux.

Resultados desta investigação: suíte regular Linux/Python 3.12 com **2.051
aprovados, zero falhas e dois skips** (comparação nativa Windows de arquivo e
diretório); históricos explícitos com **60 aprovados, zero falhas/skips**.
Total distinto: **2.111 aprovados e dois skips**. Os três módulos focados em
Python 3.13.5/Linux tiveram **91 aprovados e dois skips**, sem falhas. Permanece
um warning preexistente de depreciação AnyIO/Starlette. A revisão automatizada
das alterações e comparação com padrões privados não encontraram documentos,
dados pessoais reais ou credenciais. Não houve reprocessamento de documentos
financeiros reais nesta investigação.

### Investigação em aberto: flags 3/19 e identidade diferente (base `fd0389c`)

A nova execução do responsável mostrou três grants de controle total nas duas
leituras. Nas APIs Win32, flags `3` (`OBJECT_INHERIT | CONTAINER_INHERIT`), com
uma identidade adicional; em `GetAccessRules` e no binário exportado por
`Get-Acl`, flags `19` (as mesmas flags mais `INHERITED_ACE=16`) e usuário atual.
Isso comprova diferença entre as representações reportadas. **Não comprova que a
identidade adicional seja CREATOR OWNER, OWNER RIGHTS, nem que qualquer uma das
ACLs seja segura. A causa permanece desconhecida.**

Foi identificado um parâmetro que faltava isolar: o leitor pede
`OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION = 0x5`; o caminho padrão
.NET também inclui `GROUP_SECURITY_INFORMATION`, resultando em `0x7`. O wrapper
.NET público usa GetNamedSecurityInfo por nome ou GetSecurityInfo por handle e
constrói RawSecurityDescriptor sobre os bytes copiados. Isso fundamenta testar
5/7 e a etapa de construção .NET; **não fundamenta trocar o parâmetro do leitor
ou atribuir a ele a causa** sem execução nativa.

Referências para esta investigação:

- [SECURITY_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-information)
- [GetNamedSecurityInfoW](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getnamedsecurityinfow)
- [GetFileSecurityW](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getfilesecurityw)
- [Propagação automática de herança](https://learn.microsoft.com/en-us/windows/win32/secauthz/automatic-propagation-of-inheritable-aces)
- [Wrapper público .NET](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Security.AccessControl/src/System/Security/AccessControl/Win32.cs)

Essas referências descrevem APIs/semântica, não são evidência da causa no
computador afetado. A implementação .NET instalada no Windows 11 ainda precisa
ser confrontada no próprio ambiente.

#### Coleta dirigida, sem remediação

O novo `--investigar-heranca` mantém um handle Python de leitura aberto, sem
share-delete, enquanto executa o probe PowerShell/C# local. No **mesmo processo
PowerShell**, o probe compara:

- GetNamedSecurityInfoW e GetFileSecurityW, com máscaras 5 e 7;
- GetSecurityInfo com 5 e 7 no mesmo handle mantido aberto;
- FileSystemSecurity com seções explícitas equivalentes a 5 e 7;
- Get-Acl, seu RawSecurityDescriptor e a projeção GetAccessRules sobre o mesmo
  objeto ACL, com uma nova serialização após GetAccessRules;
- roundtrips RawSecurityDescriptor/CommonSecurityDescriptor **somente em
  memória**, para isolar possíveis transformações .NET;
- os bytes das duas leituras Python originais, transmitidos por stdin, usando
  RawSecurityDescriptor e GetAce para verificar os parsers independentemente.

São confrontados identificadores de volume/arquivo derivados por HMAC, antes e
depois, caminho final do handle versus solicitado, identidade efetiva versus
identidade do processo, tipo de objeto e estabilidade do descritor. O probe
mantém seu próprio handle aberto sem share-delete. Caminhos redirecionados não
são aceitos. Mudança de objeto, leitura parcial, impersonação ou descritor
instável invalida a comprovação. Não se confunde coincidência do nome com
identidade do objeto.

As máscaras das chamadas Win32 e seções dos construtores .NET são controladas
explicitamente. Para Get-Acl/GetAccessRules, `security_information=null` indica
que os parâmetros internos do provider instalado não foram interceptados; não
se registra 7 como parâmetro observado por suposição. A comparação com os
construtores .NET explícitos permite investigar esse caminho separadamente.

O relatório distingue igualdade binária integral, igualdade da DACL, diferenças
de controle/grupo, igualdade das regras e alteração **somente** do bit 16.
Esta última é uma observação, não equivalência automática de segurança: se SID,
máscara, tipo ou outro bit também mudar, o diagnóstico não a classifica como
mera diferença de marcador herdado. As regras e duplicatas são conservadas.

`creator_owner`, `creator_group`, `owner_rights`, `everyone` e
`authenticated_users` são classificações de SIDs especiais públicos, identificados
por igualdade exata. Não são novas identidades permitidas. CREATOR OWNER é um
placeholder relevante à herança; OWNER RIGHTS é outro principal, relacionado aos
direitos do proprietário. Um não pode ser substituído pelo outro ou pelo usuário
sem evidência. Nenhuma transformação é aplicada à ACL ou à política.

SIDs/contas/caminhos/descritores não são impressos: o relatório usa HMACs com
chave efêmera por execução, inclusive para bytes dos descritores e DACLs. A chave
e os descritores transitam apenas em memória/stdin. Não há campos arbitrários
vindos do subprocesso na resposta, nem stderr ou mensagens brutas de exceção.
Nenhuma política de execução do PowerShell é alterada e nenhuma elevação é
solicitada. Add-Type pode usar temporários/caches de compilação do .NET; não
escreve na área privada nem embute descritores na fonte compilada.

#### Comandos para o responsável (Windows)

```powershell
git switch feature/central-validacao-v2
git pull --ff-only origin feature/central-validacao-v2
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado" --investigar-heranca
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado" --comparar-leituras
python -X utf8 -m conversor.private_security --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
python -X utf8 -m pytest -q tests/test_windows_acl_investigation.py tests/test_windows_acl_reader.py tests/test_acl_diagnostics.py tests/test_private_permissions.py
```

`--investigar-heranca` sempre termina com código **2**, investigação pendente e
`autoriza_acesso=false`, mesmo quando as leituras coincidirem. É uma coleta de
evidências, não a auditoria nem uma liberação. Compartilhar apenas o JSON desse
diagnóstico e o resumo dos testes; não compartilhar SDDL, chaves, saída de
icacls, descritores, nomes de contas ou conteúdo da área privada. Se falhar,
`etapa` identifica caminho/objeto/leitura/compilação, sem revelar a exceção.

#### Critério para prosseguir

Os seis novos casos nativos usam **somente diretórios temporários sintéticos**:
ACL explícita, ACL herdada, CREATOR OWNER, OWNER RIGHTS, grant a Everyone e
propagação do CREATOR OWNER para um filho. Apenas as ACLs dessas fixtures novas
são configuradas; a investigação deve preservá-las byte a byte. Everyone e
principais especiais continuam bloqueados pela política conservadora. São
verificados o mesmo objeto, parsers independentes, estabilidade e ausência de
autorização. Os casos são skipped fora do Windows, sem emular sucesso nativo.

**Não há correção causal publicada nesta etapa.** O leitor/política de
`fd0389c` permanecem intactos, inclusive o bloqueio original. Só após o resultado
nativo será possível distinguir uma transformação legítima de herança,
representações distintas por parâmetros, falha do parser, diferença de processo
ou inconsistência real. Qualquer ajuste de autorização dependerá dessa evidência,
com regressão contra acesso efetivamente amplo. Não há merge na main, mudança
financeira, processamento de documentos, alteração de vínculos/chaves/históricos
ou homologação Windows concluída. Esta investigação não está encerrada.

Verificações desta coleta: suíte regular Linux/Python 3.12, **2.081 aprovados,
zero falhas, oito skips nativos**; históricos explícitos, **60 aprovados**, sem
falhas/skips. Total distinto: **2.141 aprovados**. Focados em Python 3.13/Linux:
**121 aprovados, zero falhas, oito skips**. Um warning AnyIO/Starlette já existente.
O wheel foi construído e contém os três recursos Python/PowerShell/C# necessários.
O código C#/PInvoke e a execução PowerShell deste probe **não foram compilados ou
executados neste ambiente Linux**; fazem parte da validação nativa pendente.
A revisão de privacidade não identificou dados reais ou credenciais nas mudanças.

### Evidências nativas de `9b129c4` e coleta dirigida v3

O responsável executou o probe no Windows 11: leituras completas e estáveis,
mas `objeto_e_identidade_comprovados=false`. Python Named/File retornaram 120
bytes, OWNER RIGHTS e flags 3; C# Named/Handle/Get-Acl retornaram 164 bytes,
usuário e flags 19; C# File retornou 136 bytes, usuário e flags 3. Esses resultados
são evidência recebida, não execução Windows neste ambiente Linux.

**O booleano agregado anterior não identifica a comparação que falhou.** Ele
combinava identidade por HMAC, estabilidade, comparação literal de caminho,
share-delete e identidade efetiva. Portanto, sua falsidade não comprova, sozinha,
que o handle Python aponte para outro arquivo. Os layouts revisados de
BY_HANDLE_FILE_INFORMATION têm 13 DWORDs, tamanho 52, volume no offset 28 e
índices alto/baixo nos offsets 44/48. Não foi encontrado defeito de layout ou
formatação na inspeção; a nova execução conferirá isso independentemente.

O responsável confirmou instalação do Python pela **Microsoft Store**. A
[documentação oficial do Python](https://docs.python.org/3.13/using/windows.html#redirection-of-local-data-registry-and-temporary-paths)
descreve redirecionamento de AppData para cópias privadas em instalações da Store.
Isso é uma hipótese concreta de resolução por processo, **ainda não comprovação
sobre a pasta afetada**. Não se recomenda mover, copiar, recriar ou mesclar
pastas, chaves ou vínculos com base nessa hipótese.

#### Correção comprovada da preparação do teste

`tests/bbz/test_persistent_links.py::repo` criava sua raiz com
`mkdir(mode=0o700)` e só depois construía o repositório. O
[código CPython 3.13](https://github.com/python/cpython/blob/3.13/Modules/posixmodule.c)
(`os_mkdir_impl`, ramo MS_WINDOWS) aplica nesse modo uma DACL protegida com
SYSTEM, Administradores e OWNER RIGHTS. Não é correto afirmar genericamente que
o modo é ignorado no Windows 3.13. A política atual do conversor rejeita o
principal especial; a raiz já existente não é corrigida automaticamente. Assim,
a fixture podia falhar antes de chegar à alteração intencional da chave.

O auxiliar agora usa `criar_diretorio_privado` na criação da **nova raiz
sintética**, incluindo o mecanismo de proteção Windows existente. A mesma
fixture não repara silenciosamente uma raiz preexistente insegura. O teste da
chave confere primeiro a privacidade da raiz/chave, torna somente a chave
sintética permissiva, exige a rejeição e confirma a preservação dos bytes da
chave e do registro. A política e o repositório de produção não mudaram.
Um teste nativo adicional confere a DACL criada pelo mkdir no CPython 3.13+;
sua execução local permanece pendente.

#### O que a v3 distingue

`evidencias.comparacao_objeto` e `probe.comparacao_identidade` acrescentam apenas
booleanos de comparação, nunca valores de volume, índices, caminhos, nomes de
pacotes ou tokens:

- Igualdade de volume, índices alto/baixo, identidade completa e sua serialização
  hexadecimal unsigned com largura mínima 8 e cultura invariável.
- Compatibilidade do HMAC com vetor binário fixo, tamanho e offsets dos layouts
  ctypes/PInvoke, arquitetura e identidade do usuário do processo.
- Estabilidade do handle Python, do handle C# e das reaberturas C#, separadas da
  igualdade entre processos; cada parcela do agregado é visível.
- Correspondência dos caminhos finais obtidos dos handles e do caminho
  solicitado. Diferenças meramente literais de prefixo Win32, capitalização ou
  separador final não são tratadas, sozinhas, como troca de objeto.
- Presença/verificabilidade de identidade de pacote e comparação dos flags de
  token AppContainer, elevação e virtualização. Os flags de virtualização UAC
  não comprovam nem descartam, sozinhos, redirecionamento da Store.

Os valores necessários transitam apenas em memória/stdin. C# tenta reabrir o
caminho final obtido do handle Python e **só consulta a ACL nessa leitura cruzada
se o identificador conferir com o handle Python**. A disponibilidade dessa
reabertura e sua identidade são booleanos separados. Os três resultados
`Python_final_*` distinguem essa leitura da leitura do caminho solicitado. Falha
na abertura ou identidade inconclusiva não libera nada. `leituras_completas`
cobre a matriz principal; `leituras_caminho_fisico_completas` cobre a leitura
cruzada adicional. Ambas precisam ser examinadas.

`Named_5_selected` repete em C# a máscara 5 com ponteiros group/sacl NULL;
`Python_Named_5_all` repete em ctypes os quatro ponteiros `out`. O campo
`saidas_opcionais` registra owner/group/dacl/sacl por booleanos em cada fonte,
além da máscara e API já registradas. Isso isola os argumentos dentro de cada
processo. A hipótese dos ponteiros opcionais, sozinha, não explica a divergência
Python/C# de **GetFileSecurityW**, que não tem esses ponteiros de saída.
Também são repetidas as leituras Python após o probe: alteração de descritor
passa a invalidar `descritores_estaveis`, mesmo com identidade de arquivo estável.

| Evidência | Significado que pode ser afirmado |
|---|---|
| Flags 3 / 19 | OI+CI / OI+CI+INHERITED_ACE; diferença de marcador, não aprovação |
| Controle 0x9004 / 0x8004 | SELF_RELATIVE+DACL_PRESENT, com/sem DACL_PROTECTED |
| OWNER RIGHTS | Principal especial relativo ao proprietário, não SID literal do usuário nem CREATOR OWNER |
| Grupo/controle/SID diferentes | Diferenças adicionais; não podem ser ignoradas por haver apenas bit 16 em outras ACEs |

`controle_decodificado` explicita DACL_PROTECTED (0x1000),
DACL_AUTO_INHERITED (0x400), AUTO_INHERIT_REQ (0x100) e SELF_RELATIVE (0x8000).
Nenhum desses bits é confundido com INHERITED_ACE (0x10) do cabeçalho da ACE.
OWNER RIGHTS, CREATOR OWNER, Everyone e demais identidades não foram incluídos
na lista permitida. A auditoria original pode continuar rejeitando a raiz.

#### Interpretação antes de propor qualquer correção adicional

1. HMAC/layout incompatíveis: investigar instrumentação; não concluir troca de
   arquivo. Componentes iguais com serialização diferente também exigem revisão
   da instrumentação.
2. Somente comparação literal de caminho falha: avaliar os caminhos normalizados
   e a identidade; isso não demonstra troca de objeto.
3. Layout/HMAC compatíveis, componentes e caminhos finais distintos e reabertura
   do caminho Python comprovada: evidência forte de resolução diferente por
   processo; confrontar as ACLs da leitura cruzada e os indicadores de pacote.
4. Mesmo objeto comprovado, resultados diferentes: confrontar a matriz NULL/out,
   APIs e construtores .NET, contexto e estabilidade; não normalizar por aproximação.

A causa da divergência da **pasta real** continua pendente até essa conferência.
Não foi alterado o leitor de permissões ou sua política. Não houve acesso a
PDFs/XLSX reais, alteração de ACLs reais, vínculos, chaves ou históricos.

Para repetir no Windows, com a mesma conta e sem elevação:

```powershell
git switch feature/central-validacao-v2
git pull --ff-only origin feature/central-validacao-v2
$conversorPrivado = "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
python -X utf8 -m conversor.private_security --private-dir "$conversorPrivado" --investigar-heranca
python -X utf8 -m conversor.private_security --private-dir "$conversorPrivado"
python -X utf8 -m pytest -q tests/test_private_permissions.py tests/test_windows_acl_investigation.py tests/test_windows_acl_reader.py tests/test_acl_diagnostics.py tests/bbz/test_persistent_links.py
python -X utf8 -m pytest -q
python -X utf8 -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

O comando investigativo continua retornando 2 com `autoriza_acesso=false` e
`causa_confirmada=false`. Enviar somente seu JSON sanitizado e os resumos dos
testes; não enviar SDDL, caminhos resolvidos, nomes de pacote, chaves ou arquivos
privados. Não há executor Windows disponível neste ambiente: compilação/execução
da v3 e a suíte **completa Windows** ainda dependem dessa execução local.

Resultados locais da v3 (Linux): **2.106 aprovados, zero falhas, nove skips** na
suíte regular; **60 aprovados**, sem falhas/skips, nos históricos explícitos.
Total distinto: **2.166 aprovados**. Focados com Python 3.13.5, incluindo os testes
de vínculos persistentes: **202 aprovados, zero falhas, nove skips**. Todos os
skips desta execução são casos Windows nativos; permanece um warning preexistente
AnyIO/Starlette. O teste da chave permissiva passou aqui com a fixture corrigida,
mas seu resultado Windows precisa ser confirmado. O probe anterior compilou e
executou no Windows do responsável; a **v3 modificada** não foi compilada ou
executada nativamente neste ambiente. A revisão de privacidade não encontrou
dados reais ou credenciais nas mudanças. A main permanece fora desta publicação.
