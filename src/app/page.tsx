import Link from 'next/link'

const card:React.CSSProperties={background:'#141414',border:'1px solid #2b2b2b',borderRadius:18,padding:20,textDecoration:'none',color:'#fff',display:'block'}
const button:React.CSSProperties={display:'inline-block',marginTop:16,background:'#ffd400',color:'#000',padding:'10px 14px',borderRadius:10,fontWeight:900}

export default function Home(){
  return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:'40px 20px'}}>
    <div style={{maxWidth:980,margin:'0 auto'}}>
      <div className="eyebrow">CLICK-GO</div>
      <h1 className="title">Central de Acessos</h1>
      <p className="subtitle">Escolha como deseja entrar. Cada área possui login e permissões independentes.</p>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:16,marginTop:28}}>
        <Link href="/login" style={card}><div style={{fontSize:30}}>🏢</div><h2>Super Admin</h2><p className="subtitle">Matriz CLICK-GO: franquias, cidades, financeiro, auditoria e controle geral.</p><span style={button}>Entrar na Matriz</span></Link>
        <Link href="/franqueado/login" style={card}><div style={{fontSize:30}}>📍</div><h2>Franqueado</h2><p className="subtitle">Operação local: motoristas, categorias, tarifas, documentos, mapa e repasses.</p><span style={button}>Entrar como Franqueado</span></Link>
        <Link href="/passageiro" style={card}><div style={{fontSize:30}}>🚕</div><h2>Passageiro</h2><p className="subtitle">Criar conta, solicitar corrida, pagamentos, favoritos, histórico e suporte.</p><span style={button}>Abrir Passageiro</span></Link>
        <Link href="/motorista-app" style={card}><div style={{fontSize:30}}>🚘</div><h2>Motorista</h2><p className="subtitle">Cadastro, documentos, aprovação, corridas, carteira e operação.</p><span style={button}>Abrir Motorista</span></Link>
      </div>
      <div style={{marginTop:22,padding:16,border:'1px solid #2b2b2b',borderRadius:14,background:'#101010'}}>
        <strong>Para testar vários perfis no mesmo computador:</strong>
        <p className="subtitle" style={{marginBottom:0}}>Use uma janela anônima para cada perfil ou saia da conta atual antes de entrar em outra área. Assim uma sessão não substitui a outra durante os testes.</p>
      </div>
    </div>
  </main>
}
