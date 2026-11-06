'use strict';
const $=id=>document.getElementById(id);
let csrf='',ctx=null,config=null,current=null,details=null,identifying=null,version=0,expiry=null;
let proposals=[],visibleBills=100,visiblePreview=50,visibleUnits=100;
function node(tag,text,className){const n=document.createElement(tag);n.textContent=text??'';if(className)n.className=className;return n;}
async function api(path,opts={}){
  const headers=new Headers(opts.headers||{});if(csrf)headers.set('X-CSRF-Token',csrf);
  const response=await fetch(path,{...opts,headers,credentials:'same-origin',cache:'no-store'});
  if(!response.ok){let data={};try{data=await response.json();}catch{}const messages={CONTEXTO_INDISPONIVEL:'Identifique novamente o relatório para continuar.',CONFIGURACAO_ALTERADA_RECARREGUE:'A configuração mudou. Clique em Recarregar configuração antes de salvar.',CSRF_INVALIDO:'A sessão precisa ser renovada. Recarregue a página.',SESSAO_ENCERRADA:'Sessão encerrada. Recarregue a página.',DOCUMENTO_ALTERADO_IDENTIFIQUE_NOVAMENTE:'O arquivo mudou. Identifique novamente o relatório.',IDENTIDADE_CONFLITANTE:'A identidade do documento conflita com o condomínio escolhido.',DOCUMENTO_NAO_IDENTIFICADO_COM_SEGURANCA:'Não foi possível comprovar o formato e a identidade. Confira o relatório.',DOCUMENTO_NAO_CONVERTIDO_COM_SEGURANCA:'Documento não convertido. Confira formato, fechamento e evidências.',RESULTADO_INDISPONIVEL:'O resultado expirou, foi descartado ou pertence a outra sessão.',PARAMETROS_INVALIDOS:'Confira os campos e seus formatos antes de salvar.'};const e=new Error(data.mensagem||messages[data.detail]||'Não foi possível concluir. Confira o documento e tente novamente.');e.data=data;e.status=response.status;throw e;}return response;
}
function error(e){$('erro').textContent=e.message||'Falha local. Tente novamente.';$('erro').hidden=false;}
function clearResult(message='Sua análise aparecerá aqui.'){
  clearTimeout(expiry);current=null;details=null;$('resultado').hidden=true;$('vazio').hidden=false;
  for(const id of ['linhas','previa-linhas','previa-cabecalho','resumo','avisos','detalhes-legiveis','json-detalhes','revisao-cadastral-lista'])$(id).replaceChildren();
  $('detalhes').close();$('revisao-cadastral').hidden=true;$('contexto').textContent=message;
}
function clearContext(){ctx=config=null;proposals=[];$('endereco-campos').disabled=true;$('mapeamento-campos').disabled=true;$('endereco-condominio').value='';$('vinculos-lista').replaceChildren();$('unidades-lista').replaceChildren();$('endereco-cadastro-resumo').textContent='Identifique o relatório para configurar';}
function showConfig(data){
  ctx=data.contexto;config=data;proposals=data.mapeamentos.map(({bloco,codigo})=>({bloco,codigo}));
  $('endereco-campos').disabled=false;$('mapeamento-campos').disabled=false;$('endereco-condominio').value=`${data.administradora} · ${data.nome}`;
  $('endereco-cadastro-resumo').textContent=`${data.nome} · revisão ${data.revisao} · nesta sessão`;
  for(const name of ['logradouro','numero','cep','bairro','cidade','uf'])$(`endereco-${name}`).value=data.endereco?.[name]||'';
  $('vinculos-lista').replaceChildren();for(const m of data.mapeamentos)$('vinculos-lista').append(node('div',`${m.bloco||'(sem bloco)'} → ${m.codigo}: ${m.estado}${m.aplicado?' · formato já documentado':' · não aplicado'}`,`config-item ${m.estado}`));
  $('vinculos-status').textContent=data.limite;visibleUnits=100;renderUnits();
}
function renderUnits(){
  $('unidades-lista').replaceChildren();for(const u of (config?.unidades||[]).slice(0,visibleUnits))$('unidades-lista').append(node('div',`${u.bloco?u.bloco+' / ':''}${u.unidade} → ${u.cedente||'aguarda comprovação'} · ${u.estado}`,`config-item ${u.estado}`));
  $('mais-unidades').hidden=(config?.unidades.length||0)<=visibleUnits;
}
async function identify(choice='auto'){
  await sessionReady;
  const file=$('inadimplencia').files[0];clearContext();$('confirmacao').hidden=true;const ticket=++version;
  if(!file){$('identidade').textContent='O condomínio será identificado pelo documento.';return;}
  $('identidade').textContent='Conferindo estrutura e identidade do documento…';
  const data=new FormData();data.append('inadimplencia',file);data.append('condominio',choice);
  try{const r=await(await api('/api/identificar',{method:'POST',body:data})).json();if(ticket!==version)return;showConfig(r);$('identidade').textContent=`Identificado para diagnóstico: ${r.administradora} · ${r.nome}`;}
  catch(e){if(ticket!==version)return;$('identidade').textContent='Identidade ainda não comprovada.';if(e.data?.confirmacao_necessaria){$('confirmacao').hidden=false;$('confirmacao-texto').textContent=e.message;$('confirmacao-opcoes').replaceChildren();for(const p of e.data.candidatos){const b=node('button',`Confirmar ${p.nome}`,'secundario');b.type='button';b.onclick=()=>{identifying=identify(p.id);};$('confirmacao-opcoes').append(b);}}else error(e);}
}
async function saveConfig(address){
  if(!ctx)throw new Error('Identifique o condomínio antes de configurar.');
  const data={revisao_esperada:config.revisao,endereco:address,mapeamentos:proposals};
  const saved=await(await api(`/api/contextos/${ctx}/configuracao`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json();showConfig(saved);return saved;
}
$('cadastro-condominio-form').onsubmit=async e=>{e.preventDefault();try{const address={};for(const n of ['logradouro','numero','cep','bairro','cidade','uf'])address[n]=$(`endereco-${n}`).value.trim();address.cep=address.cep.replace('-','');await saveConfig(address);$('endereco-cadastro-status').textContent='Endereço salvo nesta sessão. Será aplicado somente ao condomínio identificado; reanalise para atualizar um resultado existente.';}catch(e){$('endereco-cadastro-status').textContent=e.message;}};
$('mapeamento-form').onsubmit=async e=>{e.preventDefault();const old=[...proposals];try{const item={bloco:$('map-bloco').value.trim(),codigo:$('map-codigo').value.trim()};proposals=proposals.filter(m=>m.bloco!==item.bloco);proposals.push(item);await saveConfig(config.endereco);$('map-codigo').value='';}catch(e){proposals=old;$('vinculos-status').textContent=e.message;}};
$('recarregar-endereco').onclick=async()=>{try{showConfig(await(await api(`/api/contextos/${ctx}/configuracao`)).json());$('endereco-cadastro-status').textContent='Configuração atual recarregada.';}catch(e){$('endereco-cadastro-status').textContent=e.message;}};
$('mais-unidades').onclick=()=>{visibleUnits+=100;renderUnits();};
$('inadimplencia').onchange=()=>{identifying=identify();};
function unitLabel(id){const u=details?.codificacao_template?.unidades?.[id];return u?`${u.bloco_original?u.bloco_original+' / ':''}${u.unidade_original}`:id;}
function money(value){const [whole,cents='00']=String(value).split('.');return 'R$ '+whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+','+cents.padEnd(2,'0');}
function brDate(s){return s?s.split('-').reverse().join('/'):'';}
function renderBills(){
  if(!details)return;const q=$('busca').value.toLocaleLowerCase('pt-BR'),filter=$('filtro').value;
  const items=details.decisoes.filter(d=>(filter==='todas'||(filter==='excluido'?d.situacao_financeira==='excluido':d.situacao===filter))&&`${unitLabel(d.unidade_id)} ${d.id} ${d.boleto}`.toLocaleLowerCase('pt-BR').includes(q));
  $('linhas').replaceChildren();for(const d of items.slice(0,visibleBills)){
    const row=document.createElement('tr');for(const value of [unitLabel(d.unidade_id),`${/(?:^|:)[a-f0-9]{64}$/.test(d.boleto||'')?(details.boletos[d.id]?.composicao?.itens?.[0]?.descricao_original||'Lançamento da fonte'):d.boleto||'Lançamento'} · ${brDate(d.vencimento)}`,money(d.valor),d.situacao_financeira==='elegivel_na_simulacao'?'Elegível pela régua':d.situacao_financeira==='excluido'?'Não elegível':'Em revisão',d.situacao==='elegivel'?'No Excel':d.situacao==='nao_elegivel'?'Fora da seleção':'Retida para revisão',(d.bloqueios||[]).length?'Pendência documental — confira os detalhes':({prazo_nao_atingido:'Prazo não atingido',prazo_satisfeito:'Prazo satisfeito',veto_coletivo:'Veto da unidade',valor_original_zero:'Original sem valor de dívida'}[d.motivo_selecao]||'Conferir detalhes')])row.append(node('td',value));
    const cell=document.createElement('td'),button=node('button','Detalhes','secundario');button.onclick=()=>showBill(d);cell.append(button);row.append(cell);$('linhas').append(row);
  }
  $('contagem').textContent=`${Math.min(visibleBills,items.length)} de ${items.length} boletos neste filtro.`;$('mais-boletos').hidden=items.length<=visibleBills;$('linhas').closest('.table-wrap').scrollLeft=0;
}
function showBill(d){
  const b=details.boletos[d.id];$('detalhes-legiveis').replaceChildren(node('p',`Unidade ${unitLabel(d.unidade_id)} · vencimento ${brDate(d.vencimento)}`),node('p',`Original: ${money(d.valor)} · ${d.situacao_financeira} · resultado: ${d.situacao}`));
  for(const item of b?.composicao?.itens||[])$('detalhes-legiveis').append(node('p',`${item.descricao_original||item.codigo}: ${item.valor}`));
  $('json-detalhes').textContent=JSON.stringify({decisao:d,boleto:b},null,2);$('detalhes').showModal();
}
function renderPreview(){
  const p=details?.previa_template;if(!p)return;$('previa-cabecalho').replaceChildren();const header=document.createElement('tr');for(const c of ['Situação',...p.colunas])header.append(node('th',c));$('previa-cabecalho').append(header);$('previa-linhas').replaceChildren();
  for(const line of p.linhas.slice(0,visiblePreview)){const row=document.createElement('tr');row.append(node('td',line.bloqueada?'Retida: '+line.motivos.join(', '):'Apta para diagnóstico'));for(const v of line.valores||Array(30).fill('Indisponível por conflito'))row.append(node('td',v??''));$('previa-linhas').append(row);}
  $('mais-previa').hidden=p.linhas.length<=visiblePreview;
}
async function convert(demo=false){
  await sessionReady;
  $('erro').hidden=true;let body=new FormData();
  if(demo){$('data-ref').value='2026-10-21';body.append('data_ref','2026-10-21');body.append('modo',document.querySelector('[name=modo]:checked').value);}
  else{
    if(identifying)await identifying;if(!ctx){error(new Error('Confirme a identidade do condomínio antes de analisar.'));return;}
    for(const role of ['inadimplencia','cadastro','referencia'])if($(role).files[0])body.append(role,$(role).files[0]);
    body.append('data_ref',$('data-ref').value);body.append('modo',document.querySelector('[name=modo]:checked').value);body.append('condominio',config.perfil);body.append('contexto',ctx);
  }
  if(current){try{await api(`/api/conversoes/${current.id}`,{method:'DELETE'});}catch{}clearResult();}
  $('progresso').hidden=false;$('vazio').hidden=true;$('analisar').disabled=true;$('demo').disabled=true;
  try{
    current=await(await api(demo?'/api/exemplo':'/api/conversoes',{method:'POST',body})).json();
    details=await(await api(`/api/conversoes/${current.id}/detalhes`)).json();$('resultado').hidden=false;$('contexto').textContent=`${current.administradora} · ${current.condominio} · ${brDate(current.data_ref)} · modo ${current.modo}`;
    $('resumo').replaceChildren();for(const [key,label] of [['unidades','Unidades'],['boletos','Boletos'],['elegiveis_pela_regua','Elegíveis pela régua'],['dividas_efetivamente_geradas','Dívidas no Excel']]){const card=node('div','', 'indicador');card.append(node('strong',current.resumo[key]),node('span',label));$('resumo').append(card);}
    $('avisos').textContent='Excel diagnóstico de 30 colunas. Sem cobrança ou importação operacional. Prévia e resultado expiram em até 15 minutos e são descartados após o download. Nenhuma associação pessoal é presumida.';
    const cadastroAtual=current['cadastro_'+current.perfil];
    const revisaoAtual=current['revisao_cadastral_'+current.perfil]||[];
    if(cadastroAtual?.fornecido){const card=node('div','','indicador');card.append(node('strong',cadastroAtual.associacoes_retidas),node('span','Associações cadastrais retidas'));$('resumo').append(card);}
    if(cadastroAtual?.associacoes_retidas)$('avisos').textContent+=` ${cadastroAtual.associacoes_retidas} associações cadastrais retidas, sem excluir dívidas elegíveis.`;
    if(cadastroAtual?.documentos_rejeitados_no_cadastro)$('avisos').textContent+=` ${cadastroAtual.documentos_rejeitados_no_cadastro} documentos inválidos ou malformados no cadastro recebido, preservados como evidência temporária e não atribuídos.`;
    if(cadastroAtual?.datas_emissao_cadastro?.length)$('avisos').textContent+=` Cadastro emitido em ${cadastroAtual.datas_emissao_cadastro.map(brDate).join(', ')}; documentos e contatos exigem comprovação da identidade atual.`;
    $('revisao-cadastral').hidden=!revisaoAtual.length;$('revisao-cadastral-lista').replaceChildren();
    const motivosCadastro={OMA_DOCUMENTO_AUSENTE_OU_INVALIDO_ASSOCIACAO_RETIDA:'Documento ausente ou inválido; associação pessoal retida',PASSAREDO_RESPONSAVEL_DIVERGENTE_CADASTRO:'Nomes divergentes',PASSAREDO_RESPONSAVEL_MULTIPLO_DOCUMENTO_RETIDO:'Multiplicidade sem vínculo documental suficiente',PASSAREDO_DOCUMENTOS_CONFLITANTES_CADASTRO:'Documentos conflitantes'};
    for(const item of revisaoAtual)$('revisao-cadastral-lista').append(node('p',`Unidade ${item.unidade} · inadimplência: ${item.responsavel_inadimplencia} · cadastro: ${item.responsavel_cadastro} · ${item.lancamentos} lançamento(s) · ${motivosCadastro[item.motivo]||'Revisão documental'}.`));
    visibleBills=100;visiblePreview=50;renderBills();renderPreview();$('download').disabled=!current.arquivo_teste_disponivel;
    expiry=setTimeout(()=>discard('Resultado expirado e descartado.'),current.retencao_segundos*1000);
  }catch(e){error(e);}finally{$('progresso').hidden=true;$('analisar').disabled=false;$('demo').disabled=false;}
}
async function discard(message='Análise descartada.'){if(current){try{const r=await(await api(`/api/conversoes/${current.id}`,{method:'DELETE'})).json();if(r.descarte_pendente_de_resposta)message='Descarte solicitado; respostas em andamento ainda precisam liberar seus recursos.';}catch(e){if(e.status!==404)message='Prévia local fechada. Não foi possível confirmar o descarte no servidor; o prazo de expiração continua ativo.';}}clearResult(message);}
$('converter').onsubmit=e=>{e.preventDefault();convert();};$('demo').onclick=()=>convert(true);
$('filtro').onchange=$('busca').oninput=()=>{visibleBills=100;renderBills();};$('mais-boletos').onclick=()=>{visibleBills+=100;renderBills();};$('mais-previa').onclick=()=>{visiblePreview+=50;renderPreview();};$('fechar').onclick=()=>$('detalhes').close();$('descartar').onclick=()=>discard();
$('download').onclick=async()=>{if(!current)return;try{const r=await api(`/api/conversoes/${current.id}/excel`),blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='DIAGNOSTICO_NAO_IMPORTAR.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),0);clearResult('Download recebido. Prévia local encerrada; o servidor descarta ao terminar as respostas em andamento.');for(const name of ['inadimplencia','cadastro','referencia'])$(name).value='';clearContext();}catch(e){error(e);}};
$('sair').onclick=async()=>{try{await api('/api/sessao',{method:'DELETE'});location.reload();}catch(e){error(e);}};
const sessionReady=(async()=>{try{const r=await(await api('/api/sessao')).json();csrf=r.csrf;}catch(e){error(new Error('Sessão encerrada. Recarregue a página para iniciar outra sessão local.'));}})();
