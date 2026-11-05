# MVP de conversão efêmera local

A versão consolidada combina, por merge sem conflitos, a entrega XLSX `eb26e0ff0ce0988522bb2b67a41ab694a0fe9a75` e o MVP `71e0b58547ffdebee9f7883852473bd75a283e06`. Ambos os commits originais são ancestrais da branch `feat/mvp-efemero-consolidado`, em worktree próprio, sobre a main original `04f29ff5fc9124b988bd611d3d1b8d7224ae874f`. Não contém a infraestrutura experimental P0.2-D nem modifica a branch/PR #6.

## Executar

Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,web]'
python -m conversor.web --port 8000
```

No PowerShell, ative com `.\.venv\Scripts\Activate.ps1`; os comandos Python são os mesmos. A validação desta entrega foi em Linux, incluindo Chromium; a execução Windows desta frente ainda requer validação própria.

Defina uma chave de 12 a 128 caracteres na entrada oculta do terminal. Ela permanece na memória, não é exibida nem gravada pelo aplicativo. Para automação local, pode-se fornecer `CONVERSOR_CHAVE_LOCAL` pelo ambiente, sem colocar seu valor em logs ou argumentos. Abra `http://127.0.0.1:8000`, autentique-se e envie o relatório. Há um exemplo inteiramente sintético na própria tela. Não existe opção de host público no inicializador padrão.

`python -m conversor.web.ephemeral` é uma entrada equivalente. A aplicação antiga continua importável pelos testes; seu inicializador só pode ser usado explicitamente com `--legado-persistente` e não faz parte do contrato efêmero. Não use esse modo para a nova entrega.

## Fluxo e evidências

- Inadimplência: PDF textual ou XLSX reconhecido pelos leitores existentes, até 20 MiB.
- Cadastro PDF/XLSX e referência XLSX opcionais: evidência somente desta conversão, até 20 MiB cada. O sondador rejeita conteúdo inválido/protegido, macros, links externos e limites estruturais nos três papéis antes de converter.
- Campos A/B, data e condomínio usam o contrato existente. O reconhecimento não usa nome de arquivo como comprovação.
- Leitores, elegibilidade, valores, vencimentos, composições, IDs, hashes de proveniência e escritor de 30 colunas permanecem os mesmos. A única alteração no serviço é a leitura UTF-8 explícita da configuração versionada; também foi corrigido o erro sintático `finally2026:` da main para permitir importar o leitor XLSX.
- Não são carregados inventários/fontes anteriores, cadastro de endereços do usuário ou repositório de vínculos persistentes. Não há criação de novos vínculos operacionais. Quando as regras exigem referência documental (por exemplo, ABROLHOS), ela precisa ser fornecida novamente; sem prova, o bloqueio original é preservado.
- O Excel permanece diagnóstico: `DIAGNOSTICO_NAO_IMPORTAR.xlsx`. Cobrança, CRM e exportação operacional continuam bloqueados. Planos/HMAC/recibos não são criados ou modificados.

## Retenção e descarte

1. Upload multipart fica em memória. O parser limita cada arquivo antes de escrever um chunk e mantém o spool acima desse limite: não há rollover dos uploads para disco. Erro, multipart incompleto e desconexão fecham os buffers de parsing.
2. Cada conversão recebe uma `TemporaryDirectory` isolada dentro da área temporária do processo, criada pelo SO. O serviço existente grava ali Excel, canônicos e auditorias intermediárias; não grava os PDFs/XLSX recebidos. Não foi feita uma reestruturação do núcleo para retirar todas essas escritas.
3. Ao concluir ou falhar a conversão, o diretório da conversão é removido antes de disponibilizar o resultado. Se a limpeza falhar, não há resposta de sucesso; o diretório próprio fica pendente para novas tentativas periódicas e no encerramento. Não se declara descarte concluído diante de erro de limpeza.
4. O Excel e um resumo reduzido ficam na memória; no perfil Passaredo, também a lista de revisão de responsáveis divergentes, restrita à sessão e ao mesmo prazo: máximo de oito resultados e 32 MiB de Excel em cache; cada Excel tem teto de 10 MiB. O resultado expira 15 minutos após concluir, sem extensão por consulta. A limpeza periódica ocorre aproximadamente a cada segundo, além das verificações a cada acesso.
5. Download autenticado adquire uma referência ativa ao Excel; expiração, descarte ou logout impedem novos acessos, mas preservam essa referência até a resposta terminar/falhar. O envio tem limite de 60 segundos. Após servir o download, o resultado não fica disponível novamente. Downloads já ativos precisam liberar suas referências antes da remoção do cache.
6. Logout, descarte explícito ou expiração removem resultados sem respostas ativas. A sessão expira em oito horas. O servidor tem duas conversões simultâneas e não aceita uma fila ilimitada de uploads.
7. Encerramento normal aguarda os workers, limpa sessões/resultados e remove a área temporária. Não apaga arquivos externos nem diretórios de outras execuções. Cancelar a requisição após iniciar o worker não interrompe o parser/conversor: ele termina, limpa seu temporário e pode deixar um resultado sem destinatário no cache até o TTL. Não há prazo máximo de processamento; isso é uma limitação pendente, inclusive para o tempo de encerramento normal.

