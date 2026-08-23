'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Building2, CarFront, Route, WalletCards, Headphones,
  MapPin, Users, Map, ShieldCheck, SlidersHorizontal, ReceiptText,
  BadgeDollarSign, Megaphone, ScrollText, Smartphone, ChevronRight,
  Bell, Search, CircleUserRound, PanelLeft
} from 'lucide-react'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'

const primary = [
  {label:'Visão geral',href:'/dashboard',icon:LayoutDashboard},
  {label:'Franquias',href:'/franquias',icon:Building2},
  {label:'Motoristas',href:'/motoristas',icon:CarFront},
  {label:'Corridas',href:'/corridas',icon:Route},
  {label:'Financeiro',href:'/financeiro',icon:WalletCards},
  {label:'Suporte',href:'/suporte',icon:Headphones},
]

const groups = [
  {title:'Rede e operação',items:[
    {label:'Cidades',href:'/cidades',icon:MapPin},{label:'Passageiros',href:'/passageiros',icon:Users},
    {label:'Mapa em tempo real',href:'/mapa',icon:Map},{label:'Controle operacional',href:'/controle',icon:SlidersHorizontal},
    {label:'Bloqueios',href:'/bloqueios',icon:ShieldCheck},{label:'Acessos',href:'/acessos',icon:CircleUserRound},
  ]},
  {title:'Tarifas e pagamentos',items:[
    {label:'Tarifas e categorias',href:'/tarifas',icon:ReceiptText},{label:'Regiões e áreas',href:'/regioes',icon:MapPin},
    {label:'Pagamentos e carteira',href:'/configuracoes-pagamentos',icon:WalletCards},{label:'Repasses',href:'/repasses',icon:BadgeDollarSign},
    {label:'Antecipações',href:'/antecipacoes',icon:BadgeDollarSign},{label:'Planos',href:'/planos',icon:ReceiptText},
  ]},
  {title:'Crescimento e sistema',items:[
    {label:'Cupons',href:'/cupons',icon:BadgeDollarSign},{label:'Promoções',href:'/promocoes',icon:Megaphone},
    {label:'Auditoria e logs',href:'/auditoria',icon:ScrollText},{label:'App Passageiro',href:'/passageiro',icon:Smartphone},
    {label:'App Motorista',href:'/motorista-app',icon:Smartphone},{label:'Painel Franqueado',href:'/franqueado',icon:Building2},
  ]},
]

export default function AppShell({children}:{children:React.ReactNode}){
  const pathname=usePathname()
  const assist=<AuthAssist/>
  if(pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname==='/login'||pathname==='/redefinir-senha') return <>{children}{assist}</>
  const active=(href:string)=>pathname===href||pathname.startsWith(href+'/')

  return <RoleGate role="super_admin" loginPath="/login">
    <div className="pro-shell">
      <aside className="pro-sidebar">
        <div className="pro-brand">
          <div className="pro-brand-mark">CG</div>
          <div><strong>CLICK-GO</strong><span>Matriz · Super Admin</span></div>
        </div>
        <div className="pro-sidebar-caption">Gestão da plataforma</div>
        <nav className="pro-nav">
          {primary.map(({label,href,icon:Icon})=><Link key={href} href={href} className={active(href)?'pro-nav-link active':'pro-nav-link'}><Icon size={18}/><span>{label}</span>{active(href)&&<ChevronRight size={15} className="pro-nav-arrow"/>}</Link>)}
          {groups.map(group=><div className="pro-nav-group" key={group.title}><div className="pro-nav-title">{group.title}</div>{group.items.map(({label,href,icon:Icon})=><Link key={href} href={href} className={active(href)?'pro-nav-link active':'pro-nav-link'}><Icon size={17}/><span>{label}</span>{active(href)&&<ChevronRight size={14} className="pro-nav-arrow"/>}</Link>)}</div>)}
        </nav>
        <div className="pro-sidebar-footer"><div className="pro-health"><span/>Operação monitorada</div><small>CLICK-GO Plataforma</small></div>
      </aside>

      <section className="pro-workspace">
        <header className="pro-topbar">
          <div className="pro-topbar-context"><PanelLeft size={19}/><div><strong>Central de Gestão</strong><span>Controle nacional da operação</span></div></div>
          <div className="pro-topbar-actions">
            <div className="pro-search"><Search size={17}/><span>Buscar na plataforma</span></div>
            <button className="pro-icon-button" aria-label="Notificações"><Bell size={18}/><i/></button>
            <div className="pro-user"><div className="pro-avatar">SA</div><div><strong>Super Admin</strong><span>Matriz CLICK-GO</span></div></div>
          </div>
        </header>
        <main className="pro-main">{children}</main>
      </section>
      {assist}
    </div>
  </RoleGate>
}
