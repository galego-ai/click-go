import './globals.css'
import Link from 'next/link'

export const metadata = { title: 'CLICK-GO Super Admin', description: 'Plataforma de mobilidade urbana CLICK-GO' }

const groups = [
  { title: 'Visão geral', items: [['Dashboard','/dashboard'],['Controle Total','/controle']] },
  { title: 'Rede', items: [['Franquias','/franquias'],['Cidades','/cidades'],['Acessos','/acessos']] },
  { title: 'Planos & Tarifas', items: [['Planos','/planos'],['Tarifas & Categorias','/tarifas'],['Regiões & Áreas','/regioes']] },
  { title: 'Operação', items: [['Motoristas','/motoristas'],['Relatório por Motorista','/relatorios-motoristas'],['Passageiros','/passageiros'],['Corridas','/corridas'],['Mapa em tempo real','/mapa'],['Bloqueios','/bloqueios']] },
  { title: 'Financeiro', items: [['Faturamento','/financeiro'],['Pagamentos','/pagamentos'],['Repasses','/repasses'],['Antecipações','/antecipacoes']] },
  { title: 'Marketing', items: [['Cupons','/cupons'],['Promoções','/promocoes'],['Banners & Anunciantes','/controle#banners']] },
  { title: 'Atendimento', items: [['Suporte','/suporte'],['Auditoria & Logs','/auditoria']] },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Super Admin</small></div></div>
      <nav className="nav">
        {groups.map(group => <div className="nav-group" key={group.title}><div className="nav-title">{group.title}</div>{group.items.map(([label,href]) => <Link key={href} href={href}>{label}</Link>)}</div>)}
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div></body></html>
}
