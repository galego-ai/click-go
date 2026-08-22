'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'

const primary = [
  ['Dashboard','/dashboard'],
  ['Franquias','/franquias'],
  ['Motoristas','/motoristas'],
  ['Corridas','/corridas'],
  ['Financeiro','/financeiro'],
  ['Suporte','/suporte'],
]

const groups = [
  { title: 'Rede e acessos', items: [['Cidades','/cidades'],['Acessos','/acessos'],['Planos','/planos']] },
  { title: 'Operação', items: [['Passageiros','/passageiros'],['Mapa em tempo real','/mapa'],['Relatório por Motorista','/relatorios-motoristas'],['Bloqueios','/bloqueios'],['Controle Total','/controle']] },
  { title: 'Tarifas e áreas', items: [['Tarifas & Categorias','/tarifas'],['Regiões & Áreas','/regioes']] },
  { title: 'Pagamentos', items: [['Pagamentos','/pagamentos'],['Pagamentos & Carteira','/configuracoes-pagamentos'],['Repasses','/repasses'],['Antecipações','/antecipacoes']] },
  { title: 'Marketing e gestão', items: [['Cupons','/cupons'],['Promoções','/promocoes'],['Banners & Anunciantes','/controle#banners'],['Auditoria & Logs','/auditoria']] },
  { title: 'Aplicativos', items: [['App Passageiro','/passageiro'],['App Motorista','/motorista-app'],['Painel Franqueado','/franqueado']] },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  if (pathname.startsWith('/franqueado') || pathname.startsWith('/passageiro') || pathname.startsWith('/motorista-app') || pathname === '/login' || pathname === '/redefinir-senha') return <>{children}</>

  const isActive = (href:string) => href.split('#')[0] === pathname

  return <RoleGate role="super_admin" loginPath="/login">
    <div className="shell">
      <aside className="sidebar sidebar-compact">
        <div className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Super Admin</small></div></div>
        <nav className="nav nav-compact">
          <div className="nav-primary">
            {primary.map(([label,href]) => <Link className={isActive(href)?'active':''} key={href} href={href}>{label}</Link>)}
          </div>
          <div className="nav-more-label">Mais opções</div>
          {groups.map(group => {
            const open = group.items.some(([,href]) => isActive(href))
            return <details className="nav-details" key={group.title} open={open}>
              <summary>{group.title}</summary>
              <div className="nav-details-items">
                {group.items.map(([label,href]) => <Link className={isActive(href)?'active':''} key={href} href={href}>{label}</Link>)}
              </div>
            </details>
          })}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  </RoleGate>
}
