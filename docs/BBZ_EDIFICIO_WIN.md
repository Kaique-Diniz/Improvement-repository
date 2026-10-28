# BBZ — EDIFÍCIO WIN: extensão diagnóstica

## Dependência e limites

Branch `feature/bbz-edificio-win`, criada do NOVA REBOUÇAS validado em
`c8d7d24bc1333fcc46e68c98ce855cf97e9dcca9`, que incorpora INNOVA
`4a7d362381ea82ba4a618871a84a1f35ea547ca2`. Na abertura a árvore estava limpa;
`main` local permanecia em `0d0c2d1e21dcda4d8168a6b8850a01fefa38ee78`.
Preservar essa ordem na revisão/integração futura, sem duplicar commits.

Somente WIN foi habilitado. ABROLHOS permanece bloqueado. Sem push/merge/deploy,
plano real aprovado ou ativado, cobrança, exportação operacional, integração CRM
ou homologação para produção. A conferência manual Windows continua pendente.

## Identidade e configurações

- Destino easyCollector **567**, origem BBZ **117**, identidade canônica
  `cond_bbz_edificio_win`. Catálogo existente reutilizado sem alterar suas relações.
- Código de origem com zeros é confrontado pelo valor documental normalizado;
  o token original permanece na auditoria. Financeiro e Cadastro não precisam
  ter o mesmo preenchimento de zeros, mas precisam identificar o mesmo condomínio.
- Perfil diagnóstico `edificio_win@1.0.0`: referência explícita **2026-10-26**,
  hipótese autorizada **atraso > 31 dias corridos**. Inclusividade operacional e
  vigência continuam pendentes. Judicial de **61 dias não é filtro**.
- Régua original inventariada, aba `RÉGUA DE COBRANÇA`, **E166**. Versão/hash no
  perfil. Condições de acordo e observações administrativas ficam na evidência
  privada; não foram transformadas em ações ou regras financeiras automáticas.
- Original zero segue o tratamento BBZ sem dívida, mas preservado em auditoria
  e podendo motivar cadastro no B. Centavo, A/AJ/J/AE e antiguidade não recebem
  vetos TREE. Não há limite arbitrário de ano nem encaminhamento judicial.

## Codificação comprovada e reutilizável

Foi acrescentado ao codificador existente `bloco_tipo_unidade`, configurável
por perfil. Não há leitor específico WIN nem inventário de unidades reais no
código. Dois padrões documentais foram conferidos em 42 unidades:

| Origem | CEDENTE e contrato | COMPLEMENTO |
|---|---|---|
| Bloco `0`, unidade numérica | `BL00-UNID` + número com quatro dígitos + `-567` | `BL0-UNI` + número sem preenchimento |
| Bloco `VG`, literal `VG` + três dígitos + M/P/G | `BL00-` + literal original + `-567` | `BL0-` + literal original |

Há evidência em 37 unidades numéricas e cinco vagas, incluindo identidade e
recibos das vagas. Blocos e unidades **canônicos permanecem originais**: a
representação `BL00`/`BL0` na saída não reclassifica o bloco canônico VG.
Três unidades financeiras não têm linha histórica individual comprovada;
recebem o padrão de apresentação documentado, sem presumir correspondência
com pessoa, contrato histórico ou contato. Seus dados ficam na auditoria privada.
Grafias fora dos padrões continuam provisórias; colisões de saída são rejeitadas.

Nome cedente `BBZ`; produto `CONDOMÍNIO EDIFÍCIO WIN`. O endereço privado cadastrado
segue prioritário. Sem configuração/fonte, endereço fica vazio; complemento da
unidade é independente. Os padrões e a versão/hash da evidência ficam no diagnóstico.

## Leitura real e reconciliação

Reutilizados `bbz_inadimplencia_xlsx_v1`, classificador documental
`descricao_obrigacao_bbz_condominio@1.1.0`, motor e escritor existentes. Nenhuma
alteração na leitura financeira ou nova expressão descritiva foi necessária.

| Verificação | Resultado |
|---|---:|
| Unidades financeiras | 45 |
| Recibos / componentes | 672 / 2.111 |
| Dívidas elegíveis no A | 631 |
| Dívidas / cadastros no B | 631 / 41 |
| Recibos fora do prazo | 41 |
| Recibos com original zero | 0 |
| Descrições comprovadas / pendentes | 672 / 0 |
| Vencimento mais antigo | 2016 |
| Recibos anteriores a 2020 | 195 |
| Marcadores A / J preservados | 4 / 425 |
| Componentes de centavo / negativos | 1 / 6 |

