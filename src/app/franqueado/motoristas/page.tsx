'use client'

import Link from 'next/link'
import {useEffect,useMemo,useState} from 'react'
import {supabase} from '@/lib/supabase'

type DriverStatus='pending'|'approved'|'rejected'|'blocked'
type BillingMode='wallet_per_ride'|'monthly'
type RideFeeMode='fixed'|'percentage'
type Driver={
 id:string;status:DriverStatus;online:boolean;rating:number|string;city_id:string|null;city_name:string|null;city_state:string|null;created_at:string;
 has_card_machine:boolean;card_machine_approved:boolean;full_name:string|null;email:string|null;phone:string|null;cpf:string|null;cnh_number:string|null;cnh_category:string|null;pix_key:string|null;
 vehicle_id:string|null;vehicle_make:string|null;vehicle_model:string|null;vehicle_year:number|null;vehicle_plate:string|null;vehicle_color:string|null;vehicle_type:string|null;
 balance:number|string;billing_mode:BillingMode;ride_fee_mode:RideFeeMode;per_ride_fee:number|string;ride_fee_percentage:number|string;monthly_fee:number|string;monthly_due_day:number;monthly_paid_until:string|null;
 minimum_balance:number|string;low_balance_threshold:number|string;operational_enabled:boolean
}

type EditForm={full_name:string;phone:string;cpf:string;cnh_number:string;cnh_category:string;pix_key:string;status:DriverStatus;rejection_reason:string;has_card_machine:boolean;vehicle_make:string;vehicle_model:string;vehicle_year:string;vehicle_plate:string;vehicle_color:string;vehicle_type:string}
type BillingForm={billing_mode:BillingMode;ride_fee_mode:RideFeeMode;per_ride_fee:string;ride_fee_percentage:string;monthly_fee:string;monthly_due_day:string;monthly_paid_until:string}

