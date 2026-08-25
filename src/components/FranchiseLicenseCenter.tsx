'use client'

import Link from 'next/link'
import {useEffect,useMemo,useState} from 'react'
import {
  Activity, BadgeCheck, Ban, Building2, CalendarClock, CarFront, CheckCircle2, ChevronRight,
  CircleDollarSign, ClipboardCheck, CreditCard, FileCheck2, Gauge, Headphones, KeyRound, MapPinned,
  RefreshCw, Search, Settings2, ShieldCheck, Smartphone, Sparkles, UsersRound, WalletCards, XCircle
} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Plan={id:string;name:string;monthly_fee:number;setup_fee:number;billing_model:string;included_rides:number;overage_fee_per_ride:number;fixed_fee_per_ride:number;percentage_rate:number;matrix_commission_percentage:number;enabled_modules:Record<string,boolean>|null;active:boolean}
type Snapshot={
 id:string;trade_name:string;legal_name:string;document:string|null;active:boolean;contact_name:string|null;contact_email:string|null;contact_phone:string|null
 license_status:'pending'|'active'|'past_due'|'suspended'|'cancelled';activation_date:string|null;next_due_date:string|null;due_day:number;contract_status:string;contract_reference:string|null
 territory_type:string;onboarding_status:string;support_mode_enabled:boolean;white_label_mode:string;commercial_notes:string|null
 subscription_id:string|null;plan_id:string|null;plan_name:string|null;billing_model:string|null;monthly_fee:number;setup_fee:number;percentage_rate:number;fixed_fee_per_ride:number
 included_rides:number;overage_fee_per_ride:number;matrix_commission_percentage:number;enabled_modules:Record<string,boolean>|null;support_level:string|null;white_label_level:string|null
 cities:City[];city_count:number;admin_id:string|null;admin_name:string|null;admin_email:string|null;drivers:number;drivers_online:number;drivers_pending:number;passengers_month:number
 rides_month:number;gross_month:number;overage_rides:number;computed_usage_fee:number;computed_total_due:number;invoice_id:string|null;invoice_total_due:number|null;invoice_status:string|null
 onboarding_total:number;onboarding_completed:number;config_version:number;config_changed_at:string|null;config_changed_source:string|null;created_at:string;updated_at:string|null
}
type Onboarding={id:string;step_key:string;label:string;sort_order:number;completed:boolean;completed_at:string|null;notes:string|null}
type ConfigEvent={id:number;version:number;source:string;entity:string;action:string;created_at:string}
type TempAccess={franchise:string;email:string;password:string}

const emptyCreate={trade_name:'',legal_name:'',document:'',contact_name:'',contact_email:'',contact_phone:'',territory_type:'city',due_day:'10',plan_id:''}
const money=(value:number|null|undefined)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0))
const number=(value:number|null|undefined)=>new Intl.NumberFormat('pt-BR').format(Number(value||0))
const date=(value:string|null|undefined)=>value?new Date(value+'T12:00:00').toLocaleDateString('pt-BR'):'—'
const dateTime=(value:string|null|undefined)=>value?new Date(value).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—'

const statusMap={
 active:{label:'Ativa',className:'green'},pending:{label:'Pendente',className:'yellow'},past_due:{label:'Em atraso',className:'yellow'},suspended:{label:'Suspensa',className:'red'},cancelled:{label:'Cancelada',className:'red'}
} as const
const sourceLabel:Record<string,string>={matrix:'Matriz',franchise:'Franqueado',staff:'Equipe',driver_app:'App Motorista',passenger_app:'App Passageiro',system:'Sistema'}
const entityLabel:Record<string,string>={ride_categories:'Tarifas/categorias',franchise_settings:'Configuração regional',advertising_banners:'Anúncios',promotions:'Promoções',coupons:'Cupons',franchise_business_hours:'Horários',franchise_city_payment_settings:'Pagamentos',franchise_operational_wallet_settings:'Carteira operacional'}

