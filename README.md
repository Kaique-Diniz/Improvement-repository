# Conversor Inteligente de Inadimplência — MVP local

Aplicação web para **upload → reconhecimento → leitura → análise A/B → consulta → XLSX de teste**.
Reutiliza os leitores Habita/FL/Cadastro, o núcleo determinístico 4.2 e o escritor
universal existente. **Desenvolvimento e testes privados; não homologado para produção.**
A solicitação mais recente priorizou esse fluxo funcional sobre os incrementos
puramente documentais anteriores. Os registros abaixo dessa seção são históricos.

## Versão integrada — remoção de arquivos, hierarquia TREE e conferência VG

No TREE, **cota = unidade**, reunindo todos os seus boletos. Um boleto de original
R$ 0,01 ou com A/AJ/J veta o conjunto; somente depois se aplica o prazo individual
`>30` dias. A interface separa contagens, veto financeiro e retenção técnica,
com unidades expansíveis e identificação dos boletos causadores.

Validação privada: **112 cotas, 769 boletos, 63 selecionados em 15 contratos**,
coincidentes financeiramente com a referência. O bloqueio Habita/VG mantém zero
dívidas geradas. PLAZA preservado, inclusive os XLSX de teste byte a byte.
Os botões × e a codificação PLAZA estão incluídos na mesma linha de histórico,
sem conflito entre as correções. Conferência direta do PDF: o rótulo VG na página
149 repete o total geral reconciliado, mas diverge dos 120 boletos do próprio VG.
Não foi comprovado erro de extração que permita retirar essa retenção por escopo
documental ambíguo; o leitor e os valores permanecem inalterados.

