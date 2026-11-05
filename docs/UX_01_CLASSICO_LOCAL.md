# UX-01 — interface clássica local, sem senha manual

Implementação sobre `e479d2362df85ee196ed0b0ba472c6fd56278e06`, branch `feat/mvp-classico-local-sem-login`, worktree `/workspace/Improvement-mvp-classico`. A frente Forest Hill não foi incorporada. Publicação autorizada para auditoria externa, sem merge ou aprovação operacional.

## Executar e usar

```sh
python -m conversor.web
```

Abrir `http://127.0.0.1:8000`. Não há prompt, chave para copiar ou requisito de `CONVERSOR_CHAVE_LOCAL`. A porta pode ser alterada com `--port`; o modo padrão não aceita `--host` e sempre escuta em `127.0.0.1`. A variável antiga é ignorada pelo inicializador padrão. O navegador recebe uma sessão técnica automática, individual por contexto de navegador. Abas do mesmo contexto compartilham essa sessão; outro navegador/contexto recebe uma sessão distinta.

O visual usa a identidade e o CSS clássicos, com cliente novo para a API efêmera. Não há chamadas ao servidor persistente legado. O antigo modo explícito de diagnóstico legado não faz parte deste fluxo. A factory Python conserva `acesso=...` opcional para compatibilidade da API anterior e suas regressões; o inicializador e a interface novos usam a sessão automática e não oferecem esse login.

1. Selecionar o relatório; o sistema verifica estrutura e identidade.
2. Fonte homologada exata é reconhecida automaticamente. Arquivo novo com layout compartilhado exige confirmação rápida, sem pressupor condomínio.
3. Conferir endereço e torres/unidades, se necessário, vinculados ao condomínio identificado.
4. Escolher data de referência e modo A/B; analisar.
5. Filtrar boletos, buscar unidades, conferir componentes, origem e prévia das 30 colunas.
6. Baixar o Excel diagnóstico ou descartar. Downloads e prévias em andamento preservam recursos até terminar ou falhar.

Nenhum arquivo é automaticamente enviado a cobrança, CRM ou exportação operacional.

## Reconhecimento seguro

O SHA-256 é calculado sobre os bytes reais. O Passaredo homologado pode ser reconhecido em `auto` após validar XLSX, aba, colunas e fechamento. As 11 colunas compartilhadas e o nome/código do arquivo não bastam. Uma escolha explícita conflitante com uma identidade conhecida é rejeitada. Mais de um perfil vinculado aos mesmos bytes também é conflito.

Novos perfis precisam de registro de identidade e despacho de leitor próprios. Um hash de perfil futuro não implementado não cai no leitor Passaredo. Forest Hill permanece na sua frente isolada. Sem identidade conhecida, a sugestão de Passaredo exige confirmação humana somente para diagnóstico; não afirma homologação nem autorização operacional.

A revisão UX-01 substitui a exigência anterior de seleção manual para os bytes homologados. Não altera a regra Passaredo > 60 dias nem as validações/retencões A1. O teste anterior foi atualizado apenas nessa expectativa, mantendo a rejeição de layout desconhecido e acrescentando conflitos, fontes distintas e estrutura inválida com hash registrado.

## APIs efêmeras

| API | Contrato |
| --- | --- |
| `GET /` | Interface clássica e cookie de sessão técnica, se necessário |
| `GET /api/sessao` | Token CSRF da sessão válida; o cliente administra automaticamente |
| `DELETE /api/sessao` | Encerra a sessão e solicita descarte dos seus resultados/metadados |
| `GET /api/config` | Perfis e limites do fluxo, sem fontes financeiras persistentes |
| `POST /api/identificar` | Multipart: inadimplência e condomínio opcional; identidade confirmada ou HTTP 409 com sugestão |
| `GET /api/contextos/{id}/configuracao` | Metadados administrativos apenas do proprietário da sessão |
| `PUT /api/contextos/{id}/configuracao` | Endereço de seis campos, propostas de mapeamento e revisão esperada |
| `POST /api/conversoes` | Upload efêmero existente; aceita contexto identificado para conferir hash/perfil |
| `POST /api/exemplo` | Exemplo inteiramente sintético, modos A/B |
| `GET /api/conversoes/{id}/detalhes` | Decisões, componentes, origem, codificação e prévia, somente na janela temporária |
| `GET /api/conversoes/{id}/excel` | Excel diagnóstico, sessão proprietária e CSRF; consumo solicita descarte |
| `DELETE /api/conversoes/{id}` | Solicita descarte; informa se há resposta ativa |
| `GET /api/conversoes/{id}/operacional.xlsx` | Continua bloqueado |

