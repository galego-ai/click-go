'use client'

import {useEffect,useMemo,useState} from 'react'
import {Activity, BadgeCheck, CarFront, Gauge, Megaphone, RefreshCw, Settings2, ShieldCheck, Smartphone, Tags, UsersRound, WalletCards} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type Network={id:string;trade_name:string;license_status:string;config_version:number;config_changed_at:string|null;config_changed_source:string|null;rides_month:number;drivers_online:number;enabled_modules:Record<string,boolean>|null}
type Event={id:number;franchise_id:string|null;version:number;source:string;entity:string;action:string;created_at:string}
const when=(v:string|null)=>v?new Date(v).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—'
const source:Record<string,string>={matrix:'Matriz',franchise:'Franqueado',staff:'Equipe',driver_app:'Motorista',passenger_app:'Passageiro',system:'Sistema'}
const entity:Record<string,string>={ride_categories:'Tarifas e categorias',franchise_settings:'Configurações',advertising_banners:'Anúncios',promotions:'Promoções',coupons:'Cupons',franchise_business_hours:'Horários',franchise_city_payment_settings:'Pagamentos',franchise_operational_wallet_settings:'Carteiras'}

export default function EcosystemPage(){
 const[network,setNetwork]=useState<Network[]>([]);const[events,setEvents]=useState<Event[]>([]);const[loading,setLoading]=useState(true);const[msg,setMsg]=useState('')
 async function load(){setLoading(true);const[n,e]=await Promise.all([supabase.rpc('super_admin_franchise_network_snapshot'),supabase.from('configuration_events').select('id,franchise_id,version,source,entity,action,created_at').order('created_at',{ascending:false}).limit(30)]);if(n.error)setMsg(n.error.message);else setNetwork((Array.isArray(n.data)?n.data:[]) as Network[]);if(e.error)setMsg(e.error.message);else setEvents((e.data||[]) as Event[]);setLoading(false)}
 useEffect(()=>{void load();const c=supabase.channel('clickgo-ecosystem-sync').on('postgres_changes',{event:'*',schema:'public',table:'configuration_events'},()=>void load()).on('postgres_changes',{event:'*',schema:'public',table:'rides'},()=>void load()).subscribe();return()=>{void supabase.removeChannel(c)}},[])
 const healthy=useMemo(()=>network.filter(x=>x.license_status==='active').length,[network]);const latest=events[0]
 const surfaces=[
  {title:'Matriz CLICK-GO',icon:<ShieldCheck/>,text:'Planos, licenças, territórios, regras globais e sobrescrita de configurações locais.',status:'Controle mestre'},
  {title:'Painel do Franqueado',icon:<Gauge/>,text:'Tarifas, motoristas, pagamentos, promoções, anúncios, suporte e operação da própria região.',status:'Escopo regional'},
  {title:'App Passageiro',icon:<Smartphone/>,text:'Categorias, preços, formas de pagamento, anúncios e regras ativas recebidas da mesma configuração central.',status:'Configuração sincronizada'},
  {title:'App Motorista',icon:<CarFront/>,text:'Chamados, categorias, regras operacionais e estado da licença ligados à operação regional.',status:'Configuração sincronizada'},
 ]
 return <>
  <div className="topbar compact-topbar"><div><div className="eyebrow">CLICK-GO Gestão · Tecnologia</div><h1 className="title">Apps e sincronização</h1><p className="subtitle">Uma única fonte de verdade para Matriz, Franqueado, Passageiro e Motorista. Alterou no painel, a configuração ganha nova versão; a atividade dos apps volta para os painéis.</p></div><button className="button secondary" onClick={()=>void load()} disabled={loading}><RefreshCw size={16}/>{loading?'Atualizando':'Atualizar status'}</button></div>
  {msg&&<div className="license-message">{msg}</div>}
  <div className="sync-overview-grid">
   <div className="card sync-health"><span className="command-kicker"><Activity size={14}/> Rede em tempo real</span><strong>{healthy}/{network.length}</strong><p>operações com licença ativa</p></div>
   <div className="card sync-health"><span className="command-kicker"><Settings2 size={14}/> Versão mais alta</span><strong>{network.reduce((m,x)=>Math.max(m,Number(x.config_version||0)),0)}</strong><p>controle de configuração</p></div>
   <div className="card sync-health"><span className="command-kicker"><CarFront size={14}/> Motoristas online</span><strong>{network.reduce((s,x)=>s+Number(x.drivers_online||0),0)}</strong><p>atividade atual da rede</p></div>
   <div className="card sync-health"><span className="command-kicker"><BadgeCheck size={14}/> Último evento</span><strong className="sync-small-value">{latest?entity[latest.entity]||latest.entity:'—'}</strong><p>{latest?`${source[latest.source]||latest.source} · ${when(latest.created_at)}`:'sem alterações recentes'}</p></div>
  </div>
  <section className="section"><div className="section-heading"><div><h2>Um ecossistema, quatro superfícies</h2><p className="subtitle">Os recursos são diferentes por perfil, mas os dados e regras vêm do mesmo núcleo.</p></div></div><div className="ecosystem-surfaces">{surfaces.map(s=><div className="card ecosystem-surface" key={s.title}><span className="ecosystem-icon">{s.icon}</span><div><strong>{s.title}</strong><p>{s.text}</p><small><BadgeCheck size={12}/>{s.status}</small></div></div>)}</div></section>
  <div className="grid-2 section">
   <div className="card"><div className="card-head-row"><div><div className="eyebrow">Configuração compartilhada</div><h2>O que sincroniza</h2></div><RefreshCw size={20}/></div><div className="sync-module-list"><div><Tags/><span><strong>Tarifas e categorias</strong><small>Preço base, km, minuto, mínimo, cancelamento, espera e tipo de veículo.</small></span></div><div><WalletCards/><span><strong>Pagamentos</strong><small>Dinheiro, PIX, cartão no app, maquininha, taxas e regras de carteira.</small></span></div><div><Megaphone/><span><strong>Marketing</strong><small>Anúncios, cupons, promoções e campanhas regionais.</small></span></div><div><UsersRound/><span><strong>Operação</strong><small>Motoristas, corridas, localização, bloqueios e aprovações retornam para o painel.</small></span></div></div></div>
   <div className="card"><div className="card-head-row"><div><div className="eyebrow">Versões por operação</div><h2>Estado da rede</h2></div><Settings2 size={20}/></div><div className="sync-franchise-list">{network.length===0?<p className="empty">Nenhuma operação.</p>:network.map(f=><div key={f.id}><span className={'event-dot '+(f.license_status==='active'?'healthy':'')}/><div><strong>{f.trade_name}</strong><small>Licença {f.license_status} · {f.rides_month||0} corridas no mês</small></div><b>v{f.config_version||0}</b><time>{when(f.config_changed_at)}</time></div>)}</div></div>
  </div>
  <section className="section"><div className="section-heading"><div><h2>Histórico de sincronização</h2><p className="subtitle">Mudanças administrativas ficam versionadas e auditáveis.</p></div></div><div className="card"><div className="event-list sync-event-full">{events.length===0?<p className="empty">Nenhum evento de configuração ainda.</p>:events.map(ev=>{const f=network.find(x=>x.id===ev.franchise_id);return <div key={ev.id}><span className="event-dot"/><div><strong>{entity[ev.entity]||ev.entity}</strong><small>{f?.trade_name||'Configuração global'} · {source[ev.source]||ev.source} · {ev.action}</small></div><b>v{ev.version}</b><time>{when(ev.created_at)}</time></div>})}</div></div></section>
 </>
}
