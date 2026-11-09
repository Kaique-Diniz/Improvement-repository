# BPQ-01 — Terraço Beach Parque / HABITACIONAL

Entrega local para auditoria, sem commit, push, PR ou merge. Branch
`feat/terraco-beach-parque-habitacional-efemero`, worktree
`/workspace/Improvement-beach-parque`, HEAD/base
`2b7d6347d23e0ea79e16216c10042b5a20674344`.
Não inclui VEC-01, ITJ-01 nem a infraestrutura Windows experimental.

## Identidade, fontes e regra provisória

Perfil `terraco_beach_parque`, família própria `habitacional_beach`,
administradora `habitacional`, condomínio `condominio_terraco_beach_parque`.
Os leitores exigem o código interno 3075 e o nome interno completo. O número
2811 do nome de arquivo não comprova identidade, equivalência nem destino.
Nenhum código numérico de destino é criado.

Os três SHA-256 fornecidos foram conferidos sobre os bytes reais. Hash conhecido
somente permite reconhecimento automático depois de validar a gramática e a
identidade. Fontes novas compatíveis exigem confirmação explícita; a escolha
não substitui validação estrutural. O cadastro é validado independentemente.
O leitor financeiro BBZ/OMA/HABITA não processa este perfil: somente a sondagem
estrutural e utilitários técnicos compatíveis são compartilhados.

A linha 570 da régua atualizada é evidência do prazo extrajudicial de 30 dias,
judicial de 60 e não envio de cartas. Somente essa linha foi consultada;
credenciais e informações operacionais não foram copiadas. A seleção autorizada
é provisória e estrita: `(data_ref - vencimento).days > 30`. Inclusividade e
vigência operacional continuam pendentes. Não se implementa cobrança judicial,
contato, reenvio ou cartas; prefixos A/J não são decisões empresariais.

## Financeiro e reconciliação privada

`beach_parque_xlsx.py` exige a aba única `relatorio (4)`, período válido,
identidade, unidades, cabeçalhos de 12 colunas e todos os fechamentos.
Usa Decimal e compara seis colunas monetárias em componentes → recibo → unidade
→ condomínio. Nenhuma linha desconhecida, fórmula, recibo incompleto ou
fechamento divergente é ignorado. Até componente zerado exige conta/histórico.

Cada ocorrência documental gera um boleto próprio. Conta repetida continua
sendo componente distinto; código de recibo repetido não apaga ocorrência.
O ID inclui a unidade, o token integral e a linha de abertura. O identificador
técnico contém a linha preenchida com zeros antes do código, para o desempate
local; espaços do prefixo são representados por ponto no campo canônico Id.
O recibo literal fica em evidência e na prévia. Nenhum hash real é normalizado.

Emissão numérica fica bruta, sem virar data ou competência. Conta, histórico,
moeda, seis valores, formatos, linha, ordem e SHA ficam na evidência temporária.
O valor exportado é exclusivamente G do fechamento do recibo, original total;
principal, multa, correção, juros e atualizado não o substituem.

| Indicador conferido | Resultado |
| --- | ---: |
| Unidades financeiras | 183: A 69, B 56, C 57, especial 0 uma |
| Recibos | 1.010 |
| Componentes | 7.365 |
| Original integral | R$ 741.289,05 |
| Prefixos | 629 numéricos, 315 A, 66 J |
| Divergências de fechamento (recibo/unidade/geral) | 0 / 0 / 0 |
| Elegíveis em 16/10/2026 | 850 em 111 unidades |
| Original elegível | R$ 603.477,71 |
| Fora da seleção | 160 em 159 unidades; R$ 137.811,34 |
| Vencimento dos não elegíveis | 10/10/2026 |
| Elegíveis em 06/11/2026 | 850 |
| Elegíveis em 10/11/2026 | 1.010 |
| Multiconjunto unidade/vencimento/original/multiplicidade contra template | zero diferenças |
| Modo A efetivo | 850 linhas financeiras |
| Modo B efetivo | 1.009: 850 financeiras + 159 cadastrais |

Os modos foram executados pelo serviço real, com cadastro, em diretórios
TemporaryDirectory separados; os canônicos, auditorias, manifestos e resultados
privados foram removidos ao concluir cada execução. As fontes recebidas para
homologação continuam fora do Git e não foram alteradas.

