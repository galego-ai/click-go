import RealtimeMapData from '@/components/RealtimeMapData'
export default function Page(){return <><div className="topbar"><div><div className="eyebrow">Operação ao vivo</div><h1 className="title">Mapa em tempo real</h1><p className="subtitle">Receba posições dos motoristas via Supabase Realtime e prepare a renderização no Google Maps/Mapbox.</p></div></div><RealtimeMapData/></>}
