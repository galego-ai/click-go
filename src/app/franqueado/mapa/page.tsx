'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

type Driver={id:string;online:boolean;status:string;city_id:string|null}
type Location={driver_id:string;lat:number;lng:number;heading:number|null;speed_kmh:number|null;updated_at:string}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',borderRadius:10,padding:'10px 14px',fontWeight:800,textDecoration:'none'}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}

declare global { interface Window { google:any } }

export default function MapaPage(){
 const ref=useRef<HTMLDivElement|null>(null);const [drivers,setDrivers]=useState<Driver[]>([]),[locs,setLocs]=useState<Location[]>([]),[msg,setMsg]=useState(''),[loaded,setLoaded]=useState(false)
 useEffect(()=>{load();const id=setInterval(load,15000);return()=>clearInterval(id)},[])
 useEffect(()=>{renderMap()},[drivers,locs,loaded])
 async function load(){try{const {data:{user}}=await supabase.auth.getUser();if(!user)return setMsg('Faça login.');const {data:p}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(!p||p.role!=='franchise_admin'||!p.franchise_id)return setMsg('Acesso exclusivo do franqueado.');const {data:d}=await supabase.from('drivers').select('id,online,status,city_id').eq('franchise_id',p.franchise_id);const ids=(d||[]).map((x:any)=>x.id);setDrivers((d||[]) as Driver[]);if(ids.length){const {data:l}=await supabase.from('driver_locations').select('*').in('driver_id',ids).order('updated_at',{ascending:false});setLocs((l||[]) as Location[])}}catch(e:any){setMsg(e.message)}}
 useEffect(()=>{const key=process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;if(!key){setMsg('Mapa preparado. Falta configurar NEXT_PUBLIC_GOOGLE_MAPS_API_KEY na Vercel.');return}if(window.google?.maps){setLoaded(true);return}const s=document.createElement('script');s.src=`https://maps.googleapis.com/maps/api/js?key=${key}`;s.async=true;s.onload=()=>setLoaded(true);s.onerror=()=>setMsg('Não foi possível carregar o Google Maps.');document.head.appendChild(s);return()=>{s.onload=null}},[])
 function renderMap(){if(!loaded||!ref.current||!window.google?.maps)return;const valid=locs.filter(l=>drivers.some(d=>d.id===l.driver_id));const center=valid[0]?{lat:valid[0].lat,lng:valid[0].lng}:{lat:-15.7801,lng:-47.9292};const map=new window.google.maps.Map(ref.current,{center,zoom:valid.length?13:5,mapTypeControl:false,streetViewControl:false});valid.forEach(l=>{const d=drivers.find(x=>x.id===l.driver_id);new window.google.maps.Marker({position:{lat:l.lat,lng:l.lng},map,title:`Motorista ${l.driver_id.slice(0,8)} · ${d?.online?'online':'offline'}`})})}
 const active=drivers.filter(d=>d.online&&d.status==='approved').length
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1400,margin:'0 auto'}}><div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO</div><h1>Mapa operacional</h1><div style={{color:'#9ca3af'}}>Atualização automática a cada 15 segundos</div></div><Link href="/franqueado/operacao" style={btn}>Central operacional</Link></div>{msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',margin:'15px 0'}}>{msg}</div>}<div style={{display:'grid',gridTemplateColumns:'1fr 330px',gap:16,marginTop:16}}><div ref={ref} style={{height:650,borderRadius:16,background:'#1a1a1a',border:'1px solid #292929'}}/><aside style={box}><h2>Motoristas</h2><div style={{fontSize:28,fontWeight:900,color:'#ffd400'}}>{active} online</div><div style={{display:'grid',gap:8,marginTop:15,maxHeight:540,overflow:'auto'}}>{locs.filter(l=>drivers.some(d=>d.id===l.driver_id)).map(l=>{const d=drivers.find(x=>x.id===l.driver_id);return <div key={l.driver_id} style={{...box,padding:11}}><b>{l.driver_id.slice(0,8)}</b><div style={{color:d?.online?'#86efac':'#9ca3af'}}>{d?.online?'● Online':'● Offline'}</div><div style={{fontSize:12,color:'#9ca3af'}}>{l.lat.toFixed(5)}, {l.lng.toFixed(5)} · {Number(l.speed_kmh||0).toFixed(0)} km/h</div><a href={`https://www.google.com/maps?q=${l.lat},${l.lng}`} target="_blank" rel="noreferrer" style={{color:'#ffd400',fontSize:12}}>Abrir localização</a></div>})}</div></aside></div></div></main>
}
