'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  if (pathname.startsWith('/franqueado')) return <>{children}</>

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-badge">CG</span> CLICK-GO</div>
      <nav className="nav">
        <Link href="/dashboard">Dashboard</Link><Link href="/cidades">Cidades</Link><Link href="/franquias">Franquias</Link><Link href="/motoristas">Motoristas</Link><Link href="/corridas">Corridas</Link>
        <div style={{height:1,background:'#292929',margin:'10px 0'}} />
        <Link href="/passageiro">App Passageiro</Link><Link href="/motorista-app">App Motorista</Link><Link href="/franqueado">Painel Franqueado</Link>
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div>
}
