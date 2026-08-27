'use client'

import {useEffect,useState} from 'react'
import {supabase} from '@/lib/supabase'
import PassengerPaymentMethods from '@/components/PassengerPaymentMethods'

type Method={id:string;method_type:string;provider:string|null;brand:string|null;last4:string|null;is_default:boolean;active:boolean}
const btn:React.CSSProperties={position:'fixed',right:18,bottom:18,zIndex:9000,background:'#ffd400',color:'#000',border:0,borderRadius:999,padding:'13px 17px',fontWeight:900,boxShadow:'0 8px 30px #0005',cursor:'pointer'}

export default function PassengerPaymentsLauncher(){
 const[passengerId,setPassengerId]=useState<string|null>(null),[methods,setMethods]=useState<Method[]>([]),[open,setOpen]=useState(false),[loading,setLoading]=useState(false)
 useEffect(()=>{void load();const{data}=supabase.auth.onAuthStateChange(()=>void load());return()=>data.subscription.unsubscribe()},[])
 async function load(){
  const{data:{user}}=await supabase.auth.getUser();if(!user){setPassengerId(null);setMethods([]);return}
  const{data:p}=await supabase.from('profiles').select('role').eq('id',user.id).maybeSingle();if(p?.role!=='passenger'){setPassengerId(null);return}
  setPassengerId(user.id);const{data:m}=await supabase.from('passenger_payment_methods').select('id,method_type,provider,brand,last4,is_default,active').eq('passenger_id',user.id).eq('active',true).order('created_at',{ascending:false});setMethods((m||[]) as Method[])
 }
 async function changed(){setLoading(true);await load();setLoading(false);window.setTimeout(()=>window.location.reload(),900)}
 if(!passengerId)return null
 return <>
  <button style={btn} onClick={()=>setOpen(true)}>💳 Pagamentos Efí</button>
  {open&&<div style={{position:'fixed',inset:0,zIndex:9500,background:'rgba(0,0,0,.72)',display:'grid',placeItems:'center',padding:14}} onMouseDown={e=>{if(e.currentTarget===e.target)setOpen(false)}}><div style={{width:'min(860px,100%)',maxHeight:'92vh',overflow:'auto',background:'#080808',color:'#fff',border:'1px solid #333',borderRadius:22,padding:20,boxShadow:'0 30px 80px #000'}}><div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,marginBottom:12}}><div><div style={{fontSize:12,fontWeight:900,color:'#ffd400'}}>EFÍ BANK</div><h2 style={{margin:'4px 0'}}>Pagamentos do Passageiro</h2></div><button onClick={()=>setOpen(false)} style={{border:0,borderRadius:12,padding:'9px 12px',background:'#222',color:'#fff',fontWeight:800}}>Fechar</button></div>{loading&&<div style={{color:'#ffd400',marginBottom:10}}>Atualizando...</div>}<PassengerPaymentMethods passengerId={passengerId} methods={methods} onChanged={changed}/></div></div>}
 </>
}
