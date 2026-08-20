import { useEffect, useState } from 'react'
import {
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import MapView, { Marker } from 'react-native-maps'
import { router, useLocalSearchParams } from 'expo-router'
import { supabase } from '@/lib/supabase'

type RideRow = {
  id: string
  status: string
  driver_id: string | null
  origin_lat: number
  origin_lng: number
  destination_lat: number
  destination_lng: number
  destination_label: string
  estimated_fare: number | null
  final_fare: number | null
  profiles?: {
    full_name?: string | null
    phone?: string | null
    avatar_url?: string | null
  } | null
}

export default function Ride() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const [ride, setRide] = useState<RideRow | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [text, setText] = useState('')

  async function load() {
    if (!id) return

    const rideResult = await supabase
      .from('rides')
      .select('*,profiles:passenger_id(full_name,phone,avatar_url)')
      .eq('id', id)
      .single()

    if (rideResult.error) {
      Alert.alert('Corrida', rideResult.error.message)
      return
    }

    setRide(rideResult.data as RideRow)

    const messageResult = await supabase
      .from('ride_chat_messages')
      .select('*')
      .eq('ride_id', id)
      .order('created_at')

    setMessages(messageResult.data || [])
  }

  useEffect(() => {
    load()
    if (!id) return

    const channel = supabase
      .channel(`driver-ride-${id}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'rides', filter: `id=eq.${id}` },
        load,
      )
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'ride_chat_messages',
          filter: `ride_id=eq.${id}`,
        },
        load,
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [id])

  async function updateRide(eventType: string, status: string, extra: Record<string, unknown> = {}) {
    if (!id) return

    const {
      data: { user },
    } = await supabase.auth.getUser()

    if (!user) return

    const now = new Date().toISOString()
    const patch: Record<string, unknown> = { status, ...extra }

    if (status === 'in_progress') patch.started_at = now
    if (status === 'completed') patch.completed_at = now

    const { error } = await supabase
      .from('rides')
      .update(patch)
      .eq('id', id)
      .eq('driver_id', user.id)

    if (error) {
      Alert.alert('Corrida', error.message)
      return
    }

    await supabase.from('ride_events').insert({
      ride_id: id,
      driver_id: user.id,
      event_type: eventType,
      metadata: { source: 'driver_app' },
    })

    await load()
  }

  async function finish() {
    if (!ride) return

    await updateRide('ride_completed', 'completed', {
      final_fare: ride.final_fare || ride.estimated_fare,
    })

    router.replace('/wallet')
  }

  async function send() {
    if (!id || !text.trim()) return

    const {
      data: { user },
    } = await supabase.auth.getUser()

    if (!user) return

    await supabase.from('ride_chat_messages').insert({
      ride_id: id,
      sender_id: user.id,
      message: text.trim(),
    })

    setText('')
  }

  function navigateTo(lat: number, lng: number) {
    Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`)
  }

  if (!ride) {
    return (
      <View style={styles.center}>
        <Text style={styles.muted}>Carregando corrida...</Text>
      </View>
    )
  }

  const goingToPassenger = ride.status === 'accepted' || ride.status === 'driver_arriving'
  const target = goingToPassenger
    ? { lat: ride.origin_lat, lng: ride.origin_lng, label: 'Passageiro' }
    : { lat: ride.destination_lat, lng: ride.destination_lng, label: 'Destino' }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
      <Text style={styles.heading}>
        {ride.status === 'in_progress' ? 'Viagem em andamento' : 'Corrida ativa'}
      </Text>

      <MapView
        style={styles.map}
        initialRegion={{
          latitude: target.lat,
          longitude: target.lng,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }}
      >
        <Marker
          coordinate={{ latitude: target.lat, longitude: target.lng }}
          title={target.label}
        />
      </MapView>

      <View style={styles.card}>
        <Text style={styles.label}>Passageiro</Text>
        <Text style={styles.text}>{ride.profiles?.full_name || 'Passageiro CLICK-GO'}</Text>
        <Text style={styles.label}>Destino</Text>
        <Text style={styles.text}>{ride.destination_label}</Text>
        <Text style={styles.money}>
          Estimativa R$ {Number(ride.estimated_fare || 0).toFixed(2).replace('.', ',')}
        </Text>
        <Pressable style={styles.secondary} onPress={() => navigateTo(target.lat, target.lng)}>
          <Text style={styles.white}>Abrir navegação</Text>
        </Pressable>
      </View>

      <View style={styles.actions}>
        {ride.status === 'accepted' && (
          <Pressable
            style={styles.secondary}
            onPress={() => updateRide('arrived_pickup', 'driver_arriving')}
          >
            <Text style={styles.white}>Cheguei ao passageiro</Text>
          </Pressable>
        )}

        {ride.status === 'driver_arriving' && (
          <Pressable
            style={styles.main}
            onPress={() => updateRide('ride_started', 'in_progress')}
          >
            <Text style={styles.mainText}>Iniciar viagem</Text>
          </Pressable>
        )}

        {ride.status === 'in_progress' && (
          <Pressable style={styles.main} onPress={finish}>
            <Text style={styles.mainText}>Finalizar viagem</Text>
          </Pressable>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.text}>Chat</Text>
        {messages.slice(-6).map((message) => (
          <Text key={message.id} style={styles.message}>
            {message.message}
          </Text>
        ))}

        <View style={styles.chat}>
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="Mensagem ao passageiro"
            placeholderTextColor="#777"
          />
          <Pressable style={styles.main} onPress={send}>
            <Text style={styles.mainText}>Enviar</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#080808' },
  center: {
    flex: 1,
    backgroundColor: '#080808',
    justifyContent: 'center',
    alignItems: 'center',
  },
  heading: { color: '#FFD400', fontSize: 26, fontWeight: '900' },
  map: { height: 280, borderRadius: 18, marginTop: 12 },
  card: {
    backgroundColor: '#141414',
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#292929',
    marginTop: 12,
  },
  label: { color: '#9CA3AF', fontSize: 12, marginTop: 7 },
  text: { color: '#fff', fontWeight: '900', fontSize: 17 },
  money: { color: '#FFD400', fontWeight: '900', fontSize: 19, marginTop: 14 },
  secondary: {
    backgroundColor: '#202020',
    padding: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  main: { backgroundColor: '#FFD400', padding: 14, borderRadius: 12, alignItems: 'center' },
  white: { color: '#fff', fontWeight: '800' },
  mainText: { color: '#000', fontWeight: '900' },
  actions: { marginTop: 12 },
  muted: { color: '#9CA3AF' },
  message: { color: '#fff', backgroundColor: '#222', padding: 9, borderRadius: 10, marginTop: 6 },
  chat: { flexDirection: 'row', gap: 8, marginTop: 10 },
  input: {
    flex: 1,
    backgroundColor: '#0b0b0b',
    color: '#fff',
    borderWidth: 1,
    borderColor: '#292929',
    borderRadius: 12,
    padding: 12,
  },
})
