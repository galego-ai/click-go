'use client'
import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Row={city:string;franchise:string;rides:number;gross:number}
export default function DashboardData(){
 const [k,setK]=useState<Record<string,number>>({});const [rows,setRows]=useState<Row[]>([]);const [msg,setMsg]=useState('Carregando dados...')
 useEffect(()=>{load()},[])
 async function count(table:string,filter?:[string,string]){let q=supabase.from(table).select('*',{count:'exact',head:true});if(filter)q=q.eq(filter[0],filter[1]);const {count}=await q;return count||0}
 async function load(){try{
   const [cities,franchises,passengers,drivers,online,ongoing,completed,cancelled,pendingPayments,pendingPayouts,tickets]=await Promise.all([
    count('cities'),count('franchises',['active','true']),count('profiles',['role','passenger']),count('drivers'),count('drivers',['online','true']),count('rides',['status','in_progress']),count('rides',['status','completed']),count('rides',['status','cancelled']),count('payments',['status','pending']),count('payouts',['status','requested']),count('support_tickets',['status','open'])
   ])
   const {data:rideData,error}=await supabase.from('rides').select('city_id,franchise_id,final_fare').eq('status','completed');if(error)throw error
   const {data:cityData}=await supabase.from('cities').select('id,name,state');const {data:frData}=await supabase.from('franchises').select('id,trade_name')
   const map=new Map<string,Row>();let revenue=0;(rideData||[]).forEach((r:any)=>{const fare=Number(r.final_fare||0);revenue+=fare;const key=`${r.city_id||''}|${r.franchise_id||''}`;const city=cityData?.find((c:any)=>c.id===r.city_id);const fr=frData?.find((f:any)=>f.id===r.franchise_id);const old=map.get(key)||{city:city?`${city.name}/${city.state}`:'—',franchise:fr?.trade_name||'—',rides:0,gross:0};old.rides++;old.gross+=fare;map.set(key,old)})
   setK({cities,franchises,passengers,drivers,online,ongoing,completed,cancelled,pendingPayments,pendingPayouts,tickets,revenue});setRows([...map.values()].sort((a,b)=>b.gross-a.gross).slice(0,5));setMsg('')
 }catch(e){setMsg(e instanceof Error?e.message:'Erro ao carregar dashboard')}}
 const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0)
 const primary=[
  ['Faturamento geral',brl(k.revenue)],
  ['Franquias ativas',k.franchises||0],
  ['Motoristas online',k.online||0],
  ['Corridas agora',k.ongoing||0],
  ['Pendências financeiras',(k.pendingPayments||0)+(k.pendingPayouts||0)],
  ['Chamados abertos',k.tickets||0],
 ]
 const secondary=[['Cidades',k.cities||0],['Passageiros',k.passengers||0],['Motoristas',k.drivers||0],['Concluídas',k.completed||0],['Canceladas',k.cancelled||0]]
 return <>
  {msg&&<p className="empty">{msg}</p>}
  <div className="grid dashboard-kpis">{primary.map(([label,value])=><div className="card dashboard-card" key={String(label)}><div className="label">{label}</div><div className="metric">{value}</div></div>)}</div>
  <div className="compact-stats">{secondary.map(([label,value])=><div className="compact-stat" key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div>
  <div className="section dashboard-section"><div className="section-heading"><div><h2>Resumo por cidade</h2><p className="subtitle">5 maiores operações por faturamento concluído.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Cidade</th><th>Franqueado</th><th>Corridas</th><th>Faturamento</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={4} className="empty">Sem corridas concluídas.</td></tr>:rows.map((r,i)=><tr key={i}><td>{r.city}</td><td>{r.franchise}</td><td>{r.rides}</td><td>{brl(r.gross)}</td></tr>)}</tbody></table></div></div>
 </>
}
