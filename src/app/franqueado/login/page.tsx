'use client'

import Link from 'next/link'
import { FormEvent, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function FranchiseLoginPage(){
 const[email,setEmail]=useState('')
 const[password,setPassword]=useState('')
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

 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}>
  <div className="eyebrow">CLICK-GO</div>
  <h1 className="title">Painel do Franqueado</h1>
  <p className="subtitle">Entre com a conta vinculada à sua franquia.</p>
  <form onSubmit={login} className="module-list" style={{marginTop:22}}>
   <div className="field"><label>E-mail</label><input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></div>
   <div className="field"><label>Senha</label><input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required/></div>
   <button className="button" type="submit" disabled={busy}>{busy?'Entrando...':'Entrar'}</button>
   {msg&&<p className="empty">{msg}</p>}
  </form>
  <p className="empty" style={{marginTop:18}}>Acesso da matriz? <Link href="/login" style={{color:'#ffd400'}}>Entrar como Super Admin</Link></p>
 </div>
}
