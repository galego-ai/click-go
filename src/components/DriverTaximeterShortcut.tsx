'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function DriverTaximeterShortcut(){
 const path=usePathname()
 if(!path.startsWith('/motorista-app')||path.startsWith('/motorista-app/taximetro'))return null
 return <Link href="/motorista-app/taximetro" style={{position:'fixed',left:18,bottom:18,zIndex:9996,background:'#ffd400',color:'#000',textDecoration:'none',borderRadius:999,padding:'12px 16px',fontWeight:950,boxShadow:'0 12px 30px #0006',border:'2px solid #111'}}>🚕 Taxímetro / Maçaneta</Link>
}
