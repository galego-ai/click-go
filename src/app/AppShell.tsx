'use client'

import Link from 'next/link'
import {usePathname} from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'

const primary=[
 ['📊 Dashboard Geral','/dashboard'],
 ['🌍 Franquias e Licenças','/franquias'],
 ['⚙️ Configurações Globais','/configuracoes'],
 ['📋 Planos e Preços','/planos'],
 ['📈 Relatórios Consolidados','/relatorios'],
 ['🛡️ Auditoria','/auditoria'],
 ['👥 Usuários Matriz','/acessos'],
 ['🔧 Suporte Técnico','/suporte'],
] as const

const advanced=[
 ['Mapa ao vivo','/mapa'],
 ['Operação e corridas','/corridas'],
 ['Financeiro','/financeiro'],
 ['Cidades e territórios','/cidades'],
 ['Motoristas','/motoristas'],
 ['Passageiros','/passageiros'],
 ['Tarifas e categorias','/tarifas'],
 ['Pagamentos','/pagamentos'],
 ['Repasses','/repasses'],
 ['Antecipações','/antecipacoes'],
 ['Apps e sincronização','/ecossistema'],
 ['Cupons e promoções','/promocoes'],
 ['Notificações push','/notificacoes-push'],
] as const

export default function AppShell({children}:{children:React.ReactNode}){
 const pathname=usePathname(),assist=<AuthAssist/>
 if(pathname==='/'||pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname.startsWith('/acompanhar')||pathname==='/login'||pathname==='/redefinir-senha')return <>{children}{assist}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/'),advancedOpen=advanced.some(([,href])=>active(href))
 return <RoleGate role="super_admin" loginPath="/login"><div className="shell shell-light"><aside className="sidebar sidebar-compact"><Link href="/dashboard" className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO Gestão</strong><small>Matriz</small></div></Link><nav className="nav nav-compact"><div className="nav-primary">{primary.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div><details className="nav-details matrix-advanced" open={advancedOpen}><summary>Ferramentas avançadas</summary><div className="nav-details-items">{advanced.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div></details></nav></aside><main className="main">{children}</main>{assist}</div></RoleGate>
}
