'use client'

import { FormEvent,useEffect,useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Category={
 id:string;name:string;city_id:string;base_fare:number|string;price_per_km:number|string;price_per_minute:number|string;
 minimum_fare:number|string;cancellation_fee:number|string;dynamic_multiplier:number|string;active:boolean;locked_by_matrix:boolean;
 required_vehicle_type:string|null;icon_url:string|null;map_marker_url:string|null;wait_tolerance_minutes:number|string;waiting_fee_per_minute:number|string
}
type WaitDraft={tolerance:string;fee:string}
const input:React.CSSProperties={width:'100%',background:'#0b0b0b',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const emptyForm={name:'',city_id:'',base_fare:'',price_per_km:'',price_per_minute:'',minimum_fare:'',cancellation_fee:'',dynamic_multiplier:'1',required_vehicle_type:'car',wait_tolerance_minutes:'5',waiting_fee_per_minute:'0.50'}

export default function CategoriasPage(){
 const[fid,setFid]=useState(''),[cities,setCities]=useState<City[]>([]),[items,setItems]=useState<Category[]>([]),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false),[marker,setMarker]=useState<File|null>(null)
 const[f,setF]=useState(emptyForm)
 const[waitDraft,setWaitDraft]=useState<Record<string,WaitDraft>>({})
 useEffect(()=>{load()},[])
 async function load(){
  setBusy(true)
  try{
   const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login.')
   const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
   if(!p||p.role!=='franchise_admin'||!p.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
   setFid(p.franchise_id)
   const[fc,c]=await Promise.all([
    supabase.from('franchise_cities').select('city_id,cities(id,name,state)').eq('franchise_id',p.franchise_id),
    supabase.from('ride_categories').select('*').eq('franchise_id',p.franchise_id).order('name')
   ])
   const cr=(fc.data||[]).map((x:any)=>x.cities).filter(Boolean);setCities(cr)
   const categories=(c.data||[]) as Category[];setItems(categories)
   const drafts:Record<string,WaitDraft>={};for(const x of categories)drafts[x.id]={tolerance:String(x.wait_tolerance_minutes??5),fee:String(x.waiting_fee_per_minute??0.5)};setWaitDraft(drafts)
   if(cr[0])setF(v=>({...v,city_id:v.city_id||cr[0].id}))
  }catch(e:any){setMsg(e.message)}finally{setBusy(false)}
 }
 function validMoney(v:string){return v.trim()!==''&&Number.isFinite(Number(v))&&Number(v)>=0}
 async function upload(file:File,categoryId?:string){
  if(!fid)return null
  if(file.size>2*1024*1024)throw new Error('A imagem do marcador deve ter no máximo 2 MB.')
  if(!['image/jpeg','image/png','image/webp','image/svg+xml'].includes(file.type))throw new Error('Use JPG, PNG, WEBP ou SVG.')
  const ext=(file.name.split('.').pop()||'png').replace(/[^a-z0-9]/gi,'').toLowerCase();const path=`${fid}/${categoryId||'new'}-${Date.now()}.${ext}`
  const{error}=await supabase.storage.from('category-markers').upload(path,file,{upsert:false,contentType:file.type});if(error)throw error
  return supabase.storage.from('category-markers').getPublicUrl(path).data.publicUrl
 }
 async function create(e:FormEvent){
  e.preventDefault();if(!fid)return
  if(!validMoney(f.base_fare)||!validMoney(f.price_per_km)||!validMoney(f.price_per_minute)||!validMoney(f.minimum_fare)||!validMoney(f.cancellation_fee)||!validMoney(f.dynamic_multiplier)||Number(f.dynamic_multiplier)<1||!validMoney(f.waiting_fee_per_minute)||!Number.isInteger(Number(f.wait_tolerance_minutes))||Number(f.wait_tolerance_minutes)<0){setMsg('Preencha todas as tarifas e a regra de espera com valores válidos.');return}
  setBusy(true)
  try{
   let markerUrl:string|null=null;if(marker)markerUrl=await upload(marker)
   const{error}=await supabase.from('ride_categories').insert({franchise_id:fid,city_id:f.city_id,name:f.name.trim(),base_fare:Number(f.base_fare),price_per_km:Number(f.price_per_km),price_per_minute:Number(f.price_per_minute),minimum_fare:Number(f.minimum_fare),cancellation_fee:Number(f.cancellation_fee),dynamic_multiplier:Number(f.dynamic_multiplier),wait_tolerance_minutes:Number(f.wait_tolerance_minutes),waiting_fee_per_minute:Number(f.waiting_fee_per_minute),active:true,source:'franchise',locked_by_matrix:false,required_vehicle_type:f.required_vehicle_type||null,icon_url:markerUrl,map_marker_url:markerUrl})
   if(error)throw error
   setF(v=>({...emptyForm,city_id:v.city_id}));setMarker(null);setMsg('Categoria criada com regra de espera configurada.');await load()
  }catch(e:any){setMsg(e.message||'Erro ao criar categoria.')}finally{setBusy(false)}
 }
 async function toggle(c:Category){if(c.locked_by_matrix)return setMsg('Categoria bloqueada pela matriz.');const{error}=await supabase.from('ride_categories').update({active:!c.active}).eq('id',c.id);setMsg(error?error.message:'Categoria atualizada.');if(!error)await load()}
 async function replaceMarker(c:Category,file:File|null){if(!file)return;setBusy(true);try{const url=await upload(file,c.id);const{error}=await supabase.from('ride_categories').update({icon_url:url,map_marker_url:url}).eq('id',c.id);if(error)throw error;setMsg('Ícone do mapa atualizado.');await load()}catch(e:any){setMsg(e.message||'Erro ao atualizar ícone.')}finally{setBusy(false)}}
 async function saveWait(c:Category){
  if(c.locked_by_matrix)return setMsg('Categoria bloqueada pela matriz.')
  const d=waitDraft[c.id];if(!d||!Number.isInteger(Number(d.tolerance))||Number(d.tolerance)<0||Number(d.tolerance)>120||!validMoney(d.fee)){setMsg('Tolerância deve ser de 0 a 120 minutos e a taxa deve ser um valor válido.');return}
  setBusy(true)
  const{error}=await supabase.from('ride_categories').update({wait_tolerance_minutes:Number(d.tolerance),waiting_fee_per_minute:Number(d.fee)}).eq('id',c.id)
  setBusy(false);setMsg(error?error.message:'Regra de espera atualizada.');if(!error)await load()
 }
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1200,margin:'0 auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO</div><h1>Categorias de corrida</h1><p style={{color:'#9ca3af'}}>Defina preços, tipo do veículo, tolerância de espera no embarque e a cobrança por minuto após a tolerância.</p></div><Link href="/franqueado" style={{...btn,textDecoration:'none'}}>Painel do franqueado</Link></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:16}}>{msg}</div>}
  <div style={{display:'grid',gridTemplateColumns:'380px 1fr',gap:16}}>
   <form onSubmit={create} style={box}><h2>Nova categoria</h2><div style={{display:'grid',gap:9}}>
    <input required placeholder="Nome: Econômico, Moto, Premium..." style={input} value={f.name} onChange={e=>setF({...f,name:e.target.value})}/>
    <select required style={input} value={f.city_id} onChange={e=>setF({...f,city_id:e.target.value})}>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select>
    <select style={input} value={f.required_vehicle_type} onChange={e=>setF({...f,required_vehicle_type:e.target.value})}><option value="car">Carro</option><option value="motorcycle">Moto</option><option value="">Qualquer veículo</option></select>
    <label style={{display:'grid',gap:5,fontSize:12,color:'#9ca3af'}}>Ícone/foto do veículo no mapa<input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" style={input} onChange={e=>setMarker(e.target.files?.[0]||null)}/></label>
    <input required type="number" min="0" step="0.01" placeholder="Preço base (R$)" style={input} value={f.base_fare} onChange={e=>setF({...f,base_fare:e.target.value})}/>
    <input required type="number" min="0" step="0.01" placeholder="Preço por km (R$)" style={input} value={f.price_per_km} onChange={e=>setF({...f,price_per_km:e.target.value})}/>
    <input required type="number" min="0" step="0.01" placeholder="Preço por minuto (R$)" style={input} value={f.price_per_minute} onChange={e=>setF({...f,price_per_minute:e.target.value})}/>
    <input required type="number" min="0" step="0.01" placeholder="Tarifa mínima (R$)" style={input} value={f.minimum_fare} onChange={e=>setF({...f,minimum_fare:e.target.value})}/>
    <input required type="number" min="0" step="0.01" placeholder="Taxa de cancelamento (R$)" style={input} value={f.cancellation_fee} onChange={e=>setF({...f,cancellation_fee:e.target.value})}/>
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:9}}><label style={{fontSize:12,color:'#9ca3af'}}>Tolerância de espera (min)<input required type="number" min="0" max="120" step="1" style={{...input,marginTop:5}} value={f.wait_tolerance_minutes} onChange={e=>setF({...f,wait_tolerance_minutes:e.target.value})}/></label><label style={{fontSize:12,color:'#9ca3af'}}>Taxa após tolerância (R$/min)<input required type="number" min="0" step="0.01" style={{...input,marginTop:5}} value={f.waiting_fee_per_minute} onChange={e=>setF({...f,waiting_fee_per_minute:e.target.value})}/></label></div>
    <label style={{fontSize:12,color:'#9ca3af'}}>Multiplicador dinâmico<input required type="number" min="1" step="0.01" style={{...input,marginTop:5}} value={f.dynamic_multiplier} onChange={e=>setF({...f,dynamic_multiplier:e.target.value})}/></label>
    <button disabled={busy} style={btn}>{busy?'Salvando...':'Criar categoria'}</button>
   </div></form>
   <section style={box}><h2>Categorias cadastradas</h2><div style={{display:'grid',gap:10}}>{items.map(c=>{
    const d=waitDraft[c.id]||{tolerance:String(c.wait_tolerance_minutes??5),fee:String(c.waiting_fee_per_minute??0.5)}
    return <div key={c.id} style={{...box,padding:13}}><div style={{display:'grid',gridTemplateColumns:'58px 1fr auto',gap:12,alignItems:'center'}}>
     <div>{c.map_marker_url||c.icon_url?<img src={c.map_marker_url||c.icon_url||''} alt="Marcador" style={{width:52,height:52,borderRadius:'50%',objectFit:'cover',border:'2px solid #ffd400'}}/>:<div style={{width:52,height:52,borderRadius:'50%',background:'#222',display:'grid',placeItems:'center',fontSize:26}}>🚗</div>}</div>
     <div><b>{c.name}</b><div style={{color:'#9ca3af',fontSize:13}}>Base R$ {Number(c.base_fare).toFixed(2)} · km R$ {Number(c.price_per_km).toFixed(2)} · min R$ {Number(c.price_per_minute).toFixed(2)} · mínima R$ {Number(c.minimum_fare).toFixed(2)}</div><label style={{display:'inline-block',marginTop:8,fontSize:12,color:'#ffd400',cursor:'pointer'}}>Trocar ícone do mapa <input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" hidden onChange={e=>replaceMarker(c,e.target.files?.[0]||null)}/></label></div>
     <button disabled={c.locked_by_matrix} style={{...btn,background:c.active?'#333':'#ffd400',color:c.active?'#fff':'#000'}} onClick={()=>toggle(c)}>{c.locked_by_matrix?'Bloqueada pela matriz':c.active?'Desativar':'Ativar'}</button>
    </div><div style={{marginTop:12,paddingTop:12,borderTop:'1px solid #292929',display:'grid',gridTemplateColumns:'1fr 1fr auto',gap:9,alignItems:'end'}}><label style={{fontSize:12,color:'#9ca3af'}}>Tolerância no embarque (min)<input type="number" min="0" max="120" step="1" style={{...input,marginTop:5}} value={d.tolerance} onChange={e=>setWaitDraft(v=>({...v,[c.id]:{...d,tolerance:e.target.value}}))}/></label><label style={{fontSize:12,color:'#9ca3af'}}>Cobrança após tolerância (R$/min)<input type="number" min="0" step="0.01" style={{...input,marginTop:5}} value={d.fee} onChange={e=>setWaitDraft(v=>({...v,[c.id]:{...d,fee:e.target.value}}))}/></label><button disabled={busy||c.locked_by_matrix} style={btn} onClick={()=>saveWait(c)}>Salvar espera</button></div></div>
   })}{!items.length&&<div>Nenhuma categoria cadastrada.</div>}</div></section>
  </div>
 </div></main>
}
