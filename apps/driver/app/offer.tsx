import { useEffect, useState } from 'react'
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { supabase } from '@/lib/supabase'

export default function Offer() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const [offer, setOffer] = useState<any>(null)
  const [seconds, setSeconds] = useState(0)
  const [responding, setResponding] = useState(false)

  async function load() {
    if (!id) return
    const { data, error } = await supabase
      .from('ride_offers')
      .select('*,rides(*)')
      .eq('id', id)
      .single()

    if (error) {
      Alert.alert('Corrida', error.message)
      router.replace('/home')
      return
    }

    setOffer(data)
    setSeconds(Math.max(0, Math.floor((new Date(data.expires_at).getTime() - Date.now()) / 1000)))
  }

  useEffect(() => {
    load()
  }, [id])

  useEffect(() => {
    if (!offer?.id) return
    const timer = setInterval(() => {
      setSeconds((current) => {
        if (current <= 1) {
          clearInterval(timer)
          expire()
          return 0
        }
        return current - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [offer?.id])

  async function expire() {
    if (!offer || offer.status !== 'pending' || responding) return
    setResponding(true)
    await supabase
      .from('ride_offers')
      .update({ status: 'expired', responded_at: new Date().toISOString() })
      .eq('id', offer.id)
      .eq('status', 'pending')

    await supabase.rpc('dispatch_ride', { p_ride_id: offer.ride_id })
    router.replace('/home')
  }

  async function respond(accept: boolean) {
    if (!offer || responding) return
    setResponding(true)

    const { data, error } = await supabase.rpc('respond_to_ride_offer', {
      p_offer_id: offer.id,
      p_accept: accept,
    })

    if (error) {
      setResponding(false)
      Alert.alert('Corrida', error.message)
      return
    }

    if (!data?.ok) {
      Alert.alert(
        'Corrida indisponível',
        data?.reason === 'already_taken'
          ? 'Outro motorista aceitou antes.'
          : 'Esta oferta expirou ou não está mais disponível.',
      )
      router.replace('/home')
      return
    }

    if (data.accepted) {
      router.replace({ pathname: '/ride', params: { id: data.ride_id || offer.ride_id } })
    } else {
      router.replace('/home')
    }
  }

  if (!offer) {
    return (
      <View style={s.container}>
        <Text style={s.muted}>Carregando oferta...</Text>
      </View>
    )
  }

  return (
    <View style={s.container}>
      <Text style={s.timer}>{seconds}s</Text>
      <Text style={s.title}>Nova corrida</Text>

      <View style={s.card}>
        <Text style={s.label}>Embarque</Text>
        <Text style={s.text}>{offer.rides?.origin_label}</Text>
        <Text style={s.label}>Destino</Text>
        <Text style={s.text}>{offer.rides?.destination_label}</Text>
        <Text style={s.muted}>
          {offer.distance_to_pickup_km ?? '—'} km até o passageiro • {offer.eta_to_pickup_min ?? '—'} min
        </Text>
        <Text style={s.muted}>
          Raio atual: {offer.radius_km ?? '—'} km
        </Text>
        <Text style={s.money}>
          Ganho estimado R$ {Number(offer.estimated_driver_earning || 0).toFixed(2).replace('.', ',')}
        </Text>
      </View>

      <Pressable style={[s.accept, responding && s.disabled]} disabled={responding} onPress={() => respond(true)}>
        <Text style={s.acceptText}>{responding ? 'PROCESSANDO...' : 'ACEITAR'}</Text>
      </Pressable>
      <Pressable style={[s.reject, responding && s.disabled]} disabled={responding} onPress={() => respond(false)}>
        <Text style={s.white}>Recusar</Text>
      </Pressable>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#080808', padding: 22, justifyContent: 'center' },
  timer: { color: '#FFD400', fontSize: 50, fontWeight: '900', textAlign: 'center' },
  title: { color: '#fff', fontSize: 28, fontWeight: '900', textAlign: 'center', marginBottom: 16 },
  card: { backgroundColor: '#141414', borderRadius: 18, padding: 18, borderWidth: 1, borderColor: '#292929' },
  label: { color: '#9CA3AF', fontSize: 12, marginTop: 8 },
  text: { color: '#fff', fontWeight: '800', fontSize: 17, marginTop: 3 },
  muted: { color: '#9CA3AF', marginTop: 12 },
  money: { color: '#FFD400', fontSize: 20, fontWeight: '900', marginTop: 16 },
  accept: { backgroundColor: '#FFD400', padding: 18, borderRadius: 14, alignItems: 'center', marginTop: 16 },
  reject: { backgroundColor: '#2a1111', padding: 16, borderRadius: 14, alignItems: 'center', marginTop: 10 },
  acceptText: { color: '#000', fontWeight: '900', fontSize: 18 },
  white: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.6 },
})
