import { useState } from 'react'
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { router } from 'expo-router'
import { supabase } from '@/lib/supabase'

type VehicleType = 'car' | 'motorcycle'

export default function Register() {
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    phone: '',
    cpf: '',
    cnh: '',
    category: 'B',
    plate: '',
    make: '',
    model: '',
    year: '',
    color: '',
  })
  const [vehicleType, setVehicleType] = useState<VehicleType>('car')

  const set = (key: string, value: string) => setForm({ ...form, [key]: value })

  async function save() {
    const { data, error } = await supabase.auth.signUp({ email: form.email, password: form.password })
    if (error || !data.user) return Alert.alert('Cadastro', error?.message || 'Falha ao criar conta')

    await supabase.from('profiles').upsert({
      id: data.user.id,
      full_name: form.name,
      phone: form.phone,
      role: 'driver',
      active: true,
    })

    await supabase.from('drivers').upsert({
      id: data.user.id,
      status: 'pending',
      online: false,
    })

    await supabase.from('driver_profiles').upsert({
      driver_id: data.user.id,
      cpf: form.cpf,
      cnh_number: form.cnh,
      cnh_category: form.category,
    })

    await supabase.from('vehicles').insert({
      driver_id: data.user.id,
      plate: form.plate,
      make: form.make,
      model: form.model,
      year: Number(form.year) || null,
      color: form.color,
      vehicle_type: vehicleType,
    })

    Alert.alert('Cadastro enviado', 'Sua conta ficará em análise até aprovação do franqueado.')
    router.replace('/login')
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
      <Text style={s.title}>Cadastro do motorista</Text>

      {[
        ['name', 'Nome completo'],
        ['email', 'E-mail'],
        ['password', 'Senha'],
        ['phone', 'Telefone'],
        ['cpf', 'CPF'],
        ['cnh', 'CNH'],
        ['category', 'Categoria CNH'],
        ['plate', 'Placa'],
        ['make', 'Marca'],
        ['model', 'Modelo'],
        ['year', 'Ano'],
        ['color', 'Cor'],
      ].map(([key, label]) => (
        <TextInput
          key={key}
          style={s.input}
          placeholder={label}
          placeholderTextColor="#777"
          secureTextEntry={key === 'password'}
          value={(form as any)[key]}
          onChangeText={(value) => set(key, value)}
        />
      ))}

      <Text style={s.vehicleLabel}>Tipo do veículo</Text>
      <View style={s.vehicleRow}>
        <Pressable
          style={[s.vehicleButton, vehicleType === 'car' && s.vehicleSelected]}
          onPress={() => setVehicleType('car')}
        >
          <Text style={[s.vehicleText, vehicleType === 'car' && s.vehicleTextSelected]}>Carro</Text>
        </Pressable>
        <Pressable
          style={[s.vehicleButton, vehicleType === 'motorcycle' && s.vehicleSelected]}
          onPress={() => setVehicleType('motorcycle')}
        >
          <Text style={[s.vehicleText, vehicleType === 'motorcycle' && s.vehicleTextSelected]}>Moto</Text>
        </Pressable>
      </View>

      <Text style={s.note}>
        O tipo do veículo será usado pelo sistema para enviar apenas corridas compatíveis com a categoria aprovada.
        Depois do cadastro, envie foto, CPF, CNH e CRLV pela área de documentos. O franqueado fará a análise.
      </Text>

      <Pressable style={s.button} onPress={save}>
        <Text style={s.buttonText}>Enviar cadastro</Text>
      </Pressable>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#080808' },
  title: { color: '#FFD400', fontSize: 26, fontWeight: '900', marginBottom: 16 },
  input: {
    backgroundColor: '#141414',
    color: '#fff',
    borderWidth: 1,
    borderColor: '#292929',
    borderRadius: 12,
    padding: 13,
    marginBottom: 9,
  },
  vehicleLabel: { color: '#fff', fontWeight: '800', marginTop: 5, marginBottom: 8 },
  vehicleRow: { flexDirection: 'row', gap: 10, marginBottom: 8 },
  vehicleButton: {
    flex: 1,
    backgroundColor: '#141414',
    borderWidth: 1,
    borderColor: '#292929',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  vehicleSelected: { backgroundColor: '#FFD400', borderColor: '#FFD400' },
  vehicleText: { color: '#fff', fontWeight: '800' },
  vehicleTextSelected: { color: '#000' },
  note: { color: '#9CA3AF', lineHeight: 20, marginVertical: 10 },
  button: { backgroundColor: '#FFD400', padding: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { fontWeight: '900', color: '#000' },
})
