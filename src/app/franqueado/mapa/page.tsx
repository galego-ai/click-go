'use client'

import { useEffect,useRef,useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

type Driver={id:string;online:boolean;status:string;city_id:string|null}
type Location={driver_id:string;lat:number;lng:number;heading:number|null;speed_kmh:number|null;updated_at:string}
type Place={id:string;name:string;address:string;phone:string;lat:number;lng:number;type:string;googleMapsUri:string}
type Center={lat:number;lng:number;label:string}
type MapMode='street'|'satellite'

const btn:React.CSSProperties={background:'#ffd400',color:'#000',borderRadius:10,padding:'10px 14px',fontWeight:800,textDecoration:'none',border:0,cursor:'pointer'}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}

export default function MapaPage(){
 const ref=useRef<HTMLDivElement|null>(null),mapRef=useRef<any>(null),LRef=useRef<any>(null),baseRef=useRef<any>(null),labelsRef=useRef<any[]>([]),driverLayerRef=useRef<any>(null),placeLayerRef=useRef<any>(null),placeCache=useRef({key:'',at:0}),centeredRef=useRef(false)
 const[drivers,setDrivers]=useState<Driver[]>([]),[locs,setLocs]=useState<Location[]>([]),[places,setPlaces]=useState<Place[]>([]),[centerHint,setCenterHint]=useState<Center|null>(null),[msg,setMsg]=useState(''),[googleMsg,setGoogleMsg]=useState(''),[ready,setReady]=useState(false),[mode,setMode]=useState<MapMode>('street')

 useEffect(()=>{load();const id=setInterval(load,15000);return()=>clearInterval(id)},[])
 useEffect(()=>{let cancelled=false;(async()=>{if(!ref.current||mapRef.current)return;const L=await import('leaflet');if(cancelled||!ref.current)return;LRef.current=L;const map=L.map(ref.current,{zoomControl:false,attributionControl:true,minZoom:3,maxZoom:19}).setView([-15.7801,-47.9292],5);mapRef.current=map;driverLayerRef.current=L.layerGroup().addTo(map);placeLayerRef.current=L.layerGroup().addTo(map);map.on('moveend',()=>{const c=map.getCenter();loadPlaces(c.lat,c.lng)});setReady(true)})().catch(()=>setMsg('Não foi possível iniciar o mapa operacional.'));return()=>{cancelled=true;if(mapRef.current){try{mapRef.current.remove()}catch{}mapRef.current=null}}},[])
 useEffect(()=>{if(!ready)return;applyMapMode()},[ready,mode])
 useEffect(()=>{if(!ready)return;renderMarkers()},[ready,drivers,locs,places,centerHint])

 async function loadPlaces(lat:number,lng:number){
  const key=`${lat.toFixed(2)}:${lng.toFixed(2)}`,now=Date.now();if(placeCache.current.key===key&&now-placeCache.current.at<300000)return;placeCache.current={key,at:now}
  try{const r=await fetch(`/api/google-places?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}&radius=2500`,{cache:'no-store'});const j=await r.json();if(r.ok&&Array.isArray(j.places)){setPlaces(j.places);setGoogleMsg('')}else if(j?.configured===false){setPlaces([]);setGoogleMsg('O mapa está funcionando. Para mostrar empresas e telefones cadastrados no Google, falta configurar GOOGLE_PLACES_API_KEY no servidor da Vercel.')}}catch{setGoogleMsg('Mapa funcionando; consulta de empresas do Google temporariamente indisponível.')}
 }

 async function load(){try{
  const{data:{user}}=await supabase.auth.getUser();if(!user){setMsg('Faça login.');return}
  const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe;if(!p||p.role!=='franchise_admin'||!p.franchise_id){setMsg('Acesso exclusivo do franqueado.');return}
  const[{data:d,error:de},{data:fc,error:fce}]=await Promise.all([supabase.from('drivers').select('id,online,status,city_id').eq('franchise_id',p.franchise_id),supabase.from('franchise_cities').select('cities(name,state,center_lat,center_lng)').eq('franchise_id',p.franchise_id).limit(1)]);if(de)throw de;if(fce)throw fce
  const city:any=(fc||[])[0]?.cities;if(city&&Number.isFinite(Number(city.center_lat))&&Number.isFinite(Number(city.center_lng)))setCenterHint({lat:Number(city.center_lat),lng:Number(city.center_lng),label:`${city.name}/${city.state}`})
  const ds=(d||[]) as Driver[],ids=ds.map(x=>x.id);setDrivers(ds)
  if(ids.length){const{data:l,error:le}=await supabase.from('driver_locations').select('*').in('driver_id',ids).order('updated_at',{ascending:false});if(le)throw le;const rows=(l||[]) as Location[];setLocs(rows);if(rows[0])loadPlaces(rows[0].lat,rows[0].lng);else if(city?.center_lat&&city?.center_lng)loadPlaces(Number(city.center_lat),Number(city.center_lng))}
  else{setLocs([]);if(city?.center_lat&&city?.center_lng)loadPlaces(Number(city.center_lat),Number(city.center_lng))}
  setMsg('')
 }catch(e:any){setMsg(e.message||'Erro ao carregar o mapa.')}}

 function applyMapMode(){
  const L=LRef.current,map=mapRef.current;if(!L||!map)return
  if(baseRef.current)try{map.removeLayer(baseRef.current)}catch{}
  for(const layer of labelsRef.current)try{map.removeLayer(layer)}catch{};labelsRef.current=[]
  if(mode==='street'){
   baseRef.current=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map)
  }else{
   baseRef.current=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles © Esri'}).addTo(map)
   const roads=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,opacity:.85}).addTo(map)
   const names=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,opacity:1}).addTo(map)
   labelsRef.current=[roads,names]
  }
 }

 function renderMarkers(){
  const L=LRef.current,map=mapRef.current,driverLayer=driverLayerRef.current,placeLayer=placeLayerRef.current;if(!L||!map||!driverLayer||!placeLayer)return
  driverLayer.clearLayers();placeLayer.clearLayers()
  const valid=locs.filter(l=>drivers.some(d=>d.id===l.driver_id))
  valid.forEach(l=>{const d=drivers.find(x=>x.id===l.driver_id);const m=L.circleMarker([l.lat,l.lng],{radius:9,weight:3,color:'#111111',fillColor:d?.online?'#22c55e':'#9ca3af',fillOpacity:1});m.bindPopup(`<b>Motorista ${l.driver_id.slice(0,8)}</b><br>${d?.online?'Online':'Offline'}<br>${Number(l.speed_kmh||0).toFixed(0)} km/h`);m.addTo(driverLayer)})
  places.forEach(p=>{if(!Number.isFinite(Number(p.lat))||!Number.isFinite(Number(p.lng)))return;const phone=p.phone?`<br><b>📞 ${escapeHtml(p.phone)}</b>`:'<br>Telefone não informado no Google';const address=p.address?`<br>${escapeHtml(p.address)}`:'';const m=L.circleMarker([Number(p.lat),Number(p.lng)],{radius:7,weight:2,color:'#111111',fillColor:'#ffd400',fillOpacity:1});m.bindPopup(`<b>${escapeHtml(p.name)}</b>${address}${phone}`);m.addTo(placeLayer)})
  if(!centeredRef.current){if(valid.length){const bounds=L.latLngBounds(valid.map(x=>[x.lat,x.lng]));valid.length===1?map.setView([valid[0].lat,valid[0].lng],14):map.fitBounds(bounds.pad(.2));centeredRef.current=true}else if(centerHint){map.setView([centerHint.lat,centerHint.lng],13);centeredRef.current=true}}
 }
 function escapeHtml(v:string){return String(v||'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]||c))}
 function zoom(delta:number){const map=mapRef.current;if(!map)return;delta>0?map.zoomIn():map.zoomOut()}
 const active=drivers.filter(d=>d.online&&d.status==='approved').length

 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1400,margin:'0 auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO</div><h1>Mapa operacional</h1><div style={{color:'#9ca3af'}}>Motoristas atualizados a cada 15 segundos · mapa funciona sem chave pública do Google · empresas Google aparecem quando o Places estiver configurado</div></div><Link href="/franqueado/operacao" style={btn}>Central operacional</Link></div>
  {msg&&<div style={{...box,borderColor:'#7f1d1d',color:'#fecaca',margin:'15px 0'}}>{msg}</div>}{googleMsg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',margin:'15px 0'}}>{googleMsg}</div>}
  <div style={{display:'flex',gap:8,marginTop:16,flexWrap:'wrap'}}><button style={{...btn,background:mode==='street'?'#ffd400':'#222',color:mode==='street'?'#000':'#fff'}} onClick={()=>setMode('street')}>Rua / bairros</button><button style={{...btn,background:mode==='satellite'?'#ffd400':'#222',color:mode==='satellite'?'#000':'#fff'}} onClick={()=>setMode('satellite')}>Satélite + nomes</button><button style={{...btn,background:'#222',color:'#fff'}} onClick={()=>zoom(1)}>＋ Zoom</button><button style={{...btn,background:'#222',color:'#fff'}} onClick={()=>zoom(-1)}>－ Zoom</button></div>
  <div style={{display:'grid',gridTemplateColumns:'minmax(0,1fr) 350px',gap:16,marginTop:10}}><div ref={ref} style={{height:650,borderRadius:16,background:'#1a1a1a',border:'1px solid #292929',overflow:'hidden'}}/><aside style={{...box,maxHeight:650,overflow:'auto'}}>
   <h2>Motoristas</h2><div style={{fontSize:28,fontWeight:900,color:'#ffd400'}}>{active} online</div><div style={{display:'grid',gap:8,marginTop:15}}>{locs.filter(l=>drivers.some(d=>d.id===l.driver_id)).map(l=>{const d=drivers.find(x=>x.id===l.driver_id);return <div key={l.driver_id} style={{...box,padding:11}}><b>{l.driver_id.slice(0,8)}</b><div style={{color:d?.online?'#86efac':'#9ca3af'}}>{d?.online?'● Online':'● Offline'}</div><div style={{fontSize:12,color:'#9ca3af'}}>{l.lat.toFixed(5)}, {l.lng.toFixed(5)} · {Number(l.speed_kmh||0).toFixed(0)} km/h</div><a href={`https://www.google.com/maps?q=${l.lat},${l.lng}`} target="_blank" rel="noreferrer" style={{color:'#ffd400',fontSize:12}}>Abrir localização</a></div>})}</div>
   <h2 style={{marginTop:22}}>Empresas próximas</h2><div style={{color:'#9ca3af',fontSize:12,marginBottom:10}}>Quando GOOGLE_PLACES_API_KEY estiver configurada, aparecem aqui empresas cadastradas no Google com telefone e endereço.</div><div style={{display:'grid',gap:8}}>{places.map(p=><div key={p.id} style={{...box,padding:11}}><b>{p.name}</b>{p.type&&<div style={{fontSize:12,color:'#9ca3af'}}>{p.type}</div>}<div style={{fontSize:12,color:'#d1d5db',marginTop:4}}>{p.address}</div>{p.phone?<a href={`tel:${p.phone.replace(/[^+\d]/g,'')}`} style={{color:'#ffd400',fontWeight:800,display:'block',marginTop:6}}>📞 {p.phone}</a>:<div style={{fontSize:12,color:'#6b7280',marginTop:6}}>Telefone não informado no Google</div>}</div>)}{!places.length&&<div style={{color:'#9ca3af'}}>Nenhuma empresa Google carregada nesta área.</div>}</div>
  </aside></div>
 </div></main>
}
