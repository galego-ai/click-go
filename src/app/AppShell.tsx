'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'

const groups = [
  { title: 'Visão geral', items: [['Dashboard','/dashboard'],['Controle Total','/controle']] },
  { title: 'Rede', items: [['Franquias','/franquias'],['Cidades','/cidades'],['Acessos','/acessos']] },
  { title: 'Planos & Tarifas', items: [['Planos','/planos'],['Tarifas & Categorias','/tarifas'],['Regiões & Áreas','/regioes']] },
  { title: 'Operação', items: [['Motoristas','/motoristas'],['Relatório por Motorista','/relatorios-motoristas'],['Passageiros','/passageiros'],['Corridas','/corridas'],['Mapa em tempo real','/mapa'],['Bloqueios','/bloqueios']] },
  { title: 'Financeiro', items: [['Faturamento','/financeiro'],['Pagamentos','/pagamentos'],['Repasses','/repasses'],['Antecipações','/antecipacoes']] },
  { title: 'Marketing', items: [['Cupons','/cupons'],['Promoções','/promocoes'],['Banners & Anunciantes','/controle#banners']] },
  { title: 'Atendimento', items: [['Suporte','/suporte'],['Auditoria & Logs','/auditoria']] },
  { title: 'Aplicativos', items: [['App Passageiro','/passageiro'],['App Motorista','/motorista-app'],['Painel Franqueado','/franqueado']] },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  if (pathname.startsWith('/franqueado') || pathname.startsWith('/passageiro') || pathname.startsWith('/motorista-app') || pathname === '/login' || pathname === '/redefinir-senha') return <>{children}</>

  return <RoleGate role="super_admin" loginPath="/login">
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Super Admin</small></div></div>
        <nav className="nav">
          {groups.map(group => <div className="nav-group" key={group.title}><div className="nav-title">{group.title}</div>{group.items.map(([label,href]) => <Link key={href} href={href}>{label}</Link>)}</div>)}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  </RoleGate>
}
