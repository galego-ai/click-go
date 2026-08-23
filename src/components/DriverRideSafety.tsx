'use client'

import { FormEvent,useEffect,useRef,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Loc={lat:number;lng:number}
type Props={rideId:string;status:string;location:Loc|null;origin:Loc;destination:Loc}
type Contact={id:string;name:string;phone:string;relationship:string|null}
const btn:React.CSSProperties={border:0,borderRadius:10,padding:'11px 14px',fontWeight:900,cursor:'pointer'}
const input:React.CSSProperties={background:'#0b0b0b',color:'#fff',border:'1px solid #444',borderRadius:10,padding:'11px 12px'}
const pinInput:React.CSSProperties={...input,fontSize:18,fontWeight:900,letterSpacing:5,width:145,textAlign:'center'}

function pointSegmentDistanceMeters(p:Loc,a:Loc,b:Loc){
 const rad=p.lat*Math.PI/180,kx=111320*Math.cos(rad),ky=110540
 const ax=(a.lng-p.lng)*kx,ay=(a.lat-p.lat)*ky,bx=(b.lng-p.lng)*kx,by=(b.lat-p.lat)*ky
 const dx=bx-ax,dy=by-ay,len=dx*dx+dy*dy
 const t=len?Math.max(0,Math.min(1,-(ax*dx+ay*dy)/len)):0
 const x=ax+t*dx,y=ay+t*dy
 return Math.sqrt(x*x+y*y)
}

export default function DriverRideSafety({rideId,status,location,origin,destination}:Props){
 const[pin,setPin]=useState(''),[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[route,setRoute]=useState<[number,number][]>([]),[alerted,setAlerted]=useState(false),[contact,setContact]=useState<Contact|null>(null),[showContactForm,setShowContactForm]=useState(false)
 const farHits=useRef(0),lastReport=useRef(0),routeRide=useRef(''),thresholdRef=useRef(100)
 useEffect(()=>{void loadContact()},[])
 useEffect(()=>{
  if(status!=='in_progress'){setRoute([]);farHits.current=0;thresholdRef.current=100;return}
  if(routeRide.current===rideId&&route.length)return
  const c=new AbortController();routeRide.current=rideId
  ;(async()=>{try{const p=new URLSearchParams({origin_lat:String(origin.lat),origin_lng:String(origin.lng),destination_lat:String(destination.lat),destination_lng:String(destination.lng)});const r=await fetch(`/api/route?${p}`,{signal:c.signal});const b=await r.json();if(r.ok&&Array.isArray(b.coordinates))setRoute(b.coordinates)}catch{}})()
  return()=>c.abort()
 },[rideId,status,origin.lat,origin.lng,destination.lat,destination.lng])
 useEffect(()=>{
  if(status!=='in_progress'||!location||route.length<2)return
  let min=Infinity
  const step=Math.max(1,Math.floor(route.length/400))
  let previous:{lat:number;lng:number}|null=null
  for(let i=0;i<route.length;i+=step){const [lat,lng]=route[i],current={lat,lng};if(previous)min=Math.min(min,pointSegmentDistanceMeters(location,previous,current));previous=current}
  const [lastLat,lastLng]=route[route.length-1];if(previous&&(previous.lat!==lastLat||previous.lng!==lastLng))min=Math.min(min,pointSegmentDistanceMeters(location,previous,{lat:lastLat,lng:lastLng}))
  if(min>=thresholdRef.current)farHits.current+=1;else farHits.current=0
  const now=Date.now();if(farHits.current<3||now-lastReport.current<300000)return
  farHits.current=0
  void supabase.rpc('report_route_deviation',{p_ride_id:rideId,p_lat:location.lat,p_lng:location.lng,p_distance_m:Math.round(min)}).then(({data,error})=>{
   if(error)return
   if(data?.threshold_m!=null)thresholdRef.current=Math.max(100,Number(data.threshold_m))
   if(data?.reported){lastReport.current=Date.now();setAlerted(true);setMsg(`Possível desvio de rota registrado (${Math.round(min)} m da rota planejada).`)}
   else if(data?.duplicate)lastReport.current=Date.now()
  })
 },[location?.lat,location?.lng,status,route,rideId])
 async function loadContact(){
  const{data:{user}}=await supabase.auth.getUser();if(!user)return
  const{data}=await supabase.from('user_emergency_contacts').select('id,name,phone,relationship').eq('owner_id',user.id).eq('active',true).order('is_primary',{ascending:false}).order('created_at',{ascending:true}).limit(1).maybeSingle()
  setContact((data||null) as Contact|null)
 }
 async function saveContact(e:FormEvent<HTMLFormElement>){
  e.preventDefault();setBusy(true);setMsg('')
  const f=new FormData(e.currentTarget),name=String(f.get('name')||'').trim(),phone=String(f.get('phone')||'').trim(),relationship=String(f.get('relationship')||'').trim()
  const{data:{user}}=await supabase.auth.getUser();if(!user){setBusy(false);setMsg('Faça login novamente.');return}
  const{error}=await supabase.from('user_emergency_contacts').insert({owner_id:user.id,name,phone,relationship:relationship||null,is_primary:true,active:true})
  setBusy(false);if(error){setMsg(error.message);return}setShowContactForm(false);setMsg('Contato de emergência cadastrado.');await loadContact()
 }
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
  {status==='driver_arriving'&&<div style={{background:'#101010',border:'1px solid #665600',borderRadius:13,padding:13}}><b style={{color:'#ffd400'}}>🔐 Confirmar embarque com PIN</b><div style={{color:'#9ca3af',fontSize:12,margin:'5px 0 10px'}}>Peça ao passageiro o PIN de 4 dígitos exibido no app. A corrida só inicia após a confirmação.</div><div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><input value={pin} onChange={e=>setPin(e.target.value.replace(/\D/g,'').slice(0,4))} inputMode="numeric" autoComplete="one-time-code" placeholder="0000" aria-label="PIN de 4 dígitos" style={pinInput}/><button disabled={busy||pin.length!==4} onClick={verifyAndStart} style={{...btn,background:'#ffd400',color:'#000'}}>▶ Validar PIN e iniciar</button></div></div>}
  {['accepted','driver_arriving','in_progress'].includes(status)&&<div style={{background:'#101010',border:'1px solid #292929',borderRadius:13,padding:12,display:'grid',gap:9}}><div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><button disabled={busy} onClick={sos} style={{...btn,background:'#b91c1c',color:'#fff'}}>🆘 SOS</button>{status==='in_progress'&&<span style={{fontSize:12,color:alerted?'#fca5a5':'#9ca3af'}}>{alerted?'⚠ Desvio registrado':'🛡 Monitoramento de desvio de rota ativo'}</span>}</div>{contact?<div style={{display:'flex',justifyContent:'space-between',gap:9,alignItems:'center'}}><div><b>Contato de emergência: {contact.name}</b><div style={{color:'#9ca3af',fontSize:12,marginTop:3}}>{contact.relationship||'Pessoa de confiança'} · {contact.phone}</div></div><a href={`tel:${contact.phone.replace(/[^0-9+]/g,'')}`} style={{...btn,background:'#222',color:'#fff',textDecoration:'none',padding:'9px 11px'}}>Ligar</a></div>:<div><div style={{fontSize:12,color:'#9ca3af'}}>Nenhum contato de emergência cadastrado.</div><button onClick={()=>setShowContactForm(v=>!v)} style={{...btn,background:'#222',color:'#fff',padding:'8px 10px',marginTop:7}}>{showContactForm?'Fechar':'Cadastrar contato'}</button>{showContactForm&&<form onSubmit={saveContact} style={{display:'grid',gap:7,marginTop:8}}><input required name="name" minLength={2} placeholder="Nome" style={input}/><input required name="phone" placeholder="Telefone / WhatsApp" style={input}/><input name="relationship" placeholder="Relação: esposa, irmão, amigo..." style={input}/><button disabled={busy} style={{...btn,background:'#ffd400',color:'#000'}}>Salvar contato principal</button></form>}</div>}</div>}
  {msg&&<div style={{fontSize:12,color:'#ffe66b'}}>{msg}</div>}
 </div>
}
