'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import type { LayerGroup, Map as LeafletMap } from 'leaflet'
import type { RealtimeChannel } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { distanceMeters } from '@/lib/geo'
import {
  cityDriverLocationsTopic,
  rideDriverLocationTopic,
  type DriverLocationBroadcast,
} from '@/lib/realtime-gps'
import DriverRideSafety from '@/components/DriverRideSafety'
import 'leaflet/dist/leaflet.css'

type Driver = {
  id: string
  status: string
  online: boolean
  rating: number | string
  city_id: string | null
  franchise_id: string | null
}

type Profile = { id: string; full_name: string | null; email: string | null; role: string }
type Offer = {
  offer_id: string
  ride_id: string
  distance_to_pickup_km: number | string
  eta_to_pickup_min: number
  estimated_driver_earning: number | string
  origin_label: string
  origin_lat: number
  origin_lng: number
  destination_label: string
  destination_lat: number
  destination_lng: number
  category_name: string | null
}
type Ride = {
  id: string
  status: string
  origin_label: string
  origin_lat: number
  origin_lng: number
  destination_label: string
  destination_lat: number
  destination_lng: number
  estimated_fare: number | string | null
  final_fare: number | string | null
  payment_method_preference: string | null
  accepted_at: string | null
  arrived_at: string | null
  started_at: string | null
  wait_free_seconds: number
  wait_fee_per_minute: number | string
  wait_charge_amount: number | string
}
type Location = { lat: number; lng: number; heading: number | null; speed: number | null }
type WalletSummary = {
  operational_balance: number | string
  earnings_balance: number | string
  minimum_balance: number | string
  low_balance_threshold: number | string
  ride_fee: number | string
  operational_enabled: boolean
  billing_mode: 'wallet_per_ride' | 'monthly'
  monthly_fee: number | string
  monthly_due_day: number
  monthly_paid_until: string | null
  cash_negative_limit: number | string
  cash_allowed: boolean
}
type SettlementNotice = {
  method: string
  commission: number
  rideFee: number
  cancellationCollection: number
  balance: number | null
}
type OfferResponse = { accepted?: boolean; reason?: string }
type AdvanceResult = {
  wait_charge_amount?: number | string
  direct_collection_commission_debit?: number | string
  per_ride_fee_debit?: number | string
  cancellation_collection_debit?: number | string
  operational_balance_after?: number | string | null
  status?: string
}

type PersistedPoint = { lat: number; lng: number }

