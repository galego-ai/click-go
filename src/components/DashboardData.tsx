'use client'
import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type RideRow={city_id:string|null;franchise_id:string|null;final_fare:number|string|null}
type CityRow={id:string;name:string;state:string}
type FranchiseRow={id:string;trade_name:string|null}
type Row={city:string;franchise:string;rides:number;gross:number}
type Metrics={franchises:number;online:number;ongoing:number;revenue:number;pending:number;tickets:number}

export default function DashboardData(){
 const [k,setK]=useState<Metrics>({franchises:0,online:0,ongoing:0,revenue:0,pending:0,tickets:0})
 const [rows,setRows]=useState<Row[]>([])
 const [msg,setMsg]=useState('Carregando dados…')
 useEffect(()=>{void load()},[])
 async function count(table:string,filter?:[string,string]){let q=supabase.from(table).select('*',{count:'exact',head:true});if(filter)q=q.eq(filter[0],filter[1]);const {count,error}=await q;if(error)throw error;return count||0}
 async function load(){try{
   const start=new Date();start.setHours(0,0,0,0)
   const [franchises,online,ongoingRes,pendingPayments,pendingPayouts,tickets,rideRes,cityRes,frRes]=await Promise.all([
    count('franchises',['active','true']),
    count('drivers',['online','true']),
    supabase.from('rides').select('id',{count:'exact',head:true}).in('status',['accepted','driver_arriving','arrived','in_progress']),
    count('payments',['status','pending']),
    count('payouts',['status','requested']),
    count('support_tickets',['status','open']),
    supabase.from('rides').select('city_id,franchise_id,final_fare').eq('status','completed').gte('completed_at',start.toISOString()),
    supabase.from('cities').select('id,name,state'),
    supabase.from('franchises').select('id,trade_name')
   ])
   if(ongoingRes.error)throw ongoingRes.error;if(rideRes.error)throw rideRes.error;if(cityRes.error)throw cityRes.error;if(frRes.error)throw frRes.error
   const rides=(rideRes.data||[]) as RideRow[],cities=(cityRes.data||[]) as CityRow[],frs=(frRes.data||[]) as FranchiseRow[]
   const cityById=new Map(cities.map(c=>[c.id,c]));const frById=new Map(frs.map(f=>[f.id,f]));const grouped=new Map<string,Row>();let revenue=0
   for(const ride of rides){const fare=Number(ride.final_fare||0);revenue+=fare;const key=`${ride.city_id||''}|${ride.franchise_id||''}`;const city=ride.city_id?cityById.get(ride.city_id):undefined;const fr=ride.franchise_id?frById.get(ride.franchise_id):undefined;const row=grouped.get(key)||{city:city?`${city.name}/${city.state}`:'—',franchise:fr?.trade_name||'—',rides:0,gross:0};row.rides+=1;row.gross+=fare;grouped.set(key,row)}
   setK({franchises,online,ongoing:ongoingRes.count||0,revenue,pending:pendingPayments+pendingPayouts,tickets})
   setRows([...grouped.values()].sort((a,b)=>b.gross-a.gross).slice(0,5));setMsg('')
 }catch(e){setMsg(e instanceof Error?e.message:'Erro ao carregar dashboard')}}
 const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0)
 const primary=[['Faturamento hoje',brl(k.revenue)],['Franquias ativas',k.franchises],['Motoristas online',k.online],['Corridas agora',k.ongoing]]
 return <>
  {msg&&<p className="empty">{msg}</p>}
  <div className="grid dashboard-kpis">{primary.map(([label,value])=><div className="card dashboard-card" key={String(label)}><div className="label">{label}</div><div className="metric">{value}</div></div>)}</div>
  <div className="compact-stats" style={{gridTemplateColumns:'repeat(2,minmax(0,1fr))'}}><div className="compact-stat"><span>Pendências financeiras</span><strong>{k.pending}</strong></div><div className="compact-stat"><span>Chamados abertos</span><strong>{k.tickets}</strong></div></div>
  <div className="section dashboard-section"><div className="section-heading"><div><h2>Operação de hoje</h2><p className="subtitle">Resumo das cidades com corridas concluídas hoje.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Cidade</th><th>Franqueado</th><th>Corridas</th><th>Faturamento</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={4} className="empty">Ainda não há corridas concluídas hoje.</td></tr>:rows.map((r,i)=><tr key={`${r.city}-${i}`}><td>{r.city}</td><td>{r.franchise}</td><td>{r.rides}</td><td>{brl(r.gross)}</td></tr>)}</tbody></table></div></div>
 </>
}
