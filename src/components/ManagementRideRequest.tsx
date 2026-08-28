'use client'

import {useEffect,useMemo,useState} from 'react'
import AddressSearch from '@/components/AddressSearch'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Category={id:string;name:string;city_id:string;franchise_id:string|null}
type Passenger={id:string;full_name:string|null;phone:string|null;email:string|null}
type Driver={driver_id:string;full_name:string|null;rating:number;distance_to_pickup_km:number;speed_kmh:number;vehicle:string|null;plate:string|null;updated_at:string}
type Preview={franchise_id:string;city_id:string;category_id:string;payment_method:string;distance_km:number;duration_min:number;automatic_fare:number;dynamic_multiplier:number;max_pickup_radius_km:number;drivers:Driver[]}
type Point={label:string;lat:number;lng:number}

const card:React.CSSProperties={background:'#fff',border:'1px solid #e5e7eb',borderRadius:18,padding:18,color:'#111827'}
const input:React.CSSProperties={width:'100%',background:'#fff',color:'#111827',border:'1px solid #d1d5db',borderRadius:12,padding:'12px 13px',fontSize:14}
const button:React.CSSProperties={border:0,borderRadius:12,padding:'12px 15px',fontWeight:900,cursor:'pointer',background:'#ffd400',color:'#111'}
const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))

