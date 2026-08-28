'use client'

import Link from 'next/link'
import {usePathname} from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'
import MatrixSupportBanner from '@/components/MatrixSupportBanner'

const primary=[
 ['📊 Dashboard Geral','/dashboard'],
 ['🏢 Franquias','/franquias'],
 ['🗺️ Territórios','/cidades'],
 ['📋 Planos e Preços','/planos'],
 ['💳 Financeiro da Matriz','/financeiro'],
 ['🔒 Cobranças e Inadimplência','/bloqueios'],
] as const

const operation=[
 ['📲 Solicitar Corrida','/chamadas'],
 ['🚘 Motoristas','/motoristas'],
 ['👤 Passageiros','/passageiros'],
 ['🛣️ Corridas','/corridas'],
 ['💰 Tarifas','/tarifas'],
 ['🚕 Taxímetro por Franquia','/taximetro-franquias'],
 ['🎯 Promoções e Cupons','/promocoes'],
 ['💬 Chamados / Suporte','/suporte'],
 ['🔔 Notificações','/notificacoes-push'],
] as const

const governance=[
 ['🛡️ Auditoria','/auditoria'],
 ['⚙️ Configurações Gerais','/configuracoes'],
 ['👥 Usuários da Matriz','/acessos'],
 ['🔄 Apps e Sincronização','/ecossistema'],
] as const

export default function AppShell({children}:{children:React.ReactNode}){
 const pathname=usePathname(),assist=<AuthAssist/>
 if(pathname==='/'||pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname.startsWith('/acompanhar')||pathname==='/login'||pathname==='/redefinir-senha')return <>{children}{assist}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/')
 const governanceOpen=governance.some(([,href])=>active(href))
 return <RoleGate role="super_admin" loginPath="/login"><div className="shell shell-light"><aside className="sidebar sidebar-compact"><Link href="/dashboard" className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Painel Matriz</small></div></Link><nav className="nav nav-compact"><div className="nav-primary">{primary.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div><div className="nav-section-label">Operação da rede</div><div className="nav-primary">{operation.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div><details className="nav-details matrix-advanced" open={governanceOpen}><summary>Governança e sistema</summary><div className="nav-details-items">{governance.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div></details></nav><div className="sidebar-note"><strong>Arquitetura oficial</strong><span>Matriz controla a rede inteira. Cada franqueado acessa somente sua própria operação.</span></div></aside><main className="main"><MatrixSupportBanner/>{children}</main>{assist}</div></RoleGate>
}
