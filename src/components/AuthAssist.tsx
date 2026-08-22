'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const button:React.CSSProperties={border:'1px solid #3a3a3a',borderRadius:10,padding:'9px 12px',fontWeight:800,cursor:'pointer',boxShadow:'0 8px 24px #0008'}

export default function AuthAssist(){
 const pathname=usePathname()
 const[show,setShow]=useState(false),[hasPassword,setHasPassword]=useState(false),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 const canRecover=pathname==='/passageiro'||pathname==='/motorista-app'||pathname==='/franqueado/login'

 useEffect(()=>{
  const sync=()=>{
   let count=0
   document.querySelectorAll<HTMLInputElement>('input').forEach(el=>{
    const hint=`${el.name||''} ${el.placeholder||''} ${el.autocomplete||''}`
    if(el.type==='password'||el.dataset.cgPassword==='1'||/senha|password|current-password|new-password/i.test(hint)){
     el.dataset.cgPassword='1';count++
     const next=show?'text':'password'
     if(el.type!==next)el.type=next
    }
   })
   setHasPassword(count>0)
  }
  sync()
  const observer=new MutationObserver(sync)
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['type','name','placeholder']})
  return()=>observer.disconnect()
 },[show,pathname])

 function recoveryDestination(){
  if(pathname==='/passageiro')return 'passageiro-web'
  if(pathname==='/motorista-app')return 'motorista-web'
  if(pathname==='/franqueado/login')return 'franqueado'
  return 'login'
 }

 async function recover(){
  const email=Array.from(document.querySelectorAll<HTMLInputElement>('input[type="email"]')).find(el=>el.offsetParent!==null)?.value?.trim()||''
  if(!email){setMsg('Digite primeiro o e-mail da sua conta.');return}
  setBusy(true);setMsg('Enviando recuperação...')
  const redirectTo=`${window.location.origin}/redefinir-senha?destino=${encodeURIComponent(recoveryDestination())}`
  const{error}=await supabase.auth.resetPasswordForEmail(email,{redirectTo})
  setBusy(false)
  setMsg(error?error.message:'E-mail de recuperação CLICK-GO enviado. Depois de criar a nova senha, você voltará ao acesso correto.')
 }

 if(!hasPassword)return null
 return <div style={{position:'fixed',right:16,bottom:16,zIndex:5000,display:'grid',gap:7,maxWidth:330}}>
  {msg&&<div style={{background:'#111',color:'#ffe66b',border:'1px solid #665600',borderRadius:10,padding:'9px 11px',fontSize:12}}>{msg}</div>}
  <button type="button" onClick={()=>setShow(v=>!v)} style={{...button,background:'#222',color:'#fff'}}>{show?'🙈 Ocultar senha':'👁 Ver senha'}</button>
  {canRecover&&<button type="button" disabled={busy} onClick={recover} style={{...button,background:'#ffd400',color:'#000'}}>{busy?'Enviando...':'Esqueci minha senha?'}</button>}
 </div>
}
