'use client'

import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'
import RideCoordinatesDetails from '@/components/RideCoordinatesDetails'

type Ride={id:string;status:string;origin_label:string;destination_label:string;estimated_fare:number|string|null;final_fare:number|string|null;requested_at:string;origin_lat:number|null;origin_lng:number|null;destination_lat:number|null;destination_lng:number|null;arrived_at:string|null;arrived_lat:number|null;arrived_lng:number|null;started_at:string|null;started_lat:number|null;started_lng:number|null;completed_at:string|null;completed_lat:number|null;completed_lng:number|null;wait_charge_amount:number|string|null}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:14,padding:14}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})

export default function DriverRideHistory(){
 const[rides,setRides]=useState<Ride[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState('')
 useEffect(()=>{load()},[])
 async function load(){setLoading(true);const{data:{user}}=await supabase.auth.getUser();if(!user){setLoading(false);return}const{data,error}=await supabase.from('rides').select('id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,origin_lat,origin_lng,destination_lat,destination_lng,arrived_at,arrived_lat,arrived_lng,started_at,started_lat,started_lng,completed_at,completed_lat,completed_lng,wait_charge_amount').eq('driver_id',user.id).order('requested_at',{ascending:false}).limit(100);setLoading(false);if(error){setError(error.message);return}setRides((data||[]) as Ride[])}
 if(loading)return <p className="subtitle">Carregando histórico...</p>
 if(error)return <p style={{color:'#fca5a5'}}>{error}</p>
 return <div style={{display:'grid',gap:10}}>{rides.map(r=><div key={r.id} style={box}><div style={{display:'grid',gridTemplateColumns:'1fr auto',gap:12}}><div><b>{r.origin_label} → {r.destination_label}</b><div style={{fontSize:12,color:'#9ca3af',marginTop:5}}>{new Date(r.requested_at).toLocaleString('pt-BR')} · {r.status}</div></div><div style={{fontWeight:900,color:'#ffd400'}}>{money(r.final_fare??r.estimated_fare)}</div></div><RideCoordinatesDetails ride={r} dark/></div>)}{!rides.length&&<div style={box}>Nenhuma corrida encontrada.</div>}</div>
}
