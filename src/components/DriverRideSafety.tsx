'use client'

import { useEffect,useRef,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Loc={lat:number;lng:number}
type Props={rideId:string;status:string;location:Loc|null;origin:Loc;destination:Loc}
const btn:React.CSSProperties={border:0,borderRadius:10,padding:'11px 14px',fontWeight:900,cursor:'pointer'}
const input:React.CSSProperties={background:'#0b0b0b',color:'#fff',border:'1px solid #444',borderRadius:10,padding:'11px 12px',fontSize:18,fontWeight:900,letterSpacing:5,width:145,textAlign:'center'}

function haversineMeters(a:Loc,b:Loc){
 const R=6371000,toRad=(x:number)=>x*Math.PI/180
 const dLat=toRad(b.lat-a.lat),dLng=toRad(b.lng-a.lng),la1=toRad(a.lat),la2=toRad(b.lat)
 const h=Math.sin(dLat/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dLng/2)**2
 return 2*R*Math.asin(Math.min(1,Math.sqrt(h)))
}

export default function DriverRideSafety({rideId,status,location,origin,destination}:Props){
 const[pin,setPin]=useState(''),[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[route,setRoute]=useState<[number,number][]>([]),[alerted,setAlerted]=useState(false)
 const farHits=useRef(0),lastReport=useRef(0),routeRide=useRef('')
 useEffect(()=>{
  if(status!=='in_progress'){setRoute([]);farHits.current=0;return}
  if(routeRide.current===rideId&&route.length)return
  const c=new AbortController();routeRide.current=rideId
  ;(async()=>{try{const p=new URLSearchParams({origin_lat:String(origin.lat),origin_lng:String(origin.lng),destination_lat:String(destination.lat),destination_lng:String(destination.lng)});const r=await fetch(`/api/route?${p}`,{signal:c.signal});const b=await r.json();if(r.ok&&Array.isArray(b.coordinates))setRoute(b.coordinates)}catch{}})()
  return()=>c.abort()
 },[rideId,status,origin.lat,origin.lng,destination.lat,destination.lng])
 useEffect(()=>{
  if(status!=='in_progress'||!location||route.length<2)return
  let min=Infinity
  for(let i=0;i<route.length;i+=Math.max(1,Math.floor(route.length/250))){const [lat,lng]=route[i];min=Math.min(min,haversineMeters(location,{lat,lng}))}
  if(min>=300)farHits.current+=1;else farHits.current=0
  const now=Date.now();if(farHits.current<3||now-lastReport.current<300000)return
  lastReport.current=now;farHits.current=0
  void supabase.rpc('report_route_deviation',{p_ride_id:rideId,p_lat:location.lat,p_lng:location.lng,p_distance_m:Math.round(min)}).then(({data,error})=>{if(!error&&data?.reported){setAlerted(true);setMsg(`Possível desvio de rota registrado (${Math.round(min)} m da rota planejada).`)}})
 },[location?.lat,location?.lng,status,route,rideId])
 async function verifyAndStart(){
  if(!/^\d{4}$/.test(pin)){setMsg('Digite os 4 números informados pelo passageiro.');return}
  setBusy(true);setMsg('Validando PIN...')
  const{data,error}=await supabase.rpc('verify_ride_start_pin',{p_ride_id:rideId,p_pin:pin})
  if(error){setBusy(false);setMsg(error.message);return}
  if(!data?.verified){setBusy(false);setMsg(data?.locked?'Muitas tentativas incorretas. Validação bloqueada por alguns minutos.':`PIN incorreto. ${data?.remaining_attempts??''} tentativa(s) restante(s).`);return}
  setMsg('PIN confirmado. Iniciando corrida...')
  const{error:startError}=await supabase.rpc('advance_driver_ride',{p_ride_id:rideId,p_action:'start'})
  setBusy(false)
  if(startError){setMsg(startError.message);return}
  setPin('');setMsg('PIN confirmado e corrida iniciada com segurança.')
 }
 async function sos(){
  if(!window.confirm('Acionar o SOS desta corrida? O alerta ficará registrado no sistema.'))return
  setBusy(true)
  const{data,error}=await supabase.rpc('trigger_ride_sos',{p_ride_id:rideId,p_lat:location?.lat??null,p_lng:location?.lng??null,p_message:'SOS acionado pelo motorista no app CLICK-GO.'})
  setBusy(false);setMsg(error?error.message:data?.ok?'SOS registrado com a localização disponível.':'Não foi possível confirmar o SOS.')
 }
 return <div style={{marginTop:13,display:'grid',gap:9}}>
  {status==='driver_arriving'&&<div style={{background:'#101010',border:'1px solid #665600',borderRadius:13,padding:13}}><b style={{color:'#ffd400'}}>🔐 Confirmar embarque com PIN</b><div style={{color:'#9ca3af',fontSize:12,margin:'5px 0 10px'}}>Peça ao passageiro o PIN de 4 dígitos exibido no app. A corrida só inicia após a confirmação.</div><div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><input value={pin} onChange={e=>setPin(e.target.value.replace(/\D/g,'').slice(0,4))} inputMode="numeric" autoComplete="one-time-code" placeholder="0000" aria-label="PIN de 4 dígitos" style={input}/><button disabled={busy||pin.length!==4} onClick={verifyAndStart} style={{...btn,background:'#ffd400',color:'#000'}}>▶ Validar PIN e iniciar</button></div></div>}
  {['accepted','driver_arriving','in_progress'].includes(status)&&<div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><button disabled={busy} onClick={sos} style={{...btn,background:'#b91c1c',color:'#fff'}}>🆘 SOS</button>{status==='in_progress'&&<span style={{fontSize:12,color:alerted?'#fca5a5':'#9ca3af'}}>{alerted?'⚠ Desvio registrado':'🛡 Monitoramento de desvio de rota ativo'}</span>}</div>}
  {msg&&<div style={{fontSize:12,color:'#ffe66b'}}>{msg}</div>}
 </div>
}
