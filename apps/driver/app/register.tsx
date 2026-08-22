import { useEffect, useState } from 'react'
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { router } from 'expo-router'
import { supabase } from '@/lib/supabase'

type VehicleType='car'|'motorcycle'
type RegistrationCity={city_id:string;city_name:string;state:string;franchise_id:string;franchise_name:string}

function digits(v:string){return v.replace(/\D/g,'')}
function isValidCpf(v:string){const cpf=digits(v);if(cpf.length!==11||/^(\d)\1{10}$/.test(cpf))return false;let sum=0;for(let i=0;i<9;i++)sum+=Number(cpf[i])*(10-i);let first=(sum*10)%11;if(first===10)first=0;if(first!==Number(cpf[9]))return false;sum=0;for(let i=0;i<10;i++)sum+=Number(cpf[i])*(11-i);let second=(sum*10)%11;if(second===10)second=0;return second===Number(cpf[10])}

export default function Register(){
 const[form,setForm]=useState({name:'',email:'',password:'',phone:'',cpf:'',cnh:'',category:'B',plate:'',make:'',model:'',year:'',color:''})
 const[vehicleType,setVehicleType]=useState<VehicleType>('car');const[cities,setCities]=useState<RegistrationCity[]>([]);const[selectedCity,setSelectedCity]=useState('');const[loading,setLoading]=useState(false)
 const set=(key:string,value:string)=>setForm({...form,[key]:value})
 useEffect(()=>{(async()=>{const{data,error}=await supabase.rpc('list_driver_registration_cities');if(error){Alert.alert('Cidades',error.message);return}setCities((data||[]) as RegistrationCity[])})()},[])
 async function save(){
  if(!selectedCity){Alert.alert('Escolha a cidade','Selecione a cidade onde deseja trabalhar. Seu cadastro será enviado ao franqueado responsável por ela.');return}
  if(form.name.trim().length<3||!form.email.includes('@')||form.password.length<6||digits(form.phone).length<10){Alert.alert('Cadastro','Confira nome, e-mail, telefone e senha.');return}
  if(!isValidCpf(form.cpf)){Alert.alert('CPF inválido','Informe um CPF válido.');return}
  if(!form.cnh.trim()||!form.plate.trim()||!form.make.trim()||!form.model.trim()){Alert.alert('Cadastro','Preencha CNH e os dados do veículo.');return}
  const selected=cities.find(c=>c.city_id===selectedCity);if(!selected){Alert.alert('Cidade indisponível','Escolha novamente a cidade.');return}
  setLoading(true)
  const{data,error}=await supabase.auth.signUp({email:form.email.trim().toLowerCase(),password:form.password,options:{data:{app_role:'driver',full_name:form.name.trim(),phone:form.phone.trim(),cpf:digits(form.cpf),requested_city_id:selected.city_id,cnh_number:form.cnh.trim(),cnh_category:form.category.trim(),vehicle_plate:form.plate.trim(),vehicle_make:form.make.trim(),vehicle_model:form.model.trim(),vehicle_year:form.year.trim(),vehicle_color:form.color.trim(),vehicle_type:vehicleType}}})
  setLoading(false)
  if(error){const m=error.message.toLowerCase().includes('database')?'Não foi possível concluir. Confira se o CPF já está cadastrado e se a cidade possui franqueado ativo.':error.message;Alert.alert('Cadastro',m);return}
  if(!data.user){Alert.alert('Cadastro','Não foi possível criar a conta.');return}
  Alert.alert('Cadastro enviado',`Seu cadastro foi enviado para análise do franqueado de ${selected.city_name}/${selected.state}. Você só poderá ficar online após a aprovação.`)
  router.replace('/login')
 }
 return <ScrollView style={s.screen} contentContainerStyle={{padding:20,paddingBottom:40}}><Text style={s.title}>Cadastro do motorista</Text><Text style={s.subtitle}>Escolha primeiro a cidade onde você pretende trabalhar.</Text>
  <Text style={s.section}>Cidade de atuação</Text>{cities.length===0?<View style={s.notice}><Text style={s.noticeText}>Nenhuma cidade está liberada para cadastro no momento. O Super Admin precisa vincular a cidade a um franqueado ativo.</Text></View>:cities.map(c=><Pressable key={`${c.city_id}-${c.franchise_id}`} style={[s.city,selectedCity===c.city_id&&s.citySelected]} onPress={()=>setSelectedCity(c.city_id)}><Text style={[s.cityName,selectedCity===c.city_id&&s.cityNameSelected]}>{c.city_name}/{c.state}</Text><Text style={[s.cityFranchise,selectedCity===c.city_id&&s.cityNameSelected]}>Validação: {c.franchise_name}</Text></Pressable>)}
  <Text style={s.section}>Dados pessoais e veículo</Text>{[['name','Nome completo'],['email','E-mail'],['password','Senha'],['phone','Telefone'],['cpf','CPF'],['cnh','CNH'],['category','Categoria CNH'],['plate','Placa'],['make','Marca'],['model','Modelo'],['year','Ano'],['color','Cor']].map(([key,label])=><TextInput key={key} style={s.input} placeholder={label} placeholderTextColor="#777" secureTextEntry={key==='password'} keyboardType={key==='year'||key==='cpf'||key==='phone'?'number-pad':key==='email'?'email-address':'default'} autoCapitalize={key==='email'?'none':'sentences'} value={(form as any)[key]} onChangeText={v=>set(key,v)}/>)}
  <Text style={s.vehicleLabel}>Tipo do veículo</Text><View style={s.vehicleRow}><Pressable style={[s.vehicleButton,vehicleType==='car'&&s.vehicleSelected]} onPress={()=>setVehicleType('car')}><Text style={[s.vehicleText,vehicleType==='car'&&s.vehicleTextSelected]}>Carro</Text></Pressable><Pressable style={[s.vehicleButton,vehicleType==='motorcycle'&&s.vehicleSelected]} onPress={()=>setVehicleType('motorcycle')}><Text style={[s.vehicleText,vehicleType==='motorcycle'&&s.vehicleTextSelected]}>Moto</Text></Pressable></View>
  <Text style={s.note}>Depois do cadastro, envie foto, CNH e CRLV pela área de documentos. O franqueado responsável pela cidade selecionada receberá um alerta e fará a aprovação.</Text><Pressable style={[s.button,loading&&{opacity:.6}]} onPress={save} disabled={loading}><Text style={s.buttonText}>{loading?'Enviando...':'Enviar cadastro'}</Text></Pressable>
 </ScrollView>
}
const s=StyleSheet.create({screen:{flex:1,backgroundColor:'#080808'},title:{color:'#FFD400',fontSize:26,fontWeight:'900',marginBottom:5},subtitle:{color:'#9CA3AF',lineHeight:20,marginBottom:16},section:{color:'#fff',fontWeight:'900',fontSize:16,marginTop:8,marginBottom:10},city:{backgroundColor:'#141414',borderWidth:1,borderColor:'#292929',borderRadius:13,padding:14,marginBottom:8},citySelected:{backgroundColor:'#FFD400',borderColor:'#FFD400'},cityName:{color:'#fff',fontWeight:'900'},cityFranchise:{color:'#9CA3AF',fontSize:12,marginTop:4},cityNameSelected:{color:'#000'},notice:{backgroundColor:'#141414',borderWidth:1,borderColor:'#292929',borderRadius:13,padding:14,marginBottom:12},noticeText:{color:'#FFD400',lineHeight:19},input:{backgroundColor:'#141414',color:'#fff',borderWidth:1,borderColor:'#292929',borderRadius:12,padding:13,marginBottom:9},vehicleLabel:{color:'#fff',fontWeight:'800',marginTop:5,marginBottom:8},vehicleRow:{flexDirection:'row',gap:10,marginBottom:8},vehicleButton:{flex:1,backgroundColor:'#141414',borderWidth:1,borderColor:'#292929',borderRadius:12,padding:14,alignItems:'center'},vehicleSelected:{backgroundColor:'#FFD400',borderColor:'#FFD400'},vehicleText:{color:'#fff',fontWeight:'800'},vehicleTextSelected:{color:'#000'},note:{color:'#9CA3AF',lineHeight:20,marginVertical:10},button:{backgroundColor:'#FFD400',padding:15,borderRadius:12,alignItems:'center'},buttonText:{fontWeight:'900',color:'#000'}})
