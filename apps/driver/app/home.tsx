import { useEffect, useRef, useState } from 'react'
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import * as Location from 'expo-location'
import { router } from 'expo-router'
import MapView, { Marker, PROVIDER_GOOGLE } from 'react-native-maps'
import { supabase } from '@/lib/supabase'

export default function Home() {
  const [driver, setDriver] = useState<any>(null)
  const [offers, setOffers] = useState<any[]>([])
  const [loc, setLoc] = useState<any>(null)
  const watch = useRef<Location.LocationSubscription | null>(null)

  async function load() {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return router.replace('/login')

    const d = await supabase.from('drivers').select('*,profiles(full_name,avatar_url),vehicles(*)').eq('id', user.id).single()
    setDriver(d.data)

    const o = await supabase
      .from('ride_offers')
      .select('*,rides(origin_label,destination_label,estimated_fare,estimated_distance_km)')
      .eq('driver_id', user.id)
      .eq('status', 'pending')
      .gt('expires_at', new Date().toISOString())
      .order('created_at', { ascending: false })
    setOffers(o.data || [])

    const p = await Location.getForegroundPermissionsAsync()
    if (p.status === 'granted') {
      const current = await Location.getLastKnownPositionAsync()
      if (current?.coords) setLoc(current.coords)
    }
  }

  useEffect(() => {
    load()
    const ch = supabase.channel('driver-offers').on('postgres_changes', { event: '*', schema: 'public', table: 'ride_offers' }, load).subscribe()
    return () => {
      supabase.removeChannel(ch)
      watch.current?.remove()
    }
  }, [])

  async function toggle() {
    if (!driver) return
    if (driver.status !== 'approved') return Alert.alert('Conta em análise', 'Você só poderá ficar online após aprovação do franqueado.')
    const online = !driver.online

    if (online) {
      const p = await Location.requestForegroundPermissionsAsync()
      if (p.status !== 'granted') return Alert.alert('Localização', 'Permissão necessária.')
      watch.current = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, timeInterval: 5000, distanceInterval: 20 },
        async (position) => {
          setLoc(position.coords)
          await supabase.from('driver_locations').upsert({
            driver_id: driver.id,
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            heading: position.coords.heading,
            speed_kmh: (position.coords.speed || 0) * 3.6,
            updated_at: new Date().toISOString(),
          })
        },
      )
    } else {
      watch.current?.remove()
    }

    await supabase.from('drivers').update({ online }).eq('id', driver.id)
    load()
  }

  return (
    <ScrollView style={s.sc} contentContainerStyle={{ padding: 18, paddingBottom: 40 }}>
      <View style={s.top}>
        <View>
          <Text style={s.logo}>CLICK-GO</Text>
          <Text style={s.name}>{driver?.profiles?.full_name || 'Motorista'}</Text>
        </View>
        <Pressable style={[s.online, driver?.online && s.onlineOn]} onPress={toggle}>
          <Text style={s.onlineText}>{driver?.online ? 'ONLINE' : 'OFFLINE'}</Text>
        </Pressable>
      </View>

      <View style={s.mapWrap}>
        {loc ? (
          <MapView
            provider={PROVIDER_GOOGLE}
            style={StyleSheet.absoluteFill}
            showsUserLocation
            showsMyLocationButton
            initialRegion={{
              latitude: loc.latitude,
              longitude: loc.longitude,
              latitudeDelta: 0.02,
              longitudeDelta: 0.02,
            }}
            region={{
              latitude: loc.latitude,
              longitude: loc.longitude,
              latitudeDelta: 0.02,
              longitudeDelta: 0.02,
            }}
          >
            <Marker
              coordinate={{ latitude: loc.latitude, longitude: loc.longitude }}
              title="Você está aqui"
              description={driver?.online ? 'Disponível para corridas' : 'Offline'}
            />
          </MapView>
        ) : (
          <View style={s.mapFallback}>
            <Text style={s.pin}>●</Text>
            <Text style={s.muted}>Ative-se para mostrar sua localização no mapa</Text>
          </View>
        )}
      </View>

      <View style={s.grid}>
        <Pressable style={s.card} onPress={() => router.push('/wallet')}><Text style={s.k}>Carteira</Text><Text style={s.v}>Saldo e Pix</Text></Pressable>
        <Pressable style={s.card} onPress={() => router.push('/earnings')}><Text style={s.k}>Ganhos</Text><Text style={s.v}>Dia • Semana • Mês</Text></Pressable>
        <Pressable style={s.card} onPress={() => router.push('/documents')}><Text style={s.k}>Documentos</Text><Text style={s.v}>CNH • CRLV • CPF</Text></Pressable>
        <Pressable style={s.card} onPress={() => router.push('/support')}><Text style={s.k}>Suporte</Text><Text style={s.v}>Falar com a operação</Text></Pressable>
      </View>

      <Text style={s.section}>Chamadas próximas</Text>
      {offers.length ? offers.map((o) => (
        <Pressable key={o.id} style={s.offer} onPress={() => router.push({ pathname: '/offer', params: { id: o.id } })}>
          <View style={{ flex: 1 }}>
            <Text style={s.k}>{o.rides?.origin_label}</Text>
            <Text style={s.muted}>→ {o.rides?.destination_label}</Text>
            <Text style={s.muted}>{o.distance_to_pickup_km ?? '—'} km até passageiro • {o.eta_to_pickup_min ?? '—'} min</Text>
          </View>
          <Text style={s.money}>R$ {Number(o.estimated_driver_earning || 0).toFixed(2).replace('.', ',')}</Text>
        </Pressable>
      )) : (
        <View style={s.card}><Text style={s.muted}>{driver?.online ? 'Aguardando chamadas próximas...' : 'Fique online para receber corridas.'}</Text></View>
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  sc: { flex: 1, backgroundColor: '#080808' },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  logo: { color: '#FFD400', fontSize: 24, fontWeight: '900' },
  name: { color: '#fff', fontSize: 18, fontWeight: '800' },
  online: { backgroundColor: '#3a1111', paddingVertical: 12, paddingHorizontal: 18, borderRadius: 999 },
  onlineOn: { backgroundColor: '#14532d' },
  onlineText: { color: '#fff', fontWeight: '900' },
  mapWrap: { height: 230, borderRadius: 20, overflow: 'hidden', marginTop: 18, borderWidth: 1, borderColor: '#292929' },
  mapFallback: { flex: 1, backgroundColor: '#101820', alignItems: 'center', justifyContent: 'center', padding: 20 },
  pin: { color: '#FFD400', fontSize: 36 },
  muted: { color: '#9CA3AF', marginTop: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 14 },
  card: { backgroundColor: '#141414', borderWidth: 1, borderColor: '#292929', borderRadius: 15, padding: 15, flexGrow: 1, minWidth: '45%' },
  k: { color: '#fff', fontWeight: '900' },
  v: { color: '#9CA3AF', marginTop: 5, fontSize: 12 },
  section: { color: '#fff', fontSize: 19, fontWeight: '900', marginTop: 22, marginBottom: 8 },
  offer: { backgroundColor: '#141414', borderWidth: 1, borderColor: '#FFD400', borderRadius: 16, padding: 16, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between', gap: 10 },
  money: { color: '#FFD400', fontWeight: '900', fontSize: 18 },
})
