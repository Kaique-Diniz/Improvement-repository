const $ = id => document.getElementById(id);
let atual = null, aguardando = false, revisaoSelecao = 0;
let catalogoCondominios=[], enderecoVersao=null, enderecoRevisao=0, carregandoEndereco=false, salvandoEndereco=false;
const camposEndereco=['logradouro','numero','cep','bairro','cidade','uf'];
const arquivos = ['inadimplencia','cadastro','referencia'];
const financeiro = {elegivel_na_simulacao:'Elegível por regra',excluido:'Não elegível por regra',pendente_revisao:'Indeterminada',bloqueado:'Bloqueada'};
const nomes = {elegivel:'Elegível na prévia',nao_elegivel:'Não elegível',revisao:'Revisão necessária'};
async function api(url, options={}) {
  const r = await fetch(url, options);
  const data = await r.json();
  if (!r.ok) {
    if (r.status===401) { $('login').hidden=false; $('app').hidden=true; }
    throw new Error(data.detail || 'Falha na comunicação com o servidor.');
  }
  return data;
}
function elemento(tag,text,cls) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
function atualizarArquivo(id) {
  const arquivo=$(id).files[0], nome=$(id+'-nome');
  nome.textContent=arquivo?arquivo.name:'Nenhum arquivo selecionado';nome.title=arquivo?arquivo.name:'';
  $('remover-'+id).hidden=!arquivo;
}
function limparResultado() {
  atual=null;$('resultado').hidden=true;$('erro').hidden=true;$('progresso').hidden=true;$('vazio').hidden=false;
  for(const id of ['download','inconsistencias','manifesto']) { $(id).hidden=true;$(id).removeAttribute('href'); }
  $('fechamento-global').hidden=true;$('fechamento-global').replaceChildren();
  $('endereco-resultado').replaceChildren();
  for(const id of ['linhas','grupos-cotas','previa-linhas','previa-cabecalho','resumo','avisos','comparacao','detalhes-legiveis','json-detalhes'])$(id).replaceChildren();
  $('cotas-agrupadas').open=false;
  $('previa-template').open=false;
  if($('detalhes').open)$('detalhes').close();
  $('contexto').textContent='Sua análise aparecerá aqui.';
}
function selecaoAlterada(e) {
  const anterior=!!atual;revisaoSelecao++;limparResultado();
  if(arquivos.includes(e.target.id))atualizarArquivo(e.target.id);
  let aviso=anterior||!$('selecao-aviso').hidden?'Seleção alterada. Faça uma nova análise para atualizar a prévia e os downloads.':'';
  if(!$('inadimplencia').files.length)aviso='Selecione um PDF de inadimplência para iniciar uma nova análise.';
  else if(e.target.id==='inadimplencia'&&($('cadastro').files.length||$('referencia').files.length))aviso='PDF alterado. Confira se o Cadastro e a referência ainda selecionados pertencem ao mesmo condomínio. Remova os anteriores pelo × e faça uma nova análise.';
  $('selecao-aviso').textContent=aviso;$('selecao-aviso').hidden=!aviso;
}
for(const id of arquivos) {
  atualizarArquivo(id);
  $('remover-'+id).onclick=()=>{$(id).value='';$(id).dispatchEvent(new Event('change',{bubbles:true}));$(id).focus();};
}
$('converter').addEventListener('change',selecaoAlterada);
function bloquear(b) {
  aguardando=b;document.querySelectorAll('#app button').forEach(x=>x.disabled=b||x.hasAttribute('data-sempre-desativado'));
  document.querySelectorAll('#converter input,#converter select,#cadastro-condominio-form input,#cadastro-condominio-form select').forEach(x=>x.disabled=b);
  $('salvar-endereco').disabled=b||carregandoEndereco||salvandoEndereco||enderecoVersao===null;
}
function falhar(e) {
  const mensagem=e.message==='CADASTRO_DE_OUTRO_CONDOMINIO'?'O Cadastro complementar pertence a outro condomínio. Remova-o pelo × ou selecione o cadastro correspondente ao PDF de inadimplência.':e.message;
  $('progresso').hidden=true;$('erro').hidden=false;$('erro').textContent='Análise interrompida: '+mensagem+(mensagem.endsWith('.')?'':'.')+' Confira os arquivos e os parâmetros.';bloquear(false);
}
async function configurar() {
  const c=await api('/api/config'); $('login').hidden=true; $('app').hidden=false; $('sair').hidden=false;
  $('casos').replaceChildren();
  for(const caso of c.fontes_privadas) { const b=elemento('button',caso.nome,'secundario');b.type='button';b.onclick=()=>executar('privado',caso.id);$('casos').append(b); }
  $('fontes-privadas').hidden=!c.fontes_privadas.length;
  catalogoCondominios=c.condominios;
  const admins=[...new Map(c.condominios.map(p=>[p.administradora_id,p.administradora])).entries()];
  $('endereco-administradora').replaceChildren(...admins.map(([id,nome])=>new Option(nome,id)));
  await selecionarCondominioEndereco();
}

