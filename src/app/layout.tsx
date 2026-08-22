import './globals.css'
import Link from 'next/link'

export const metadata = { title: 'CLICK-GO Super Admin', description: 'Plataforma de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-badge">CG</span> CLICK-GO</div>
      <nav className="nav">
        <Link href="/dashboard">Dashboard</Link><Link href="/cidades">Cidades</Link><Link href="/franquias">Franquias</Link><Link href="/motoristas">Motoristas</Link><Link href="/corridas">Corridas</Link>
        <div style={{height:1,background:'#292929',margin:'10px 0'}} />
        <Link href="/passageiro">App Passageiro</Link><Link href="/motorista-app">App Motorista</Link>
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div></body></html>
}
