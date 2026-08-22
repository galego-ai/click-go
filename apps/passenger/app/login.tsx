import {useState} from 'react'
import {Alert,Pressable,StyleSheet,Text,TextInput,View} from 'react-native'
import {router} from 'expo-router'
import {supabase} from '@/lib/supabase'
import {colors} from '@/lib/theme'
import {uploadPendingPassengerAvatar} from '@/lib/passengerAvatar'

export default function Login(){
  const[email,setEmail]=useState('')
  const[password,setPassword]=useState('')
  const[loading,setLoading]=useState(false)

  async function login(){
    const cleanEmail=email.trim().toLowerCase()
    if(!/^\S+@\S+\.\S+$/.test(cleanEmail)){
      Alert.alert('E-mail inválido','Informe o e-mail usado no cadastro.')
      return
    }
    if(!password){
      Alert.alert('Informe sua senha','Digite a senha para entrar.')
      return
    }

    setLoading(true)
    const {data,error}=await supabase.auth.signInWithPassword({email:cleanEmail,password})
    if(error){
      setLoading(false)
      Alert.alert('Não foi possível entrar','Confira seu e-mail e senha. Se acabou de se cadastrar, confirme seu e-mail antes de entrar.')
      return
    }

    if(data.user){
      try{
        await uploadPendingPassengerAvatar(data.user.id,cleanEmail)
      }catch{
        // A foto pendente será tentada novamente no próximo login.
      }
    }

    setLoading(false)
    router.replace('/home')
  }

  return <View style={s.screen}>
    <Text style={s.logo}>CLICK-GO</Text>
    <Text style={s.title}>Entrar</Text>
    <Text style={s.sub}>Acesse sua conta de passageiro com e-mail e senha.</Text>

    <Text style={s.label}>E-mail</Text>
    <TextInput
      style={s.input}
      value={email}
      onChangeText={setEmail}
      placeholder="voce@email.com"
      placeholderTextColor={colors.muted}
      keyboardType="email-address"
      autoCapitalize="none"
      autoCorrect={false}
    />

    <Text style={s.label}>Senha</Text>
    <TextInput
      style={s.input}
      value={password}
      onChangeText={setPassword}
      placeholder="Sua senha"
      placeholderTextColor={colors.muted}
      secureTextEntry
      autoCapitalize="none"
      onSubmitEditing={login}
    />

    <Pressable style={[s.button,loading&&s.disabled]} onPress={login} disabled={loading}>
      <Text style={s.buttonText}>{loading?'Entrando...':'Entrar'}</Text>
    </Pressable>

    <View style={s.accountRow}>
      <Text style={s.accountText}>Ainda não tem uma conta?</Text>
      <Pressable onPress={()=>router.push('/register')} disabled={loading}>
        <Text style={s.accountLink}>Cadastre-se</Text>
      </Pressable>
    </View>

    <Text style={s.note}>O cadastro e o acesso agora usam e-mail e senha, sem depender de SMS.</Text>
  </View>
}

const s=StyleSheet.create({
  screen:{flex:1,backgroundColor:colors.black,padding:24,justifyContent:'center'},
  logo:{color:colors.yellow,fontSize:30,fontWeight:'900',marginBottom:28},
  title:{color:colors.white,fontSize:28,fontWeight:'800'},
  sub:{color:colors.muted,fontSize:15,lineHeight:22,marginTop:8,marginBottom:24},
  label:{color:colors.white,fontWeight:'700',fontSize:14,marginTop:12,marginBottom:7},
  input:{backgroundColor:colors.panel,color:colors.white,borderWidth:1,borderColor:colors.line,borderRadius:14,padding:16,fontSize:16},
  button:{backgroundColor:colors.yellow,padding:16,borderRadius:14,alignItems:'center',marginTop:22},
  disabled:{opacity:0.6},
  buttonText:{color:'#000',fontWeight:'900',fontSize:16},
  accountRow:{flexDirection:'row',justifyContent:'center',alignItems:'center',gap:6,marginTop:24},
  accountText:{color:colors.muted,fontSize:14},
  accountLink:{color:colors.yellow,fontSize:14,fontWeight:'900'},
  note:{color:colors.muted,fontSize:12,textAlign:'center',marginTop:28},
})