export default function ManagementRideRequest({mode}:{mode:'matrix'|'franchise'}){
 const[cities,setCities]=useState<City[]>([]),[categories,setCategories]=useState<Category[]>([]),[passengers,setPassengers]=useState<Passenger[]>([])
 const[lookup,setLookup]=useState(''),[passengerId,setPassengerId]=useState(''),[cityId,setCityId]=useState(''),[categoryId,setCategoryId]=useState('')
 const[origin,setOrigin]=useState<Point|null>(null),[destination,setDestination]=useState<Point|null>(null),[payment,setPayment]=useState('auto')
 const[preview,setPreview]=useState<Preview|null>(null),[driverId,setDriverId]=useState(''),[fare,setFare]=useState(''),[note,setNote]=useState('')
 const[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 const selectedPassenger=passengers.find(p=>p.id===passengerId)
 const visibleCategories=useMemo(()=>categories.filter(c=>!cityId||c.city_id===cityId),[categories,cityId])

 useEffect(()=>{void loadScope()},[])
 async function loadScope(){
  setBusy(true);setMsg('')
  try{
   const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Sessão não encontrada.')
   const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
   if(mode==='matrix'&&p?.role!=='super_admin')throw new Error('Acesso exclusivo da Matriz.')
   if(mode==='franchise'&&!['franchise_admin','operator'].includes(String(p?.role||'')))throw new Error('Acesso exclusivo da operação da franquia.')
   if(mode==='matrix'){
    const[c,cat]=await Promise.all([
     supabase.from('cities').select('id,name,state').eq('active',true).order('name'),
     supabase.from('ride_categories').select('id,name,city_id,franchise_id').eq('active',true).not('franchise_id','is',null).order('name')
    ]);if(c.error)throw c.error;if(cat.error)throw cat.error;setCities((c.data||[]) as City[]);setCategories((cat.data||[]) as Category[]);if(c.data?.[0])setCityId(c.data[0].id)
   }else{
    const fid=p?.franchise_id;if(!fid)throw new Error('Franquia não vinculada.')
    const[c,cat]=await Promise.all([
     supabase.from('franchise_cities').select('cities(id,name,state)').eq('franchise_id',fid),
     supabase.from('ride_categories').select('id,name,city_id,franchise_id').eq('franchise_id',fid).eq('active',true).order('name')
    ]);if(c.error)throw c.error;if(cat.error)throw cat.error;const rows=((c.data||[]) as any[]).map(x=>x.cities).filter(Boolean) as City[];setCities(rows);setCategories((cat.data||[]) as Category[]);if(rows[0])setCityId(rows[0].id)
   }
  }catch(e:any){setMsg(e.message||'Não foi possível carregar a operação.')}finally{setBusy(false)}
 }
 async function findPassenger(){
  if(lookup.trim().length<3){setMsg('Digite telefone, e-mail ou pelo menos 3 letras do nome.');return}
  setBusy(true);setMsg('Localizando passageiro...')
  const{data,error}=await supabase.rpc('management_find_passenger',{p_lookup:lookup.trim()});setBusy(false)
  if(error){setMsg(error.message);return}const list=(Array.isArray(data)?data:[]) as Passenger[];setPassengers(list);setPassengerId(list[0]?.id||'');setMsg(list.length?'Passageiro(s) localizado(s).':'Nenhum passageiro encontrado. Cadastre o passageiro antes de solicitar a corrida.')
 }
 async function calculate(){
  if(!cityId||!categoryId||!origin||!destination){setMsg('Selecione cidade, categoria, embarque e destino.');return}
  setBusy(true);setMsg('Calculando pela localização do embarque...')
  const{data,error}=await supabase.rpc('management_manual_ride_preview',{p_city_id:cityId,p_category_id:categoryId,p_origin_lat:origin.lat,p_origin_lng:origin.lng,p_destination_lat:destination.lat,p_destination_lng:destination.lng,p_payment_method:payment});setBusy(false)
  if(error){setMsg(error.message);return}const p=data as Preview;setPreview(p);setDriverId('');setFare(String(Number(p.automatic_fare||0).toFixed(2)));setMsg(`Valor calculado ${brl(p.automatic_fare)}. Motoristas estão ordenados pela distância ATÉ O EMBARQUE.`)
 }
 async function createRide(){
  if(!passengerId||!selectedPassenger||!cityId||!categoryId||!origin||!destination||!preview){setMsg('Complete o cálculo e escolha o passageiro antes de enviar.');return}
  const manualFare=Number(String(fare).replace(',','.'));if(!Number.isFinite(manualFare)||manualFare<=0){setMsg('Informe um valor válido para a corrida.');return}
  setBusy(true);setMsg('Criando corrida...')
  const{data,error}=await supabase.rpc('management_create_manual_ride_v2',{p_passenger_id:passengerId,p_passenger_lookup:lookup.trim(),p_city_id:cityId,p_category_id:categoryId,p_origin_label:origin.label,p_origin_lat:origin.lat,p_origin_lng:origin.lng,p_destination_label:destination.label,p_destination_lat:destination.lat,p_destination_lng:destination.lng,p_payment_method:payment,p_manual_fare:manualFare,p_requested_driver_id:driverId||null,p_note:note.trim()||null});setBusy(false)
  if(error){setMsg(error.message);return}
  const result=data as any;setMsg(driverId?`Corrida criada por ${brl(result.fare)} e enviada ao motorista selecionado.`:`Corrida criada por ${brl(result.fare)}. O sistema está chamando o motorista elegível mais próximo DO EMBARQUE.`);setPreview(null);setDriverId('');setNote('')
 }

 return <div style={{maxWidth:1180,margin:'0 auto',display:'grid',gap:16}}>
  <div><div className="eyebrow">{mode==='matrix'?'Matriz CLICK-GO':'Operação da franquia'}</div><h1 style={{margin:'5px 0'}}>Solicitar corrida pelo painel</h1><p style={{color:'#6b7280',margin:0}}>Escolha o embarque e o destino, edite o valor se necessário e selecione um motorista ou deixe em automático. <b>O automático sempre procura pelo ponto de embarque, nunca pela localização do administrador/franqueado.</b></p></div>
  {msg&&<div style={{...card,borderColor:'#e4c400',background:'#fff9d6'}}>{msg}</div>}
  <section style={card}><h2 style={{marginTop:0}}>1. Passageiro</h2><div style={{display:'grid',gridTemplateColumns:'minmax(0,1fr) auto',gap:8}}><input style={input} value={lookup} onChange={e=>setLookup(e.target.value)} placeholder="Telefone, e-mail ou nome do passageiro"/><button style={button} disabled={busy} onClick={()=>void findPassenger()}>Buscar passageiro</button></div>{passengers.length>0&&<select style={{...input,marginTop:10}} value={passengerId} onChange={e=>setPassengerId(e.target.value)}>{passengers.map(p=><option key={p.id} value={p.id}>{p.full_name||'Sem nome'} · {p.phone||p.email||'sem contato'}</option>)}</select>}</section>
  <section style={card}><h2 style={{marginTop:0}}>2. Operação e rota</h2><div style={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:12,marginBottom:14}}><label><b>Cidade</b><select style={{...input,marginTop:6}} value={cityId} onChange={e=>{setCityId(e.target.value);setCategoryId('');setPreview(null)}}><option value="">Selecione</option>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select></label><label><b>Categoria</b><select style={{...input,marginTop:6}} value={categoryId} onChange={e=>{setCategoryId(e.target.value);setPreview(null)}}><option value="">Selecione</option>{visibleCategories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label></div><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}><AddressSearch title="Local de embarque" placeholder="Digite o endereço do embarque" onSelect={r=>{setOrigin({label:r.label,lat:r.lat,lng:r.lng});setPreview(null)}}/><AddressSearch title="Destino" placeholder="Digite o endereço do destino" onSelect={r=>{setDestination({label:r.label,lat:r.lat,lng:r.lng});setPreview(null)}}/></div><div style={{display:'grid',gridTemplateColumns:'1fr auto',gap:10,alignItems:'end',marginTop:14}}><label><b>Pagamento</b><select style={{...input,marginTop:6}} value={payment} onChange={e=>setPayment(e.target.value)}><option value="auto">Automático conforme cidade</option><option value="cash">Dinheiro</option><option value="pix">PIX</option><option value="card">Cartão no app</option><option value="card_machine">Cartão/maquininha</option></select></label><button style={button} disabled={busy} onClick={()=>void calculate()}>Calcular e localizar motoristas</button></div></section>
  {preview&&<section style={card}><h2 style={{marginTop:0}}>3. Valor e motorista</h2><div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:10,marginBottom:14}}><Metric label="Valor automático" value={brl(preview.automatic_fare)}/><Metric label="Distância estimada" value={`${preview.distance_km} km`}/><Metric label="Tempo estimado" value={`${preview.duration_min} min`}/><Metric label="Dinâmica" value={`x${Number(preview.dynamic_multiplier||1).toFixed(2)}`}/></div><label><b>Valor da corrida — editável</b><input style={{...input,marginTop:6,maxWidth:260}} inputMode="decimal" value={fare} onChange={e=>setFare(e.target.value)}/></label><div style={{marginTop:16}}><b>Motorista</b><select style={{...input,marginTop:6}} value={driverId} onChange={e=>setDriverId(e.target.value)}><option value="">Automático — chamar o mais próximo do EMBARQUE</option>{(preview.drivers||[]).map(d=><option key={d.driver_id} value={d.driver_id}>{d.full_name||'Motorista'} · {Number(d.distance_to_pickup_km).toFixed(2)} km do embarque · {d.vehicle||''} {d.plate||''}</option>)}</select><small style={{display:'block',color:'#6b7280',marginTop:6}}>A lista usa a localização GPS do motorista comparada com as coordenadas do embarque.</small></div><label style={{display:'block',marginTop:14}}><b>Observação opcional</b><input style={{...input,marginTop:6}} value={note} onChange={e=>setNote(e.target.value)} placeholder="Ex.: passageiro solicitou corrida por telefone"/></label><button style={{...button,marginTop:16,fontSize:16}} disabled={busy||!passengerId} onClick={()=>void createRide()}>{busy?'Enviando...':driverId?'Criar e atribuir ao motorista':'Criar e buscar mais próximo do embarque'}</button></section>}
 </div>
}

function Metric({label,value}:{label:string;value:string}){return <div style={{background:'#f9fafb',border:'1px solid #e5e7eb',borderRadius:14,padding:12}}><small style={{color:'#6b7280'}}>{label}</small><strong style={{display:'block',fontSize:18,marginTop:4}}>{value}</strong></div>}
