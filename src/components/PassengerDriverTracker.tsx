'use client'

import { useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'
import 'leaflet/dist/leaflet.css'

type Loc={lat:number;lng:number;heading:number|null;speed_kmh:number|null;updated_at:string}
type RidePoint={origin_lat:number;origin_lng:number;destination_lat:number;destination_lng:number}

export default function PassengerDriverTracker({rideId,driverId}:{rideId:string;driverId:string}){
 const[loc,setLoc]=useState<Loc|null>(null),[ride,setRide]=useState<RidePoint|null>(null),[msg,setMsg]=useState('Carregando localização do motorista...')
 const mapEl=useRef<HTMLDivElement|null>(null),mapRef=useRef<any>(null),layerRef=useRef<any>(null)
 useEffect(()=>{load();const ch=supabase.channel(`passenger-driver-${driverId}`).on('postgres_changes',{event:'*',schema:'public',table:'driver_locations',filter:`driver_id=eq.${driverId}`},(p:any)=>{if(p.new?.lat!=null){setLoc(p.new as Loc);setMsg('Localização atualizada em tempo real.')}}).subscribe();return()=>{supabase.removeChannel(ch)}},[rideId,driverId])
 async function load(){const[{data:l,error:le},{data:r,error:re}]=await Promise.all([supabase.from('driver_locations').select('lat,lng,heading,speed_kmh,updated_at').eq('driver_id',driverId).maybeSingle(),supabase.from('rides').select('origin_lat,origin_lng,destination_lat,destination_lng').eq('id',rideId).single()]);if(l)setLoc(l as Loc);if(r)setRide(r as RidePoint);if(le)setMsg('A localização do motorista aparecerá assim que o GPS dele atualizar.');else if(re)setMsg(re.message);else setMsg(l?'Motorista localizado.':'Aguardando GPS do motorista...')}
 useEffect(()=>{let alive=true;(async()=>{if(!mapEl.current)return;const L=await import('leaflet');if(!alive)return;if(!mapRef.current){mapRef.current=L.map(mapEl.current).setView([-14.52472,-49.14083],14);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors',maxZoom:19}).addTo(mapRef.current);layerRef.current=L.layerGroup().addTo(mapRef.current)}layerRef.current.clearLayers();const pts:[number,number][]=[];if(loc){L.circleMarker([loc.lat,loc.lng],{radius:9}).bindTooltip('Motorista').addTo(layerRef.current);pts.push([loc.lat,loc.lng])}if(ride){L.circleMarker([ride.origin_lat,ride.origin_lng],{radius:7}).bindTooltip('Embarque').addTo(layerRef.current);L.circleMarker([ride.destination_lat,ride.destination_lng],{radius:7}).bindTooltip('Destino').addTo(layerRef.current);pts.push([ride.origin_lat,ride.origin_lng]);if(loc)L.polyline([[loc.lat,loc.lng],[ride.origin_lat,ride.origin_lng]]).addTo(layerRef.current)}if(pts.length>1)mapRef.current.fitBounds(pts,{padding:[30,30]});else if(pts.length===1)mapRef.current.setView(pts[0],15)})();return()=>{alive=false}},[loc,ride]);useEffect(()=>()=>{if(mapRef.current){mapRef.current.remove();mapRef.current=null}},[])
 return <div style={{marginTop:14,background:'#0d0d0d',border:'1px solid #292929',borderRadius:14,padding:10}}><b>Motorista em tempo real</b><div ref={mapEl} style={{height:260,borderRadius:11,overflow:'hidden',marginTop:9}}/><div style={{color:'#9ca3af',fontSize:12,marginTop:8}}>{msg}{loc?` · última atualização ${new Date(loc.updated_at).toLocaleTimeString('pt-BR')}`:''}</div></div>
}
