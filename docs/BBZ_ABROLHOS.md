# BBZ — ABROLHOS: conferência de requisitos e cobertura diagnóstica

## Resultado e genealogia

Branch `feature/bbz-abrolhos`, criada do WIN
`eaa8fc885210cc00d70a1586591696438a6499ea`, preservando NOVA REBOUÇAS
`c8d7d24` e INNOVA `4a7d362`. Sem push, merge, deploy, exportação operacional,
integração CRM ou homologação para produção.

A implementação diagnóstica está concluída, com cobertura documental parcial
do destino. **Não se comprovou que as 90 unidades pertençam a ABROLHOS.** O
responsável confirmou que não existe documento adicional vinculando os blocos
e prefixos à torre. As unidades sem prova permanecem retidas; não há mapa
presumido de todo o empreendimento para o destino 788.

## Matriz de conferência das especificações

| Requisito solicitado | Implementação / evidência | Situação |
|---|---|---|
| Reutilização da arquitetura BBZ | Leitores XLSX/PDF, motor, classificador e escritor universal existentes; nenhum conversor financeiro paralelo | Atendido |
| Origem 575/0575 separada do destino 788 | Catálogo de integração, perfil `abrolhos@1.0.0`, identidade candidata `cond_bbz_abrolhos`; códigos originais preservados | Atendido |
| Papel do arquivo por conteúdo | O arquivo chamado `Cadastro.xlsx` é o financeiro; somente o PDF é Cadastro Geral de pessoas | Atendido |
| Empreendimento compartilhado não comprova torre | Novo contrato `escopo_destino_documental@1.0.0`; 25 unidades com evidência histórica individual, 65 sem prova | Parcial por falta de fonte; retenção implementada |
| Mapeamento versionado e auditável | Origem, hash financeiro, hash da referência, hash do perfil, chaves, recibos e linhas comprovantes em `escopo_destino.json` e manifesto | Atendido para o escopo demonstrado |
| Não associar outra torre ou por aproximação | Sem equivalência automática por nome genérico, bloco, prefixo, endereço ou unidade próxima; produto conflitante retém | Atendido |
| Preservar todos os dados financeiros | 90 unidades, 216 recibos, 1.472 componentes; seis colunas reconciliadas por recibo, unidade e fechamento | Atendido |
| Prazo diagnóstico explícito | Referência 26/10/2026 e atraso > 60 dias corridos; 59/60/61 e > 90 testados; vigência não presumida | Atendido para diagnóstico |
| Judicial e marcadores | Judicial de 90 dias não filtra; AE/AJ/J preservados; sem vetos TREE de A/AJ/J/AE ou centavo | Atendido |
| Identificadores sem perder prefixos | Codificador por perfil conserva bloco/unidade, zeros e letras, rejeita formatos não comprovados e colisões | Atendido |
| Cadastro completo, papéis e continuidades | 529 unidades, 205 páginas, 723 cabeçalhos e 194 continuações; original integral na auditoria privada | Atendido |
| Associação cadastral somente no escopo | 25 fichas localizadas; demais 504 não aproveitadas; 65 unidades financeiras sem associação de documentos/contatos | Atendido |
| Documentos e contatos com evidência | 23 documentos válidos, 18 telefones e 31 e-mails; duas associações documentais retidas | Atendido; conflitos humanos pendentes |
| Endereço físico e correspondência | Endereço físico do empreendimento segmentado; correspondência/papéis preservados separadamente; configuração privada mantém prioridade | Atendido; não havia configuração ABROLHOS para comparar |
| Descrição documental da dívida | Política BBZ 1.1.0 existente: 212 descrições comprovadas, quatro neutras em revisão, sem competência inferida | Atendido com ressalva documental |
| Comparação histórica sem copiar dados | 103 vínculos únicos por identidade, vencimento e original; diferenças das 30 colunas detalhadas privadamente | Atendido |
| Modos A/B sem expansão do Cadastro | A: 103 dívidas; B: mesmas 103 + 24 cadastros únicos, Y:AD vazias | Atendido no escopo comprovado |
| Contrato universal | Uma aba `Dados`, 30 cabeçalhos literais; documento/CEP textuais, datas nativas, valores numéricos, parcelas sequenciais | Atendido |
| Sem Cadastro e upload comum | Quatro combinações A/B com/sem Cadastro; navegador real com upload normal, autenticação, remoção de arquivos e download | Atendido |
| Testes e regressões | 43 casos novos; 1.844 testes; oito verificações de schemas; 20 cenários privados dos seis condomínios anteriores | Atendido |
| Privacidade e limites operacionais | Fontes e artefatos reais fora do Git; revisão de segredos/dados; endpoint operacional bloqueado | Atendido |
| Homologação integral do conjunto | Pertencimento completo à torre, conflitos, vigência/inclusividade operacional e conferência Windows ainda não comprovados | Pendente; não declarada |

