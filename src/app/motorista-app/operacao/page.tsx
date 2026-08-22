'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'
import 'leaflet/dist/leaflet.css'

type Driver={id:string;status:string;online:boolean;rating:number|string;city_id:string|null;franchise_id:string|null}
type Profile={id:string;full_name:string|null;email:string|null;role:string}
type Offer={offer_id:string;ride_id:string;expires_at:string;distance_to_pickup_km:number|string;eta_to_pickup_min:number;estimated_driver_earning:number|string;estimated_fare:number|string;origin_label:string;origin_lat:number;origin_lng:number;destination_label:string;destination_lat:number;destination_lng:number;category_name:string|null}
type Ride={id:string;status:string;origin_label:string;origin_lat:number;origin_lng:number;destination_label:string;destination_lat:number;destination_lng:number;estimated_fare:number|string|null;final_fare:number|string|null;payment_method_preference:string|null;accepted_at:string|null;started_at:string|null}
type Location={lat:number;lng:number;heading:number|null;speed:number|null}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})

export default function DriverOperationPage(){
 const[profile,setProfile]=useState<Profile|null>(null),[driver,setDriver]=useState<Driver|null>(null),[offers,setOffers]=useState<Offer[]>([]),[ride,setRide]=useState<Ride|null>(null),[location,setLocation]=useState<Location|null>(null),[balance,setBalance]=useState(0),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 const watchRef=useRef<number|null>(null),lastSentRef=useRef(0),mapEl=useRef<HTMLDivElement|null>(null),mapRef=useRef<any>(null),layerRef=useRef<any>(null)

 useEffect(()=>{load();return()=>{if(watchRef.current!==null&&navigator.geolocation)navigator.geolocation.clearWatch(watchRef.current)}},[])
 useEffect(()=>{
  if(!profile)return
  const offerChannel=supabase.channel(`driver-offers-${profile.id}`).on('postgres_changes',{event:'*',schema:'public',table:'ride_offers',filter:`driver_id=eq.${profile.id}`},()=>loadOffers()).subscribe()
  const rideChannel=supabase.channel(`driver-rides-${profile.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'rides',filter:`driver_id=eq.${profile.id}`},()=>loadCurrentRide()).subscribe()
  return()=>{supabase.removeChannel(offerChannel);supabase.removeChannel(rideChannel)}
 },[profile?.id])

 useEffect(()=>{
  let alive=true
  ;(async()=>{
    if(!mapEl.current)return
    const L=await import('leaflet');if(!alive)return
    if(!mapRef.current){mapRef.current=L.map(mapEl.current).setView([-14.52472,-49.14083],13);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors',maxZoom:19}).addTo(mapRef.current);layerRef.current=L.layerGroup().addTo(mapRef.current)}
    layerRef.current.clearLayers()
    const points:[number,number][]=[]
    if(location){L.circleMarker([location.lat,location.lng],{radius:8}).bindTooltip('Você').addTo(layerRef.current);points.push([location.lat,location.lng])}
    const target=ride||offers[0]
    if(target){L.circleMarker([target.origin_lat,target.origin_lng],{radius:8}).bindTooltip('Passageiro / origem').addTo(layerRef.current);L.circleMarker([target.destination_lat,target.destination_lng],{radius:8}).bindTooltip('Destino').addTo(layerRef.current);L.polyline([[target.origin_lat,target.origin_lng],[target.destination_lat,target.destination_lng]]).addTo(layerRef.current);points.push([target.origin_lat,target.origin_lng],[target.destination_lat,target.destination_lng])}
    if(points.length>1)mapRef.current.fitBounds(points,{padding:[35,35]});else if(points.length===1)mapRef.current.setView(points[0],15)
  })();return()=>{alive=false}
 },[location,ride,offers])
 useEffect(()=>()=>{if(mapRef.current){mapRef.current.remove();mapRef.current=null}},[])

 async function load(){setBusy(true);setMsg('');try{
  const{data:{user}}=await supabase.auth.getUser();if(!user){setBusy(false);return}
  const{data:p,error:pe}=await supabase.from('profiles').select('id,full_name,email,role').eq('id',user.id).single();if(pe)throw pe;if(!p||p.role!=='driver')throw new Error('Esta área é exclusiva do motorista.')
  const{data:d,error:de}=await supabase.from('drivers').select('id,status,online,rating,city_id,franchise_id').eq('id',user.id).single();if(de)throw de
  setProfile(p as Profile);setDriver(d as Driver)
  await Promise.all([loadOffers(),loadCurrentRide(),loadWallet(user.id)])
  if(d.online)startLocationWatch(false)
 }catch(e:any){setMsg(e.message||'Erro ao carregar operação.')}finally{setBusy(false)}}

 async function loadOffers(){const{data,error}=await supabase.rpc('get_driver_pending_offers');if(!error)setOffers((data||[]) as Offer[])}
 async function loadCurrentRide(){const{data:{user}}=await supabase.auth.getUser();if(!user)return;const{data,error}=await supabase.from('rides').select('id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,payment_method_preference,accepted_at,started_at').eq('driver_id',user.id).in('status',['accepted','driver_arriving','in_progress']).order('accepted_at',{ascending:false}).limit(1).maybeSingle();if(!error)setRide((data||null) as Ride|null)}
 async function loadWallet(uid:string){const{data}=await supabase.from('wallets').select('balance').eq('owner_id',uid).maybeSingle();setBalance(Number(data?.balance||0))}

 function getPosition():Promise<GeolocationPosition>{return new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000,maximumAge:5000}))}
 async function toggleOnline(){
  if(!driver)return;if(driver.status!=='approved'){setMsg('O franqueado precisa aprovar seu cadastro antes de você ficar online.');return}
  if(driver.online){setBusy(true);const{error}=await supabase.rpc('set_driver_online',{p_online:false,p_lat:null,p_lng:null});setBusy(false);if(error){setMsg(error.message);return}if(watchRef.current!==null){navigator.geolocation.clearWatch(watchRef.current);watchRef.current=null}setDriver({...driver,online:false});setOffers([]);setMsg('Você está offline e não receberá novas corridas.');return}
  if(!navigator.geolocation){setMsg('Seu aparelho não disponibiliza GPS.');return}
  setBusy(true);setMsg('Obtendo sua localização...')
  try{const pos=await getPosition();const loc={lat:pos.coords.latitude,lng:pos.coords.longitude,heading:pos.coords.heading,speed:pos.coords.speed};const{error}=await supabase.rpc('set_driver_online',{p_online:true,p_lat:loc.lat,p_lng:loc.lng});if(error)throw error;setLocation(loc);setDriver({...driver,online:true});startLocationWatch(true);setMsg('Você está online e já pode receber chamadas próximas.');await loadOffers()}catch(e:any){setMsg(e.code===1?'Permita o acesso à localização para ficar online.':e.message||'Não foi possível ativar o modo online.')}finally{setBusy(false)}
 }

 function startLocationWatch(force:boolean){
  if(!navigator.geolocation||watchRef.current!==null)return
  watchRef.current=navigator.geolocation.watchPosition(async pos=>{
    const loc={lat:pos.coords.latitude,lng:pos.coords.longitude,heading:pos.coords.heading,speed:pos.coords.speed};setLocation(loc)
    const now=Date.now();if(!force&&now-lastSentRef.current<5000)return;lastSentRef.current=now
    await supabase.rpc('update_driver_location',{p_lat:loc.lat,p_lng:loc.lng,p_heading:loc.heading,p_speed_kmh:loc.speed==null?null:loc.speed*3.6})
  },err=>setMsg(err.code===1?'A localização foi bloqueada. Ative o GPS para continuar recebendo corridas.':'Falha ao atualizar sua localização.'),{enableHighAccuracy:true,maximumAge:3000,timeout:15000})
 }

 async function respond(offer:Offer,accept:boolean){setBusy(true);const{data,error}=await supabase.rpc('respond_to_ride_offer',{p_offer_id:offer.offer_id,p_accept:accept});setBusy(false);if(error){setMsg(error.message);await loadOffers();return}if(accept&&data?.accepted){setMsg('Corrida aceita. Siga até o passageiro.');setOffers([]);await loadCurrentRide()}else{setMsg(accept?'Esta chamada já foi aceita por outro motorista.':'Chamada recusada.');await loadOffers()}}
 async function advance(action:'arrived'|'start'|'complete'){if(!ride)return;setBusy(true);const{data,error}=await supabase.rpc('advance_driver_ride',{p_ride_id:ride.id,p_action:action});setBusy(false);if(error){setMsg(error.message);return}setMsg(action==='arrived'?'Status atualizado: a caminho do passageiro.':action==='start'?'Corrida iniciada.':'Corrida concluída e ganho enviado para sua carteira.');await loadCurrentRide();if(action==='complete'&&profile)await loadWallet(profile.id);if(data?.status==='completed')setRide(null)}

 if(!profile)return <main style={{minHeight:'calc(100vh - 60px)',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:620,margin:'10vh auto',...box}}><div className="eyebrow">Operação do motorista</div><h1>Entre no App Motorista</h1><p className="subtitle">Faça login primeiro para ativar o GPS, ficar online e receber corridas.</p><Link href="/motorista-app" style={{...btn,display:'inline-block',textDecoration:'none',marginTop:12}}>Ir para o login</Link>{msg&&<p style={{color:'#ffe66b'}}>{msg}</p>}</div></main>

 const offer=offers[0]
 const navTarget=ride||offer
 const mapsUrl=navTarget?`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${navTarget.origin_lat},${navTarget.origin_lng}`)}`:''
 return <main style={{minHeight:'calc(100vh - 60px)',background:'#080808',color:'#fff',padding:20}}><div style={{maxWidth:1200,margin:'0 auto',display:'grid',gap:14}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:14,alignItems:'center',flexWrap:'wrap'}}><div><div className="eyebrow">Operação em tempo real</div><h1 style={{margin:'5px 0'}}>Olá, {profile.full_name?.split(' ')[0]||'motorista'}</h1><p className="subtitle">Avaliação {Number(driver?.rating||0).toFixed(1)} · Carteira {money(balance)}</p></div><button onClick={toggleOnline} disabled={busy} style={{...btn,background:driver?.online?'#15803d':'#ffd400',color:driver?.online?'#fff':'#000',fontSize:16}}>{busy?'Aguarde...':driver?.online?'● ONLINE — ficar offline':'○ OFFLINE — ficar online'}</button></div>
  {driver?.status!=='approved'&&<div style={{...box,borderColor:'#7c2d12',color:'#fed7aa'}}>Seu cadastro está <b>{driver?.status}</b>. A operação só será liberada depois da aprovação do franqueado.</div>}
  <div style={{...box,padding:10}}><div ref={mapEl} style={{height:380,borderRadius:14,overflow:'hidden'}}/></div>
  {driver?.online&&location&&<div style={box}><b>GPS ativo</b><div style={{color:'#9ca3af',marginTop:6}}>{location.lat.toFixed(5)}, {location.lng.toFixed(5)} · localização enviada ao CLICK-GO em tempo real.</div></div>}
  {!ride&&offer&&<div style={{...box,border:'2px solid #ffd400'}}><div className="eyebrow">Nova corrida</div><div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'start',marginTop:8,flexWrap:'wrap'}}><div><h2 style={{margin:'0 0 8px'}}>{offer.category_name||'Corrida CLICK-GO'}</h2><div><b>Embarque:</b> {offer.origin_label}</div><div style={{marginTop:5}}><b>Destino:</b> {offer.destination_label}</div><div style={{color:'#9ca3af',marginTop:8}}>{Number(offer.distance_to_pickup_km).toFixed(1)} km até o passageiro · aproximadamente {offer.eta_to_pickup_min} min</div></div><div style={{textAlign:'right'}}><div style={{fontSize:12,color:'#9ca3af'}}>Ganho estimado</div><div style={{fontSize:28,fontWeight:900,color:'#ffd400'}}>{money(offer.estimated_driver_earning)}</div></div></div><div style={{display:'flex',gap:9,marginTop:14}}><button style={{...btn,flex:1}} disabled={busy} onClick={()=>respond(offer,true)}>Aceitar corrida</button><button style={{...btn,background:'#3a1b1b',color:'#fff',flex:1}} disabled={busy} onClick={()=>respond(offer,false)}>Recusar</button></div></div>}
  {!ride&&driver?.online&&!offer&&<div style={box}><h3 style={{marginTop:0}}>Aguardando chamadas...</h3><p className="subtitle">Mantenha o GPS ligado. O sistema procura motoristas em ondas de 1, 2, 3, 5 e 8 km.</p></div>}
  {ride&&<div style={{...box,borderColor:'#166534'}}><div className="eyebrow">Corrida atual</div><h2 style={{margin:'6px 0'}}>{ride.status==='accepted'?'Corrida aceita':ride.status==='driver_arriving'?'A caminho do passageiro':'Corrida em andamento'}</h2><div><b>Origem:</b> {ride.origin_label}</div><div style={{marginTop:5}}><b>Destino:</b> {ride.destination_label}</div><div style={{marginTop:8,color:'#9ca3af'}}>Pagamento: {ride.payment_method_preference||'não informado'} · valor estimado {money(ride.estimated_fare)}</div><div style={{display:'flex',gap:9,marginTop:14,flexWrap:'wrap'}}>{mapsUrl&&<a href={mapsUrl} target="_blank" rel="noreferrer" style={{...btn,textDecoration:'none',background:'#222',color:'#fff'}}>Abrir navegação</a>}{ride.status==='accepted'&&<button style={btn} disabled={busy} onClick={()=>advance('arrived')}>Iniciar deslocamento</button>}{ride.status==='driver_arriving'&&<button style={btn} disabled={busy} onClick={()=>advance('start')}>Passageiro embarcou — iniciar corrida</button>}{ride.status==='in_progress'&&<button style={btn} disabled={busy} onClick={()=>advance('complete')}>Concluir corrida</button>}</div></div>}
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b'}}>{msg}</div>}
 </div></main>
}
