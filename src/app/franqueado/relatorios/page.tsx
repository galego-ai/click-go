'use client'

import {useEffect,useMemo,useState} from 'react'
import {supabase} from '@/lib/supabase'

type Summary={completed:number;cancelled:number;drivers:number;online:number;revenue:number}
type ManagedDriver={id:string;full_name:string|null;online:boolean;status:string}
type Person={id:string;full_name:string|null}
type City={id:string;name:string;state:string}
type Ride={id:string;passenger_id:string;driver_id:string|null;city_id:string|null;status:string;final_fare:number|string|null;estimated_fare:number|string|null;requested_at:string;completed_at:string|null}

const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0)
const statusLabel:Record<string,string>={requested:'Solicitada',searching:'Procurando motorista',accepted:'Aceita',driver_arriving:'Motorista a caminho',arrived:'Motorista chegou',in_progress:'Em andamento',completed:'Concluída',cancelled:'Cancelada'}

export default function FranchiseReportsPage(){
 const[summary,setSummary]=useState<Summary>({completed:0,cancelled:0,drivers:0,online:0,revenue:0}),[rides,setRides]=useState<Ride[]>([]),[drivers,setDrivers]=useState<ManagedDriver[]>([]),[people,setPeople]=useState<Person[]>([]),[cities,setCities]=useState<City[]>([]),[msg,setMsg]=useState('Carregando relatório...')
 useEffect(()=>{void load()},[])
 async function load(){
  setMsg('Carregando relatório...')
  const{data:{user}}=await supabase.auth.getUser();if(!user){setMsg('Sessão não encontrada.');return}
  const{data:p,error:pe}=await supabase.from('profiles').select('franchise_id').eq('id',user.id).single();if(pe||!p?.franchise_id){setMsg(pe?.message||'Franquia não vinculada.');return}
  const start=new Date();start.setDate(1);start.setHours(0,0,0,0)
  const[rideRes,driverRes]=await Promise.all([
   supabase.from('rides').select('id,passenger_id,driver_id,city_id,status,final_fare,estimated_fare,requested_at,completed_at').eq('franchise_id',p.franchise_id).gte('requested_at',start.toISOString()).order('requested_at',{ascending:false}).limit(250),
   supabase.rpc('franchise_list_driver_management')
  ])
  if(rideRes.error){setMsg(rideRes.error.message);return}if(driverRes.error){setMsg(driverRes.error.message);return}
  const rideList=(rideRes.data||[]) as Ride[];const driverList=(Array.isArray(driverRes.data)?driverRes.data:[]) as ManagedDriver[]
  const personIds=Array.from(new Set(rideList.flatMap(r=>[r.passenger_id,r.driver_id].filter((x):x is string=>Boolean(x)))))
  const cityIds=Array.from(new Set(rideList.map(r=>r.city_id).filter((x):x is string=>Boolean(x))))
  const [personRes,cityRes]=await Promise.all([
   personIds.length?supabase.from('profiles').select('id,full_name').in('id',personIds):Promise.resolve({data:[] as Person[],error:null}),
   cityIds.length?supabase.from('cities').select('id,name,state').in('id',cityIds):Promise.resolve({data:[] as City[],error:null})
  ])
  if(personRes.error){setMsg(personRes.error.message);return}if(cityRes.error){setMsg(cityRes.error.message);return}
  const completed=rideList.filter(r=>r.status==='completed');const cancelled=rideList.filter(r=>r.status==='cancelled');const revenue=completed.reduce((s,r)=>s+Number(r.final_fare??r.estimated_fare??0),0)
  setRides(rideList);setDrivers(driverList);setPeople((personRes.data||[]) as Person[]);setCities((cityRes.data||[]) as City[]);setSummary({completed:completed.length,cancelled:cancelled.length,drivers:driverList.length,online:driverList.filter(d=>d.online&&d.status==='approved').length,revenue});setMsg('')
 }
 const peopleMap=useMemo(()=>new Map(people.map(p=>[p.id,p.full_name?.trim()||'Nome não informado'])),[people])
 const driverMap=useMemo(()=>new Map(drivers.map(d=>[d.id,d.full_name?.trim()||peopleMap.get(d.id)||'Motorista sem nome'])),[drivers,peopleMap])
 const cityMap=useMemo(()=>new Map(cities.map(c=>[c.id,`${c.name}/${c.state}`])),[cities])
 const cards=[['Corridas concluídas',summary.completed.toLocaleString('pt-BR'),'mês atual'],['Cancelamentos',summary.cancelled.toLocaleString('pt-BR'),'mês atual'],['Motoristas cadastrados',summary.drivers.toLocaleString('pt-BR'),`${summary.online} online agora`],['Faturamento em corridas',brl(summary.revenue),'mês atual']] as const
 return <div className="regional-home"><div className="regional-heading"><div><div className="eyebrow">Minha operação</div><h1>Relatórios</h1><p>Indicadores e corridas da sua franquia com nomes legíveis, sem códigos técnicos.</p></div><button className="button secondary" onClick={()=>void load()}>Atualizar</button></div>{msg&&<div className="regional-alert">{msg}</div>}<div className="regional-kpis">{cards.map(([label,value,hint])=><div className="regional-kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>)}</div><section className="card" style={{marginTop:18}}><div className="section-heading"><div><h2>Corridas do mês</h2><p className="subtitle">Passageiros, motoristas e cidades aparecem pelo nome.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Data</th><th>Passageiro</th><th>Motorista</th><th>Cidade</th><th>Status</th><th>Valor</th></tr></thead><tbody>{rides.length===0?<tr><td colSpan={6} className="empty">Nenhuma corrida registrada neste mês.</td></tr>:rides.map(r=><tr key={r.id}><td>{new Date(r.requested_at).toLocaleString('pt-BR')}</td><td><strong>{peopleMap.get(r.passenger_id)||'Passageiro sem nome'}</strong></td><td>{r.driver_id?<strong>{driverMap.get(r.driver_id)||peopleMap.get(r.driver_id)||'Motorista sem nome'}</strong>:<span className="empty">Aguardando motorista</span>}</td><td>{r.city_id?cityMap.get(r.city_id)||'Cidade não identificada':'—'}</td><td>{statusLabel[r.status]||r.status}</td><td>{brl(Number(r.final_fare??r.estimated_fare??0))}</td></tr>)}</tbody></table></div></section></div>
}