## Prova de escopo e limitações

A família documental reconhece `CONDOMINIO JARDINS DO BRASIL`, origem 575/0575,
como empreendimento compartilhado. Não há legenda documental demonstrando que
todos os blocos 0/D/E ou prefixos A/B/C sejam exclusivos de ABROLHOS. A ocorrência
isolada da palavra ABROLHOS no Cadastro pertence a correspondência, não a uma
identificação de torre utilizável como mapa.

O adaptador `scope_reference.py` exige referência XLSX segura com o contrato de
30 colunas, administradora e produto de destino explícitos, codificação integral
de bloco/unidade, contrato concordante, nome financeiro concordante e um único
recibo com vencimento e valor original coincidentes. Não copia CPF, contatos,
endereço ou descrição histórica. Evidência contraditória para o destino retém a
unidade e preserva as duas origens. Fórmulas não servem de prova.

O resultado comprova vínculo **histórico para diagnóstico**, não titularidade
atual, vigência ou aprovação humana. A prova é recalculada pelos documentos em
cada processamento: alterar manualmente um snapshot não libera unidades.
Sem a referência, o financeiro continua legível, mas nenhuma unidade ganha
autorização de associação ao destino apenas pelo código genérico. A interface
mostra a cobertura e a retenção específica `DESTINO_TORRE_NAO_COMPROVADO`.

Nesta amostra, as 25 unidades comprovadas contêm 145 recibos: 103 elegíveis e
42 recentes. As 65 unidades inconclusivas contêm outros 71 recibos, também
recentes. Portanto, são **113 não elegíveis financeiramente**, dos quais 71
têm adicionalmente retenção de identidade; não são duas populações somáveis.
No modo B, somente 24 unidades comprovadas têm recibo não elegível. As demais
unidades não geram cadastro adicional, mesmo estando no Cadastro Geral.

## Codificação e regras

Perfil de saída comprovado: nome cedente `BBZ`, produto
`JARDINS DO BRASIL ABROLHOS`, `COMPLEMENTO = BL{bloco}-UNI{unidade_literal}` e
`CEDENTE = NM_CONTRATO_CEDENTE = COMPLEMENTO + '-788'`.
O sufixo foi conferido no histórico; não foi transplantado de outro condomínio.
O bloco 0 admite a forma documental de um dígito + SS + três dígitos; D admite
A/B/C + cinco dígitos; E admite A/B + cinco dígitos. Esses padrões **codificam**
unidades, mas não comprovam pertencimento à torre. Não há lista de unidades
inadimplentes reais em configuração pública.

Régua inventariada de 26/10/2026, aba `RÉGUA DE COBRANÇA`, E174, com menção
adicional na linha 625. Hash e vínculo ficam no perfil; conteúdo administrativo,
acordos e credenciais permanecem privados. Mais de 60 dias é a hipótese
diagnóstica autorizada; judicial de 90 não integra a seleção. Vigência
operacional continua não informada. Original zero permanece na auditoria sem
gerar dívida, conforme política BBZ; valores pequenos e negativos não recebem
exclusão coletiva. Nesta amostra não há componente negativo, mas a preservação
de negativos está testada sinteticamente. Foram preservados AE=14, AJ=2 e J=29.

## Cadastro, descrições e comparação

