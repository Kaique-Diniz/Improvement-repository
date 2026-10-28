# BBZ — NOVA REBOUÇAS: extensão diagnóstica

## Dependência e escopo

Branch `feature/bbz-nova-reboucas`, criada da ponta validada
`feature/bbz-innova-blue`, commit `4a7d362381ea82ba4a618871a84a1f35ea547ca2`.
Na abertura, `main` estava em `0d0c2d1e21dcda4d8168a6b8850a01fefa38ee78`.
Integrar posteriormente INNOVA antes desta extensão, ou revisar o histórico
completo em conjunto. Não duplicar commits por cherry-pick.

Somente NOVA REBOUÇAS foi acrescentado aos perfis habilitados. WIN e ABROLHOS
continuam bloqueados. Nenhum push, merge, deploy, plano real aprovado/ativado,
cobrança, exportação operacional ou integração easyCollector foi autorizado
por esta implementação. Homologação manual Windows permanece pendente.

## Identidade, leitura e saída

- Catálogo persistente existente: easyCollector **696**, código BBZ **286**;
  Cadastro apresenta **0286**. Reconhecimento por conteúdo, nunca por filename.
- Perfil financeiro/diagnóstico `nova_reboucas@1.0.0`; regras compartilhadas do
  motor, atraso **estritamente superior a 30 dias corridos**. É hipótese
  diagnóstica autorizada; inclusividade e vigência operacional ainda pendentes.
- Referência dos testes privados: **2026-10-26**; judicial de 90 dias não é filtro.
  Régua de origem: `RÉGUA DE COBRANÇA`, **E546**, hash registrado no perfil.
  Condições de acordo e observações administrativas não viram regras automáticas.
- Marcadores A/AJ/J/AE e centavo não herdam vetos TREE. Foram encontrados A e J,
  preservados documentalmente sem excluir recibos por analogia.
- Leitores `bbz_inadimplencia_xlsx_v1` e `bbz_cadastro_geral_pdf_v1` reutilizados,
  sem cópia por condomínio ou alteração da interpretação monetária.
- Perfil de identificadores comprovado no histórico: `BBZ`,
  `BL{bloco}-UNI{unidade com quatro dígitos}-696`, complemento sem sufixo,
  produto `COND. EDIF. NOVA REBOUÇAS`. Bloco **0** comprovado; não presumir
  códigos para outros blocos. O leitor mantém unidades alfanuméricas; sem
  codificação documentada, sua representação fica provisória e sinalizada.
- Política descritiva `descricao_obrigacao_bbz_condominio@1.1.0`, herdada do
  INNOVA. Competência somente pelo histórico principal explícito. Nenhuma nova
  expressão foi necessária. Recibo, componentes e origens permanecem intactos.
- Aba `Dados`, 30 colunas, documentos/CEP textuais, datas Excel, original
  numérico, parcelas sequenciais por contrato, modos A/B. Endereço privado
  cadastrado tem prioridade sem alterar complemento ou misturar pessoas.

## Evidências privadas obtidas

| Verificação | Resultado |
|---|---:|
| Unidades financeiras | 12 |
| Recibos / componentes | 102 / 123 |
| Dívidas no modo A | 95 |
| Dívidas / cadastros no B | 95 / 7 |
| Recibos fora do prazo / original zero | 7 / 0 |
| Descrições comprovadas / pendentes | 102 / 0 |
| Unidades cadastrais / páginas | 144 / 58 |
| Cabeçalhos / continuidades | 199 / 55 |
| Unidades com locação no Cadastro completo | 28 |
| Unidades financeiras localizadas no Cadastro | 12 |
| Documentos vinculados após confronto com referência | 11 |
| Telefones / e-mails aproveitados, por unidade | 11 / 12 |
| Associações retidas após confronto histórico | 1 |

Originais, principal, multa, correção, juros e atualizado reconciliados por
componente, recibo, unidade e condomínio, com Decimal. Totais monetários, dados
pessoais e evidências por registro estão exclusivamente no relatório privado.
Com/sem Cadastro: mesmas dívidas, valores, vencimentos, parcelas, naturezas e
identificadores. No B há sete cadastros distintos com Y:AD vazias; as outras
unidades do Cadastro Geral não geram linhas.

