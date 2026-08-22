import {useState} from 'react'
import {Alert,Image,Pressable,ScrollView,StyleSheet,Text,TextInput,View} from 'react-native'
import {router} from 'expo-router'
import * as ImagePicker from 'expo-image-picker'
import {supabase} from '@/lib/supabase'
import {colors} from '@/lib/theme'
import {savePendingPassengerAvatar, uploadPassengerAvatar} from '@/lib/passengerAvatar'

type Photo = {uri:string; mimeType:string}

function digits(value:string){return value.replace(/\D/g,'')}

function formatCpf(value:string){
  const d=digits(value).slice(0,11)
  if(d.length<=3)return d
  if(d.length<=6)return `${d.slice(0,3)}.${d.slice(3)}`
  if(d.length<=9)return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`
  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`
}

function isValidCpf(value:string){
  const cpf=digits(value)
  if(cpf.length!==11||/^(\d)\1{10}$/.test(cpf))return false

  let sum=0
  for(let i=0;i<9;i++)sum+=Number(cpf[i])*(10-i)
  let first=(sum*10)%11
  if(first===10)first=0
  if(first!==Number(cpf[9]))return false

  sum=0
  for(let i=0;i<10;i++)sum+=Number(cpf[i])*(11-i)
  let second=(sum*10)%11
  if(second===10)second=0
  return second===Number(cpf[10])
}

export default function Register(){
  const[fullName,setFullName]=useState('')
  const[phone,setPhone]=useState('')
  const[email,setEmail]=useState('')
  const[cpf,setCpf]=useState('')
  const[password,setPassword]=useState('')
  const[confirmPassword,setConfirmPassword]=useState('')
  const[photo,setPhoto]=useState<Photo|null>(null)
  const[loading,setLoading]=useState(false)

  async function selectPhoto(source:'camera'|'library'){
    if(source==='camera'){
      const permission=await ImagePicker.requestCameraPermissionsAsync()
      if(!permission.granted){Alert.alert('Permissão necessária','Autorize o uso da câmera para tirar sua foto.');return}
    }else{
      const permission=await ImagePicker.requestMediaLibraryPermissionsAsync()
      if(!permission.granted){Alert.alert('Permissão necessária','Autorize o acesso às fotos para escolher sua foto de perfil.');return}
    }

    const result=source==='camera'
      ? await ImagePicker.launchCameraAsync({mediaTypes:ImagePicker.MediaTypeOptions.Images,allowsEditing:true,aspect:[1,1],quality:0.7})
      : await ImagePicker.launchImageLibraryAsync({mediaTypes:ImagePicker.MediaTypeOptions.Images,allowsEditing:true,aspect:[1,1],quality:0.7})

    if(!result.canceled&&result.assets[0]){
      const asset=result.assets[0]
      setPhoto({uri:asset.uri,mimeType:asset.mimeType||'image/jpeg'})
    }
  }

  async function register(){
    const cleanEmail=email.trim().toLowerCase()
    const cleanPhone=phone.trim()
    const cleanCpf=digits(cpf)
    const cleanName=fullName.trim()

    if(cleanName.length<3){Alert.alert('Nome inválido','Informe seu nome completo.');return}
    if(digits(cleanPhone).length<10){Alert.alert('Telefone inválido','Informe um telefone com DDD.');return}
    if(!/^\S+@\S+\.\S+$/.test(cleanEmail)){Alert.alert('E-mail inválido','Informe um e-mail válido.');return}
    if(!isValidCpf(cleanCpf)){Alert.alert('CPF inválido','Confira o CPF. O cadastro só aceita CPF com dígitos verificadores válidos.');return}
    if(!photo){Alert.alert('Foto obrigatória','Adicione uma foto sua para concluir o cadastro.');return}
    if(password.length<6){Alert.alert('Senha inválida','A senha deve ter pelo menos 6 caracteres.');return}
    if(password!==confirmPassword){Alert.alert('Senhas diferentes','A confirmação da senha não confere.');return}

    setLoading(true)
    const {data,error}=await supabase.auth.signUp({
      email:cleanEmail,
      password,
      options:{data:{app_role:'passenger',full_name:cleanName,phone:cleanPhone,cpf:cleanCpf}},
    })

    if(error){
      setLoading(false)
      const message=error.message.toLowerCase().includes('already')
        ? 'Este e-mail já possui cadastro.'
        : error.message.toLowerCase().includes('database')
          ? 'Não foi possível concluir. Confira se este CPF já está cadastrado.'
          : error.message
      Alert.alert('Não foi possível cadastrar',message)
      return
    }

    if(data.user?.identities&&data.user.identities.length===0){
      setLoading(false)
      Alert.alert('E-mail já cadastrado','Use a opção Entrar para acessar sua conta.')
      return
    }

    if(!data.user){
      setLoading(false)
      Alert.alert('Cadastro não concluído','Não foi possível criar sua conta. Tente novamente.')
      return
    }

    if(data.session){
      try{
        await uploadPassengerAvatar(data.user.id,photo.uri,photo.mimeType)
      }catch{
        await savePendingPassengerAvatar(cleanEmail,photo.uri,photo.mimeType)
      }
      setLoading(false)
      router.replace('/home')
      return
    }

    await savePendingPassengerAvatar(cleanEmail,photo.uri,photo.mimeType)
    setLoading(false)
    Alert.alert(
      'Confirme seu e-mail',
      'Sua conta foi criada. Abra o e-mail de confirmação e depois entre no CLICK-GO. Sua foto será enviada no primeiro acesso.',
      [{text:'OK',onPress:()=>router.replace('/login')}],
    )
  }

  return <ScrollView style={s.screen} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
    <Text style={s.logo}>CLICK-GO</Text>
    <Text style={s.title}>Criar conta</Text>
    <Text style={s.sub}>Preencha seus dados para usar o CLICK-GO Passageiro.</Text>

    <View style={s.photoArea}>
      {photo?<Image source={{uri:photo.uri}} style={s.photo}/>:<View style={s.photoPlaceholder}><Text style={s.photoInitial}>+</Text></View>}
      <View style={s.photoButtons}>
        <Pressable style={s.secondaryButton} onPress={()=>selectPhoto('camera')}><Text style={s.secondaryText}>Tirar foto</Text></Pressable>
        <Pressable style={s.secondaryButton} onPress={()=>selectPhoto('library')}><Text style={s.secondaryText}>Galeria</Text></Pressable>
      </View>
    </View>

    <Text style={s.label}>Nome completo</Text>
    <TextInput style={s.input} value={fullName} onChangeText={setFullName} placeholder="Seu nome completo" placeholderTextColor={colors.muted} autoCapitalize="words"/>

    <Text style={s.label}>Telefone</Text>
    <TextInput style={s.input} value={phone} onChangeText={setPhone} placeholder="(62) 99999-9999" placeholderTextColor={colors.muted} keyboardType="phone-pad"/>

    <Text style={s.label}>E-mail</Text>
    <TextInput style={s.input} value={email} onChangeText={setEmail} placeholder="voce@email.com" placeholderTextColor={colors.muted} keyboardType="email-address" autoCapitalize="none" autoCorrect={false}/>

    <Text style={s.label}>CPF</Text>
    <TextInput style={s.input} value={cpf} onChangeText={v=>setCpf(formatCpf(v))} placeholder="000.000.000-00" placeholderTextColor={colors.muted} keyboardType="number-pad" maxLength={14}/>
    <Text style={s.hint}>O CPF é conferido pelos dígitos verificadores e não pode estar duplicado.</Text>

    <Text style={s.label}>Senha</Text>
    <TextInput style={s.input} value={password} onChangeText={setPassword} placeholder="Mínimo de 6 caracteres" placeholderTextColor={colors.muted} secureTextEntry autoCapitalize="none"/>

    <Text style={s.label}>Confirmar senha</Text>
    <TextInput style={s.input} value={confirmPassword} onChangeText={setConfirmPassword} placeholder="Digite a senha novamente" placeholderTextColor={colors.muted} secureTextEntry autoCapitalize="none"/>

    <Pressable style={[s.button,loading&&s.disabled]} onPress={register} disabled={loading}>
      <Text style={s.buttonText}>{loading?'Cadastrando...':'Cadastrar'}</Text>
    </Pressable>

    <Pressable onPress={()=>router.replace('/login')} disabled={loading}>
      <Text style={s.link}>Já tem uma conta? Entrar</Text>
    </Pressable>
  </ScrollView>
}

