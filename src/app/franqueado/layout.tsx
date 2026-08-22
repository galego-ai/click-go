import Link from 'next/link'

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 return <><div style={{position:'fixed',right:18,bottom:18,zIndex:50,display:'flex',gap:8}}><Link href="/franqueado" style={{background:'#222',color:'#fff',padding:'10px 13px',borderRadius:10,border:'1px solid #333',fontWeight:800}}>Central</Link><Link href="/franqueado/cadastros" style={{background:'#ffd400',color:'#000',padding:'10px 13px',borderRadius:10,fontWeight:900}}>+ Cadastro</Link></div>{children}</>
}
