'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'

const core=[
 ['/franqueado','Início'],
 ['/franqueado/operacao','Operação'],
 ['/franqueado/cadastros','Motoristas e passageiros'],
 ['/franqueado/categorias','Tarifas'],
 ['/franqueado/carteiras','Carteiras'],
 ['/franqueado/pagamentos','Financeiro'],
] as const

const more=[
 ['/franqueado/mapa','Mapa ao vivo'],
 ['/franqueado/documentos','Documentos pendentes'],
 ['/franqueado/cancelamentos','Cancelamentos'],
 ['/franqueado/anuncios','Anúncios'],
 ['/franqueado/repasse','Repasses'],
 ['/franqueado/taximetros','Taxímetros'],
 ['/franqueado/seguranca','Segurança'],
 ['/franqueado/taxas','Taxas da operação'],
 ['/franqueado/motoristas-categorias','Categorias dos motoristas'],
] as const

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 if(pathname==='/franqueado/login'||pathname==='/franqueado/trocar-senha-temporaria')return <>{children}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/')
 const moreOpen=more.some(([href])=>active(href))
 return <RoleGate role="franchise_admin" loginPath="/franqueado/login">
  <div className="regional-shell">
   <aside className="regional-sidebar">
    <Link href="/franqueado" className="regional-brand"><span>CG</span><div><strong>CLICK-GO</strong><small>Regional</small></div></Link>
    <nav className="regional-nav">
     {core.map(([href,label])=><Link key={href} href={href} className={active(href)?'active':''}>{label}</Link>)}
     <details className="regional-more" open={moreOpen}>
      <summary>Mais opções</summary>
      <div>{more.map(([href,label])=><Link key={href} href={href} className={active(href)?'active':''}>{label}</Link>)}</div>
     </details>
    </nav>
   </aside>
   <main className="regional-main">{children}</main>
  </div>
 </RoleGate>
}