export default function FranchiseLicenseCenter(){
 const[rows,setRows]=useState<Snapshot[]>([]);const[plans,setPlans]=useState<Plan[]>([]);const[cities,setCities]=useState<City[]>([])
 const[selectedId,setSelectedId]=useState('');const[search,setSearch]=useState('');const[statusFilter,setStatusFilter]=useState('all');const[loading,setLoading]=useState(true);const[msg,setMsg]=useState('')
 const[showCreate,setShowCreate]=useState(false);const[createForm,setCreateForm]=useState(emptyCreate);const[busy,setBusy]=useState('');const[cityToAssign,setCityToAssign]=useState('');const[planToAssign,setPlanToAssign]=useState('')
 const[onboarding,setOnboarding]=useState<Onboarding[]>([]);const[events,setEvents]=useState<ConfigEvent[]>([]);const[supportMode,setSupportMode]=useState(false);const[temp,setTemp]=useState<TempAccess|null>(null)

 async function load(silent=false){
  if(!silent)setLoading(true);setMsg('')
  const[snapshot,planRes,cityRes]=await Promise.all([
   supabase.rpc('super_admin_franchise_network_snapshot'),
   supabase.from('franchise_plans').select('id,name,monthly_fee,setup_fee,billing_model,included_rides,overage_fee_per_ride,fixed_fee_per_ride,percentage_rate,matrix_commission_percentage,enabled_modules,active').order('name'),
   supabase.from('cities').select('id,name,state').eq('active',true).order('name')
  ])
  if(snapshot.error)setMsg(snapshot.error.message);else{
   const data=(Array.isArray(snapshot.data)?snapshot.data:[]) as Snapshot[];setRows(data)
   setSelectedId(current=>current&&data.some(x=>x.id===current)?current:(data[0]?.id||''))
  }
  setPlans((planRes.data||[]) as Plan[]);setCities((cityRes.data||[]) as City[])
  if(planRes.error||cityRes.error)setMsg(planRes.error?.message||cityRes.error?.message||'Falha ao carregar cadastros.')
  setLoading(false)
 }
 useEffect(()=>{void load();const channel=supabase.channel('clickgo-matrix-network-live')
   .on('postgres_changes',{event:'*',schema:'public',table:'configuration_events'},()=>void load(true))
   .on('postgres_changes',{event:'*',schema:'public',table:'rides'},()=>void load(true))
   .on('postgres_changes',{event:'*',schema:'public',table:'driver_locations'},()=>void load(true))
   .subscribe();return()=>{void supabase.removeChannel(channel)}},[])

 const selected=rows.find(x=>x.id===selectedId)||null
 useEffect(()=>{setSupportMode(false);setTemp(null);if(!selectedId){setOnboarding([]);setEvents([]);return}void loadDetails(selectedId)},[selectedId])
 async function loadDetails(id:string){
  const[o,e]=await Promise.all([
   supabase.from('franchise_onboarding_steps').select('id,step_key,label,sort_order,completed,completed_at,notes').eq('franchise_id',id).order('sort_order'),
   supabase.from('configuration_events').select('id,version,source,entity,action,created_at').eq('franchise_id',id).order('created_at',{ascending:false}).limit(8)
  ])
  setOnboarding((o.data||[]) as Onboarding[]);setEvents((e.data||[]) as ConfigEvent[])
 }

 const visible=useMemo(()=>rows.filter(row=>{
  const q=search.trim().toLowerCase();const hay=[row.trade_name,row.legal_name,row.plan_name||'',row.admin_name||'',...(row.cities||[]).map(c=>`${c.name}/${c.state}`)].join(' ').toLowerCase()
  return(!q||hay.includes(q))&&(statusFilter==='all'||row.license_status===statusFilter)
 }),[rows,search,statusFilter])
 const totals=useMemo(()=>({
  franchises:rows.length,active:rows.filter(x=>x.license_status==='active').length,attention:rows.filter(x=>['past_due','suspended','pending'].includes(x.license_status)).length,
  rides:rows.reduce((s,x)=>s+x.rides_month,0),driversOnline:rows.reduce((s,x)=>s+x.drivers_online,0),due:rows.reduce((s,x)=>s+Number(x.invoice_total_due??x.computed_total_due??0),0)
 }),[rows])

 async function createFranchise(e:React.FormEvent){
  e.preventDefault();setBusy('create');setMsg('Criando estrutura da nova operação...')
  const due=Math.min(28,Math.max(1,Number(createForm.due_day)||10))
  const{data,error}=await supabase.from('franchises').insert({trade_name:createForm.trade_name.trim(),legal_name:createForm.legal_name.trim(),document:createForm.document.trim()||null,contact_name:createForm.contact_name.trim()||null,contact_email:createForm.contact_email.trim()||null,contact_phone:createForm.contact_phone.trim()||null,territory_type:createForm.territory_type,due_day:due,active:true,license_status:createForm.plan_id?'active':'pending',activation_date:createForm.plan_id?new Date().toISOString().slice(0,10):null,onboarding_status:'in_progress'}).select('id').single()
  if(error||!data){setBusy('');setMsg(error?.message||'Não foi possível cadastrar a franquia.');return}
  if(createForm.plan_id){
   const plan=plans.find(p=>p.id===createForm.plan_id);const nextDue=new Date();nextDue.setDate(due);if(nextDue<new Date())nextDue.setMonth(nextDue.getMonth()+1)
   const sub=await supabase.from('franchise_subscriptions').insert({franchise_id:data.id,plan_id:createForm.plan_id,status:'active',license_status:'active',matrix_commission_percentage:Number(plan?.matrix_commission_percentage||0),due_day:due,next_due_date:nextDue.toISOString().slice(0,10),activated_at:new Date().toISOString()})
   if(sub.error)setMsg('Franquia criada, mas o plano precisa ser vinculado manualmente: '+sub.error.message)
  }
  setCreateForm(emptyCreate);setShowCreate(false);setBusy('');await load();setSelectedId(data.id);setMsg('Nova operação criada. Agora conclua território, contrato e administrador no checklist.')
 }

 async function setLicense(status:Snapshot['license_status']){if(!selected)return;if(!confirm(`Alterar a licença de ${selected.trade_name} para ${statusMap[status].label}?`))return;setBusy('license');const update:any={license_status:status,updated_at:new Date().toISOString()};if(status==='active'){update.active=true;update.blocked_at=null;update.blocked_reason=null;update.activation_date=selected.activation_date||new Date().toISOString().slice(0,10)}if(status==='suspended'||status==='cancelled')update.active=false;const{error}=await supabase.from('franchises').update(update).eq('id',selected.id);setBusy('');setMsg(error?error.message:`Licença alterada para ${statusMap[status].label}.`);if(!error)await load()}
 async function setContract(status:string){if(!selected)return;setBusy('contract');const{error}=await supabase.from('franchises').update({contract_status:status,updated_at:new Date().toISOString()}).eq('id',selected.id);setBusy('');setMsg(error?error.message:'Status contratual atualizado.');if(!error)await load()}
 async function assignPlan(){if(!selected||!planToAssign){setMsg('Escolha um plano.');return}const plan=plans.find(p=>p.id===planToAssign);if(!plan)return;setBusy('plan');await supabase.from('franchise_subscriptions').update({status:'cancelled',license_status:'cancelled',ends_at:new Date().toISOString(),updated_at:new Date().toISOString()}).eq('franchise_id',selected.id).eq('status','active');const due=selected.due_day||10;const next=new Date();next.setDate(due);if(next<new Date())next.setMonth(next.getMonth()+1);const{error}=await supabase.from('franchise_subscriptions').insert({franchise_id:selected.id,plan_id:plan.id,status:'active',license_status:'active',matrix_commission_percentage:Number(plan.matrix_commission_percentage||0),due_day:due,next_due_date:next.toISOString().slice(0,10),activated_at:new Date().toISOString()});if(!error)await supabase.from('franchises').update({license_status:'active',active:true,activation_date:selected.activation_date||new Date().toISOString().slice(0,10),next_due_date:next.toISOString().slice(0,10),updated_at:new Date().toISOString()}).eq('id',selected.id);setBusy('');setPlanToAssign('');setMsg(error?error.message:`Plano ${plan.name} aplicado.`);if(!error)await load()}
 async function assignCity(){if(!selected||!cityToAssign){setMsg('Escolha uma cidade.');return}const city=cities.find(c=>c.id===cityToAssign);const current=await supabase.from('franchise_cities').select('franchise_id').eq('city_id',cityToAssign).maybeSingle();if(current.data?.franchise_id&&current.data.franchise_id!==selected.id&&!confirm(`${city?.name}/${city?.state} já pertence a outra operação. Transferir o território?`))return;if(current.data?.franchise_id&&current.data.franchise_id!==selected.id)await supabase.from('franchise_cities').delete().eq('city_id',cityToAssign);const{error}=await supabase.from('franchise_cities').upsert({franchise_id:selected.id,city_id:cityToAssign});setCityToAssign('');setMsg(error?error.message:'Território atualizado.');if(!error)await load()}
 async function toggleStep(step:Onboarding){if(!selected)return;const next=!step.completed;const{error}=await supabase.from('franchise_onboarding_steps').update({completed:next,completed_at:next?new Date().toISOString():null,updated_at:new Date().toISOString()}).eq('id',step.id);if(error){setMsg(error.message);return}await loadDetails(selected.id);await load(true)}
 async function generateAccess(){if(!selected)return;const chosen=window.prompt('Senha temporária (mínimo 8 caracteres com letras e números). Deixe em branco para gerar automaticamente.','');if(chosen===null)return;setBusy('access');setTemp(null);const body:any={action:'generate',franchise_id:selected.id};if(chosen.trim())body.temporary_password=chosen.trim();const{data,error}=await supabase.functions.invoke('franchise-temp-password',{body});setBusy('');if(error||data?.error){setMsg(data?.error||error?.message||'Falha ao gerar acesso.');return}setTemp({franchise:selected.trade_name,email:data.email,password:data.temporary_password});setMsg('Acesso administrativo preparado com senha temporária.')}

 const completion=selected?.onboarding_total?Math.round(selected.onboarding_completed/selected.onboarding_total*100):0
 const realDue=selected?Number(selected.invoice_total_due??selected.computed_total_due??0):0
 const moduleNames:Record<string,string>={passenger_app:'Passageiro',driver_app:'Motorista',dispatch:'Despacho',finance:'Financeiro',support:'Suporte',marketing:'Marketing',reports:'Relatórios'}

 return <div className="license-center">
  <div className="network-command card">
   <div className="network-command-title"><div><span className="command-kicker"><ShieldCheck size={15}/> Rede licenciada CLICK-GO</span><h2>Central de Franquias e Licenças</h2><p>Gestão comercial, territorial, operacional e tecnológica em um único ambiente.</p></div><div className="toolbar"><button className="button secondary" onClick={()=>void load()} disabled={loading}><RefreshCw size={16}/>{loading?'Atualizando':'Atualizar rede'}</button><button className="button" onClick={()=>setShowCreate(v=>!v)}><Building2 size={16}/>{showCreate?'Fechar cadastro':'Nova operação'}</button></div></div>
   <div className="network-kpis">
    <div><span>Operações</span><strong>{number(totals.franchises)}</strong><small>{totals.active} com licença ativa</small></div>
    <div><span>Atenção comercial</span><strong>{number(totals.attention)}</strong><small>pendentes, em atraso ou suspensas</small></div>
    <div><span>Corridas no mês</span><strong>{number(totals.rides)}</strong><small>toda a rede</small></div>
    <div><span>Motoristas online</span><strong>{number(totals.driversOnline)}</strong><small>agora</small></div>
    <div><span>Receita da matriz</span><strong>{money(totals.due)}</strong><small>prevista/faturada no mês</small></div>
   </div>
  </div>

  {showCreate&&<form className="card license-create" onSubmit={createFranchise}><div className="section-heading"><div><div className="eyebrow">Nova licença</div><h2>Criar operação CLICK-GO</h2><p className="subtitle">A estrutura de implantação e auditoria será criada automaticamente.</p></div></div><div className="form-grid"><div className="field"><label>Nome fantasia</label><input className="input" required value={createForm.trade_name} onChange={e=>setCreateForm({...createForm,trade_name:e.target.value})}/></div><div className="field"><label>Razão social</label><input className="input" required value={createForm.legal_name} onChange={e=>setCreateForm({...createForm,legal_name:e.target.value})}/></div><div className="field"><label>CPF/CNPJ</label><input className="input" value={createForm.document} onChange={e=>setCreateForm({...createForm,document:e.target.value})}/></div><div className="field"><label>Responsável</label><input className="input" value={createForm.contact_name} onChange={e=>setCreateForm({...createForm,contact_name:e.target.value})}/></div><div className="field"><label>E-mail administrativo</label><input className="input" type="email" value={createForm.contact_email} onChange={e=>setCreateForm({...createForm,contact_email:e.target.value})}/></div><div className="field"><label>Telefone</label><input className="input" value={createForm.contact_phone} onChange={e=>setCreateForm({...createForm,contact_phone:e.target.value})}/></div><div className="field"><label>Território contratado</label><select className="input" value={createForm.territory_type} onChange={e=>setCreateForm({...createForm,territory_type:e.target.value})}><option value="city">Uma cidade</option><option value="multi_city">Várias cidades</option><option value="region">Região</option></select></div><div className="field"><label>Dia de vencimento</label><input className="input" type="number" min="1" max="28" value={createForm.due_day} onChange={e=>setCreateForm({...createForm,due_day:e.target.value})}/></div><div className="field"><label>Plano inicial</label><select className="input" value={createForm.plan_id} onChange={e=>setCreateForm({...createForm,plan_id:e.target.value})}><option value="">Definir depois</option>{plans.filter(p=>p.active).map(p=><option key={p.id} value={p.id}>{p.name} · {money(p.monthly_fee)}</option>)}</select></div></div><div className="toolbar" style={{marginTop:16}}><button className="button" disabled={busy==='create'}><Sparkles size={16}/>{busy==='create'?'Criando estrutura...':'Criar licença e implantação'}</button></div></form>}

  {msg&&<div className="license-message">{msg}</div>}

  <div className="license-workspace">
   <aside className="license-list card">
    <div className="license-list-head"><div><strong>Rede CLICK-GO</strong><span>{visible.length} operação(ões)</span></div></div>
    <div className="license-search"><Search size={16}/><input placeholder="Buscar franquia, cidade, plano..." value={search} onChange={e=>setSearch(e.target.value)}/></div>
    <div className="license-filters"><button className={statusFilter==='all'?'active':''} onClick={()=>setStatusFilter('all')}>Todas</button><button className={statusFilter==='active'?'active':''} onClick={()=>setStatusFilter('active')}>Ativas</button><button className={statusFilter==='past_due'?'active':''} onClick={()=>setStatusFilter('past_due')}>Em atraso</button><button className={statusFilter==='suspended'?'active':''} onClick={()=>setStatusFilter('suspended')}>Suspensas</button></div>
    <div className="license-items">{loading&&rows.length===0?<div className="empty">Carregando rede...</div>:visible.length===0?<div className="empty">Nenhuma operação encontrada.</div>:visible.map(row=>{const s=statusMap[row.license_status];return <button key={row.id} className={'license-item '+(row.id===selectedId?'selected':'')} onClick={()=>setSelectedId(row.id)}><div className="license-item-top"><span className="license-avatar">{row.trade_name.slice(0,2).toUpperCase()}</span><div><strong>{row.trade_name}</strong><small>{row.cities?.map(c=>`${c.name}/${c.state}`).join(' · ')||'Território pendente'}</small></div><ChevronRight size={17}/></div><div className="license-item-meta"><span className={'pill '+s.className}>{s.label}</span><span>{row.plan_name||'Sem plano'}</span><b>{number(row.rides_month)} corridas</b></div></button>})}</div>
   </aside>

   <section className="license-detail">
    {!selected?<div className="card empty-state"><Building2 size={34}/><h2>Selecione uma operação</h2><p>Os dados completos da licença aparecerão aqui.</p></div>:<>
     <div className={'card franchise-hero '+(supportMode?'support-active':'')}>
      {supportMode&&<div className="support-ribbon"><Headphones size={15}/> MODO SUPORTE ATIVO · visualização segura usando a sessão da Matriz</div>}
      <div className="franchise-hero-row"><div className="franchise-identity"><span className="franchise-logo">CG</span><div><div className="eyebrow">{selected.plan_name||'Licença sem plano'}</div><h1>{selected.trade_name}</h1><p>{selected.cities?.map(c=>`${c.name}/${c.state}`).join(' · ')||'Território ainda não liberado'} · {selected.legal_name}</p></div></div><div className="franchise-hero-actions"><span className={'license-status '+statusMap[selected.license_status].className}>{statusMap[selected.license_status].label}</span><button className="button secondary" onClick={()=>setSupportMode(v=>!v)} disabled={!selected.support_mode_enabled}><Headphones size={16}/>{supportMode?'Sair do suporte':'Entrar como suporte'}</button></div></div>
      <div className="franchise-hero-metrics"><div><span>Corridas no mês</span><strong>{number(selected.rides_month)}</strong><small>{selected.included_rides>0?`${number(selected.included_rides)} incluídas no plano`:'sem franquia de corridas'}</small></div><div><span>Excedentes</span><strong>{number(selected.overage_rides)}</strong><small>{money(selected.overage_fee_per_ride)} por excedente</small></div><div><span>Valor à Matriz</span><strong>{money(realDue)}</strong><small>{selected.invoice_status?'fatura '+selected.invoice_status:'cálculo em tempo real'}</small></div><div><span>Próximo vencimento</span><strong>{date(selected.next_due_date)}</strong><small>dia padrão {selected.due_day}</small></div></div>
     </div>

     <div className="franchise-grid-3">
      <div className="card management-card"><div className="management-card-title"><CircleDollarSign size={18}/><div><strong>Licença e cobrança</strong><span>Controle comercial da matriz</span></div></div><dl><div><dt>Plano</dt><dd>{selected.plan_name||'Não contratado'}</dd></div><div><dt>Mensalidade</dt><dd>{money(selected.monthly_fee)}</dd></div><div><dt>Uso no mês</dt><dd>{money(selected.computed_usage_fee)}</dd></div><div><dt>Modelo</dt><dd>{selected.billing_model||'—'}</dd></div><div><dt>Implantação</dt><dd>{money(selected.setup_fee)}</dd></div></dl><div className="inline-control"><select className="input" value={planToAssign} onChange={e=>setPlanToAssign(e.target.value)}><option value="">Trocar/aplicar plano</option>{plans.filter(p=>p.active).map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><button className="button" disabled={!planToAssign||busy==='plan'} onClick={assignPlan}>{busy==='plan'?'Aplicando...':'Aplicar'}</button></div></div>
      <div className="card management-card"><div className="management-card-title"><MapPinned size={18}/><div><strong>Território</strong><span>Exclusividade por cidade/região</span></div></div><div className="territory-chips">{selected.cities?.length?selected.cities.map(c=><span key={c.id}>{c.name}/{c.state}</span>):<em>Nenhuma cidade vinculada</em>}</div><div className="inline-control"><select className="input" value={cityToAssign} onChange={e=>setCityToAssign(e.target.value)}><option value="">Adicionar/transferir cidade</option>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select><button className="button" disabled={!cityToAssign} onClick={assignCity}>Vincular</button></div><small className="management-note">Tipo contratado: {selected.territory_type==='city'?'cidade':selected.territory_type==='multi_city'?'múltiplas cidades':'região'}</small></div>
      <div className="card management-card"><div className="management-card-title"><FileCheck2 size={18}/><div><strong>Contrato e acesso</strong><span>Governança da operação</span></div></div><dl><div><dt>Contrato</dt><dd>{selected.contract_status}</dd></div><div><dt>Administrador</dt><dd>{selected.admin_name||'Pendente'}</dd></div><div><dt>E-mail</dt><dd>{selected.admin_email||selected.contact_email||'—'}</dd></div></dl><div className="inline-control"><select className="input" value={selected.contract_status} onChange={e=>void setContract(e.target.value)} disabled={busy==='contract'}><option value="pending">Contrato pendente</option><option value="signed">Assinado</option><option value="expired">Expirado</option><option value="cancelled">Cancelado</option></select><button className="button secondary" onClick={generateAccess} disabled={busy==='access'}><KeyRound size={15}/>{busy==='access'?'Gerando...':'Acesso admin'}</button></div></div>
     </div>

     {temp&&<div className="card temp-access"><div><span className="eyebrow">Senha temporária · mostrar uma única vez</span><h3>{temp.franchise}</h3></div><div><label>E-mail</label><strong>{temp.email}</strong></div><div><label>Senha temporária</label><strong>{temp.password}</strong></div><button className="button secondary" onClick={()=>setTemp(null)}>Ocultar</button></div>}

     <div className="franchise-grid-2">
      <div className="card onboarding-card"><div className="card-head-row"><div><div className="eyebrow">Implantação</div><h2>Checklist de liberação</h2></div><span className="progress-value">{completion}%</span></div><div className="progress-track"><span style={{width:`${completion}%`}}/></div><div className="onboarding-list">{onboarding.map(step=><button key={step.id} onClick={()=>void toggleStep(step)} className={step.completed?'done':''}>{step.completed?<CheckCircle2 size={19}/>:<span className="step-circle"/>}<span><strong>{step.label}</strong><small>{step.completed?`Concluído ${dateTime(step.completed_at)}`:'Pendente'}</small></span></button>)}</div></div>
      <div className="card operation-card"><div className="card-head-row"><div><div className="eyebrow">Operação ao vivo</div><h2>Apps e atividade</h2></div><Activity size={22}/></div><div className="operation-metrics"><div><CarFront/><span><strong>{number(selected.drivers_online)}</strong> online</span></div><div><UsersRound/><span><strong>{number(selected.drivers)}</strong> motoristas</span></div><div><Smartphone/><span><strong>{number(selected.passengers_month)}</strong> passageiros/mês</span></div><div><Gauge/><span><strong>{number(selected.drivers_pending)}</strong> aprovações</span></div></div><div className="module-strip">{Object.entries(selected.enabled_modules||{}).map(([key,on])=><span key={key} className={on?'on':'off'}>{on?<BadgeCheck size={13}/>:<XCircle size={13}/>} {moduleNames[key]||key}</span>)}</div>{supportMode&&<div className="support-panel"><strong>Visão de suporte da Matriz</strong><p>Você está vendo a operação com a sua própria credencial de Super Admin. Nenhuma senha do franqueado é revelada ou utilizada.</p><div className="support-links"><Link href="/corridas">Corridas</Link><Link href="/mapa">Mapa</Link><Link href="/motoristas">Motoristas</Link><Link href="/tarifas">Tarifas</Link><Link href="/suporte">Chamados</Link></div></div>}</div>
     </div>

     <div className="franchise-grid-2">
      <div className="card sync-card"><div className="card-head-row"><div><div className="eyebrow">Sincronização</div><h2>Painel ↔ Apps</h2></div><span className="sync-version">v{selected.config_version}</span></div><p className="subtitle">Tarifas, pagamentos, anúncios, cupons, promoções e regras locais geram uma nova versão de configuração.</p><div className="sync-status"><span><CheckCircle2 size={16}/> Configuração centralizada</span><span><RefreshCw size={16}/> Apps consultam a versão ativa</span><span><Activity size={16}/> Corridas retornam em tempo real ao painel</span></div><div className="sync-last"><span>Última mudança</span><strong>{dateTime(selected.config_changed_at)}</strong><small>{sourceLabel[selected.config_changed_source||'']||selected.config_changed_source||'Sem alterações registradas'}</small></div></div>
      <div className="card event-card"><div className="card-head-row"><div><div className="eyebrow">Auditoria técnica</div><h2>Últimas alterações sincronizadas</h2></div><Settings2 size={20}/></div><div className="event-list">{events.length===0?<p className="empty">Ainda não há alterações de configuração registradas.</p>:events.map(ev=><div key={ev.id}><span className="event-dot"/><div><strong>{entityLabel[ev.entity]||ev.entity}</strong><small>{sourceLabel[ev.source]||ev.source} · {ev.action} · versão {ev.version}</small></div><time>{dateTime(ev.created_at)}</time></div>)}</div></div>
     </div>

     <div className="card license-actions"><div><div className="eyebrow">Controle da Matriz</div><h2>Status da licença</h2><p className="subtitle">A rotina diária também ajusta automaticamente atraso e suspensão com base nas faturas e carência do plano.</p></div><div className="license-action-buttons"><button disabled={busy==='license'} onClick={()=>void setLicense('active')}><BadgeCheck/>Ativar</button><button disabled={busy==='license'} onClick={()=>void setLicense('past_due')}><CalendarClock/>Marcar atraso</button><button disabled={busy==='license'} onClick={()=>void setLicense('suspended')}><Ban/>Suspender</button><button disabled={busy==='license'} onClick={()=>void setLicense('cancelled')} className="danger"><XCircle/>Cancelar</button></div></div>
    </>}
   </section>
  </div>
 </div>
}