## Descrições, parcelas e codificação

O primeiro componente principal fornece o histórico literal. Os 15 padrões
literais de `domain/beach_parque.py` justificam mês/ano de vencimento apenas
como apresentação: 61 linhas; as outras 789 mantêm o histórico sem adição.
Nenhum desses 15 padrões ocorre com tratamento misto na referência. Não há
competência presumida nem extensão automática da lista a textos semelhantes.
Os 850 conteúdos-base coincidem com o template.

Parcelas consideram somente elegíveis por unidade, vencimento crescente e
identificador estável com ordem documental de abertura. Dois grupos de empate
entre elegíveis, quatro linhas, explicam duas posições históricas diferentes;
848 parcelas coincidem e duas permanecem diferentes. Isso também altera o
sufixo de parcela em duas descrições, sem alterar conteúdo-base ou valores.
Não foi alterada a ordenação universal nem a de outro perfil. Há um terceiro
grupo de empate no universo integral, fora dessa comparação histórica.

A codificação documental valida letra e cinco dígitos: A/ILHABE, B/ANG,
C/BUZ e somente o especial 0/DANPRI. Exemplos públicos: A00001 →
`BLILHABE-UNIA00001`, B00001 → `BLANG-UNIB00001`, C00206 →
`BLBUZ-UNIC00206`, DANPRI → `BL00-UNIDANPRI`.
CEDENTE e contrato acrescentam `-TERRAÇO BEACH PARQUE`; complemento não.
Não se convertem unidades para inteiros nem se admitem aliases arbitrários.
Mapeamento inconsistente e colisão bloqueiam; originais ficam no canônico.

## Cadastro e matriz conservadora

PDF conferido: 230 páginas, emissão 22/01/2025, 622 registros distintos:
207 por torre A/B/C e um especial 0. Foram reunidas 206 continuações, com
cliente/nome/unidade e posição da continuação compatíveis. Todas as 183 unidades
financeiras e as 111 elegíveis foram encontradas. Há 22 unidades alugadas,
seis entre as elegíveis. A geometria própria permite o cabeçalho documental
sem CNPJ do empreendimento; não infere documento ausente nem altera a exigência
de outros leitores.

A ficha temporária mantém papéis distintos de titular, pagador, locatário,
unidade e correspondência/observações, com coordenadas, página, linha e SHA.
Dados do pagador não se tornam dados pessoais do titular, inclusive DANPRI.
Contatos de unidade, locatário e texto livre não são promovidos ao titular.
A pessoa canônica associável contém exclusivamente o titular identificado.

Política `beach_parque_titular_nominal_documento_valido_A1@1`: aplica A1 sem
alterar suas regras; exige unidade exata, nome concordante, documento válido,
sem multiplicidade ou conflito, antes de transferir documentos **e contatos**.
O marcador E não bloqueia automaticamente razão social comprovada com CNPJ e
designador empresarial. CPF/CNPJ malformado permanece na evidência original;
não é atribuído nem interrompe toda a conversão. Telefones completos podem ter
DDD vazio; não há preenchimento ou captura parcial de sequências maiores.
A concordância com cadastro de 2025 não certifica titularidade atual em 2026.

| Motivo exclusivo por lançamento | Unidades no universo integral | Total | Elegíveis | Não elegíveis |
| --- | ---: | ---: | ---: | ---: |
| Nome divergente (código A1 PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO) | 13 | 65 | 55 | 10 |
| Multiplicidade sem vínculo individual inequívoco (código A1 PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO) | 1 | 17 | 16 | 1 |
| Titular sem documento válido (BPQ_TITULAR_SEM_DOCUMENTO_VALIDO_ASSOCIACAO_RETIDA) | 2 | 33 | 32 | 1 |
| Total retido, sem exclusão financeira | 16 | 115 | 103 | 12 |

Não há ausência de cadastro, documentos inválidos ou conflitos fiscais válidos
observados nesta amostra. As 13 divergências nominais incluem oito unidades
entre elegíveis, afetando 55 dívidas. As duas unidades elegíveis sem documento
do titular afetam 32 dívidas; o preenchimento histórico do template não prova
associação. Os 16 lançamentos elegíveis adicionais por multiplicidade mantêm
nomes financeiros e exigem prova individual, sem escolher o primeiro documento.