Não se promete apagamento forense, exclusão de swap/dumps, memória do interpretador, buffers do servidor/SO, cópias do navegador ou downloads salvos pelo usuário. SIGKILL, queda de energia e falhas persistentes do filesystem podem deixar resíduos no diretório temporário; a próxima inicialização não identifica nem recolhe esses resíduos. Essa exigência permanece pendente de implementação e validação: será necessário comprovar a propriedade dos diretórios antes de qualquer remoção, sem varredura destrutiva baseada apenas em prefixo. O isolamento da nova execução não significa que resíduos anteriores tenham sido descartados. Arquivos temporários têm o isolamento nativo do SO; não foi incorporado o verificador/adapter Windows experimental nem certificada uma DACL Windows operacional.

## Segurança e limites

Autenticação local por cookie HttpOnly/SameSite=Strict, comparação constante da chave, limite de tentativas, isolamento por sessão, recusa de Host remoto/origem cruzada, CSP, no-store e erros sanitizados. O servidor não registra corpos, conteúdo financeiro, nomes de arquivos enviados ou chaves, e inicia com access log desativado. A entrada no fluxo efêmero não abre documentos privados reais automaticamente.

O processamento e os parsers rodam no processo local, com limites já existentes de documentos e dois workers. Não há isolamento de processo para um parser comprometido nem prazo máximo de CPU de conversão. Os limites de RAM do cache não são limite de RSS da aplicação ou do tamanho transitório das estruturas financeiras. Não há suporte operacional à exposição na rede; manter o bind local.

Os testes legados de persistência continuam executados sem remoção/skip. Eles validam o contrato antigo nas fábricas antigas; isso não habilita seus endpoints no novo aplicativo. A substituição de contrato é explícita: referências/endereços/revisões de outra conversão não são reaproveitados no fluxo efêmero. As regressões novas testam o bloqueio por ausência de evidência, em vez de simular comprovação ausente.

## Próxima etapa

Depois da revisão deste fluxo, expandir uma administradora por vez: assinatura/identidade documental, leitor quando necessário e fixtures sintéticas representativas. Reutilizar leitores e regras somente com compatibilidade comprovada. Não iniciar expansão nesta entrega nem inferir novas regras financeiras.

## Verificações para a publicação de auditoria

As regressões sintéticas incluem expiração pelo coletor sem tráfego HTTP, dois downloads ativos com liberação após cancelamento, cancelamento durante parsing multipart, worker em andamento após cancelamento de requisição, reinício normal sem reutilização de sessão/resultados e orçamento global do cache. O cenário de resíduo de execução anterior registra expressamente que ele permanece intocado; não certifica recuperação após SIGKILL. Chromium real deve validar autenticação, upload, demonstração, reconhecimento, download de 30 colunas e descarte normal.

A publicação é para auditoria. Permanecem pendentes o limite global de memória do processo, a identificação e o tratamento seguro dos resíduos de encerramento forçado, o isolamento/prazo dos parsers e a interrupção controlada de conversões canceladas. Os limites por upload, workers e cache reduzem a concorrência e a retenção, mas não satisfazem essas garantias por si só.

### Registro histórico: publicação isolada do MVP (`71e0b58`)

- Python 3.12: 30 regressões do fluxo efêmero aprovadas; suíte completa com 1.933 aprovados, uma falha, zero erros/skips e um warning de depreciação do Starlette/AnyIO.
- A falha é `tests/bbz/test_edificio_win.py::test_idempotencia_de_canonico_e_xlsx`, na comparação das decisões de duas fontes sintetizadas separadamente. Ela permanecia na branch isolada do MVP; a correção que reutiliza os mesmos bytes foi publicada independentemente em `fix/xlsx-idempotencia-entradas`. A suíte completa daquela entrega isolada **não estava verde**. A consolidação abaixo inclui essa correção.
- Chromium real: autenticação, upload PDF/cadastro/referência, reconhecimento FL/PLAZA, botão de demonstração, download de 30 colunas com valores sintéticos esperados e recusa de segundo download aprovados. A área temporária ficou sem arquivos após converter e foi removida no SIGTERM normal.
- `compileall`, sintaxe JavaScript, `pip check`, whitespace e revisão de escopo são verificados antes do commit. Nenhum arquivo financeiro real, credencial operacional ou fixture binária é incluído.

