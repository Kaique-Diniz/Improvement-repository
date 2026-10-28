# Vínculos documentais persistentes — revisão local

Branch `feature/vinculos-documentais-persistentes`, criada de `main` em
`d43ce983b7a8decb5d421b729c0dd3aedb5fcd86`. Nenhuma regra financeira, perfil
financeiro, leitor ou coluna do Excel foi alterado. Sem push/merge/deploy,
cobrança, exportação operacional ou integração externa.

## Funcionamento

O ABROLHOS mantém a validação de pertencimento ativada. O código de origem do
empreendimento e os prefixos de unidades não comprovam o destino 788.
O template continua opcional para leitura, comparação e novas evidências.
Uma unidade com vínculo persistente aprovado e verificável pode seguir o
diagnóstico A/B sem reenviar esse template. Unidade desconhecida, recusada,
revogada, conflitante ou que precise de revalidação continua retida.

A referência atual conciliada pode comprovar o escopo daquela análise, como
antes, e registra somente **candidatos** para uso futuro. Não os aprova.
Nome, contrato, produto/destino, bloco/unidade, vencimento e original precisam
cumprir a conciliação estrita existente. Não há lista de unidades reais no código.
Sem referência e sem aprovação persistente não há linhas liberadas por inferência.

O pertencimento é independente de titularidade/documentos. Conflitos válidos
retêm CPF/CNPJ e contatos, sem alterar seleção financeira. A retenção permanece
após reinício e sem template. Os bytes históricos verificados também são
reutilizados para confronto se o Cadastro for fornecido somente depois da
aprovação de pertencimento. Não se transfere CPF ou contato da referência.
Não existe botão para apagar essas pendências documentais; sua resolução exige
nova comprovação específica, fora desta autorização de pertencimento.

## Contratos e arquitetura

- `domain/document_links.py`: identidade de origem, candidato/vínculo, evidências,
  aprovação, pendência documental, eventos e snapshot tipados, contrato 1.0.
- `application/document_link_ports.py`: porta de repositório, sem dependência de
  JSON; PostgreSQL não foi implementado.
- `application/document_links.py`: preparação estrita, consulta e revalidação,
  confronto adicional e retenções, sem decidir regras financeiras.
- `adapters/document_links_json.py`: persistência privada, concorrência,
  autenticação dos registros por HMAC e evidências por conteúdo.
- `domain/document_scope.py`: novo escopo **1.1**, que aceita fontes históricas
  verificadas e aprovação válida. O contrato **1.0** mantém suas restrições e
  não vira cadastro aprovado automaticamente.
- `web/service.py`: consulta por unidade, preserva condições financeiras e aplica
  retenções separadas. Só o perfil que exige escopo usa o novo repositório.
- `web/app.py` e `static/vinculos.js`: consulta, candidatos e decisões individuais
  com a autenticação/sessão e proteção de origem já existentes.

A chave usa administradora + nome documental normalizado do empreendimento +
código administrativo normalizado + bloco e unidade **literais completos**.
O código original é preservado; 575/0575 são a mesma origem, mas A00001 não é A1,
e D/A00001 não é E/A00001. Não se usa `unidade_id`, recibo ou hash do novo arquivo
como chave. Origem e destino são campos separados; destinos incompatíveis não
podem ser aprovados simultaneamente. Uma mudança do nome financeiro ou perfil
de identificação suspende o aproveitamento e registra a fonte da divergência.

O cadastro guarda hashes/HMAC de conciliação e identidade, não nomes de devedores,
CPFs ou contatos em texto. Evidências originais necessárias à verificação são
preservadas privadamente, por SHA-256, sem alteração dos bytes. A aprovação
registra responsável declarado, sessão autenticada, data/hora com fuso,
fundamento e hash exato do candidato. Validade de revalidação é opcional e
explícita; não se presume vigência financeira. Endereço configurado é independente
do hash de identificação e não obriga nova aprovação do pertencimento.

## Armazenamento e integridade

Tudo fica em `--private-dir/vinculos_documentais/`:

| Arquivo/diretório | Finalidade |
|---|---|
| `registro.json` | Histórico completo e assinado, com snapshots versionados |
| `chave.bin` | Chave HMAC local; nunca compartilhar ou comitar |
| `cabecas/` | Checkpoints imutáveis assinados para detectar rollback/remoção parcial |
| `evidencias/` | Bytes originais por hash; sem caminhos externos fornecidos pelo cliente |
| `escrita.lock` | Bloqueio entre threads/processos, com revisão esperada |

JSON usa serialização determinística, gravação temporária, flush/fsync e troca
atômica. Eventos têm sequência, hash anterior e assinatura; aprovar requer
candidato e hash/revisão atuais. Revisão concorrente rejeita a ação. A escrita
do XLSX verifica e trava o snapshot consultado para impedir uso de revisão já
alterada durante a análise. O manifesto informa revisão/hash do cadastro,
origens das comprovações, contagens, pendências, novas evidências e contradições.
O download de um XLSX de análise anterior também exige que o cadastro não tenha
mudado; após uma decisão/revogação, é necessário reprocessar. Auditoria e arquivos
históricos são preservados, sem apagar evidências.

São recusados checkout Git, caminhos fora da área privada, symlinks em arquivos
ou ancestrais, hardlinks e reparse points/junctions Windows. Registro sem chave,
fonte com hash divergente, JSON adulterado, checkpoint ausente ou rollback não
reinicializam o cadastro. Os registros ficam retidos, com erro explícito.

