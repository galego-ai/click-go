'use client'

import { useEffect, useMemo, useState } from 'react'
import { supabase } from '@/lib/supabase'

type FeeMode = 'fixed' | 'percentage'
type BillingMode = 'wallet_per_ride' | 'monthly'
type Driver = { id: string; status: string }
type Profile = { id: string; full_name: string | null; email: string | null }
type City = { id: string; name: string; state: string }
type CityAccess = { city_id: string }
type Billing = {
  driver_id: string
  billing_mode: BillingMode
  per_ride_fee: number | string
  ride_fee_mode: FeeMode | null
  ride_fee_percentage: number | string | null
  monthly_fee: number | string
  monthly_due_day: number
  monthly_paid_until: string | null
  active: boolean
}
type GlobalWallet = {
  enabled: boolean
  minimum_balance_to_receive: number | string
  low_balance_threshold: number | string
  default_ride_fee: number | string
  default_ride_fee_mode: FeeMode
  default_ride_fee_percentage: number | string
  franchise_can_set_ride_fee: boolean
  cash_negative_limit: number | string
}
type LocalWallet = {
  franchise_id: string
  ride_fee: number | string | null
  ride_fee_mode: FeeMode | null
  ride_fee_percentage: number | string | null
  minimum_balance_to_receive: number | string | null
  low_balance_threshold: number | string | null
  locked_by_matrix: boolean
}
type CityWallet = {
  franchise_id: string
  city_id: string
  cash_negative_limit: number | string
  locked_by_matrix: boolean
}

