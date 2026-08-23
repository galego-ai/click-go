'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'

type RideSummary={
 id:string;origin_lat:number|null;origin_lng:number|null;destination_lat:number|null;destination_lng:number|null;
 arrived_at:string|null;arrived_lat:number|null;arrived_lng:number|null;started_at:string|null;started_lat:number|null;started_lng:number|null;
 completed_at:string|null;completed_lat:number|null;completed_lng:number|null;wait_charge_amount:number|string|null
}
type Point={id:number;lat:number;lng:number;heading:number|null;speed_kmh:number|null;phase:string;recorded_at:string}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const coord=(lat:number|null,lng:number|null)=>lat==null||lng==null?'—':`${Number(lat).toFixed(6)}, ${Number(lng).toFixed(6)}`

export default function RideCoordinatesDetails({ride,dark=false}:{ride:RideSummary;dark?:boolean}){
 const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false),[loading,setLoading]=useState(false),[points,setPoints]=useState<Point[]>([]),[error,setError]=useState('')
 async function toggle(){
  const next=!open;setOpen(next);if(!next||loaded)return
  setLoading(true);setError('')
  const{data,error}=await supabase.from('ride_location_points').select('id,lat,lng,heading,speed_kmh,phase,recorded_at').eq('ride_id',ride.id).order('recorded_at',{ascending:true})
  setLoading(false);if(error){setError(error.message);return}setPoints((data||[]) as Point[]);setLoaded(true)
 }
 const panel=dark?'#0d0d0d':'#f7f7f7',border=dark?'#303030':'#ddd',muted=dark?'#9ca3af':'#666'
 return <div style={{marginTop:8}}>
  <button onClick={toggle} style={{border:`1px solid ${border}`,background:panel,color:dark?'#fff':'#111',borderRadius:9,padding:'7px 10px',fontWeight:800,cursor:'pointer'}}>{open?'Ocultar coordenadas':'Ver coordenadas e trajeto'}</button>
  {open&&<div style={{marginTop:8,background:panel,border:`1px solid ${border}`,borderRadius:12,padding:12,fontSize:12,color:dark?'#fff':'#111'}}>
   <div style={{display:'grid',gap:5}}>
    <div><b>Origem solicitada:</b> {coord(ride.origin_lat,ride.origin_lng)}</div>
    <div><b>Destino solicitado:</b> {coord(ride.destination_lat,ride.destination_lng)}</div>
    <div><b>Chegada ao embarque:</b> {coord(ride.arrived_lat,ride.arrived_lng)}{ride.arrived_at?` · ${new Date(ride.arrived_at).toLocaleString('pt-BR')}`:''}</div>
    <div><b>Início da corrida:</b> {coord(ride.started_lat,ride.started_lng)}{ride.started_at?` · ${new Date(ride.started_at).toLocaleString('pt-BR')}`:''}</div>
    <div><b>Fim da corrida:</b> {coord(ride.completed_lat,ride.completed_lng)}{ride.completed_at?` · ${new Date(ride.completed_at).toLocaleString('pt-BR')}`:''}</div>
    <div><b>Taxa de espera registrada:</b> {money(ride.wait_charge_amount)}</div>
   </div>
   <div style={{borderTop:`1px solid ${border}`,marginTop:10,paddingTop:10}}><b>Pontos GPS registrados durante a corrida</b>{loading&&<div style={{color:muted,marginTop:6}}>Carregando...</div>}{error&&<div style={{color:'#dc2626',marginTop:6}}>{error}</div>}{loaded&&!points.length&&<div style={{color:muted,marginTop:6}}>Nenhum ponto adicional foi registrado nesta corrida.</div>}{points.length>0&&<div style={{maxHeight:260,overflow:'auto',marginTop:7,display:'grid',gap:5}}>{points.map((p,i)=><div key={p.id} style={{padding:'7px 8px',border:`1px solid ${border}`,borderRadius:8}}><b>#{i+1}</b> · {Number(p.lat).toFixed(6)}, {Number(p.lng).toFixed(6)} · {p.phase} · {new Date(p.recorded_at).toLocaleString('pt-BR')}{p.speed_kmh!=null?` · ${Number(p.speed_kmh).toFixed(0)} km/h`:''}{p.heading!=null?` · rumo ${Number(p.heading).toFixed(0)}°`:''}</div>)}</div>}</div>
  </div>}
 </div>
}