const s=StyleSheet.create({
  screen:{flex:1,backgroundColor:colors.black},
  content:{padding:24,paddingBottom:48},
  logo:{color:colors.yellow,fontSize:28,fontWeight:'900',marginTop:12,marginBottom:18},
  title:{color:colors.white,fontSize:28,fontWeight:'800'},
  sub:{color:colors.muted,fontSize:15,lineHeight:22,marginTop:6,marginBottom:24},
  photoArea:{alignItems:'center',marginBottom:20},
  photo:{width:112,height:112,borderRadius:56,borderWidth:3,borderColor:colors.yellow},
  photoPlaceholder:{width:112,height:112,borderRadius:56,borderWidth:2,borderColor:colors.line,backgroundColor:colors.panel,alignItems:'center',justifyContent:'center'},
  photoInitial:{color:colors.yellow,fontSize:46,fontWeight:'300'},
  photoButtons:{flexDirection:'row',gap:10,marginTop:12},
  secondaryButton:{borderWidth:1,borderColor:colors.yellow,borderRadius:12,paddingVertical:10,paddingHorizontal:18},
  secondaryText:{color:colors.yellow,fontWeight:'800'},
  label:{color:colors.white,fontWeight:'700',fontSize:14,marginTop:14,marginBottom:7},
  input:{backgroundColor:colors.panel,color:colors.white,borderWidth:1,borderColor:colors.line,borderRadius:14,padding:15,fontSize:16},
  hint:{color:colors.muted,fontSize:12,lineHeight:17,marginTop:6},
  button:{backgroundColor:colors.yellow,padding:17,borderRadius:14,alignItems:'center',marginTop:28},
  disabled:{opacity:0.6},
  buttonText:{color:'#000',fontWeight:'900',fontSize:16},
  link:{color:colors.yellow,textAlign:'center',fontWeight:'800',marginTop:22},
})
