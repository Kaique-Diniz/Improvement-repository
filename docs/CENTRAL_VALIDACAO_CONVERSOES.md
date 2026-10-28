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
