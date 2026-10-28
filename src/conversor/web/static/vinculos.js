/* Ações locais individuais; a API repete autenticação, CAS e integridade. */
let cadastroVinculos=null;
function preencherCondominiosVinculos(condominios){
  $('vinculo-condominio').replaceChildren(...condominios.map(c=>new Option(c.administradora+' · '+c.nome,c.administradora_id+'/'+c.condominio_id)));
}
async function consultarVinculos(){
  try{
    const [a,c]=$('vinculo-condominio').value.split('/');
    cadastroVinculos=await api('/api/vinculos?administradora_id='+encodeURIComponent(a)+'&condominio_id='+encodeURIComponent(c));
    mostrarVinculos();
  }catch(e){cadastroVinculos=null;$('vinculos-lista').replaceChildren();$('vinculos-status').textContent=e.message;}
}
function mostrarVinculos(){
  const d=cadastroVinculos;$('vinculos-lista').replaceChildren();$('vinculos-historico').replaceChildren();
  $('vinculos-status').textContent=d.registros.length+' vínculos · revisão '+d.revisao+'. Refaça a análise após uma decisão para atualizar o XLSX.';
  for(const r of d.registros){
    const box=elemento('section',undefined,'vinculo-card'),i=r.identidade;
    box.append(elemento('h3',i.bloco_literal+' / '+i.unidade_literal+' → '+r.codigo_destino+' · '+r.estado),elemento('p',i.empreendimento+' · origem '+i.codigo_original+' · versão '+r.versao),elemento('p',r.motivo));
    if(r.pendencias_documentais.length)box.append(elemento('strong','Documento e contatos retidos: conflito documental pendente. A decisão de pertencimento não remove essa retenção.'));
    const fontes=elemento('details');fontes.append(elemento('summary','Conferir evidências e aprovação'));
    for(const ev of r.evidencias)fontes.append(elemento('p',ev.papel+' · '+localOrigem(ev.origem)+' · SHA-256 '+ev.origem.sha256));
    if(r.aprovacao)fontes.append(elemento('p','Aprovado por '+r.aprovacao.responsavel+' em '+r.aprovacao.aprovado_em+' · '+r.aprovacao.fundamento));
    box.append(fontes);
    const label=elemento('label'),check=elemento('input');check.type='checkbox';label.append(check,document.createTextNode(' Conferi as evidências desta unidade para este destino.'));box.append(label);
    const acoes=r.estado==='candidato'?[['aprovar','Aprovar esta unidade'],['recusar','Recusar candidato']]:r.estado==='revogado'||r.estado==='recusado'?[]:[['revogar','Revogar vínculo']];
    for(const [acao,texto]of acoes){
      const b=elemento('button',texto,'secundario');b.type='button';b.onclick=()=>decidirVinculo(r,acao,check.checked);box.append(b);
    }
    $('vinculos-lista').append(box);
  }
  for(const e of d.historico)$('vinculos-historico').append(elemento('p','#'+e.sequencia+' · '+e.acao+' · '+e.registro.identidade.bloco_literal+'/'+e.registro.identidade.unidade_literal+' · '+e.responsavel+' · '+e.fundamento));
}
async function decidirVinculo(r,acao,confirmar){
  try{
    const responsavel=$('vinculo-responsavel').value.trim(),fundamento=$('vinculo-fundamento').value.trim();
    if(!responsavel||!fundamento)throw new Error('Informe responsável e fundamento da decisão.');
    if(acao==='aprovar'&&!confirmar)throw new Error('Confira e marque as evidências desta unidade antes de aprovar.');
    await api('/api/vinculos/'+r.id+'/decisao',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({acao,responsavel,fundamento,confirmar_evidencias:confirmar,revalidar_ate:$('vinculo-revalidar').value||null,revisao_esperada:cadastroVinculos.revisao,conteudo_sha256:r.conteudo_sha256})});
    revisaoSelecao++;limparResultado();await consultarVinculos();
  }catch(e){$('vinculos-status').textContent=e.message;}
}
$('recarregar-vinculos').onclick=consultarVinculos;
if(catalogoCondominios.length)preencherCondominiosVinculos(catalogoCondominios);
$('vinculo-condominio').onchange=consultarVinculos;
$('candidatos-vinculos').onclick=async()=>{
  try{
    if(!atual)throw new Error('Analise primeiro o financeiro com a referência histórica verificável.');
    if(!cadastroVinculos)await consultarVinculos();
    if(!cadastroVinculos)throw new Error('Cadastro de vínculos indisponível.');
    const responsavel=$('vinculo-responsavel').value.trim();if(!responsavel)throw new Error('Informe o responsável pela preparação.');
    await api('/api/vinculos/candidatos/'+atual.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({responsavel,revisao_esperada:cadastroVinculos.revisao})});
    await consultarVinculos();
  }catch(e){$('vinculos-status').textContent=e.message;}
};