Seis colunas monetárias reconciliadas por componente, recibo, unidade e condomínio
com Decimal. Valores monetários reais e inventário individual permanecem somente
na área privada. O único componente de centavo não é o original integral do
recibo; não se converte em zero nem provoca exclusão. Nenhum recibo integral de
centavo foi encontrado nesta fonte; esse caso também está coberto sinteticamente.

Há 18 unidades com dívidas elegíveis e 41 com algum recibo recente: 14 aparecem
nos dois grupos, conforme os modos universais. Cadastros adicionais não duplicam
por recibo, têm Y:AD vazias e não trazem dívida recente. As 631 dívidas A/B são
idênticas. Parcelas sequenciais por contrato, datas nativas, 30 colunas em `Dados`.

## Ausência de Cadastro Geral

**CADASTRO_GERAL_NAO_FORNECIDO**. Foram localizados somente financeiro, template
histórico e régua do WIN. A ausência é informação do processamento e do manifesto,
visível na interface; não é erro de leitura, conflito de documento ou bloqueio
financeiro. Nomes financeiros são preservados; CPF/CNPJ e contatos sem origem
ficam vazios. Dados pessoais do template não são copiados.

Um futuro Cadastro correto pode ser associado pela política BBZ existente por
papel/identidade. Isso foi testado exclusivamente com PDF sintético, sem declarar
Cadastro real do WIN disponível. Cadastro de outro condomínio é rejeitado.

## Comparação histórica BIFF8

Conversor isolado herdado do NOVA REBOUÇAS, sem ampliar o leitor financeiro.
A coluna AE do histórico é integralmente vazia, inclusive no cabeçalho; contém
somente formatação. A extensão `conversao_referencia_biff8@1.1` conserva no
manifesto tipo/valor/formato das 875 células extras, confirma o vazio integral
e mantém a referência convertida com 30 colunas. Qualquer dado extra, inclusive
zero, espaço ou booleano, continua rejeitado. Fórmulas/macros são rejeitadas;
links não são executados. Original preservado e conversão determinística.

- **631 dívidas históricas:** bijeção comprovada com os 631 recibos elegíveis por
  identidade, vencimento e original; descrições literais coincidem em **631/631**.
- **243 linhas cadastrais históricas:** não são o resultado do modo B atual.
  Há 29 linhas com vínculo ao financeiro atual e 214 sem vínculo comprovado;
  três repetições cadastrais dentro das linhas vinculadas.
- Seis diferenças de nomes ocorrem em linhas cadastrais históricas vinculadas.
  Nenhuma altera o nome financeiro nem prova troca de titularidade.
- Documentos/telefones/e-mails antigos e diferenças de representação ficam na
  comparação privada, sem completar dados atuais por suposição.

A referência não comprova regra operacional nem autoriza importação. O modo B
atual deriva dos 41 recibos não elegíveis; não reproduz os 243 cadastros antigos.

## Testes e pendências

**1.801 testes aprovados**: 1.741 regulares e 60 explícitos históricos,
incluindo 50 novos casos. Oito verificações de schemas e JavaScript aprovadas.
Chromium validou upload comum, seleção automática/explicita, A/B, download, aviso
de Cadastro não fornecido, remoção da referência e XLSX idêntico sem referência;
mobile sem overflow e nenhum erro JavaScript.

Testes sintéticos cobrem datas antigas nativas/textuais, ano completo/abreviado,
limites 30/31/32 e 61/62 dias, centavo, zero, negativos, componentes e encargos,
marcadores, descrição documental, ausência de Cadastro, associação por papel,
identidade 117/567/zeros, tipos de unidade, saída/proveniência, rejeições, A/B,
idempotência, bloqueios, BIFF8 e upload/download autenticado.

Regressões reais TREE/PLAZA/NOVA YORK/INNOVA/NOVA REBOUÇAS usam as bases privadas
anteriores: canônicos e XLSX comparados byte a byte. Permanecem o diagnóstico
Habita/VG, retenções cadastrais/documentais, 33 descrições elegíveis em revisão
INNOVA, INAT/PASTEL e a ressalva temporal NOVA REBOUÇAS. Nenhum crítico liberado.

Pendências: confirmação operacional da inclusividade do prazo e vigência,
Cadastro real WIN ainda não fornecido, três unidades sem linha histórica e
validação manual Windows dos arquivos gerados. Não se transforma implementação
diagnóstica em homologação operacional.

Comandos de regressão local:

```sh
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

Artefatos privados: `/workspace/validacao-privada-fase3/bbz/edificio_win/`.
Incluem inventário/hashes, conversão e manifesto, A/B, valores/atualizado por
recibo/unidade, diferenças do histórico, auditoria de centavo e evidências do
navegador e das regressões. Nenhum desses documentos reais integra o commit.
