import FinanceQueue from '@/components/FinanceQueue'
export default function Page(){return <><div className="topbar"><div><div className="eyebrow">Financeiro</div><h1 className="title">Pagamentos</h1><p className="subtitle">Acompanhe e atualize pagamentos Pix, cartão, dinheiro e carteira por status.</p></div></div><FinanceQueue kind="payments"/></>}
