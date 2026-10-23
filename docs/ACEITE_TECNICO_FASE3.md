# Aceite técnico da Fase 3 — revisão de 21/10/2026

**Recomendação: leitores tecnicamente aptos para encerramento da Fase 3, com
ressalvas e bloqueios operacionais preservados.** A decisão de encerrar/avançar
permanece com o responsável. Não há liberação dos lotes bloqueados, homologação
para produção ou início da Fase 4 nesta entrega.

**Decisão posterior do responsável:** encerramento técnico da Fase 3 autorizado
explicitamente, com as ressalvas deste documento e os bloqueios de lote, unidade
e cadastro mantidos. Evidências aceitas: 458 testes aprovados, 884 boletos
reconciliados e 132 correspondências financeiras. Esta decisão não homologa o
produto para produção nem resolve as pendências de dados/fontes. A preparação
da Fase 4 foi autorizada, começando pela revisão da arquitetura e das regras.

## Evidências de aceite

As cinco fontes autorizadas tiveram SHA-256 novamente conferido, sem alteração.
Documentos, gabaritos, scripts de investigação e resultados individuais continuam
exclusivamente na área privada, fora do Git. Referências Excel são resultados
esperados; não decidem titularidade nem autorizam alterações de cobrança.

| Critério | Evidência | Resultado |
|---|---|---|
| Habita | 112 unidades, 769 boletos, 2.082 componentes | Preservados |
| FL | 50 unidades, 115 boletos, 985 componentes | Preservados |
| Continuidade monetária | 33 boletos Habita e 17 FL com componentes em várias páginas | Sem omissões/duplicações frente ao inventário independente |
| Continuidade descritiva FL | Outros três boletos com continuação apenas descritiva | Sem novos lançamentos |
| Reconciliação | Identidade, vencimentos, valores, composições, páginas, acréscimos Habita e saldo final FL | Zero divergências financeiras; objetos dos 884 boletos iguais aos anteriores |
| Referências Excel | Unidade, boleto, vencimento e valor original | 63 dívidas Habita + 69 FL = 132 correspondências preservadas |
| Cruzamento cadastral | 390 registros, somente 50 unidades inadimplentes | Todas as 50 encontradas por condomínio + bloco/torre + unidade; nenhum cadastro adicional misturado |
| Auditoria | Formato/versão, arquivo/hash, página/linha; campos cadastrais brutos com coordenadas | Preservados |
| Template | 30 cabeçalhos e ordem; CPF/CNPJ válido textual, inclusive zeros iniciais | Contratos preservados; importação integral ainda pendente |
| Regressão | 432 anteriores + 26 novos | 458 aprovados |

## Subtotal Habita

Na página 149, o subtotal rotulado `Total do Bloco VG` reproduz os cinco campos
do `Total Geral`, em vez da soma exclusiva VG. Uma reextração independente por
coordenadas confirma os valores encontrados em layout. O total geral concilia
com a soma dos componentes; o subtotal VG não concilia com seu próprio escopo.

Classificação: **inconsistência de subtotalização ou rotulagem/apresentação no
relatório original**. Não foi demonstrado erro de extração. Sem esclarecimento
do emissor, não é possível distinguir cálculo de escopo incorreto de rótulo
incorreto. Nenhum valor foi corrigido. `SUBTOTAL_BLOCO_DIVERGENTE` permanece
crítico e bloqueia o lote; solicitar retificação/esclarecimento documentado.

## Revisão individual das 34 unidades FL

O dossiê privado registra, para cada unidade, ambos os nomes, classificação,
campos originais do Cadastro, posições/páginas/linhas e ação de revisão.

| Evidência textual | Unidades | Tratamento |
|---|---:|---|
| Nomes compostos coincidentes, com múltiplos titulares indicados | 17 | Vínculo documento/titular continua pendente |
| Nome do Cadastro é prefixo do nome da inadimplência, com múltiplos titulares | 11 | Preservar textos e bloquear associação automática |
| Nome simples do Cadastro é prefixo do nome da inadimplência | 6 | Diferença textual não comprova identidade; manter revisão |

Os nomes do Cadastro reproduzem exatamente os fragmentos da coluna do PDF.
As 17 diferenças são prefixos textuais, compatíveis com abreviação/limitação de
apresentação na fonte; não se comprovou perda de tokens pelo leitor. Não foi
comprovada alteração cadastral nem conflito real de titularidade nessas 34
unidades. Isso não prova identidade: os 34 bloqueios foram preservados, incluindo
28 casos com múltiplos titulares e 17 diferenças textuais, com sobreposição.
Nenhum titular foi substituído automaticamente.

Os **dois conflitos de CPF válido são duas ocorrências em uma mesma unidade**,
entre Cadastro e referência Excel. Continuam bloqueados na comparação documental,
com ambos os documentos e fontes. A referência não alimenta o leitor financeiro
nem resolve o cadastro. A leitura isolada do Cadastro não libera esse dossiê de
comparação: ele permanece retido para revisão humana. Datas de emissão/posição
dos relatórios e nome da planilha não comprovam vigência do vínculo. A decisão
precisa de comprovante de titular/documento vigente, responsável e fundamento.

Nas quatro ocorrências de zeros iniciais, os documentos completos estão na fonte;
não se completou a referência numericamente. Sua associação ao titular continua
pendente. As três ocorrências de CNPJ válido permanecem aceitas pelo contrato.

## Competências e contatos

