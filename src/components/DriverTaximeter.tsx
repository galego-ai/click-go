'use client'

import { useEffect,useMemo,useRef,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Location={lat:number;lng:number}
type Category={category_id:string;category_name:string;base_fare:number|string;price_per_km:number|string;price_per_minute:number|string;minimum_fare:number|string;multiplier:number|string}
type Session={id:string;category_id:string;status:string;base_fare:number|string;price_per_km:number|string;price_per_minute:number|string;minimum_fare:number|string;multiplier:number|string;started_at:string;last_tick_at:string;ended_at:string|null;distance_m:number|string;elapsed_seconds:number;current_amount:number|string;final_amount:number|string|null;payment_method:string|null}
type Finance={gross_amount:number|string;fee_amount:number|string;pending_amount:number|string;driver_net_amount:number|string;charges_count:number;wallet_balance:number|string;effective_rule:{fee_mode:string;fee_value:number|string;source_scope:string}|null;recent:any[]}

const panel:React.CSSProperties={background:'#101010',border:'1px solid #333',borderRadius:18,padding:16}
const input:React.CSSProperties={background:'#080808',color:'#fff',border:'1px solid #3a3a3a',borderRadius:10,padding:'11px 12px'}
const button:React.CSSProperties={border:0,borderRadius:11,padding:'11px 14px',fontWeight:900,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const clock=(s:number)=>`${Math.floor(Math.max(0,s)/3600).toString().padStart(2,'0')}:${Math.floor((Math.max(0,s)%3600)/60).toString().padStart(2,'0')}:${Math.floor(Math.max(0,s)%60).toString().padStart(2,'0')}`
const feeRule=(r:Finance['effective_rule'])=>!r||r.fee_mode==='none'?'Sem taxa':r.fee_mode==='percentage'?`${Number(r.fee_value||0).toFixed(2)}% por corrida`:`${money(r.fee_value)} por corrida`

export default function DriverTaximeter({blockedByRide=false,showMoney=true}:{blockedByRide?:boolean;showMoney?:boolean}){
 const[categories,setCategories]=useState<Category[]>([]),[selected,setSelected]=useState(''),[session,setSession]=useState<Session|null>(null),[history,setHistory]=useState<Session[]>([]),[finance,setFinance]=useState<Finance|null>(null),[payment,setPayment]=useState('cash'),[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[now,setNow]=useState(Date.now())
 const ticking=useRef(false)
 useEffect(()=>{void load();const t=window.setInterval(()=>setNow(Date.now()),1000);return()=>window.clearInterval(t)},[])
 useEffect(()=>{if(!session||session.status!=='running')return;const t=window.setInterval(()=>void tick(),5000);return()=>window.clearInterval(t)},[session?.id,session?.status])
 async function load(){
  const{data:{user}}=await supabase.auth.getUser();if(!user)return
  const[{data:cats,error:ce},{data:running,error:re},{data:hist},{data:fin,error:fe}]=await Promise.all([
   supabase.rpc('get_my_taximeter_categories'),
   supabase.from('driver_taximeter_sessions').select('id,category_id,status,base_fare,price_per_km,price_per_minute,minimum_fare,multiplier,started_at,last_tick_at,ended_at,distance_m,elapsed_seconds,current_amount,final_amount,payment_method').eq('driver_id',user.id).eq('status','running').limit(1).maybeSingle(),
   supabase.from('driver_taximeter_sessions').select('id,category_id,status,base_fare,price_per_km,price_per_minute,minimum_fare,multiplier,started_at,last_tick_at,ended_at,distance_m,elapsed_seconds,current_amount,final_amount,payment_method').eq('driver_id',user.id).in('status',['finished','cancelled']).order('started_at',{ascending:false}).limit(5),
   supabase.rpc('get_my_taximeter_financial_summary',{})
  ])
  if(ce)setMsg(ce.message);else{const rows=(cats||[]) as Category[];setCategories(rows);if(rows[0])setSelected(v=>v||rows[0].category_id)}
  if(!re)setSession((running||null) as Session|null)
  setHistory((hist||[]) as Session[])
  if(!fe&&fin)setFinance(fin as Finance)
 }
 function position():Promise<Location>{return new Promise((resolve,reject)=>{if(!navigator.geolocation)return reject(new Error('GPS indisponível.'));navigator.geolocation.getCurrentPosition(p=>resolve({lat:p.coords.latitude,lng:p.coords.longitude}),reject,{enableHighAccuracy:true,timeout:12000,maximumAge:2500})})}
 async function start(){
  if(blockedByRide){setMsg('Finalize a corrida CLICK-GO ativa antes de usar o taxímetro livre.');return}
  if(!selected){setMsg('Nenhuma categoria autorizada para o taxímetro.');return}
  if(!window.confirm('Girar a maçaneta para OCUPADO e iniciar o taxímetro?'))return
  setBusy(true);setMsg('Ligando taxímetro e obtendo GPS...')
  try{const p=await position();const{data,error}=await supabase.rpc('start_driver_taximeter',{p_category_id:selected,p_lat:p.lat,p_lng:p.lng});if(error)throw error;setMsg('Maçaneta em OCUPADO. Taxímetro iniciado.');await load();if(data?.session_id)setNow(Date.now())}catch(e:any){setMsg(e?.message||'Não foi possível iniciar o taxímetro.')}finally{setBusy(false)}
 }
 async function tick(){
  if(!session||ticking.current)return;ticking.current=true
  try{const p=await position();const{data,error}=await supabase.rpc('tick_driver_taximeter',{p_session_id:session.id,p_lat:p.lat,p_lng:p.lng});if(!error&&data)setSession(v=>v?{...v,current_amount:data.amount,distance_m:data.distance_m,elapsed_seconds:data.elapsed_seconds,last_tick_at:new Date().toISOString()}:v)}catch{}finally{ticking.current=false}
 }
 async function finish(){
  if(!session)return;if(!window.confirm('Finalizar o taxímetro e voltar a maçaneta para LIVRE?'))return
  setBusy(true);setMsg('Finalizando taxímetro...')
  try{const p=await position();const{data,error}=await supabase.rpc('finish_driver_taximeter',{p_session_id:session.id,p_lat:p.lat,p_lng:p.lng,p_payment_method:payment});if(error)throw error;const f=data?.financial,fee=Number(f?.fee_amount||0);setMsg(fee>0?`Taxímetro finalizado: ${money(data?.final_amount)} · taxa ${money(fee)} ${f?.status==='pending'?'pendente na carteira':'quitada pela carteira'}.`:`Taxímetro finalizado: ${money(data?.final_amount)} · sem taxa operacional.`);setSession(null);await load()}catch(e:any){setMsg(e?.message||'Não foi possível finalizar o taxímetro.')}finally{setBusy(false)}
 }
 async function cancel(){
  if(!session||!window.confirm('Cancelar esta sessão do taxímetro? Ela ficará registrada como cancelada.'))return
  setBusy(true);const{error}=await supabase.rpc('cancel_driver_taximeter',{p_session_id:session.id});setBusy(false);if(error){setMsg(error.message);return}setSession(null);setMsg('Taxímetro cancelado e maçaneta em LIVRE.');await load()
 }
 async function settlePending(){
  if(!finance||Number(finance.pending_amount||0)<=0)return
  if(!window.confirm('Usar o saldo da carteira operacional para quitar as taxas pendentes do taxímetro?'))return
  setBusy(true);setMsg('Quitando taxas pendentes...')
  const{data,error}=await supabase.rpc('settle_driver_taximeter_pending_fees',{p_driver_id:null})
  setBusy(false)
  if(error){setMsg(error.message);return}
  setMsg(Number(data?.settled_count||0)>0?`${data.settled_count} taxa(s) quitada(s): ${money(data.settled_amount)}.`:'O saldo atual ainda não é suficiente para quitar a próxima pendência.')
  await load()
 }
 const category=categories.find(c=>c.category_id===(session?.category_id||selected))
 const liveElapsed=session?Math.max(Number(session.elapsed_seconds||0),Math.floor((now-new Date(session.started_at).getTime())/1000)):0
 const liveAmount=useMemo(()=>{if(!session)return 0;const raw=(Number(session.base_fare||0)+(Number(session.distance_m||0)/1000)*Number(session.price_per_km||0)+(liveElapsed/60)*Number(session.price_per_minute||0))*Number(session.multiplier||1);return Math.max(Number(session.minimum_fare||0),raw)},[session?.id,session?.distance_m,session?.base_fare,session?.price_per_km,session?.price_per_minute,session?.minimum_fare,session?.multiplier,liveElapsed])
 const shown=(v:any)=>showMoney?money(v):'R$ ••••'
 return <section style={{...panel,borderColor:session?'#ffd400':'#333'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}><div><div style={{fontSize:12,fontWeight:950,color:'#ffd400',letterSpacing:.8}}>TAXÍMETRO / MAÇANETA</div><h2 style={{margin:'4px 0 0'}}>Corrida livre</h2><div style={{fontSize:12,color:'#9ca3af',marginTop:4}}>Para passageiro pego na rua, fora de uma chamada CLICK-GO. Usa a tarifa oficial da categoria.</div></div><div style={{padding:'7px 12px',borderRadius:999,fontWeight:950,background:session?'#7c2d12':'#14532d',color:'#fff'}}>{session?'OCUPADO':'LIVRE'}</div></div>
  {!session?<div style={{display:'grid',gridTemplateColumns:'1fr auto',gap:12,marginTop:14,alignItems:'end'}}><label style={{display:'grid',gap:5,fontSize:12,color:'#9ca3af'}}>Categoria / tarifa<select value={selected} onChange={e=>setSelected(e.target.value)} style={input}>{categories.map(c=><option key={c.category_id} value={c.category_id}>{c.category_name} · base {money(c.base_fare)} · km {money(c.price_per_km)} · min {money(c.price_per_minute)}</option>)}</select></label><button disabled={busy||blockedByRide||!selected} onClick={start} style={{...button,minWidth:210,background:blockedByRide?'#333':'#ffd400',color:blockedByRide?'#aaa':'#000',fontSize:15}}>↻ Girar maçaneta · OCUPADO</button></div>:
  <div style={{marginTop:14,display:'grid',gap:12}}><div style={{background:'#050505',border:'2px solid #ffd400',borderRadius:18,padding:18,textAlign:'center'}}><div style={{fontSize:12,color:'#9ca3af',fontWeight:900}}>VALOR NO TAXÍMETRO</div><div style={{fontSize:46,fontWeight:950,color:'#ffd400',lineHeight:1.1,marginTop:5}}>{shown(liveAmount)}</div><div style={{display:'flex',justifyContent:'center',gap:18,flexWrap:'wrap',marginTop:12,color:'#d1d5db'}}><span>⏱ {clock(liveElapsed)}</span><span>🛣 {(Number(session.distance_m||0)/1000).toFixed(2)} km</span><span>🏳 x{Number(session.multiplier||1).toFixed(2)}</span></div></div><div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:8}}><div style={panel}><div style={{fontSize:11,color:'#9ca3af'}}>BANDEIRADA</div><b>{shown(session.base_fare)}</b></div><div style={panel}><div style={{fontSize:11,color:'#9ca3af'}}>POR KM</div><b>{shown(session.price_per_km)}</b></div><div style={panel}><div style={{fontSize:11,color:'#9ca3af'}}>POR MINUTO</div><b>{shown(session.price_per_minute)}</b></div><div style={panel}><div style={{fontSize:11,color:'#9ca3af'}}>MÍNIMA</div><b>{shown(session.minimum_fare)}</b></div></div><div style={{display:'flex',gap:9,flexWrap:'wrap',alignItems:'center'}}><select value={payment} onChange={e=>setPayment(e.target.value)} style={input}><option value="cash">Dinheiro</option><option value="pix_external">PIX direto</option><option value="card_machine">Cartão / maquininha</option></select><button disabled={busy} onClick={finish} style={{...button,background:'#ffd400',color:'#000',flex:1}}>↻ Finalizar · maçaneta LIVRE</button><button disabled={busy} onClick={cancel} style={{...button,background:'#3f1515',color:'#fff'}}>Cancelar</button></div></div>}
  {category&&!session&&<div style={{fontSize:12,color:'#9ca3af',marginTop:9}}>Tarifa selecionada: {category.category_name} · mínima {money(category.minimum_fare)} · multiplicador x{Number(category.multiplier||1).toFixed(2)}.</div>}
  {blockedByRide&&!session&&<div style={{marginTop:9,fontSize:12,color:'#fbbf24'}}>O taxímetro livre fica bloqueado enquanto existir uma corrida CLICK-GO ativa.</div>}
  {finance&&<div style={{...panel,marginTop:13,borderColor:Number(finance.pending_amount||0)>0?'#7c5c00':'#2b4c36'}}><div style={{display:'flex',justifyContent:'space-between',gap:10,alignItems:'center',flexWrap:'wrap'}}><div><div style={{fontSize:11,color:'#9ca3af',fontWeight:900}}>FINANCEIRO DO TAXÍMETRO · 30 DIAS</div><div style={{fontWeight:950,marginTop:3}}>Regra atual: {feeRule(finance.effective_rule)}</div></div><div style={{fontSize:12,color:'#9ca3af'}}>Carteira: <b style={{color:'#fff'}}>{shown(finance.wallet_balance)}</b></div></div><div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:8,marginTop:10}}><div><small style={{color:'#9ca3af'}}>BRUTO</small><div style={{fontWeight:900}}>{shown(finance.gross_amount)}</div></div><div><small style={{color:'#9ca3af'}}>TAXAS</small><div style={{fontWeight:900}}>{shown(finance.fee_amount)}</div></div><div><small style={{color:'#9ca3af'}}>LÍQUIDO</small><div style={{fontWeight:900,color:'#4ade80'}}>{shown(finance.driver_net_amount)}</div></div><div><small style={{color:'#9ca3af'}}>PENDENTE</small><div style={{fontWeight:900,color:Number(finance.pending_amount||0)>0?'#fbbf24':'#4ade80'}}>{shown(finance.pending_amount)}</div></div></div>{Number(finance.pending_amount||0)>0&&<button disabled={busy} onClick={settlePending} style={{...button,background:'#ffd400',color:'#000',marginTop:11,width:'100%'}}>Quitar pendências com saldo da carteira</button>}</div>}
  {msg&&<div style={{marginTop:10,fontSize:12,color:'#ffe66b'}}>{msg}</div>}
  {history.length>0&&<details style={{marginTop:13}}><summary style={{cursor:'pointer',fontWeight:800}}>Últimos taxímetros</summary><div style={{display:'grid',gap:7,marginTop:9}}>{history.map(h=><div key={h.id} style={{display:'flex',justifyContent:'space-between',gap:10,borderTop:'1px solid #292929',paddingTop:7,fontSize:12}}><span>{new Date(h.started_at).toLocaleString('pt-BR')} · {(Number(h.distance_m||0)/1000).toFixed(2)} km · {clock(Number(h.elapsed_seconds||0))}</span><b style={{color:h.status==='finished'?'#ffd400':'#9ca3af'}}>{h.status==='finished'?shown(h.final_amount):'cancelado'}</b></div>)}</div></details>}
 </section>
}
