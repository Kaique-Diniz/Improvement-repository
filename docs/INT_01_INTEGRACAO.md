# INT-01 — Forest Hill, UX-01 e Passaredo A1

Integração técnica com publicação controlada autorizada para auditoria externa, sem merge ou autorização operacional.

## Bases e aplicação

- Base UX-01: `7053bd5b17a38f075c740497348b67f0b0f591d0`.
- Forest Hill aplicado: `2ffa236e9ff35eeef8f8ca17621493273c55ddb9`.
- Ancestral Passaredo A1: `e479d2362df85ee196ed0b0ba472c6fd56278e06`.
- Nova branch: `feat/integracao-forest-hill-ux01`.
- Novo worktree: `/workspace/Improvement-integracao-forest-ux01`.

O Forest Hill foi aplicado com `cherry-pick --no-commit`. Houve um conflito textual em `service.py`, no reconhecimento. O despacho foi resolvido manualmente para combinar hash, perfil e gramática. A conciliação automática de `ephemeral.py` foi revisada para preservar a sessão/CSRF da UX-01 e os resumos Forest Hill. A aplicação inicial foi encerrada sem commit e o staging limpo sem alterar bytes dos arquivos, com HEAD em `7053bd5`. A publicação autorizada acrescenta um único commit de integração nessa nova branch. As branches originais permanecem intactas.

## Reconhecimento e cadastro

`readers/auto_gestao_identity.py` registra explicitamente cada gramática e callback de leitura. Estrutura e composição tabulares são verificadas antes de escolher candidatos. Passaredo aceita a forma numérica compatível com a codificação documentada de quatro dígitos significativos, preservando zeros e texto original; Forest Hill conserva sua gramática AV.P/RUA. Nenhum dado financeiro é normalizado para obter compatibilidade.

- Hash homologado exato só identifica o perfil se a estrutura e a gramática correspondem.
- Seleção conflitante com identidade conhecida é rejeitada.
- Documento novo exige confirmação mesmo se houver só um candidato compatível.
- Múltiplos candidatos são apresentados sem selecionar o primeiro; nenhum perfil compatível significa rejeição.
- Perfil futuro sem leitor registrado falha de forma fechada.
- Nome/código de arquivo não comprova identidade.

O cadastro passa por validação independente e só pode usar um perfil compatível com o financeiro comprovado ou confirmado. Cadastro numérico Passaredo não é aplicado a Forest Hill; cadastro AV.P/RUA não é aplicado ao Passaredo. Hash conhecido do outro perfil também provoca rejeição. A política A1 continua exigindo nome/unidade e evidência documental concordantes para atribuir documentos e contatos. Layout/unidade isolados não comprovam titularidade.

## Interface e backend preservados

A interface clássica mantém sessão técnica automática, sem senha, em `127.0.0.1:8000`. Configurações de endereço e propostas de torres ficam somente em memória na sessão, por perfil identificado. Formatos pendentes/conflitantes não alteram codificação ou pertencimento.

Métricas, avisos de documentos rejeitados e painel de pendências cadastrais usam as chaves do perfil efetivo: `cadastro_passaredo`/`revisao_cadastral_passaredo` ou `cadastro_forest_hill`/`revisao_cadastral_forest_hill`. O painel é esvaziado ao descartar, expirar ou receber o download. Filtros, detalhes, componentes/proveniência, prévia das 30 colunas e modos A/B continuam disponíveis.

Continuam Host/Origin/CSRF, cookie HttpOnly/SameSite, IDs aleatórios e isolamento de sessões. Upload, quotas de processamento e cache de 32 MiB incluindo prévia permanecem inalterados. Intermediários são descartados antes da resposta; Excel/prévia duram até 15 minutos ou liberação das respostas ativas. Não há histórico, associações pessoais persistentes ou exportação operacional.

## Financeiro preservado

