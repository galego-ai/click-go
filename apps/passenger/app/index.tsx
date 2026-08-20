import { useEffect } from 'react'
import { ActivityIndicator, View } from 'react-native'
import { router } from 'expo-router'
import { supabase } from '@/lib/supabase'
import { colors } from '@/lib/theme'

export default function Index(){
  useEffect(()=>{(async()=>{
    const {data:{session}}=await supabase.auth.getSession()
    router.replace(session ? '/home' : '/login')
  })()},[])
  return <View style={{flex:1,backgroundColor:colors.black,alignItems:'center',justifyContent:'center'}}><ActivityIndicator color={colors.yellow}/></View>
}