O cruzamento usa condomínio candidato + bloco/unidade textual + titular
comprovado e papéis cadastrais. O universo bruto de 529 fichas não é rotulado
como 529 membros comprovados de ABROLHOS. Duas unidades possuem documentos
válidos divergentes do histórico, afetando nove linhas de referência; associação
de documento/contatos fica retida. O documento histórico não foi encontrado
nos demais papéis do Cadastro. A causa permanece indeterminada; não se presume
troca de titularidade nem se substitui a fonte atual pelo template.

Não se contam as 65 associações sem prova de torre como ausência de CPF. Elas
possuem categoria própria de escopo pendente. Os 23 documentos aproveitados
são válidos e textuais; sem Cadastro, documentos e contatos ficam vazios.

Quatro recibos elegíveis não têm natureza principal reconhecida pela política
atual, com 14 componentes e 11 históricos distintos. Usam descrição neutra e
revisão, preservando componentes e origens. Uma adaptação futura depende de
evidência segura para novas naturezas; não foi criada classificação para imitar
o histórico. Outros 212 recibos têm descrição comprovada.

As 103 dívidas foram vinculadas individualmente ao histórico, com identidade,
nome, vencimento, original, contrato e parcela concordantes. As descrições
literais não coincidem: em 99 casos há sufixo histórico de parcela separado,
dispensado pela política BBZ atual; os quatro restantes continuam em revisão.
As 103 datas históricas são texto, enquanto a saída usa datas Excel equivalentes.
Endereço/logradouro, bairro e cidade diferem nas 103 linhas: mantém-se a fonte
física atual do empreendimento, sem escolher o endereço antigo do template.
Não havia endereço ABROLHOS no cadastro privado local para comparação.
Há diferenças de contato, discriminadas por campo e fonte no relatório privado,
e nove linhas com documento retido. Esses dados não foram copiados do histórico.

## Evidências de execução

**1.844 testes aprovados:** 1.784 da suíte regular e 60 históricos explícitos,
incluindo 43 novos casos ABROLHOS. Oito geradores de schemas passaram em `--check`;
JavaScript passou na verificação sintática. Um aviso preexistente de depreciação
AnyIO/Starlette não afeta o resultado.

Chromium validou upload comum do financeiro chamado Cadastro.xlsx com PDF e
referência, modos A/B, download, retirada efetiva do PDF cadastral, retirada da
referência com retenção por escopo, interface mobile sem overflow e zero erros
JavaScript. Sem referência, os 103 elegíveis financeiros continuam visíveis,
mas sem linhas disponíveis por falta de prova de destino. Endpoint operacional
retorna bloqueio, independentemente de haver arquivo diagnóstico.

Os 20 cenários privados dos seis condomínios anteriores preservam canônicos e
XLSX **byte a byte**, com e sem Cadastro quando disponível. Resultados A/B:
TREE 63/63+103; PLAZA 69/69+46; NOVA YORK 26/26+2; INNOVA 639/639+6;
NOVA REBOUÇAS 95/95+7; WIN 631/631+41. Preservadas as retenções documentais,
INAT/PASTEL, descrições pendentes e a anomalia diagnóstica Habita/VG.

```sh
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

Fontes, hashes completos, valores, inventário de todos os recibos, diferenças
individuais e evidências do navegador ficam somente em
`/workspace/validacao-privada-fase3/bbz/abrolhos/`, com permissões restritas.
Saídas: `diagnosticos/{com_cadastro,sem_cadastro}/{A,B}/TESTE_LOCAL_NAO_IMPORTAR.xlsx`.
Auditoria: `auditoria_privada_completa.json` e
`AUDITORIA_PRIVADA_ABROLHOS_NAO_IMPORTAR.xlsx`; regressões em
`regressao/resumo_privado.json`. Nenhum desses artefatos reais integra o commit.

Pendências reais: prova adicional para as 65 unidades, revisão dos quatro
históricos e dos dois conflitos documentais, confirmação operacional do prazo
e vigência, eventual configuração do endereço pela interface e conferência
manual Windows. A ausência de documento adicional foi confirmada pelo
responsável e **não foi convertida em permissão** para ampliar o escopo.
