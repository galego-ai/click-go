'use client'

import { useEffect, useRef, useState } from 'react'
import type { CircleMarker, Map as LeafletMap } from 'leaflet'
import { supabase } from '@/lib/supabase'
import {
  cityDriverLocationsTopic,
  parseDriverLocationBroadcast,
  type DriverLocationBroadcast,
} from '@/lib/realtime-gps'
import 'leaflet/dist/leaflet.css'

type Loc = DriverLocationBroadcast
type City = { id: string; name: string; state: string }
type ProfileScope = { role: string }
type CityAccess = { city_id: string }
type DriverIdRow = { id: string }

export default function RealtimeMapData() {
  const [rows, setRows] = useState<Loc[]>([])
  const [cities, setCities] = useState<City[]>([])
  const [selectedCity, setSelectedCity] = useState('')
  const [msg, setMsg] = useState('Conectando ao Realtime...')
  const [mapReady, setMapReady] = useState(false)

  const mapEl = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<LeafletMap | null>(null)
  const leafletRef = useRef<typeof import('leaflet') | null>(null)
  const markersRef = useRef<Map<string, CircleMarker>>(new Map())
  const locationsRef = useRef<Map<string, Loc>>(new Map())

  function syncRows() {
    setRows(
      Array.from(locationsRef.current.values()).sort(
        (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
      ),
    )
  }

  function clearLocations() {
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current.clear()
    locationsRef.current.clear()
    setRows([])
  }

  function renderLocation(location: Loc) {
    const L = leafletRef.current
    const map = mapRef.current
    if (!L || !map) return

    const current = markersRef.current.get(location.driver_id)
    const popup = `<strong>Motorista ${location.driver_id.slice(0, 8)}</strong><br/>Velocidade: ${Math.round(location.speed_kmh ?? 0)} km/h<br/>Atualizado: ${new Date(location.updated_at).toLocaleString('pt-BR')}`

    if (current) {
      current.setLatLng([location.lat, location.lng]).setPopupContent(popup)
      return
    }

    const marker = L.circleMarker([location.lat, location.lng], {
      radius: 8,
      weight: 2,
      fillOpacity: 0.8,
    })
    marker.bindPopup(popup).addTo(map)
    markersRef.current.set(location.driver_id, marker)
  }

  function applyLocation(location: Loc) {
    locationsRef.current.set(location.driver_id, location)
    renderLocation(location)
    syncRows()
  }

  async function loadScope() {
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      setMsg('Faça login para acompanhar a operação.')
      return
    }

    const { data: profile, error: profileError } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single()

    if (profileError) {
      setMsg(profileError.message)
      return
    }

    const scope = profile as ProfileScope
    let allowedCities: City[] = []

    if (scope.role === 'super_admin') {
      const { data, error } = await supabase
        .from('cities')
        .select('id,name,state')
        .eq('active', true)
        .order('name')
      if (error) {
        setMsg(error.message)
        return
      }
      allowedCities = (data ?? []) as City[]
    } else {
      const { data: access, error: accessError } = await supabase
        .from('profile_city_access')
        .select('city_id')
        .eq('profile_id', user.id)

      if (accessError) {
        setMsg(accessError.message)
        return
      }

      const cityIds = ((access ?? []) as CityAccess[]).map((item) => item.city_id)
      if (cityIds.length > 0) {
        const { data, error } = await supabase
          .from('cities')
          .select('id,name,state')
          .in('id', cityIds)
          .order('name')
        if (error) {
          setMsg(error.message)
          return
        }
        allowedCities = (data ?? []) as City[]
      }
    }

    setCities(allowedCities)
    if (allowedCities[0]) setSelectedCity(allowedCities[0].id)
    else setMsg('Nenhuma cidade autorizada para este usuário.')
  }

  async function loadSnapshot(cityId: string) {
    setMsg('Carregando posições atuais...')
    clearLocations()

    const { data: drivers, error: driversError } = await supabase
      .from('drivers')
      .select('id')
      .eq('city_id', cityId)
      .eq('online', true)

    if (driversError) {
      setMsg(driversError.message)
      return
    }

    const driverIds = ((drivers ?? []) as DriverIdRow[]).map((driver) => driver.id)
    if (driverIds.length === 0) {
      setMsg('Realtime ativo · nenhum motorista online nesta cidade.')
      return
    }

    const { data, error } = await supabase
      .from('driver_locations')
      .select('driver_id,lat,lng,heading,speed_kmh,updated_at')
      .in('driver_id', driverIds)
      .order('updated_at', { ascending: false })

    if (error) {
      setMsg(error.message)
      return
    }

    for (const location of (data ?? []) as Loc[]) {
      locationsRef.current.set(location.driver_id, location)
      renderLocation(location)
    }
    syncRows()

    const map = mapRef.current
    const L = leafletRef.current
    if (map && L && locationsRef.current.size > 0) {
      const bounds = L.latLngBounds(
        Array.from(locationsRef.current.values()).map((location) => [
          location.lat,
          location.lng,
        ] as [number, number]),
      )
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 })
    }

    setMsg('Realtime Broadcast privado ativo.')
  }

  useEffect(() => {
    void loadScope()
  }, [])

  useEffect(() => {
    let alive = true
    void (async () => {
      if (!mapEl.current) return
      const L = await import('leaflet')
      if (!alive || !mapEl.current) return
      leafletRef.current = L
      mapRef.current = L.map(mapEl.current, { zoomControl: true }).setView(
        [-14.52472, -49.14083],
        13,
      )
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapRef.current)
      setMapReady(true)
    })()

    return () => {
      alive = false
      mapRef.current?.remove()
      mapRef.current = null
      leafletRef.current = null
      markersRef.current.clear()
    }
  }, [])

  useEffect(() => {
    if (!mapReady || !selectedCity) return
    let cancelled = false
    let channel: ReturnType<typeof supabase.channel> | null = null

    void (async () => {
      await loadSnapshot(selectedCity)
      if (cancelled) return

      await supabase.realtime.setAuth()
      channel = supabase
        .channel(cityDriverLocationsTopic(selectedCity), {
          config: { private: true },
        })
        .on('broadcast', { event: 'location' }, (event) => {
          const location = parseDriverLocationBroadcast(event.payload)
          if (location) applyLocation(location)
        })
        .subscribe((status) => {
          if (status === 'SUBSCRIBED') setMsg('Realtime Broadcast privado ativo.')
          else if (status === 'CHANNEL_ERROR') setMsg('Falha ao conectar o mapa ao Realtime.')
        })
    })()

    return () => {
      cancelled = true
      if (channel) void supabase.removeChannel(channel)
      clearLocations()
    }
  }, [mapReady, selectedCity])

  const selectedCityLabel = cities.find((city) => city.id === selectedCity)

  return (
    <>
      <div className="section" style={{ display: 'flex', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
        <label style={{ minWidth: 260 }}>
          <span className="label">Cidade monitorada</span>
          <select
            value={selectedCity}
            onChange={(event) => setSelectedCity(event.target.value)}
            style={{ width: '100%', marginTop: 6, padding: 10, borderRadius: 10, background: '#111', color: '#fff', border: '1px solid #333' }}
          >
            {cities.map((city) => (
              <option key={city.id} value={city.id}>
                {city.name} / {city.state}
              </option>
            ))}
          </select>
        </label>
        <div style={{ color: '#9ca3af', fontSize: 13 }}>
          Canal: {selectedCityLabel ? `${selectedCityLabel.name}/${selectedCityLabel.state}` : '—'}
        </div>
      </div>

      <div className="grid-3">
        <div className="card">
          <div className="label">Posições recebidas</div>
          <div className="metric kpi-good">{rows.length}</div>
        </div>
        <div className="card">
          <div className="label">Última atualização</div>
          <div className="metric" style={{ fontSize: 18 }}>
            {rows[0] ? new Date(rows[0].updated_at).toLocaleTimeString('pt-BR') : '—'}
          </div>
        </div>
        <div className="card">
          <div className="label">Realtime</div>
          <div className="metric" style={{ fontSize: 18 }}>{msg || 'Ativo'}</div>
        </div>
      </div>

      <div className="section">
        <div
          ref={mapEl}
          style={{ height: 460, borderRadius: 16, overflow: 'hidden', border: '1px solid #292929' }}
        />
      </div>

      <div className="section">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Motorista</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Velocidade</th>
                <th>Atualizado</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={5} className="empty">Nenhuma localização recebida.</td></tr>
              ) : rows.map((row) => (
                <tr key={row.driver_id}>
                  <td>{row.driver_id.slice(0, 8)}…</td>
                  <td>{row.lat.toFixed(6)}</td>
                  <td>{row.lng.toFixed(6)}</td>
                  <td>{Math.round(row.speed_kmh ?? 0)} km/h</td>
                  <td>{new Date(row.updated_at).toLocaleString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
