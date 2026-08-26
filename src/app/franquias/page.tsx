import Link from 'next/link'
import SimpleFranchiseCenter from '@/components/SimpleFranchiseCenter'

export default function Page(){
 return <>
  <div className="simple-page">
   <div className="simple-header">
    <div><div className="simple-eyebrow">Matriz CLICK-GO</div><h1>Franquias</h1><p>Veja a rede inteira de forma simples. Clique em uma franquia para aprofundar.</p></div>
    <div className="simple-actions"><Link className="simple-btn" href="/franquias/avancado">Administração avançada</Link><Link className="simple-btn primary" href="/franquias/avancado">+ Nova franquia</Link></div>
   </div>
  </div>
  <SimpleFranchiseCenter/>
 </>
}
