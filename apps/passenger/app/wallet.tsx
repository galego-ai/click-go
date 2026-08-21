import {useEffect,useState} from 'react'
import {Alert,Linking,Pressable,ScrollView,StyleSheet,Text,TextInput,View} from 'react-native'
import {router,useLocalSearchParams} from 'expo-router'
import {supabase} from '@/lib/supabase'
import {colors} from '@/lib/theme'

const methods=['pix','cash','card','wallet']

export default function Wallet(){
 const{rideId}=useLocalSearchParams<{rideId?:string}>()
 const[ride,setRide]=useState<any>(null)
 const[method,setMethod]=useState('pix')
 const[rating,setRating]=useState('5')
 const[comment,setComment]=useState('')
 const[saved,setSaved]=useState<any[]>([])
 const[pix,setPix]=useState<any>(null)
 const[loadingPix,setLoadingPix]=useState(false)

 useEffect(()=>{(async()=>{const {data:{user}}=await supabase.auth.getUser();if(!user)return;const m=await supabase.from('passenger_payment_methods').select('*').eq('passenger_id',user.id).eq('active',true);setSaved(m.data||[]);if(rideId){const r=await supabase.from('rides').select('*').eq('id',rideId).single();setRide(r.data)}})()},[rideId])

 async function saveRatingAndReceipt(paymentMethod:string){
  if(!rideId||!ride)return
  const {data:{user}}=await supabase.auth.getUser();if(!user)return
  const amount=Number(ride.final_fare||ride.estimated_fare||0)
  if(ride.driver_id)await supabase.from('ride_ratings').upsert({ride_id:rideId,passenger_id:user.id,driver_id:ride.driver_id,rating:Number(rating),comment},{onConflict:'ride_id,passenger_id'})
  await supabase.from('ride_receipts').upsert({ride_id:rideId,passenger_id:user.id,fare:amount,discount:0,total:amount,payment_method:paymentMethod},{onConflict:'ride_id'})
 }

 async function createPix(){
  if(!rideId)return Alert.alert('Pix','Corrida não encontrada.')
  setLoadingPix(true)
  const {data,error}=await supabase.functions.invoke('efi-pix',{body:{action:'create',ride_id:rideId}})
  setLoadingPix(false)
  if(error||data?.error)return Alert.alert('Pix Efí',data?.error||error?.message||'Não foi possível gerar o Pix.')
  setPix(data)
 }

 async function checkPix(){
  if(!pix?.txid)return
  setLoadingPix(true)
  const {data,error}=await supabase.functions.invoke('efi-pix',{body:{action:'status',txid:pix.txid}})
  setLoadingPix(false)
  if(error||data?.error)return Alert.alert('Pix Efí',data?.error||error?.message||'Não foi possível consultar o Pix.')
  setPix(data)
  if(data?.status==='paid'){
   await saveRatingAndReceipt('pix')
   Alert.alert('Pagamento confirmado','Pix recebido com sucesso pela Efí.')
   router.replace('/history')
  }else Alert.alert('Pix','Pagamento ainda não confirmado.')
 }

 async function finish(){
  if(!rideId||!ride)return
  if(method==='pix')return createPix()
  const {data:{user}}=await supabase.auth.getUser();if(!user)return
  const amount=Number(ride.final_fare||ride.estimated_fare||0)
  const {error}=await supabase.from('payments').insert({ride_id:rideId,franchise_id:ride.franchise_id,payer_id:user.id,amount,method,status:method==='cash'?'authorized':'pending',provider:method==='card'?'card_provider':null})
  if(error)return Alert.alert('Pagamento',error.message)
  await saveRatingAndReceipt(method)
  Alert.alert('Concluído','Pagamento registrado e avaliação salva.')
  router.replace('/history')
 }

 return <ScrollView style={s.screen} contentContainerStyle={{padding:18}}>
  <Text style={s.title}>Pagamento</Text>
  <Text style={s.muted}>Escolha Pix, dinheiro, cartão ou carteira.</Text>
  <View style={s.methods}>{methods.map(m=><Pressable key={m} style={[s.method,method===m&&s.selected]} onPress={()=>{setMethod(m);setPix(null)}}><Text style={s.methodText}>{m==='cash'?'Dinheiro':m==='card'?'Cartão':m==='wallet'?'Carteira':'Pix Efí'}</Text></Pressable>)}</View>
  {saved.length>0&&<View style={s.card}><Text style={s.section}>Cartões/meios salvos</Text>{saved.map(x=><Text key={x.id} style={s.muted}>{x.method_type} {x.brand||''} {x.last4?`•••• ${x.last4}`:''}</Text>)}</View>}
  {rideId&&<View style={s.card}>
   <Text style={s.section}>Avalie o motorista</Text>
   <View style={s.stars}>{['1','2','3','4','5'].map(x=><Pressable key={x} onPress={()=>setRating(x)}><Text style={[s.star,Number(x)<=Number(rating)&&{color:colors.yellow}]}>★</Text></Pressable>)}</View>
   <TextInput style={s.input} value={comment} onChangeText={setComment} placeholder="Comentário opcional" placeholderTextColor={colors.muted}/>
   {method==='pix'&&pix&&<View style={s.pixBox}>
    <Text style={s.section}>Pix gerado</Text>
    <Text style={s.muted}>Valor: R$ {Number(pix.amount||0).toFixed(2).replace('.',',')}</Text>
    <Text style={s.pixCode} selectable>{pix.qrcode||'Copia e cola indisponível'}</Text>
    {pix.visualization_link&&<Pressable style={s.secondary} onPress={()=>Linking.openURL(pix.visualization_link)}><Text style={s.secondaryText}>Abrir QR Code Efí</Text></Pressable>}
    <Pressable style={s.button} onPress={checkPix} disabled={loadingPix}><Text style={s.buttonText}>{loadingPix?'Consultando...':'Verificar pagamento'}</Text></Pressable>
   </View>}
   {!pix&&<Pressable style={s.button} onPress={finish} disabled={loadingPix}><Text style={s.buttonText}>{loadingPix?'Gerando...':method==='pix'?'Gerar Pix Efí':'Confirmar pagamento e avaliação'}</Text></Pressable>}
  </View>}
 </ScrollView>
}

