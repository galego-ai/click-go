'use client'

import { useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'
import AddressSearch from '@/components/AddressSearch'
import PassengerDriverTracker from '@/components/PassengerDriverTracker'
import 'leaflet/dist/leaflet.css'

type Point={lat:number;lng:number}
type PaymentMethod={id:string;method_type:string;brand:string|null;last4:string|null;is_default:boolean}
type RideOption={city_id:string;franchise_id:string;city_name:string;state:string;category_id:string|null;category_name:string|null;required_vehicle_type:string|null;distance_km:number|string;duration_min:number|string;fare:number|string|null;multiplier:number|string|null}
type PaySettings={cash_enabled:boolean;pix_enabled:boolean;card_app_enabled:boolean;card_machine_enabled:boolean;card_credit_enabled:boolean;card_debit_enabled:boolean;app_card_gateway:string|null;card_surcharge_percentage:number|string;card_fee_bearer:string;installments_enabled:boolean;max_installments:number}
type Ride={id:string;status:string;driver_id:string|null;estimated_fare:number|string|null;final_fare:number|string|null;origin_label:string;destination_label:string;estimated_arrival_min:number|null;cancellation_fee_applied:boolean;cancellation_fee_amount:number|string}
type SearchResult={label:string;lat:number;lng:number}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:16}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})