O Cadastro foi emitido em **29/07/2025**; data e rodapé das 58 páginas são
preservados na auditoria temporal opt-in deste perfil. `BBZ_CADASTRO_PERIODO_ANTERIOR`
é alerta; emissão não prova vigência, troca de titular ou atesto de atualidade.
Nomes financeiros e titulares cadastrais concordam nas 12 unidades. Um conflito
entre documentos válidos de Cadastro e referência atinge dez recibos: documento
e contatos retidos, fontes preservadas, nome financeiro e dívidas mantidos.
Documento histórico não localizado nos demais papéis das 144 fichas. Causa
indeterminada; não afirmar erro do histórico nem mudança de titularidade.
Sem referência, a cobertura se limita às fontes enviadas; sem Cadastro não se
copiam documentos do histórico nem se exige inventário anterior do Codex.

## Referência `.xls`: comparação isolada

O original é BIFF8/OLE, **não** XLSX. Continua imutável. O módulo isolado
`conversor.adapters.historical_xls` faz conversão privada para comparação e
manifesto por célula: tipo, valor, formato, hashes original/convertido, datas e
transformações verificadas por reabertura. Não amplia o leitor financeiro.
Macros/fórmulas são rejeitadas, links não são executados nem transportados.
Saída determinística; texto começando por `=` permanece literal.

O histórico tem Y com o cabeçalho duplicado de AA. A transformação explícita
`--revisar-cabecalho-y` conserva esse fato no manifesto e normaliza somente a
estrutura da referência; não altera o original ou copia seus dados para a saída.
Zero inicial de célula numérica só é reproduzido quando comprovado pelo formato
explícito. Número sem formato não recebe dígitos inventados e gera ressalva.
O manifesto contém informações pessoais: deve permanecer fora do Git.

Comparação: **95 dívidas históricas**, 90 com unidade/data/original coincidentes;
três pertencem a unidades ausentes do financeiro atual e duas têm vencimentos
não encontrados. Cinco dívidas atuais não possuem correspondência histórica.
Dos **52 cadastros históricos**, sete pertencem a unidades do financeiro e 45
estão fora dele. Não reproduzir esses 45 cadastros nem ajustar dívidas pela
referência. Diferenças de documento, contatos e descrição são detalhadas
privadamente, sem usar a referência como fonte preferencial.

Para uma referência legada, instalar a dependência opcional e converter antes
do upload (diretório privado já existente, permissões restritas):

```sh
python -m pip install -e '.[historico]'
python -m conversor.adapters.historical_xls --origem '/area-privada/Template.xls' --destino '/area-privada/conversao' --revisar-cabecalho-y
```

Selecionar `referencia_convertida.xlsx` no campo opcional do MVP e conservar
`conversao_referencia_privada.json` ao lado. O upload financeiro não aceita
`.xls`. O original e o manifesto fazem a cadeia de evidências da referência.

## Validação e pendências

**1.751 testes aprovados**: 1.691 regulares e 60 explícitos históricos, incluindo
58 novos casos. Oito verificações de schemas, JavaScript e dependências passaram.
Chromium: upload/download real A/B, remoção do Cadastro, reprocessamento sem
complemento, versão mobile sem overflow e nenhuma falha JavaScript.


Testes sintéticos: identidade 286/0286/696, isolamento, limites 29/30/31/32,
marcadores, centavo, zero, componentes, descrições, papéis, conflito documental,
Cadastro anterior/continuidades, endereço privado, contatos, CPF/CNPJ, A/B,
idempotência, bloqueios e upload/download autenticado. Conversão BIFF8 cobre
épocas 1900/1904, zeros comprovados, cabeçalho Y, fórmulas, rejeições e reprodução.

Canônicos e XLSX TREE/PLAZA/NOVA YORK/INNOVA comparados byte a byte com os
artefatos privados anteriores. INNOVA mantém 33 descrições de dívidas elegíveis
em revisão, duas associações documentais retidas e INAT/PASTEL sem mapeamento.
Os seis recibos zero continuam separadamente preservados em auditoria.

Pendências humanas: inclusividade operacional do prazo, vigência/aprovação
formal, atualidade do Cadastro de 2025, conflito documental da unidade retida,
diferenças do histórico e validação manual no Windows. Nenhuma delas foi
silenciosamente resolvida pela implementação.

Área privada: `/workspace/validacao-privada-fase3/bbz/nova_reboucas/`.
Inventário, quatro diagnósticos A/B com/sem Cadastro, auditoria por recibo,
conversão original/manifesto, evidências do navegador e regressões permanecem
fora do repositório, com fontes inalteradas e permissões restritas.
