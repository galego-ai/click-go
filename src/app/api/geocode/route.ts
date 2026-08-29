import { NextRequest, NextResponse } from 'next/server'
import { getMapboxAccessToken } from '@/lib/map-provider-config'

export const dynamic = 'force-dynamic'

type Provider = 'google' | 'mapbox' | 'nominatim'

type AddressParts = {
  street?: string
  number?: string
  neighborhood?: string
  city?: string
  state?: string
  postcode?: string
}

type SearchResult = AddressParts & {
  label: string
  name?: string
  subtitle?: string
  category?: string
  kind: 'place' | 'address'
  lat: number
  lng: number
  distanceKm?: number
  source?: Provider
  score?: number
}

function parseCoord(value: string | null, min: number, max: number) {
  if (value === null || value.trim() === '') return null
  const n = Number(value)
  return Number.isFinite(n) && n >= min && n <= max ? n : null
}

function str(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function first(...values: unknown[]) {
  for (const value of values) {
    const text = str(value)
    if (text) return text
  }
  return ''
}

function normalize(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function formatCep(value?: string) {
  const digits = String(value || '').replace(/\D/g, '')
  if (digits.length === 8) return `${digits.slice(0, 5)}-${digits.slice(5)}`
  return String(value || '').trim()
}

function fullAddress(parts: AddressParts, fallback = '') {
  const street = str(parts.street)
  const number = str(parts.number)
  const neighborhood = str(parts.neighborhood)
  const city = str(parts.city)
  const state = str(parts.state)
  const postcode = formatCep(parts.postcode)

  const chunks: string[] = []
  if (street) chunks.push(number ? `${street}, ${number}` : street)
  else if (number) chunks.push(number)
  if (neighborhood) chunks.push(neighborhood)
  if (city || state) chunks.push(city && state ? `${city}/${state}` : city || state)
  if (postcode) chunks.push(`CEP ${postcode}`)

  const built = chunks.filter(Boolean).join(' - ')
  return built || fallback.trim()
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

function distance(lat: number | null, lng: number | null, rLat: number, rLng: number) {
  return lat !== null && lng !== null && Number.isFinite(rLat) && Number.isFinite(rLng)
    ? haversine(lat, lng, rLat, rLng)
    : undefined
}

function withContext(q: string, context: string) {
  const cleanContext = context.trim().slice(0, 100)
  if (!cleanContext) return q
  const qn = normalize(q)
  const cn = normalize(cleanContext)
  if (!cn || qn.includes(cn)) return q
  return `${q}, ${cleanContext}`
}

function completenessBonus(row: SearchResult) {
  let bonus = 0
  if (row.street) bonus += 7
  if (row.number) bonus += 8
  if (row.neighborhood) bonus += 8
  if (row.city) bonus += 6
  if (row.state) bonus += 4
  if (row.postcode) bonus += 10
  return bonus
}

function rankResults(rows: SearchResult[], q: string, context: string, limit = 6) {
  const query = normalize(q)
  const queryTokens = query.split(' ').filter(token => token.length > 1)
  const contextTokens = normalize(context).split(' ').filter(token => token.length > 2)
  const seen = new Set<string>()

  return rows
    .filter(row => row.label && Number.isFinite(row.lat) && Number.isFinite(row.lng))
    .map(row => {
      const label = normalize(row.label)
      const name = normalize(row.name || '')
      const matchedTokens = queryTokens.filter(token => label.includes(token) || name.includes(token)).length
      const contextMatches = contextTokens.filter(token => label.includes(token)).length
      const km = row.distanceKm

      let score = 0
      if (query && (label.startsWith(query) || name.startsWith(query))) score -= 70
      else if (query && (label.includes(query) || name.includes(query))) score -= 48
      score -= matchedTokens * 9
      score -= contextMatches * 7
      score -= completenessBonus(row)

      if (typeof km === 'number') {
        score += Math.min(km, 300) * 1.15
        if (km <= 2) score -= 34
        else if (km <= 5) score -= 26
        else if (km <= 10) score -= 18
        else if (km <= 25) score -= 8
        else if (km >= 80) score += 28
      }

      if (row.source === 'google') score -= 6
      else if (row.source === 'mapbox') score -= 4

      return { ...row, score }
    })
    .sort((a, b) => (a.score ?? 0) - (b.score ?? 0) || (a.distanceKm ?? 9999) - (b.distanceKm ?? 9999))
    .filter(row => {
      const key = `${normalize(row.label)}|${row.lat.toFixed(4)}|${row.lng.toFixed(4)}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .slice(0, limit)
    .map(({ score: _score, source: _source, ...row }) => row)
}

function googleParts(components: any[] = []): AddressParts {
  const byType = (type: string, short = false) => {
    const item = components.find(c => Array.isArray(c?.types) && c.types.includes(type))
    return str(short ? item?.short_name : item?.long_name)
  }
  return {
    street: byType('route'),
    number: byType('street_number'),
    neighborhood: first(
      byType('sublocality_level_1'),
      byType('sublocality'),
      byType('neighborhood'),
      byType('administrative_area_level_4'),
    ),
    city: first(byType('locality'), byType('administrative_area_level_2'), byType('postal_town')),
    state: byType('administrative_area_level_1', true),
    postcode: byType('postal_code'),
  }
}

async function mapboxSearch(q: string, lat: number | null, lng: number | null): Promise<SearchResult[]> {
  const token = await getMapboxAccessToken()
  if (!token) return []
  const url = new URL('https://api.mapbox.com/search/geocode/v6/forward')
  url.searchParams.set('q', q)
  url.searchParams.set('country', 'br')
  url.searchParams.set('limit', '8')
  url.searchParams.set('autocomplete', 'true')
  url.searchParams.set('language', 'pt-BR')
  url.searchParams.set('access_token', token)
  if (lat !== null && lng !== null) url.searchParams.set('proximity', `${lng},${lat}`)

  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(1800) })
  if (!res.ok) return []
  const json = await res.json() as any

  return (json?.features || []).map((f: any) => {
    const c = f?.geometry?.coordinates || []
    const props = f?.properties || {}
    const ctx = props.context || {}
    const featureType = str(props.feature_type)
    const contextAddress = ctx.address || {}
    const contextStreet = ctx.street || {}
    const parts: AddressParts = {
      street: first(contextStreet.name, featureType === 'street' ? props.name : '', featureType === 'address' ? props.name : ''),
      number: first(contextAddress.address_number, props.address_number),
      neighborhood: first(ctx.neighborhood?.name, ctx.locality?.name, ctx.district?.name),
      city: first(ctx.place?.name, ctx.city?.name),
      state: first(ctx.region?.region_code, ctx.region?.name),
      postcode: first(ctx.postcode?.name),
    }
    const fallback = first(props.full_address, props.place_formatted, props.name)
    const label = fullAddress(parts, fallback)
    const rLat = Number(c[1])
    const rLng = Number(c[0])
    return {
      ...parts,
      label,
      name: first(props.name, parts.street, label) || undefined,
      subtitle: label,
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: distance(lat, lng, rLat, rLng),
      source: 'mapbox' as const,
    }
  })
}

async function nominatimSearch(q: string, lat: number | null, lng: number | null): Promise<SearchResult[]> {
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('format', 'jsonv2')
  url.searchParams.set('q', q)
  url.searchParams.set('countrycodes', 'br')
  url.searchParams.set('limit', '8')
  url.searchParams.set('addressdetails', '1')
  if (lat !== null && lng !== null) {
    const latDelta = 0.14
    const lngDelta = 0.16
    url.searchParams.set('viewbox', `${lng - lngDelta},${lat + latDelta},${lng + lngDelta},${lat - latDelta}`)
    url.searchParams.set('bounded', '0')
  }

  const res = await fetch(url, {
    headers: {
      'User-Agent': 'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.5',
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(1800),
  })
  if (!res.ok) return []
  const json = await res.json() as any[]

  return (Array.isArray(json) ? json : []).map((r: any) => {
    const a = r?.address || {}
    const parts: AddressParts = {
      street: first(a.road, a.pedestrian, a.residential, a.footway, a.path),
      number: first(a.house_number),
      neighborhood: first(a.neighbourhood, a.suburb, a.quarter, a.city_district),
      city: first(a.city, a.town, a.village, a.municipality, a.county),
      state: first(a.state_code, a['ISO3166-2-lvl4']?.split('-')?.[1], a.state),
      postcode: first(a.postcode),
    }
    const fallback = str(r.display_name)
    const label = fullAddress(parts, fallback)
    const rLat = Number(r.lat)
    const rLng = Number(r.lon)
    return {
      ...parts,
      label,
      name: first(r.name, parts.street, label) || undefined,
      subtitle: label,
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: distance(lat, lng, rLat, rLng),
      source: 'nominatim' as const,
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
  url.searchParams.set('components', 'country:BR')
  url.searchParams.set('key', key)
  if (lat !== null && lng !== null) {
    url.searchParams.set('bounds', `${lat - .12},${lng - .12}|${lat + .12},${lng + .12}`)
  }

  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(1800) })
  if (!res.ok) return []
  const json = await res.json() as any

  return (json?.results || []).slice(0, 8).map((r: any) => {
    const rLat = Number(r.geometry?.location?.lat)
    const rLng = Number(r.geometry?.location?.lng)
    const parts = googleParts(r.address_components || [])
    const fallback = str(r.formatted_address)
    const label = fullAddress(parts, fallback)
    return {
      ...parts,
      label,
      name: first(parts.street, fallback) || undefined,
      subtitle: label,
      category: 'Endereço',
      kind: 'address' as const,
      lat: rLat,
      lng: rLng,
      distanceKm: distance(lat, lng, rLat, rLng),
      source: 'google' as const,
    }
  })
}

async function rankedForwardSearch(q: string, context: string, lat: number | null, lng: number | null) {
  const contextual = withContext(q, context)
  const [google, mapbox, osm] = await Promise.all([
    googleGeocode(contextual, lat, lng).catch(() => []),
    mapboxSearch(q, lat, lng).catch(() => []),
    nominatimSearch(contextual, lat, lng).catch(() => []),
  ])

  const merged = rankResults([...google, ...mapbox, ...osm], q, context)
  return {
    results: merged,
    provider: google.length && (mapbox.length || osm.length) ? 'mixed' : google.length ? 'google' : mapbox.length ? 'mapbox' : osm.length ? 'nominatim' : 'none',
  }
}

async function googleReverse(lat: number, lng: number): Promise<SearchResult | null> {
  const key = process.env.GOOGLE_MAPS_SERVER_API_KEY || process.env.GOOGLE_PLACES_API_KEY
  if (!key) return null
  const url = new URL('https://maps.googleapis.com/maps/api/geocode/json')
  url.searchParams.set('latlng', `${lat},${lng}`)
  url.searchParams.set('language', 'pt-BR')
  url.searchParams.set('region', 'br')
  url.searchParams.set('key', key)

  try {
    const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(1800) })
    if (!res.ok) return null
    const json = await res.json() as any
    const r = json?.results?.[0]
    if (!r) return null
    const parts = googleParts(r.address_components || [])
    const label = fullAddress(parts, str(r.formatted_address))
    return { ...parts, label, kind: 'address', category: 'Localização atual', lat, lng }
  } catch {
    return null
  }
}

async function nominatimReverse(lat: number, lng: number): Promise<SearchResult | null> {
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
      signal: AbortSignal.timeout(1800),
    })
    if (!res.ok) return null
    const json = await res.json() as any
    if (!json) return null
    const a = json.address || {}
    const parts: AddressParts = {
      street: first(a.road, a.pedestrian, a.residential, a.footway, a.path),
      number: first(a.house_number),
      neighborhood: first(a.neighbourhood, a.suburb, a.quarter, a.city_district),
      city: first(a.city, a.town, a.village, a.municipality, a.county),
      state: first(a.state_code, a['ISO3166-2-lvl4']?.split('-')?.[1], a.state),
      postcode: first(a.postcode),
    }
    const label = fullAddress(parts, str(json.display_name))
    return { ...parts, label, kind: 'address', category: 'Localização atual', lat, lng }
  } catch {
    return null
  }
}

async function mapboxReverse(lat: number, lng: number): Promise<SearchResult | null> {
  const token = await getMapboxAccessToken()
  if (!token) return null
  try {
    const url = new URL('https://api.mapbox.com/search/geocode/v6/reverse')
    url.searchParams.set('longitude', String(lng))
    url.searchParams.set('latitude', String(lat))
    url.searchParams.set('country', 'br')
    url.searchParams.set('language', 'pt-BR')
    url.searchParams.set('access_token', token)
    const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(1800) })
    if (!res.ok) return null
    const json = await res.json() as any
    const f = json?.features?.[0]
    if (!f) return null
    const props = f.properties || {}
    const ctx = props.context || {}
    const parts: AddressParts = {
      street: first(ctx.street?.name, props.name),
      number: first(ctx.address?.address_number, props.address_number),
      neighborhood: first(ctx.neighborhood?.name, ctx.locality?.name, ctx.district?.name),
      city: first(ctx.place?.name, ctx.city?.name),
      state: first(ctx.region?.region_code, ctx.region?.name),
      postcode: first(ctx.postcode?.name),
    }
    const label = fullAddress(parts, first(props.full_address, props.place_formatted, props.name, 'Minha localização'))
    return { ...parts, label, kind: 'address', category: 'Localização atual', lat, lng }
  } catch {
    return null
  }
}

async function reverseLookup(lat: number, lng: number): Promise<SearchResult | null> {
  const google = await googleReverse(lat, lng)
  if (google?.label) return google
  const osm = await nominatimReverse(lat, lng)
  if (osm?.label) return osm
  return await mapboxReverse(lat, lng) || { label: 'Minha localização atual', kind: 'address', category: 'Localização atual', lat, lng }
}

function response(payload: Record<string, unknown>, status = 200) {
  return NextResponse.json(payload, {
    status,
    headers: status === 200
      ? { 'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=120' }
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
    return response({ results: result ? [result] : [], provider: 'auto', completeAddress: true })
  }

  const q = (request.nextUrl.searchParams.get('q') || '').trim()
  const context = (request.nextUrl.searchParams.get('context') || '').trim().slice(0, 100)
  if (q.length < 3) return response({ error: 'Digite pelo menos 3 caracteres.' }, 400)
  if (q.length > 180) return response({ error: 'Endereço muito longo.' }, 400)

  try {
    const found = await rankedForwardSearch(q, context, lat, lng)
    return response({
      results: found.results,
      regionalized: lat !== null && lng !== null,
      contextApplied: Boolean(context),
      provider: found.provider,
      rankedByProximity: lat !== null && lng !== null,
      completeAddress: true,
      parallel: true,
      attribution: 'Google Maps / Mapbox / © OpenStreetMap contributors',
    })
  } catch {
    return response({ error: 'Serviço de endereços temporariamente indisponível.' }, 502)
  }
}
