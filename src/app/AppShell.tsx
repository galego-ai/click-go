'use client'

import Link from 'next/link'
import {usePathname} from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import AuthAssist from '@/components/AuthAssist'

const primary=[
 ['Início','/dashboard'],
 ['Franquias','/franquias'],
 ['Operação','/mapa'],
 ['Financeiro','/financeiro'],
 ['Suporte','/suporte'],
] as const

const administration=[
 ['Planos e preços','/planos'],
 ['Configurações','/configuracoes'],
 ['Relatórios','/relatorios'],
 ['Auditoria','/auditoria'],
 ['Usuários da matriz','/acessos'],
 ['Cidades e territórios','/cidades'],
 ['Motoristas','/motoristas'],
 ['Passageiros','/passageiros'],
 ['Tarifas e categorias','/tarifas'],
 ['Pagamentos e repasses','/pagamentos'],
 ['Apps e sincronização','/ecossistema'],
 ['Campanhas e notificações','/promocoes'],
] as const

export default function AppShell({children}:{children:React.ReactNode}){
 const pathname=usePathname(),assist=<AuthAssist/>
 if(pathname==='/'||pathname.startsWith('/franqueado')||pathname.startsWith('/passageiro')||pathname.startsWith('/motorista-app')||pathname.startsWith('/acompanhar')||pathname==='/login'||pathname==='/redefinir-senha')return <>{children}{assist}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/'),adminOpen=administration.some(([,href])=>active(href))
 return <RoleGate role="super_admin" loginPath="/login"><div className="simple-shell"><aside className="simple-sidebar"><Link href="/dashboard" className="simple-brand"><span className="simple-brand-mark">CG</span><div><strong>CLICK-GO</strong><small>Gestão da Matriz</small></div></Link><nav className="simple-nav">{primary.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}<details className="simple-more" open={adminOpen}><summary>Administração</summary><div>{administration.map(([label,href])=><Link className={active(href)?'active':''} key={href} href={href}>{label}</Link>)}</div></details></nav></aside><main className="simple-main">{children}</main>{assist}</div></RoleGate>
}
