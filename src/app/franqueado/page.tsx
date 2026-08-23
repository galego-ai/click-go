'use client'

import Link from 'next/link'
import {useEffect,useState} from 'react'
import {Activity,ArrowRight,CarFront,CheckCircle2,FileClock,Map,MapPin,Percent,RadioTower,RefreshCw,Route,Users,WalletCards} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type Profile={id:string;full_name:string|null;role:string;franchise_id:string|null}
type City={id:string;name:string;state:string}
type Driver={id:string;status:string;online:boolean}
type Ride={id:string;status:string;estimated_fare:number|string|null;final_fare:number|string|null;requested_at:string}
type Wallet={driver_id:string;balance:number|string}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})

export default function FranchiseHome(){
 const[me,setMe]=useState<Profile|null>(null),[cities,setCities]=useState<City[]>([]),[drivers,setDrivers]=useState<Driver[]>([]),[rides,setRides]=useState<Ride[]>([]),[passengers,setPassengers]=useState(0),[wallets,setWallets]=useState<Wallet[]>([]),[pendingDocs,setPendingDocs]=useState(0),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{load()},[])
 async function load(){setBusy(true);setMsg('');try{const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login como franqueado.');const{data:p,error:pe}=await supabase.from('profiles').select('id,full_name,role,franchise_id').eq('id',user.id).single();if(pe)throw pe;if(!p||p.role!=='franchise_admin'||!p.franchise_id)throw new Error('Acesso exclusivo do franqueado.');setMe(p as Profile);const[{data:fc,error:fce},{data:d,error:de},{data:r,error:re},{data:w,error:we},{count:pc,error:pce},{count:dc,error:dce}]=await Promise.all([supabase.from('franchise_cities').select('cities(id,name,state)').eq('franchise_id',p.franchise_id),supabase.from('drivers').select('id,status,online').eq('franchise_id',p.franchise_id),supabase.from('rides').select('id,status,estimated_fare,final_fare,requested_at').eq('franchise_id',p.franchise_id).order('requested_at',{ascending:false}).limit(100),supabase.from('driver_operational_wallets').select('driver_id,balance'),supabase.from('rides').select('passenger_id',{count:'exact',head:true}).eq('franchise_id',p.franchise_id),supabase.from('driver_documents').select('id',{count:'exact',head:true}).eq('status','pending')]);if(fce)throw fce;if(de)throw de;if(re)throw re;if(we)throw we;if(pce)throw pce;if(dce)throw dce;setCities((fc||[]).map((x:any)=>x.cities).filter(Boolean) as City[]);setDrivers((d||[]) as Driver[]);setRides((r||[]) as Ride[]);setWallets((w||[]) as Wallet[]);setPassengers(pc||0);setPendingDocs(dc||0)}catch(e:any){setMsg(e.message||'Não foi possível carregar sua operação.')}finally{setBusy(false)}}
 const completed=rides.filter(r=>r.status==='completed'),ongoing=rides.filter(r=>['accepted','driver_arriving','in_progress','searching','requested'].includes(r.status)),revenue=completed.reduce((s,r)=>s+Number(r.final_fare??r.estimated_fare??0),0),online=drivers.filter(d=>d.online&&d.status==='approved').length,pending=drivers.filter(d=>d.status==='pending').length,lowWallets=wallets.filter(w=>Number(w.balance)<5).length
 const quick=[
  {href:'/franqueado/operacao',title:'Central operacional',desc:'Corridas, chamadas e motoristas em tempo real.',icon:RadioTower},
  {href:'/franqueado/documentos',title:'Aprovações',desc:'Confira documentos e libere novos motoristas.',icon:CheckCircle2,badge:pendingDocs+pending},
  {href:'/franqueado/mapa',title:'Mapa da cidade',desc:'Veja motoristas online e a área de operação.',icon:Map},
  {href:'/franqueado/taxas',title:'Taxas R$ / %',desc:'Configure cobrança por motorista sem misturar com tarifas.',icon:Percent},
  {href:'/franqueado/carteiras',title:'Carteiras',desc:'Saldo operacional, recargas e movimentações.',icon:WalletCards,badge:lowWallets},
  {href:'/franqueado/categorias',title:'Categorias e preços',desc:'Preço base, km, minuto, mínima e dinâmica.',icon:CarFront},
 ]
 return <main style={{minHeight:'calc(100vh - 66px)',background:'#09090b',color:'#fff',padding:'26px 28px 36px'}}><div style={{maxWidth:1400,margin:'0 auto'}}>
  <div className="pro-page-head"><div><div className="eyebrow">Sua operação</div><h1>Visão geral da franquia</h1><p className="subtitle">{me?.full_name||'Franqueado'} · {cities.length?cities.map(c=>`${c.name}/${c.state}`).join(' · '):'Nenhuma cidade vinculada'}</p></div><div className="pro-page-actions"><span className="pro-chip"><span/>Sistema operacional</span><button className="button secondary" onClick={load} disabled={busy}><RefreshCw size={15} style={{verticalAlign:'middle',marginRight:6}}/>{busy?'Atualizando':'Atualizar'}</button></div></div>
  {msg&&<div className="card" style={{borderColor:'#665600',color:'#ffe66b',marginBottom:15}}>{msg}</div>}

  <div className="grid dashboard-kpis">
   <div className="card dashboard-card"><div className="label">Faturamento concluído</div><div className="metric">{money(revenue)}</div><div className="kpi-good" style={{fontSize:12,marginTop:5}}>{completed.length} corridas concluídas</div></div>
   <div className="card dashboard-card"><div className="label">Motoristas online</div><div className="metric">{online}</div><div style={{fontSize:12,color:'#9a9aa2',marginTop:5}}>de {drivers.filter(d=>d.status==='approved').length} aprovados</div></div>
   <div className="card dashboard-card"><div className="label">Corridas agora</div><div className="metric">{ongoing.length}</div><div style={{fontSize:12,color:'#9a9aa2',marginTop:5}}>em busca, aceitas ou em andamento</div></div>
   <div className="card dashboard-card"><div className="label">Cadastros pendentes</div><div className="metric">{pending+pendingDocs}</div><div className={pending+pendingDocs?'kpi-warn':'kpi-good'} style={{fontSize:12,marginTop:5}}>motoristas/documentos para analisar</div></div>
   <div className="card dashboard-card"><div className="label">Passageiros atendidos</div><div className="metric">{passengers}</div><div style={{fontSize:12,color:'#9a9aa2',marginTop:5}}>vínculos de corridas da franquia</div></div>
   <div className="card dashboard-card"><div className="label">Carteiras com saldo baixo</div><div className="metric">{lowWallets}</div><div className={lowWallets?'kpi-warn':'kpi-good'} style={{fontSize:12,marginTop:5}}>abaixo de R$ 5,00</div></div>
  </div>

  <section className="section"><div className="section-heading"><div><h2>O que precisa da sua atenção</h2><p className="subtitle">Prioridades da operação, sem misturar configurações avançadas.</p></div></div><div className="grid-3"><Link href="/franqueado/documentos" className="card" style={{display:'flex',gap:13,alignItems:'center'}}><div className="module-number"><FileClock size={17}/></div><div><b>{pendingDocs+pending} aprovações pendentes</b><div className="label" style={{marginTop:3}}>Documentos e cadastros aguardando análise</div></div><ArrowRight size={17} style={{marginLeft:'auto'}}/></Link><Link href="/franqueado/operacao" className="card" style={{display:'flex',gap:13,alignItems:'center'}}><div className="module-number"><Activity size={17}/></div><div><b>{ongoing.length} corridas em operação</b><div className="label" style={{marginTop:3}}>Acompanhar chamadas e andamento</div></div><ArrowRight size={17} style={{marginLeft:'auto'}}/></Link><Link href="/franqueado/carteiras" className="card" style={{display:'flex',gap:13,alignItems:'center'}}><div className="module-number"><WalletCards size={17}/></div><div><b>{lowWallets} saldos baixos</b><div className="label" style={{marginTop:3}}>Motoristas próximos de perder liberação</div></div><ArrowRight size={17} style={{marginLeft:'auto'}}/></Link></div></section>

  <section className="section"><div className="section-heading"><div><h2>Atalhos de gestão</h2><p className="subtitle">Cada assunto em seu lugar. Abra somente a área que precisa usar.</p></div></div><div className="grid-3">{quick.map(({href,title,desc,icon:Icon,badge})=><Link href={href} className="card" key={href} style={{display:'flex',gap:13,alignItems:'flex-start',minHeight:110}}><div style={{width:42,height:42,borderRadius:13,background:'#242112',color:'#ffd400',display:'grid',placeItems:'center',flex:'0 0 auto'}}><Icon size={20}/></div><div style={{minWidth:0}}><div style={{display:'flex',alignItems:'center',gap:7}}><b>{title}</b>{typeof badge==='number'&&badge>0&&<span className="pill yellow">{badge}</span>}</div><p className="label" style={{margin:'6px 0 0',lineHeight:1.45}}>{desc}</p></div><ArrowRight size={16} style={{marginLeft:'auto',color:'#777'}}/></Link>)}</div></section>

  <section className="section"><div className="section-heading"><div><h2>Últimas corridas</h2><p className="subtitle">As atividades mais recentes da sua franquia.</p></div><Link href="/franqueado/operacao" className="button secondary">Ver operação</Link></div><div className="table-wrap"><table className="table"><thead><tr><th>Quando</th><th>Status</th><th>Valor</th></tr></thead><tbody>{rides.slice(0,8).map(r=><tr key={r.id}><td>{new Date(r.requested_at).toLocaleString('pt-BR')}</td><td><span className={`pill ${r.status==='completed'?'green':r.status==='cancelled'?'red':'yellow'}`}>{r.status}</span></td><td>{money(r.final_fare??r.estimated_fare)}</td></tr>)}{!rides.length&&<tr><td colSpan={3} className="empty">Nenhuma corrida registrada ainda.</td></tr>}</tbody></table></div></section>
  <div style={{display:'flex',gap:8,alignItems:'center',color:'#777',fontSize:11,marginTop:18}}><MapPin size={14}/> A Matriz continua podendo sobrescrever e bloquear regras da franquia.</div>
 </div></main>
}
