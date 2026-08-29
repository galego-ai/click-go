'use client'

import {useEffect,useRef,useState} from 'react'
import type {CircleMarker,Map as LeafletMap} from 'leaflet'
import {supabase} from '@/lib/supabase'
import {cityDriverLocationsTopic,parseDriverLocationBroadcast,type DriverLocationBroadcast} from '@/lib/realtime-gps'
import 'leaflet/dist/leaflet.css'

type MapLoc={
 driver_id:string
 full_name?:string|null
 online?:boolean
 dispatch_online?:boolean
 status?:string
 activity_state?:string
 active_ride_id?:string|null
 taximeter_session_id?:string|null
 taximeter_amount?:number|null
 online_since?:string|null
 city_id?:string|null
 city_name?:string|null
 city_state?:string|null
 lat:number|null
 lng:number|null
 heading:number|null
 speed_kmh:number|null
 updated_at:string|null
}
type City={id:string;name:string;state:string;center_lat:number|null;center_lng:number|null}
type ProfileScope={role:string;franchise_id:string|null}
type CityAccess={city_id:string}
type FranchiseCity={city_id:string;cities:City[]}
type DriverIdRow={id:string;city_id:string|null}
type Person={id:string;full_name:string|null}
type SupportSession={franchise_id:string;franchise_name:string}|null

function activityLabel(row:MapLoc){
 const state=String(row.activity_state||row.status||'online')
 if(state==='taximeter')return 'Taxímetro ocupado'
 if(state==='in_progress')return 'Em corrida'
 if(state==='driver_arriving')return 'A caminho do passageiro'
 if(state==='accepted')return 'Corrida aceita'
 return 'Online'
}

function safeNumber(value:unknown):number|null{
 const n=Number(value)
 return Number.isFinite(n)?n:null
}

