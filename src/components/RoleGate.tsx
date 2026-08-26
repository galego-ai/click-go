'use client'

import {useEffect,useState} from 'react'
import {useRouter,usePathname} from 'next/navigation'
import {supabase} from '@/lib/supabase'

type Role='super_admin'|'franchise_admin'|'operator'

export default function RoleGate({role,loginPath,children}:{role:Role|Role[];loginPath:string;children:React.ReactNode}){
 const router=useRouter();const pathname=usePathname();const[ready,setReady]=useState(false)
 useEffect(()=>{let alive=true;async function verify(){
  const{data:{user}}=await supabase.auth.getUser();if(!alive)return;if(!user){router.replace(loginPath);return}
  const{data:profile,error:profileError}=await supabase.from('profiles').select('role,franchise_id,active').eq('id',user.id).maybeSingle();if(!alive)return
  if(profileError||!profile){await supabase.auth.signOut();router.replace(loginPath);return}
  const metadataRole=user.app_metadata?.role as string|undefined
  if(metadataRole&&profile.role&&metadataRole!==profile.role){await supabase.auth.signOut();router.replace(loginPath);return}
  const currentRole=(metadataRole||profile.role) as string|undefined
  const allowed=Array.isArray(role)?role:[role];if(!currentRole||!allowed.includes(currentRole as Role)){router.replace(loginPath);return}
  if(profile.active===false){await supabase.auth.signOut();router.replace(loginPath);return}
  if(currentRole==='franchise_admin'&&!profile.franchise_id){await supabase.auth.signOut();router.replace(loginPath);return}
  if(currentRole==='operator'){
   const{data:staff}=await supabase.from('franchise_staff_permissions').select('active').eq('profile_id',user.id).maybeSingle();if(!staff?.active){await supabase.auth.signOut();router.replace(loginPath);return}
  }
  if((currentRole==='franchise_admin'||currentRole==='operator')&&user.app_metadata?.must_change_password===true&&pathname!=='/franqueado/trocar-senha-temporaria'){router.replace('/franqueado/trocar-senha-temporaria');return}
  setReady(true)
 }verify();return()=>{alive=false}},[role,loginPath,router,pathname])
 if(!ready)return <div className="card" style={{maxWidth:520,margin:'12vh auto',textAlign:'center'}}><div className="eyebrow">CLICK-GO Gestão</div><h2>Verificando acesso...</h2><p className="subtitle">Validando perfil, empresa e permissões.</p></div>
 return <>{children}</>
}
