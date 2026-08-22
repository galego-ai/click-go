import {Modal,Pressable,StyleSheet,Text,View} from 'react-native'
import {router} from 'expo-router'
import {supabase} from '@/lib/supabase'
import {colors} from '@/lib/theme'

type Props={visible:boolean;onClose:()=>void}

const items=[
 ['⌂','Início','/home'],
 ['◷','Histórico de corridas','/history'],
 ['💳','Formas de pagamento','/wallet'],
 ['★','Favoritos','/favorites'],
 ['▣','Agendar corrida','/schedule'],
 ['👤','Meu cadastro','/profile'],
 ['🛡','Segurança','/safety'],
 ['?','Suporte','/support'],
] as const

export default function PassengerSideMenu({visible,onClose}:Props){
 async function go(path:string){onClose();router.push(path as any)}
 async function logout(){await supabase.auth.signOut();onClose();router.replace('/login')}
 return <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
  <View style={s.overlay}>
   <Pressable style={s.backdrop} onPress={onClose}/>
   <View style={s.drawer}>
    <View style={s.brand}><Text style={s.logo}>CLICK-GO</Text><Text style={s.sub}>Passageiro</Text></View>
    <View style={s.menu}>{items.map(([icon,label,path])=><Pressable key={path} style={s.item} onPress={()=>go(path)}><Text style={s.icon}>{icon}</Text><Text style={s.label}>{label}</Text></Pressable>)}</View>
    <Pressable style={s.logout} onPress={logout}><Text style={s.logoutText}>Sair da conta</Text></Pressable>
   </View>
  </View>
 </Modal>
}

const s=StyleSheet.create({
 overlay:{flex:1,flexDirection:'row'},backdrop:{...StyleSheet.absoluteFillObject,backgroundColor:'rgba(0,0,0,.65)'},drawer:{width:'84%',maxWidth:360,height:'100%',backgroundColor:colors.black,borderRightWidth:1,borderRightColor:colors.line,paddingTop:54,paddingHorizontal:20,paddingBottom:30},brand:{paddingBottom:22,borderBottomWidth:1,borderBottomColor:colors.line},logo:{color:colors.yellow,fontSize:27,fontWeight:'900'},sub:{color:colors.muted,marginTop:3},menu:{paddingTop:14,flex:1},item:{flexDirection:'row',alignItems:'center',gap:14,paddingVertical:15,borderBottomWidth:1,borderBottomColor:'#171717'},icon:{width:26,textAlign:'center',color:colors.yellow,fontSize:18},label:{color:colors.white,fontSize:16,fontWeight:'700'},logout:{borderWidth:1,borderColor:colors.yellow,borderRadius:14,padding:14,alignItems:'center'},logoutText:{color:colors.yellow,fontWeight:'900'},
})
