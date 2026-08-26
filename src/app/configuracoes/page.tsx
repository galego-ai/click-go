import Link from 'next/link'

const items=[
 ['/tarifas','Tarifas e categorias','Regras de preço e categorias controladas pela Matriz.'],
 ['/configuracoes-pagamentos','Pagamentos e gateways','PIX, cartões, gateways e regras financeiras globais.'],
 ['/cidades','Cidades e territórios','Cobertura, cidades ativas e associação territorial.'],
 ['/regioes','Regiões e áreas','Áreas operacionais e regras geográficas.'],
 ['/ecossistema','Apps e sincronização','Versões de configuração compartilhadas com Passageiro e Motorista.'],
 ['/notificacoes-push','Notificações','Comunicação operacional e avisos para os aplicativos.'],
] as const

export default function Page(){return <><div className="topbar compact-topbar"><div><div className="eyebrow">Matriz CLICK-GO</div><h1 className="title">Configurações Globais</h1><p className="subtitle">Regras da rede em um só lugar. A Matriz pode sobrescrever configurações locais quando necessário.</p></div></div><div className="grid-3">{items.map(([href,title,desc])=><Link href={href} className="card" key={href} style={{display:'block'}}><strong>{title}</strong><p className="subtitle" style={{marginTop:7}}>{desc}</p></Link>)}</div></>}
