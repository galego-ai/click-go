import PlanManager from '@/components/PlanManager'
import SubscriptionManager from '@/components/SubscriptionManager'
export default function Page(){return <><div className="topbar"><div><div className="eyebrow">Monetização</div><h1 className="title">Planos das franquias</h1><p className="subtitle">Controle mensalidade, percentual ou valor por corrida, limite, excedente, comissão da matriz e atribuição de planos a cada franquia.</p></div></div><PlanManager/><SubscriptionManager/></>}