const s=StyleSheet.create({screen:{flex:1,backgroundColor:colors.black},title:{color:colors.white,fontSize:27,fontWeight:'900'},muted:{color:colors.muted,marginTop:7},methods:{flexDirection:'row',flexWrap:'wrap',gap:10,marginTop:18},method:{backgroundColor:colors.panel,borderWidth:1,borderColor:colors.line,borderRadius:14,paddingVertical:14,paddingHorizontal:18},selected:{borderColor:colors.yellow},methodText:{color:colors.white,fontWeight:'800'},card:{backgroundColor:colors.panel,padding:16,borderRadius:16,borderWidth:1,borderColor:colors.line,marginTop:18},section:{color:colors.white,fontWeight:'900',fontSize:18,marginBottom:10},stars:{flexDirection:'row',marginBottom:12},star:{fontSize:34,color:'#444'},input:{backgroundColor:'#0b0b0b',color:colors.white,borderWidth:1,borderColor:colors.line,borderRadius:12,padding:13},button:{backgroundColor:colors.yellow,padding:15,borderRadius:12,alignItems:'center',marginTop:12},buttonText:{color:'#000',fontWeight:'900'},pixBox:{marginTop:16,borderTopWidth:1,borderTopColor:colors.line,paddingTop:14},pixCode:{color:colors.white,backgroundColor:'#0b0b0b',borderRadius:12,padding:12,marginTop:10,fontSize:12},secondary:{borderWidth:1,borderColor:colors.yellow,padding:13,borderRadius:12,alignItems:'center',marginTop:12},secondaryText:{color:colors.yellow,fontWeight:'900'}})