## Consolidação funcional — validação local

- A integração preserva os dois commits aprovados e não exigiu resolver conflitos. `xlsx_reader.py` e `test_edificio_win.py` mantêm exatamente a entrega XLSX; os demais módulos de produção mantêm exatamente a entrega MVP. Não há mudanças adicionais em regras, formatos, hashes, identificadores, bloqueios ou ACLs.
- Testes direcionados: **77 aprovados**. Suíte Linux/Python 3.12 completa: **1.935 aprovados**, zero falhas, erros ou skips; um warning de depreciação do Starlette/AnyIO.
- Em três processos Python separados, com intervalo entre execuções, passaram os três cenários de cada execução: mesmos bytes preservam decisões/canônicos/Excel, fontes distintas mantêm seus hashes SHA-256 reais, e o endpoint efêmero produz Excel idêntico para entradas idênticas. Nenhum hash é normalizado.
- Chromium real confirmou autenticação, upload sintético PDF/cadastro/referência, reconhecimento FL/PLAZA, 30 colunas e valores esperados, download, exemplo sintético e descarte normal. A área temporária ficou vazia após converter e foi removida no SIGTERM.
- `compileall`, `pip check`, sintaxe JavaScript, YAML do workflow e whitespace foram verificados localmente. Nenhum teste legado foi removido, ignorado ou relaxado.

O workflow herdado da main configurava Python 3.11 e instalava somente pytest/openpyxl, incompatível com o requisito Python >=3.12 do projeto. Nesta branch funcional, ele usa `windows-latest`, Python 3.12, venv exclusivo, instalação `.[test,web]`, `pip check`, `compileall`, três repetições de idempotência em processos separados e a suíte completa. Permissões: `contents: read`. O push nesta branch também dispara a validação; o gatilho de PR para main foi preservado. Não foram transportados os módulos experimentais Windows nem modificados testes para esconder diferenças nativas.

**Windows permanece pendente de evidência real nesta revisão local.** A validação Linux e o YAML não certificam a execução Windows. O acesso da CLI à API GitHub retornou `Forbidden`; a interface web acessível não possui sessão autenticada. A abertura do PR draft e a coleta do resultado dependem de acesso disponível, sem mudança de rede ou autenticação interativa.

### Pendências que continuam abertas

- Limite global de memória/RSS e isolamento/prazo máximo de parsers: os limites atuais abrangem uploads, concorrência e cache, não todas as alocações do processo.
- Resíduos após SIGKILL/queda de energia: não são identificados nem recolhidos automaticamente na próxima inicialização. A limpeza normal e as tentativas de limpeza de diretórios próprios não comprovam recuperação de uma execução anterior.
- Cancelamento após iniciar um worker: o worker termina e limpa seu temporário; um resultado sem destinatário pode permanecer em memória até o TTL. O encerramento normal espera os workers, sem limite máximo de processamento.
- Cópias do navegador, swap e apagamento forense permanecem fora da garantia de descarte.
- Compatibilidade Windows deste conjunto ainda depende da execução real do workflow. Nenhuma nova frente ACL foi iniciada.

A próxima prioridade funcional é uma nova administradora por vez, mediante identificação do formato e exemplos representativos sintéticos. Reconhecimento/leitor serão reutilizados somente com compatibilidade documental comprovada, sem criar regras financeiras. Esta consolidação não acrescenta camadas de segurança nem inicia uma administradora sem evidência do formato.

## Perfil PASSAREDO / AUTO GESTÃO

O novo perfil usa inadimplência XLSX e cadastro complementar XLSX opcional. Toda fonte sem identidade interna exige seleção explícita do perfil, mesmo com hash conhecido; a seleção não dispensa a validação estrutural. Nome de arquivo não comprova condomínio ou código de destino. [Contrato do perfil e critérios das retenções](PASSAREDO.md). As divergências de responsáveis ficam disponíveis para revisão transitória na tela, sem transferência de CPF/contatos por mera coincidência de unidade. Nenhuma nova operação de cobrança foi habilitada.
