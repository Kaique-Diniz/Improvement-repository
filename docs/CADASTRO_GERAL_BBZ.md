# Cadastro Geral PDF BBZ — piloto NOVA YORK

Implementado somente para diagnóstico do NOVA YORK PENTHOUSES. O complemento é
opcional; os outros quatro condomínios BBZ continuam sem perfil financeiro ativo.
Não há aprovação de planos, atesto humano automático, exportação operacional,
integração easyCollector ou homologação para produção.

## Implementação e critérios

| Camada | Responsabilidade |
|---|---|
| `domain/bbz_cadastro.py` | Evidências tipadas por titular, locatário, pagador, unidade, correspondência e observações; compatíveis com os contratos históricos. |
| `readers/bbz_cadastro.py` | Família `bbz_cadastro_geral_pdf_v1`: geometria, identidade repetida, paginação, resumo, fichas e continuações. Não seleciona dívidas. |
| `readers/operational.py` | Registro pelo protocolo existente, hash e proveniência conferidos. |
| `application/bbz_cadastro.py` | Política `bbz_associacao_por_papel@1.0.0`: vínculo estrutural e pessoal comprovado; financeiro preservado. |
| `web/service.py` e interface | Upload comum opcional, indicadores, revisão por unidade e persistência privada da extração cadastral/auditoria. |

O reconhecimento usa conteúdo, catálogo persistente e perfil habilitado; nome de
arquivo e código easyCollector ausente no PDF não impedem a associação. Código
administrativo com zeros iniciais é comparado em forma normalizada, preservando
sua grafia original. Nome, código e CNPJ válido do condomínio devem permanecer
consistentes entre páginas. A identidade fiscal foi confrontada com as evidências
privadas existentes nesta validação; isso não é um atesto humano nem autentica
a emissão de PDFs futuros.

O PDF real usa criptografia de permissões com abertura sem senha e extração
permitida. O leitor cadastral BBZ aceita somente esse caso, após verificar a
permissão de extração e a assinatura estrutural completa. Não busca senhas,
não regrava o original e mantém limites de arquivo, páginas, stream e texto.
A sondagem genérica e os demais formatos continuam rejeitando PDFs protegidos.

O vínculo usa administradora + condomínio + bloco/unidade normalizados, com os
mesmos IDs do leitor financeiro. Código do cliente é auxiliar e pode repetir.
Continuação exige primeiro cabeçalho da nova página, ficha anterior, identidade,
nome e cliente consistentes. Duplicação de ficha, colisão normalizada, ausência
de cabeçalho, paginação incompleta e resumo divergente impedem o cruzamento.
O rodapé é reconhecido pelo seu conteúdo; dados legítimos próximos dele não são
suprimidos por uma faixa geométrica arbitrária.

## Seleção cadastral

- O nome financeiro permanece na saída. Nome compatível exige igualdade após
  normalização simples de acentos, caixa e espaços, sem correspondência parcial.
- Documentos e contatos aproveitados são exclusivamente do titular cadastral
  comprovadamente associado à identidade financeira. Locatário, pagador,
  contatos da unidade e observações permanecem separados na auditoria.
- Pagador não identificado nominalmente não é presumido igual ao titular.
  Documento repetido em outro papel não gera falso conflito nem é transferido.
- Divergência de nome ou documentos retém a associação cadastral individual,
  registra fontes e mantém os dados não associados fora da projeção. Não exclui
  recibos nem altera elegibilidade. Críticos financeiros/documentais anteriores
  continuam bloqueantes e não são reavaliados pela política BBZ.
- Ausência/invalidade de documento produz campo vazio e aviso/alerta. CPF/CNPJ,
  telefones e CEP preservam texto e zeros; DDD não é inferido. Até cinco pares
  DDD/FONE e três e-mails são projetados; excedentes e entradas não segmentadas
  ficam nas evidências originais. E-mail malformado não é corrigido.
- Endereço físico explícito do cabeçalho pode preencher a fonte quando totalmente
  segmentável. Endereço privado cadastrado continua prioritário em todas as
  linhas, com complemento individual. Divergências são alertadas; cobrança e
  endereço do locatário são apenas evidências auxiliares.

## Validação privada

| Conferência | Resultado |
|---|---:|
| Páginas / unidades cadastrais distintas | 48 / 125 |
| Cabeçalhos / continuações | 169 / 44 |
| Unidades alugadas / códigos de cliente compartilhados | 7 / 1 |
| Unidades financeiras localizadas | 7 / 7 |
| Unidades com documento válido vinculado | 6 |
| Associações retidas por titular divergente | 1 |
| Telefones / e-mails aproveitados, contados por unidade | 4 / 9 |
| Modo A / modo B | 26 dívidas / mesmas 26 dívidas + 2 cadastros |
| Descrições financeiras coincidentes com a referência | 26 / 26 |

A unidade divergente mantém o nome financeiro e documento/contatos de terceiros
em branco. As duas identidades e suas origens ficam na auditoria privada. Não
se impõe meta de preenchimento integral nem se usa a planilha histórica como
fonte cadastral atual. Os valores, vencimentos, recibos, componentes, nomes
financeiros, identificadores e parcelas permaneceram inalterados. Y:AD ficam
vazias nos dois cadastros. Sem complemento, canônicos e XLSX anteriores do piloto
permaneceram idênticos. TREE/PLAZA também foram comparados integralmente.

A auditoria guarda a extração integral de 125 fichas em
`cadastro_bbz_original.json`, vinculada por hash no manifesto, além das decisões
por unidade. Papéis, campos originais, documento, leitor/versão, hash, página,
linha, coluna geométrica e seção são rastreáveis. Os arquivos reais, relatórios
por unidade e valores detalhados permanecem exclusivamente na área privada.

## Testes e limites

**1.605 testes aprovados**: 1.545 regulares + 60 explícitos; 59 novos testes
sintéticos. Oito verificações de schemas preservam os contratos históricos.
Inclui duas/três páginas por ficha, continuação junto ao rodapé, duplicidades,
colisões, cliente compartilhado, zeros, unidades alfanuméricas, papéis distintos,
CPF/CNPJ válidos/inválidos, documentos repetidos/conflitantes, limites e
normalização de contatos, corrupção/incompletude, proteção PDF, upload,
autenticação, endereço privado e preservação dos bloqueios críticos.

```bash
python -m pytest -q
python -m pytest -q tests/homologacao/pacote_suite.py tests/homologacao/revisao_suite.py tests/homologacao/leitores_fase3_suite.py
```

Navegador validado com upload real A/B, referência opcional, endereço fictício
privado, downloads autenticados, detalhe da associação retida e remoção do PDF
complementar seguida de novo processamento. Exportação operacional retorna 409.
Testes executados em Linux; teste nativo da instalação Windows continua humano.
Variantes de outros condomínios, associação de documentos de pagador/locatário
sem prova nominal e aprovação de conflitos permanecem fora desta entrega.
