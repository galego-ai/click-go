import { useEffect, useMemo, useState } from 'react'
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import * as Location from 'expo-location'
import { router } from 'expo-router'
import { supabase } from '@/lib/supabase'
import { colors } from '@/lib/theme'

type Category = {
  id: string
  name: string
  base_fare: number
  minimum_fare: number
  price_per_km: number
  price_per_minute: number
  city_id: string
  franchise_id: string | null
}

type Point = { lat: number; lng: number }

function km(a: Point, b: Point) {
  const R = 6371
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLon = ((b.lng - a.lng) * Math.PI) / 180
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) *
      Math.cos((b.lat * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x)) * 1.25
}

export default function Home() {
  const [origin, setOrigin] = useState('Localizando...')
  const [coords, setCoords] = useState<Point | null>(null)
  const [destination, setDestination] = useState('')
  const [destCoords, setDestCoords] = useState<Point | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [selected, setSelected] = useState<Category | null>(null)
  const [cityId, setCityId] = useState<string | null>(null)
  const [distance, setDistance] = useState(0)
  const [minutes, setMinutes] = useState(0)
  const [couponCode, setCouponCode] = useState('')
  const [coupon, setCoupon] = useState<any>(null)
  const [calculating, setCalculating] = useState(false)

  useEffect(() => {
    let mounted = true

    async function loadLocation() {
      const { status } = await Location.requestForegroundPermissionsAsync()
      if (!mounted) return
      if (status !== 'granted') {
        setOrigin('Permissão de localização negada')
        return
      }

      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High })
      if (!mounted) return

      const start = { lat: position.coords.latitude, lng: position.coords.longitude }
      setCoords(start)

      const reverse = await Location.reverseGeocodeAsync({ latitude: start.lat, longitude: start.lng })
      if (!mounted) return

      const address = reverse[0]
      const city = address?.city || address?.subregion || ''
      setOrigin([address?.street, address?.streetNumber, city].filter(Boolean).join(', ') || 'Sua localização')

      if (!city) return

      const { data: cityRow } = await supabase
        .from('cities')
        .select('id')
        .ilike('name', city)
        .eq('active', true)
        .limit(1)
        .maybeSingle()

      if (!mounted || !cityRow?.id) return
      setCityId(cityRow.id)

      const { data: categoryRows } = await supabase
        .from('ride_categories')
        .select('id,name,base_fare,minimum_fare,price_per_km,price_per_minute,city_id,franchise_id')
        .eq('city_id', cityRow.id)
        .eq('active', true)

      if (!mounted) return
      const list = (categoryRows || []) as Category[]
      setCategories(list)
      setSelected(list[0] || null)
    }

    loadLocation().catch((error: Error) => {
      if (mounted) setOrigin(error.message || 'Não foi possível obter sua localização')
    })

    return () => {
      mounted = false
    }
  }, [])

  async function calculate() {
    if (!coords || !destination.trim()) {
      Alert.alert('Informe o destino')
      return
    }

    setCalculating(true)
    try {
      const geocoded = await Location.geocodeAsync(destination)
      if (!geocoded[0]) throw new Error('Destino não encontrado')

      const end = { lat: geocoded[0].latitude, lng: geocoded[0].longitude }
      setDestCoords(end)
      const calculatedDistance = km(coords, end)
      setDistance(calculatedDistance)
      setMinutes(Math.max(1, Math.round((calculatedDistance / 28) * 60)))
    } catch (error: any) {
      Alert.alert('Rota', error.message)
    } finally {
      setCalculating(false)
    }
  }

  function rawEstimate(category: Category) {
    if (!distance) return Math.max(Number(category.minimum_fare || 0), Number(category.base_fare || 0))
    return Math.max(
      Number(category.minimum_fare || 0),
      Number(category.base_fare || 0) +
        distance * Number(category.price_per_km || 0) +
        minutes * Number(category.price_per_minute || 0),
    )
  }

  function discountFor(value: number) {
    if (!coupon) return 0
    if (coupon.discount_type === 'fixed') return Math.min(value, Number(coupon.discount_value || 0))
    const calculated = (value * Number(coupon.discount_value || 0)) / 100
    return Math.min(calculated, coupon.max_discount ? Number(coupon.max_discount) : calculated)
  }

  function estimate(category: Category) {
    const raw = rawEstimate(category)
    return Math.max(0, raw - discountFor(raw))
  }

  async function applyCoupon() {
    if (!couponCode || !cityId) return
    const { data, error } = await supabase
      .from('coupons')
      .select('*')
      .eq('code', couponCode.trim().toUpperCase())
      .eq('active', true)
      .or(`city_id.is.null,city_id.eq.${cityId}`)
      .limit(1)
      .maybeSingle()

    if (error || !data) {
      Alert.alert('Cupom', 'Cupom inválido ou indisponível nesta cidade.')
      return
    }

    setCoupon(data)
    Alert.alert('Cupom aplicado', data.description || data.code)
  }

  async function requestRide() {
    if (!coords || !destCoords || !destination || !selected || !cityId) {
      Alert.alert('Calcule a rota', 'Informe o destino e toque em Calcular rota antes de solicitar.')
      return
    }

    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      router.replace('/login')
      return
    }

    const raw = rawEstimate(selected)
    const discount = discountFor(raw)
    const { data, error } = await supabase
      .from('rides')
      .insert({
        passenger_id: user.id,
        franchise_id: selected.franchise_id,
        city_id: cityId,
        category_id: selected.id,
        coupon_id: coupon?.id || null,
        discount_amount: discount,
        status: 'requested',
        origin_label: origin,
        origin_lat: coords.lat,
        origin_lng: coords.lng,
        destination_label: destination,
        destination_lat: destCoords.lat,
        destination_lng: destCoords.lng,
        estimated_distance_km: distance,
        estimated_duration_min: minutes,
        estimated_arrival_min: Math.max(3, Math.round(minutes * 0.35)),
        estimated_fare: Math.max(0, raw - discount),
      })
      .select('id')
      .single()

    if (error) {
      Alert.alert('Não foi possível solicitar', error.message)
      return
    }

    router.push({ pathname: '/ride', params: { id: data.id } })
  }

  const routeReady = useMemo(() => Boolean(destCoords) && distance > 0, [destCoords, distance])

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={s.header}>
        <Text style={s.logo}>CLICK-GO</Text>
        <Pressable onPress={() => router.push('/history')}><Text style={s.link}>Histórico</Text></Pressable>
      </View>

      <View style={s.map}>
        <Text style={s.mapPin}>●</Text>
        <Text style={s.mapText}>Sua localização</Text>
        <Text style={s.mapSub}>{origin}</Text>
        {routeReady && <Text style={s.routeInfo}>{distance.toFixed(1)} km • aprox. {minutes} min</Text>}
      </View>

      <View style={s.card}>
        <Text style={s.label}>Para onde você vai?</Text>
        <TextInput
          style={s.input}
          placeholder="Digite o destino"
          placeholderTextColor={colors.muted}
          value={destination}
          onChangeText={(value) => {
            setDestination(value)
            setDestCoords(null)
            setDistance(0)
          }}
        />
        <Pressable style={s.calculate} onPress={calculate}>
          <Text style={s.calculateText}>{calculating ? 'Calculando...' : 'Calcular rota'}</Text>
        </Pressable>

        <View style={s.shortcuts}>
          <Pressable onPress={() => router.push('/favorites')}><Text style={s.chip}>★ Favoritos</Text></Pressable>
          <Pressable onPress={() => router.push('/schedule')}><Text style={s.chip}>◷ Agendar</Text></Pressable>
          <Pressable onPress={() => router.push('/wallet')}><Text style={s.chip}>$ Pagamento</Text></Pressable>
        </View>

        <View style={s.couponRow}>
          <TextInput
            style={[s.input, { flex: 1 }]}
            placeholder="Cupom"
            placeholderTextColor={colors.muted}
            value={couponCode}
            onChangeText={setCouponCode}
          />
          <Pressable style={s.couponButton} onPress={applyCoupon}><Text style={s.couponText}>Aplicar</Text></Pressable>
        </View>
        {coupon && <Text style={s.couponOk}>✓ {coupon.code} aplicado</Text>}
      </View>

      <Text style={s.section}>Escolha uma categoria</Text>
      {categories.length ? (
        categories.map((category) => (
          <Pressable
            key={category.id}
            onPress={() => setSelected(category)}
            style={[s.category, selected?.id === category.id && s.selected]}
          >
            <View>
              <Text style={s.categoryName}>{category.name}</Text>
              <Text style={s.categoryMeta}>
                {routeReady
                  ? `${distance.toFixed(1)} km • ${minutes} min • motorista em ~${Math.max(3, Math.round(minutes * 0.35))} min`
                  : 'Calcule a rota para ver tempo e preço'}
              </Text>
            </View>
            <Text style={s.price}>R$ {estimate(category).toFixed(2).replace('.', ',')}</Text>
          </Pressable>
        ))
      ) : (
        <View style={s.card}><Text style={s.muted}>Nenhuma categoria disponível nesta cidade.</Text></View>
      )}

      <Pressable style={[s.button, (!selected || !routeReady) && { opacity: 0.5 }]} onPress={requestRide}>
        <Text style={s.buttonText}>Solicitar motorista</Text>
      </Pressable>

      <View style={s.bottom}>
        <Pressable onPress={() => router.push('/safety')}><Text style={s.bottomLink}>Segurança</Text></Pressable>
        <Pressable onPress={() => router.push('/support')}><Text style={s.bottomLink}>Suporte</Text></Pressable>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.black, padding: 18 },
  header: { marginTop: 42, marginBottom: 18, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  logo: { color: colors.yellow, fontSize: 26, fontWeight: '900' },
  link: { color: colors.yellow, fontWeight: '700' },
  map: { height: 220, backgroundColor: '#101820', borderRadius: 22, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.line, padding: 16 },
  mapPin: { color: colors.yellow, fontSize: 36 },
  mapText: { color: colors.white, fontWeight: '800', fontSize: 18 },
  mapSub: { color: colors.muted, marginTop: 6, textAlign: 'center' },
  routeInfo: { color: colors.yellow, fontWeight: '800', marginTop: 10 },
  card: { backgroundColor: colors.panel, borderRadius: 18, padding: 16, marginTop: 16, borderWidth: 1, borderColor: colors.line },
  label: { color: colors.white, fontWeight: '800', marginBottom: 10 },
  input: { backgroundColor: '#0b0b0b', color: colors.white, borderRadius: 14, padding: 15, borderWidth: 1, borderColor: colors.line },
  calculate: { backgroundColor: colors.yellow, padding: 13, borderRadius: 12, alignItems: 'center', marginTop: 10 },
  calculateText: { color: '#000', fontWeight: '900' },
  shortcuts: { flexDirection: 'row', gap: 8, marginTop: 12, flexWrap: 'wrap' },
  chip: { color: colors.white, backgroundColor: colors.panel2, paddingVertical: 9, paddingHorizontal: 12, borderRadius: 999 },
  couponRow: { flexDirection: 'row', gap: 8, marginTop: 12 },
  couponButton: { backgroundColor: colors.panel2, paddingHorizontal: 16, borderRadius: 12, justifyContent: 'center' },
  couponText: { color: colors.white, fontWeight: '800' },
  couponOk: { color: colors.green, fontWeight: '800', marginTop: 8 },
  section: { color: colors.white, fontSize: 19, fontWeight: '800', marginTop: 22, marginBottom: 8 },
  category: { backgroundColor: colors.panel, borderRadius: 16, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: colors.line, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  selected: { borderColor: colors.yellow },
  categoryName: { color: colors.white, fontWeight: '900', fontSize: 17 },
  categoryMeta: { color: colors.muted, fontSize: 12, marginTop: 4, maxWidth: 250 },
  price: { color: colors.yellow, fontWeight: '900', fontSize: 17 },
  button: { backgroundColor: colors.yellow, padding: 17, borderRadius: 16, alignItems: 'center', marginTop: 14 },
  buttonText: { color: '#000', fontWeight: '900', fontSize: 17 },
  bottom: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 24 },
  bottomLink: { color: colors.muted, fontWeight: '700' },
  muted: { color: colors.muted },
})
