import FranchiseLicenseCenter from '@/components/FranchiseLicenseCenter'

export default function Page(){
 return <>
  <div className="topbar compact-topbar">
   <div>
    <div className="eyebrow">CLICK-GO Gestão · Matriz</div>
    <h1 className="title">Franquias e Licenças</h1>
    <p className="subtitle">Rede multiempresa por cidade ou região, com licença, implantação, cobrança, território, suporte e sincronização dos apps.</p>
   </div>
  </div>
  <FranchiseLicenseCenter/>
 </>
}
