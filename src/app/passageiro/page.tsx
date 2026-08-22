'use client'

import { FormEvent, useState } from 'react'
import { supabase } from '@/lib/supabase'

const menu = ['Início', 'Solicitar corrida', 'Histórico de corridas', 'Formas de pagamento', 'Cupons', 'Endereços favoritos', 'Ajuda e suporte', 'Meu perfil']

export default function PassengerPage() {
  const [active, setActive] = useState('Início')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function register(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    const data = new FormData(e.currentTarget)
    const email = String(data.get('email') || '').trim()
    const password = String(data.get('password') || '')
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          app_role: 'passenger',
          full_name: String(data.get('full_name') || '').trim(),
          phone: String(data.get('phone') || '').trim(),
          cpf: String(data.get('cpf') || '').trim(),
        },
      },
    })
    setLoading(false)
    setMessage(error ? error.message : 'Cadastro realizado. Confira seu e-mail para confirmar a conta.')
  }

  return <>
    <div className="topbar"><div><div className="eyebrow">App Passageiro</div><h1 className="title">CLICK-GO Passageiro</h1><p className="subtitle">Cadastro livre, sem obrigar o passageiro a escolher cidade.</p></div></div>
    <div style={{display:'grid',gridTemplateColumns:'230px 1fr',gap:16,alignItems:'start'}}>
      <aside className="card" style={{padding:10}}>
        {menu.map(item => <button key={item} onClick={() => setActive(item)} style={{display:'block',width:'100%',textAlign:'left',padding:'12px',marginBottom:6,border:0,borderRadius:10,cursor:'pointer',fontWeight:700,background:active===item?'#ffd400':'#1d1d1d',color:active===item?'#000':'#fff'}}>{item}</button>)}
      </aside>
      <section className="card">
        <div className="eyebrow">{active}</div>
        {active === 'Início' ? <>
          <h2>Cadastre-se para pedir corridas</h2>
          <p className="subtitle" style={{marginBottom:18}}>A cidade será identificada somente quando o passageiro solicitar uma corrida. O cadastro não fica preso a nenhuma franquia.</p>
          <form onSubmit={register} style={{display:'grid',gap:12,maxWidth:560}}>
            <input name="full_name" required placeholder="Nome completo" className="form-input" />
            <input name="phone" required placeholder="Telefone / WhatsApp" className="form-input" />
            <input name="cpf" placeholder="CPF" className="form-input" />
            <input name="email" required type="email" placeholder="E-mail" className="form-input" />
            <input name="password" required type="password" minLength={6} placeholder="Senha" className="form-input" />
            <button className="button" disabled={loading}>{loading ? 'Cadastrando...' : 'Criar conta de passageiro'}</button>
          </form>
          {message && <p style={{marginTop:14}}>{message}</p>}
        </> : <>
          <h2>{active}</h2>
          <p className="subtitle">Esta área já está reservada no menu do passageiro e será ligada aos dados reais da conta e das corridas.</p>
          {active === 'Histórico de corridas' && <table className="table" style={{marginTop:16}}><thead><tr><th>Data</th><th>Origem</th><th>Destino</th><th>Valor</th></tr></thead><tbody><tr><td colSpan={4} className="empty">Nenhuma corrida encontrada.</td></tr></tbody></table>}
          {active === 'Formas de pagamento' && <div className="card" style={{marginTop:16}}><strong>PIX, cartão e dinheiro</strong><p className="subtitle">O passageiro poderá escolher e gerenciar suas formas de pagamento.</p></div>}
        </>}
      </section>
    </div>
  </>
}
