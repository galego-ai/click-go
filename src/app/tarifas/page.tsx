import TariffManager from '@/components/TariffManager'
export default function Page(){return <><div className="topbar"><div><div className="eyebrow">Precificação</div><h1 className="title">Tarifas por cidade</h1><p className="subtitle">Defina tarifa base, preço por km/minuto, tarifa mínima, cancelamento e multiplicador dinâmico.</p></div></div><TariffManager/></>}
