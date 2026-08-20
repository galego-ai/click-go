'use client'
import { useEffect,useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function FranchiseGuard({children}:{children:React.ReactNode}){
 const router=useRouter(); const [state,setState]=useState<'loading'|'ok'|'denied'>('loading')
 useEffect(()=>{(async()=>{const {data:{user}}=await supabase.auth.getUser();if(!user){router.replace('/login');return}const {data}=await supabase.from('profiles').select('role,franchise_id,active').eq('id',user.id).single();if(data?.active&&data.role==='franchise_admin'&&data.franchise_id)setState('ok');else setState('denied')})()},[router])
 if(state==='loading')return <div className="card">Carregando operação...</div>
 if(state==='denied')return <div className="card"><h2>Acesso restrito</h2><p className="empty">Este endereço é exclusivo para administradores de franquia.</p></div>
 return <>{children}</>
}
