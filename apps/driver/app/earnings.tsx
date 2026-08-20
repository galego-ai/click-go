import { useEffect, useMemo, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { supabase } from '@/lib/supabase'

export default function Earnings() {
  const [rides, setRides] = useState<any[]>([])
  const [goals, setGoals] = useState<any[]>([])
  const [ratings, setRatings] = useState<any[]>([])

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const [ridesResult, goalsResult, ratingsResult] = await Promise.all([
        supabase
          .from('rides')
          .select('id,final_fare,estimated_fare,completed_at,origin_label,destination_label')
          .eq('driver_id', user.id)
          .eq('status', 'completed')
          .order('completed_at', { ascending: false })
          .limit(200),
        supabase
          .from('driver_goals')
          .select('*')
          .eq('driver_id', user.id)
          .eq('active', true)
          .order('starts_at', { ascending: false }),
        supabase
          .from('ride_ratings')
          .select('rating,comment,created_at')
          .eq('driver_id', user.id)
          .order('created_at', { ascending: false })
          .limit(50),
      ])

      setRides(ridesResult.data || [])
      setGoals(goalsResult.data || [])
      setRatings(ratingsResult.data || [])
    }

    load()
  }, [])

  const stats = useMemo(() => {
    const now = new Date()
    const startDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const startWeek = new Date(startDay)
    startWeek.setDate(startDay.getDate() - startDay.getDay())
    const startMonth = new Date(now.getFullYear(), now.getMonth(), 1)

    const sum = (from: Date) =>
      rides
        .filter((ride) => ride.completed_at && new Date(ride.completed_at) >= from)
        .reduce((total, ride) => total + Number(ride.final_fare || ride.estimated_fare || 0), 0)

    return {
      day: sum(startDay),
      week: sum(startWeek),
      month: sum(startMonth),
    }
  }, [rides])

  const brl = (value: any) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value || 0))

  return (
    <ScrollView style={s.sc} contentContainerStyle={{ padding: 18, paddingBottom: 40 }}>
      <Text style={s.h}>Ganhos</Text>
      <View style={s.grid}>
        {[
          ['Hoje', stats.day],
          ['Semana', stats.week],
          ['Mês', stats.month],
        ].map(([label, value]) => (
          <View style={s.card} key={String(label)}>
            <Text style={s.m}>{label}</Text>
            <Text style={s.money}>{brl(value)}</Text>
          </View>
        ))}
      </View>

      <Text style={s.section}>Metas</Text>
      {goals.length ? (
        goals.map((goal) => (
          <View style={s.row} key={goal.id}>
            <View>
              <Text style={s.white}>{String(goal.period_type).toUpperCase()}</Text>
              <Text style={s.m}>{goal.target_rides} corridas • meta {brl(goal.target_earnings)}</Text>
            </View>
            <Text style={s.yellow}>Bônus {brl(goal.bonus_amount)}</Text>
          </View>
        ))
      ) : (
        <Text style={s.m}>Nenhuma meta ativa.</Text>
      )}

      <Text style={s.section}>Histórico</Text>
      {rides.map((ride) => (
        <View style={s.row} key={ride.id}>
          <View style={{ flex: 1 }}>
            <Text style={s.white}>{ride.origin_label} → {ride.destination_label}</Text>
            <Text style={s.m}>{ride.completed_at ? new Date(ride.completed_at).toLocaleString('pt-BR') : '—'}</Text>
          </View>
          <Text style={s.white}>{brl(ride.final_fare || ride.estimated_fare)}</Text>
        </View>
      ))}

      <Text style={s.section}>Avaliações</Text>
      {ratings.map((rating, index) => (
        <View style={s.row} key={`${rating.created_at || index}-${index}`}>
          <View>
            <Text style={s.yellow}>{'★'.repeat(Number(rating.rating || 0))}</Text>
            <Text style={s.m}>{rating.comment || 'Sem comentário'}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  sc: { flex: 1, backgroundColor: '#080808' },
  h: { color: '#FFD400', fontSize: 27, fontWeight: '900' },
  grid: { flexDirection: 'row', gap: 8, marginTop: 14 },
  card: { flex: 1, backgroundColor: '#141414', padding: 14, borderRadius: 14, borderWidth: 1, borderColor: '#292929' },
  m: { color: '#9CA3AF', fontSize: 12 },
  money: { color: '#fff', fontWeight: '900', fontSize: 17, marginTop: 5 },
  section: { color: '#fff', fontSize: 19, fontWeight: '900', marginTop: 22, marginBottom: 8 },
  row: { backgroundColor: '#141414', padding: 14, borderRadius: 12, marginTop: 7, flexDirection: 'row', justifyContent: 'space-between', gap: 10 },
  white: { color: '#fff', fontWeight: '800' },
  yellow: { color: '#FFD400', fontWeight: '900' },
})