const money=(value:unknown)=>Number(value||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const num=(value:string)=>Number(value.replace(',','.'))
const nextMonth=()=>{const d=new Date();d.setMonth(d.getMonth()+1);return d.toISOString().slice(0,10)}
const card:React.CSSProperties={background:'#fff',border:'1px solid #e5e7eb',borderRadius:16,padding:18,boxShadow:'0 1px 2px rgba(0,0,0,.03)'}
const input:React.CSSProperties={width:'100%',border:'1px solid #d1d5db',borderRadius:10,padding:'10px 11px',background:'#fff',color:'#111827',fontSize:14}
const label:React.CSSProperties={display:'grid',gap:6,fontSize:12,fontWeight:700,color:'#4b5563'}
const button:React.CSSProperties={border:0,borderRadius:10,padding:'10px 13px',fontWeight:800,cursor:'pointer',background:'#ffd400',color:'#111'}

function editFrom(d:Driver):EditForm{return {full_name:d.full_name||'',phone:d.phone||'',cpf:d.cpf||'',cnh_number:d.cnh_number||'',cnh_category:(d.cnh_category||'AB').toUpperCase(),pix_key:d.pix_key||'',status:d.status,rejection_reason:'',has_card_machine:!!d.has_card_machine,vehicle_make:d.vehicle_make||'',vehicle_model:d.vehicle_model||'',vehicle_year:d.vehicle_year?String(d.vehicle_year):'',vehicle_plate:d.vehicle_plate||'',vehicle_color:d.vehicle_color||'',vehicle_type:d.vehicle_type||'car'}}
function billingFrom(d:Driver):BillingForm{return {billing_mode:d.billing_mode||'wallet_per_ride',ride_fee_mode:d.ride_fee_mode||'fixed',per_ride_fee:String(d.per_ride_fee??0),ride_fee_percentage:String(d.ride_fee_percentage??0),monthly_fee:String(d.monthly_fee??0),monthly_due_day:String(d.monthly_due_day??10),monthly_paid_until:d.monthly_paid_until||nextMonth()}}

export default function FranchiseDriversPage(){
 const[drivers,setDrivers]=useState<Driver[]>([]),[selectedId,setSelectedId]=useState(''),[search,setSearch]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState(''),[msg,setMsg]=useState('')
 const[edit,setEdit]=useState<EditForm|null>(null),[billing,setBilling]=useState<BillingForm|null>(null),[creditAmount,setCreditAmount]=useState('50'),[creditReason,setCreditReason]=useState('Ajuste manual do franqueado')

 useEffect(()=>{void load()},[])
 const selected=useMemo(()=>drivers.find(d=>d.id===selectedId)||null,[drivers,selectedId])
 const filtered=useMemo(()=>{const q=search.trim().toLowerCase();if(!q)return drivers;return drivers.filter(d=>[d.full_name,d.email,d.phone,d.vehicle_plate,d.vehicle_model,d.city_name].some(v=>String(v||'').toLowerCase().includes(q)))},[drivers,search])
 const online=drivers.filter(d=>d.online).length,approved=drivers.filter(d=>d.status==='approved').length,pending=drivers.filter(d=>d.status==='pending').length,blocked=drivers.filter(d=>d.status==='blocked').length

 async function load(preferId?:string){
  setLoading(true);setMsg('')
  const{data,error}=await supabase.rpc('franchise_list_driver_management')
  if(error){setMsg(error.message);setLoading(false);return}
  const list=(Array.isArray(data)?data:[]) as Driver[]
  setDrivers(list)
  const id=(preferId&&list.some(d=>d.id===preferId)?preferId:selectedId&&list.some(d=>d.id===selectedId)?selectedId:list[0]?.id)||''
  setSelectedId(id)
  const current=list.find(d=>d.id===id)
  if(current){setEdit(editFrom(current));setBilling(billingFrom(current))}else{setEdit(null);setBilling(null)}
  setLoading(false)
 }

 function choose(d:Driver){setSelectedId(d.id);setEdit(editFrom(d));setBilling(billingFrom(d));setMsg('')}
 async function saveDriver(){
  if(!selected||!edit)return
  if(!edit.full_name.trim()){setMsg('Informe o nome do motorista.');return}
  if(edit.status==='rejected'&&!edit.rejection_reason.trim()){setMsg('Informe o motivo da rejeição.');return}
  setBusy('driver');setMsg('')
  const payload={...edit,vehicle_year:edit.vehicle_year?Number(edit.vehicle_year):null}
  const{error}=await supabase.rpc('franchise_update_driver_management',{p_driver_id:selected.id,p_payload:payload})
  setBusy('')
  if(error){setMsg(error.message);return}
  setMsg('Dados do motorista atualizados com sucesso.');await load(selected.id)
 }

 async function saveBilling(){
  if(!selected||!billing)return
  const perRide=num(billing.per_ride_fee),percentage=num(billing.ride_fee_percentage),monthly=num(billing.monthly_fee),due=Number(billing.monthly_due_day)
  if([perRide,percentage,monthly,due].some(v=>!Number.isFinite(v))){setMsg('Revise os valores da cobrança.');return}
  if(percentage<0||percentage>100){setMsg('O percentual deve ficar entre 0% e 100%.');return}
  if(due<1||due>28){setMsg('O vencimento mensal deve ficar entre os dias 1 e 28.');return}
  setBusy('billing');setMsg('')
  const{error}=await supabase.rpc('set_driver_billing',{p_driver_id:selected.id,p_billing_mode:billing.billing_mode,p_per_ride_fee:perRide,p_monthly_fee:monthly,p_monthly_due_day:due,p_ride_fee_mode:billing.ride_fee_mode,p_ride_fee_percentage:percentage})
  setBusy('')
  if(error){setMsg(error.message);return}
  const text=billing.billing_mode==='monthly'?`Mensalidade de ${money(monthly)} configurada.`:billing.ride_fee_mode==='percentage'?`Cobrança de ${percentage.toLocaleString('pt-BR')}% por corrida configurada.`:`Cobrança de ${money(perRide)} por corrida configurada.`
  setMsg(text);await load(selected.id)
 }

 async function markMonthlyPaid(){
  if(!selected||!billing)return
  if(!billing.monthly_paid_until){setMsg('Escolha a data de validade da mensalidade.');return}
  setBusy('monthly');const{error}=await supabase.rpc('mark_driver_monthly_paid',{p_driver_id:selected.id,p_paid_until:billing.monthly_paid_until,p_reason:'Mensalidade confirmada no painel do franqueado'});setBusy('')
  if(error){setMsg(error.message);return}setMsg('Mensalidade registrada como paga.');await load(selected.id)
 }

 async function adjustCredit(sign:1|-1){
  if(!selected)return
  const amount=num(creditAmount)
  if(!Number.isFinite(amount)||amount<=0){setMsg('Informe um valor de crédito maior que zero.');return}
  if(!creditReason.trim()){setMsg('Informe o motivo do ajuste.');return}
  const action=sign===1?'credit':'debit';setBusy(action);setMsg('')
  const{data,error}=await supabase.rpc('adjust_driver_operational_balance',{p_driver_id:selected.id,p_amount:amount*sign,p_reason:creditReason.trim()});setBusy('')
  if(error){setMsg(error.message);return}setMsg(`Saldo atualizado para ${money(data)}.`);await load(selected.id)
 }

 async function toggleMachine(){
  if(!selected)return
  if(!selected.has_card_machine&&!selected.card_machine_approved){setMsg('Marque primeiro que o motorista possui maquininha e salve os dados.');return}
  setBusy('machine');const{error}=await supabase.rpc('set_driver_card_machine_approval',{p_driver_id:selected.id,p_approved:!selected.card_machine_approved});setBusy('')
  if(error){setMsg(error.message);return}setMsg(selected.card_machine_approved?'Autorização da maquininha removida.':'Maquininha autorizada.');await load(selected.id)
 }

 return <div className="driver-console">
  <style>{`.driver-console{max-width:1400px;margin:0 auto}.driver-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px}.driver-head h1{margin:3px 0 6px;font-size:30px}.driver-tools{display:flex;gap:8px;flex-wrap:wrap}.driver-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}.driver-kpi{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:14px}.driver-kpi span{display:block;color:#6b7280;font-size:12px}.driver-kpi strong{display:block;font-size:25px;margin-top:5px}.driver-grid{display:grid;grid-template-columns:340px minmax(0,1fr);gap:14px}.driver-list{display:grid;gap:8px;max-height:820px;overflow:auto}.driver-item{width:100%;text-align:left;border:1px solid #e5e7eb;background:#fff;border-radius:12px;padding:12px;cursor:pointer}.driver-item.active{border-color:#d6b300;box-shadow:0 0 0 2px rgba(255,212,0,.3)}.driver-item-top{display:flex;justify-content:space-between;gap:8px}.driver-item small{display:block;color:#6b7280;margin-top:4px}.driver-status{font-size:11px;font-weight:800;border-radius:999px;padding:4px 7px;background:#f3f4f6;white-space:nowrap}.driver-status.approved{background:#dcfce7;color:#166534}.driver-status.pending{background:#fef3c7;color:#92400e}.driver-status.blocked,.driver-status.rejected{background:#fee2e2;color:#991b1b}.driver-sections{display:grid;gap:14px}.driver-form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.driver-finance-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.driver-msg{padding:12px 14px;border-radius:12px;background:#fffbeb;border:1px solid #fde68a;color:#713f12;margin-bottom:14px}.driver-muted{color:#6b7280;font-size:13px}.driver-balance{font-size:28px;font-weight:900;margin:5px 0}.driver-balance.negative{color:#b91c1c}.driver-balance.positive{color:#166534}@media(max-width:1050px){.driver-grid{grid-template-columns:1fr}.driver-list{max-height:340px}.driver-form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:700px){.driver-head{display:block}.driver-tools{margin-top:12px}.driver-kpis,.driver-form-grid,.driver-finance-grid{grid-template-columns:1fr}}`}</style>
  <div className="driver-head"><div><div className="eyebrow">Painel do franqueado</div><h1>Motoristas</h1><p className="subtitle">Liste, edite, aprove ou bloqueie motoristas e controle créditos e forma de cobrança.</p></div><div className="driver-tools"><Link href="/franqueado/cadastros" className="button">+ Cadastrar motorista</Link><button className="button secondary" onClick={()=>void load(selectedId)} disabled={loading}>{loading?'Atualizando…':'Atualizar lista'}</button></div></div>
  {msg&&<div className="driver-msg">{msg}</div>}
  <div className="driver-kpis"><div className="driver-kpi"><span>Total cadastrados</span><strong>{drivers.length}</strong></div><div className="driver-kpi"><span>Aprovados</span><strong>{approved}</strong></div><div className="driver-kpi"><span>Online agora</span><strong>{online}</strong></div><div className="driver-kpi"><span>Pendentes / bloqueados</span><strong>{pending} / {blocked}</strong></div></div>
  <div className="driver-grid">
   <aside style={card}><input style={input} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar nome, e-mail, placa…"/><div className="driver-list" style={{marginTop:10}}>{filtered.map(d=><button key={d.id} className={`driver-item ${d.id===selectedId?'active':''}`} onClick={()=>choose(d)}><div className="driver-item-top"><b>{d.full_name||'Motorista sem nome'}</b><span className={`driver-status ${d.status}`}>{d.status==='approved'?'Aprovado':d.status==='pending'?'Pendente':d.status==='blocked'?'Bloqueado':'Rejeitado'}</span></div><small>{d.email||'Sem e-mail'}</small><small>{d.vehicle_plate||'Sem placa'} · {d.vehicle_model||'Veículo não informado'}</small><small>{d.city_name?`${d.city_name}/${d.city_state||''}`:'Cidade não informada'} · {d.online?'🟢 online':'⚪ offline'}</small></button>)}{!loading&&!filtered.length&&<div className="driver-muted" style={{padding:12}}>Nenhum motorista encontrado.</div>}</div></aside>
   <section className="driver-sections">{selected&&edit&&billing?<>
    <div style={card}><div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}><div><div className="driver-muted">Motorista selecionado</div><h2 style={{margin:'3px 0'}}>{selected.full_name||selected.email}</h2><div className="driver-muted">{selected.email} · avaliação {Number(selected.rating||0).toFixed(1)} · {selected.city_name}/{selected.city_state}</div></div><div><span className={`driver-status ${selected.status}`}>{selected.status}</span></div></div></div>
    <div style={card}><h3 style={{marginTop:0}}>Dados do motorista e veículo</h3><div className="driver-form-grid"><label style={label}>Nome completo<input style={input} value={edit.full_name} onChange={e=>setEdit({...edit,full_name:e.target.value})}/></label><label style={label}>E-mail<input style={{...input,background:'#f3f4f6'}} value={selected.email||''} readOnly title="O e-mail de login não é alterado por esta tela."/></label><label style={label}>Telefone<input style={input} value={edit.phone} onChange={e=>setEdit({...edit,phone:e.target.value})}/></label><label style={label}>CPF<input style={input} value={edit.cpf} onChange={e=>setEdit({...edit,cpf:e.target.value})}/></label><label style={label}>CNH<input style={input} value={edit.cnh_number} onChange={e=>setEdit({...edit,cnh_number:e.target.value})}/></label><label style={label}>Categoria CNH<select style={input} value={edit.cnh_category} onChange={e=>setEdit({...edit,cnh_category:e.target.value})}><option>A</option><option>B</option><option>AB</option><option>C</option><option>D</option><option>E</option></select></label><label style={label}>Chave PIX<input style={input} value={edit.pix_key} onChange={e=>setEdit({...edit,pix_key:e.target.value})}/></label><label style={label}>Status<select style={input} value={edit.status} onChange={e=>setEdit({...edit,status:e.target.value as DriverStatus})}><option value="pending">Pendente</option><option value="approved">Aprovado</option><option value="rejected">Rejeitado</option><option value="blocked">Bloqueado</option></select></label>{edit.status==='rejected'&&<label style={label}>Motivo da rejeição<input style={input} value={edit.rejection_reason} onChange={e=>setEdit({...edit,rejection_reason:e.target.value})}/></label>}<label style={{...label,alignContent:'end'}}><span><input type="checkbox" checked={edit.has_card_machine} onChange={e=>setEdit({...edit,has_card_machine:e.target.checked})}/> Motorista possui maquininha</span></label><label style={label}>Marca<input style={input} value={edit.vehicle_make} onChange={e=>setEdit({...edit,vehicle_make:e.target.value})}/></label><label style={label}>Modelo<input style={input} value={edit.vehicle_model} onChange={e=>setEdit({...edit,vehicle_model:e.target.value})}/></label><label style={label}>Ano<input type="number" min="1980" max="2100" style={input} value={edit.vehicle_year} onChange={e=>setEdit({...edit,vehicle_year:e.target.value})}/></label><label style={label}>Placa<input style={input} value={edit.vehicle_plate} onChange={e=>setEdit({...edit,vehicle_plate:e.target.value.toUpperCase()})}/></label><label style={label}>Cor<input style={input} value={edit.vehicle_color} onChange={e=>setEdit({...edit,vehicle_color:e.target.value})}/></label><label style={label}>Tipo<select style={input} value={edit.vehicle_type} onChange={e=>setEdit({...edit,vehicle_type:e.target.value})}><option value="car">Carro</option><option value="motorcycle">Moto</option></select></label></div><div style={{display:'flex',gap:8,marginTop:14,flexWrap:'wrap'}}><button style={button} disabled={busy==='driver'} onClick={()=>void saveDriver()}>{busy==='driver'?'Salvando…':'Salvar alterações'}</button>{selected.has_card_machine&&<button style={{...button,background:selected.card_machine_approved?'#fee2e2':'#dcfce7',color:selected.card_machine_approved?'#991b1b':'#166534'}} disabled={busy==='machine'} onClick={()=>void toggleMachine()}>{selected.card_machine_approved?'Revogar maquininha':'Autorizar maquininha'}</button>}</div></div>
    <div className="driver-finance-grid"><div style={card}><h3 style={{marginTop:0}}>Créditos do motorista</h3><div className="driver-muted">Saldo operacional atual</div><div className={`driver-balance ${Number(selected.balance)<0?'negative':'positive'}`}>{money(selected.balance)}</div><div style={{display:'grid',gap:9}}><label style={label}>Valor do ajuste<input type="number" min="0.01" step="0.01" style={input} value={creditAmount} onChange={e=>setCreditAmount(e.target.value)}/></label><label style={label}>Motivo<input style={input} value={creditReason} onChange={e=>setCreditReason(e.target.value)}/></label><div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button style={{...button,background:'#dcfce7',color:'#166534'}} disabled={!!busy} onClick={()=>void adjustCredit(1)}>{busy==='credit'?'Adicionando…':'Adicionar crédito'}</button><button style={{...button,background:'#fee2e2',color:'#991b1b'}} disabled={!!busy} onClick={()=>void adjustCredit(-1)}>{busy==='debit'?'Retirando…':'Retirar crédito'}</button></div></div><p className="driver-muted" style={{marginBottom:0}}>Todo ajuste exige motivo e fica registrado na auditoria financeira.</p></div>
     <div style={card}><h3 style={{marginTop:0}}>Como este motorista será cobrado</h3><label style={label}>Modelo<select style={input} value={billing.billing_mode} onChange={e=>setBilling({...billing,billing_mode:e.target.value as BillingMode})}><option value="wallet_per_ride">Cobrança por corrida</option><option value="monthly">Mensalidade fixa</option></select></label>{billing.billing_mode==='wallet_per_ride'?<><label style={{...label,marginTop:10}}>Forma da taxa<select style={input} value={billing.ride_fee_mode} onChange={e=>setBilling({...billing,ride_fee_mode:e.target.value as RideFeeMode})}><option value="fixed">Valor fixo por corrida</option><option value="percentage">Percentual da corrida</option></select></label>{billing.ride_fee_mode==='fixed'?<label style={{...label,marginTop:10}}>Valor por corrida<input type="number" min="0" step="0.01" style={input} value={billing.per_ride_fee} onChange={e=>setBilling({...billing,per_ride_fee:e.target.value})}/></label>:<label style={{...label,marginTop:10}}>Percentual por corrida (%)<input type="number" min="0" max="100" step="0.01" style={input} value={billing.ride_fee_percentage} onChange={e=>setBilling({...billing,ride_fee_percentage:e.target.value})}/></label>}</>:<><label style={{...label,marginTop:10}}>Valor da mensalidade<input type="number" min="0" step="0.01" style={input} value={billing.monthly_fee} onChange={e=>setBilling({...billing,monthly_fee:e.target.value})}/></label><label style={{...label,marginTop:10}}>Dia do vencimento<input type="number" min="1" max="28" style={input} value={billing.monthly_due_day} onChange={e=>setBilling({...billing,monthly_due_day:e.target.value})}/></label><label style={{...label,marginTop:10}}>Pago até<input type="date" style={input} value={billing.monthly_paid_until} onChange={e=>setBilling({...billing,monthly_paid_until:e.target.value})}/></label></>}<div style={{display:'flex',gap:8,marginTop:12,flexWrap:'wrap'}}><button style={button} disabled={busy==='billing'} onClick={()=>void saveBilling()}>{busy==='billing'?'Salvando…':'Salvar cobrança'}</button>{billing.billing_mode==='monthly'&&<button style={{...button,background:'#dcfce7',color:'#166534'}} disabled={busy==='monthly'} onClick={()=>void markMonthlyPaid()}>{busy==='monthly'?'Registrando…':'Registrar mensalidade paga'}</button>}</div><p className="driver-muted" style={{marginBottom:0}}>Mínimo para receber chamadas: {money(selected.minimum_balance)} · alerta de saldo baixo: {money(selected.low_balance_threshold)}.</p></div></div>
   </>:<div style={card}>{loading?'Carregando motoristas…':'Selecione um motorista para gerenciar.'}</div>}</section>
  </div>
 </div>
}