**1.262 testes aprovados**, oito schemas; uploads reais A/B e regressão funcional
no Chromium, sem erros JavaScript. Nenhum push ou merge desta consolidação.
Veja o [comparativo, causas, evidências e limites](docs/CORRECAO_HIERARQUIA_TREE_MVP.md).
As [instruções de atualização Windows após publicação autorizada](docs/CORRECAO_HIERARQUIA_TREE_MVP.md#atualização-windows-após-autorização-de-publicação)
não pressupõem que os commits locais já estejam disponíveis na `main` do GitHub.

## Histórico — identificadores do template PLAZA

O [perfil de saída](src/conversor/web/perfis_saida.json) separa codificação de
integração da identidade canônica e das regras financeiras. Seleção explícita por
administradora + condomínio, versão, hash da configuração e evidência da referência
na auditoria. O mapa de torres é declarado: A=1, B=2, C=3, D=4, E=5, F=6, G=7;
não há conversão alfabética automática. Sem mapa, a prévia conserva identificação
provisória e informa a pendência, sem presumir compatibilidade operacional.

Na referência privada, 42 das 47 unidades puderam ser associadas independentemente
por número e nome integral ou dados financeiros, corroborando as sete torres sem
contradições. Cinco associações restantes usam esse mapa explícito. Os três
registros adicionais do modo B não estão na referência, que contém 43 cadastros.
Essa evidência valida a projeção de teste; não aprova importação operacional.

| Campo | Projeção anterior A/0091 | Projeção corrigida |
|---|---|---|
| NM_CEDENTE_CEDENTE | PLAZA MAYOR IPIRANGA | FL |
| CEDENTE | A/91 | 10091 |
| COMPLEMENTO | A/91 | UNI0091-BL1 |
| NM_CONTRATO_CEDENTE | A/91 | 10091 |
| PRODUTO_CEDENTE | PLAZA MAYOR IPIRANGA | PLAZA MAYOR |

Upload privado comum em 23/10/2026: modo A **69 dívidas**; B **69 dívidas + 46
cadastros**. As dívidas dos dois modos são iguais. Cinco identificadores coincidem
com a referência em 69/69 dívidas. Somente esses cinco campos mudaram: demais
células, canônico completo, decisões financeiras e configuração da régua preservados.
Comparação aceita datas textuais brasileiras/ISO na referência sem alterar vencimentos.

Nas 69 dívidas, as duas diferenças de CPF são uma perda de zero inicial na
referência e um conflito entre documentos válidos; não copiar nem resolver esse
conflito automaticamente. Nove diferenças de nomes em sete unidades correspondem
a múltiplos nomes no Cadastro, que contém os nomes da referência. As 37 diferenças
de endereço correspondem a duas unidades; não há evidência para substituir o
Cadastro atual pela referência. Há telefones adicionais em 47 linhas (46 com
referência vazia), e e-mails em 47 linhas com referência vazia. Conferidos nome,
documento e contatos das 50 unidades contra o Cadastro fornecido. No conjunto das
112 linhas da referência existem quatro perdas de zeros e dois conflitos entre
documentos válidos, preservados para revisão. Referência não alimenta o cadastro.

**1.243 testes aprovados**: 1.183 regulares e 60 explícitos, incluindo 24 novos
casos; oito verificações de schemas. Relatórios por unidade e fontes permanecem
privados. Sem push/merge desta correção, exportação operacional indisponível e
sistema não homologado para produção.

## Histórico — cadastro, parcelas e notificações

Com identidade inequívoca por administradora + condomínio + torre/bloco + unidade,
o Cadastro Geral é preferencial para NOME e contatos. Diferenças de nomes são
informativas, com ambas as fontes na auditoria privada, sem afirmar titularidade
jurídica. Documentos válidos conflitantes e ambiguidades estruturais seguem retidos.
Marcadores de notificação FL são separados somente no cabeçalho da unidade.

`NU_PARCELA` conta apenas dívidas incluídas, por contrato, em vencimento crescente
e desempate por identificador estável. Competência comprovada gera `COTA MM/AAAA - N`;
competência ausente conserva o identificador original. Linhas retidas não consomem
parcelas e aparecem sem numeração final na prévia. Y:AD cadastrais continuam vazias.

Rodada integrada com os dois PDFs PLAZA privados, upload comum sem catálogo,
referência **23/10/2026**. Fontes e os 115 boletos financeiros permaneceram intactos.

| Resultado | Antes, modo B | Agora, modo B | Agora, modo A |
|---|---:|---:|---:|
| Unidades / cotas | 50 / 115 | 50 / 115 | 50 / 115 |
| Elegíveis / não elegíveis pela régua | 69 / 46 | 69 / 46 | 69 / 46 |
| Cotas retidas | 82 | 0 | 0 |
| Dívidas no XLSX de teste | 0 | 69 | 69 |
| Cadastros adicionais | 33 | 46 | 0 |

Oito marcadores administrativos separados; nove diferenças de nomes restantes
viraram avisos informativos. Sequências conferidas em seis contratos com múltiplas
dívidas e entre prévia/XLSX. Os 205 registros históricos foram preservados: 17
motivos antigos de nomes reavaliados, sem remover os dois conflitos documentais.
Sem histórico, a análise se limita às fontes enviadas; não atesta ausência de
pendências anteriores. Testes sintéticos cobrem vencimentos repetidos, mudança de
ano, retenções, conflitos, ausência cadastral e exclusões TREE em A/B.

Regressão atual: **1.219 testes**, incluindo 33 novos casos e 60 testes explícitos
de homologação sintética; oito verificações de schemas. Exportação operacional
continua indisponível. Esta correção ainda aguarda publicação autorizada.

## Histórico — pausa para validação do ambiente real

O responsável autorizou o commit, push e merge da entrega anterior em 23/10/2026.
O desenvolvimento de novas funcionalidades fica temporariamente interrompido
para testar o ambiente real com o MVP existente. Essa publicação não aprova
planos, não remove bloqueios nem libera exportação operacional ou produção.
Documentos e resultados privados permanecem fora do Git.

## Iniciar backend e frontend

Python 3.12 ou superior e Git instalados. Na pasta do repositório:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-build-isolation --no-deps -e .
python -m conversor.web --private-dir /workspace/validacao-privada-fase3/mvp
```

No PowerShell, use `.venv\Scripts\Activate.ps1` e informe em `--private-dir`
uma pasta privada local **fora do checkout Git**. O caminho `/workspace/...`
corresponde ao Codex Cloud. Não publique a porta sem proteção de rede/TLS adequada;
o padrão é somente `127.0.0.1`.

Para atualizar pelo pacote de código no Windows, pare o servidor com Ctrl+C,
extraia o pacote em uma nova pasta e preserve a pasta privada anterior fora dela.
Nessa nova pasta, execute no PowerShell (Python 3.12 instalado):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m conversor.web --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
```

Substitua o último caminho pela pasta privada que já utiliza, se diferente.
Entre novamente e atualize a página com Ctrl+F5. Não é necessário cadastrar PDFs
em inventário nem copiar o catálogo privado do Codex para analisar novos arquivos.

Abra **http://127.0.0.1:8000**. Backend e frontend são servidos juntos; não é
necessário Node, npm ou outro servidor de frontend. O processo fica ativo até
Ctrl+C. Abra `acesso-local.txt`, dentro da pasta privada, em um editor local e
cole a chave na tela de acesso. Não envie essa chave para logs, commits ou tickets.
Ela é gerada automaticamente, arquivo 0600 em diretório 0700. Sessões duram oito
horas e isolam os resultados entre navegadores. Acesso/download sempre autenticados.

## Utilizar

1. Para uma primeira demonstração, clique **Experimentar com dados sintéticos**.
   O exemplo usa explicitamente 21/10/2026 e modo B se ainda não selecionados:
   duas unidades, três cotas, continuidade entre páginas, duas dívidas elegíveis
   e um cadastro adicional. Compare escolhendo o modo A e execute novamente.
2. Para arquivos próprios, selecione reconhecimento automático ou o condomínio,
   envie o PDF e, se necessário, o Cadastro Geral FL. Selecione a referência
   explícita e A/B. Pode anexar o Excel de referência; ele nunca alimenta a extração.
3. Clique **Analisar documentos**. Acompanhe a etapa real de processamento;
   filtre situação, unidade ou cota; abra **Detalhes** para composição, motivo,
   competência e páginas/linhas de origem. Auditoria técnica pode ser expandida.
4. **Baixar XLSX de teste** aparece somente havendo registros sem bloqueios.
   O arquivo usa aba `Dados`, 30 colunas na ordem original (inclusive o espaço
   físico histórico no cabeçalho AA), CPF/CNPJ textual com zeros e Y:AD vazias
   nos cadastros. Relatório de inconsistências é um JSON separado.
5. **Exportação operacional permanece indisponível**, inclusive por chamada direta
   à API. Nenhum arquivo de teste deve ser importado no easyCollector. Não há
   integração, envio ao CRM ou execução automática de cobrança.

Neste ambiente, os botões **Fontes já autorizadas** permitem usar os cinco
originais privados sem reenviá-los. Seus tamanhos/hashes, inventários históricos
(904 registros TREE e 205 FL) e os 132 vínculos financeiros técnicos anteriores
são conferidos privadamente, preservando todas as evidências. Arquivos com
integridade divergente não são processados por esse caminho.

O catálogo privado `fontes_autorizadas.json` é opcional. Upload novo sem histórico
anterior é analisado normalmente e recebe um único aviso informativo: isso limita
a conferência aos documentos enviados, sem atestar inexistência de pendências
anteriores. Um histórico conhecido que não puder ser validado continua bloqueante;
ocorrências anteriores carregadas não são descartadas. Não copie os originais ou
esse catálogo para o Git.

A interface separa os totais pela régua das retenções por leitura/cadastro e permite
conferir as 30 colunas das linhas previstas, inclusive retidas. A identificação da
conferência fica fora dessas 30 colunas. Linhas retidas não entram no XLSX de teste;
campos com conflito documental ficam indisponíveis até revisão.

## Limites explícitos do MVP

- Condições configuradas por condomínio em `src/conversor/web/perfis.json`, somente
  para diagnóstico: TREE centavo/A/AJ/J por cota (prioridade 1), prazo >30 (0);
  PLAZA apenas prazo >30 (0); vigência de negócio inclusiva 2026-09-10, fim aberto.
  A/B é universal, sem filtro judicial/garantidora e sem configuração numérica na UI.
- A autorização mais recente permite diagnóstico real, **não** cria aprovação ou
  atesto. O fluxo autorizativo anterior e seus contratos não foram relaxados.
  O novo caso de uso chama as funções **puras diagnósticas** do mesmo motor e
  grava `autoriza_cobranca=false`, `permite_exportacao_operacional=false`.
- Habita/VG retém todo o lote. Identidade estrutural ambígua e documentos
  válidos conflitantes continuam em revisão. Cadastro é por unidade: múltiplos
  nomes e um CPF/CNPJ não são conflito, nem atribuem o documento a cada nome.
  Documento ausente ou inválido fica vazio com aviso/alerta, sem bloqueio.
  Diferenças de nomes são informativas; contatos do Cadastro são preferenciais
  quando a unidade estiver inequivocamente vinculada, sem inferir titularidade.
  A interface separa elegibilidade financeira, contatos, pendências documentais
  e retenções da prévia. Reclassificações justificadas conservam o histórico.
- Os identificadores de origem são usados nos campos de cedente/contrato/dívida
  **do arquivo de teste**. Codificação operacional desses campos e homologação
  integral easyCollector permanecem pendentes. Competência ausente não é inferida.
- Comparação verifica vínculo inequívoco e valor original; separa seleção de regras,
  dados e representação. Os vínculos técnicos históricos só são usados para os
  hashes exatos das fontes/referências. Sem vínculo, retorna não avaliável; não
  infere torre numérica a partir de letra nem usa nomes para escolher titulares.
- Armazenamento fica em `--private-dir/processamentos/<id>/`: PDFs recebidos,
  referência, canônico, auditoria e eventual XLSX. Nada disso é estático/público.
  Não há limpeza automática nem histórico de sessões na UI após reiniciar o
  servidor; retenção e exclusão dos resultados devem ser administradas localmente.
- Dois trabalhadores e até quatro trabalhos em curso; limite de 20 MB por arquivo.
  OCR, formatos adicionais, multiusuário de produção e importação no CRM não fazem
  parte desta entrega. A sessão única local não substitui um IAM de produção.
- Ainda pendem validações formais da aplicabilidade anterior à fonte de 20/10/2026
  e da redação TREE unidade/cota, atestos e aprovação dos planos. Nenhum bloqueio
  é removido por diagnóstico ou por geração do arquivo de teste.

## Verificar o fluxo

```bash
python -m pytest -q tests/web/test_mvp.py
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

Smoke test opcional no navegador, somente com dados fictícios (servidor já ativo):

```bash
python -m pip install playwright==1.56.0
python scripts/verificar_interface_mvp.py --chave-arquivo /workspace/validacao-privada-fase3/mvp/acesso-local.txt --chromium /usr/bin/chromium
```

O teste confere login, filtro, detalhes, download, bloqueio operacional e layout
móvel; grava capturas sintéticas em `/tmp`, sem registrar a chave. Se não houver
Chromium instalado, instale um navegador compatível no seu ambiente.

## Histórico do diagnóstico anterior — antes da correção consolidada

Referência do diagnóstico real: **2026-10-22**, modo B, selecionados explicitamente.

| Conjunto | Leitura | Confronto financeiro | Retenções e arquivo de teste |
|---|---|---|---|
| TREE / Habita | 112 unidades, 769 cotas; valores/componentes/vencimentos preservados | 63 valores originais coincidentes com os vínculos técnicos da referência | Todas as 769 cotas retidas por bloqueio do lote; sem XLSX |
| PLAZA / FL + Cadastro | 50 unidades, 115 cotas; cadastro complementar sem incluir as outras unidades | 69 valores originais coincidentes | Após correção cadastral: 17 unidades em revisão (82 cotas retidas); 33 cotas não elegíveis nas demais; modo B gera **33 linhas exclusivamente cadastrais**, Y:AD vazias |

As condições financeiras puras indicam 138 cotas TREE e 69 FL potencialmente
selecionáveis nessa referência, **antes dos bloqueios**. Nenhuma é liberada como
dívida operacional. A divergência entre seleção e referência não autoriza forçar
os dados ou alterar regras. A referência TREE tem uma anotação extra em AE,
registrada como formatação; o XLSX de saída continua estritamente A:AD.
A comparação cadastral/formatos e a ausência de vínculos de algumas linhas são
ressalvas explícitas; as 132 correspondências monetárias não homologam o Excel.

Correção cadastral conferida em 23/10/2026 com a mesma referência: as retenções
passaram de 34 para 17 unidades e de 99 para 82 cotas. Preservados os 205 registros
históricos, inclusive os dois registros de conflito documental, e todos os 115
boletos. As 17 unidades restantes têm divergências entre fontes, sem substituição
automática de nomes; não são bloqueadas apenas pela presença de múltiplos nomes.

Upload comum, sem catálogo, conferido com os dois PDFs PLAZA em 23/10/2026, modo B:
50 unidades, 115 cotas; 69 elegíveis pela régua e 46 não elegíveis. Retidas 82 cotas
de 17 unidades por divergências entre fontes; zero bloqueios por ausência de histórico.
Prévia com 69 dívidas retidas, 13 cadastros retidos e 33 cadastros sem retenção.
Validado também no navegador; não constitui teste nativo do Windows.

Regressão: **1.186 testes aprovados**, 1.126 regulares (incluindo 21 testes
HTTP/integração e 33 regressões de cadastro por unidade) + 60 explícitos de homologação sintética; oito
verificações de schemas passaram. Smoke test Chromium passou em login, filtro,
detalhes, download, bloqueio operacional e viewport móvel, sem erro JavaScript.
Os originais, históricos, aprovações e planos anteriores não foram modificados.
A publicação desta entrega foi autorizada posteriormente, conforme a pausa acima.

---

## Histórico de desenvolvimento e decisões anteriores

# Dossiê de transferência ao Codex — Conversor Inteligente de Inadimplência

**Verificação técnica final de aprovações:** [tabela única TREE/PLAZA e pendências humanas](docs/preparacao_4_3B_2B/VERIFICACAO_FINAL_E_DECISOES_HUMANAS.md).
Prioridade 1 > 0 demonstrada em testes sintéticos puros, sem aprovar a proposta.
Somente metadados de fontes reais foram consultados. Vigência, hash aplicável
da régua, atestos e aprovação formal continuam pendentes; sem simulação real.

**Etapa atual: preparação de aprovações para o 4.3B.2B, somente documental.**
O responsável aceitou tecnicamente o 4.3B.2A, sujeito à revisão posterior do
código. Consulte as [fichas consolidadas, prioridades propostas, vigência,
cinco atestos e checklist](docs/preparacao_4_3B_2B/PRONTIDAO_E_CHECKLIST.md).
Nenhuma decisão humana preenchida, plano real aprovado/ativado ou simulação real
executada nesta preparação. Fase 5 não iniciada; sem homologação de produção.

**Status:** Fases 1 e 2 implementadas; Fase 3 tecnicamente encerrada por autorização do responsável, com ressalvas e bloqueios operacionais preservados. Sem homologação para produção.
**Última fase concluída tecnicamente:** Fase 3 — Leitores. **458 testes aprovados**, 884 boletos reconciliados e 132 correspondências financeiras. Veja o [aceite técnico e decisão de encerramento](docs/ACEITE_TECNICO_FASE3.md).
**Fase 4 — incremento 4.3B.2A implementado exclusivamente com dados sintéticos:** integração entre inventário reconciliado, aprovação de planos, motor existente, decisões A/B e persistência auditável, sem XLSX operacional. Veja [implementação, demonstração e limites](docs/INCREMENTO_4_3B_2A_INTEGRACAO_SINTETICA.md). O [4.3B.1](docs/INCREMENTO_4_3B_1_TREE_SINTETICO.md) foi aceito tecnicamente e registrado em commit próprio. Atestos humanos e aprovação dos planos reais continuam pendentes. Branch `feature/fase-4-motor-cobranca`; sem início do 4.3B.2B ou da Fase 5.
**Arquitetura da Fase 4:** [modelo JSON, decisões e incrementos](docs/ARQUITETURA_MOTOR_FASE4.md). O laboratório sintético anterior não constitui motor geral aprovado nem homologação do Excel.
**Correção do 4.3A:** aprovada tecnicamente pelo responsável; colisões FL reconciliadas com mapa completo do legado e assinatura técnica privada. Bloqueios operacionais e atesto humano pendente preservados. Veja [causa comprovada, contratos e revalidação FL/Habita](docs/CORRECAO_IDENTIDADES_AUDITORIA_4_3A.md).
**Regressão naquela preparação:** 1.132 testes aprovados (1.111 anteriores + 21 novos puros de prioridade 1/0), com schemas históricos preservados. São 1.072 testes regulares e 60 explícitos; oito geradores de schemas conferidos. Não representam aprovação das prioridades ou homologação de planos reais.

**Requisitos de negócio revisados, somente documentação:** consulte a
[matriz atual dos oito IDs](docs/MATRIZ_NEGOCIO_PRELIMINAR_8_REGRAS.md), as
[respostas Q01–Q26](docs/DECISOES_PENDENTES_HOMOLOGACAO_REGRAS.md) e a
[proposta não executável](examples/fase4/proposta_configuracao_4_3B.revisada.json).
Centavo exclui só cota/componentes; prazo de 30 é estrito em dias corridos;
judicial/garantidora não criam filtros adicionais; cadastro universal A/B é
escolha do processamento. A implementação sintética está no 4.3B.1; integração
real, planos formais e atestos continuam pendentes. Exemplos históricos anteriores
não representam essas novas decisões; veja
[compatibilidade e limites](docs/ATUALIZACAO_REQUISITOS_EXTRAJUDICIAL_FASE4_3B.md).

**Decisão TREE confirmada:** centavo, A, AJ ou J excluem somente a cota inteira e
componentes, independentemente do vencimento; outras cotas seguem avaliação
normal. `Valor` é referência do boleto; validar seu mapeamento e os campos próprios
dos apontamentos antes da configuração técnica. Dia 31 satisfaz o prazo TREE,
sem anular exclusões/bloqueios. Atualização documental, sem plano aprovado,
assinado ou ativado e sem execução de regras reais.

**Validação técnica preparatória TREE:** o
[mapeamento dos valores e apontamentos](docs/MAPEAMENTO_TECNICO_TREE_PREPARATORIO_4_3B.md)
foi conferido no PDF privado: original integral em `Boleto.composicao.total_original`,
encargos separados e A/AJ/J associados por campo próprio ao boleto. Nenhuma regra
real foi executada; bloqueio Habita/VG mantido. Novos testes usam somente dados
inventados. Atestos, planos formais e autorização para o 4.3B.2 continuam pendentes;
a autorização posterior do 4.3B.1 limita-se a testes sintéticos.

**Apontamentos e fichas TREE:** [cobertura técnica exaustiva](docs/COBERTURA_APONTAMENTOS_FICHAS_TREE_4_3B.md)
concluída nos 769 boletos: 628 campos vazios validados, 141 preenchidos, zero
inconclusivos, incluindo 33 continuidades. Cinco fichas individuais e
[resumo de atestos](docs/RESUMO_ATESTOS_DECISOES_4_3B.md) preparados para decisão;
sem cobertura operacional emitida, atesto, assinatura ou ativação de plano real.
**Correções dos layouts reais:** [resultado antes/depois, testes e pendências](docs/CORRECOES_LEITORES_REAIS_FASE3.md). Os bloqueios permanecem obrigatórios.
**Atualização documental:** CPF/CNPJ válidos na coluna literal `CPF`, como texto; compatibilidade confirmada pelo responsável no CRM easyCollector. Conflitos documentais exigem revisão humana. Veja [contratos, auditoria e testes](docs/DOCUMENTOS_CPF_CNPJ.md). A homologação integral permanece pendente.
**Atualização:** 22/10/2026 (America/Sao_Paulo).
**Idioma do projeto:** português brasileiro.

## Objetivo
Converter relatórios de inadimplência (PDF, XLSX e arquivos complementares) de múltiplas administradoras em um único modelo Excel com 30 colunas, aplicando a régua de cobrança de cada condomínio, com detecção automática de layout, alertas, bloqueios de segurança e auditoria.

## O que compõe este pacote

- `01_PLANO_ETAPAS.md`: fases, dependências, entregáveis e pontos de controle.
- `02_ESPECIFICACAO_PRODUTO.md`: requisitos e comportamento do produto.
- `03_MODELO_DADOS_JSON.md`: entidades, relacionamentos e persistência inicial.
- `04_DICIONARIO_TEMPLATE.md`: contrato de saída, 30 campos e tratamento de linhas.
- `05_PENDENCIAS_TESTES_ACEITE.md`: decisões em aberto, cenários de testes e condições de liberação.
- `06_PROMPT_INICIAL_CODEX.md`: instruções prontas para iniciar a primeira tarefa.
- `AGENTS.md`: guia de implementação, segurança e testes para uso no repositório.
- `FONTES_E_IMPORTACAO.md`: documentos de origem e processo recomendado para entregá-los com segurança.
- `config_exemplos/*.json`: exemplos **não operacionais** de configuração. Não contém CPF, senhas ou clientes reais.

## Como usar

1. Leia `01_PLANO_ETAPAS.md`, depois `02_ESPECIFICACAO_PRODUTO.md` e `05_PENDENCIAS_TESTES_ACEITE.md`.
2. Coloque os documentos `.md`, `AGENTS.md` e `config_exemplos/` em um repositório **privado** para o Codex.
3. Não faça commit de relatórios reais, da régua completa ou de cadastros com dados pessoais/credenciais.
4. Disponibilize arquivos reais ao ambiente autorizado de teste por um caminho seguro e privado, somente quando necessário.
5. Envie a tarefa do arquivo `06_PROMPT_INICIAL_CODEX.md` ao Codex, **implementando apenas a Fase 1**.
6. Revise testes e entregas de cada fase antes de pedir a próxima.

Este pacote substitui a necessidade de colar o histórico integral de conversa no prompt. O PDF com a conversa do Claude é uma referência adicional, não a fonte normativa quando divergir destas decisões posteriores.

## Executar a Fase 1 localmente

Requer Python 3.12 ou superior. Na raiz do checkout, em Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation --editable .
.venv/bin/python -m pytest -q
.venv/bin/python -m conversor.schemas --check
```

No PowerShell/Windows, crie o venv com `py -3.12 -m venv .venv` e substitua
`.venv/bin/python` por `.venv\Scripts\python.exe` nos comandos. Os testes desta
entrega foram executados em Linux/Python 3.12; Windows ainda não foi homologado.

Exemplo local, sem dados pessoais e sem qualquer conversão/cobrança:

```bash
.venv/bin/python -m conversor.cli --dados ./dados/demo init
.venv/bin/python -m conversor.cli --dados ./dados/demo importar examples/fase1/catalogo.sintetico.json --revisao 1
.venv/bin/python -m conversor.cli --dados ./dados/demo validar
.venv/bin/python -m conversor.cli --dados ./dados/demo listar condominios
```

`init` cria a revisão 1; importação acima cria a revisão 2. Repetir `init` retorna
`CONFLITO_DE_REVISAO`, sem sobrescrever arquivos. Para atualizar um registro, usar
`gravar <colecao> <arquivo.json> --revisao <revisao-atual>`; para remover um registro
sem referências, `excluir <colecao> <id> --revisao <revisao-atual>`. Veja `--help`.
Relações novas e circulares devem entrar em conjunto por `importar`, em catálogo
completo consistente. A CLI retorna status 0 em sucesso e 2 em erros de domínio/I/O,
sem imprimir dados pessoais. Consultas Python retornam objetos tipados via
`Configuracao`, sem expô-los automaticamente no terminal.

Use o diretório `dados/` (ignorado pelo Git) ou um local privado fora do checkout.
Não force commit de fontes reais. O exemplo em `examples/fase1/` é inteiramente
sintético e todas as regras/perfis/formatos estão em rascunho. Os exemplos originais
em `config_exemplos/` foram preservados como material conceitual não operacional;
não são importados nem aprovados automaticamente.

## Arquitetura, contratos e limites

- [Arquitetura e funcionamento do JSON](docs/ARQUITETURA_FASE1.md).
- [Decisões técnicas, testes e pontos de homologação](docs/DECISOES_E_HOMOLOGACAO.md).
- [Apoio local com Ruflo](docs/RUFLO.md).
- [JSON Schemas versionados](schemas/1.0/). Regenerar com `python -m conversor.schemas`.

Os JSON Schemas descrevem a estrutura; os modelos Python também validam somatórios,
referências, vigências, aprovações e relações. A validação de prontidão do catálogo
é feita com `validar`, não só com validação estrutural de JSON Schema.

O contrato de saída tem 30 posições, CPF em branco com alerta quando ausente ou
inválido e linhas cadastrais com Y:AD vazias. Preserva o espaço final físico da
coluna AA por configuração até homologação. A entrega original da Fase 1 não gera
XLSX, aplica régua, reconhece PDFs ou enriquece com Cadastro Geral; os acréscimos
posteriores estão descritos nas seções abaixo.
Retenção, ACL, aprovação real e importação no sistema final permanecem pendentes.

As etapas seguintes exigem aprovação explícita após revisão de cada entrega.

## Fase 2 — reconhecimento automático

O comando `reconhecer` detecta PDF com texto, PDF sem texto/rasterizado/misto,
XLSX e CSV UTF-8. Classifica assinaturas e identifica administradora/condomínio
por campos explícitos. Não extrai boletos, não aplica régua e não gera Excel.
Desconhecidos, ambiguidades e configurações não homologadas bloqueiam o avanço.

Após instalar/atualizar o ambiente pelos comandos acima, crie a demonstração:

```bash
.venv/bin/python examples/fase2/gerar_demo.py --saida dados/demo_fase2
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio init
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio importar dados/demo_fase2/catalogo.json --revisao 1
.venv/bin/python -m conversor.cli --dados dados/demo_fase2/repositorio reconhecer dados/demo_fase2/habita_tree.pdf --arquivo-id fonte_sintetica --assinaturas dados/demo_fase2/assinaturas.json --data-ref 2026-10-21
```

A demonstração retorna **status 3**, resultado bloqueante com
`FORMATO_NAO_HOMOLOGADO` e `ASSINATURAS_NAO_HOMOLOGADAS`. Esse é o comportamento
esperado: os exemplos são rascunhos e não podem aprovar formatos reais.
O gerador cria arquivos novos sem sobrescrever diretório já utilizado; use outro
diretório para uma nova demonstração. A data é ilustrativa e sempre deve ser
fornecida explicitamente. A suíte testa caminhos positivos com aprovações artificiais
restritas a fixtures temporárias; não existe etapa de confirmação interativa.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

O reconhecimento retorna status 0 quando apto para próxima etapa, 3 quando bloqueado
e 2 para erros de configuração/acesso. O JSON público contém IDs opacos, hashes,
versões, cobertura das assinaturas, localização de evidências e códigos de bloqueio;
nunca trechos brutos, nomes de arquivos/pessoas ou valores financeiros extraídos.
`pronto_para_proxima_etapa` é prontidão de configuração/reconhecimento, não de cobrança.

- [Arquitetura, decisões e limites da Fase 2](docs/RECONHECIMENTO_FASE2.md).
- [Arquivos sanitizados necessários e como comparar gabaritos](tests/fixtures/sanitized/README.md).
- [Assinaturas sintéticas Habita e FL, não homologadas](examples/fase2/assinaturas.sinteticas.json).

A pasta `tests/fixtures/sanitized/` está preparada e ignora amostras locais no Git.
O comparador de contrato canônico prepara a validação dos futuros leitores sem
implementá-los nesta fase. Amostras representativas e gabaritos revisados são
necessários antes de homologar Habita/TREE ou FL/Plaza. O laboratório abaixo não
aprova as fases operacionais seguintes nem altera os bloqueios de reconhecimento.

## Laboratório do pacote sintético fornecido

O pacote está em `tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor/`,
ignorado pelo Git e preservado integralmente. Não acompanha um clone novo;
reponha a cópia autorizada nesse caminho para executar a integração. A suíte
regular gera seus próprios PDFs sintéticos pequenos e não depende do anexo.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py
.venv/bin/python -m conversor.laboratorio \
  --pacote tests/fixtures/sanitized/Homologacao_Sanitizada_Conversor \
  --saida dados/homologacao_pacote_nova_execucao
```

Use um diretório de saída novo ou vazio a cada execução. O laboratório escreve
dois XLSX com 30 colunas, os modelos antes/depois do Cadastro, decisões, ocorrências,
hashes de preservação das fixtures e relatórios JSON/Markdown. O terminal mostra
somente agregados. A configuração é `config_exemplos/laboratorio_pacote.json`.

Status do comando: **0** sem diferenças de conteúdo; **1** diferenças no Excel;
**2** bloqueios, diferenças financeiras/de controle ou fixtures alteradas. Neste
pacote o resultado esperado é **1**: valores e decisões conferem, mas há **17 células
de contato divergentes**. Quatro datas equivalentes têm representação diferente
(data nativa versus texto ISO) e são listadas separadamente. Testes verdes verificam
também a detecção dessas divergências; não significam equivalência integral ao Excel.

As duas políticas confirmadas pelo usuário — cadastro por unidade com boleto
adiado e prioridade do Cadastro em titular divergente com alerta/auditoria — valem
**somente neste laboratório**. Não existem OCR, LLM ou Ruflo no cálculo financeiro.
O Ruflo é utilizado apenas para acompanhamento local do trabalho.

Veja o [relatório verificável e próximos ajustes](docs/RELATORIO_PACOTE_SINTETICO.md).

A [revisão individual das 21 células](docs/REVISAO_DIVERGENCIAS_SINTETICAS.md)
confirmou 17 inconsistências do gabarito e quatro datas equivalentes em tipos
diferentes, sem falhas comprovadas de extração/normalização. Para executar a
regressão da revisão: `python -m pytest -q tests/homologacao/revisao_suite.py`.
A [preparação para revisão no GitHub](docs/ENVIO_GITHUB.md) registra a branch,
o escopo autorizado de publicação e o bloqueio de acesso à API de Pull Requests.