const box: React.CSSProperties = { background: '#141414', border: '1px solid #292929', borderRadius: 16, padding: 18 }
const input: React.CSSProperties = { width: '100%', background: '#0d0d0d', color: '#fff', border: '1px solid #333', borderRadius: 10, padding: '10px 11px' }
const btn: React.CSSProperties = { background: '#ffd400', color: '#000', border: 0, borderRadius: 9, padding: '10px 13px', fontWeight: 800, cursor: 'pointer' }
const money = (value: unknown) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const num = (value: string) => Number(value.replace(',', '.')) || 0
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export default function FranchiseFeesPage() {
  const [fid, setFid] = useState('')
  const [cities, setCities] = useState<City[]>([])
  const [selectedCity, setSelectedCity] = useState('')
  const [cityWallet, setCityWallet] = useState<CityWallet | null>(null)
  const [cashLimit, setCashLimit] = useState('0')
  const [drivers, setDrivers] = useState<Driver[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [billings, setBillings] = useState<Billing[]>([])
  const [globalWallet, setGlobalWallet] = useState<GlobalWallet | null>(null)
  const [localWallet, setLocalWallet] = useState<LocalWallet | null>(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const [franchiseForm, setFranchiseForm] = useState({ mode: 'fixed' as FeeMode, fixed: '0', percentage: '0', minimum: '0.01', low: '5' })
  const [driverForm, setDriverForm] = useState({ billingMode: 'wallet_per_ride' as BillingMode, feeMode: 'fixed' as FeeMode, fixed: '0', percentage: '0', monthly: '0', dueDay: '10' })

  useEffect(() => { void loadBase() }, [])
  useEffect(() => { if (fid && selectedCity) void loadCity(selectedCity) }, [fid, selectedCity])
  useEffect(() => { if (selected) applyDriver(selected) }, [selected, billings, franchiseForm.mode, franchiseForm.fixed, franchiseForm.percentage])

  async function loadBase() {
    setBusy(true)
    setMsg('')
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('Faça login.')
      const { data: profile, error: profileError } = await supabase.from('profiles').select('role,franchise_id').eq('id', user.id).single()
      if (profileError) throw profileError
      if (profile?.role !== 'franchise_admin' || !profile.franchise_id) throw new Error('Acesso exclusivo do franqueado.')

      const franchiseId = profile.franchise_id as string
      setFid(franchiseId)

      const [{ data: globalData, error: globalError }, { data: localData, error: localError }, { data: access, error: accessError }] = await Promise.all([
        supabase.from('platform_operational_wallet_settings').select('enabled,minimum_balance_to_receive,low_balance_threshold,default_ride_fee,default_ride_fee_mode,default_ride_fee_percentage,franchise_can_set_ride_fee,cash_negative_limit').eq('scope', 'global').single(),
        supabase.from('franchise_operational_wallet_settings').select('franchise_id,ride_fee,ride_fee_mode,ride_fee_percentage,minimum_balance_to_receive,low_balance_threshold,locked_by_matrix').eq('franchise_id', franchiseId).maybeSingle(),
        supabase.from('profile_city_access').select('city_id').eq('profile_id', user.id),
      ])
      if (globalError) throw globalError
      if (localError) throw localError
      if (accessError) throw accessError

      const cityIds = ((access ?? []) as CityAccess[]).map((item) => item.city_id)
      if (cityIds.length === 0) throw new Error('Nenhuma cidade foi liberada para este administrador regional.')
      const { data: cityData, error: cityError } = await supabase.from('cities').select('id,name,state').in('id', cityIds).order('name')
      if (cityError) throw cityError

      const nextGlobal = globalData as GlobalWallet
      const nextLocal = (localData || null) as LocalWallet | null
      const nextCities = (cityData ?? []) as City[]
      setGlobalWallet(nextGlobal)
      setLocalWallet(nextLocal)
      setCities(nextCities)

      const mode = (nextLocal?.ride_fee_mode || nextGlobal.default_ride_fee_mode || 'fixed') as FeeMode
      setFranchiseForm({
        mode,
        fixed: String(nextLocal?.ride_fee ?? nextGlobal.default_ride_fee ?? 0),
        percentage: String(nextLocal?.ride_fee_percentage ?? nextGlobal.default_ride_fee_percentage ?? 0),
        minimum: String(nextLocal?.minimum_balance_to_receive ?? nextGlobal.minimum_balance_to_receive ?? 0.01),
        low: String(nextLocal?.low_balance_threshold ?? nextGlobal.low_balance_threshold ?? 5),
      })
      if (nextCities[0]) setSelectedCity(nextCities[0].id)
    } catch (error: unknown) {
      setMsg(errorMessage(error, 'Erro ao carregar taxas.'))
    } finally {
      setBusy(false)
    }
  }

  async function loadCity(cityId: string) {
    setBusy(true)
    setMsg('')
    try {
      const [{ data: driverData, error: driverError }, { data: walletData, error: walletError }] = await Promise.all([
        supabase.from('drivers').select('id,status').eq('franchise_id', fid).eq('city_id', cityId).order('created_at', { ascending: false }),
        supabase.from('city_operational_wallet_settings').select('franchise_id,city_id,cash_negative_limit,locked_by_matrix').eq('franchise_id', fid).eq('city_id', cityId).maybeSingle(),
      ])
      if (driverError) throw driverError
      if (walletError) throw walletError

      const nextDrivers = (driverData ?? []) as Driver[]
      const ids = nextDrivers.map((driver) => driver.id)
      const [profilesResult, billingResult] = ids.length > 0
        ? await Promise.all([
            supabase.from('profiles').select('id,full_name,email').in('id', ids),
            supabase.from('driver_billing_settings').select('driver_id,billing_mode,per_ride_fee,ride_fee_mode,ride_fee_percentage,monthly_fee,monthly_due_day,monthly_paid_until,active').in('driver_id', ids),
          ])
        : [{ data: [], error: null }, { data: [], error: null }]

      if (profilesResult.error) throw profilesResult.error
      if (billingResult.error) throw billingResult.error

      const nextCityWallet = (walletData || null) as CityWallet | null
      setDrivers(nextDrivers)
      setProfiles((profilesResult.data ?? []) as Profile[])
      setBillings((billingResult.data ?? []) as Billing[])
      setCityWallet(nextCityWallet)
      setCashLimit(String(nextCityWallet?.cash_negative_limit ?? globalWallet?.cash_negative_limit ?? 0))
      setSelected(ids[0] || '')
    } catch (error: unknown) {
      setMsg(errorMessage(error, 'Erro ao carregar a cidade.'))
    } finally {
      setBusy(false)
    }
  }

  const names = useMemo(() => Object.fromEntries(profiles.map((profile) => [profile.id, profile])), [profiles])
  function billing(id: string) { return billings.find((item) => item.driver_id === id) }
  function applyDriver(id: string) {
    const current = billing(id)
    setDriverForm({
      billingMode: current?.billing_mode || 'wallet_per_ride',
      feeMode: (current?.ride_fee_mode || franchiseForm.mode || 'fixed') as FeeMode,
      fixed: String(current?.per_ride_fee ?? franchiseForm.fixed ?? 0),
      percentage: String(current?.ride_fee_percentage ?? franchiseForm.percentage ?? 0),
      monthly: String(current?.monthly_fee ?? 0),
      dueDay: String(current?.monthly_due_day ?? 10),
    })
  }

  async function saveFranchise() {
    if (!fid || !globalWallet) return
    if (localWallet?.locked_by_matrix) { setMsg('A Matriz bloqueou as regras da carteira desta franquia.'); return }
    if (!globalWallet.franchise_can_set_ride_fee) { setMsg('A Matriz não permite alterar o tipo/valor da taxa.'); return }
    const percentage = num(franchiseForm.percentage)
    if (franchiseForm.mode === 'percentage' && (percentage < 0 || percentage > 100)) { setMsg('O percentual deve ficar entre 0% e 100%.'); return }

    setBusy(true)
    const { error } = await supabase.from('franchise_operational_wallet_settings').upsert({
      franchise_id: fid,
      ride_fee_mode: franchiseForm.mode,
      ride_fee: num(franchiseForm.fixed),
      ride_fee_percentage: percentage,
      minimum_balance_to_receive: num(franchiseForm.minimum),
      low_balance_threshold: num(franchiseForm.low),
      locked_by_matrix: false,
      updated_at: new Date().toISOString(),
    }, { onConflict: 'franchise_id' })
    setBusy(false)
    if (error) { setMsg(error.message); return }
    setMsg(franchiseForm.mode === 'percentage' ? `Regra da franquia salva: ${percentage.toLocaleString('pt-BR')}% do valor da corrida.` : `Regra da franquia salva: ${money(num(franchiseForm.fixed))} por corrida.`)
    await loadBase()
  }

  async function saveCashLimit() {
    if (!fid || !selectedCity) return
    const limit = num(cashLimit)
    if (limit > 0 || limit < -1000) {
      setMsg('O limite deve ficar entre R$ 0,00 e -R$ 1.000,00.')
      return
    }
    if (cityWallet?.locked_by_matrix) {
      setMsg('A Matriz bloqueou o limite desta cidade.')
      return
    }

    setBusy(true)
    const { error } = await supabase.rpc('set_city_cash_negative_limit', {
      p_franchise_id: fid,
      p_city_id: selectedCity,
      p_cash_negative_limit: limit,
    })
    setBusy(false)
    if (error) { setMsg(error.message); return }
    setMsg(`Limite para corridas em dinheiro salvo em ${money(limit)}. Ao atingir esse saldo, dinheiro é bloqueado; PIX e Cartão continuam liberados.`)
    await loadCity(selectedCity)
  }

  async function saveDriver() {
    if (!selected) return
    const percentage = num(driverForm.percentage)
    if (driverForm.feeMode === 'percentage' && (percentage < 0 || percentage > 100)) { setMsg('O percentual deve ficar entre 0% e 100%.'); return }
    setBusy(true)
    const { error } = await supabase.rpc('set_driver_billing', {
      p_driver_id: selected,
      p_billing_mode: driverForm.billingMode,
      p_per_ride_fee: num(driverForm.fixed),
      p_monthly_fee: num(driverForm.monthly),
      p_monthly_due_day: Math.max(1, Math.min(28, Number(driverForm.dueDay) || 10)),
      p_ride_fee_mode: driverForm.feeMode,
      p_ride_fee_percentage: percentage,
    })
    setBusy(false)
    if (error) { setMsg(error.message); return }
    if (driverForm.billingMode === 'monthly') setMsg(`Motorista configurado com mensalidade de ${money(num(driverForm.monthly))}.`)
    else if (driverForm.feeMode === 'percentage') setMsg(`Motorista configurado com desconto de ${percentage.toLocaleString('pt-BR')}% por corrida.`)
    else setMsg(`Motorista configurado com desconto fixo de ${money(num(driverForm.fixed))} por corrida.`)
    await loadCity(selectedCity)
  }

  const current = drivers.find((driver) => driver.id === selected)
  const profile = current ? names[current.id] : null
  const exampleFare = 40
  const exampleFee = driverForm.feeMode === 'percentage' ? exampleFare * num(driverForm.percentage) / 100 : num(driverForm.fixed)
  const controlsLocked = Boolean(localWallet?.locked_by_matrix) || !globalWallet?.franchise_can_set_ride_fee
  const selectedCityData = cities.find((city) => city.id === selectedCity)

  return <main style={{ minHeight: '100vh', background: '#080808', color: '#fff', padding: 20 }}><div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gap: 14 }}>
    <div><div className="eyebrow">Painel Regional</div><h1>Taxas e carteira do motorista</h1><p className="subtitle">Configurações financeiras isoladas por operação. O limite negativo abaixo bloqueia somente corridas em dinheiro — o motorista permanece online para PIX e Cartão.</p></div>

    <section style={{ ...box, display: 'flex', gap: 14, alignItems: 'end', flexWrap: 'wrap' }}>
      <label style={{ minWidth: 280 }}>Cidade da operação<select style={input} value={selectedCity} onChange={(event) => setSelectedCity(event.target.value)}>{cities.map((city) => <option key={city.id} value={city.id}>{city.name} / {city.state}</option>)}</select></label>
      <div style={{ color: '#9ca3af', paddingBottom: 10 }}>Escopo atual: <b style={{ color: '#fff' }}>{selectedCityData ? `${selectedCityData.name}/${selectedCityData.state}` : '—'}</b></div>
    </section>

    <section style={{ ...box, borderColor: '#92400e' }}>
      <div className="eyebrow">Carteira operacional · cidade</div>
      <h2>Limite negativo para corridas em dinheiro</h2>
      <p style={{ color: '#d1d5db', lineHeight: 1.55 }}>Exemplo: com <b>-R$ 10,00</b>, o motorista continua recebendo dinheiro enquanto estiver acima de -R$ 10,00. Ao atingir -R$ 10,00, novas corridas em dinheiro são bloqueadas. <b style={{ color: '#86efac' }}>PIX e Cartão continuam LIBERADOS.</b></p>
      {cityWallet?.locked_by_matrix && <p style={{ color: '#fbbf24' }}>A Matriz bloqueou esta configuração.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px,360px) auto', gap: 10, alignItems: 'end' }}>
        <label>cash_negative_limit<input type="number" max="0" min="-1000" step="0.01" style={input} value={cashLimit} disabled={busy || Boolean(cityWallet?.locked_by_matrix)} onChange={(event) => setCashLimit(event.target.value)} /></label>
        <button style={btn} disabled={busy || Boolean(cityWallet?.locked_by_matrix)} onClick={saveCashLimit}>Salvar limite da cidade</button>
      </div>
      <div style={{ color: '#9ca3af', fontSize: 13, marginTop: 9 }}>R$ 0,00 = bloqueia dinheiro ao zerar. Valores negativos permitem uma tolerância de saldo.</div>
    </section>

    <section style={{ ...box, borderColor: '#665600' }}><h2>Regra padrão da franquia</h2>{localWallet?.locked_by_matrix && <p style={{ color: '#fbbf24' }}>Esta regra foi bloqueada pela Matriz.</p>}{globalWallet && !globalWallet.franchise_can_set_ride_fee && <p style={{ color: '#fbbf24' }}>Tipo e valor da taxa são definidos somente pela Matriz.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 10 }}>
        <label>Forma da taxa<select style={input} value={franchiseForm.mode} disabled={controlsLocked} onChange={(event) => setFranchiseForm({ ...franchiseForm, mode: event.target.value as FeeMode })}><option value="fixed">R$ fixo por corrida</option><option value="percentage">% sobre a corrida</option></select></label>
        {franchiseForm.mode === 'fixed' ? <label>Valor em R$<input type="number" min="0" step="0.01" style={input} value={franchiseForm.fixed} disabled={controlsLocked} onChange={(event) => setFranchiseForm({ ...franchiseForm, fixed: event.target.value })} /></label> : <label>Percentual (%)<input type="number" min="0" max="100" step="0.01" style={input} value={franchiseForm.percentage} disabled={controlsLocked} onChange={(event) => setFranchiseForm({ ...franchiseForm, percentage: event.target.value })} /></label>}
        <label>Alerta de saldo baixo<input type="number" min="0" step="0.01" style={input} value={franchiseForm.low} disabled={Boolean(localWallet?.locked_by_matrix)} onChange={(event) => setFranchiseForm({ ...franchiseForm, low: event.target.value })} /></label>
      </div><button style={{ ...btn, marginTop: 12 }} disabled={busy || Boolean(localWallet?.locked_by_matrix)} onClick={saveFranchise}>Salvar regra da franquia</button>
    </section>

    <div style={{ display: 'grid', gridTemplateColumns: '340px minmax(0,1fr)', gap: 14 }}>
      <aside style={box}><h2>Motoristas desta cidade</h2><div style={{ display: 'grid', gap: 8, maxHeight: 650, overflow: 'auto' }}>{drivers.map((driver) => <button key={driver.id} onClick={() => setSelected(driver.id)} style={{ ...box, textAlign: 'left', color: '#fff', cursor: 'pointer', outline: selected === driver.id ? '2px solid #ffd400' : 'none' }}><b>{names[driver.id]?.full_name || names[driver.id]?.email || driver.id.slice(0, 8)}</b><div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>Cadastro: {driver.status}</div>{billing(driver.id) && <div style={{ color: '#fde68a', fontSize: 12, marginTop: 3 }}>{billing(driver.id)?.billing_mode === 'monthly' ? `Mensal ${money(billing(driver.id)?.monthly_fee)}` : billing(driver.id)?.ride_fee_mode === 'percentage' ? `${Number(billing(driver.id)?.ride_fee_percentage || 0).toLocaleString('pt-BR')}% por corrida` : `${money(billing(driver.id)?.per_ride_fee)} por corrida`}</div>}</button>)}{!drivers.length && <div style={{ color: '#9ca3af' }}>Nenhum motorista cadastrado nesta cidade.</div>}</div></aside>

      <section style={{ display: 'grid', gap: 14 }}>{current ? <><div style={box}><div className="label">Motorista selecionado</div><h2>{profile?.full_name || profile?.email || current.id}</h2><div style={{ color: '#9ca3af' }}>A configuração individual substitui o padrão da franquia para este motorista.</div></div>
        <div style={box}><h3>Modelo de cobrança</h3><div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 10 }}><label>Modelo<select style={input} value={driverForm.billingMode} onChange={(event) => setDriverForm({ ...driverForm, billingMode: event.target.value as BillingMode })}><option value="wallet_per_ride">Carteira operacional</option><option value="monthly">Mensalidade fixa</option></select></label>
          {driverForm.billingMode === 'wallet_per_ride' ? <><label>Tipo da taxa<select style={input} value={driverForm.feeMode} onChange={(event) => setDriverForm({ ...driverForm, feeMode: event.target.value as FeeMode })}><option value="fixed">R$ fixo</option><option value="percentage">Percentual (%)</option></select></label>{driverForm.feeMode === 'fixed' ? <label>Valor por corrida<input type="number" min="0" step="0.01" style={input} value={driverForm.fixed} onChange={(event) => setDriverForm({ ...driverForm, fixed: event.target.value })} /></label> : <label>Percentual por corrida<input type="number" min="0" max="100" step="0.01" style={input} value={driverForm.percentage} onChange={(event) => setDriverForm({ ...driverForm, percentage: event.target.value })} /></label>}</> : <><label>Mensalidade<input type="number" min="0" step="0.01" style={input} value={driverForm.monthly} onChange={(event) => setDriverForm({ ...driverForm, monthly: event.target.value })} /></label><label>Vencimento (dia)<input type="number" min="1" max="28" style={input} value={driverForm.dueDay} onChange={(event) => setDriverForm({ ...driverForm, dueDay: event.target.value })} /></label></>}</div>
          {driverForm.billingMode === 'wallet_per_ride' && <div style={{ marginTop: 12, padding: 12, borderRadius: 12, background: '#0d0d0d', color: '#d1d5db' }}>Exemplo em uma corrida de <b>{money(exampleFare)}</b>: desconto operacional <b style={{ color: '#ffd400' }}>{money(exampleFee)}</b>. O limite de dinheiro é controlado separadamente por cidade.</div>}
          <button style={{ ...btn, marginTop: 12 }} disabled={busy} onClick={saveDriver}>Salvar configuração do motorista</button>
        </div></> : <div style={box}>Selecione um motorista.</div>}</section>
    </div>
    {msg && <div style={{ ...box, borderColor: '#665600', color: '#ffe66b' }}>{msg}</div>}
  </div></main>
}
