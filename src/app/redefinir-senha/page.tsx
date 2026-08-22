'use client'

import { FormEvent, useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function ResetPasswordPage(){
 const[password,setPassword]=useState('')
 const[confirm,setConfirm]=useState('')
 const[msg,setMsg]=useState('Verificando link de recuperação...')
 const[ready,setReady]=useState(false)
 const[busy,setBusy]=useState(false)

 useEffect(()=>{
  let alive=true
  supabase.auth.getSession().then(({data})=>{if(!alive)return;if(data.session){setReady(true);setMsg('Digite sua nova senha.')}else setMsg('Abra esta página pelo link recebido no e-mail de recuperação.')})
  const{data:listener}=supabase.auth.onAuthStateChange((event,session)=>{if(!alive)return;if(event==='PASSWORD_RECOVERY'||session){setReady(true);setMsg('Digite sua nova senha.')}})
  return()=>{alive=false;listener.subscription.unsubscribe()}
 },[])

 async function submit(e:FormEvent){e.preventDefault();if(password.length<6){setMsg('A senha deve ter pelo menos 6 caracteres.');return}if(password!==confirm){setMsg('As duas senhas precisam ser iguais.');return}setBusy(true);const{error}=await supabase.auth.updateUser({password});setBusy(false);if(error){setMsg(error.message);return}setMsg('Senha alterada com sucesso. Você já pode entrar no Super Admin.');setTimeout(()=>{window.location.href='/login'},1200)}

 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}><div className="eyebrow">CLICK-GO</div><h1 className="title">Redefinir senha</h1><p className="subtitle">Crie uma nova senha para sua conta.</p><form onSubmit={submit} className="module-list" style={{marginTop:22}}><div className="field"><label>Nova senha</label><input className="input" type="password" minLength={6} value={password} onChange={e=>setPassword(e.target.value)} required disabled={!ready||busy}/></div><div className="field"><label>Confirmar nova senha</label><input className="input" type="password" minLength={6} value={confirm} onChange={e=>setConfirm(e.target.value)} required disabled={!ready||busy}/></div><button className="button" type="submit" disabled={!ready||busy}>{busy?'Salvando...':'Salvar nova senha'}</button>{msg&&<p className="empty">{msg}</p>}</form></div>
}
