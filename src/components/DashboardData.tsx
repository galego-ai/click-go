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
   setK({cities,franchises,passengers,drivers,online,ongoing,completed,cancelled,pendingPayments,pendingPayouts,tickets,revenue});setRows([...map.values()]);setMsg('')
 }catch(e){setMsg(e instanceof Error?e.message:'Erro ao carregar dashboard')}}
 const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0)
 const items=[['Faturamento geral',brl(k.revenue)],['Cidades',k.cities||0],['Franquias',k.franchises||0],['Passageiros',k.passengers||0],['Motoristas',k.drivers||0],['Motoristas online',k.online||0],['Corridas em andamento',k.ongoing||0],['Corridas concluídas',k.completed||0],['Corridas canceladas',k.cancelled||0],['Pagamentos pendentes',k.pendingPayments||0],['Repasses pendentes',k.pendingPayouts||0],['Chamados abertos',k.tickets||0]]
 return <>{msg&&<p className="empty">{msg}</p>}<div className="grid">{items.map(([label,value])=><div className="card" key={String(label)}><div className="label">{label}</div><div className="metric">{value}</div></div>)}</div><div className="section"><h2>Faturamento por cidade e franqueado</h2><div className="table-wrap"><table className="table"><thead><tr><th>Cidade</th><th>Franqueado</th><th>Corridas</th><th>Faturamento</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={4} className="empty">Sem corridas concluídas.</td></tr>:rows.map((r,i)=><tr key={i}><td>{r.city}</td><td>{r.franchise}</td><td>{r.rides}</td><td>{brl(r.gross)}</td></tr>)}</tbody></table></div></div></>
}
