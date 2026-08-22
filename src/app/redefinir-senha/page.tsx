'use client'

import { FormEvent, useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function ResetPasswordPage(){
 const[password,setPassword]=useState('')
 const[confirm,setConfirm]=useState('')
 const[showPassword,setShowPassword]=useState(false)
 const[msg,setMsg]=useState('Validando seu link de recuperação...')
 const[ready,setReady]=useState(false)
 const[busy,setBusy]=useState(false)
 const[done,setDone]=useState(false)

 useEffect(()=>{
  let alive=true
  supabase.auth.getSession().then(({data})=>{if(!alive)return;if(data.session){setReady(true);setMsg('Digite e confirme sua nova senha.')}else setMsg('Abra esta página pelo link enviado ao seu e-mail.')})
  const{data:listener}=supabase.auth.onAuthStateChange((event,session)=>{if(!alive)return;if(event==='PASSWORD_RECOVERY'||session){setReady(true);setMsg('Digite e confirme sua nova senha.')}})
  return()=>{alive=false;listener.subscription.unsubscribe()}
 },[])

 async function submit(e:FormEvent){
  e.preventDefault()
  if(password.length<6){setMsg('A senha deve ter pelo menos 6 caracteres.');return}
  if(password!==confirm){setMsg('As duas senhas precisam ser iguais.');return}
  setBusy(true)
  const{error}=await supabase.auth.updateUser({password})
  setBusy(false)
  if(error){setMsg(error.message);return}
  setDone(true)
  setReady(false)
  setMsg('Senha alterada com sucesso. Volte ao aplicativo ou painel CLICK-GO e entre com a nova senha.')
 }

 const eyeStyle:React.CSSProperties={width:46,border:'1px solid #333',borderRadius:10,background:'#181818',color:'#fff',cursor:'pointer',fontSize:17}
 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}>
  <div className="eyebrow">CLICK-GO</div>
  <h1 className="title">Criar nova senha</h1>
  <p className="subtitle">Este passo só aparece depois que você abre o link enviado ao seu e-mail.</p>
  {!done&&<form onSubmit={submit} className="module-list" style={{marginTop:22}}>
   <div className="field"><label>Nova senha</label><div style={{display:'flex',gap:8}}><input className="input" style={{flex:1}} type={showPassword?'text':'password'} minLength={6} value={password} onChange={e=>setPassword(e.target.value)} required disabled={!ready||busy}/><button type="button" aria-label={showPassword?'Ocultar senha':'Mostrar senha'} onClick={()=>setShowPassword(v=>!v)} style={eyeStyle}>{showPassword?'🙈':'👁'}</button></div></div>
   <div className="field"><label>Confirmar nova senha</label><input className="input" type={showPassword?'text':'password'} minLength={6} value={confirm} onChange={e=>setConfirm(e.target.value)} required disabled={!ready||busy}/></div>
   <button className="button" type="submit" disabled={!ready||busy}>{busy?'Salvando...':'Salvar nova senha'}</button>
  </form>}
  {msg&&<p className="empty" style={{marginTop:16}}>{msg}</p>}
 </div>
}
