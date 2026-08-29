'use client'

import Link from 'next/link'
import {usePathname} from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'
import MatrixSupportBanner from '@/components/MatrixSupportBanner'
import LogoutButton from '@/components/LogoutButton'

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

const sessionCss=`
.matrix-logout{width:100%;margin-top:12px;border:1px solid #443434;background:#1b1010;color:#ffb4b4;border-radius:9px;padding:10px 12px;font-weight:850;cursor:pointer;text-align:center}.matrix-logout:hover{background:#291313;border-color:#7f2b2b;color:#fff}.matrix-logout:disabled{opacity:.6;cursor:wait}.matrix-mobile-logout{display:none}
@media(max-width:900px){.matrix-mobile-logout{display:flex;justify-content:flex-end;margin-bottom:12px}.matrix-mobile-logout .matrix-logout{width:auto;margin:0;padding:9px 12px;position:sticky;top:10px;z-index:60}}
`

export default function AppShell({children}:{children:React.ReactNode}){
 const pathname=usePathname(),assist=<AuthAssist/>
 if(pathname==='/'||pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname.startsWith('/acompanhar')||pathname==='/login'||pathname==='/redefinir-senha')return <>{children}{assist}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/')
 const governanceOpen=governance.some(([,href])=>active(href))
 return <RoleGate role="super_admin" loginPath="/login"><style>{sessionCss}</style><div className="shell shell-light"><aside className="sidebar sidebar-compact"><Link href="/dashboard" className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Painel Matriz</small></div></Link><nav className="nav nav-compact"><div className="nav-primary">{primary.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div><div className="nav-section-label">Operação da rede</div><div className="nav-primary">{operation.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div><details className="nav-details matrix-advanced" open={governanceOpen}><summary>Governança e sistema</summary><div className="nav-details-items">{governance.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div></details></nav><LogoutButton loginPath="/login" className="matrix-logout"/><div className="sidebar-note"><strong>Arquitetura oficial</strong><span>Matriz controla a rede inteira. Cada franqueado acessa somente sua própria operação.</span></div></aside><main className="main"><div className="matrix-mobile-logout"><LogoutButton loginPath="/login" className="matrix-logout" compact/></div><MatrixSupportBanner/>{children}</main>{assist}</div></RoleGate>
}