Habita não fornece competência explícita: os 769 boletos continuam com competência
nula e agora têm alerta com origem. O token de Emissão permanece bruto. Não se
inferiu competência de emissão, vencimento ou descrição. FL fornece a coluna
explícita para todos os 115 boletos; períodos de consumo não a substituem.

O Cadastro passou de zero para **389 endereços segmentados**, usando delimitadores
escritos, linhas continuadas e CEP textual. Um registro contém dois endereços
completos: saída vazia, ambos na auditoria e bloqueio da unidade. Esse registro
não pertence às 50 unidades inadimplentes deste lote.

E-mails fragmentados agora são reconstruídos antes da validação, evitando aceitar
prefixos de domínio. Em 71 registros, 55 entradas anteriores foram substituídas
e 78 completas adicionadas às listas: total armazenado de 561 para 584, respeitando
o limite por contato. Telefones alternativos entre parênteses foram recuperados
em três registros: total de 486 para 489. País duplicado e DDD ausente não foram
corrigidos por suposição. Os valores e todas as fontes constam do dossiê privado.

No Cadastro inteiro, restam quatro registros com fragmentos telefônicos inválidos,
95 sem telefone validado, 51 sem e-mail e quatro com contatos excedentes ao limite
de cinco telefones/três e-mails. Excedentes/brutos permanecem na auditoria. Entre
os 50 cadastros correspondentes há 11 ausências de telefone e seis de e-mail.
Contatos não são transferidos quando o titular está em conflito: o lote enriquecido
mantém 25 unidades sem telefone e 21 sem e-mail. Ausência de contato opcional
não dispensa nem amplia o bloqueio de titularidade.

Habita mantém 16 unidades sem telefone validado e duas sem e-mail, agora com
alertas explícitos, sem preenchimento ou DDD presumido.

## Classificação de todas as pendências restantes

| Pendência | Categoria | Próximo tratamento |
|---|---|---|
| Subtotal VG inconsistente na fonte | Bloqueante do lote | Retificação/esclarecimento documentado; manter o bloqueio atual |
| 34 unidades com associação documental/titularidade pendente | Bloqueante do cadastro ou unidade | Comprovar titular e vínculo; nenhuma prioridade implícita de fonte |
| Dois conflitos de CPF válido, uma unidade, na referência | Bloqueante do cadastro ou unidade | Revisão humana com fontes, vigência e fundamento; dossiê retido |
| Um cadastro com dois endereços completos | Bloqueante do cadastro ou unidade | Identificar endereço aplicável com evidência; não misturar o Cadastro inteiro ao lote |
| CPF/CNPJ ausente ou inválido | Alerta não bloqueante | Vazio, alerta e bruto na auditoria; distinguir de conflito entre documentos válidos |
| Telefone inválido/sem DDD/ausente, e-mail ausente, contatos excedentes | Alerta não bloqueante | Vazio quando não verificável; preservar brutos/excedentes |
| Competência Habita ausente na fonte | Alerta não bloqueante da leitura | Manter nulo; exportação de dívida que a exigir continua bloqueada |
| Critério para obter competência Habita por fonte/mapeamento adicional, se necessário | Dependência de regra de cobrança da Fase 4 | Aprovação explícita; não inferir vencimento nesta fase |
| Seleção dos 706 boletos Habita e 46 FL fora das dívidas de referência | Dependência de regra de cobrança da Fase 4 | Validar régua, prazos, apontamentos e cadastro antecipado; ausência na referência não prova erro |
| Aceitação integral de competência, datas, valores, contatos, linhas e demais campos das 30 colunas | Dependência da importação no easyCollector da Fase 5 | Ensaio controlado; CPF/CNPJ na coluna literal CPF já confirmado como requisito |

Resumo suplementar Habita, notas administrativas FL e campos originais preservados
são evidências informativas, não lançamentos adicionais. As ocorrências completas
estão classificadas por código, escopo, origem e unidade no dossiê privado.
Nenhum formato foi promovido automaticamente a produção. Bloqueios de identidade,
formato, soma e duplicidade continuam ativos. O construtor de exportação atual
recusa o lote inteiro quando há ressalva crítica; esta revisão não criou liberação
parcial de unidades.

## Testes e reprodução

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
.venv/bin/python -m conversor.schemas --check
.venv/bin/python -m conversor.recognition_schemas --check
```

Resultado: **398 testes regulares + 60 explícitos = 458**; schemas sincronizados.
Os 26 novos testes em `tests/phase3/test_final_review.py` cobrem segmentação,
continuidade de endereço/e-mail/telefone, dados inválidos e ausentes, endereços
múltiplos, competência sem inferência e bloqueio de titular com nome prefixado.
Todas as fixtures foram criadas do zero; a suíte pública independe dos PDFs reais.

A revisão privada `revisao_final_fase3_004` contém scripts reproduzíveis, confronto
dos 884 boletos, comparação das 132 dívidas, análise individual das 34 unidades,
dois conflitos documentais, competências e contatos antes/depois. O relatório
detalhado e a matriz de ocorrências permanecem fora do Git.

Não foi demonstrado impedimento de implementação dos leitores que exija nova
correção estrutural antes da revisão de encerramento. Persistem impedimentos de
uso automático dos lotes/registros identificados e dependências de negócio e
importação. Recomenda-se aceite técnico com essas ressalvas e retenções. Amostras
de um período não garantem cobertura de todas as variações futuras.
