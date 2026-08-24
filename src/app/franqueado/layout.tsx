'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import RoleGate from '@/components/RoleGate'

const core=[
 ['/franqueado','Início'],
 ['/franqueado/operacao','Operação'],
 ['/franqueado/cadastros','Motoristas e passageiros'],
 ['/franqueado/categorias','Tarifas'],
 ['/franqueado/carteiras','Carteiras'],
 ['/franqueado/pagamentos','Financeiro'],
] as const

const more=[
 ['/franqueado/mapa','Mapa ao vivo'],
 ['/franqueado/documentos','Documentos pendentes'],
 ['/franqueado/cancelamentos','Cancelamentos'],
 ['/franqueado/anuncios','Anúncios'],
 ['/franqueado/repasse','Repasses'],
 ['/franqueado/taximetros','Taxímetros'],
 ['/franqueado/seguranca','Segurança'],
 ['/franqueado/taxas','Taxas da operação'],
 ['/franqueado/motoristas-categorias','Categorias dos motoristas'],
] as const

const css=`
.regional-shell{min-height:100vh;background:#090909;color:#f7f7f7;display:grid;grid-template-columns:224px minmax(0,1fr)}
.regional-sidebar{height:100vh;position:sticky;top:0;border-right:1px solid #242424;background:#0d0d0d;padding:20px 14px;overflow:auto}
.regional-brand{display:flex;align-items:center;gap:10px;margin:0 6px 24px;color:#fff}.regional-brand span{width:38px;height:38px;border-radius:10px;background:#ffd400;color:#000;display:grid;place-items:center;font-weight:950}.regional-brand strong{display:block;font-size:17px}.regional-brand small{display:block;color:#858585;font-size:11px;margin-top:2px}
.regional-nav{display:grid;gap:4px}.regional-nav>a,.regional-more a{display:block;padding:10px 11px;border-radius:9px;color:#bdbdbd;font-size:13px;font-weight:650}.regional-nav>a:hover,.regional-more a:hover{background:#171717;color:#fff}.regional-nav>a.active,.regional-more a.active{background:#1b1b1b;color:#ffd400}
.regional-more{margin-top:8px;border-top:1px solid #222;padding-top:8px}.regional-more summary{cursor:pointer;list-style:none;color:#777;font-size:11px;text-transform:uppercase;letter-spacing:.08em;padding:9px 11px}.regional-more summary::-webkit-details-marker{display:none}.regional-more summary:after{content:'+';float:right}.regional-more[open] summary:after{content:'−'}.regional-more div{display:grid;gap:2px;padding-left:4px}
.regional-main{min-width:0;padding:28px}.regional-home{max-width:1280px;margin:0 auto}.regional-heading{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:22px}.regional-heading h1{font-size:30px;margin:4px 0}.regional-heading p{margin:0;color:#8e8e8e;font-size:14px}
.regional-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.regional-kpi{background:#121212;border:1px solid #252525;border-radius:14px;padding:16px}.regional-kpi span{display:block;color:#919191;font-size:12px}.regional-kpi strong{display:block;font-size:27px;margin:8px 0 4px}.regional-kpi small{color:#6f6f6f;font-size:11px}
.regional-alert{padding:12px 14px;border:1px solid #624f00;background:#181500;color:#ffe168;border-radius:12px;margin-bottom:14px}.regional-actions{margin-top:24px}.regional-action-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.regional-action{position:relative;min-height:92px;padding:16px 42px 16px 16px;border:1px solid #252525;background:#111;border-radius:14px}.regional-action:hover{border-color:#414141;background:#151515}.regional-action strong{display:block;font-size:15px;margin-bottom:5px}.regional-action span{display:block;color:#888;font-size:12px;line-height:1.45}.regional-action b{position:absolute;right:16px;top:50%;transform:translateY(-50%);color:#ffd400;font-size:19px}
@media(max-width:1000px){.regional-kpis{grid-template-columns:repeat(2,1fr)}.regional-action-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:820px){.regional-shell{display:block}.regional-sidebar{height:auto;position:sticky;z-index:50;padding:10px 12px;display:flex;align-items:center;gap:10px;overflow-x:auto;border-right:0;border-bottom:1px solid #242424}.regional-brand{margin:0;flex:0 0 auto}.regional-brand div{display:none}.regional-nav{display:flex;gap:3px;min-width:max-content}.regional-nav>a{white-space:nowrap}.regional-more{display:none}.regional-main{padding:18px}}
@media(max-width:620px){.regional-heading{align-items:flex-start}.regional-heading h1{font-size:24px}.regional-kpis,.regional-action-grid{grid-template-columns:1fr}.regional-main{padding:14px}.regional-heading .button{padding:9px 10px;font-size:12px}}
`

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname()
 if(pathname==='/franqueado/login'||pathname==='/franqueado/trocar-senha-temporaria')return <>{children}</>
 const active=(href:string)=>pathname===href||pathname.startsWith(href+'/')
 const moreOpen=more.some(([href])=>active(href))
 return <RoleGate role="franchise_admin" loginPath="/franqueado/login">
  <style>{css}</style>
  <div className="regional-shell">
   <aside className="regional-sidebar">
    <Link href="/franqueado" className="regional-brand"><span>CG</span><div><strong>CLICK-GO</strong><small>Regional</small></div></Link>
    <nav className="regional-nav">
     {core.map(([href,label])=><Link key={href} href={href} className={active(href)?'active':''}>{label}</Link>)}
     <details className="regional-more" open={moreOpen}>
      <summary>Mais opções</summary>
      <div>{more.map(([href,label])=><Link key={href} href={href} className={active(href)?'active':''}>{label}</Link>)}</div>
     </details>
    </nav>
   </aside>
   <main className="regional-main">{children}</main>
  </div>
 </RoleGate>
}
