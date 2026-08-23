'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type FeeMode = 'none' | 'fixed' | 'percentage'
type Settings = {
  target_franchise_id: string | null
  global_fee_mode: FeeMode
  global_fee_value: number | string
  allow_franchise_override: boolean
  override_exists: boolean
  override_fee_mode: FeeMode | null
  override_fee_value: number | string | null
  override_locked_by_matrix: boolean
  effective_fee_mode: FeeMode
  effective_fee_value: number | string
  effective_source: 'global' | 'franchise'
  can_edit: boolean
}

const box: React.CSSProperties = { background: '#141414', border: '1px solid #292929', borderRadius: 16, padding: 16 }
const field: React.CSSProperties = { background: '#0b0b0b', color: '#fff', border: '1px solid #333', borderRadius: 9, padding: '10px 11px' }
const button: React.CSSProperties = { background: '#ffd400', color: '#000', border: 0, borderRadius: 9, padding: '10px 14px', fontWeight: 900, cursor: 'pointer' }
const money = (value: unknown) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const describeRule = (mode: FeeMode, value: unknown) => mode === 'none' ? 'Sem taxa' : mode === 'percentage' ? `${Number(value || 0).toFixed(2)}% por corrida` : `${money(value)} por corrida`

export default function TaximeterFinancialSettings({ network = false }: { network?: boolean }) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [mode, setMode] = useState<FeeMode>('none')
  const [value, setValue] = useState('0')
  const [allowOverride, setAllowOverride] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => { void load() }, [])

  async function load() {
    setBusy(true)
    setMessage('')
    const { data, error } = await supabase.rpc('get_taximeter_financial_settings', { p_franchise_id: null })
    setBusy(false)
    if (error) {
      setMessage(error.message)
      return
    }

    const next = data as Settings
    setSettings(next)
    if (network) {
      setMode(next.global_fee_mode || 'none')
      setValue(String(next.global_fee_value || 0))
      setAllowOverride(next.allow_franchise_override !== false)
    } else {
      setMode((next.override_exists ? next.override_fee_mode : next.effective_fee_mode) || 'none')
      setValue(String(next.override_exists ? next.override_fee_value : next.effective_fee_value || 0))
      setAllowOverride(next.allow_franchise_override !== false)
    }
  }

  async function save() {
    if (!network && !settings?.can_edit) {
      setMessage('A matriz bloqueou alterações desta configuração.')
      return
    }

    const numericValue = mode === 'none' ? 0 : Number(value.replace(',', '.'))
    if (!Number.isFinite(numericValue) || numericValue < 0) {
      setMessage('Informe um valor válido.')
      return
    }
    if (mode === 'percentage' && numericValue > 100) {
      setMessage('O percentual deve ficar entre 0 e 100%.')
      return
    }

    setBusy(true)
    setMessage('Salvando configuração...')
    const { error } = await supabase.rpc('set_taximeter_financial_settings', {
      p_fee_mode: mode,
      p_fee_value: numericValue,
      p_scope: network ? 'global' : 'franchise',
      p_franchise_id: null,
      p_allow_franchise_override: network ? allowOverride : true,
      p_locked_by_matrix: false,
    })
    setBusy(false)

    if (error) {
      setMessage(error.message)
      return
    }

    setMessage(network ? 'Regra financeira da matriz atualizada.' : 'Regra financeira da franquia atualizada.')
    await load()
  }

  if (!settings && busy) return <div style={box}>Carregando configuração financeira do taxímetro…</div>

  const disabled = busy || (!network && !settings?.can_edit)
  const effectiveMode = settings?.effective_fee_mode || 'none'
  const effectiveValue = settings?.effective_fee_value || 0

  return <section style={{ ...box, borderColor: '#574900', marginBottom: 14 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'start', flexWrap: 'wrap' }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 950, color: '#ffd400' }}>FINANCEIRO DO TAXÍMETRO</div>
        <h2 style={{ margin: '4px 0 0' }}>Taxa das corridas livres</h2>
        <p style={{ color: '#9ca3af', fontSize: 13, margin: '6px 0 0' }}>
          {network
            ? 'Defina a regra padrão da rede. Começa sem cobrança e só passa a descontar depois que você configurar.'
            : 'A taxa é descontada da carteira operacional quando houver saldo; sem saldo, vira pendência e não bloqueia a corrida.'}
        </p>
      </div>
      <div style={{ padding: '8px 12px', border: '1px solid #333', borderRadius: 12, fontWeight: 900, color: '#ffd400' }}>
        Efetiva: {describeRule(effectiveMode, effectiveValue)}
      </div>
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(190px,1fr) minmax(150px,220px) auto', gap: 10, alignItems: 'end', marginTop: 14 }}>
      <label style={{ display: 'grid', gap: 5, fontSize: 12, color: '#9ca3af' }}>
        Modelo
        <select disabled={disabled} value={mode} onChange={event => setMode(event.target.value as FeeMode)} style={field}>
          <option value="none">Sem taxa</option>
          <option value="fixed">Valor fixo por corrida</option>
          <option value="percentage">Percentual da corrida</option>
        </select>
      </label>

      <label style={{ display: 'grid', gap: 5, fontSize: 12, color: '#9ca3af' }}>
        {mode === 'percentage' ? 'Percentual (%)' : 'Valor (R$)'}
        <input disabled={disabled || mode === 'none'} value={value} onChange={event => setValue(event.target.value)} inputMode="decimal" style={field} />
      </label>

      <button disabled={disabled} onClick={save} style={{ ...button, opacity: disabled ? 0.55 : 1 }}>
        {busy ? 'Salvando…' : 'Salvar regra'}
      </button>
    </div>

    {network ? (
      <label style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 12, fontSize: 13, color: '#d1d5db' }}>
        <input type="checkbox" checked={allowOverride} onChange={event => setAllowOverride(event.target.checked)} />
        <span>Permitir que cada franqueado defina sua própria taxa do taxímetro. Se desmarcado, prevalece a regra da matriz.</span>
      </label>
    ) : (
      <div style={{ marginTop: 12, fontSize: 12, color: settings?.can_edit ? '#9ca3af' : '#fbbf24' }}>
        {settings?.effective_source === 'franchise' ? 'A franquia está usando uma regra própria.' : 'A franquia está herdando a regra da matriz.'}
        {!settings?.can_edit ? ' A matriz bloqueou alterações locais.' : ''}
      </div>
    )}

    {message ? <div style={{ marginTop: 10, fontSize: 12, color: '#ffe66b' }}>{message}</div> : null}
  </section>
}
