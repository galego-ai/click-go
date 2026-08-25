import { NextRequest, NextResponse } from 'next/server'
import { getMapboxAccessToken } from '@/lib/map-provider-config'

export const dynamic = 'force-dynamic'

type SearchResult = {
  label: string
  name?: string
  subtitle?: string
  category?: string
  kind: 'place' | 'address'
  lat: number
  lng: number
  distanceKm?: number
}

function parseCoord(value: string | null, min: number, max: number) {
  if (value === null || value.trim() === '') return null
  const n = Number(value)
  return Number.isFinite(n) && n >= min && n <= max ? n : null
}

function haversine(lat1: number, lng1: number, lat2: number, lng2: number) {
  const r = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2
  return r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function cleanResults(rows: SearchResult[], limit = 5) {
  const seen = new Set<string>()
  return rows
    .filter(r => r.label && Number.isFinite(r.lat) && Number.isFinite(r.lng))
    .filter(r => {
      const key = `${r.label.toLowerCase()}|${r.lat.toFixed(4)}|${r.lng.toFixed(4)}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .sort((a, b) => (a.distanceKm ?? 9999) - (b.distanceKm ?? 9999))
    .slice(0, limit)
}

async function mapboxSearch(q: string, lat: number | null, lng: number | null): Promise<SearchResult[]> {
  const token = await getMapboxAccessToken()
  if (!token) return []
  const url = new URL('https://api.mapbox.com/search/geocode/v6/forward')
  url.searchParams.set('q', q)
  url.searchParams.set('country', 'br')
  url.searchParams.set('limit', '5')
  url.searchParams.set('autocomplete', 'true')
  url.searchParams.set('language', 'pt-BR')
  url.searchParams.set('access_token', token)
  if (lat !== null && lng !== null) url.searchParams.set('proximity', `${lng},${lat}`)
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(3500) })
  if (!res.ok) return []
  const json = await res.json() as any
  return (json?.features || []).map((f: any) => {
    const c = f?.geometry?.coordinates || []
    const props = f?.properties || {}
    const label = String(props.full_address || props.place_formatted || props.name || '').trim()
    const rLat = Number(c[1])
    const rLng = Number(c[0])
    return {
      label,
      name: String(props.name || '').trim() || undefined,
      subtitle: label,
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: lat !== null && lng !== null && Number.isFinite(rLat) && Number.isFinite(rLng)
        ? haversine(lat, lng, rLat, rLng)
        : undefined,
    }
  })
}

async function nominatimSearch(q: string, lat: number | null, lng: number | null): Promise<SearchResult[]> {
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('format', 'jsonv2')
  url.searchParams.set('q', q)
  url.searchParams.set('countrycodes', 'br')
  url.searchParams.set('limit', '5')
  url.searchParams.set('addressdetails', '1')
  if (lat !== null && lng !== null) {
    const latDelta = 0.30
    const lngDelta = 0.32
    url.searchParams.set('viewbox', `${lng - lngDelta},${lat + latDelta},${lng + lngDelta},${lat - latDelta}`)
    // bounded=0 mantém a busca regionalizada sem esconder um resultado válido fora da caixa.
    url.searchParams.set('bounded', '0')
  }
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.5',
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(3000),
  })
  if (!res.ok) return []
  const json = await res.json() as any[]
  return (Array.isArray(json) ? json : []).map((r: any) => {
    const rLat = Number(r.lat)
    const rLng = Number(r.lon)
    return {
      label: String(r.display_name || '').trim(),
      name: String(r.name || '').trim() || undefined,
      subtitle: String(r.display_name || '').trim(),
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: lat !== null && lng !== null && Number.isFinite(rLat) && Number.isFinite(rLng)
        ? haversine(lat, lng, rLat, rLng)
        : undefined,
    }
  })
}

async function googleGeocode(q: string, lat: number | null, lng: number | null): Promise<SearchResult[]> {
  const key = process.env.GOOGLE_MAPS_SERVER_API_KEY || process.env.GOOGLE_PLACES_API_KEY
  if (!key) return []
  const url = new URL('https://maps.googleapis.com/maps/api/geocode/json')
  url.searchParams.set('address', q)
  url.searchParams.set('region', 'br')
  url.searchParams.set('language', 'pt-BR')
  url.searchParams.set('key', key)
  if (lat !== null && lng !== null) {
    url.searchParams.set('bounds', `${lat - .15},${lng - .15}|${lat + .15},${lng + .15}`)
  }
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(3500) })
  if (!res.ok) return []
  const json = await res.json() as any
  return (json?.results || []).slice(0, 5).map((r: any) => {
    const rLat = Number(r.geometry?.location?.lat)
    const rLng = Number(r.geometry?.location?.lng)
    return {
      label: String(r.formatted_address || ''),
      subtitle: String(r.formatted_address || ''),
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: lat !== null && lng !== null && Number.isFinite(rLat) && Number.isFinite(rLng)
        ? haversine(lat, lng, rLat, rLng)
        : undefined,
    }
  })
}

async function reverseLookup(lat: number, lng: number): Promise<SearchResult | null> {
  const token = await getMapboxAccessToken()
  if (token) {
    try {
      const url = new URL('https://api.mapbox.com/search/geocode/v6/reverse')
      url.searchParams.set('longitude', String(lng))
      url.searchParams.set('latitude', String(lat))
      url.searchParams.set('country', 'br')
      url.searchParams.set('language', 'pt-BR')
      url.searchParams.set('access_token', token)
      const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(3500) })
      if (res.ok) {
        const json = await res.json() as any
        const f = json?.features?.[0]
        const c = f?.geometry?.coordinates
        if (f && c) {
          return {
            label: String(f.properties?.full_address || f.properties?.place_formatted || f.properties?.name || 'Minha localização'),
            kind: 'address',
            category: 'Localização atual',
            lat: Number(c[1]),
            lng: Number(c[0]),
          }
        }
      }
    } catch {}
  }

  try {
    const url = new URL('https://nominatim.openstreetmap.org/reverse')
    url.searchParams.set('format', 'jsonv2')
    url.searchParams.set('lat', String(lat))
    url.searchParams.set('lon', String(lng))
    url.searchParams.set('zoom', '18')
    url.searchParams.set('addressdetails', '1')
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)',
        'Accept-Language': 'pt-BR,pt;q=0.9',
      },
      cache: 'no-store',
      signal: AbortSignal.timeout(3000),
    })
    if (res.ok) {
      const json = await res.json() as any
      if (json?.display_name) {
        return {
          label: String(json.display_name),
          kind: 'address',
          category: 'Localização atual',
          lat,
          lng,
        }
      }
    }
  } catch {}

  const google = await googleGeocode(`${lat},${lng}`, lat, lng).catch(() => [])
  return google[0] || { label: 'Minha localização atual', kind: 'address', category: 'Localização atual', lat, lng }
}

function response(payload: Record<string, unknown>, status = 200) {
  return NextResponse.json(payload, {
    status,
    headers: status === 200
      ? { 'Cache-Control': 'public, s-maxage=20, stale-while-revalidate=60' }
      : undefined,
  })
}

export async function GET(request: NextRequest) {
  const reverse = request.nextUrl.searchParams.get('reverse') === '1'
  const lat = parseCoord(request.nextUrl.searchParams.get('lat'), -90, 90)
  const lng = parseCoord(request.nextUrl.searchParams.get('lng'), -180, 180)

  if (reverse) {
    if (lat === null || lng === null) return response({ error: 'Localização inválida.' }, 400)
    const result = await reverseLookup(lat, lng)
    return response({ results: result ? [result] : [], provider: 'auto' })
  }

  const q = (request.nextUrl.searchParams.get('q') || '').trim()
  if (q.length < 3) return response({ error: 'Digite pelo menos 3 caracteres.' }, 400)
  if (q.length > 180) return response({ error: 'Endereço muito longo.' }, 400)

  try {
    // Caminho principal: Mapbox autocomplete. Se já houver boas opções, responde sem aguardar fallbacks.
    const mapbox = cleanResults(await mapboxSearch(q, lat, lng).catch(() => []))
    if (mapbox.length >= 3) {
      return response({
        results: mapbox,
        regionalized: lat !== null && lng !== null,
        provider: 'mapbox',
        fast: true,
        attribution: 'Mapbox',
      })
    }

    // Fallback leve: uma única consulta Nominatim regionalizada, sem Overpass/POI pesado.
    const osm = await nominatimSearch(q, lat, lng).catch(() => [])
    let results = cleanResults([...mapbox, ...osm])

    if (results.length === 0) {
      results = cleanResults(await googleGeocode(q, lat, lng).catch(() => []))
    }

    return response({
      results,
      regionalized: lat !== null && lng !== null,
      provider: mapbox.length ? 'mapbox+nominatim' : results.length ? 'nominatim/google' : 'none',
      fast: true,
      attribution: 'Mapbox / Google Maps / © OpenStreetMap contributors',
    })
  } catch {
    return response({ error: 'Serviço de endereços temporariamente indisponível.' }, 502)
  }
}
