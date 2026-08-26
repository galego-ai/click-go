'use client'

import Link from 'next/link'
import {FormEvent,useEffect,useMemo,useState} from 'react'
import {BadgeCheck,Ban,Building2,CheckCircle2,CircleDollarSign,FileCheck2,KeyRound,MapPinned,RefreshCw,Search,ShieldCheck,Sparkles,XCircle} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Plan={id:string;name:string;monthly_fee:number;setup_fee:number;billing_model:string;included_rides:number;overage_fee_per_ride:number;fixed_fee_per_ride:number;percentage_rate:number;matrix_commission_percentage:number;active:boolean}
type Snapshot={
 id:string;trade_name:string;legal_name:string;document:string|null;active:boolean;contact_name:string|null;contact_email:string|null;contact_phone:string|null
 license_status:'pending'|'active'|'past_due'|'suspended'|'cancelled';activation_date:string|null;next_due_date:string|null;due_day:number;contract_status:string
 territory_type:string;onboarding_status:string;support_mode_enabled:boolean;subscription_id:string|null;plan_id:string|null;plan_name:string|null;billing_model:string|null
 monthly_fee:number;setup_fee:number;percentage_rate:number;fixed_fee_per_ride:number;included_rides:number;overage_fee_per_ride:number
 cities:City[];city_count:number;admin_name:string|null;admin_email:string|null;drivers:number;drivers_online:number;drivers_pending:number;passengers_month:number
 rides_month:number;gross_month:number;overage_rides:number;computed_usage_fee:number;computed_total_due:number;invoice_total_due:number|null;invoice_status:string|null
 onboarding_total:number;onboarding_completed:number;created_at:string
}
type Step={id:string;step_key:string;label:string;sort_order:number;completed:boolean;completed_at:string|null}
type ConfigEvent={id:number;version:number;source:string;entity:string;action:string;created_at:string}
type TempAccess={franchise:string;email:string;password:string}

const emptyCreate={trade_name:'',legal_name:'',document:'',contact_name:'',contact_email:'',contact_phone:'',territory_type:'city',due_day:'10',plan_id:''}
const brl=(v:number|null|undefined)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))
const num=(v:number|null|undefined)=>new Intl.NumberFormat('pt-BR').format(Number(v||0))
const dt=(v:string|null|undefined)=>v?new Date(v).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—'
const day=(v:string|null|undefined)=>v?new Date(v+'T12:00:00').toLocaleDateString('pt-BR'):'—'
const statusLabel:Record<string,string>={active:'Ativa',pending:'Pendente',past_due:'Em atraso',suspended:'Suspensa',cancelled:'Cancelada'}
const statusClass:Record<string,string>={active:'green',pending:'yellow',past_due:'yellow',suspended:'red',cancelled:'red'}

function reason(label:string){const value=window.prompt(`${label}\n\nInforme a justificativa para auditoria:`,'');return value===null?null:value.trim()||null}

