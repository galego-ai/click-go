'use client'

import { useEffect, useState } from 'react'
import { useRouter,usePathname } from 'next/navigation'
import { supabase } from '@/lib/supabase'

type Role = 'super_admin' | 'franchise_admin'

export default function RoleGate({ role, loginPath, children }: { role: Role; loginPath: string; children: React.ReactNode }) {
  const router = useRouter();const pathname=usePathname();const [ready,setReady]=useState(false)
  useEffect(()=>{let alive=true;async function verify(){const{data:{user}}=await supabase.auth.getUser();if(!alive)return;if(!user){router.replace(loginPath);return}let currentRole=user.app_metadata?.role as string|undefined;if(!currentRole){const{data:profile}=await supabase.from('profiles').select('role').eq('id',user.id).maybeSingle();currentRole=profile?.role}if(currentRole!==role){router.replace(loginPath);return}if(role==='franchise_admin'&&user.app_metadata?.must_change_password===true&&pathname!=='/franqueado/trocar-senha-temporaria'){router.replace('/franqueado/trocar-senha-temporaria');return}setReady(true)}verify();return()=>{alive=false}},[role,loginPath,router,pathname])
  if(!ready)return <div className="card" style={{maxWidth:520,margin:'12vh auto',textAlign:'center'}}><div className="eyebrow">CLICK-GO</div><h2>Verificando acesso...</h2><p className="subtitle">Aguarde a validação segura da sua sessão.</p></div>
  return <>{children}</>
}
