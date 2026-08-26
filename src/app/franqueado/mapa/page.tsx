import Link from 'next/link'
import RealtimeMapData from '@/components/RealtimeMapData'

export default function Page(){return <div className="regional-home"><div className="regional-heading"><div><div className="eyebrow">Operação ao vivo</div><h1>Mapa operacional</h1><p>Acompanhe motoristas em tempo real por cidade, sem informações técnicas desnecessárias.</p></div><Link className="button secondary" href="/franqueado/operacao">Ver corridas</Link></div><RealtimeMapData/></div>}
