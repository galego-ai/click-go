import Link from 'next/link'

const items=[
 ['/franqueado/categorias','Tarifas e categorias','Preço base, km, minuto, tarifa mínima e dinâmica.'],
 ['/franqueado/pagamentos','Formas de pagamento','PIX, dinheiro, cartão e regras financeiras da operação.'],
 ['/franqueado/taxas','Taxas da operação','Taxas locais permitidas pelo plano e pela Matriz.'],
 ['/franqueado/anuncios','Promoções e anúncios','Campanhas e comunicação exibidas nos aplicativos.'],
 ['/franqueado/motoristas-categorias','Categorias dos motoristas','Defina quem pode atender cada categoria liberada.'],
] as const

export default function Page(){return <div className="regional-home"><div className="regional-heading"><div><div className="eyebrow">Configuração regional</div><h1>Configurações Locais</h1><p>Somente opções liberadas pela Matriz aparecem para sua operação.</p></div></div><div className="regional-action-grid">{items.map(([href,title,desc])=><Link className="regional-action" href={href} key={href}><strong>{title}</strong><span>{desc}</span><b>→</b></Link>)}</div><div className="card" style={{marginTop:18}}><strong>Hierarquia CLICK-GO</strong><p className="subtitle" style={{marginTop:8}}>Quando uma configuração estiver bloqueada pela Matriz, ela continua visível para consulta, mas não pode ser alterada localmente. Alterações autorizadas são registradas na auditoria e sincronizadas com os apps.</p></div></div>}
