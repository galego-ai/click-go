import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { colors } from '@/lib/theme'

export default function RootLayout() {
  return <>
    <StatusBar style="light" />
    <Stack screenOptions={{headerStyle:{backgroundColor:colors.black},headerTintColor:colors.white,contentStyle:{backgroundColor:colors.black}}}>
      <Stack.Screen name="index" options={{headerShown:false}} />
      <Stack.Screen name="login" options={{title:'Entrar'}} />
      <Stack.Screen name="register" options={{title:'Cadastro'}} />
      <Stack.Screen name="home" options={{headerShown:false}} />
      <Stack.Screen name="ride" options={{title:'Sua corrida'}} />
      <Stack.Screen name="history" options={{title:'Histórico'}} />
      <Stack.Screen name="favorites" options={{title:'Favoritos'}} />
      <Stack.Screen name="schedule" options={{title:'Agendar corrida'}} />
      <Stack.Screen name="wallet" options={{title:'Pagamentos'}} />
      <Stack.Screen name="support" options={{title:'Suporte'}} />
      <Stack.Screen name="safety" options={{title:'Segurança'}} />
    </Stack>
  </>
}
