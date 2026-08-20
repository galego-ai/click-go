'use client'
import { useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function LoginForm(){
 const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [msg,setMsg]=useState('')
 async function login(e:React.FormEvent){e.preventDefault();setMsg('Entrando...');const {data,error}=await supabase.auth.signInWithPassword({email,password});if(error){setMsg(error.message);return}const role=data.user.app_metadata?.role;if(role!=='super_admin'){await supabase.auth.signOut();setMsg('Este acesso não é de Super Admin.');return}window.location.href='/dashboard'}
 return <div className="card" style={{maxWidth:460,margin:'10vh auto'}}><div className="eyebrow">CLICK-GO</div><h1 className="title">Super Admin</h1><p className="subtitle">Entre com a conta administrativa da matriz.</p><form onSubmit={login} className="module-list" style={{marginTop:22}}><div className="field"><label>E-mail</label><input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></div><div className="field"><label>Senha</label><input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required/></div><button className="button" type="submit">Entrar</button>{msg&&<p className="empty">{msg}</p>}</form></div>
}
