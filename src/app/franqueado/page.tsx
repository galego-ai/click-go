'use client'

import Link from 'next/link'
import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Profile={id:string;full_name:string|null;franchise_id:string|null}
type CityJoin={cities:{name:string;state:string}[]}
type RideFare={final_fare:number|string|null}
type Summary={online:number;activeRides:number;pendingDrivers:number;todayRevenue:number}

const brl=(value:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value||0)

export default function FranchiseHome(){
 const [me,setMe]=useState<Profile|null>(null)
 const [cities,setCities]=useState<string[]>([])
 const [summary,setSummary]=useState<Summary>({online:0,activeRides:0,pendingDrivers:0,todayRevenue:0})
 const [loading,setLoading]=useState(true)
 const [error,setError]=useState('')
 useEffect(()=>{void load()},[])
 async function load(){
  setLoading(true);setError('')
  try{
   const {data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Sessão não encontrada.')
   const {data:profile,error:profileError}=await supabase.from('profiles').select('id,full_name,franchise_id').eq('id',user.id).single();if(profileError)throw profileError
   const current=profile as Profile;setMe(current);if(!current.franchise_id)throw new Error('Franquia não vinculada a este acesso.')
   const start=new Date();start.setHours(0,0,0,0)
   const [cityRes,onlineRes,activeRes,pendingRes,revenueRes]=await Promise.all([
    supabase.from('franchise_cities').select('cities(name,state)').eq('franchise_id',current.franchise_id),
    supabase.from('drivers').select('id',{count:'exact',head:true}).eq('franchise_id',current.franchise_id).eq('online',true),
    supabase.from('rides').select('id',{count:'exact',head:true}).eq('franchise_id',current.franchise_id).in('status',['accepted','driver_arriving','arrived','in_progress']),
    supabase.from('drivers').select('id',{count:'exact',head:true}).eq('franchise_id',current.franchise_id).eq('status','pending'),
    supabase.from('rides').select('final_fare').eq('franchise_id',current.franchise_id).eq('status','completed').gte('completed_at',start.toISOString())
   ])
   if(cityRes.error)throw cityRes.error;if(onlineRes.error)throw onlineRes.error;if(activeRes.error)throw activeRes.error;if(pendingRes.error)throw pendingRes.error;if(revenueRes.error)throw revenueRes.error
   const cityNames=((cityRes.data||[]) as CityJoin[]).map(row=>row.cities?.[0]).filter((city):city is {name:string;state:string}=>Boolean(city)).map(city=>`${city.name}/${city.state}`)
   const todayRevenue=((revenueRes.data||[]) as RideFare[]).reduce((sum,row)=>sum+Number(row.final_fare||0),0)
   setCities(cityNames);setSummary({online:onlineRes.count||0,activeRides:activeRes.count||0,pendingDrivers:pendingRes.count||0,todayRevenue})
  }catch(err){setError(err instanceof Error?err.message:'Erro ao carregar o painel regional.')}finally{setLoading(false)}
 }
 const cards=[{label:'Motoristas online',value:String(summary.online),hint:'disponíveis agora'},{label:'Corridas em andamento',value:String(summary.activeRides),hint:'operação ao vivo'},{label:'Aguardando aprovação',value:String(summary.pendingDrivers),hint:'cadastros de motoristas'},{label:'Faturamento hoje',value:brl(summary.todayRevenue),hint:'corridas concluídas'}]
 const actions=[['/franqueado/operacao','Operação','Acompanhar corridas e motoristas'],['/franqueado/cadastros','Motoristas','Aprovar e gerenciar cadastros'],['/franqueado/categorias','Tarifas','Categorias, km, minuto e tarifa mínima'],['/franqueado/mapa','Mapa ao vivo','Ver motoristas da sua região'],['/franqueado/carteiras','Carteiras','Saldo, recargas e limite para dinheiro'],['/franqueado/pagamentos','Financeiro','Pagamentos e movimentações']] as const
 return <div className="regional-home"><div className="regional-heading"><div><div className="eyebrow">Operação regional</div><h1>{cities[0]||'CLICK-GO Regional'}</h1><p>{me?.full_name||'Administrador'}{cities.length>1?` · ${cities.join(' · ')}`:''}</p></div><button className="button secondary" onClick={()=>void load()} disabled={loading}>{loading?'Atualizando…':'Atualizar'}</button></div>{error&&<div className="regional-alert">{error}</div>}<div className="regional-kpis">{cards.map(card=><div className="regional-kpi" key={card.label}><span>{card.label}</span><strong>{loading?'—':card.value}</strong><small>{card.hint}</small></div>)}</div><section className="regional-actions"><div className="section-heading"><div><h2>Acesso rápido</h2><p className="subtitle">As funções mais usadas no dia a dia.</p></div></div><div className="regional-action-grid">{actions.map(([href,title,desc])=><Link href={href} key={href} className="regional-action"><strong>{title}</strong><span>{desc}</span><b>→</b></Link>)}</div></section></div>
}