- Passaredo: atraso em dias corridos **>60**, independente de DIAS e da disponibilidade cadastral.
- Forest Hill: hipótese autorizada **>30**, com exatamente 30 dias fora até confirmação específica. Prazo judicial não é filtro adicional.
- VALOR, vencimentos, identificadores, duplicidades, parcelas elegíveis e composições continuam sob os componentes aprovados.
- As descrições originais ficam no canônico; apresentação Forest Hill mantém sua regra específica, sem nova competência ou cálculo.
- Saída universal: 30 colunas, AA literal `NM_DIVIDA_CEDENTE` sem espaço final.
- As dez diferenças de parcela/rótulo Forest Hill em empates de vencimento permanecem para revisão específica. Não se mudou a ordenação global para imitar o histórico.

## Executar

Com o ambiente instalado a partir deste worktree:

```sh
python -m conversor.web
```

No ambiente compartilhado de desenvolvimento, sem alterar o pacote instalado das outras branches:

```sh
cd /workspace/Improvement-integracao-forest-ux01
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web
```

Abrir `http://127.0.0.1:8000`. Enviar relatório, conferir identificação/confirmação, cadastro opcional, data de referência e modo A/B. Nenhum token ou senha precisa ser copiado. Instalação inicial e limites gerais estão em `MVP_EFEMERO_LOCAL.md`.

## Validação local

A suíte integrada efetivamente executada passou com **2.140 aprovados**, zero falhas/erros/skips e um warning de depreciação Starlette/AnyIO. Os 282 direcionados incluem: Passaredo A1 96, Forest Hill 51, UX-01 26, novos INT-01 32, backend efêmero 30 e regressão BBZ Edifício Win 47. Esses números foram extraídos da execução integrada, não somados como substituto da execução.

Chromium real, com dados inteiramente fictícios: ambos os perfis em auto com binding SHA de fixture confiável; ambos novos exigindo confirmação compatível; A/B; endereço por perfil; torres pendentes; métricas e revisão cadastral; filtros, detalhes, prévia, download, origem cruzada, isolamento, expiração e descarte passaram. Os bindings de teste não alteram a configuração de produção. Capturas e relatórios anonimizados são entregues separadamente.

Reconciliação privada autorizada, referência 07/10/2026, modo A, com e sem cadastro:

| Perfil | Linhas elegíveis | Unidades elegíveis | Divergências unidade/vencimento/original |
| --- | ---: | ---: | ---: |
| Passaredo | 2.154 | 126 | 0 |
| Forest Hill | 1.625 | 98 | 0 |

Boletos e IDs coincidiram com os adapters isolados, hashes reais foram preservados e não houve exclusão financeira por cadastro. Passaredo manteve 266 retenções no lote total, sendo 250 entre elegíveis. Forest Hill manteve 178 no total, sendo 177 entre elegíveis; as dez diferenças conhecidas de apresentação em quatro unidades permanecem. Todas as fontes ficaram inalteradas e as áreas temporárias foram removidas. Nenhum dado pessoal ou valor financeiro privado é listado aqui.

Windows real **não executado**: o ambiente disponível é Linux. Testes sintéticos/mocks não são certificação Windows. A infraestrutura ACL experimental não foi incorporada.

## Pendências e limites

Continuam: confirmação do limite exato de 30 dias/vigência Forest Hill; diferenças históricas de apresentação e cadastro; configurações administrativas sem persistência entre reinícios; novos mapas dependentes de prova; ausência de teto global de RSS; resíduos possíveis após encerramento forçado sem recolhimento automático; workers que concluem após cancelamento; cópias do navegador e apagamento forense fora das garantias. Respostas ativas precisam liberar seus recursos antes do descarte definitivo.

A publicação ocorre exclusivamente em `origin/feat/integracao-forest-hill-ux01`, para auditoria externa e testes locais controlados. Main, PRs #6/#7 e branches originais permanecem inalterados. Não há merge nem criação de PR; a integração definitiva aguarda nova revisão.
