import {useEffect} from 'react'
import {View,Text} from 'react-native'
import {router} from 'expo-router'
import {supabase} from '@/lib/supabase'
export default function Index(){useEffect(()=>{supabase.auth.getSession().then(({data})=>router.replace(data.session?'/home':'/login'))},[]);return <View style={{flex:1,backgroundColor:'#080808',alignItems:'center',justifyContent:'center'}}><Text style={{color:'#FFD400',fontSize:28,fontWeight:'900'}}>CLICK-GO</Text><Text style={{color:'#9CA3AF',marginTop:8}}>Motorista</Text></View>}