A comparação dos 850 documentos de saída com o template, recompondo zeros de
CPFs numéricos apenas para comparação, tem 747 iguais, 103 preenchimentos
históricos retidos e zero documentos preenchidos diferentes. O template não é
fonte para completar documento ou contato.

Restrições do cadastro completo: nove bloqueios de reenvio, duas restrições a
carta e um registro de litígio/suspensão de contato. Os alertas por lançamento
só alcançam sua unidade; o resumo identifica o universo completo do cadastro.
Cada alerta preserva a origem do campo/cabeçalho e a evidência privada; a UI
mostra mensagem de revisão, sem texto jurídico identificável ou ação de contato.
Não exclui dívida por observação histórica. Há ainda 59 fichas com e-mail não
segmentado e 101 com telefone não segmentado: campos originais ficam na
ficha temporária; não se recuperam contatos a partir de texto ambíguo.

## Comparação das 30 colunas

Comparação por multiconjunto financeiro e ocorrência; datas são normalizadas
para comparação, dinheiro para Decimal centesimal, CPF Excel numérico recompõe
zeros sem transformar texto arbitrário em documento. Não altera dados de saída.
Não foi configurado endereço administrativo nessa execução privada. Por isso,
as seis colunas de endereço ficam vazias; o endereço padronizado histórico não
é copiado do template nem do cabeçalho. Configuração explícita de sessão,
com proveniência, foi validada nos testes HTTP e Chromium.

| Coluna | Cabeçalho atual | Tipo de saída | Iguais ao histórico | Diferentes |
| --- | --- | --- | ---: | ---: |
| 1 | `NM_CEDENTE_CEDENTE` | texto (vazio permitido) | 850 | 0 |
| 2 | `CEDENTE` | texto (vazio permitido) | 850 | 0 |
| 3 | `CPF` | texto (vazio permitido) | 747 | 103 |
| 4 | `NOME` | texto (vazio permitido) | 850 | 0 |
| 5 | `ENDERECO` | texto (vazio permitido) | 0 | 850 |
| 6 | `NUMERO` | texto (vazio permitido) | 0 | 850 |
| 7 | `COMPLEMENTO` | texto (vazio permitido) | 850 | 0 |
| 8 | `CEP` | texto (vazio permitido) | 0 | 850 |
| 9 | `BAIRRO` | texto (vazio permitido) | 0 | 850 |
| 10 | `CIDADE` | texto (vazio permitido) | 0 | 850 |
| 11 | `UF` | texto (vazio permitido) | 0 | 850 |
| 12 | `DDD1` | texto (vazio permitido) | 789 | 61 |
| 13 | `FONE1` | texto (vazio permitido) | 730 | 120 |
| 14 | `DDD2` | texto (vazio permitido) | 726 | 124 |
| 15 | `FONE2` | texto (vazio permitido) | 725 | 125 |
| 16 | `DDD3` | texto (vazio permitido) | 845 | 5 |
| 17 | `FONE3` | texto (vazio permitido) | 845 | 5 |
| 18 | `DDD4` | texto (vazio permitido) | 850 | 0 |
| 19 | `FONE4` | texto (vazio permitido) | 850 | 0 |
| 20 | `DDD5` | texto (vazio permitido) | 850 | 0 |
| 21 | `FONE5` | texto (vazio permitido) | 850 | 0 |
| 22 | `EMAIL1` | texto (vazio permitido) | 799 | 51 |
| 23 | `EMAIL2` | texto (vazio permitido) | 770 | 80 |
| 24 | `EMAIL3` | texto (vazio permitido) | 823 | 27 |
| 25 | `NM_CONTRATO_CEDENTE` | texto (vazio permitido) | 850 | 0 |
| 26 | `PRODUTO_CEDENTE` | texto (vazio permitido) | 850 | 0 |
| 27 | `NM_DIVIDA_CEDENTE` | texto (vazio permitido) | 848 | 2 |
| 28 | `NU_PARCELA` | inteiro | 848 | 2 |
| 29 | `VENCIMENTO` | data Excel | 850 | 0 |
| 30 | `VL_PARCELA` | Decimal → número Excel | 850 | 0 |

