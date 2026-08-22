'use client'

import { FormEvent, useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type City = { id: string; name: string; state: string }
const menu = ['Início', 'Corridas', 'Ganhos', 'Carteira', 'Documentos', 'Meu veículo', 'Avaliações', 'Ajuda e suporte', 'Meu perfil']

export default function DriverAppPage() {
  const [cities, setCities] = useState<City[]>([])
  const [active, setActive] = useState('Início')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    supabase.from('cities').select('id,name,state').eq('active', true).order('name').then(({data}) => setCities((data || []) as City[]))
  }, [])

  async function register(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    const data = new FormData(e.currentTarget)
    const { error } = await supabase.auth.signUp({
      email: String(data.get('email') || '').trim(),
      password: String(data.get('password') || ''),
      options: {
        data: {
          app_role: 'driver',
          requested_city_id: String(data.get('city_id') || ''),
          full_name: String(data.get('full_name') || '').trim(),
          phone: String(data.get('phone') || '').trim(),
          cpf: String(data.get('cpf') || '').trim(),
          cnh_number: String(data.get('cnh_number') || '').trim(),
          cnh_category: String(data.get('cnh_category') || '').trim(),
          vehicle_plate: String(data.get('vehicle_plate') || '').trim(),
          vehicle_make: String(data.get('vehicle_make') || '').trim(),
          vehicle_model: String(data.get('vehicle_model') || '').trim(),
          vehicle_year: String(data.get('vehicle_year') || '').trim(),
          vehicle_color: String(data.get('vehicle_color') || '').trim(),
          vehicle_type: String(data.get('vehicle_type') || '').trim(),
        },
      },
    })
    setLoading(false)
    setMessage(error ? error.message : 'Cadastro enviado. Após confirmar o e-mail, aguarde a aprovação do franqueado da cidade escolhida.')
  }

  return <>
    <div className="topbar"><div><div className="eyebrow">App Motorista</div><h1 className="title">CLICK-GO Motorista</h1><p className="subtitle">O motorista escolhe a cidade e fica pendente até o franqueado aprovar.</p></div></div>
    <div style={{display:'grid',gridTemplateColumns:'230px 1fr',gap:16,alignItems:'start'}}>
      <aside className="card" style={{padding:10}}>
        {menu.map(item => <button key={item} onClick={() => setActive(item)} style={{display:'block',width:'100%',textAlign:'left',padding:'12px',marginBottom:6,border:0,borderRadius:10,cursor:'pointer',fontWeight:700,background:active===item?'#ffd400':'#1d1d1d',color:active===item?'#000':'#fff'}}>{item}</button>)}
      </aside>
      <section className="card">
        <div className="eyebrow">{active}</div>
        {active === 'Início' ? <>
          <h2>Cadastro do motorista</h2>
          <p className="subtitle" style={{marginBottom:18}}>Escolha a cidade onde deseja trabalhar. O sistema vincula o cadastro automaticamente à franquia responsável por essa cidade.</p>
          <form onSubmit={register} style={{display:'grid',gap:12,maxWidth:620}}>
            <select name="city_id" required className="form-input" defaultValue=""><option value="" disabled>Escolha a cidade de atuação</option>{cities.map(c => <option key={c.id} value={c.id}>{c.name} - {c.state}</option>)}</select>
            <input name="full_name" required placeholder="Nome completo" className="form-input" />
            <input name="phone" required placeholder="Telefone / WhatsApp" className="form-input" />
            <input name="cpf" required placeholder="CPF" className="form-input" />
            <input name="cnh_number" required placeholder="Número da CNH" className="form-input" />
            <input name="cnh_category" required placeholder="Categoria da CNH" className="form-input" />
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_plate" required placeholder="Placa" className="form-input" /><input name="vehicle_type" placeholder="Tipo do veículo" className="form-input" /></div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_make" placeholder="Marca" className="form-input" /><input name="vehicle_model" placeholder="Modelo" className="form-input" /></div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_year" type="number" placeholder="Ano" className="form-input" /><input name="vehicle_color" placeholder="Cor" className="form-input" /></div>
            <input name="email" required type="email" placeholder="E-mail" className="form-input" />
            <input name="password" required type="password" minLength={6} placeholder="Senha" className="form-input" />
            <button className="button" disabled={loading}>{loading ? 'Enviando...' : 'Enviar cadastro para aprovação'}</button>
          </form>
          {message && <p style={{marginTop:14}}>{message}</p>}
        </> : <><h2>{active}</h2><p className="subtitle">Área do motorista. Enquanto o cadastro estiver pendente, o motorista não poderá ficar online nem receber corridas.</p></>}
      </section>
    </div>
  </>
}
