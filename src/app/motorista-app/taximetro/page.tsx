'use client'

import Link from 'next/link'
import DriverTaximeter from '@/components/DriverTaximeter'

export default function DriverTaximeterPage(){
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:20}}><div style={{maxWidth:900,margin:'0 auto',display:'grid',gap:14}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:950}}>CLICK-GO MOTORISTA</div><h1 style={{margin:'5px 0'}}>Taxímetro / Maçaneta</h1><p style={{color:'#9ca3af',margin:0}}>Corrida livre com bandeirada, quilômetro, minuto, tarifa mínima e histórico GPS.</p></div><Link href="/motorista-app/operacao" style={{background:'#222',color:'#fff',textDecoration:'none',borderRadius:10,padding:'11px 14px',fontWeight:800}}>← Operação</Link></div>
  <DriverTaximeter/>
 </div></main>
}