export default function MatrixFranchiseCenter(){
 const[rows,setRows]=useState<Snapshot[]>([]),[plans,setPlans]=useState<Plan[]>([]),[cities,setCities]=useState<City[]>([])
 const[selectedId,setSelectedId]=useState(''),[search,setSearch]=useState(''),[loading,setLoading]=useState(true),[msg,setMsg]=useState(''),[busy,setBusy]=useState('')
 const[showCreate,setShowCreate]=useState(false),[createForm,setCreateForm]=useState(emptyCreate),[planToAssign,setPlanToAssign]=useState(''),[cityToAssign,setCityToAssign]=useState(''),[contractToSet,setContractToSet]=useState('pending')
 const[steps,setSteps]=useState<Step[]>([]),[events,setEvents]=useState<ConfigEvent[]>([]),[temp,setTemp]=useState<TempAccess|null>(null)

 async function load(silent=false){
  if(!silent)setLoading(true);setMsg('')
  const[s,p,c]=await Promise.all([
   supabase.rpc('super_admin_franchise_network_snapshot'),
   supabase.from('franchise_plans').select('id,name,monthly_fee,setup_fee,billing_model,included_rides,overage_fee_per_ride,fixed_fee_per_ride,percentage_rate,matrix_commission_percentage,active').order('name'),
   supabase.from('cities').select('id,name,state').eq('active',true).order('name')
  ])
  if(s.error)setMsg(s.error.message);else{
   const data=(Array.isArray(s.data)?s.data:[]) as Snapshot[];setRows(data);setSelectedId(v=>v&&data.some(x=>x.id===v)?v:(data[0]?.id||''))
  }
  if(p.error||c.error)setMsg(p.error?.message||c.error?.message||'Falha ao carregar cadastros.');setPlans((p.data||[]) as Plan[]);setCities((c.data||[]) as City[]);setLoading(false)
 }
 useEffect(()=>{void load();const ch=supabase.channel('matrix-franchise-center-live').on('postgres_changes',{event:'*',schema:'public',table:'configuration_events'},()=>void load(true)).subscribe();return()=>{void supabase.removeChannel(ch)}},[])
 const selected=rows.find(x=>x.id===selectedId)||null
 useEffect(()=>{setTemp(null);setPlanToAssign('');setCityToAssign('');setContractToSet(selected?.contract_status||'pending');if(!selectedId){setSteps([]);setEvents([]);return}void loadDetails(selectedId)},[selectedId,selected?.contract_status])
 async function loadDetails(fid:string){const[s,e]=await Promise.all([supabase.from('franchise_onboarding_steps').select('id,step_key,label,sort_order,completed,completed_at').eq('franchise_id',fid).order('sort_order'),supabase.from('configuration_events').select('id,version,source,entity,action,created_at').eq('franchise_id',fid).order('created_at',{ascending:false}).limit(8)]);setSteps((s.data||[]) as Step[]);setEvents((e.data||[]) as ConfigEvent[])}
 const visible=useMemo(()=>{const q=search.trim().toLowerCase();return rows.filter(r=>!q||[r.trade_name,r.legal_name,r.plan_name||'',r.admin_name||'',...(r.cities||[]).map(c=>`${c.name}/${c.state}`)].join(' ').toLowerCase().includes(q))},[rows,search])
 const totals=useMemo(()=>({count:rows.length,active:rows.filter(x=>x.license_status==='active').length,rides:rows.reduce((a,x)=>a+x.rides_month,0),online:rows.reduce((a,x)=>a+x.drivers_online,0),due:rows.reduce((a,x)=>a+Number(x.invoice_total_due??x.computed_total_due??0),0)}),[rows])

 async function createFranchise(e:FormEvent){
  e.preventDefault();const why=reason('Criar nova franquia CLICK-GO');if(!why){setMsg('Operação cancelada: a justificativa é obrigatória.');return}setBusy('create')
  const{data,error}=await supabase.rpc('matrix_create_franchise',{p_trade_name:createForm.trade_name,p_legal_name:createForm.legal_name,p_document:createForm.document||null,p_contact_name:createForm.contact_name||null,p_contact_email:createForm.contact_email||null,p_contact_phone:createForm.contact_phone||null,p_territory_type:createForm.territory_type,p_due_day:Number(createForm.due_day)||10,p_plan_id:createForm.plan_id||null,p_reason:why})
  setBusy('');if(error){setMsg(error.message);return}setCreateForm(emptyCreate);setShowCreate(false);await load();if(data?.franchise_id)setSelectedId(String(data.franchise_id));setMsg('Franquia criada e registrada na auditoria.')
 }
 async function license(action:'suspend'|'reactivate'|'cancel'){
  if(!selected)return;const why=reason(`${action==='suspend'?'Suspender':action==='cancel'?'Cancelar':'Reativar'} ${selected.trade_name}`);if(!why)return
  if((action==='suspend'||action==='cancel')&&!confirm(`Confirmar ${action==='cancel'?'cancelamento':'suspensão'} da licença de ${selected.trade_name}?`))return
  setBusy('license');const{error}=await supabase.rpc('matrix_set_franchise_license',{p_franchise_id:selected.id,p_action:action,p_reason:why});setBusy('');setMsg(error?error.message:'Licença atualizada com auditoria.');if(!error)await load()
 }
 async function applyPlan(){if(!selected||!planToAssign)return;const why=reason(`Aplicar novo plano em ${selected.trade_name}`);if(!why)return;setBusy('plan');const{error}=await supabase.rpc('matrix_assign_franchise_plan',{p_franchise_id:selected.id,p_plan_id:planToAssign,p_reason:why});setBusy('');setMsg(error?error.message:'Plano aplicado e ciclo atualizado.');if(!error){setPlanToAssign('');await load()}}
 async function assignCity(){
  if(!selected||!cityToAssign)return;const city=cities.find(c=>c.id===cityToAssign);const why=reason(`Vincular ${city?.name||'cidade'} a ${selected.trade_name}`);if(!why)return;setBusy('city')
  let{data,error}=await supabase.rpc('matrix_assign_franchise_city',{p_franchise_id:selected.id,p_city_id:cityToAssign,p_reason:why,p_override:false})
  if(!error&&data?.status==='conflict'){
   const ok=confirm(`${data.city_name} pertence a ${data.current_franchise_name}. Transferir o território para ${selected.trade_name}?`)
   if(ok){const again=await supabase.rpc('matrix_assign_franchise_city',{p_franchise_id:selected.id,p_city_id:cityToAssign,p_reason:why,p_override:true});data=again.data;error=again.error}else{setBusy('');setMsg('Transferência territorial cancelada.');return}
  }
  setBusy('');setMsg(error?error.message:data?.status==='overridden'?'Território transferido e auditado.':'Território vinculado e auditado.');if(!error){setCityToAssign('');await load()}
 }
 async function removeCity(city:City){if(!selected)return;const why=reason(`Remover ${city.name}/${city.state} de ${selected.trade_name}`);if(!why)return;if(!confirm(`Remover ${city.name}/${city.state} desta franquia?`))return;setBusy('city');const{error}=await supabase.rpc('matrix_remove_franchise_city',{p_franchise_id:selected.id,p_city_id:city.id,p_reason:why});setBusy('');setMsg(error?error.message:'Território removido e auditado.');if(!error)await load()}
 async function updateContract(){if(!selected)return;const why=reason(`Alterar contrato de ${selected.trade_name} para ${contractToSet}`);if(!why)return;setBusy('contract');const{error}=await supabase.rpc('matrix_update_franchise_contract',{p_franchise_id:selected.id,p_status:contractToSet,p_reason:why});setBusy('');setMsg(error?error.message:'Contrato atualizado e auditado.');if(!error)await load()}
 async function toggleStep(step:Step){const why=reason(`${step.completed?'Reabrir':'Concluir'} etapa “${step.label}”`);if(!why)return;setBusy('step');const{error}=await supabase.rpc('matrix_set_franchise_onboarding_step',{p_step_id:step.id,p_completed:!step.completed,p_reason:why});setBusy('');setMsg(error?error.message:'Checklist atualizado e auditado.');if(!error&&selected){await loadDetails(selected.id);await load(true)}}
 async function generateAccess(){if(!selected)return;const chosen=window.prompt('Senha temporária (mínimo 8 caracteres com letras e números). Deixe em branco para gerar automaticamente.','');if(chosen===null)return;setBusy('access');setTemp(null);const body:any={action:'generate',franchise_id:selected.id};if(chosen.trim())body.temporary_password=chosen.trim();const{data,error}=await supabase.functions.invoke('franchise-temp-password',{body});setBusy('');if(error||data?.error){setMsg(String(data?.error||error?.message||'Falha ao gerar acesso.'));return}setTemp({franchise:selected.trade_name,email:data.email,password:data.temporary_password});setMsg('Acesso administrativo preparado com senha temporária.')}

 const completion=selected?.onboarding_total?Math.round(selected.onboarding_completed/selected.onboarding_total*100):0
 return <div className="regional-home">
  <div className="card"><div className="section-heading"><div><div className="eyebrow"><ShieldCheck size={15}/> Rede licenciada CLICK-GO</div><h2>Central de Franquias e Licenças</h2><p className="subtitle">Ações críticas exigem justificativa e ficam registradas na auditoria da Matriz.</p></div><div className="toolbar"><button className="button secondary" onClick={()=>void load()} disabled={loading}><RefreshCw size={15}/>{loading?'Atualizando...':'Atualizar'}</button><button className="button" onClick={()=>setShowCreate(v=>!v)}><Building2 size={15}/>{showCreate?'Fechar':'Nova franquia'}</button></div></div>
   <div className="regional-kpis"><div className="regional-kpi"><span>Franquias</span><strong>{num(totals.count)}</strong><small>{totals.active} ativas</small></div><div className="regional-kpi"><span>Corridas no mês</span><strong>{num(totals.rides)}</strong><small>rede CLICK-GO</small></div><div className="regional-kpi"><span>Motoristas online</span><strong>{num(totals.online)}</strong><small>agora</small></div><div className="regional-kpi"><span>Valor à Matriz</span><strong>{brl(totals.due)}</strong><small>faturado/previsto</small></div></div>
  </div>

  {showCreate&&<form className="card section" onSubmit={createFranchise}><div className="section-heading"><div><div className="eyebrow">Cadastro</div><h2>Nova operação</h2></div></div><div className="form-grid"><div className="field"><label>Nome fantasia</label><input className="input" required value={createForm.trade_name} onChange={e=>setCreateForm({...createForm,trade_name:e.target.value})}/></div><div className="field"><label>Razão social</label><input className="input" required value={createForm.legal_name} onChange={e=>setCreateForm({...createForm,legal_name:e.target.value})}/></div><div className="field"><label>CPF/CNPJ</label><input className="input" value={createForm.document} onChange={e=>setCreateForm({...createForm,document:e.target.value})}/></div><div className="field"><label>Responsável</label><input className="input" value={createForm.contact_name} onChange={e=>setCreateForm({...createForm,contact_name:e.target.value})}/></div><div className="field"><label>E-mail</label><input className="input" type="email" value={createForm.contact_email} onChange={e=>setCreateForm({...createForm,contact_email:e.target.value})}/></div><div className="field"><label>Telefone</label><input className="input" value={createForm.contact_phone} onChange={e=>setCreateForm({...createForm,contact_phone:e.target.value})}/></div><div className="field"><label>Território contratado</label><select className="input" value={createForm.territory_type} onChange={e=>setCreateForm({...createForm,territory_type:e.target.value})}><option value="city">Uma cidade</option><option value="multi_city">Várias cidades</option><option value="region">Região</option></select></div><div className="field"><label>Dia de vencimento</label><input className="input" type="number" min="1" max="28" value={createForm.due_day} onChange={e=>setCreateForm({...createForm,due_day:e.target.value})}/></div><div className="field"><label>Plano inicial</label><select className="input" value={createForm.plan_id} onChange={e=>setCreateForm({...createForm,plan_id:e.target.value})}><option value="">Definir depois</option>{plans.filter(p=>p.active).map(p=><option key={p.id} value={p.id}>{p.name} · {brl(p.monthly_fee)}</option>)}</select></div></div><button className="button" disabled={busy==='create'} style={{marginTop:14}}><Sparkles size={15}/>{busy==='create'?'Criando...':'Criar franquia'}</button></form>}
  {msg&&<div className="regional-alert">{msg}</div>}

  <div className="section" style={{display:'grid',gridTemplateColumns:'minmax(260px,340px) minmax(0,1fr)',gap:16,alignItems:'start'}}>
   <div className="card"><div className="field"><label>Buscar franquia</label><div style={{display:'flex',alignItems:'center',gap:8}}><Search size={15}/><input className="input" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Nome, cidade, plano..."/></div></div><div className="module-list" style={{marginTop:12,maxHeight:660,overflow:'auto'}}>{visible.map(r=><button key={r.id} className={r.id===selectedId?'button':'button secondary'} style={{justifyContent:'space-between',width:'100%'}} onClick={()=>setSelectedId(r.id)}><span style={{textAlign:'left'}}><strong style={{display:'block'}}>{r.trade_name}</strong><small>{r.cities?.map(c=>`${c.name}/${c.state}`).join(' · ')||'Sem território'}</small></span><span className={'pill '+(statusClass[r.license_status]||'')}>{statusLabel[r.license_status]||r.license_status}</span></button>)}</div></div>

   {!selected?<div className="card empty">Selecione uma franquia.</div>:<div className="module-list">
    <div className="card"><div className="section-heading"><div><div className="eyebrow">{selected.plan_name||'Sem plano'}</div><h2>{selected.trade_name}</h2><p className="subtitle">{selected.legal_name} · {selected.cities?.map(c=>`${c.name}/${c.state}`).join(' · ')||'Território pendente'}</p></div><span className={'pill '+(statusClass[selected.license_status]||'')}>{statusLabel[selected.license_status]||selected.license_status}</span></div><div className="regional-kpis"><div className="regional-kpi"><span>Mensalidade</span><strong>{brl(selected.monthly_fee)}</strong><small>{selected.billing_model||'—'}</small></div><div className="regional-kpi"><span>Corridas</span><strong>{num(selected.rides_month)}</strong><small>{num(selected.overage_rides)} excedentes</small></div><div className="regional-kpi"><span>Fatura</span><strong>{brl(selected.invoice_total_due??selected.computed_total_due)}</strong><small>{selected.invoice_status||'prévia'}</small></div><div className="regional-kpi"><span>Vencimento</span><strong>{day(selected.next_due_date)}</strong><small>dia {selected.due_day}</small></div></div></div>

    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(240px,1fr))',gap:16}}>
     <div className="card"><div className="section-heading"><div><div className="eyebrow"><CircleDollarSign size={14}/> Plano</div><h3>Cobrança da franquia</h3></div></div><p className="subtitle">Atual: {selected.plan_name||'nenhum'} · uso {brl(selected.computed_usage_fee)}</p><div className="field"><label>Novo plano</label><select className="input" value={planToAssign} onChange={e=>setPlanToAssign(e.target.value)}><option value="">Selecione</option>{plans.filter(p=>p.active).map(p=><option key={p.id} value={p.id}>{p.name} · {brl(p.monthly_fee)}</option>)}</select></div><button className="button" onClick={()=>void applyPlan()} disabled={!planToAssign||busy==='plan'}>{busy==='plan'?'Aplicando...':'Aplicar plano'}</button></div>
     <div className="card"><div className="section-heading"><div><div className="eyebrow"><MapPinned size={14}/> Território</div><h3>Cidades exclusivas</h3></div></div><div style={{display:'flex',gap:6,flexWrap:'wrap',marginBottom:12}}>{selected.cities?.length?selected.cities.map(c=><span className="pill" key={c.id}>{c.name}/{c.state} <button aria-label={`Remover ${c.name}`} onClick={()=>void removeCity(c)} style={{border:0,background:'transparent',cursor:'pointer'}}>×</button></span>):<span className="subtitle">Nenhuma cidade vinculada.</span>}</div><div className="field"><label>Adicionar ou transferir</label><select className="input" value={cityToAssign} onChange={e=>setCityToAssign(e.target.value)}><option value="">Selecione a cidade</option>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select></div><button className="button" onClick={()=>void assignCity()} disabled={!cityToAssign||busy==='city'}>{busy==='city'?'Atualizando...':'Vincular cidade'}</button></div>
     <div className="card"><div className="section-heading"><div><div className="eyebrow"><FileCheck2 size={14}/> Contrato</div><h3>Governança</h3></div></div><div className="field"><label>Status</label><select className="input" value={contractToSet} onChange={e=>setContractToSet(e.target.value)}><option value="pending">Pendente</option><option value="signed">Assinado</option><option value="expired">Expirado</option><option value="cancelled">Cancelado</option></select></div><button className="button secondary" onClick={()=>void updateContract()} disabled={busy==='contract'}>Salvar contrato</button><button className="button secondary" onClick={()=>void generateAccess()} disabled={busy==='access'} style={{marginTop:8}}><KeyRound size={14}/>{busy==='access'?'Gerando...':'Gerar acesso admin'}</button></div>
    </div>

    {temp&&<div className="card" style={{border:'1px solid #d5bb00'}}><div className="eyebrow">Senha temporária · mostrar uma única vez</div><h3>{temp.franchise}</h3><p><strong>E-mail:</strong> {temp.email}</p><p><strong>Senha temporária:</strong> {temp.password}</p><button className="button secondary" onClick={()=>setTemp(null)}>Ocultar</button></div>}

    <div className="card"><div className="section-heading"><div><div className="eyebrow">Implantação</div><h3>Checklist de liberação · {completion}%</h3></div></div><div className="module-list">{steps.map(s=><button key={s.id} className="button secondary" style={{justifyContent:'flex-start'}} onClick={()=>void toggleStep(s)} disabled={busy==='step'}>{s.completed?<CheckCircle2 size={16}/>:<span style={{width:16,height:16,border:'1px solid currentColor',borderRadius:'50%'}}/>}<span style={{textAlign:'left'}}><strong>{s.label}</strong>{s.completed&&<small style={{display:'block'}}>Concluído {dt(s.completed_at)}</small>}</span></button>)}</div></div>

    <div className="card"><div className="section-heading"><div><div className="eyebrow">Auditoria técnica</div><h3>Últimas alterações sincronizadas</h3></div><Link className="button secondary" href="/auditoria">Abrir auditoria</Link></div>{events.length===0?<p className="subtitle">Sem alterações recentes.</p>:<div className="table-wrap"><table className="table"><thead><tr><th>Origem</th><th>Entidade</th><th>Ação</th><th>Versão</th><th>Data</th></tr></thead><tbody>{events.map(e=><tr key={e.id}><td>{e.source}</td><td>{e.entity}</td><td>{e.action}</td><td>{e.version}</td><td>{dt(e.created_at)}</td></tr>)}</tbody></table></div>}</div>

    <div className="card"><div className="section-heading"><div><div className="eyebrow">Controle da Matriz</div><h3>Licença operacional</h3><p className="subtitle">“Em atraso” é calculado automaticamente pelas faturas; a Matriz controla reativação, suspensão e cancelamento.</p></div></div><div className="toolbar"><button className="button" onClick={()=>void license('reactivate')} disabled={busy==='license'}><BadgeCheck size={15}/>Reativar</button><button className="button secondary" onClick={()=>void license('suspend')} disabled={busy==='license'}><Ban size={15}/>Suspender</button><button className="button secondary" onClick={()=>void license('cancel')} disabled={busy==='license'}><XCircle size={15}/>Cancelar</button><Link className="button secondary" href="/bloqueios">Cobranças e inadimplência</Link></div></div>
   </div>}
  </div>
 </div>
}
