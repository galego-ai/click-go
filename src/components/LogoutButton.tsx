'use client'

import {useState} from 'react'
import {supabase} from '@/lib/supabase'

type Props={loginPath:string;className?:string;compact?:boolean}

export default function LogoutButton({loginPath,className='',compact=false}:Props){
 const [busy,setBusy]=useState(false)
 const logout=async()=>{
  if(busy)return
  setBusy(true)
  try{await supabase.auth.signOut({scope:'local'})}catch{}
  try{
   for(const storage of [window.localStorage,window.sessionStorage]){
    for(let i=storage.length-1;i>=0;i--){
     const key=storage.key(i)
     if(key&&key.startsWith('sb-')&&key.endsWith('-auth-token'))storage.removeItem(key)
    }
   }
  }catch{}
  window.location.replace(loginPath)
 }
 return <button type="button" className={className} onClick={logout} disabled={busy} aria-label="Sair do painel">{busy?'Saindo...':compact?'🚪 Sair':'🚪 Sair do painel'}</button>
}
