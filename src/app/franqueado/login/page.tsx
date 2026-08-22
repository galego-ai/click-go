'use client'

import Link from 'next/link'
import { FormEvent, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function FranchiseLoginPage(){
 const[email,setEmail]=useState('')
 const[password,setPassword]=useState('')
 const[showPassword,setShowPassword]=useState(false)
 const[msg,setMsg]=useState('')
 const[busy,setBusy]=useState(false)

 async function login(e:FormEvent){
  e.preventDefault();setBusy(true);setMsg('Entrando...')
  const {data,error}=await supabase.auth.signInWithPassword({email,password})
  if(error){setMsg(error.message);setBusy(false);return}
  let role=data.user.app_metadata?.role as string|undefined
  if(!role){const{data:p}=await supabase.from('profiles').select('role').eq('id',data.user.id).maybeSingle();role=p?.role}
  if(role!=='franchise_admin'){
   await supabase.auth.signOut()
   setMsg(role==='super_admin'?'Esta conta é da matriz. Entre pelo acesso Super Admin.':'Esta conta não é de administrador de franquia.')
   setBusy(false);return
  }
  window.location.href='/franqueado'
 }

 async function recover(){
  if(!email.trim()){setMsg('Digite primeiro o e-mail da sua conta.');return}
  setBusy(true);setMsg('Enviando recuperação...')
  const redirectTo=`${window.location.origin}/redefinir-senha?destino=franqueado`
  const{error}=await supabase.auth.resetPasswordForEmail(email.trim(),{redirectTo})
  setBusy(false)
  setMsg(error?error.message:'Link de recuperação CLICK-GO enviado. Depois de criar a nova senha, você voltará ao login do Franqueado.')
 }

 const eye:React.CSSProperties={width:46,border:'1px solid #333',borderRadius:10,background:'#181818',color:'#fff',cursor:'pointer',fontSize:17}
 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}>
  <div className="eyebrow">CLICK-GO</div>
  <h1 className="title">Painel do Franqueado</h1>
  <p className="subtitle">Entre com a conta vinculada à sua franquia.</p>
  <form onSubmit={login} className="module-list" style={{marginTop:22}}>
   <div className="field"><label>E-mail</label><input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></div>
   <div className="field"><label>Senha</label><div style={{display:'flex',gap:8}}><input className="input" style={{flex:1}} type={showPassword?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} required/><button type="button" aria-label={showPassword?'Ocultar senha':'Mostrar senha'} onClick={()=>setShowPassword(v=>!v)} style={eye}>{showPassword?'🙈':'👁'}</button></div></div>
   <button className="button" type="submit" disabled={busy}>{busy?'Entrando...':'Entrar'}</button>
   <button className="button secondary" type="button" disabled={busy} onClick={recover}>Esqueci minha senha?</button>
   {msg&&<p className="empty">{msg}</p>}
  </form>
  <p className="empty" style={{marginTop:18}}>Acesso da matriz? <Link href="/login" style={{color:'#ffd400'}}>Entrar como Super Admin</Link></p>
 </div>
}
