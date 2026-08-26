import Link from 'next/link'
import FranchiseLicenseCenter from '@/components/FranchiseLicenseCenter'

export default function Page(){
 return <>
  <div className="simple-page">
   <div className="simple-header">
    <div><div className="simple-eyebrow">Administração</div><h1>Gestão avançada de franquias</h1><p>Use esta área somente para cadastro, implantação, plano, território e ações administrativas.</p></div>
    <Link className="simple-btn" href="/franquias">← Voltar para franquias</Link>
   </div>
  </div>
  <FranchiseLicenseCenter/>
 </>
}
