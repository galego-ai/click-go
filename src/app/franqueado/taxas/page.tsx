'use client'

import { useEffect,useMemo,useState } from 'react'
import { supabase } from '@/lib/supabase'

type FeeMode='fixed'|'percentage'
type Driver={id:string;status:string}
type Profile={id:string;full_name:string|null;email:string|null}
type Billing={driver_id:string;billing_mode:'wallet_per_ride'|'monthly';per_ride_fee:number|string;ride_fee_mode:FeeMode|null;ride_fee_percentage:number|string|null;monthly_fee:number|string;monthly_due_day:number;monthly_paid_until:string|null;active:boolean}
type GlobalWallet={enabled:boolean;minimum_balance_to_receive:number|string;low_balance_threshold:number|string;default_ride_fee:number|string;default_ride_fee_mode:FeeMode;default_ride_fee_percentage:number|string;franchise_can_set_ride_fee:boolean}
type LocalWallet={franchise_id:string;ride_fee:number|string|null;ride_fee_mode:FeeMode|null;ride_fee_percentage:number|string|null;minimum_balance_to_receive:number|string|null;low_balance_threshold:number|string|null;locked_by_matrix:boolean}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'10px 11px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:9,padding:'10px 13px',fontWeight:800,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const num=(v:string)=>Number(v.replace(',','.'))||0