export default function PassengerRideRequest({methods,onRideCreated}:{methods:PaymentMethod[];onRideCreated?:()=>void}){
 const mapEl=useRef<HTMLDivElement|null>(null),mapRef=useRef<any>(null),layerRef=useRef<any>(null),originRef=useRef<Point|null>(null)
 const[origin,setOrigin]=useState<Point|null>(null),[destination,setDestination]=useState<Point|null>(null)
 const[originLabel,setOriginLabel]=useState('Minha localização'),[destinationLabel,setDestinationLabel]=useState('Destino selecionado no mapa')
 const[options,setOptions]=useState<RideOption[]>([]),[selected,setSelected]=useState<string>(''),[payment,setPayment]=useState('cash'),[paySettings,setPaySettings]=useState<PaySettings|null>(null)
 const[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[currentRide,setCurrentRide]=useState<Ride|null>(null)

 useEffect(()=>{originRef.current=origin},[origin])
 useEffect(()=>{const preferred=methods.find(m=>m.is_default)||methods[0];if(preferred?.method_type==='card'&&paySettings?.card_app_enabled)setPayment('card')},[methods,paySettings?.card_app_enabled])

 useEffect(()=>{
   let alive=true
   ;(async()=>{
     if(!mapEl.current)return
     const L=await import('leaflet');if(!alive)return
     if(!mapRef.current){
       mapRef.current=L.map(mapEl.current).setView([-14.52472,-49.14083],13)
       L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors',maxZoom:19}).addTo(mapRef.current)
       layerRef.current=L.layerGroup().addTo(mapRef.current)
       mapRef.current.on('click',(e:any)=>{const p={lat:e.latlng.lat,lng:e.latlng.lng};if(!originRef.current){setOrigin(p);setOriginLabel('Origem selecionada no mapa')}else{setDestination(p);setDestinationLabel('Destino selecionado no mapa')}})
     }
     layerRef.current.clearLayers()
     if(origin)L.circleMarker([origin.lat,origin.lng],{radius:8}).bindTooltip('Origem').addTo(layerRef.current)
     if(destination)L.circleMarker([destination.lat,destination.lng],{radius:8}).bindTooltip('Destino').addTo(layerRef.current)
     if(origin&&destination){L.polyline([[origin.lat,origin.lng],[destination.lat,destination.lng]]).addTo(layerRef.current);mapRef.current.fitBounds([[origin.lat,origin.lng],[destination.lat,destination.lng]],{padding:[35,35]})}
     else if(origin)mapRef.current.setView([origin.lat,origin.lng],15)
     else if(destination)mapRef.current.setView([destination.lat,destination.lng],15)
   })()
   return()=>{alive=false}
 },[origin,destination])
 useEffect(()=>()=>{if(mapRef.current){mapRef.current.remove();mapRef.current=null}},[])

 useEffect(()=>{
   if(!currentRide?.id)return
   const channel=supabase.channel(`passenger-ride-${currentRide.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'rides',filter:`id=eq.${currentRide.id}`},(payload:any)=>{setCurrentRide(payload.new as Ride);if(['completed','cancelled'].includes(payload.new.status))onRideCreated?.()}).subscribe()
   return()=>{supabase.removeChannel(channel)}
 },[currentRide?.id,onRideCreated])

 function clearCalculated(){setOptions([]);setSelected('');setPaySettings(null)}
 function useMyLocation(){setMsg('');if(!navigator.geolocation){setMsg('Este navegador não disponibiliza geolocalização. Clique no mapa para marcar a origem.');return}setBusy(true);navigator.geolocation.getCurrentPosition(pos=>{const p={lat:pos.coords.latitude,lng:pos.coords.longitude};setOrigin(p);setOriginLabel('Minha localização atual');clearCalculated();setBusy(false)},err=>{setMsg(err.code===1?'Permissão de localização negada. Você pode pesquisar ou marcar a origem no mapa.':'Não foi possível obter sua localização. Pesquise ou marque a origem no mapa.');setBusy(false)},{enableHighAccuracy:true,timeout:12000,maximumAge:30000})}
 function chooseOrigin(r:SearchResult){setOrigin({lat:r.lat,lng:r.lng});setOriginLabel(r.label);clearCalculated();setMsg('Origem encontrada. Agora escolha o destino.')}
 function chooseDestination(r:SearchResult){setDestination({lat:r.lat,lng:r.lng});setDestinationLabel(r.label);clearCalculated();setMsg('Destino encontrado. Agora calcule as opções da corrida.')}

 async function calculate(){
   if(!origin||!destination){setMsg('Defina a origem e o destino.');return}
   setBusy(true);setMsg('Calculando cidade, distância, tempo, tarifas e pagamentos...');clearCalculated()
   const{data,error}=await supabase.rpc('get_passenger_ride_options',{p_origin_lat:origin.lat,p_origin_lng:origin.lng,p_destination_lat:destination.lat,p_destination_lng:destination.lng})
   if(error){setBusy(false);setMsg(error.message);return}
   const rows=(data||[]) as RideOption[];setOptions(rows);const first=rows[0]
   if(!first){setBusy(false);setMsg('Não foi possível calcular opções para esta rota.');return}
   const{data:ps,error:pse}=await supabase.rpc('get_effective_payment_settings',{p_city_id:first.city_id});setBusy(false)
   if(pse){setMsg(pse.message);return}
   const settings=(ps?.[0]||null) as PaySettings|null;setPaySettings(settings)
   if(!first.category_id){setMsg(`Localização reconhecida como ${first.city_name}/${first.state}, mas a franquia ainda não configurou nenhuma categoria/tarifa ativa.`);return}
   if(!settings||(!settings.cash_enabled&&!settings.pix_enabled&&!settings.card_app_enabled&&!settings.card_machine_enabled)){setMsg('Nenhuma forma de pagamento está habilitada para esta cidade.');return}
   setSelected(first.category_id)
   const hasCard=methods.some(m=>m.method_type==='card')
   if(settings.cash_enabled)setPayment('cash');else if(settings.pix_enabled)setPayment('pix');else if(settings.card_app_enabled&&hasCard)setPayment('card');else if(settings.card_machine_enabled)setPayment('card_machine')
   setMsg(`Operação encontrada em ${first.city_name}/${first.state}. Escolha a categoria e a forma de pagamento.`)
 }

 async function requestRide(){
   if(!origin||!destination||!selected){setMsg('Calcule e selecione uma categoria antes de pedir a corrida.');return}
   setBusy(true);setMsg('Procurando motoristas próximos...')
   const{data,error}=await supabase.rpc('create_passenger_ride',{p_origin_label:originLabel,p_origin_lat:origin.lat,p_origin_lng:origin.lng,p_destination_label:destinationLabel,p_destination_lat:destination.lat,p_destination_lng:destination.lng,p_category_id:selected,p_payment_method:payment})
   if(error){setBusy(false);setMsg(error.message);return}
   const rideId=String(data);const{data:r,error:re}=await supabase.from('rides').select('id,status,driver_id,estimated_fare,final_fare,origin_label,destination_label,estimated_arrival_min,cancellation_fee_applied,cancellation_fee_amount').eq('id',rideId).single();setBusy(false)
   if(re){setMsg(re.message);return}setCurrentRide(r as Ride);setMsg(payment==='card_machine'?'Corrida solicitada. O sistema buscará somente motoristas autorizados com maquininha.':'Corrida solicitada. O CLICK-GO está procurando motoristas aprovados e online.');onRideCreated?.()
 }
 async function cancelRide(){if(!currentRide)return;setBusy(true);const{data,error}=await supabase.rpc('cancel_passenger_ride',{p_ride_id:currentRide.id});setBusy(false);if(error){setMsg(error.message);return}setMsg(data?.cancellation_fee_applied?`Corrida cancelada. Taxa aplicada: ${money(data.cancellation_fee_amount)}.`:'Corrida cancelada sem taxa.');const{data:r}=await supabase.from('rides').select('id,status,driver_id,estimated_fare,final_fare,origin_label,destination_label,estimated_arrival_min,cancellation_fee_applied,cancellation_fee_amount').eq('id',currentRide.id).single();if(r)setCurrentRide(r as Ride);onRideCreated?.()}
 function resetRoute(){setDestination(null);setDestinationLabel('Destino selecionado no mapa');clearCalculated();setCurrentRide(null);setMsg('Pesquise ou clique no mapa para escolher um novo destino.')}
 const validOptions=options.filter(o=>o.category_id),selectedOption=validOptions.find(o=>o.category_id===selected),trackDriver=!!currentRide?.driver_id&&['accepted','driver_arriving','in_progress'].includes(currentRide.status),savedCards=methods.filter(m=>m.method_type==='card')
 const hasPaymentOption=!!paySettings&&(paySettings.cash_enabled||paySettings.pix_enabled||paySettings.card_machine_enabled||(paySettings.card_app_enabled&&savedCards.length>0))

 return <div style={{display:'grid',gap:14}}>
  <div><h2 style={{marginBottom:6}}>Solicitar corrida</h2><p className="subtitle">Pesquise origem e destino, use sua localização ou marque os pontos diretamente no mapa.</p></div>
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><div style={box}><AddressSearch title="Pesquisar origem" placeholder="Rua, número, bairro, cidade..." onSelect={chooseOrigin}/></div><div style={box}><AddressSearch title="Pesquisar destino" placeholder="Para onde você vai?" onSelect={chooseDestination}/></div></div>
  <div style={{...box,padding:10}}><div ref={mapEl} style={{height:400,borderRadius:14,overflow:'hidden'}}/></div>
  <div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button style={btn} onClick={useMyLocation} disabled={busy}>📍 Usar minha localização</button><button style={{...btn,background:'#222',color:'#fff'}} onClick={()=>{setOrigin(null);setDestination(null);setOriginLabel('Origem selecionada no mapa');setDestinationLabel('Destino selecionado no mapa');clearCalculated();setCurrentRide(null);setMsg('Clique no mapa para marcar a origem e depois o destino.')}}>Marcar tudo no mapa</button><button style={{...btn,background:'#222',color:'#fff'}} onClick={resetRoute}>Novo destino</button></div>
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}><label style={{display:'grid',gap:6}}>Origem selecionada<input style={input} value={originLabel} onChange={e=>setOriginLabel(e.target.value)}/></label><label style={{display:'grid',gap:6}}>Destino selecionado<input style={input} value={destinationLabel} onChange={e=>setDestinationLabel(e.target.value)}/></label></div>
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}><div style={box}><b>Origem</b><div style={{color:'#9ca3af',marginTop:6}}>{origin?`${origin.lat.toFixed(5)}, ${origin.lng.toFixed(5)}`:'Ainda não definida'}</div></div><div style={box}><b>Destino</b><div style={{color:'#9ca3af',marginTop:6}}>{destination?`${destination.lat.toFixed(5)}, ${destination.lng.toFixed(5)}`:'Ainda não definido'}</div></div></div>
  {!currentRide&&<button style={btn} onClick={calculate} disabled={busy||!origin||!destination}>{busy?'Processando...':'Calcular opções da corrida'}</button>}
  {options[0]&&<div style={box}><b>{options[0].city_name}/{options[0].state}</b><div style={{color:'#9ca3af',marginTop:6}}>Distância estimada: {Number(options[0].distance_km).toFixed(1)} km · Tempo estimado: {Math.ceil(Number(options[0].duration_min))} min</div></div>}
  {!!validOptions.length&&!currentRide&&<><div style={{display:'grid',gap:10}}>{validOptions.map(o=><button key={o.category_id!} onClick={()=>setSelected(o.category_id!)} style={{...box,textAlign:'left',cursor:'pointer',color:'#fff',outline:selected===o.category_id?'2px solid #ffd400':'none'}}><div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center'}}><div><b>{o.category_name}</b><div style={{color:'#9ca3af',fontSize:13,marginTop:5}}>{o.required_vehicle_type?`Veículo: ${o.required_vehicle_type}`:'Categoria disponível'}{Number(o.multiplier||1)>1?` · Dinâmica ${Number(o.multiplier).toFixed(2)}x`:''}</div></div><strong style={{fontSize:22,color:'#ffd400'}}>{money(o.fare)}</strong></div></button>)}</div>
   {paySettings&&<div style={box}><label style={{display:'grid',gap:6}}>Forma de pagamento<select value={payment} onChange={e=>setPayment(e.target.value)} style={input}>{paySettings.cash_enabled&&<option value="cash">Dinheiro</option>}{paySettings.pix_enabled&&<option value="pix">PIX</option>}{paySettings.card_app_enabled&&savedCards.map(m=><option key={m.id} value="card">{m.brand||'Cartão no app'} •••• {m.last4}</option>)}{paySettings.card_machine_enabled&&<option value="card_machine">Cartão na maquininha do motorista</option>}</select></label>{paySettings.card_app_enabled&&!savedCards.length&&<div style={{color:'#fbbf24',fontSize:13,marginTop:8}}>Cartão no aplicativo está liberado, mas você ainda não possui cartão cadastrado.</div>}{Number(paySettings.card_surcharge_percentage||0)>0&&payment==='card'&&<div style={{color:'#9ca3af',fontSize:13,marginTop:8}}>Acréscimo configurado para cartão: {Number(paySettings.card_surcharge_percentage).toFixed(2)}%.</div>}{payment==='card_machine'&&<div style={{color:'#9ca3af',fontSize:13,marginTop:8}}>A chamada será enviada somente a motoristas com maquininha autorizada pelo franqueado.</div>}</div>}
   <button style={btn} onClick={requestRide} disabled={busy||!selected||!hasPaymentOption}>{busy?'Solicitando...':`Pedir corrida${selectedOption?.fare?` · ${money(selectedOption.fare)}`:''}`}</button></>}
  {currentRide&&<div style={{...box,borderColor:'#665600'}}><div className="eyebrow">Corrida atual</div><h3 style={{margin:'6px 0'}}>{currentRide.status==='requested'||currentRide.status==='searching'?'Procurando motorista...':currentRide.status==='accepted'?'Motorista aceitou a corrida':currentRide.status==='driver_arriving'?'Motorista a caminho':currentRide.status==='in_progress'?'Corrida em andamento':currentRide.status==='completed'?'Corrida concluída':currentRide.status==='cancelled'?'Corrida cancelada':currentRide.status}</h3><div style={{color:'#d1d5db'}}>{currentRide.origin_label} → {currentRide.destination_label}</div><div style={{marginTop:8,fontWeight:800}}>{money(currentRide.final_fare??currentRide.estimated_fare)}</div>{trackDriver&&<PassengerDriverTracker rideId={currentRide.id} driverId={currentRide.driver_id!}/>} {['requested','searching','accepted','driver_arriving'].includes(currentRide.status)&&<button style={{...btn,background:'#3a1b1b',color:'#fff',marginTop:12}} onClick={cancelRide} disabled={busy}>Cancelar corrida</button>}</div>}
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b'}}>{msg}</div>}
 </div>
}
