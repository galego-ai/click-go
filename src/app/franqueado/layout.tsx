'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, UserPlus, FileCheck2, Tags, Ban, RadioTower, WalletCards,
  Percent, CreditCard, Megaphone, Landmark, Map, Bell, ChevronRight, CircleUserRound
} from 'lucide-react'
import RoleGate from '@/components/RoleGate'

const groups=[
 {title:'Operação',items:[
  {href:'/franqueado',name:'Visão geral',icon:LayoutDashboard},
  {href:'/franqueado/operacao',name:'Central operacional',icon:RadioTower},
  {href:'/franqueado/mapa',name:'Mapa em tempo real',icon:Map},
 ]},
 {title:'Cadastros',items:[
  {href:'/franqueado/cadastros',name:'Motoristas e passageiros',icon:UserPlus},
  {href:'/franqueado/documentos',name:'Aprovações e documentos',icon:FileCheck2},
  {href:'/franqueado/categorias',name:'Categorias e preços',icon:Tags},
  {href:'/franqueado/cancelamentos',name:'Cancelamentos',icon:Ban},
 ]},
 {title:'Financeiro',items:[
  {href:'/franqueado/carteiras',name:'Carteiras dos motoristas',icon:WalletCards},
  {href:'/franqueado/taxas',name:'Taxas R$ / %',icon:Percent},
  {href:'/franqueado/pagamentos',name:'Pagamentos',icon:CreditCard},
  {href:'/franqueado/repasse',name:'Repasses',icon:Landmark},
 ]},
 {title:'Comercial',items:[
  {href:'/franqueado/anuncios',name:'Anúncios e campanhas',icon:Megaphone},
 ]},
]

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 if(pathname==='/franqueado/login'||pathname==='/franqueado/trocar-senha-temporaria') return <>{children}</>
 const active=(href:string)=>href==='/franqueado'?pathname===href:pathname===href||pathname.startsWith(href+'/')
 return <RoleGate role="franchise_admin" loginPath="/franqueado/login">
  <div className="fr-shell">
   <aside className="fr-sidebar">
    <div className="fr-brand"><div className="mark">CG</div><div><strong>CLICK-GO</strong><small>Painel do Franqueado</small></div></div>
    <nav className="fr-nav">{groups.map(group=><div key={group.title}><div className="fr-nav-section">{group.title}</div>{group.items.map(({href,name,icon:Icon})=><Link className={active(href)?'fr-link active':'fr-link'} key={href} href={href}><Icon size={17}/><span>{name}</span>{active(href)&&<ChevronRight size={14} style={{marginLeft:'auto'}}/>}</Link>)}</div>)}</nav>
    <div className="fr-footer">Sua operação local · regras da Matriz sempre prevalecem</div>
   </aside>
   <section className="fr-main">
    <header className="fr-topbar">
      <div className="fr-context"><strong>Gestão da franquia</strong><span>Operação, motoristas, preços e financeiro</span></div>
      <div className="fr-actions"><button className="pro-icon-button" aria-label="Notificações"><Bell size={17}/><i/></button><div className="pro-avatar"><CircleUserRound size={17}/></div></div>
    </header>
    <div className="fr-workspace">{children}</div>
   </section>
  </div>
 </RoleGate>
}
