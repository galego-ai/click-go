import TaximeterFinancialSettings from '@/components/TaximeterFinancialSettings'
import TaximeterOperationsReport from '@/components/TaximeterOperationsReport'

export default function TaximeterReportPage(){
  return <div style={{display:'grid',gap:14}}>
    <TaximeterFinancialSettings network/>
    <TaximeterOperationsReport network/>
  </div>
}
