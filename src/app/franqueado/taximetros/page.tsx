import TaximeterFinancialSettings from '@/components/TaximeterFinancialSettings'
import TaximeterOperationsReport from '@/components/TaximeterOperationsReport'

export default function FranchiseTaximeterReportPage(){
  return <div style={{display:'grid',gap:14}}>
    <TaximeterFinancialSettings/>
    <TaximeterOperationsReport/>
  </div>
}
