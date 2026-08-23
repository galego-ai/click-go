'use client'

import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Alert={
 id:string;ride_id:string;alert_type:'sos'|'route_deviation';severity:string;reporter_role:string;lat:number|null;lng:number|null;
 distance_from_route_m:number|null;message:string|null;status:'open'|'resolved';created_at:string;resolved_at:string|null;
 ride_status:string;origin_label:string;destination_label:string;passenger_name:string|null;driver_name:string|null
}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:16}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 13px',fontWeight:900,cursor:'pointer'}

export default function FranchiseSafetyPage(){
 const[items,setItems]=useState<Alert[]>([]),[filter,setFilter]=useState<'open'|'all'>('open'),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 useEffect(()=>{void load();const t=window.setInterval(load,10000);return()=>window.clearInterval(t)},[filter])
 async function load(){
  const{data,error}=await supabase.rpc('get_operation_safety_alerts',{p_status:filter,p_limit:200})
  if(error){setMsg(error.message);return}
  setItems(Array.isArray(data)?data as Alert[]:[])
 }
 async function resolve(id:string){
  if(!window.confirm('Marcar este alerta como atendido/resolvido?'))return
  setBusy(true);const{error}=await supabase.rpc('resolve_ride_safety_alert',{p_alert_id:id});setBusy(false)
  if(error){setMsg(error.message);return}setMsg('Alerta marcado como resolvido.');await load()
 }
 const openCount=items.filter(x=>x.status==='open').length
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1250,margin:'0 auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:14,alignItems:'center',flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:950}}>CLICK-GO · SEGURANÇA</div><h1 style={{margin:'5px 0'}}>Central de alertas da operação</h1><p style={{color:'#9ca3af',maxWidth:760}}>Acompanhe SOS acionados por passageiro/motorista e possíveis desvios de rota detectados durante as corridas da sua franquia.</p></div><div style={{...box,minWidth:170,textAlign:'center',borderColor:openCount?'#991b1b':'#166534'}}><div style={{fontSize:12,color:'#9ca3af'}}>ALERTAS ABERTOS</div><div style={{fontSize:34,fontWeight:950,color:openCount?'#f87171':'#4ade80'}}>{openCount}</div></div></div>
  <div style={{display:'flex',gap:8,margin:'18px 0'}}><button onClick={()=>setFilter('open')} style={{...btn,background:filter==='open'?'#ffd400':'#222',color:filter==='open'?'#000':'#fff'}}>Abertos</button><button onClick={()=>setFilter('all')} style={{...btn,background:filter==='all'?'#ffd400':'#222',color:filter==='all'?'#000':'#fff'}}>Todos</button><button onClick={()=>load()} style={{...btn,background:'#222',color:'#fff'}}>Atualizar</button></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:12}}>{msg}</div>}
  <div style={{display:'grid',gap:12}}>{items.map(a=>{
   const isSos=a.alert_type==='sos',coord=a.lat!=null&&a.lng!=null?`${Number(a.lat).toFixed(6)}, ${Number(a.lng).toFixed(6)}`:'Localização não disponível'
   const maps=a.lat!=null&&a.lng!=null?`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${a.lat},${a.lng}`)}`:''
   return <article key={a.id} style={{...box,border:`1px solid ${a.status==='open'?(isSos?'#991b1b':'#a16207'):'#2f4f3a'}`}}>
    <div style={{display:'grid',gridTemplateColumns:'1fr auto',gap:14,alignItems:'start'}}><div><div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><span style={{fontSize:22}}>{isSos?'🆘':'⚠️'}</span><b style={{fontSize:18}}>{isSos?'SOS da corrida':'Possível desvio de rota'}</b><span style={{fontSize:11,fontWeight:900,padding:'4px 7px',borderRadius:999,background:a.status==='open'?'#3f1515':'#16351f',color:a.status==='open'?'#fca5a5':'#86efac'}}>{a.status==='open'?'ABERTO':'RESOLVIDO'}</span></div><div style={{color:'#9ca3af',fontSize:12,marginTop:5}}>Corrida {a.ride_id.slice(0,8)} · {new Date(a.created_at).toLocaleString('pt-BR')} · origem do alerta: {a.reporter_role}</div></div>{a.status==='open'&&<button disabled={busy} onClick={()=>resolve(a.id)} style={{...btn,background:'#166534',color:'#fff'}}>✓ Marcar atendido</button>}</div>
    <div style={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:10,marginTop:13}}><div style={{background:'#0d0d0d',borderRadius:11,padding:11}}><b>Passageiro</b><div style={{color:'#d1d5db',marginTop:3}}>{a.passenger_name||'—'}</div></div><div style={{background:'#0d0d0d',borderRadius:11,padding:11}}><b>Motorista</b><div style={{color:'#d1d5db',marginTop:3}}>{a.driver_name||'—'}</div></div></div>
    <div style={{marginTop:11,lineHeight:1.5}}><div><b>Embarque:</b> {a.origin_label}</div><div><b>Destino:</b> {a.destination_label}</div><div><b>Local do alerta:</b> {coord}{a.distance_from_route_m!=null?` · ${Math.round(Number(a.distance_from_route_m))} m da rota planejada`:''}</div>{a.message&&<div><b>Registro:</b> {a.message}</div>}</div>
    <div style={{display:'flex',gap:8,marginTop:12,flexWrap:'wrap'}}>{maps&&<a href={maps} target="_blank" rel="noreferrer" style={{...btn,textDecoration:'none',background:'#222',color:'#fff'}}>📍 Abrir localização</a>}<span style={{padding:'10px 12px',border:'1px solid #333',borderRadius:10,color:'#9ca3af',fontSize:12}}>Status da corrida: {a.ride_status}</span>{a.resolved_at&&<span style={{padding:'10px 12px',border:'1px solid #333',borderRadius:10,color:'#9ca3af',fontSize:12}}>Resolvido em {new Date(a.resolved_at).toLocaleString('pt-BR')}</span>}</div>
   </article>
  })}{!items.length&&<div style={{...box,textAlign:'center',padding:34,color:'#9ca3af'}}>Nenhum alerta {filter==='open'?'aberto':''} encontrado.</div>}</div>
 </div></main>
}