Não existem novos endpoints de aprovação operacional, histórico financeiro ou associações pessoais persistentes. O cliente novo usa `/assets/classico.*` e o CSS clássico versionado; não usa `app.js`/`vinculos.js` legados para operações de API.

## Endereço, torres e identidade

A configuração fica em memória, por sessão e por perfil efetivamente identificado. Um contexto contém identidade, digest e metadados de unidades, sem nome de responsável, CPF, contatos, boletos ou bytes da planilha. O contexto é aleatório, expira em 15 minutos e pertence à sessão. Reutilizá-lo com outros bytes ou perfil é rejeitado.

Endereço contém somente logradouro, número, CEP, bairro, cidade e UF. Não aceita complemento individual. A mudança é versionada por revisão otimista e tem origem administrativa na auditoria. O endereço só é aplicado quando administradora e condomínio do processamento coincidem; complemento e endereço original permanecem preservados. A interface permite salvar e recarregar. Uma análise já concluída não muda retroativamente: precisa ser refeita.

Configurações administrativas da sessão podem ser reutilizadas em novas conversões do mesmo perfil, até encerrar/expirar a sessão. Não há persistência entre reinícios nesta entrega. Se futuramente for necessária, requer contrato explícito de configuração local fora do Git, sem conteúdo documental/financeiro. Nenhum banco legado foi reativado.

A consulta mostra a codificação documental existente, unidades pendentes e propostas conflitantes. Proposta igual ao mapa já documentado é comprovada; divergente do mapa é conflitante; sem prova é pendente. Propostas pendentes/conflitantes não alteram a codificação nem a seleção. Comprovar um formato não comprova pertencimento ou titularidade. Novos vínculos não documentados exigem revisão da prova antes de integrar configuração confiável; a interface não transforma digitação em autorização. Evidências fornecidas na conversão continuam obrigatórias para casos como ABROLHOS.

## Sessão e proteção local

O cookie é host-only, HttpOnly e SameSite=Strict. Secure é usado em HTTPS; a URL local solicitada usa HTTP e o servidor fica restrito ao loopback. Requisições da interface recebem proteção por sessão, Host, Origin e token CSRF automático; nenhum segredo precisa ser digitado ou copiado. O token não vai em URL.

Requisições de outro site/origem ou de outra porta são bloqueadas, inclusive GETs sensíveis. Escritas exigem Origin exata e CSRF. Download também exige CSRF e é obtido pelo cliente via fetch, sem link desprotegido. CSP permanece sem unsafe-eval e sem scripts inline, com proteção contra embedding. Sem CORS para sites externos e sem cache nas respostas. Erros de validação são sanitizados, sem ecoar o conteúdo enviado.

O limite de arquivo continua 20 MiB, pedido total 61 MiB, duas operações simultâneas e até oito resultados. Excel até 10 MiB. O orçamento global de resultados continua 32 MiB, agora contabilizando também os bytes da prévia. Metadados de contextos têm teto separado de 8 MiB e até 32 contextos; sessões continuam limitadas a 32 e oito horas. Isso não é limite global de RSS do processo.

## Retenção e limites

Uploads multipart continuam em memória, sem spill. Processamentos usam diretórios temporários isolados e descartam intermediários antes de publicar o resultado. Excel e detalhes ficam apenas em memória, até 15 minutos ou descarte. O janitor continua operando durante inatividade. Logout/reinício normal elimina sessões e configurações. Respostas ativas conservam referências necessárias e as liberam em finally, inclusive em erro. A interface distingue solicitação de descarte de eliminação já confirmada.

Limitações herdadas: encerramento forçado pode deixar resíduos; não existe recolhimento automático por prefixo sem comprovar propriedade. Workers iniciados concluem após cancelamento, com resultado sujeito ao TTL. Não há garantia de apagamento forense nem de remoção de cópias baixadas/cacheadas pelo navegador. Não há limite total de RSS. A tela pagina renderização de boletos/prévia, mas mantém a resposta da análise em memória durante sua janela autorizada.

A configuração administrativa é somente de sessão. Não se cria prova para torre desconhecida nem nova política financeira. Não há integração Windows experimental. A publicação destina-se à revisão externa; a aprovação técnica e operacional permanece pendente.