export default function RealtimeMapData({compact=false}:{compact?:boolean}){
 const[rows,setRows]=useState<MapLoc[]>([])
 const[cities,setCities]=useState<City[]>([])
 const[selectedCity,setSelectedCity]=useState('')
 const[msg,setMsg]=useState('Conectando ao mapa...')
 const[mapReady,setMapReady]=useState(false)
 const[supportName,setSupportName]=useState('')
 const[scopeRole,setScopeRole]=useState('')
 const mapEl=useRef<HTMLDivElement|null>(null)
 const mapRef=useRef<LeafletMap|null>(null)
 const leafletRef=useRef<typeof import('leaflet')|null>(null)
 const markersRef=useRef<Map<string,CircleMarker>>(new Map())
 const locationsRef=useRef<Map<string,MapLoc>>(new Map())

 const syncRows=()=>setRows(Array.from(locationsRef.current.values()).sort((a,b)=>Date.parse(b.updated_at||b.online_since||'1970-01-01')-Date.parse(a.updated_at||a.online_since||'1970-01-01')))

 function removeLocation(driverId:string){
  const marker=markersRef.current.get(driverId)
  if(marker)marker.remove()
  markersRef.current.delete(driverId)
  locationsRef.current.delete(driverId)
 }

 function clearLocations(){
  markersRef.current.forEach(marker=>marker.remove())
  markersRef.current.clear()
  locationsRef.current.clear()
  setRows([])
 }

 function renderLocation(location:MapLoc){
  const L=leafletRef.current,map=mapRef.current
  const lat=Number(location.lat),lng=Number(location.lng)
  if(!L||!map||!Number.isFinite(lat)||!Number.isFinite(lng))return
  const current=markersRef.current.get(location.driver_id)
  const name=location.full_name?.trim()||'Motorista'
  const updated=location.updated_at?new Date(location.updated_at).toLocaleString('pt-BR'):'Aguardando GPS'
  const activity=activityLabel(location)
  const taximeter=location.activity_state==='taximeter'&&Number.isFinite(Number(location.taximeter_amount))?`<br/>Taxímetro: ${Number(location.taximeter_amount).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}`:''
  const popup=`<strong>${name}</strong><br/>Status: ${activity}<br/>Velocidade: ${Math.round(location.speed_kmh??0)} km/h${taximeter}<br/>Atualizado: ${updated}`
  if(current){current.setLatLng([lat,lng]).setPopupContent(popup);return}
  const marker=L.circleMarker([lat,lng],{radius:8,weight:2,color:'#111827',fillColor:location.activity_state==='taximeter'?'#ffd400':'#22c55e',fillOpacity:.9})
  marker.bindPopup(popup).addTo(map)
  markersRef.current.set(location.driver_id,marker)
 }

 function applyLocation(location:MapLoc){
  if(location.online===false){removeLocation(location.driver_id);syncRows();return}
  const previous=locationsRef.current.get(location.driver_id)
  const merged={...previous,...location,full_name:location.full_name||previous?.full_name||'Motorista'} as MapLoc
  locationsRef.current.set(location.driver_id,merged)
  renderLocation(merged)
  syncRows()
 }

 function applySnapshot(list:MapLoc[]){
  const keep=new Set(list.map(item=>item.driver_id))
  for(const driverId of Array.from(locationsRef.current.keys()))if(!keep.has(driverId))removeLocation(driverId)
  for(const item of list)applyLocation(item)
  syncRows()
 }

 async function loadScope(){
  const{data:{user}}=await supabase.auth.getUser()
  if(!user){setMsg('Faça login para acompanhar a operação.');return}
  const{data:profile,error}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single()
  if(error){setMsg(error.message);return}
  const scope=profile as ProfileScope
  setScopeRole(scope.role)
  let allowed:City[]=[]
  if(scope.role==='super_admin'){
   const supportRes=await supabase.rpc('matrix_active_support_session')
   const support=(supportRes.data||null) as SupportSession
   setSupportName(String(support?.franchise_name||''))
   if(support?.franchise_id){
    const r=await supabase.from('franchise_cities').select('city_id,cities(id,name,state,center_lat,center_lng)').eq('franchise_id',support.franchise_id)
    if(r.error){setMsg(r.error.message);return}
    allowed=((r.data||[]) as unknown as FranchiseCity[]).map(x=>x.cities?.[0]).filter((x):x is City=>Boolean(x)).sort((a,b)=>a.name.localeCompare(b.name))
   }else{
    const r=await supabase.from('cities').select('id,name,state,center_lat,center_lng').eq('active',true).order('name')
    if(r.error){setMsg(r.error.message);return}
    allowed=(r.data||[]) as City[]
   }
  }else if(scope.franchise_id){
   setSupportName('')
   const r=await supabase.from('franchise_cities').select('city_id,cities(id,name,state,center_lat,center_lng)').eq('franchise_id',scope.franchise_id)
   if(r.error){setMsg(r.error.message);return}
   allowed=((r.data||[]) as unknown as FranchiseCity[]).map(x=>x.cities?.[0]).filter((x):x is City=>Boolean(x)).sort((a,b)=>a.name.localeCompare(b.name))
  }else{
   setSupportName('')
   const a=await supabase.from('profile_city_access').select('city_id').eq('profile_id',user.id)
   if(a.error){setMsg(a.error.message);return}
   const ids=((a.data||[]) as CityAccess[]).map(x=>x.city_id)
   if(ids.length){
    const r=await supabase.from('cities').select('id,name,state,center_lat,center_lng').in('id',ids).order('name')
    if(r.error){setMsg(r.error.message);return}
    allowed=(r.data||[]) as City[]
   }
  }
  clearLocations()
  setCities(allowed)
  setSelectedCity(current=>allowed.some(c=>c.id===current)?current:(allowed[0]?.id||''))
  if(!allowed[0])setMsg('Nenhuma cidade autorizada para este acesso.')
 }

 async function loadSnapshot(cityId:string,resetView=false){
  setMsg('Atualizando posições...')
  const selected=cities.find(c=>c.id===cityId)
  if(scopeRole==='franchise_admin'){
   const r=await supabase.rpc('franchise_live_driver_map',{p_city_id:cityId})
   if(r.error){setMsg(r.error.message);return}
   const list=(Array.isArray(r.data)?r.data:[]) as MapLoc[]
   applySnapshot(list)
   const located=list.filter(x=>Number.isFinite(Number(x.lat))&&Number.isFinite(Number(x.lng)))
   if(resetView&&selected&&mapRef.current&&!located.length&&Number.isFinite(Number(selected.center_lat))&&Number.isFinite(Number(selected.center_lng)))mapRef.current.setView([Number(selected.center_lat),Number(selected.center_lng)],13)
   if(resetView&&mapRef.current&&leafletRef.current&&located.length){const bounds=leafletRef.current.latLngBounds(located.map(x=>[Number(x.lat),Number(x.lng)] as[number,number]));mapRef.current.fitBounds(bounds,{padding:[30,30],maxZoom:16})}
   setMsg(list.length?`Mapa ao vivo · ${list.length} motorista(s) monitorado(s).`:'Mapa ao vivo · nenhum motorista em operação nesta cidade.')
   return
  }

  const d=await supabase.from('drivers').select('id,city_id').eq('city_id',cityId).eq('online',true)
  if(d.error){setMsg(d.error.message);return}
  const driverRows=(d.data||[]) as DriverIdRow[]
  const ids=driverRows.map(x=>x.id)
  if(!ids.length){applySnapshot([]);if(resetView&&selected&&mapRef.current&&Number.isFinite(Number(selected.center_lat))&&Number.isFinite(Number(selected.center_lng)))mapRef.current.setView([Number(selected.center_lat),Number(selected.center_lng)],13);setMsg('Mapa ao vivo · nenhum motorista online nesta cidade.');return}
  const[p,l]=await Promise.all([
   supabase.from('profiles').select('id,full_name').in('id',ids),
   supabase.from('driver_locations').select('driver_id,lat,lng,heading,speed_kmh,updated_at').in('driver_id',ids).order('updated_at',{ascending:false})
  ])
  if(p.error){setMsg(p.error.message);return}
  if(l.error){setMsg(l.error.message);return}
  const names=new Map(((p.data||[]) as Person[]).map(x=>[x.id,x.full_name||'Motorista']))
  const byLocation=new Map(((l.data||[]) as DriverLocationBroadcast[]).map(x=>[x.driver_id,x]))
  const list=driverRows.map(drow=>{const loc=byLocation.get(drow.id);return{driver_id:drow.id,full_name:names.get(drow.id)||'Motorista',online:true,status:'approved',activity_state:'online',city_id:drow.city_id,lat:loc?.lat??null,lng:loc?.lng??null,heading:loc?.heading??null,speed_kmh:loc?.speed_kmh??null,updated_at:loc?.updated_at??null} as MapLoc})
  applySnapshot(list)
  const located=list.filter(x=>Number.isFinite(Number(x.lat))&&Number.isFinite(Number(x.lng)))
  const map=mapRef.current,L=leafletRef.current
  if(resetView&&map&&L&&located.length){const bounds=L.latLngBounds(located.map(x=>[Number(x.lat),Number(x.lng)] as[number,number]));map.fitBounds(bounds,{padding:[30,30],maxZoom:16})}
  setMsg(`Mapa ao vivo · ${driverRows.length} motorista(s) online.`)
 }

 useEffect(()=>{
  void loadScope()
  const onSupport=()=>void loadScope()
  window.addEventListener('clickgo-support-session-changed',onSupport)
  return()=>window.removeEventListener('clickgo-support-session-changed',onSupport)
 },[])

 useEffect(()=>{
  let alive=true
  ;(async()=>{
   if(!mapEl.current)return
   const L=await import('leaflet')
   if(!alive||!mapEl.current)return
   leafletRef.current=L
   mapRef.current=L.map(mapEl.current,{zoomControl:true,attributionControl:true}).setView([-14.52472,-49.14083],12)
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:19}).addTo(mapRef.current)
   setMapReady(true)
  })()
  return()=>{alive=false;mapRef.current?.remove();mapRef.current=null;leafletRef.current=null;markersRef.current.clear()}
 },[])

 useEffect(()=>{
  if(!mapReady||!selectedCity||!scopeRole)return
  let cancelled=false
  let channel:ReturnType<typeof supabase.channel>|null=null
  let snapshotTimer:ReturnType<typeof setInterval>|null=null
  ;(async()=>{
   clearLocations()
   await loadSnapshot(selectedCity,true)
   if(cancelled)return
   await supabase.realtime.setAuth()
   channel=supabase.channel(cityDriverLocationsTopic(selectedCity),{config:{private:true}})
    .on('broadcast',{event:'location'},event=>{
     const location=parseDriverLocationBroadcast(event.payload)
     if(!location)return
     const raw=(event.payload&&typeof event.payload==='object'?event.payload:{}) as Record<string,unknown>
     const previous=locationsRef.current.get(location.driver_id)
     applyLocation({
      ...location,
      full_name:previous?.full_name||'Motorista',
      online:typeof raw.online==='boolean'?raw.online:true,
      activity_state:typeof raw.activity_state==='string'?raw.activity_state:previous?.activity_state||'online',
      taximeter_amount:safeNumber(raw.taximeter_amount)??previous?.taximeter_amount??null,
     })
    })
    .subscribe(status=>{
     if(status==='SUBSCRIBED')setMsg(current=>current.includes('motorista')?current:'Mapa ao vivo conectado.')
     else if(status==='CHANNEL_ERROR')setMsg('Falha temporária no mapa ao vivo.')
    })
   snapshotTimer=setInterval(()=>{if(!cancelled)void loadSnapshot(selectedCity,false)},30000)
  })()
  return()=>{cancelled=true;if(snapshotTimer)clearInterval(snapshotTimer);if(channel)void supabase.removeChannel(channel);clearLocations()}
 },[mapReady,selectedCity,cities,scopeRole])

 const selected=cities.find(c=>c.id===selectedCity)
 return <div className={compact?'live-map-card compact':'live-map-card'}>
  {supportName&&<div className="regional-alert"><strong>Matriz (Suporte) · {supportName}</strong><br/>O mapa está limitado ao território da franquia atendida.</div>}
  <div className="live-map-head"><div><div className="eyebrow">Mapa operacional</div><h2>Motoristas em tempo real</h2><p className="subtitle">Acompanhe posição, atividade e taxímetro dos motoristas da sua operação.</p></div><label><span className="label">Cidade</span><select className="input" value={selectedCity} onChange={e=>setSelectedCity(e.target.value)}>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select></label></div>
  <div className="live-map-summary"><span><b>{rows.length}</b> motorista(s) monitorado(s)</span><span>{selected?`${selected.name}/${selected.state}`:'—'}</span><span>{msg}</span></div>
  <div ref={mapEl} className="live-map-canvas" style={{height:compact?330:460}}/>
  {!compact&&<div className="table-wrap" style={{marginTop:14}}><table className="table"><thead><tr><th>Motorista</th><th>Atividade</th><th>Velocidade</th><th>Atualizado</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={4} className="empty">Nenhum motorista em operação nesta cidade.</td></tr>:rows.map(row=><tr key={row.driver_id}><td><strong>{row.full_name||'Motorista sem nome'}</strong></td><td><span className="pill green">{activityLabel(row)}</span>{row.activity_state==='taximeter'&&Number.isFinite(Number(row.taximeter_amount))?<small style={{display:'block',marginTop:4}}>Taxímetro: {Number(row.taximeter_amount).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</small>:null}</td><td>{Math.round(row.speed_kmh??0)} km/h</td><td>{row.updated_at?new Date(row.updated_at).toLocaleString('pt-BR'):'Aguardando localização GPS'}</td></tr>)}</tbody></table></div>}
 </div>
}
