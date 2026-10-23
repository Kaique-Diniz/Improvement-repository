const $ = id => document.getElementById(id);
let atual = null, aguardando = false;
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
function bloquear(b) { aguardando=b; document.querySelectorAll('#app button').forEach(x=>x.disabled=b||x.hasAttribute('data-sempre-desativado')); }
function falhar(e) { $('progresso').hidden=true; $('erro').hidden=false; $('erro').textContent='Análise interrompida: '+e.message+'. Confira os arquivos e os parâmetros.'; bloquear(false); }
async function configurar() {
  const c=await api('/api/config'); $('login').hidden=true; $('app').hidden=false; $('sair').hidden=false;
  $('casos').replaceChildren();
  for(const caso of c.fontes_privadas) { const b=elemento('button',caso.nome,'secundario');b.type='button';b.onclick=()=>executar('privado',caso.id);$('casos').append(b); }
  $('fontes-privadas').hidden=!c.fontes_privadas.length;
}
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
  bloquear(true);$('vazio').hidden=true;$('erro').hidden=true;$('resultado').hidden=true;$('progresso').hidden=false;$('etapa').textContent='Recebendo documentos…';
  try { const j=await api(endpoint,{method:'POST',body:f}); await acompanhar(j.id); }catch(e){falhar(e);}
}
$('converter').addEventListener('submit',e=>{e.preventDefault();executar('upload');});$('demo').onclick=()=>executar('demo');
async function acompanhar(id) {
  const j=await api('/api/processamentos/'+id);
  if(j.estado==='erro')throw new Error(j.codigo);
  if(j.estado==='processando') { $('etapa').textContent=j.etapa||'Iniciando extração…';await new Promise(r=>setTimeout(r,650));return acompanhar(id); }
  atual=j.resultado;mostrar();bloquear(false);
}
function mostrar() {
  const r=atual;$('progresso').hidden=true;$('resultado').hidden=false;
  $('contexto').textContent=r.administradora+' · '+r.condominio+' · Referência '+r.data_ref.split('-').reverse().join('/')+' · Modo '+r.modo+(r.origem_execucao==='exemplo_sintetico'?' · EXEMPLO SINTÉTICO':' · DIAGNÓSTICO PRIVADO');
  const stats=[['Unidades',r.resumo.unidades],['Cotas extraídas',r.resumo.cotas],['Elegíveis sem bloqueio',r.resumo.elegivel||0],['Não elegíveis',r.resumo.nao_elegivel||0],['Revisão necessária',r.resumo.revisao||0],['Cadastros adicionais',r.resumo.cadastros_adicionais]];
  $('resumo').replaceChildren(...stats.map(([label,n])=>{const d=elemento('div',undefined,'metrica');d.append(elemento('span',label),elemento('strong',String(n)));return d;}));
  $('avisos').replaceChildren(...r.avisos.map(x=>elemento('p',x)));
  if(r.resumo.revisao) $('avisos').prepend(elemento('p','Há cotas retidas para revisão. Bloqueios de lote, unidade e identidade foram preservados.'));
  $('download').hidden=!r.arquivo_teste_disponivel;$('download').href='/api/processamentos/'+r.id+'/arquivo-teste.xlsx';$('sem-excel').hidden=r.arquivo_teste_disponivel;
  $('inconsistencias').href='/api/processamentos/'+r.id+'/inconsistencias.json';
  $('comparacao').hidden=!r.comparacao;
  if(r.comparacao){$('comparacao').replaceChildren(elemento('h3','Confronto com a referência'),elemento('p','A referência é um resultado esperado, não um gabarito absoluto. Nenhuma diferença altera os dados extraídos.'),elemento('pre',JSON.stringify(r.comparacao.resumo,null,2)),elemento('p',r.comparacao.limite));}
  desenharTabela();
}
function desenharTabela() {
  if(!atual)return;
  const filtro=$('filtro').value,busca=$('busca').value.trim().toLowerCase();
  const ds=atual.decisoes.filter(d=>(filtro==='todas'||d.situacao===filtro)&&(!busca||[d.bloco,d.unidade,d.cota].join(' ').toLowerCase().includes(busca)));
  $('linhas').replaceChildren(...ds.map(d=>{const tr=elemento('tr');const unidade=elemento('td',d.bloco+' / '+d.unidade);const cota=elemento('td',d.cota);cota.append(elemento('small',d.vencimento.split('-').reverse().join('/')));const valor=elemento('td',new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(d.valor)));const estado=elemento('td');estado.append(elemento('span',nomes[d.situacao],'status '+d.situacao));const motivo=elemento('td',d.motivos.map(motivoLegivel).join(' · ')||'Condições avaliadas','motivo');const detalhe=elemento('td');const b=elemento('button','Detalhes','secundario');b.onclick=()=>{abrirDetalhes(d);};detalhe.append(b);tr.append(unidade,cota,valor,estado,motivo,detalhe);return tr;}));
  $('contagem').textContent=ds.length+' de '+atual.decisoes.length+' cotas · Valores originais, sem recalcular encargos';
}
$('filtro').onchange=desenharTabela;$('busca').oninput=desenharTabela;$('fechar').onclick=()=>$('detalhes').close();
configurar().catch(()=>{});

function motivoLegivel(c) {
  const textos={tree_centavo:'Valor original de R$ 0,01: cota excluída',tree_apontamento_a:'Apontamento A: cota excluída',tree_apontamento_aj:'Apontamento AJ: cota excluída',tree_apontamento_j:'Apontamento J: cota excluída',tree_prazo_30:'Atraso superior a 30 dias, sem exclusões',plaza_prazo_30:'Atraso superior a 30 dias',tree_prazo_30_nao_atingido:'Prazo superior a 30 dias não atingido',plaza_prazo_30_nao_atingido:'Prazo superior a 30 dias não atingido',SUBTOTAL_BLOCO_DIVERGENTE:'Subtotal do bloco divergente: lote retido',TITULAR_DIVERGENTE:'Titularidade diverge entre fontes',DOCUMENTOS_CONFLITANTES:'CPF/CNPJ conflitantes: revisão humana',DOCUMENTO_TITULAR_NAO_CONFIRMADO:'Documento sem associação comprovada ao titular',DOCUMENTO_INVALIDO:'Documento inválido: revisão necessária',INVENTARIO_EXTERNO_AUSENTE_OU_DIVERGENTE:'Inventário histórico ausente ou divergente: resultado retido',CONDICAO_INDETERMINADA:'Evidência insuficiente para decidir'};
  return textos[c]||c.toLowerCase().replaceAll('_',' ');
}
function abrirDetalhes(d) {
  const box=$('detalhes-legiveis');box.replaceChildren();
  box.append(elemento('h3',d.condominio+' · '+d.bloco+' / '+d.unidade),elemento('p','Cota '+d.cota+' · Vencimento '+d.vencimento.split('-').reverse().join('/')+' · '+nomes[d.situacao]));
  for(const m of d.motivos)box.append(elemento('p',motivoLegivel(m)));
  box.append(elemento('h3','Composição original'));
  for(const c of d.componentes)box.append(elemento('p',c.descricao_original+' · R$ '+c.valor+' · página '+c.origem.pagina+', linha '+c.origem.linha));
  box.append(elemento('p','Competência: '+(d.competencia||'não informada na fonte; preservada em branco')));
  box.append(elemento('p','Documento: '+(d.documento.estado.length?d.documento.estado.map(motivoLegivel).join('; '):'validado na fonte associada')));
  $('json-detalhes').textContent=JSON.stringify(d,null,2);$('detalhes').showModal();
}