export default function FranchiseFeesPage(){
 const[fid,setFid]=useState(''),[drivers,setDrivers]=useState<Driver[]>([]),[profiles,setProfiles]=useState<Profile[]>([]),[billings,setBillings]=useState<Billing[]>([]),[globalWallet,setGlobalWallet]=useState<GlobalWallet|null>(null),[localWallet,setLocalWallet]=useState<LocalWallet|null>(null),[selected,setSelected]=useState(''),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 const[franchiseForm,setFranchiseForm]=useState({mode:'fixed' as FeeMode,fixed:'0',percentage:'0',minimum:'0.01',low:'5'})
 const[driverForm,setDriverForm]=useState({billingMode:'wallet_per_ride' as 'wallet_per_ride'|'monthly',feeMode:'fixed' as FeeMode,fixed:'0',percentage:'0',monthly:'0',dueDay:'10'})
 useEffect(()=>{load()},[])
 useEffect(()=>{if(selected)applyDriver(selected)},[selected,billings,franchiseForm.mode,franchiseForm.fixed,franchiseForm.percentage])

 async function load(){
  setBusy(true);setMsg('')
  try{
   const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login.')
   const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
   if(p?.role!=='franchise_admin'||!p.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
   setFid(p.franchise_id)
   const[{data:g,error:ge},{data:l,error:le},{data:d,error:de},{data:b,error:be}]=await Promise.all([
    supabase.from('platform_operational_wallet_settings').select('enabled,minimum_balance_to_receive,low_balance_threshold,default_ride_fee,default_ride_fee_mode,default_ride_fee_percentage,franchise_can_set_ride_fee').eq('scope','global').single(),
    supabase.from('franchise_operational_wallet_settings').select('franchise_id,ride_fee,ride_fee_mode,ride_fee_percentage,minimum_balance_to_receive,low_balance_threshold,locked_by_matrix').eq('franchise_id',p.franchise_id).maybeSingle(),
    supabase.from('drivers').select('id,status').eq('franchise_id',p.franchise_id).order('created_at',{ascending:false}),
    supabase.from('driver_billing_settings').select('driver_id,billing_mode,per_ride_fee,ride_fee_mode,ride_fee_percentage,monthly_fee,monthly_due_day,monthly_paid_until,active').eq('franchise_id',p.franchise_id)
   ])
   if(ge)throw ge;if(le)throw le;if(de)throw de;if(be)throw be
   const ids=(d||[]).map(x=>x.id)
   const{data:pr,error:pre}=ids.length?await supabase.from('profiles').select('id,full_name,email').in('id',ids):{data:[],error:null} as any
   if(pre)throw pre
   setGlobalWallet(g as GlobalWallet);setLocalWallet((l||null) as LocalWallet|null);setDrivers((d||[]) as Driver[]);setBillings((b||[]) as Billing[]);setProfiles((pr||[]) as Profile[])
   const mode=(l?.ride_fee_mode||g?.default_ride_fee_mode||'fixed') as FeeMode
   setFranchiseForm({mode,fixed:String(l?.ride_fee??g?.default_ride_fee??0),percentage:String(l?.ride_fee_percentage??g?.default_ride_fee_percentage??0),minimum:String(l?.minimum_balance_to_receive??g?.minimum_balance_to_receive??0.01),low:String(l?.low_balance_threshold??g?.low_balance_threshold??5)})
   if(!selected&&ids[0])setSelected(ids[0])
  }catch(e:any){setMsg(e.message||'Erro ao carregar taxas.')}finally{setBusy(false)}
 }

 const names=useMemo(()=>Object.fromEntries(profiles.map(p=>[p.id,p])),[profiles])
 function billing(id:string){return billings.find(b=>b.driver_id===id)}
 function applyDriver(id:string){const b=billing(id);setDriverForm({billingMode:b?.billing_mode||'wallet_per_ride',feeMode:(b?.ride_fee_mode||franchiseForm.mode||'fixed') as FeeMode,fixed:String(b?.per_ride_fee??franchiseForm.fixed??0),percentage:String(b?.ride_fee_percentage??franchiseForm.percentage??0),monthly:String(b?.monthly_fee??0),dueDay:String(b?.monthly_due_day??10)})}

 async function saveFranchise(){
  if(!fid||!globalWallet)return
  if(localWallet?.locked_by_matrix){setMsg('A Matriz bloqueou as regras da carteira desta franquia.');return}
  if(!globalWallet.franchise_can_set_ride_fee){setMsg('A Matriz não permite alterar o tipo/valor da taxa. O franqueado só pode ajustar os limites de saldo.');return}
  const percentage=num(franchiseForm.percentage);if(franchiseForm.mode==='percentage'&&(percentage<0||percentage>100)){setMsg('O percentual deve ficar entre 0% e 100%.');return}
  setBusy(true)
  const{error}=await supabase.from('franchise_operational_wallet_settings').upsert({franchise_id:fid,ride_fee_mode:franchiseForm.mode,ride_fee:num(franchiseForm.fixed),ride_fee_percentage:percentage,minimum_balance_to_receive:num(franchiseForm.minimum),low_balance_threshold:num(franchiseForm.low),locked_by_matrix:false,updated_at:new Date().toISOString()},{onConflict:'franchise_id'})
  setBusy(false);if(error){setMsg(error.message);return}
  setMsg(franchiseForm.mode==='percentage'?`Regra da franquia salva: ${percentage.toLocaleString('pt-BR')}% do valor da corrida.`:`Regra da franquia salva: ${money(num(franchiseForm.fixed))} por corrida.`);await load()
 }

 async function saveDriver(){
  if(!selected)return
  const percentage=num(driverForm.percentage);if(driverForm.feeMode==='percentage'&&(percentage<0||percentage>100)){setMsg('O percentual deve ficar entre 0% e 100%.');return}
  setBusy(true)
  const{error}=await supabase.rpc('set_driver_billing',{p_driver_id:selected,p_billing_mode:driverForm.billingMode,p_per_ride_fee:num(driverForm.fixed),p_monthly_fee:num(driverForm.monthly),p_monthly_due_day:Math.max(1,Math.min(28,Number(driverForm.dueDay)||10)),p_ride_fee_mode:driverForm.feeMode,p_ride_fee_percentage:percentage})
  setBusy(false);if(error){setMsg(error.message);return}
  if(driverForm.billingMode==='monthly')setMsg(`Motorista configurado com mensalidade de ${money(num(driverForm.monthly))}.`)
  else if(driverForm.feeMode==='percentage')setMsg(`Motorista configurado com desconto de ${percentage.toLocaleString('pt-BR')}% por corrida.`)
  else setMsg(`Motorista configurado com desconto fixo de ${money(num(driverForm.fixed))} por corrida.`)
  await load()
 }

 const current=drivers.find(d=>d.id===selected),p=current?names[current.id]:null
 const exampleFare=40
 const exampleFee=driverForm.feeMode==='percentage'?exampleFare*num(driverForm.percentage)/100:num(driverForm.fixed)
 const controlsLocked=!!localWallet?.locked_by_matrix||!globalWallet?.franchise_can_set_ride_fee

 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:20}}><div style={{maxWidth:1200,margin:'0 auto',display:'grid',gap:14}}>
  <div><div className="eyebrow">Painel do franqueado</div><h1>Taxas do motorista — R$ ou %</h1><p className="subtitle">O saldo operacional libera chamadas e cobre automaticamente taxas e comissões. A taxa por corrida pode ser um valor fixo em reais ou um percentual sobre o valor da corrida.</p></div>

  <section style={{...box,borderColor:'#665600'}}><h2>Regra padrão da franquia</h2>{localWallet?.locked_by_matrix&&<p style={{color:'#fbbf24'}}>Esta regra foi bloqueada pela Matriz.</p>}{globalWallet&&!globalWallet.franchise_can_set_ride_fee&&<p style={{color:'#fbbf24'}}>Tipo e valor da taxa são definidos somente pela Matriz.</p>}
   <div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:10}}>
    <label>Forma da taxa<select style={input} value={franchiseForm.mode} disabled={controlsLocked} onChange={e=>setFranchiseForm({...franchiseForm,mode:e.target.value as FeeMode})}><option value="fixed">R$ fixo por corrida</option><option value="percentage">% sobre a corrida</option></select></label>
    {franchiseForm.mode==='fixed'?<label>Valor em R$<input type="number" min="0" step="0.01" style={input} value={franchiseForm.fixed} disabled={controlsLocked} onChange={e=>setFranchiseForm({...franchiseForm,fixed:e.target.value})}/></label>:<label>Percentual (%)<input type="number" min="0" max="100" step="0.01" style={input} value={franchiseForm.percentage} disabled={controlsLocked} onChange={e=>setFranchiseForm({...franchiseForm,percentage:e.target.value})}/></label>}
    <label>Saldo mínimo para chamadas<input type="number" min="0" step="0.01" style={input} value={franchiseForm.minimum} disabled={!!localWallet?.locked_by_matrix} onChange={e=>setFranchiseForm({...franchiseForm,minimum:e.target.value})}/></label>
    <label>Alerta de saldo baixo<input type="number" min="0" step="0.01" style={input} value={franchiseForm.low} disabled={!!localWallet?.locked_by_matrix} onChange={e=>setFranchiseForm({...franchiseForm,low:e.target.value})}/></label>
   </div><button style={{...btn,marginTop:12}} disabled={busy||!!localWallet?.locked_by_matrix} onClick={saveFranchise}>Salvar regra da franquia</button>
  </section>

  <div style={{display:'grid',gridTemplateColumns:'340px minmax(0,1fr)',gap:14}}>
   <aside style={box}><h2>Motoristas</h2><div style={{display:'grid',gap:8,maxHeight:650,overflow:'auto'}}>{drivers.map(d=><button key={d.id} onClick={()=>setSelected(d.id)} style={{...box,textAlign:'left',color:'#fff',cursor:'pointer',outline:selected===d.id?'2px solid #ffd400':'none'}}><b>{names[d.id]?.full_name||names[d.id]?.email||d.id.slice(0,8)}</b><div style={{color:'#9ca3af',fontSize:12,marginTop:4}}>Cadastro: {d.status}</div>{billing(d.id)&&<div style={{color:'#fde68a',fontSize:12,marginTop:3}}>{billing(d.id)?.billing_mode==='monthly'?`Mensal ${money(billing(d.id)?.monthly_fee)}`:billing(d.id)?.ride_fee_mode==='percentage'?`${Number(billing(d.id)?.ride_fee_percentage||0).toLocaleString('pt-BR')}% por corrida`:`${money(billing(d.id)?.per_ride_fee)} por corrida`}</div>}</button>)}{!drivers.length&&<div style={{color:'#9ca3af'}}>Nenhum motorista cadastrado.</div>}</div></aside>

   <section style={{display:'grid',gap:14}}>{current?<><div style={box}><div className="label">Motorista selecionado</div><h2>{p?.full_name||p?.email||current.id}</h2><div style={{color:'#9ca3af'}}>A configuração individual substitui o padrão da franquia para este motorista.</div></div>
    <div style={box}><h3>Modelo de cobrança</h3><div style={{display:'grid',gridTemplateColumns:'repeat(3,minmax(0,1fr))',gap:10}}><label>Modelo<select style={input} value={driverForm.billingMode} onChange={e=>setDriverForm({...driverForm,billingMode:e.target.value as any})}><option value="wallet_per_ride">Carteira operacional</option><option value="monthly">Mensalidade fixa</option></select></label>
     {driverForm.billingMode==='wallet_per_ride'?<><label>Tipo da taxa<select style={input} value={driverForm.feeMode} onChange={e=>setDriverForm({...driverForm,feeMode:e.target.value as FeeMode})}><option value="fixed">R$ fixo</option><option value="percentage">Percentual (%)</option></select></label>{driverForm.feeMode==='fixed'?<label>Valor por corrida<input type="number" min="0" step="0.01" style={input} value={driverForm.fixed} onChange={e=>setDriverForm({...driverForm,fixed:e.target.value})}/></label>:<label>Percentual por corrida<input type="number" min="0" max="100" step="0.01" style={input} value={driverForm.percentage} onChange={e=>setDriverForm({...driverForm,percentage:e.target.value})}/></label>}</>:<><label>Mensalidade<input type="number" min="0" step="0.01" style={input} value={driverForm.monthly} onChange={e=>setDriverForm({...driverForm,monthly:e.target.value})}/></label><label>Vencimento (dia)<input type="number" min="1" max="28" style={input} value={driverForm.dueDay} onChange={e=>setDriverForm({...driverForm,dueDay:e.target.value})}/></label></>}</div>
     {driverForm.billingMode==='wallet_per_ride'&&<div style={{marginTop:12,padding:12,borderRadius:12,background:'#0d0d0d',color:'#d1d5db'}}>Exemplo em uma corrida de <b>{money(exampleFare)}</b>: desconto operacional <b style={{color:'#ffd400'}}>{money(exampleFee)}</b>. Nas corridas em dinheiro ou maquininha, as comissões recebidas diretamente pelo motorista também são descontadas automaticamente do mesmo saldo.</div>}
     <button style={{...btn,marginTop:12}} disabled={busy} onClick={saveDriver}>Salvar configuração do motorista</button>
    </div></>:<div style={box}>Selecione um motorista.</div>}</section>
  </div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b'}}>{msg}</div>}
 </div></main>
}