const box: React.CSSProperties = { background: '#141414', border: '1px solid #292929', borderRadius: 16, padding: 18 }
const btn: React.CSSProperties = { background: '#ffd400', color: '#000', border: 0, borderRadius: 10, padding: '11px 14px', fontWeight: 800, cursor: 'pointer' }
const money = (value: unknown) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const clock = (seconds: number) => `${Math.floor(Math.max(0, seconds) / 60).toString().padStart(2, '0')}:${Math.floor(Math.max(0, seconds) % 60).toString().padStart(2, '0')}`
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export default function DriverOperationPage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [driver, setDriver] = useState<Driver | null>(null)
  const [offers, setOffers] = useState<Offer[]>([])
  const [ride, setRide] = useState<Ride | null>(null)
  const [location, setLocation] = useState<Location | null>(null)
  const [wallet, setWallet] = useState<WalletSummary | null>(null)
  const [machinePaid, setMachinePaid] = useState(false)
  const [settlement, setSettlement] = useState<SettlementNotice | null>(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [now, setNow] = useState(Date.now())
  const [showMoney, setShowMoney] = useState(true)

  const watchRef = useRef<number | null>(null)
  const mapEl = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<LeafletMap | null>(null)
  const layerRef = useRef<LayerGroup | null>(null)
  const cityGpsChannelRef = useRef<RealtimeChannel | null>(null)
  const rideGpsChannelRef = useRef<RealtimeChannel | null>(null)
  const cityGpsReadyRef = useRef(false)
  const rideGpsReadyRef = useRef(false)
  const lastBroadcastAtRef = useRef(0)
  const lastBroadcastPointRef = useRef<PersistedPoint | null>(null)
  const lastPersistedAtRef = useRef(0)
  const lastPersistedPointRef = useRef<PersistedPoint | null>(null)

  useEffect(() => {
    const saved = window.localStorage.getItem('clickgo-driver-show-money')
    if (saved === '0') setShowMoney(false)
    void load()
    return () => {
      if (watchRef.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchRef.current)
    }
  }, [])

  useEffect(() => {
    if (ride?.status !== 'driver_arriving') return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [ride?.status, ride?.arrived_at])

  useEffect(() => {
    if (!profile) return
    const offersChannel = supabase
      .channel(`driver-offers-${profile.id}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'ride_offers', filter: `driver_id=eq.${profile.id}` }, () => { void loadOffers() })
      .subscribe()
    const ridesChannel = supabase
      .channel(`driver-rides-${profile.id}`)
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'rides', filter: `driver_id=eq.${profile.id}` }, () => { void loadCurrentRide() })
      .subscribe()
    return () => {
      void supabase.removeChannel(offersChannel)
      void supabase.removeChannel(ridesChannel)
    }
  }, [profile?.id])

  useEffect(() => {
    cityGpsReadyRef.current = false
    const old = cityGpsChannelRef.current
    cityGpsChannelRef.current = null
    if (old) void supabase.removeChannel(old)
    if (!driver?.online || !driver.city_id) return

    let cancelled = false
    void (async () => {
      await supabase.realtime.setAuth()
      if (cancelled) return
      const channel = supabase.channel(cityDriverLocationsTopic(driver.city_id as string), { config: { private: true } })
      cityGpsChannelRef.current = channel
      channel.subscribe((status) => {
        cityGpsReadyRef.current = status === 'SUBSCRIBED'
      })
    })()

    return () => {
      cancelled = true
      cityGpsReadyRef.current = false
      const channel = cityGpsChannelRef.current
      cityGpsChannelRef.current = null
      if (channel) void supabase.removeChannel(channel)
    }
  }, [driver?.online, driver?.city_id])

  useEffect(() => {
    rideGpsReadyRef.current = false
    const old = rideGpsChannelRef.current
    rideGpsChannelRef.current = null
    if (old) void supabase.removeChannel(old)
    if (!ride?.id) return

    let cancelled = false
    void (async () => {
      await supabase.realtime.setAuth()
      if (cancelled) return
      const channel = supabase.channel(rideDriverLocationTopic(ride.id), { config: { private: true } })
      rideGpsChannelRef.current = channel
      channel.subscribe((status) => {
        rideGpsReadyRef.current = status === 'SUBSCRIBED'
      })
    })()

    return () => {
      cancelled = true
      rideGpsReadyRef.current = false
      const channel = rideGpsChannelRef.current
      rideGpsChannelRef.current = null
      if (channel) void supabase.removeChannel(channel)
    }
  }, [ride?.id])

  useEffect(() => {
    let alive = true
    void (async () => {
      if (!mapEl.current) return
      const L = await import('leaflet')
      if (!alive || !mapEl.current) return
      if (!mapRef.current) {
        mapRef.current = L.map(mapEl.current).setView([-14.52472, -49.14083], 13)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }).addTo(mapRef.current)
        layerRef.current = L.layerGroup().addTo(mapRef.current)
      }
      const layer = layerRef.current
      const map = mapRef.current
      if (!layer || !map) return
      layer.clearLayers()
      const points: [number, number][] = []
      if (location) {
        L.circleMarker([location.lat, location.lng], { radius: 8 }).bindTooltip('Você').addTo(layer)
        points.push([location.lat, location.lng])
      }
      const target = ride || offers[0]
      if (target) {
        L.circleMarker([target.origin_lat, target.origin_lng], { radius: 8 }).bindTooltip('Passageiro / embarque').addTo(layer)
        L.circleMarker([target.destination_lat, target.destination_lng], { radius: 8 }).bindTooltip('Destino').addTo(layer)
        L.polyline([[target.origin_lat, target.origin_lng], [target.destination_lat, target.destination_lng]]).addTo(layer)
        points.push([target.origin_lat, target.origin_lng], [target.destination_lat, target.destination_lng])
      }
      if (points.length > 1) map.fitBounds(points, { padding: [35, 35] })
      else if (points.length === 1) map.setView(points[0], 15)
    })()
    return () => { alive = false }
  }, [location, ride, offers])

  useEffect(() => () => {
    mapRef.current?.remove()
    mapRef.current = null
  }, [])

  async function load() {
    setBusy(true)
    setMsg('')
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return
      const { data: profileData, error: profileError } = await supabase.from('profiles').select('id,full_name,email,role').eq('id', user.id).single()
      if (profileError) throw profileError
      if (!profileData || profileData.role !== 'driver') throw new Error('Esta área é exclusiva do motorista.')
      const { data: driverData, error: driverError } = await supabase.from('drivers').select('id,status,online,rating,city_id,franchise_id').eq('id', user.id).single()
      if (driverError) throw driverError
      setProfile(profileData as Profile)
      setDriver(driverData as Driver)
      await Promise.all([loadOffers(), loadCurrentRide(), loadWallet()])
      if (driverData.online) startLocationWatch(false)
    } catch (error: unknown) {
      setMsg(errorMessage(error, 'Erro ao carregar operação.'))
    } finally {
      setBusy(false)
    }
  }

  async function loadOffers() {
    const { data, error } = await supabase.rpc('get_driver_pending_offers')
    if (!error) setOffers((data || []) as Offer[])
  }

  async function loadCurrentRide() {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return
    const { data, error } = await supabase
      .from('rides')
      .select('id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,payment_method_preference,accepted_at,arrived_at,started_at,wait_free_seconds,wait_fee_per_minute,wait_charge_amount')
      .eq('driver_id', user.id)
      .in('status', ['accepted', 'driver_arriving', 'in_progress'])
      .order('accepted_at', { ascending: false })
      .limit(1)
      .maybeSingle()
    if (error) return
    const currentRide = (data || null) as Ride | null
    setRide(currentRide)
    if (currentRide?.payment_method_preference === 'card_machine') {
      const { data: payment } = await supabase.from('payments').select('id').eq('ride_id', currentRide.id).eq('method', 'card_machine').eq('status', 'paid').limit(1).maybeSingle()
      setMachinePaid(Boolean(payment))
    } else setMachinePaid(false)
  }

  async function loadWallet() {
    const { data, error } = await supabase.rpc('get_my_driver_wallet_summary_v2')
    if (!error) setWallet((data?.[0] || null) as WalletSummary | null)
  }

  function getPosition(): Promise<GeolocationPosition> {
    return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 15_000, maximumAge: 5_000 }))
  }

  function toggleMoney() {
    setShowMoney((visible) => {
      const next = !visible
      window.localStorage.setItem('clickgo-driver-show-money', next ? '1' : '0')
      return next
    })
  }

  function shownMoney(value: unknown) { return showMoney ? money(value) : 'R$ ••••' }

  async function toggleOnline() {
    if (!driver) return
    if (driver.status !== 'approved') {
      setMsg('O franqueado precisa aprovar seu cadastro antes de você ficar online.')
      return
    }
    if (driver.online) {
      setBusy(true)
      const { error } = await supabase.rpc('set_driver_online', { p_online: false, p_lat: null, p_lng: null })
      setBusy(false)
      if (error) { setMsg(error.message); return }
      if (watchRef.current !== null) {
        navigator.geolocation.clearWatch(watchRef.current)
        watchRef.current = null
      }
      setDriver({ ...driver, online: false })
      setOffers([])
      setMsg('Você está offline.')
      return
    }
    if (!navigator.geolocation) {
      setMsg('Seu aparelho não disponibiliza GPS.')
      return
    }

    setBusy(true)
    try {
      const pos = await getPosition()
      const nextLocation: Location = { lat: pos.coords.latitude, lng: pos.coords.longitude, heading: pos.coords.heading, speed: pos.coords.speed }
      const { error } = await supabase.rpc('set_driver_online', { p_online: true, p_lat: nextLocation.lat, p_lng: nextLocation.lng })
      if (error) throw error
      setLocation(nextLocation)
      setDriver({ ...driver, online: true })
      lastPersistedAtRef.current = Date.now()
      lastPersistedPointRef.current = nextLocation
      startLocationWatch(true)
      setMsg('Você está online e pode receber chamadas.')
      await Promise.all([loadOffers(), loadWallet()])
    } catch (error: unknown) {
      setMsg(wallet?.billing_mode === 'monthly'
        ? 'Não foi possível ficar online. Verifique sua mensalidade, GPS e aprovação do cadastro.'
        : errorMessage(error, 'Não foi possível ficar online. Verifique o GPS e a aprovação do cadastro.'))
    } finally {
      setBusy(false)
    }
  }

  async function broadcastLocation(nextLocation: Location, force: boolean) {
    if (!profile) return
    const nowMs = Date.now()
    const previous = lastBroadcastPointRef.current
    const moved = previous ? distanceMeters(previous, nextLocation) : Number.POSITIVE_INFINITY

    if (!force && (nowMs - lastBroadcastAtRef.current < 3_000 || moved < 10)) return

    const payload: DriverLocationBroadcast = {
      driver_id: profile.id,
      lat: nextLocation.lat,
      lng: nextLocation.lng,
      heading: nextLocation.heading,
      speed_kmh: nextLocation.speed == null ? null : nextLocation.speed * 3.6,
      updated_at: new Date().toISOString(),
    }

    lastBroadcastAtRef.current = nowMs
    lastBroadcastPointRef.current = nextLocation

    const sends: Promise<unknown>[] = []
    if (cityGpsReadyRef.current && cityGpsChannelRef.current) {
      sends.push(cityGpsChannelRef.current.send({ type: 'broadcast', event: 'location', payload }))
    }
    if (rideGpsReadyRef.current && rideGpsChannelRef.current) {
      sends.push(rideGpsChannelRef.current.send({ type: 'broadcast', event: 'location', payload }))
    }
    if (sends.length) await Promise.allSettled(sends)
  }

  async function persistLocation(nextLocation: Location, force: boolean) {
    const nowMs = Date.now()
    const previous = lastPersistedPointRef.current
    const moved = previous ? distanceMeters(previous, nextLocation) : Number.POSITIVE_INFINITY
    if (!force && nowMs - lastPersistedAtRef.current < 15_000 && moved < 100) return

    lastPersistedAtRef.current = nowMs
    lastPersistedPointRef.current = nextLocation
    await supabase.rpc('update_driver_location', {
      p_lat: nextLocation.lat,
      p_lng: nextLocation.lng,
      p_heading: nextLocation.heading,
      p_speed_kmh: nextLocation.speed == null ? null : nextLocation.speed * 3.6,
    })
  }

  function startLocationWatch(forceFirst: boolean) {
    if (!navigator.geolocation || watchRef.current !== null) return
    let forceNext = forceFirst
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const nextLocation: Location = { lat: pos.coords.latitude, lng: pos.coords.longitude, heading: pos.coords.heading, speed: pos.coords.speed }
        setLocation(nextLocation)
        const force = forceNext
        forceNext = false
        void broadcastLocation(nextLocation, force)
        void persistLocation(nextLocation, force)
      },
      () => setMsg('Falha ao atualizar sua localização. Mantenha o GPS permitido.'),
      { enableHighAccuracy: true, maximumAge: 2_000, timeout: 15_000 },
    )
  }

  async function respond(offer: Offer, accept: boolean) {
    setBusy(true)
    const { data, error } = await supabase.rpc('respond_to_ride_offer', { p_offer_id: offer.offer_id, p_accept: accept })
    setBusy(false)
    if (error) { setMsg(error.message); await loadOffers(); return }
    const response = (data || {}) as OfferResponse
    if (accept && response.accepted) {
      setMsg('Corrida aceita. Abra a navegação e siga até o passageiro.')
      setOffers([])
      await loadCurrentRide()
    } else {
      const paymentBlocked = response.reason === 'payment_method_blocked' || response.reason === 'cash_balance_limit'
      setMsg(paymentBlocked
        ? 'Esta forma de pagamento não está liberada para sua carteira agora.'
        : response.reason === 'wallet_or_driver_unavailable'
          ? 'Seu cadastro ou plano não permite aceitar esta chamada.'
          : response.reason === 'card_machine_not_authorized'
            ? 'Sua maquininha ainda não está autorizada.'
            : accept ? 'Esta chamada ficou indisponível.' : 'Chamada recusada.')
      await loadOffers()
    }
  }

  async function confirmMachine() {
    if (!ride) return
    setBusy(true)
    const { error } = await supabase.rpc('confirm_driver_machine_payment', { p_ride_id: ride.id })
    setBusy(false)
    if (error) { setMsg(error.message); return }
    setMachinePaid(true)
    setMsg('Pagamento na maquininha registrado. Agora você pode concluir a corrida.')
  }

  async function advance(action: 'arrived' | 'start' | 'complete') {
    if (!ride) return
    setBusy(true)
    const method = ride.payment_method_preference || ''
    const { data, error } = await supabase.rpc('advance_driver_ride', { p_ride_id: ride.id, p_action: action })
    setBusy(false)
    if (error) { setMsg(error.message); return }
    const result = (data || {}) as AdvanceResult

    if (action === 'arrived') setMsg('Chegada ao embarque registrada. A tolerância de espera começou agora.')
    else if (action === 'start') setMsg(Number(result.wait_charge_amount || 0) > 0 ? `Corrida iniciada. Espera registrada: ${money(result.wait_charge_amount)}.` : 'Corrida iniciada dentro da tolerância de espera.')
    else if (method === 'cash' || method === 'card_machine') {
      setSettlement({
        method,
        commission: Number(result.direct_collection_commission_debit || 0),
        rideFee: Number(result.per_ride_fee_debit || 0),
        cancellationCollection: Number(result.cancellation_collection_debit || 0),
        balance: result.operational_balance_after == null ? null : Number(result.operational_balance_after),
      })
      setMsg(method === 'cash'
        ? 'Corrida concluída. O dinheiro foi recebido diretamente por você e os débitos correspondentes foram registrados na Carteira Operacional.'
        : 'Corrida concluída. O valor foi recebido na maquininha e os débitos correspondentes foram registrados na Carteira Operacional.')
    } else if (method === 'pix') setMsg('Corrida concluída. No PIX pelo app, a divisão entre motorista, franqueado e matriz é automática após a confirmação do pagamento.')
    else setMsg(wallet?.billing_mode === 'wallet_per_ride' ? `Corrida concluída. Foi aplicado o desconto configurado de ${money(result.per_ride_fee_debit || wallet?.ride_fee)}.` : 'Corrida concluída.')

    await Promise.all([loadCurrentRide(), loadWallet()])
    if (result.status === 'completed') setRide(null)
    if (method === 'card_machine') setMachinePaid(false)
  }

  if (!profile) return <main style={{ minHeight: 'calc(100vh - 60px)', background: '#080808', color: '#fff', padding: 24 }}><div style={{ maxWidth: 620, margin: '10vh auto', ...box }}><h1>Entre no App Motorista</h1><p className="subtitle">Faça login para ativar o GPS e receber corridas.</p><Link href="/motorista-app" style={{ ...btn, display: 'inline-block', textDecoration: 'none' }}>Ir para o login</Link></div></main>

  const offer = offers[0]
  const target = ride || offer
  const navLat = ride?.status === 'in_progress' ? ride.destination_lat : target?.origin_lat
  const navLng = ride?.status === 'in_progress' ? ride.destination_lng : target?.origin_lng
  const mapsUrl = navLat != null && navLng != null ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${navLat},${navLng}`)}&travelmode=driving` : ''
  const monthlyOk = Boolean(wallet?.billing_mode === 'monthly' && wallet.monthly_paid_until && new Date(wallet.monthly_paid_until + 'T12:00:00') >= new Date())
  const cashOk = wallet?.billing_mode !== 'wallet_per_ride' || Boolean(wallet?.cash_allowed)
  const elapsed = ride?.status === 'driver_arriving' && ride.arrived_at ? Math.max(0, Math.floor((now - new Date(ride.arrived_at).getTime()) / 1000)) : 0
  const freeSeconds = Number(ride?.wait_free_seconds || 0)
  const remaining = Math.max(0, freeSeconds - elapsed)
  const billableSeconds = Math.max(0, elapsed - freeSeconds)
  const billableMinutes = billableSeconds > 0 ? Math.ceil(billableSeconds / 60) : 0
  const liveWaitCharge = billableMinutes * Number(ride?.wait_fee_per_minute || 0)

  return <main style={{ minHeight: 'calc(100vh - 60px)', background: '#080808', color: '#fff', padding: 20 }}><div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gap: 14 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}><div><div className="eyebrow">Operação em tempo real</div><h1 style={{ margin: '5px 0' }}>Olá, {profile.full_name?.split(' ')[0] || 'motorista'}</h1><p className="subtitle">Avaliação {Number(driver?.rating || 0).toFixed(1)} · {wallet?.billing_mode === 'monthly' ? `Plano mensal ${shownMoney(wallet.monthly_fee)} · ${monthlyOk ? 'em dia' : 'pendente'}` : `Saldo operacional ${shownMoney(wallet?.operational_balance)} · ${shownMoney(wallet?.ride_fee)} por corrida`}</p></div><div style={{ display: 'flex', gap: 8, alignItems: 'center' }}><button aria-label={showMoney ? 'Ocultar ganhos e carteira' : 'Mostrar ganhos e carteira'} title={showMoney ? 'Ocultar ganhos e carteira' : 'Mostrar ganhos e carteira'} onClick={toggleMoney} style={{ ...btn, background: '#222', color: '#fff', fontSize: 20, padding: '9px 13px' }}>{showMoney ? '👁️' : '🙈'}</button><button onClick={toggleOnline} disabled={busy} style={{ ...btn, background: driver?.online ? '#15803d' : '#ffd400', color: driver?.online ? '#fff' : '#000' }}>{busy ? 'Aguarde...' : driver?.online ? '● ONLINE — ficar offline' : '○ OFFLINE — ficar online'}</button></div></div>

    {wallet && <div style={{ ...box, borderColor: wallet.billing_mode === 'monthly' ? (monthlyOk ? '#166534' : '#a16207') : (cashOk ? '#166534' : '#b45309'), display: 'grid', gap: 10 }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'center' }}><div>{wallet.billing_mode === 'monthly' ? <><b>Plano mensal</b><div style={{ color: '#9ca3af', marginTop: 5 }}>Mensalidade {shownMoney(wallet.monthly_fee)} · vencimento dia {wallet.monthly_due_day} · {wallet.monthly_paid_until ? `pago até ${new Date(wallet.monthly_paid_until + 'T12:00:00').toLocaleDateString('pt-BR')}` : 'pagamento pendente'}</div></> : <><b>Carteira por corrida</b><div style={{ color: '#9ca3af', marginTop: 5 }}>Saldo {shownMoney(wallet.operational_balance)} · limite para dinheiro {shownMoney(wallet.cash_negative_limit)} · desconto {shownMoney(wallet.ride_fee)} por corrida concluída.</div></>}</div><button aria-label="Alternar visibilidade dos valores" onClick={toggleMoney} style={{ ...btn, background: '#222', color: '#fff' }}>{showMoney ? '👁 Ocultar' : '🙈 Mostrar'}</button></div>{wallet.billing_mode === 'wallet_per_ride' && !wallet.cash_allowed && <div style={{ background: '#3b1d0d', border: '1px solid #b45309', borderRadius: 12, padding: 12, color: '#fed7aa', lineHeight: 1.5 }}><b>Corrida em dinheiro bloqueada por saldo.</b> Recarregue via PIX. <strong style={{ color: '#fff' }}>Corridas no Cartão/PIX continuam LIBERADAS.</strong></div>}{wallet.billing_mode === 'wallet_per_ride' && wallet.cash_allowed && <div style={{ color: '#86efac', fontSize: 13 }}>Dinheiro, PIX e Cartão liberados para recebimento conforme as regras da sua operação.</div>}</div>}

    <div style={{ ...box, padding: 10 }}><div ref={mapEl} style={{ height: 380, borderRadius: 14, overflow: 'hidden' }} /></div>
    {!ride && offer && <div style={{ ...box, border: '2px solid #ffd400' }}><div className="eyebrow">Nova corrida</div><h2>{offer.category_name || 'Corrida CLICK-GO'}</h2><div><b>Embarque:</b> {offer.origin_label}</div><div><b>Destino:</b> {offer.destination_label}</div><div style={{ color: '#9ca3af', marginTop: 6 }}>{Number(offer.distance_to_pickup_km).toFixed(1)} km até o passageiro · {offer.eta_to_pickup_min} min</div><div style={{ fontSize: 25, fontWeight: 900, color: '#ffd400', marginTop: 8 }}>Ganho estimado {shownMoney(offer.estimated_driver_earning)}</div><div style={{ display: 'flex', gap: 9, marginTop: 12 }}><button style={{ ...btn, flex: 1 }} onClick={() => respond(offer, true)}>Aceitar</button><button style={{ ...btn, background: '#3a1b1b', color: '#fff', flex: 1 }} onClick={() => respond(offer, false)}>Recusar</button></div></div>}
    {!ride && driver?.online && !offer && <div style={box}><b>Aguardando chamadas...</b><div style={{ color: '#9ca3af', marginTop: 5 }}>Mantenha o GPS ligado.</div></div>}
    {ride && <div style={{ ...box, borderColor: '#166534' }}><div className="eyebrow">Corrida atual</div><h2>{ride.status === 'accepted' ? 'A caminho do embarque' : ride.status === 'driver_arriving' ? 'Aguardando passageiro' : 'Corrida em andamento'}</h2><div><b>Origem:</b> {ride.origin_label}</div><div><b>Destino:</b> {ride.destination_label}</div><div style={{ color: '#9ca3af', marginTop: 7 }}>Pagamento: {ride.payment_method_preference || 'não informado'} · {shownMoney(Number(ride.estimated_fare || 0) + Number(ride.wait_charge_amount || 0))}</div>
      {ride.status === 'driver_arriving' && <div style={{ marginTop: 13, background: remaining > 0 ? '#172015' : '#2a1c0d', border: `1px solid ${remaining > 0 ? '#2f6d38' : '#8a5b16'}`, borderRadius: 13, padding: 13 }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}><div><b>{remaining > 0 ? 'Tolerância de espera' : 'Espera tarifada'}</b><div style={{ color: '#bfc6bf', fontSize: 13, marginTop: 4 }}>{remaining > 0 ? `Cobrança começa em ${clock(remaining)}` : `Tempo após tolerância: ${clock(billableSeconds)}`}</div></div><div style={{ textAlign: 'right' }}><div style={{ fontSize: 22, fontWeight: 900, color: '#ffd400' }}>{remaining > 0 ? clock(remaining) : shownMoney(liveWaitCharge)}</div><div style={{ fontSize: 11, color: '#9ca3af' }}>{remaining > 0 ? `${money(ride.wait_fee_per_minute)}/min depois` : `${money(ride.wait_fee_per_minute)}/min`}</div></div></div></div>}
      <DriverRideSafety rideId={ride.id} status={ride.status} location={location ? { lat: location.lat, lng: location.lng } : null} origin={{ lat: ride.origin_lat, lng: ride.origin_lng }} destination={{ lat: ride.destination_lat, lng: ride.destination_lng }} />
      <div style={{ display: 'flex', gap: 9, marginTop: 14, flexWrap: 'wrap' }}>{mapsUrl && <a href={mapsUrl} target="_blank" rel="noreferrer" style={{ ...btn, textDecoration: 'none', background: '#222', color: '#fff' }}>🧭 Abrir navegação</a>}{ride.status === 'accepted' && <button style={{ ...btn, background: '#0f766e', color: '#fff' }} onClick={() => advance('arrived')}>📍 Cheguei ao embarque</button>}{ride.status === 'in_progress' && ride.payment_method_preference === 'card_machine' && !machinePaid && <button style={{ ...btn, background: '#166534', color: '#fff' }} onClick={confirmMachine}>Pagamento recebido na maquininha</button>}{ride.status === 'in_progress' && <button style={btn} disabled={ride.payment_method_preference === 'card_machine' && !machinePaid} onClick={() => advance('complete')}>Concluir corrida</button>}</div>
    </div>}
    {msg && <div style={{ ...box, borderColor: '#665600', color: '#ffe66b' }}>{msg}</div>}
    {settlement && <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(0,0,0,.78)', display: 'grid', placeItems: 'center', padding: 18 }}><div style={{ ...box, maxWidth: 520, width: '100%', border: '2px solid #ffd400', boxShadow: '0 24px 80px rgba(0,0,0,.6)' }}><div className="eyebrow">Corrida concluída</div><h2 style={{ margin: '7px 0 10px' }}>Débito na Carteira Operacional</h2><p style={{ color: '#d1d5db', lineHeight: 1.55, marginTop: 0 }}>{settlement.method === 'cash' ? 'Como o passageiro pagou em dinheiro diretamente a você, a parte do franqueado e da matriz foi descontada dos seus créditos operacionais.' : 'Como o pagamento foi recebido diretamente na sua maquininha, a parte do franqueado e da matriz foi descontada dos seus créditos operacionais.'}</p><div style={{ display: 'grid', gap: 8, margin: '14px 0' }}>{settlement.commission > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span>Comissão da corrida</span><b style={{ color: '#fca5a5' }}>- {money(settlement.commission)}</b></div>}{settlement.rideFee > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span>Taxa por corrida do seu plano</span><b style={{ color: '#fca5a5' }}>- {money(settlement.rideFee)}</b></div>}{settlement.cancellationCollection > 0 && <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span>Repasse de taxa de cancelamento recebida</span><b style={{ color: '#fca5a5' }}>- {money(settlement.cancellationCollection)}</b></div>}<div style={{ borderTop: '1px solid #333', paddingTop: 10, display: 'flex', justifyContent: 'space-between', gap: 12 }}><span>Saldo operacional após os débitos</span><strong style={{ color: '#ffd400' }}>{settlement.balance == null ? '—' : money(settlement.balance)}</strong></div></div><button onClick={() => setSettlement(null)} style={{ ...btn, width: '100%', marginTop: 14 }}>Entendi</button></div></div>}
  </div></main>
}
