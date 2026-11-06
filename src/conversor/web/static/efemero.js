'use strict';
const $ = id => document.getElementById(id);
let current = null;
function clearReview() { $('review-items').replaceChildren(); $('review-panel').hidden=true; }
const status = (text, error=false) => { $('status').textContent=text; $('status').classList.toggle('error', error); };
async function api(path, options={}) {
  const response=await fetch(path, {credentials:'same-origin', cache:'no-store', ...options});
  if (!response.ok) {
    let code='FALHA_LOCAL_SEGURA';
    try { code=(await response.json()).detail || code; } catch (_) {}
    if (code==='PASSAREDO_LAYOUT_RECONHECIDO_INFORME_PERFIL') code='Layout Passaredo reconhecido. Selecione o condomínio Passaredo para esta conversão diagnóstica; as colunas e o nome do arquivo não comprovam a identidade.';
    throw new Error(code);
  }
  return response;
}
async function config() {
  const data=await (await api('/api/config')).json();
  $('profile').replaceChildren(new Option('Reconhecer pelo documento','auto'));
  for (const profile of data.perfis) $('profile').add(new Option(`${profile.administradora} · ${profile.nome}`,profile.id));
  $('login-panel').hidden=true; $('conversion-panel').hidden=false;
}
$('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await api('/api/sessao', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chave:$('key').value})});
    $('key').value=''; await config(); status('Acesso liberado. Os documentos desta conversão não serão usados em conversões futuras.');
  } catch (error) { status(error.message,true); }
});
async function convert(demo=false) {
  const form=$('conversion-form');
  if (!demo && !form.reportValidity()) return;
  const data=new FormData(form);
  for (const name of ['inadimplencia','cadastro','referencia']) {
    const file=data.get(name);
    if (demo || !file || !file.size) data.delete(name);
    else if (file.size>20*1024*1024) { status('LIMITE_UPLOAD_EXCEDIDO',true); return; }
  }
  $('convert').disabled=true; $('demo').disabled=true;
  status('Reconhecendo os documentos, aplicando as regras existentes e preparando o Excel…');
  try {
    if (current) { await api(`/api/conversoes/${current.id}`,{method:'DELETE'}); current=null; }
    $('result').hidden=true; clearReview();
    current=await (await api(demo?'/api/exemplo':'/api/conversoes',{method:'POST',body:data})).json();
    $('result-title').textContent=`${current.administradora} · ${current.condominio}`;
    const r=current.resumo;
    $('result-summary').textContent=`Referência ${current.data_ref.split('-').reverse().join('/')} · modo ${current.modo} · ${r.unidades} unidades · ${r.boletos} boletos · ${r.linhas_teste} linhas diagnósticas.`;
    $('download').disabled=!current.arquivo_teste_disponivel;
    $('result-warning').textContent=current.arquivo_teste_disponivel ? 'Excel de 30 colunas para conferência. Não importar no CRM. O resultado expira em até 15 minutos e é descartado após servir o download.' : 'Não há linhas aptas para download. A ausência de evidência documental não foi substituída por uma associação presumida.';
    const cadastroTabular=current.cadastro_passaredo || current.cadastro_forest_hill || current.cadastro_parque_santa_monica || current.cadastro_vero_encanto;
    if (cadastroTabular?.associacoes_retidas) $('result-warning').textContent+=` Há ${cadastroTabular.associacoes_retidas} associações cadastrais retidas para revisão; documentos e contatos não foram transferidos por mera coincidência de unidade.`;
    if (cadastroTabular?.documentos_rejeitados_no_cadastro) $('result-warning').textContent+=` Há ${cadastroTabular.documentos_rejeitados_no_cadastro} documento(s) inválido(s) ou malformado(s) no cadastro recebido. Foram preservados na evidência temporária e não atribuídos a responsáveis.`;
    if (current.identificacao_condominio==='condominio_informado_pelo_usuario') $('result-warning').textContent+=' Condomínio informado pelo usuário para este diagnóstico; isso não autoriza operação.';
    const reviews=current.revisao_cadastral_passaredo || current.revisao_cadastral_forest_hill || current.revisao_cadastral_parque_santa_monica || current.revisao_cadastral_vero_encanto || [];
    $('review-panel').hidden=!reviews.length;
    for (const review of reviews) {
      const item=document.createElement('p');
      item.textContent=`Unidade ${review.unidade} · inadimplência: ${review.responsavel_inadimplencia} · cadastro: ${review.responsavel_cadastro} · ${review.lancamentos} lançamento(s) analisado(s). Documento e contatos retidos para revisão.`;
      $('review-items').append(item);
    }
    $('result').hidden=false;
    for (const input of form.querySelectorAll('input[type=file]')) input.value='';
    status('Conversão concluída. Os arquivos temporários do processamento já foram removidos.');
  } catch (error) { status(error.message,true); }
  finally { $('convert').disabled=false; $('demo').disabled=false; }
}
$('conversion-form').addEventListener('submit',event=>{event.preventDefault();convert();});
$('demo').addEventListener('click',()=>convert(true));
$('download').addEventListener('click',async()=>{
  if (!current) return;
  $('download').disabled=true;
  try {
    const response=await api(`/api/conversoes/${current.id}/excel`);
    const blob=await response.blob(); const url=URL.createObjectURL(blob);
    const link=document.createElement('a');link.href=url;link.download='DIAGNOSTICO_NAO_IMPORTAR.xlsx';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    status('Resposta de download recebida. O resultado foi descartado no servidor; confira a cópia salva pelo navegador.'); current=null; clearReview();
  } catch (error) { status(error.message,true); }
});
$('discard').addEventListener('click',async()=>{
  try {
    let pending=false;
    if (current) pending=(await (await api(`/api/conversoes/${current.id}`,{method:'DELETE'})).json()).descarte_pendente_de_resposta;
    current=null;$('result').hidden=true; clearReview();
    status(pending?'Descarte solicitado. A resposta ativa precisa terminar ou falhar antes da liberação dos dados que utiliza.':'Resultado descartado.');
  }
  catch(error) { status(error.message,true); }
});
$('logout').addEventListener('click',async()=>{
  try { await api('/api/sessao',{method:'DELETE'});current=null;clearReview();$('result').hidden=true;$('conversion-panel').hidden=true;$('login-panel').hidden=false;status('Sessão encerrada. Respostas ativas terminam antes da liberação dos dados que utilizam.'); }
  catch(error) { status(error.message,true); }
});
function setDate(){const d=new Date();$('reference-date').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
setDate();
config().catch(()=>{});
