import {useState} from 'react'
import {Alert,Pressable,StyleSheet,Text,TextInput,View} from 'react-native'
import {router} from 'expo-router'
import {supabase} from '@/lib/supabase'
import {colors} from '@/lib/theme'

export default function Login(){
  const[phone,setPhone]=useState('+55')
  const[token,setToken]=useState('')
  const[sent,setSent]=useState(false)
  const[loading,setLoading]=useState(false)
  const[registerMode,setRegisterMode]=useState(false)

  async function send(){
    const cleanPhone=phone.trim()
    if(cleanPhone.length<12){
      Alert.alert('Telefone inválido','Informe o telefone com DDD, por exemplo: +55 62 99999-9999.')
      return
    }

    setLoading(true)
    const {error}=await supabase.auth.signInWithOtp({
      phone:cleanPhone,
      options:{shouldCreateUser:registerMode},
    })
    setLoading(false)

    if(error){
      Alert.alert(
        registerMode?'Não foi possível cadastrar':'Não foi possível entrar',
        registerMode?error.message:'Confira se este telefone já possui cadastro. Se ainda não tiver conta, toque em "Cadastre-se".',
      )
      return
    }

    setPhone(cleanPhone)
    setSent(true)
  }

  async function verify(){
    setLoading(true)
    const {data,error}=await supabase.auth.verifyOtp({phone,token,type:'sms'})

    if(error){
      setLoading(false)
      Alert.alert('Código inválido',error.message)
      return
    }

    if(data.user){
      if(registerMode){
        const {error:profileError}=await supabase.from('profiles').upsert(
          {id:data.user.id,role:'passenger',phone,active:true},
          {onConflict:'id'},
        )
        if(profileError){
          setLoading(false)
          Alert.alert('Cadastro não concluído',profileError.message)
          return
        }
      }
      router.replace('/home')
    }

    setLoading(false)
  }

  function changeMode(){
    setRegisterMode(value=>!value)
    setSent(false)
    setToken('')
  }

  return <View style={s.screen}>
    <Text style={s.logo}>CLICK-GO</Text>
    <Text style={s.title}>{sent?'Digite o código':registerMode?'Crie sua conta':'Entre com seu telefone'}</Text>
    <Text style={s.sub}>
      {sent
        ? `Enviamos um código por SMS para ${phone}.`
        : registerMode
          ? 'Cadastre-se gratuitamente com seu telefone para solicitar suas corridas.'
          : 'Informe o telefone que você já cadastrou para entrar.'}
    </Text>

    {!sent
      ? <TextInput style={s.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+55 62 99999-9999" placeholderTextColor={colors.muted}/>
      : <TextInput style={s.input} value={token} onChangeText={setToken} keyboardType="number-pad" placeholder="Código SMS" placeholderTextColor={colors.muted}/>
    }

    <Pressable style={s.button} onPress={sent?verify:send} disabled={loading}>
      <Text style={s.buttonText}>{loading?'Aguarde...':sent?'Confirmar código':registerMode?'Cadastrar':'Entrar'}</Text>
    </Pressable>

    {sent&&<Pressable onPress={()=>setSent(false)}><Text style={s.link}>Alterar telefone</Text></Pressable>}

    {!sent&&<View style={s.accountRow}>
      <Text style={s.accountText}>{registerMode?'Já tem uma conta?':'Ainda não tem uma conta?'}</Text>
      <Pressable onPress={changeMode}>
        <Text style={s.accountLink}>{registerMode?'Entrar':'Cadastre-se'}</Text>
      </Pressable>
    </View>}

    <Text style={s.note}>{registerMode?'Seu cadastro será confirmado pelo código SMS.':'Recuperação de acesso: solicite um novo código SMS a qualquer momento.'}</Text>
  </View>
}

const s=StyleSheet.create({
  screen:{flex:1,backgroundColor:colors.black,padding:24,justifyContent:'center'},
  logo:{color:colors.yellow,fontSize:30,fontWeight:'900',marginBottom:28},
  title:{color:colors.white,fontSize:28,fontWeight:'800'},
  sub:{color:colors.muted,fontSize:15,lineHeight:22,marginTop:8,marginBottom:24},
  input:{backgroundColor:colors.panel,color:colors.white,borderWidth:1,borderColor:colors.line,borderRadius:14,padding:16,fontSize:18},
  button:{backgroundColor:colors.yellow,padding:16,borderRadius:14,alignItems:'center',marginTop:14},
  buttonText:{color:'#000',fontWeight:'900',fontSize:16},
  link:{color:colors.yellow,textAlign:'center',marginTop:18,fontWeight:'700'},
  accountRow:{flexDirection:'row',justifyContent:'center',alignItems:'center',gap:6,marginTop:24},
  accountText:{color:colors.muted,fontSize:14},
  accountLink:{color:colors.yellow,fontSize:14,fontWeight:'900'},
  note:{color:colors.muted,fontSize:12,textAlign:'center',marginTop:28},
})
