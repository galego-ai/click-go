'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'

const items=[
 ['/franqueado','Painel'],
 ['/franqueado/cadastros','Cadastros'],
 ['/franqueado/documentos','Documentos'],
 ['/franqueado/categorias','Categorias'],
 ['/franqueado/operacao','Operação'],
 ['/franqueado/repasse','Repasses'],
 ['/franqueado/mapa','Mapa'],
]

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 if(pathname==='/franqueado/login') return <>{children}</>

 return <RoleGate role="franchise_admin" loginPath="/franqueado/login">
  <div style={{background:'#080808',minHeight:'100vh'}}>
   <header style={{position:'sticky',top:0,zIndex:1000,background:'#0b0b0bee',backdropFilter:'blur(10px)',borderBottom:'1px solid #262626',padding:'10px 16px',display:'flex',alignItems:'center',gap:12,overflowX:'auto'}}>
    <Link href="/franqueado" style={{color:'#000',background:'#ffd400',fontWeight:900,textDecoration:'none',padding:'9px 12px',borderRadius:9,whiteSpace:'nowrap'}}>CLICK-GO Franqueado</Link>
    {items.map(([href,name])=><Link key={href} href={href} style={{color:'#e5e7eb',textDecoration:'none',fontWeight:700,fontSize:14,padding:'8px 9px',whiteSpace:'nowrap'}}>{name}</Link>)}
   </header>
   {children}
  </div>
 </RoleGate>
}
