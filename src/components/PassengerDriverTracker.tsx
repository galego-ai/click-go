'use client'

import { useEffect,useRef,useState } from 'react'
import { supabase } from '@/lib/supabase'
import PassengerRideSafety from '@/components/PassengerRideSafety'
import 'leaflet/dist/leaflet.css'

type Loc={lat:number;lng:number;heading:number|null;speed_kmh:number|null;updated_at:string}
type RidePoint={origin_lat:number;origin_lng:number;destination_lat:number;destination_lng:number;status:string;category_id:string|null}
type Cat={name:string;map_marker_url:string|null;icon_url:string|null}
type DriverCard={driver_id:string;full_name:string|null;avatar_url:string|null;rating:number|string|null;vehicle_make:string|null;vehicle_model:string|null;vehicle_year:number|null;vehicle_plate:string|null;vehicle_color:string|null;vehicle_type:string|null}

export default function PassengerDriverTracker({rideId,driverId}:{rideId:string;driverId:string}){
 const[loc,setLoc]=useState<Loc|null>(null),[ride,setRide]=useState<RidePoint|null>(null),[cat,setCat]=useState<Cat|null>(null),[driver,setDriver]=useState<DriverCard|null>(null),[route,setRoute]=useState<[number,number][]>([]),[provider,setProvider]=useState(''),[msg,setMsg]=useState('Carregando localização do motorista...')
 const mapEl=useRef<HTMLDivElement|null>(null),mapRef=useRef<any>(null),layerRef=useRef<any>(null),routeSeq=useRef(0)
 useEffect(()=>{
  load()
  const ch=supabase.channel(`passenger-driver-${driverId}`).on('postgres_changes',{event:'*',schema:'public',table:'driver_locations',filter:`driver_id=eq.${driverId}`},(p:any)=>{if(p.new?.lat!=null){setLoc(p.new as Loc);setMsg('Localização atualizada em tempo real.')}}).subscribe()
  const rh=supabase.channel(`passenger-tracker-ride-${rideId}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'rides',filter:`id=eq.${rideId}`},(p:any)=>{if(p.new)setRide(p.new as RidePoint)}).subscribe()
  return()=>{supabase.removeChannel(ch);supabase.removeChannel(rh)}
 },[rideId,driverId])
 async function load(){
  const[{data:l,error:le},{data:r,error:re},{data:dc,error:dce}]=await Promise.all([
   supabase.from('driver_locations').select('lat,lng,heading,speed_kmh,updated_at').eq('driver_id',driverId).maybeSingle(),
   supabase.from('rides').select('origin_lat,origin_lng,destination_lat,destination_lng,status,category_id').eq('id',rideId).single(),
   supabase.rpc('get_passenger_current_driver_card',{p_ride_id:rideId})
  ])
  if(l)setLoc(l as Loc)
  if(r){setRide(r as RidePoint);if(r.category_id){const{data:c}=await supabase.from('ride_categories').select('name,map_marker_url,icon_url').eq('id',r.category_id).maybeSingle();if(c)setCat(c as Cat)}}
  if(!dce&&dc?.[0])setDriver(dc[0] as DriverCard)
  if(le)setMsg('A localização do motorista aparecerá assim que o GPS dele atualizar.');else if(re)setMsg(re.message);else setMsg(l?'Motorista localizado.':'Aguardando GPS do motorista...')
 }
 useEffect(()=>{
  if(!loc||!ride){setRoute([]);return}
  const seq=++routeSeq.current;const target=ride.status==='in_progress'?{lat:ride.destination_lat,lng:ride.destination_lng}:{lat:ride.origin_lat,lng:ride.origin_lng};const c=new AbortController()
  ;(async()=>{try{const p=new URLSearchParams({origin_lat:String(loc.lat),origin_lng:String(loc.lng),destination_lat:String(target.lat),destination_lng:String(target.lng)});const r=await fetch(`/api/route?${p}`,{signal:c.signal});const b=await r.json();if(seq===routeSeq.current&&r.ok&&Array.isArray(b.coordinates)){setRoute(b.coordinates);setProvider(b.provider||'')}}catch{}})()
  return()=>c.abort()
 },[loc?.lat,loc?.lng,ride?.status,ride?.origin_lat,ride?.origin_lng,ride?.destination_lat,ride?.destination_lng])
 useEffect(()=>{
  let alive=true
  ;(async()=>{if(!mapEl.current)return;const L=await import('leaflet');if(!alive)return
   if(!mapRef.current){mapRef.current=L.map(mapEl.current,{zoomControl:false}).setView([-14.52472,-49.14083],14);const token=process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;if(token)L.tileLayer(`https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{z}/{x}/{y}@2x?access_token=${token}`,{attribution:'© Mapbox © OpenStreetMap',maxZoom:19}).addTo(mapRef.current);else L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).addTo(mapRef.current);layerRef.current=L.layerGroup().addTo(mapRef.current)}
   layerRef.current.clearLayers();const pts:[number,number][]=[]
   if(loc){const markerUrl=cat?.map_marker_url||cat?.icon_url;let marker:any;if(markerUrl)marker=L.marker([loc.lat,loc.lng],{icon:L.icon({iconUrl:markerUrl,iconSize:[44,44],iconAnchor:[22,22]})});else marker=L.marker([loc.lat,loc.lng],{icon:L.divIcon({html:'<div style="width:42px;height:42px;border-radius:50%;background:#111;border:3px solid #ffd400;display:grid;place-items:center;font-size:22px">🚗</div>',className:'',iconSize:[42,42],iconAnchor:[21,21]})});marker.bindTooltip(driver?.full_name?`Motorista: ${driver.full_name}`:cat?.name?`Motorista · ${cat.name}`:'Motorista').addTo(layerRef.current);pts.push([loc.lat,loc.lng])}
   if(ride){L.circleMarker([ride.origin_lat,ride.origin_lng],{radius:7,color:'#111',fillColor:'#19c7a3',fillOpacity:1}).bindTooltip('Embarque').addTo(layerRef.current);L.circleMarker([ride.destination_lat,ride.destination_lng],{radius:7,color:'#111',fillColor:'#ff8a3d',fillOpacity:1}).bindTooltip('Destino').addTo(layerRef.current);const target=ride.status==='in_progress'?[ride.destination_lat,ride.destination_lng] as [number,number]:[ride.origin_lat,ride.origin_lng] as [number,number];pts.push(target)}
   if(route.length>1)L.polyline(route,{weight:7,opacity:.9}).addTo(layerRef.current);if(pts.length>1)mapRef.current.fitBounds(pts,{padding:[35,35]});else if(pts.length===1)mapRef.current.setView(pts[0],15)
  })();return()=>{alive=false}
 },[loc,ride,route,cat,driver?.full_name])
 useEffect(()=>()=>{if(mapRef.current){mapRef.current.remove();mapRef.current=null}},[])
 const vehicle=[driver?.vehicle_make,driver?.vehicle_model,driver?.vehicle_year].filter(Boolean).join(' ')
 return <div style={{display:'grid',gap:12}}>
  <div style={{marginTop:4,background:'#0d0d0d',color:'#fff',border:'1px solid #292929',borderRadius:16,padding:10}}>
   {driver&&<div style={{display:'grid',gridTemplateColumns:'64px 1fr auto',gap:12,alignItems:'center',padding:'5px 4px 12px'}}>
    {driver.avatar_url?<img src={driver.avatar_url} alt="Foto do motorista" style={{width:60,height:60,borderRadius:'50%',objectFit:'cover',border:'2px solid #ffd400'}}/>:<div style={{width:60,height:60,borderRadius:'50%',background:'#222',display:'grid',placeItems:'center',fontSize:26,border:'2px solid #ffd400'}}>👤</div>}
    <div><div style={{fontWeight:900,fontSize:18}}>{driver.full_name||'Motorista CLICK-GO'}</div><div style={{fontSize:13,color:'#d1d5db',marginTop:3}}>{vehicle||driver.vehicle_type||'Veículo'}{driver.vehicle_color?` · ${driver.vehicle_color}`:''}</div><div style={{fontSize:13,color:'#ffd400',marginTop:3,fontWeight:800}}>{driver.vehicle_plate||'Placa em atualização'}</div></div>
    <div style={{textAlign:'right'}}><div style={{fontSize:18,fontWeight:900}}>★ {Number(driver.rating||0).toFixed(1)}</div><div style={{fontSize:11,color:'#9ca3af'}}>avaliação</div></div>
   </div>}
   <div style={{display:'flex',justifyContent:'space-between',gap:10,alignItems:'center'}}><b>Rastreamento em tempo real</b><span style={{fontSize:11,color:'#9ca3af'}}>rota: {provider==='mapbox'?'Mapbox':provider==='google'?'Google':'continuidade'}</span></div>
   <div ref={mapEl} style={{height:320,borderRadius:12,overflow:'hidden',marginTop:9}}/>
   <div style={{color:'#9ca3af',fontSize:12,marginTop:8}}>{msg}{loc?` · ${Number(loc.speed_kmh||0).toFixed(0)} km/h · atualização ${new Date(loc.updated_at).toLocaleTimeString('pt-BR')}`:''}</div>
  </div>
  <PassengerRideSafety rideId={rideId} status={ride?.status||''}/>
 </div>
}
