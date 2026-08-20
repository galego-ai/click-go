import './globals.css'
import Link from 'next/link'

export const metadata = { title: 'CLICK-GO Super Admin', description: 'Plataforma de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-badge">CG</span> CLICK-GO</div>
      <nav className="nav">
        <Link href="/dashboard">Dashboard</Link><Link href="/cidades">Cidades</Link><Link href="/franquias">Franquias</Link><Link href="/motoristas">Motoristas</Link><Link href="/corridas">Corridas</Link>
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div></body></html>
}
