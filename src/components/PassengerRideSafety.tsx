'use client'

import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Contact={id:string;name:string;phone:string;relationship:string|null}
type Safety={pin:string|null;pin_verified_at:string|null;primary_contact:Contact|null}
type Alert={id:string;alert_type:string;severity:string;reporter_role:string;message:string|null;distance_from_route_m:number|null;status:string;created_at:string}
const panel:React.CSSProperties={background:'#fff',border:'1px solid #e5e7eb',borderRadius:18,padding:15,color:'#111'}
const btn:React.CSSProperties={border:0,borderRadius:13,padding:'12px 14px',fontWeight:900,cursor:'pointer'}

export default function PassengerRideSafety({rideId,status}:{rideId:string;status:string}){
 const[safety,setSafety]=useState<Safety|null>(null),[alerts,setAlerts]=useState<Alert[]>([]),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 useEffect(()=>{void load();const t=window.setInterval(loadAlerts,10000);return()=>window.clearInterval(t)},[rideId])
 useEffect(()=>{void load()},[status])
 async function load(){await Promise.all([loadSafety(),loadAlerts()])}
 async function loadSafety(){const{data,error}=await supabase.rpc('get_passenger_ride_safety',{p_ride_id:rideId});if(!error&&data)setSafety(data as Safety)}
 async function loadAlerts(){const{data,error}=await supabase.rpc('get_ride_safety_alerts',{p_ride_id:rideId});if(!error)setAlerts(Array.isArray(data)?data as Alert:[])}
 function getPosition():Promise<GeolocationPosition|null>{return new Promise(resolve=>{if(!navigator.geolocation)return resolve(null);navigator.geolocation.getCurrentPosition(resolve,()=>resolve(null),{enableHighAccuracy:true,timeout:7000,maximumAge:5000})})}
 async function sos(){
  if(!window.confirm('Acionar o SOS desta corrida? Este evento será registrado com sua localização quando disponível.'))return
  setBusy(true);setMsg('Registrando alerta de segurança...')
  const p=await getPosition()
  const{data,error}=await supabase.rpc('trigger_ride_sos',{p_ride_id:rideId,p_lat:p?.coords.latitude??null,p_lng:p?.coords.longitude??null,p_message:'SOS acionado pelo passageiro no app CLICK-GO.'})
  setBusy(false)
  if(error){setMsg(error.message);return}
  setMsg(data?.ok?'SOS registrado. Compartilhe a corrida e procure ajuda local adequada em uma emergência.':'Não foi possível confirmar o SOS.')
  await loadAlerts()
 }
 const active=alerts.filter(a=>a.status==='open')
 const pinVisible=['accepted','driver_arriving'].includes(status)&&!safety?.pin_verified_at
 return <div style={{...panel,display:'grid',gap:12,borderColor:active.length?'#ef4444':'#e5e7eb'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center'}}><div><b style={{fontSize:17}}>🛡️ Segurança da corrida</b><div style={{fontSize:12,color:'#666',marginTop:3}}>PIN de embarque, SOS e alertas do trajeto.</div></div><button disabled={busy} onClick={sos} style={{...btn,background:'#b91c1c',color:'#fff'}}>SOS</button></div>
  {pinVisible&&<div style={{background:'#111',color:'#fff',borderRadius:14,padding:14,textAlign:'center'}}><div style={{fontSize:12,color:'#d1d5db',fontWeight:800}}>PIN PARA INICIAR A CORRIDA</div><div style={{fontSize:34,fontWeight:950,letterSpacing:9,color:'#ffd400',marginTop:5}}>{safety?.pin||'••••'}</div><div style={{fontSize:12,color:'#d1d5db',marginTop:5}}>Informe estes 4 dígitos ao motorista somente depois de conferir motorista, foto, veículo e placa.</div></div>}
  {safety?.pin_verified_at&&<div style={{background:'#ecfdf5',border:'1px solid #a7f3d0',borderRadius:12,padding:10,color:'#065f46',fontWeight:800}}>✓ PIN confirmado — embarque validado.</div>}
  {safety?.primary_contact&&<div style={{display:'flex',justifyContent:'space-between',gap:10,alignItems:'center',background:'#f8fafc',borderRadius:12,padding:10}}><div><b>{safety.primary_contact.name}</b><div style={{fontSize:12,color:'#666'}}>{safety.primary_contact.relationship||'Contato de segurança'} · {safety.primary_contact.phone}</div></div><a href={`tel:${safety.primary_contact.phone.replace(/[^0-9+]/g,'')}`} style={{...btn,background:'#111',color:'#fff',textDecoration:'none',padding:'9px 11px'}}>Ligar</a></div>}
  {active.length>0&&<div style={{background:'#fef2f2',border:'1px solid #fecaca',borderRadius:12,padding:11}}><b style={{color:'#991b1b'}}>Alerta de segurança ativo</b>{active.slice(0,2).map(a=><div key={a.id} style={{fontSize:12,color:'#7f1d1d',marginTop:5}}>{a.alert_type==='route_deviation'?`Possível desvio de rota${a.distance_from_route_m?` · ${Math.round(Number(a.distance_from_route_m))} m`:''}`:'SOS acionado'} · {new Date(a.created_at).toLocaleTimeString('pt-BR')}</div>)}</div>}
  {msg&&<div style={{fontSize:12,color:'#7c2d12'}}>{msg}</div>}
 </div>
}
