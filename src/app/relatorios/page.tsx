import Link from 'next/link'

const items=[
 ['/relatorios-motoristas','Motoristas','Atividade, cadastros, desempenho e status.'],
 ['/financeiro','Financeiro consolidado','Receita, pendências, franquias e movimentos da rede.'],
 ['/corridas','Corridas','Operação, status e volume de corridas.'],
 ['/auditoria','Auditoria','Alterações administrativas, origem e histórico.'],
 ['/suporte','Suporte','Chamados e indicadores de atendimento.'],
 ['/franquias','Franquias e licenças','Consumo, plano, excedentes e situação das operações.'],
] as const

export default function Page(){return <><div className="topbar compact-topbar"><div><div className="eyebrow">Matriz CLICK-GO</div><h1 className="title">Relatórios Consolidados</h1><p className="subtitle">Acesse os principais relatórios da rede sem navegar por menus técnicos.</p></div></div><div className="grid-3">{items.map(([href,title,desc])=><Link href={href} className="card" key={href} style={{display:'block'}}><strong>{title}</strong><p className="subtitle" style={{marginTop:7}}>{desc}</p></Link>)}</div></>}
