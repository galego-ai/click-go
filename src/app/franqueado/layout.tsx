import Link from 'next/link'
import FranchiseGuard from '@/components/FranchiseGuard'

const groups=[
 {title:'Visão geral',items:[['Dashboard','/franqueado']]},
 {title:'Operação',items:[['Motoristas','/franqueado/motoristas'],['Passageiros','/franqueado/passageiros'],['Corridas','/franqueado/corridas'],['Mapa da cidade','/franqueado/mapa']]},
 {title:'Preços & oferta',items:[['Categorias & Tarifas','/franqueado/tarifas'],['Áreas & Horários','/franqueado/configuracoes']]},
 {title:'Financeiro',items:[['Faturamento & Comissão','/franqueado/financeiro'],['Extrato & Repasses','/franqueado/repasses']]},
 {title:'Marketing',items:[['Cupons & Promoções','/franqueado/marketing']]},
 {title:'Atendimento',items:[['Chamados & Relatórios','/franqueado/suporte']]},
]
export default function Layout({children}:{children:React.ReactNode}){return <FranchiseGuard><div className="shell"><aside className="sidebar"><div className="brand"><span className="brand-badge">CG</span><div><strong>CLICK-GO</strong><small>Painel do Franqueado</small></div></div><nav className="nav">{groups.map(g=><div className="nav-group" key={g.title}><div className="nav-title">{g.title}</div>{g.items.map(([l,h])=><Link href={h} key={h}>{l}</Link>)}</div>)}</nav></aside><main className="main">{children}</main></div></FranchiseGuard>}