AA atual é `NM_DIVIDA_CEDENTE`, sem o espaço final do cabeçalho histórico.
Contatos têm diferenças além das retenções por causa de papel, segmentação e
ordem documental; não foram modificados para imitar o template. Documentos,
nomes, identificadores, descrição-base e dinheiro têm matrizes separadas.

## Navegador, segurança e descarte

Chromium real, exclusivamente com documentos fictícios: CLI em 127.0.0.1 sem
senha manual, sessão técnica HttpOnly, reconhecimento automático do hash de
teste vinculado apenas no processo de homologação, fonte nova com confirmação,
PDF opcional, endereço em memória, torres/unidades e prévia de 30 colunas.
A fixture produziu quatro financeiras no A e quatro mais uma cadastral no B;
duas associações retidas e uma sem cadastro, sem apagar dívidas. Downloads
isolados, recusa de sessão alheia, Host/Origin/CSRF, bloqueio operacional,
expiração sem tráfego e limpeza de intermediários/shutdown foram confirmados.
As imagens de evidência contêm somente dados fictícios e ficam fora do Git.

Multipart continua em memória, com limites anteriores a spill. Intermediários
privados temporários são descartados após processamento; Excel e prévia ficam
em cache isolado por sessão por até 15 minutos, ou até encerrar os downloads
ativos. O coletor roda em inatividade. Não se promete exclusão enquanto resposta
ou worker ainda utilizar os dados. Nenhum histórico pessoal permanente é aberto.
Perfis, gramáticas, máscaras documentais e regras são configuração do software.

## Validação local final

- 59 testes Beach Parque aprovados.
- 413 testes direcionados/de regressão aprovados, incluindo Passaredo, Forest
  Hill, Parque Santa Mônica, interface clássica e fluxo efêmero.
- Suíte Linux/Python 3.12.14: 2.271 aprovados, zero falhas, erros e skips;
  um warning preexistente Starlette/AnyIO de depreciação.
- Chromium real: modos A/B, download, confirmação, endereço e descarte aprovados.
- pip check, compileall, sintaxe JavaScript e whitespace aprovados.
- Novos arquivos também são incluídos na inspeção de whitespace e no patch;
  staging permanece vazio. Sem dados pessoais/credenciais/fontes binárias.
- Nenhuma implementação ou teste anterior foi desabilitado, removido ou relaxado.

## Pendências e limites

- Revisão externa e execução Windows real; Linux/Chromium não homologam Windows.
- Aprovação da inclusividade e vigência operacional dos 30 dias, atualidade
  cadastral, prova das associações retidas e tratamento humano das restrições.
- Novas descrições fora da lista preservam histórico literal; não recebem mês
  automaticamente. Mudanças de gramática exigem nova validação documental.
- As duas posições históricas de parcela permanecem distintas por desempate
  técnico estável, sem ajuste financeiro ou reordenação global.
- Permanecem os limites documentados do MVP: orçamento de cache não é limite
  global de RSS; dois workers não constituem sandbox de parser nem prazo de CPU.
- Cancelamento aguarda o worker terminar e limpar; resultados sem destinatário
  podem expirar em memória. Shutdown normal aguarda workers sem prazo máximo.
- SIGKILL/queda de energia podem deixar resíduos temporários. Não há varredura
  segura de resíduos de execução anterior na inicialização. Não se certificam
  apagamento forense, swap, dumps ou cópias salvas pelo navegador/usuário.
- A integração com outras novas administradoras, CRM, exportação operacional,
  comunicação, cobrança e infraestrutura ACL permanece fora desta entrega.

## Execução local

Com Python 3.12 e dependências `.[test,web]`, executar no worktree:

```bash
PYTHONPATH=src /workspace/Improvement-repository/.venv/bin/python -m conversor.web --port 8038
```

Abrir `http://127.0.0.1:8038`, enviar a fonte financeira, confirmar apenas quando
compatível, fornecer cadastro opcional e endereço administrativo autorizado,
selecionar data/modo, conferir pendências e baixar o diagnóstico. O servidor
permanece local; não é autorização operacional. Aguardar auditoria externa.
