import ModulePage from '@/components/ModulePage'
export default function Page(){return <>
<div className="topbar"><div><div className="eyebrow">Operação ao vivo</div><h1 className="title">Mapa em tempo real</h1><p className="subtitle">Visualize motoristas online, corridas em andamento e distribuição da operação por cidade.</p></div><div className="toolbar"><button className="button secondary">Filtrar cidade</button><button className="button secondary">Somente online</button></div></div>
<div className="grid-3"><div className="card"><div className="label">Motoristas online</div><div className="metric kpi-good">0</div></div><div className="card"><div className="label">Corridas em andamento</div><div className="metric kpi-warn">0</div></div><div className="card"><div className="label">Cidades monitoradas</div><div className="metric">0</div></div></div>
<div className="section"><div className="map-placeholder"><div><strong>Mapa CLICK-GO</strong><p>Integração preparada para Google Maps/Mapbox + localização em tempo real via Supabase Realtime.</p></div></div></div>
</>}