function endpointEndereco(){return '/api/condominios/'+encodeURIComponent($('endereco-administradora').value)+'/'+encodeURIComponent($('endereco-condominio').value)+'/endereco';}
async function selecionarCondominioEndereco(condominioId) {
  const ps=catalogoCondominios.filter(p=>p.administradora_id===$('endereco-administradora').value);
  $('endereco-condominio').replaceChildren(...ps.map(p=>new Option(p.nome,p.condominio_id)));
  if(condominioId)$('endereco-condominio').value=condominioId;
  await carregarEndereco();
}
async function carregarEndereco() {
  const revisao=++enderecoRevisao;carregandoEndereco=true;enderecoVersao=null;$('salvar-endereco').disabled=true;
  camposEndereco.forEach(k=>{$('endereco-'+k).value='';$('endereco-'+k).disabled=true;});
  $('endereco-cadastro-status').textContent='Consultando endereço…';
  try {
    const d=await api(endpointEndereco());if(revisao!==enderecoRevisao)return;
    enderecoVersao=d.versao;camposEndereco.forEach(k=>$('endereco-'+k).value=d.endereco[k]||'');
    const fonte=d.origem==='perfil_privado_existente'?'Configuração privada existente; será preservada.':d.cadastrado?'Fornecido pelo usuário · versão '+d.versao+' · '+new Date(d.atualizado_em).toLocaleString('pt-BR'): 'Endereço não cadastrado';
    $('endereco-cadastro-status').textContent=fonte;$('endereco-cadastro-resumo').textContent=d.condominio+' · '+(d.cadastrado?'Endereço cadastrado':'Endereço não cadastrado');
  } catch(e){if(revisao===enderecoRevisao)$('endereco-cadastro-status').textContent='Não foi possível consultar o cadastro. Recarregue antes de salvar.';}
  finally {if(revisao===enderecoRevisao){carregandoEndereco=false;camposEndereco.forEach(k=>$('endereco-'+k).disabled=aguardando);$('salvar-endereco').disabled=aguardando||salvandoEndereco||enderecoVersao===null;}}
}
$('endereco-administradora').onchange=()=>selecionarCondominioEndereco();
$('endereco-condominio').onchange=()=>carregarEndereco();
$('recarregar-endereco').onclick=()=>carregarEndereco();
$('endereco-uf').oninput=()=>{$('endereco-uf').value=$('endereco-uf').value.toUpperCase();};
$('cadastro-condominio-form').addEventListener('submit',async e=>{
  e.preventDefault();if(aguardando||carregandoEndereco||salvandoEndereco||enderecoVersao===null)return;
  const admin=$('endereco-administradora').value,cond=$('endereco-condominio').value;
  const endereco=Object.fromEntries(camposEndereco.map(k=>[k,$('endereco-'+k).value.trim()]));endereco.cep=endereco.cep.replace(/[^0-9]/g,'');
  salvandoEndereco=true;bloquear(true);$('endereco-cadastro-status').textContent='Salvando endereço…';
  try {
    const d=await api(endpointEndereco(),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({endereco,versao_esperada:enderecoVersao})});
    enderecoVersao=d.versao;$('endereco-cadastro-status').textContent='Endereço salvo · versão '+d.versao+'. Será usado nas próximas análises.';
    $('endereco-cadastro-resumo').textContent=d.condominio+' · Endereço cadastrado';
    if(atual?.administradora_id===admin&&atual?.condominio_id===cond){revisaoSelecao++;limparResultado();$('selecao-aviso').hidden=false;$('selecao-aviso').textContent='Endereço atualizado. Faça uma nova análise para gerar a prévia e os downloads com o cadastro atual.';}
  }catch(err){
    const conflito=err.message==='ENDERECO_ALTERADO_POR_OUTRA_SESSAO';
    $('endereco-cadastro-status').textContent=conflito?'Outra sessão atualizou este endereço. Recarregue o cadastro antes de editar novamente.':'Não foi possível salvar. Confira os campos e recarregue o cadastro.';
    if(conflito)enderecoVersao=null;
  }finally{salvandoEndereco=false;bloquear(false);}
});
$('login-form').addEventListener('submit',async e=>{e.preventDefault();try{await api('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chave:$('chave').value})});$('chave').value='';$('login-error').textContent='';await configurar();}catch(err){$('login-error').textContent=err.message;}});
$('sair').onclick=async()=>{await api('/api/session',{method:'DELETE'});location.reload();};
async function executar(tipo,id) {
  if(aguardando)return;
  if(tipo==='demo'&&!$('data-ref').value) $('data-ref').value='2026-10-21';
  if(tipo==='demo'&&!document.querySelector('input[name="modo"]:checked'))document.querySelector('input[name="modo"][value="B"]').checked=true;
  const modo=document.querySelector('input[name="modo"]:checked');
  if(!$('data-ref').value||!modo) { $('erro').hidden=false;$('erro').textContent='Selecione a data de referência e o modo A ou B.';return; }
  if(tipo==='upload'&&!$('inadimplencia').files.length) { $('erro').hidden=false;$('erro').textContent='Envie o PDF de inadimplência.';return; }
  const f=new FormData();f.append('data_ref',$('data-ref').value);f.append('modo',modo.value);
  let endpoint='/api/exemplo';
  if(tipo==='privado')endpoint='/api/fontes-privadas/'+encodeURIComponent(id)+'/processar';
  if(tipo==='upload') { endpoint='/api/processamentos'; f.append('condominio',$('condominio').value); for(const role of ['inadimplencia','cadastro','referencia'])if($(role).files.length)f.append(role,$(role).files[0]); }
  const revisao=revisaoSelecao;
  limparResultado();$('selecao-aviso').hidden=true;bloquear(true);$('vazio').hidden=true;$('progresso').hidden=false;$('etapa').textContent='Recebendo documentos…';
  try { const j=await api(endpoint,{method:'POST',body:f}); await acompanhar(j.id,revisao); }catch(e){if(revisao===revisaoSelecao)falhar(e);else bloquear(false);}
}
$('converter').addEventListener('submit',e=>{e.preventDefault();executar('upload');});$('demo').onclick=()=>executar('demo');
async function acompanhar(id,revisao) {
  const j=await api('/api/processamentos/'+id);
  if(revisao!==revisaoSelecao){bloquear(false);return;}
  if(j.estado==='erro')throw new Error(j.codigo);
  if(j.estado==='processando') { $('etapa').textContent=j.etapa||'Iniciando extração…';await new Promise(r=>setTimeout(r,650));return acompanhar(id,revisao); }
  atual=j.resultado;mostrar();bloquear(false);
}
function mostrar() {
  const r=atual;$('progresso').hidden=true;$('resultado').hidden=false;
  $('contexto').textContent=r.administradora+' · '+r.condominio+' · Referência '+r.data_ref.split('-').reverse().join('/')+' · Modo '+r.modo+(r.origem_execucao==='exemplo_sintetico'?' · EXEMPLO SINTÉTICO':' · DIAGNÓSTICO PRIVADO');
  const stats=[['Unidades / cotas',r.resumo.cotas],['Boletos extraídos',r.resumo.boletos],['Cotas elegíveis pela régua',r.resumo.cotas_elegiveis_pela_regua],['Cotas excluídas por veto coletivo',r.resumo.cotas_excluidas_por_veto],['Boletos selecionados pela régua',r.resumo.boletos_selecionados_pela_regua],['Boletos fora do prazo',r.resumo.boletos_nao_selecionados_prazo],['Cotas retidas tecnicamente',r.resumo.cotas_retidas],['Boletos retidos tecnicamente',r.resumo.boletos_retidos],['Cadastros adicionais',r.resumo.cadastros_adicionais]];
  if(r.resumo.indeterminadas_pela_regua)stats.push(['Boletos indeterminados pela régua',r.resumo.indeterminadas_pela_regua]);
  stats.push(['Dívidas disponíveis só para teste',r.resumo.dividas_efetivamente_geradas]);
  $('resumo').replaceChildren(...stats.map(([label,n])=>{const d=elemento('div',undefined,'metrica');d.append(elemento('span',label),elemento('strong',String(n)));return d;}));
  $('avisos').replaceChildren(...r.avisos.map(x=>elemento('p',x)));
  const endereco=r.endereco_condominio;
  $('endereco-resultado').replaceChildren(elemento('p',endereco?.cadastrado?'Endereço do condomínio cadastrado; origem e configuração registradas na auditoria.':'Endereço não cadastrado. O diagnóstico pode continuar normalmente.'));
  const cadastrar=elemento('button',endereco?.cadastrado?'Conferir endereço do condomínio':'Cadastrar endereço','secundario');cadastrar.type='button';
  cadastrar.onclick=async()=>{$('endereco-administradora').value=r.administradora_id;await selecionarCondominioEndereco(r.condominio_id);$('cadastro-condominios').open=true;$('cadastro-condominios').scrollIntoView({behavior:'smooth'});$('endereco-logradouro').focus();};
  $('endereco-resultado').append(cadastrar);
  const reconciliado=r.fechamento_habita?.estado==='reconciliado_somente_diagnostico';
  $('fechamento-global').hidden=!r.fechamento_habita||r.fechamento_habita.estado==='nao_aplicavel';
  if(reconciliado)$('fechamento-global').replaceChildren(elemento('strong','Habita/VG · Anomalia global de fechamento reconciliado'),elemento('p','O subtotal impresso repete o total geral e diverge do VG calculado. Todos os lançamentos e o total geral foram conferidos. A ocorrência crítica original permanece na auditoria. A dispensa vale somente para XLSX diagnóstico; não representa problema individual dos boletos nem liberação operacional. Confira o manifesto.'));
  else if(r.fechamento_habita?.estado==='nao_reconciliado')$('fechamento-global').replaceChildren(elemento('strong','Fechamento global não reconciliado · Lote retido'),elemento('p','A divergência de subtotal não atende às condições da dispensa diagnóstica. É uma retenção global; não significa que cada boleto tenha um erro individual. Consulte o relatório e o manifesto.'));
  const historicos={nao_disponivel:'Sem histórico anterior (informativo)',carregado:'Histórico anterior carregado',vazio_inventariado:'Histórico conferido sem ocorrências anteriores',divergente:'Histórico conhecido ausente ou divergente: revisão necessária',exemplo_sintetico:'Exemplo sintético'};
  $('historico-tecnico').textContent=(historicos[r.historico_tecnico.estado]||r.historico_tecnico.estado)+' · '+r.historico_tecnico.aviso;
  if(r.resumo.boletos_retidos) $('avisos').prepend(elemento('p','Há boletos retidos tecnicamente, inclusive os selecionados pela régua. Um veto financeiro e um impedimento técnico são situações distintas; os bloqueios continuam preservados.'));
  $('download').hidden=!r.arquivo_teste_disponivel;$('download').href='/api/processamentos/'+r.id+'/arquivo-teste.xlsx';$('sem-excel').hidden=r.arquivo_teste_disponivel;
  $('inconsistencias').hidden=false;$('inconsistencias').href='/api/processamentos/'+r.id+'/inconsistencias.json';
  $('manifesto').hidden=false;$('manifesto').href='/api/processamentos/'+r.id+'/manifesto-diagnostico.json';
  $('comparacao').hidden=!r.comparacao;
  if(r.comparacao){$('comparacao').replaceChildren(elemento('h3','Confronto com a referência'),elemento('p','A referência é um resultado esperado, não um gabarito absoluto. Nenhuma diferença altera os dados extraídos.'),elemento('pre',JSON.stringify(r.comparacao.resumo,null,2)),elemento('p',r.comparacao.limite));}
  desenharTabela();mostrarCotas();mostrarPrevia();
}
function mostrarCotas() {
  const estados={elegivel:'Com boletos selecionados pela régua',excluida_por_veto:'Excluída por veto coletivo',sem_boleto_no_prazo:'Sem boleto no prazo',pendente_revisao:'Avaliação financeira inconclusiva'};
  const decisoes=new Map(atual.decisoes.map(d=>[d.id,d]));
  $('grupos-cotas').replaceChildren(...atual.cotas.map(c=>{
    const grupo=elemento('details',undefined,'cota-grupo');
    grupo.append(elemento('summary',c.bloco+'/'+c.unidade+' · '+c.boletos_ids.length+' boletos · '+estados[c.situacao_financeira]+(c.retida_tecnicamente?' · Retida tecnicamente':'')));
    for(const causa of c.causas_veto)grupo.append(elemento('p','Boleto '+causa.boleto+' vetou toda a cota: '+motivoLegivel(causa.regra_id)+' · '+causa.origens.map(o=>'página '+o.pagina+', linha '+o.linha).join('; ')));
    if(c.impedimentos_tecnicos.length)grupo.append(elemento('p','Retenção técnica: '+c.impedimentos_tecnicos.map(motivoLegivel).join('; ')));
    for(const id of c.boletos_ids) {
      const d=decisoes.get(id),boleto=elemento('details',undefined,'boleto-grupo'),conteudo=elemento('div');
      boleto.append(elemento('summary','Boleto '+d.boleto+' · '+d.vencimento.split('-').reverse().join('/')+' · R$ '+d.valor+' · '+financeiro[d.situacao_financeira]),conteudo);
      boleto.ontoggle=()=>{if(boleto.open&&!conteudo.childElementCount)preencherDetalhes(d,conteudo);};
      grupo.append(boleto);
    }
    return grupo;
  }));
}
function mostrarPrevia() {
  const p=atual.previa_template,head=elemento('tr');
  for(const label of ['Situação / origem',...p.colunas]) {const th=elemento('th',label);th.scope='col';head.append(th);}
  $('previa-cabecalho').replaceChildren(head);
  $('previa-linhas').replaceChildren(...p.linhas.map(l=>{
    const tr=elemento('tr'),identidade=elemento('td',(l.bloqueada?'RETIDA':'Prévia sem retenção')+' · '+l.tipo+' · '+l.bloco+'/'+l.unidade+(l.cota?' · Boleto '+l.cota:''));
    if(l.numeracao_pendente)identidade.append(elemento('small','Numeração final pendente: linha retida não consome parcela.'));
    if(l.motivos.length)identidade.append(elemento('small',l.motivos.map(motivoLegivel).join('; ')));
    if(!l.valores)identidade.append(elemento('small','Campos indisponíveis até resolução das pendências.'));
    tr.append(identidade,...(l.valores||Array(30).fill('—')).map(v=>elemento('td',String(v))));return tr;
  }));
  $('previa-contagem').textContent=p.linhas.length+' linhas previstas · '+p.linhas.filter(l=>l.bloqueada).length+' retidas · 30 colunas do template, além da identificação de conferência.';
}
function desenharTabela() {
  if(!atual)return;
  const filtro=$('filtro').value,busca=$('busca').value.trim().toLowerCase();
  const ds=atual.decisoes.filter(d=>(filtro==='todas'||d.situacao===filtro)&&(!busca||[d.bloco,d.unidade,d.cota].join(' ').toLowerCase().includes(busca)));
  $('linhas').replaceChildren(...ds.map(d=>{
    const tr=elemento('tr');
    const unidade=elemento('td',d.bloco+' / '+d.unidade);
    const cota=elemento('td',d.cota);cota.append(elemento('small',d.vencimento.split('-').reverse().join('/')));
    const valor=elemento('td',new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(d.valor)));
    const regra=elemento('td',financeiro[d.situacao_financeira]||d.situacao_financeira);
    const contato=elemento('td',contatoLegivel(d));
    if(d.alertas_cadastrais.includes('DIVERGENCIA_NOME_ENTRE_FONTES'))contato.append(elemento('small','Nomes diferentes: contato preferencial do Cadastro, sem retenção por esse motivo.'));
    const documental=elemento('td',d.pendencias_documentais.length?d.pendencias_documentais.map(motivoLegivel).join(' · '):'Sem conflito documental');
    const estado=elemento('td');estado.append(elemento('span',nomes[d.situacao],'status '+d.situacao));
    if(d.apto_xlsx_diagnostico)estado.append(elemento('small','Disponível exclusivamente para XLSX diagnóstico'));
    const motivo=elemento('td',d.motivos.map(motivoLegivel).join(' · ')||'Condições avaliadas','motivo');
    const detalhe=elemento('td');const b=elemento('button','Detalhes','secundario');b.onclick=()=>abrirDetalhes(d);detalhe.append(b);
    tr.append(unidade,cota,valor,regra,contato,documental,estado,motivo,detalhe);return tr;
  }));
  $('contagem').textContent=ds.length+' de '+atual.decisoes.length+' boletos · '+atual.cotas.length+' cotas/unidades · Valores originais, sem recalcular encargos';
}
$('filtro').onchange=desenharTabela;$('busca').oninput=desenharTabela;$('fechar').onclick=()=>$('detalhes').close();
configurar().catch(()=>{});

function motivoLegivel(c) {
  const textos={tree_centavo:'Boleto de original R$ 0,01 na unidade: veto coletivo',tree_apontamento_a:'Apontamento A em boleto da unidade: veto coletivo',tree_apontamento_aj:'Apontamento AJ em boleto da unidade: veto coletivo',tree_apontamento_j:'Apontamento J em boleto da unidade: veto coletivo',tree_prazo_30:'Prazo individual superior a 30 dias; sujeito aos vetos da cota',plaza_prazo_30:'Atraso superior a 30 dias',tree_prazo_30_nao_atingido:'Prazo superior a 30 dias não atingido',plaza_prazo_30_nao_atingido:'Prazo superior a 30 dias não atingido',TELEFONE_SEM_DDD:'Telefone preservado com DDD vazio (informativo)',ENDERECO_DIVERGENTE_PRESERVADO:'Endereço atual divergente preservado; conferir a origem',ENDERECO_PARCIAL_PRESERVADO:'Endereço parcial preservado sem completar com dados incompatíveis',SUBTOTAL_BLOCO_DIVERGENTE:'Subtotal do bloco divergente: lote retido',TITULAR_DIVERGENTE:'Divergência histórica de nomes: conferir reavaliação',MARCADOR_ADMINISTRATIVO_NO_CABECALHO:'Marcador administrativo separado do nome; preservado na auditoria',CONTATO_COMPLEMENTADO_DA_INADIMPLENCIA:'Contato cadastral ausente complementado com a fonte de inadimplência',DIVERGENCIA_NOME_ENTRE_FONTES:'Nomes diferentes entre fontes (informativo); contato do Cadastro Geral preferencial',DOCUMENTOS_CONFLITANTES:'CPF/CNPJ conflitantes: revisão humana',DOCUMENTO_TITULAR_NAO_CONFIRMADO:'Vínculo documental entre registros exige revisão',DOCUMENTO_AUSENTE:'CPF/CNPJ não informado (opcional)',DOCUMENTO_INVALIDO:'CPF/CNPJ inválido: saída em branco com alerta',INVENTARIO_EXTERNO_AUSENTE_OU_DIVERGENTE:'Histórico conhecido não pôde ser validado: revisão necessária',CONDICAO_INDETERMINADA:'Evidência insuficiente para decidir'};
  return textos[c]||c.toLowerCase().replaceAll('_',' ');
}
function contatoLegivel(d) {
  const docs={disponivel:'CPF/CNPJ disponível no registro da unidade',ausente:'CPF/CNPJ não informado (opcional)',invalido:'CPF/CNPJ inválido: ficará vazio',revisao:'CPF/CNPJ em revisão'};
  return (docs[d.contato.documento]||d.contato.documento)+' · Telefone '+(d.contato.telefone?'disponível':'não informado')+' · E-mail '+(d.contato.email?'disponível':'não informado');
}
function preencherDetalhes(d,box) {
  box.replaceChildren();
  box.append(elemento('h3',d.condominio+' · '+d.bloco+' / '+d.unidade),elemento('p','Boleto '+d.boleto+' · Vencimento '+d.vencimento.split('-').reverse().join('/')+' · '+nomes[d.situacao]));
  box.append(elemento('h3','Elegibilidade financeira'),elemento('p',financeiro[d.situacao_financeira]||d.situacao_financeira));
  const rotulo=atual.rotulos_template?.[d.id];
  if(rotulo)box.append(elemento('h3','Rótulo apresentado no template'),elemento('p',rotulo.rotulo+(rotulo.base==='vencimento_apresentacao'?' · Mês/ano do vencimento somente para apresentação; não informa competência.':'')),elemento('p','Identificador original do boleto: '+rotulo.identificador_origem));
  if(d.anomalia_global_reconciliada)box.append(elemento('h3','Anomalia global de fechamento'),elemento('p','Habita/VG integralmente reconciliado para diagnóstico local. Ocorrência original preservada; não é uma pendência individual deste boleto. Não autoriza exportação operacional.'));
  const cota=atual.cotas.find(c=>c.id===d.cota_id);
  if(d.veto_coletivo)for(const c of cota.causas_veto)box.append(elemento('p','Veto coletivo: boleto '+c.boleto+' · '+motivoLegivel(c.regra_id)+' · '+c.origens.map(o=>'página '+o.pagina+', linha '+o.linha).join('; ')));
  box.append(elemento('h3','Informações de contato da unidade'),elemento('p',contatoLegivel(d)));
  for(const m of d.alertas_cadastrais)box.append(elemento('p',motivoLegivel(m)));
  const endereco=atual.enderecos_template?.[d.unidade_id];
  if(endereco?.estado==='endereco_explicito_configurado')box.append(elemento('p','Endereço padrão configurado explicitamente para este condomínio; origem registrada na auditoria.'));
  if(endereco?.alertas?.length){
    box.append(elemento('h3','Conferência do endereço'),elemento('p','Endereço atual preservado sem combinar campos com o padrão.'));
    const padrao=atual.endereco_condominio?.configuracao?.endereco||{};
    for(const k of camposEndereco)if((endereco.endereco_origem?.[k]||'')!==(padrao[k]||''))box.append(elemento('p',k.toUpperCase()+' · Fonte atual: '+(endereco.endereco_origem?.[k]||'não informado')+' · Padrão cadastrado: '+(padrao[k]||'não informado')));
  }
  box.append(elemento('h3','Pendências documentais'),elemento('p',d.pendencias_documentais.length?d.pendencias_documentais.map(motivoLegivel).join('; '):'Sem conflito documental. Vários nomes não atribuem o documento a cada pessoa.'));
  box.append(elemento('h3','Impedimentos para exportação'),elemento('p',d.bloqueios.length?d.bloqueios.map(motivoLegivel).join('; '):'Sem retenção técnica específica deste boleto para a prévia.'));
  box.append(elemento('p','Exportação operacional indisponível em todos os casos.'));
  for(const m of d.motivos)box.append(elemento('p',motivoLegivel(m)));
  box.append(elemento('h3','Composição original'));
  for(const c of d.componentes)box.append(elemento('p',c.descricao_original+' · R$ '+c.valor+' · página '+c.origem.pagina+', linha '+c.origem.linha));
  box.append(elemento('p','Competência: '+(d.competencia||'não informada na fonte; preservada em branco')));
  box.append(elemento('p','Documento: '+(d.documento.estado.length?d.documento.estado.map(motivoLegivel).join('; '):'disponível no registro da unidade, sem atribuição individual')));
}
function abrirDetalhes(d) {
  preencherDetalhes(d,$('detalhes-legiveis'));
  $('json-detalhes').textContent=JSON.stringify({boleto:d,cota:atual.cotas.find(c=>c.id===d.cota_id)},null,2);$('detalhes').showModal();
}