Falha entre checkpoint e substituição do JSON também causa retenção. Não apagar
checkpoints para contorná-la: conservar os arquivos para revisão/recuperação.
Backups devem conter **a pasta inteira**, incluindo chave, evidências e checkpoints,
e permanecer privados. Git pull não modifica essa área nem o cadastro de endereços.

A raiz de confiança é o operador/conta local com acesso à pasta privada. HMAC
não substitui IAM, assinatura institucional nem uma âncora externa: quem controla
a chave e todos os arquivos pode reconstruir o acervo. No Windows, manter ACLs
restritas à conta autorizada; chmod não constitui isolamento NTFS suficiente.
O responsável informado é vinculado à sessão autenticada por chave local; não
foi introduzido um sistema de identidade individual externo.
Limites iniciais: 20 MiB por fonte e 32 MiB para o histórico JSON. A capacidade
não é ampliada silenciosamente; acervos maiores exigem revisão de armazenamento.
O contrato de origem e a porta são reutilizáveis; a obtenção do contexto nesta
entrega usa os metadados já validados do leitor BBZ. Outra família deverá
fornecer sua identidade de origem comprovada, sem mapeamento presumido.

## Inicialização pela interface no Windows

Após disponibilização autorizada desta branch, iniciar mantendo a pasta privada
atual, com Python 3.13:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m conversor.web --host 127.0.0.1 --port 8000 --private-dir "$env:LOCALAPPDATA\ConversorInadimplencia\privado"
```

1. Entre com a chave local já existente. Não copie JSON manualmente.
2. Envie o financeiro ABROLHOS (o arquivo chamado Cadastro.xlsx é financeiro),
   o Cadastro Geral PDF correspondente e o template histórico. Escolha a data
   de referência explícita e o modo A ou B.
3. Analise e abra **Conferir vínculos e candidatos**, ou **Vínculos de condomínios**.
   A referência estritamente conciliada gera candidatos, sem aprová-los.
4. Confira cada bloco/unidade, destino, SHA/localização das fontes e pendências.
   Informe responsável e fundamento. Marque a conferência daquela unidade e
   clique **Aprovar esta unidade**. Não há aprovação em massa.
5. Repita somente para os candidatos efetivamente conferidos. A aprovação do
   pertencimento não libera CPF/contatos retidos nem constitui atesto de fontes.
6. Remova o template pelo X e faça nova análise. Unidades aprovadas com fontes
   íntegras são reutilizadas; candidatas ainda não aprovadas permanecem retidas.
7. Compare A e B; reinicie o servidor com o mesmo `--private-dir` e repita.
   Endereço, CPF/contatos retidos, 30 colunas e parcelas devem continuar corretos.

Para mudanças de identidade ou evidências: analise os novos documentos e use
**Preparar candidatos da análise atual**, que revalida os bytes originais e a
revisão. É necessária nova decisão individual. Revogação/recusa não é anulada
automaticamente pela mesma referência; uma nova comprovação é exigida.
JSON antigo `escopo_destino.json` não é uma migração ou autorização válida.

Os endpoints de consulta, preparação e decisão são locais, autenticados e
protegidos contra origens cruzadas. Não são APIs de integração com CRM.

## Validação e limites da entrega

55 casos sintéticos novos: descoberta sem aprovação, aprovação individual,
reinício, novos recibos, ausência de template, origem com zeros, torres semelhantes,
mudanças de nome/perfil, conflitos de destino, referência contraditória, documento
conflitante, fontes íntegras, revogação, corrupção, rollback, caminhos proibidos,
concorrência, atomicidade, contrato/manifesto, modos A/B e API autenticada.
O navegador usa somente fixtures fictícias para testar aprovação e revogação.

Documentos reais estavam disponíveis no ambiente privado autorizado. A conferência
reconcilia 90 unidades/216 recibos/1.472 componentes e prepara **25 candidatos**;
65 unidades continuam inconclusivas. Com referência: A 103 dívidas; B mesmas
103 + 24 cadastros, XLSX idêntico ao baseline. Os dois conflitos conservam as nove
linhas históricas de evidência. Nenhuma aprovação humana real foi registrada.
Sem referência e sem aprovação, inclusive após preparar candidatos, as 90
unidades ficam retidas e a análise financeira permanece visível.

O cenário real **aprovado sem template** aguarda a aprovação humana local das
unidades; não foi simulado por identidades fictícias sobre dados reais. Sua
equivalência foi exercitada somente com fixtures sintéticas. Não se declara
homologação real desse cenário, nem homologação nativa Windows por testes Linux.

Regressões privadas dos seis anteriores comparam canônicos e XLSX byte a byte.
Os detalhes individuais permanecem fora do Git. Oito verificações de schemas
históricas são preservadas; há uma nova verificação para os quatro schemas
aditivos de vínculos/escopo. Comandos:

Resultado da entrega: **1.899 testes aprovados por ambiente** (1.839 regulares
e 60 históricos explícitos), incluindo 55 novos. Execuções em Linux com Python
3.12 e 3.13.5; os mesmos testes nas duas versões não são somados como novos casos.
Os 20 cenários privados dos seis anteriores preservam canônicos/XLSX idênticos.
Chromium validou aprovação sintética individual, A/B sem referência, conflito
retido, reinício, revogação e mobile, sem erros JavaScript.

```sh
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
python -m conversor.document_link_schemas --check
```

Pendências: aprovações humanas reais, revisão documental dos dois conflitos,
identidade das 65 unidades restantes e homologação manual Windows. Nenhuma
retenção foi eliminada nem regra ajustada para reproduzir o histórico.
