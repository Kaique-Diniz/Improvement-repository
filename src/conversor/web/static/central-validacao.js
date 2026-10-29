/* Conferência somente de leitura. Não altera decisões, vínculos ou o XLSX. */
let centralRegistros=[];
const centralEstados={conforme:'Conforme',conforme_com_ressalvas:'Conforme com ressalvas',erro_critico:'Erro crítico',nao_verificavel:'Não verificável',nao_aplicavel:'Não aplicável',sem_arquivo:'Sem linhas aptas',revisao:'Revisão necessária',nao_elegivel:'Excluído por regra',ressalva:'Ressalva'};
const centralCategorias={estrutura:'Estrutura do Excel',seguranca:'Integridade e segurança',planejamento:'Linhas planejadas',rastreabilidade:'Rastreabilidade',elegibilidade:'Elegibilidade',dados_leitor:'Dados do leitor',vinculos:'Pertencimento',retencoes:'Proteção cadastral',documental:'Dados pessoais retidos',financeira:'Exclusão financeira',retencao:'Retenção documental ou técnica'};
function mostrarValidacao(r){
  const val=r.validacao_conversao;$('central-validacao').hidden=!val;
  if(!val){centralRegistros=[];return;}
  const i=val.indicadores||{};
  $('central-validacao-estado').textContent=(centralEstados[val.estado]||val.estado)+(val.estado==='erro_critico'?' · Download diagnóstico bloqueado':' · Somente diagnóstico local');
  $('central-validacao-contexto').textContent=r.condominio+' · '+r.administradora+' · Referência '+r.data_ref.split('-').reverse().join('/')+' · Modo '+r.modo;
  const cards=[['Boletos encontrados',i.boletos_analisados],['Elegíveis financeiramente',i.boletos_elegiveis_financeiros],['Excluídos por regras',i.boletos_excluidos_financeiros],['Boletos retidos para revisão',i.boletos_em_revisao],['Dívidas lidas no Excel',i.linhas_divida],['Cadastros lidos no Excel',i.linhas_cadastrais],['Unidades no Excel',i.unidades_no_xlsx],['Total escrito (R$)',i.valor_financeiro_xlsx],['Total planejado (R$)',i.valor_financeiro_planejado],['Total canônico selecionado (R$)',i.valor_financeiro_canonico]];
  function metricas(id,items){$(id).replaceChildren(...items.map(([label,n])=>{const e=elemento('div',undefined,'metrica');e.append(elemento('span',label),elemento('strong',String(n??'Não informado')));return e;}));}
  metricas('central-validacao-indicadores',cards);
  metricas('central-validacao-vinculos',[['Unidades comprovadas',i.unidades_escopo_comprovado],['Unidades sem pertencimento comprovado',i.unidades_escopo_pendente],['Unidades com vínculo persistente aprovado',i.unidades_vinculo_persistente]]);
  metricas('central-validacao-protecao',[['Unidades com conflito documental conhecido',i.unidades_conflito_documental],['Linhas financeiras com contatos retidos',i.linhas_financeiras_contatos_retidos??i.linhas_com_contato_retido],['Outras unidades com dados protegidos',i.unidades_outros_dados_protegidos],['Unidades com dados protegidos (total, motivos sobrepostos)',i.unidades_contato_retido]]);
  $('central-validacao-checks').replaceChildren(...(val.verificacoes||[]).map(v=>{
    const tr=elemento('tr'),estado=elemento('td');estado.append(elemento('span',centralEstados[v.estado]||v.estado,'verificacao '+v.estado));
    tr.append(elemento('td',v.descricao),estado,elemento('td',v.evidencia));return tr;
  }));
  $('central-validacao-mensagens').replaceChildren(...[...(val.erros||[]),...(val.avisos||[])].map(m=>elemento('p',m.descricao+(m.quantidade?' ('+m.quantidade+')':''))));
  centralRegistros=[...(val.registros||[]),...(val.erros||[]).map(e=>({...e,estado:'erro_critico'}))];
  for(const id of ['central-filtro-unidade','central-filtro-boleto']){$(id).value='';$(id).oninput=filtrarValidacao;}
  for(const [id,chave,rotulos]of [['central-filtro-categoria','categoria',centralCategorias],['central-filtro-estado','estado',centralEstados]]){
    $(id).replaceChildren(new Option('Todos',''),...[...new Set(centralRegistros.map(v=>v[chave]).filter(Boolean))].sort().map(v=>new Option(rotulos[v]||v,v)));$(id).onchange=filtrarValidacao;
  }
  filtrarValidacao();
  $('central-validacao-laudo').hidden=false;$('central-validacao-laudo').href='/api/processamentos/'+r.id+'/validacao-conversao.json';
  $('central-validacao-download-status').textContent='';
}
function filtrarValidacao(){
  const u=$('central-filtro-unidade').value.trim().toLowerCase(),b=$('central-filtro-boleto').value.trim().toLowerCase(),c=$('central-filtro-categoria').value,e=$('central-filtro-estado').value;
  const rows=centralRegistros.filter(v=>(!u||[v.bloco,v.unidade,v.unidade_id].join(' / ').toLowerCase().includes(u))&&(!b||[v.boleto,v.boleto_id].join(' ').toLowerCase().includes(b))&&(!c||v.categoria===c)&&(!e||v.estado===e));
  $('central-validacao-registros').replaceChildren(...rows.map(v=>{const tr=elemento('tr');tr.append(elemento('td',v.unidade?[v.bloco,v.unidade].join(' / '):(v.unidade_id||'Não identificada')),elemento('td',v.boleto||v.boleto_id||'Não aplicável'),elemento('td',centralCategorias[v.categoria]||v.categoria),elemento('td',centralEstados[v.estado]||v.estado),elemento('td',v.descricao),elemento('td',v.linha?'Excel, linha '+v.linha+(v.coluna?', coluna '+v.coluna:''):(v.origens||[]).map(o=>localOrigem(o)+' · SHA '+o.sha256.slice(0,12)+'…').join('; ')||'Consulte a decisão do processamento'));return tr;}));
  if(!rows.length){const tr=elemento('tr'),td=elemento('td','Nenhum registro para estes filtros.');td.colSpan=6;tr.append(td);$('central-validacao-registros').append(tr);}
  $('central-validacao-contagem').textContent=rows.length+' de '+centralRegistros.length+' registros. '+(atual?.validacao_conversao?.detalhes_limitados?'Detalhes de erros limitados; o laudo mantém a contagem integral.':'Sem nomes, documentos ou contatos nesta lista.');
}
let centralBaixando=false;
async function baixarConferido(event,tipo){
  event.preventDefault();if(!atual||centralBaixando)return;
  const analise=atual,revisao=revisaoSelecao,link=event.currentTarget,url=link.getAttribute('href');if(!url)return;
  centralBaixando=true;link.setAttribute('aria-disabled','true');
  try{
    const response=await fetch(url);
    if(!response.ok){const data=await response.json();if(response.status===401){$('login').hidden=false;$('app').hidden=true;}throw new Error(data.detail||'ARQUIVO_INDISPONIVEL');}
    const blob=await response.blob();if(atual?.id!==analise.id||revisao!==revisaoSelecao)return;
    const object=URL.createObjectURL(blob),a=document.createElement('a');a.href=object;a.download=tipo==='xlsx'?'TESTE_LOCAL_NAO_IMPORTAR_'+analise.id.slice(0,8)+'.xlsx':'VALIDACAO_CONVERSAO_'+analise.id.slice(0,8)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(object),1000);
    $('central-validacao-download-status').textContent='Arquivo conferido e disponibilizado somente para diagnóstico.';
  }catch(error){
    if(atual?.id!==analise.id||revisao!==revisaoSelecao)return;
    const motivos={VINCULOS_ALTERADOS_REPROCESSAR:'O cadastro de vínculos mudou. Faça novo processamento.',XLSX_ALTERADO_APOS_VALIDACAO_REPROCESSAR:'O Excel foi alterado após a validação. Download bloqueado; faça novo processamento.',ARQUIVO_PRIVADO_INDISPONIVEL_REPROCESSAR:'O arquivo está indisponível ou não é seguro. Faça novo processamento.',LAUDO_ALTERADO_APOS_ANALISE:'O laudo foi alterado após a análise. Download bloqueado.',VALIDACAO_CRITICA_DOWNLOAD_BLOQUEADO:'A Central encontrou um erro crítico. Consulte o laudo.'};
    $('central-validacao-download-status').textContent=motivos[error.message]||'Não foi possível disponibilizar o arquivo. Confira a sessão e faça novo processamento.';
    if(tipo==='xlsx'){$('download').hidden=true;$('central-validacao-estado').textContent='Download diagnóstico bloqueado após a análise. Os resultados anteriores permanecem para conferência.';}
  }finally{centralBaixando=false;link.removeAttribute('aria-disabled');}
}
$('download').addEventListener('click',e=>baixarConferido(e,'xlsx'));
$('central-validacao-laudo').addEventListener('click',e=>baixarConferido(e,'json'));
