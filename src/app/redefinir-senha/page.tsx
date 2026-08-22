'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { supabase } from '@/lib/supabase'

type Destination={label:string;href:string;fallback?:string}

const destinations:Record<string,Destination>={
 'super-admin':{label:'Super Admin',href:'/login'},
 'franqueado':{label:'Painel do Franqueado',href:'/franqueado/login'},
 'passageiro-web':{label:'Passageiro',href:'/passageiro'},
 'motorista-web':{label:'Motorista',href:'/motorista-app'},
 'passageiro-app':{label:'App Passageiro',href:'clickgopassageiro://login',fallback:'/passageiro'},
 'motorista-app':{label:'App Motorista',href:'clickgomotorista://login',fallback:'/motorista-app'},
 login:{label:'CLICK-GO',href:'/login'},
}

export default function ResetPasswordPage(){
 const[password,setPassword]=useState('')
 const[confirm,setConfirm]=useState('')
 const[showPassword,setShowPassword]=useState(false)
 const[msg,setMsg]=useState('Validando seu link de recuperação...')
 const[ready,setReady]=useState(false)
 const[busy,setBusy]=useState(false)
 const[done,setDone]=useState(false)
 const[destinationKey,setDestinationKey]=useState('login')
 const destination=useMemo(()=>destinations[destinationKey]||destinations.login,[destinationKey])

 useEffect(()=>{
  const key=new URLSearchParams(window.location.search).get('destino')||'login'
  setDestinationKey(destinations[key]?key:'login')
  let alive=true
  supabase.auth.getSession().then(({data})=>{if(!alive)return;if(data.session){setReady(true);setMsg('Digite e confirme sua nova senha.')}else setMsg('Abra esta página pelo link enviado ao seu e-mail.')})
  const{data:listener}=supabase.auth.onAuthStateChange((event,session)=>{if(!alive)return;if(event==='PASSWORD_RECOVERY'||session){setReady(true);setMsg('Digite e confirme sua nova senha.')}})
  return()=>{alive=false;listener.subscription.unsubscribe()}
 },[])

 function goBack(){
  if(destination.href.startsWith('clickgo')){
   window.location.href=destination.href
   if(destination.fallback)setTimeout(()=>{window.location.href=destination.fallback!},1400)
   return
  }
  window.location.href=destination.href
 }

 async function submit(e:FormEvent){
  e.preventDefault()
  if(password.length<6){setMsg('A senha deve ter pelo menos 6 caracteres.');return}
  if(password!==confirm){setMsg('As duas senhas precisam ser iguais.');return}
  setBusy(true)
  const{error}=await supabase.auth.updateUser({password})
  setBusy(false)
  if(error){setMsg(error.message);return}
  await supabase.auth.signOut()
  setDone(true)
  setReady(false)
  setMsg(`Senha alterada com sucesso. Retornando para ${destination.label}...`)
  setTimeout(goBack,1100)
 }

 const eyeStyle:React.CSSProperties={width:46,border:'1px solid #333',borderRadius:10,background:'#181818',color:'#fff',cursor:'pointer',fontSize:17}
 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}>
  <div className="eyebrow">CLICK-GO</div>
  <h1 className="title">Criar nova senha</h1>
  <p className="subtitle">Depois de salvar, você volta para o acesso que solicitou a recuperação.</p>
  {!done&&<form onSubmit={submit} className="module-list" style={{marginTop:22}}>
   <div className="field"><label>Nova senha</label><div style={{display:'flex',gap:8}}><input className="input" style={{flex:1}} type={showPassword?'text':'password'} minLength={6} value={password} onChange={e=>setPassword(e.target.value)} required disabled={!ready||busy}/><button type="button" aria-label={showPassword?'Ocultar senha':'Mostrar senha'} onClick={()=>setShowPassword(v=>!v)} style={eyeStyle}>{showPassword?'🙈':'👁'}</button></div></div>
   <div className="field"><label>Confirmar nova senha</label><input className="input" type={showPassword?'text':'password'} minLength={6} value={confirm} onChange={e=>setConfirm(e.target.value)} required disabled={!ready||busy}/></div>
   <button className="button" type="submit" disabled={!ready||busy}>{busy?'Salvando...':'Salvar nova senha'}</button>
  </form>}
  {msg&&<p className="empty" style={{marginTop:16}}>{msg}</p>}
  {done&&<button className="button" type="button" onClick={goBack} style={{marginTop:14}}>Voltar para {destination.label}</button>}
 </div>
}
