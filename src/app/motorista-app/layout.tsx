'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function DriverAppLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 return <div style={{minHeight:'100vh',background:'#080808'}}>
  <header style={{position:'sticky',top:0,zIndex:1200,background:'#0b0b0bf2',backdropFilter:'blur(10px)',borderBottom:'1px solid #292929',padding:'10px 16px',display:'flex',gap:9,alignItems:'center',overflowX:'auto'}}>
   <Link href="/motorista-app" style={{background:'#ffd400',color:'#000',fontWeight:900,textDecoration:'none',padding:'9px 12px',borderRadius:9,whiteSpace:'nowrap'}}>CLICK-GO Motorista</Link>
   <Link href="/motorista-app" style={{color:pathname==='/motorista-app'?'#ffd400':'#e5e7eb',fontWeight:800,textDecoration:'none',padding:'8px',whiteSpace:'nowrap'}}>Cadastro e documentos</Link>
   <Link href="/motorista-app/operacao" style={{color:pathname.startsWith('/motorista-app/operacao')?'#ffd400':'#e5e7eb',fontWeight:800,textDecoration:'none',padding:'8px',whiteSpace:'nowrap'}}>Operação e corridas</Link>
   <Link href="/motorista-app/carteira" style={{color:pathname.startsWith('/motorista-app/carteira')?'#ffd400':'#e5e7eb',fontWeight:800,textDecoration:'none',padding:'8px',whiteSpace:'nowrap'}}>Carteira</Link>
  </header>
  {children}
 </div>
}
