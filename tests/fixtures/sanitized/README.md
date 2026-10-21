# Recepção de amostras sanitizadas e laboratório sintético

Em 21/10/2026 foi recebido o pacote **100% sintético**, recriado do zero,
`Homologacao_Sanitizada_Conversor/`. Ele está disponível localmente nesta pasta,
com os nove arquivos originais preservados; não é amostra representativa real.
O pacote, gabaritos e resultados permanecem ignorados pelo Git. Consulte
[o relatório do laboratório](../../../docs/RELATORIO_PACOTE_SINTETICO.md) e execute
`python -m pytest -q tests/homologacao/pacote_suite.py` após instalar o projeto.

As instruções abaixo continuam necessárias para a homologação futura com
amostras representativas sanitizadas. Nenhum leitor está aprovado para produção.

A integração posterior da Fase 3 acrescenta o contrato comum dos leitores e uma
validação privada fora de Git, com manifesto/hash e comparação canônica. Consulte
[LEITORES_FASE3.md](../../../docs/LEITORES_FASE3.md). Não colocar documentos reais
nesta pasta: o caminho privado externo ainda deve ser confirmado/autorizado.

Esta pasta é reservada a material previamente sanitizado e autorizado. O `.gitignore`
local ignora tudo, exceto esta documentação e o manifesto **de exemplo**. Não force
commit de PDFs, gabaritos de clientes, cadastros, senhas ou dados originais.

Copie `manifesto.exemplo.json` para `manifesto.local.json`, ajuste data de referência,
caminhos e IDs opacos. A data do exemplo é ilustrativa, não uma convenção de negócio.
Os arquivos referenciados ainda não existem; nenhum formato está homologado por isso.

## Arquivos necessários agora, para homologar reconhecimento

1. `habita_tree_sanitizado.pdf`: PDF com texto da família Habita/TREE, com cabeçalho,
   marcadores de tabela e identificação explícita de administradora/condomínio.
2. `fl_plaza_sanitizado.pdf`: PDF com texto da família FL/Plaza, nas mesmas condições.
3. `habita_tree.reconhecimento.esperado.json` e
   `fl_plaza.reconhecimento.esperado.json`: gabaritos revisados com `tipo`, `estado`,
   `formato_id`, `administradora_id`, `condominio_id` e `bloqueios` (lista de códigos).
4. `catalogo.homologacao.json` e `assinaturas.homologacao.json`, em diretório
   protegido: IDs consistentes com os
   gabaritos, rótulos/identificadores sanitizados, referências e evidência de revisão.
   Os identificadores sanitizados precisam concordar entre fontes e configuração.
5. Para homologar também a reutilização em outros condomínios, fornecer adicionalmente
   `habita_outro_condominio_sanitizado.pdf` e `fl_outro_condominio_sanitizado.pdf`,
   com `habita_outro_condominio.reconhecimento.esperado.json` e
   `fl_outro_condominio.reconhecimento.esperado.json`. Incluir as identidades no
   catálogo/assinaturas revisados. Não renomear o mesmo PDF como se isso provasse
   reconhecimento de outra identidade; os seis arquivos anteriores são o conjunto
   mínimo dos dois casos iniciais, não uma homologação de todos os condomínios.

Cada gabarito de reconhecimento tem este formato (IDs ilustrativos, a ajustar):

```json
{
  "tipo": "pdf_texto",
  "estado": "conhecido_validado",
  "formato_id": "fmt_revisado_v1",
  "administradora_id": "adm_sanitizada",
  "condominio_id": "cond_sanitizado",
  "bloqueios": []
}
```

O gabarito deve ser revisado independentemente do resultado do programa. Esses
arquivos não devem ser gerados copiando uma saída divergente para fazê-la passar.

Preserve posições, rótulos, codificação de fonte, ordem/quantidade das colunas e
quebras de página. Não rasterize o PDF durante a anonimização: isso mudaria o tipo
do documento. Dados pessoais e credenciais devem ser removidos de texto, metadados,
anexos e camadas ocultas, preservando a estrutura relevante. Não envie régua bruta.

## Complementos para homologar leitores operacionais na Fase 3

- Preserve pelo menos duas páginas adjacentes com um boleto continuado e outro
  boleto distinto. Para Habita, inclua também variações de bloco/DEP/unidade; para
  FL, torres/blocos e notas entre boletos. Prefira os relatórios completos sanitizados
  quando isso for autorizado, para detectar variações que um recorte omite.
- `habita_tree.canonico.esperado.json` e `fl_plaza.canonico.esperado.json`:
  `LoteCanonico` revisado manualmente, com unidades, boletos, composição assinada,
  vencimento/competência, apontamentos e todas as referências de origem/hash.
  Um boleto continuado deve constar uma única vez, com múltiplas origens.
- Cadastro Geral do Plaza sanitizado, se houver aceite de enriquecimento: mantenha
  as mesmas chaves sintéticas condomínio/torre/unidade e datas entre todos os arquivos.
- XLSX por blocos A–G sanitizados, quando utilizados como fonte de conferência,
  com mesmos identificadores e valores sintéticos coerentes com o PDF/gabarito.

Os JSONs `resultados/*.canonico.obtido.json` serão produzidos pelos futuros leitores;
não são gerados pelo reconhecimento. O comparador já valida o contrato canônico e
detecta campos divergentes, somas inválidas, origem ausente e duplicação de boleto.
Isso prepara os testes operacionais. Os leitores adicionados no laboratório
implementam apenas as gramáticas do pacote sintético, ainda não homologadas.

## Comparação local, sem imprimir conteúdo dos documentos

```bash
.venv/bin/python tests/homologacao/runner.py \
  --manifesto tests/fixtures/sanitized/manifesto.local.json \
  --raiz tests/fixtures/sanitized --etapa reconhecimento \
  --dados private/catalogo --assinaturas private/assinaturas.json
```

Antes de executar, importe `catalogo.homologacao.json` no repositório JSON protegido
usando a CLI de configuração, e use `assinaturas.homologacao.json` no argumento
`--assinaturas` (ou sua cópia protegida `private/assinaturas.json`). Nunca promova
os exemplos sintéticos para essa configuração como se tivessem sido homologados.

Fase 3, somente depois de gerar os resultados por leitores autorizados:

```bash
.venv/bin/python tests/homologacao/runner.py \
  --manifesto tests/fixtures/sanitized/manifesto.local.json \
  --raiz tests/fixtures/sanitized --etapa contrato-canonico
```

Status 0 significa comparação aprovada para os casos fornecidos, 1 divergência e
2 material ausente/inválido. O comando não altera aprovação de formatos, assinaturas
ou regras. Seleção e revisão da representatividade continuam necessárias. Não foi
executada comparação com amostras reais nesta entrega. Não há testes pulados por
falta de amostra: a suíte regular é sintética; esses comandos são uma validação
separada, a executar quando o material autorizado estiver disponível.
