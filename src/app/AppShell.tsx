'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'

const primary=[
 ['Visão geral','/dashboard'],
 ['Operação','/corridas'],
 ['Franquias e Licenças','/franquias'],
 ['Financeiro','/financeiro'],
 ['Suporte','/suporte'],
] as const

const groups=[
 {title:'Cadastros',items:[['Cidades e territórios','/cidades'],['Motoristas','/motoristas'],['Passageiros','/passageiros'],['Acessos e equipe','/acessos']]},
 {title:'Operação avançada',items:[['Mapa ao vivo','/mapa'],['Segurança','/seguranca'],['Bloqueios','/bloqueios'],['Taxímetros','/taximetros'],['Relatórios','/relatorios-motoristas']]},
 {title:'Tarifas e pagamentos',items:[['Tarifas e categorias','/tarifas'],['Regiões e áreas','/regioes'],['Pagamentos','/pagamentos'],['Carteiras e gateways','/configuracoes-pagamentos'],['Repasses','/repasses'],['Antecipações','/antecipacoes']]},
 {title:'Gestão da rede',items:[['Planos e licenciamento','/planos'],['Apps e sincronização','/ecossistema'],['Cupons','/cupons'],['Promoções','/promocoes'],['Auditoria','/auditoria'],['Notificações push','/notificacoes-push']]},
] as const

export default function AppShell({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 const assist=<AuthAssist/>
 if(pathname==='/'||pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname.startsWith('/acompanhar')||pathname==='/login'||pathname==='/redefinir-senha')return <>{children}{assist}</>
 const active=(href:string)=>pathname===href.split('#')[0]||pathname.startsWith(href.split('#')[0]+'/')
 return <RoleGate role="super_admin" loginPath="/login">
  <div className="shell">
   <aside className="sidebar sidebar-compact">
    <Link href="/dashboard" className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Gestão · Matriz</small></div></Link>
    <nav className="nav nav-compact">
     <div className="nav-primary">{primary.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div>
     <div className="nav-more-label">Gestão completa</div>
     {groups.map(group=>{const open=group.items.some(([,href])=>active(href));return <details className="nav-details" key={group.title} open={open}><summary>{group.title}</summary><div className="nav-details-items">{group.items.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div></details>})}
    </nav>
   </aside>
   <main className="main">{children}</main>
   {assist}
  </div>
 </RoleGate>
}
