'use client'

import Link from 'next/link'
import {FormEvent,useEffect,useMemo,useState} from 'react'
import type {CSSProperties} from 'react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Category={
 id:string
 name:string
 city_id:string
 base_fare:number|string
 price_per_km:number|string
 price_per_minute:number|string
 minimum_fare:number|string
 cancellation_fee:number|string
 dynamic_multiplier:number|string
 active:boolean
 locked_by_matrix:boolean
 required_vehicle_type:string|null
 icon_url:string|null
 map_marker_url:string|null
 wait_tolerance_minutes:number|string
 waiting_fee_per_minute:number|string
 route_deviation_threshold_m:number|string
 source:string|null
}
type Draft={
 name:string
 city_id:string
 base_fare:string
 price_per_km:string
 price_per_minute:string
 minimum_fare:string
 cancellation_fee:string
 dynamic_multiplier:string
 required_vehicle_type:string
 wait_tolerance_minutes:string
 waiting_fee_per_minute:string
 route_deviation_threshold_m:string
 active:boolean
}

const input:CSSProperties={width:'100%',background:'#0b0b0b',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px',boxSizing:'border-box'}
const btn:CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const secondary:CSSProperties={...btn,background:'#252525',color:'#fff',border:'1px solid #3a3a3a'}
const box:CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const label:CSSProperties={fontSize:12,color:'#a1a1aa',display:'grid',gap:5}
const emptyDraft=(cityId=''):Draft=>({name:'',city_id:cityId,base_fare:'',price_per_km:'',price_per_minute:'',minimum_fare:'',cancellation_fee:'',dynamic_multiplier:'1',required_vehicle_type:'car',wait_tolerance_minutes:'5',waiting_fee_per_minute:'0.50',route_deviation_threshold_m:'800',active:true})
const asDraft=(c:Category):Draft=>({name:c.name,city_id:c.city_id,base_fare:String(c.base_fare??0),price_per_km:String(c.price_per_km??0),price_per_minute:String(c.price_per_minute??0),minimum_fare:String(c.minimum_fare??0),cancellation_fee:String(c.cancellation_fee??0),dynamic_multiplier:String(c.dynamic_multiplier??1),required_vehicle_type:c.required_vehicle_type||'',wait_tolerance_minutes:String(c.wait_tolerance_minutes??5),waiting_fee_per_minute:String(c.waiting_fee_per_minute??0.5),route_deviation_threshold_m:String(c.route_deviation_threshold_m??800),active:Boolean(c.active)})
const money=(v:number|string)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))

export default function CategoriasPage(){
 const[fid,setFid]=useState('')
 const[cities,setCities]=useState<City[]>([])
 const[items,setItems]=useState<Category[]>([])
 const[msg,setMsg]=useState('')
 const[busy,setBusy]=useState(false)
 const[query,setQuery]=useState('')
 const[createDraft,setCreateDraft]=useState<Draft>(emptyDraft())
 const[createMarker,setCreateMarker]=useState<File|null>(null)
 const[editing,setEditing]=useState<Category|null>(null)
 const[editDraft,setEditDraft]=useState<Draft|null>(null)
 const[editMarker,setEditMarker]=useState<File|null>(null)

 useEffect(()=>{void load()},[])

 const filtered=useMemo(()=>{
  const q=query.trim().toLowerCase()
  if(!q)return items
  return items.filter(c=>`${c.name} ${cityName(c.city_id)} ${c.required_vehicle_type||''}`.toLowerCase().includes(q))
 },[items,query,cities])

 function cityName(id:string){const c=cities.find(x=>x.id===id);return c?`${c.name}/${c.state}`:'Cidade'}

 async function load(){
  setBusy(true);setMsg('')
  try{
   const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login novamente.')
   const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
   if(!p||p.role!=='franchise_admin'||!p.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
   setFid(p.franchise_id)
   const{data:fc,error:fce}=await supabase.from('franchise_cities').select('city_id').eq('franchise_id',p.franchise_id);if(fce)throw fce
   const ids=(fc||[]).map(x=>x.city_id).filter((x):x is string=>Boolean(x))
   let cityRows:City[]=[]
   if(ids.length){const{data:cr,error:ce}=await supabase.from('cities').select('id,name,state').in('id',ids).order('name');if(ce)throw ce;cityRows=(cr||[]) as City[]}
   setCities(cityRows)
   const{data:cats,error:catError}=await supabase.from('ride_categories').select('id,name,city_id,base_fare,price_per_km,price_per_minute,minimum_fare,cancellation_fee,dynamic_multiplier,active,locked_by_matrix,required_vehicle_type,icon_url,map_marker_url,wait_tolerance_minutes,waiting_fee_per_minute,route_deviation_threshold_m,source').eq('franchise_id',p.franchise_id).order('name');if(catError)throw catError
   const categoryRows=(cats||[]) as Category[];setItems(categoryRows)
   setCreateDraft(v=>({...v,city_id:v.city_id||cityRows[0]?.id||''}))
   if(editing){const fresh=categoryRows.find(x=>x.id===editing.id)||null;setEditing(fresh);setEditDraft(fresh?asDraft(fresh):null)}
  }catch(e){setMsg(e instanceof Error?e.message:'Erro ao carregar categorias e tarifas.')}finally{setBusy(false)}
 }

 function valid(d:Draft){
  const values=[d.base_fare,d.price_per_km,d.price_per_minute,d.minimum_fare,d.cancellation_fee,d.waiting_fee_per_minute]
  if(!d.name.trim()||!d.city_id)return 'Informe nome e cidade.'
  if(values.some(v=>v.trim()===''||!Number.isFinite(Number(v))||Number(v)<0))return 'As tarifas devem ter valores válidos e não negativos.'
  if(!Number.isFinite(Number(d.dynamic_multiplier))||Number(d.dynamic_multiplier)<1)return 'O multiplicador dinâmico deve ser 1 ou maior.'
  const wait=Number(d.wait_tolerance_minutes),deviation=Number(d.route_deviation_threshold_m)
  if(!Number.isInteger(wait)||wait<0||wait>120)return 'A tolerância de espera deve ficar entre 0 e 120 minutos.'
  if(!Number.isInteger(deviation)||deviation<100||deviation>5000)return 'O alerta de desvio deve ficar entre 100 e 5.000 metros.'
  return ''
 }

 async function upload(file:File,categoryId='new'){
  if(!fid)throw new Error('Franquia não identificada.')
  if(file.size>2*1024*1024)throw new Error('A imagem deve ter no máximo 2 MB.')
  if(!['image/jpeg','image/png','image/webp','image/svg+xml'].includes(file.type))throw new Error('Use JPG, PNG, WEBP ou SVG.')
  const ext=(file.name.split('.').pop()||'png').replace(/[^a-z0-9]/gi,'').toLowerCase()
  const path=`${fid}/${categoryId}-${Date.now()}.${ext}`
  const{error}=await supabase.storage.from('category-markers').upload(path,file,{upsert:false,contentType:file.type});if(error)throw error
  return supabase.storage.from('category-markers').getPublicUrl(path).data.publicUrl
 }

 function payload(d:Draft,markerUrl?:string|null){
  return {name:d.name.trim(),base_fare:Number(d.base_fare),price_per_km:Number(d.price_per_km),price_per_minute:Number(d.price_per_minute),minimum_fare:Number(d.minimum_fare),cancellation_fee:Number(d.cancellation_fee),dynamic_multiplier:Number(d.dynamic_multiplier),required_vehicle_type:d.required_vehicle_type||null,wait_tolerance_minutes:Number(d.wait_tolerance_minutes),waiting_fee_per_minute:Number(d.waiting_fee_per_minute),route_deviation_threshold_m:Number(d.route_deviation_threshold_m),active:d.active,...(markerUrl?{icon_url:markerUrl,map_marker_url:markerUrl}:{})}
 }

 async function createCategory(e:FormEvent){
  e.preventDefault();const errorText=valid(createDraft);if(errorText){setMsg(errorText);return}
  setBusy(true);setMsg('')
  try{
   const markerUrl=createMarker?await upload(createMarker):null
   const{error}=await supabase.rpc('franchise_upsert_ride_category',{p_category_id:null,p_city_id:createDraft.city_id,p_payload:payload(createDraft,markerUrl)});if(error)throw error
   setCreateDraft(emptyDraft(createDraft.city_id));setCreateMarker(null);setMsg('Categoria criada e tarifas salvas.');await load()
  }catch(e){setMsg(e instanceof Error?e.message:'Erro ao criar categoria.')}finally{setBusy(false)}
 }

 function startEdit(c:Category){
  if(c.locked_by_matrix){setMsg('Esta categoria foi bloqueada pela Matriz e está disponível somente para consulta.');return}
  setEditing(c);setEditDraft(asDraft(c));setEditMarker(null);setMsg('')
  window.scrollTo({top:0,behavior:'smooth'})
 }

 function closeEdit(){setEditing(null);setEditDraft(null);setEditMarker(null)}

 async function saveEdit(e:FormEvent){
  e.preventDefault();if(!editing||!editDraft)return
  if(editing.locked_by_matrix){setMsg('Categoria bloqueada pela Matriz.');return}
  const errorText=valid(editDraft);if(errorText){setMsg(errorText);return}
  setBusy(true);setMsg('')
  try{
   const markerUrl=editMarker?await upload(editMarker,editing.id):null
   const{error}=await supabase.rpc('franchise_upsert_ride_category',{p_category_id:editing.id,p_city_id:editing.city_id,p_payload:payload(editDraft,markerUrl)});if(error)throw error
   setMsg('Categoria e tarifas atualizadas com sucesso.');closeEdit();await load()
  }catch(e){setMsg(e instanceof Error?e.message:'Erro ao atualizar categoria.')}finally{setBusy(false)}
 }

 async function toggle(c:Category){
  if(c.locked_by_matrix){setMsg('Categoria bloqueada pela Matriz.');return}
  setBusy(true)
  const{error}=await supabase.rpc('franchise_upsert_ride_category',{p_category_id:c.id,p_city_id:c.city_id,p_payload:{active:!c.active}})
  setBusy(false);setMsg(error?error.message:c.active?'Categoria desativada.':'Categoria ativada.');if(!error)await load()
 }

 function fareFields(d:Draft,setD:(next:Draft)=>void,disabled=false){
  return <>
   <div style={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:9}}>
    <label style={label}>Preço base (R$)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.base_fare} onChange={e=>setD({...d,base_fare:e.target.value})}/></label>
    <label style={label}>Tarifa mínima (R$)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.minimum_fare} onChange={e=>setD({...d,minimum_fare:e.target.value})}/></label>
    <label style={label}>Preço por km (R$)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.price_per_km} onChange={e=>setD({...d,price_per_km:e.target.value})}/></label>
    <label style={label}>Preço por minuto (R$)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.price_per_minute} onChange={e=>setD({...d,price_per_minute:e.target.value})}/></label>
    <label style={label}>Taxa de cancelamento (R$)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.cancellation_fee} onChange={e=>setD({...d,cancellation_fee:e.target.value})}/></label>
    <label style={label}>Multiplicador dinâmico<input disabled={disabled} type="number" min="1" step="0.01" style={input} value={d.dynamic_multiplier} onChange={e=>setD({...d,dynamic_multiplier:e.target.value})}/></label>
   </div>
   <div style={{display:'grid',gridTemplateColumns:'repeat(3,minmax(0,1fr))',gap:9}}>
    <label style={label}>Tolerância de espera (min)<input disabled={disabled} type="number" min="0" max="120" step="1" style={input} value={d.wait_tolerance_minutes} onChange={e=>setD({...d,wait_tolerance_minutes:e.target.value})}/></label>
    <label style={label}>Espera após tolerância (R$/min)<input disabled={disabled} type="number" min="0" step="0.01" style={input} value={d.waiting_fee_per_minute} onChange={e=>setD({...d,waiting_fee_per_minute:e.target.value})}/></label>
    <label style={label}>Alerta de desvio (m)<input disabled={disabled} type="number" min="100" max="5000" step="50" style={input} value={d.route_deviation_threshold_m} onChange={e=>setD({...d,route_deviation_threshold_m:e.target.value})}/></label>
   </div>
  </>
 }

 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1250,margin:'0 auto'}}>
  <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap',marginBottom:18}}><div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO · FRANQUEADO</div><h1 style={{margin:'6px 0'}}>Categorias e tarifas</h1><p style={{color:'#a1a1aa',margin:0}}>Crie categorias e edite os preços usados nas corridas da sua operação.</p></div><Link href="/franqueado" style={{...secondary,textDecoration:'none'}}>← Dashboard</Link></header>

  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:16}}>{msg}</div>}

  {editing&&editDraft&&<form onSubmit={saveEdit} style={{...box,borderColor:'#665600',marginBottom:18}}>
   <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}><div><div style={{color:'#ffd400',fontWeight:900}}>EDITANDO</div><h2 style={{margin:'4px 0'}}>{editing.name}</h2><span style={{color:'#a1a1aa',fontSize:13}}>{cityName(editing.city_id)}</span></div><button type="button" style={secondary} onClick={closeEdit}>Fechar edição</button></div>
   <div style={{display:'grid',gap:12,marginTop:16}}>
    <div style={{display:'grid',gridTemplateColumns:'2fr 1fr 1fr',gap:9}}><label style={label}>Nome da categoria<input required style={input} value={editDraft.name} onChange={e=>setEditDraft({...editDraft,name:e.target.value})}/></label><label style={label}>Cidade<select disabled style={input} value={editDraft.city_id}><option value={editDraft.city_id}>{cityName(editDraft.city_id)}</option></select></label><label style={label}>Tipo de veículo<select style={input} value={editDraft.required_vehicle_type} onChange={e=>setEditDraft({...editDraft,required_vehicle_type:e.target.value})}><option value="car">Carro</option><option value="motorcycle">Moto</option><option value="">Qualquer veículo</option></select></label></div>
    {fareFields(editDraft,setEditDraft)}
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:9,alignItems:'end'}}><label style={label}>Novo ícone do mapa (opcional)<input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" style={input} onChange={e=>setEditMarker(e.target.files?.[0]||null)}/></label><label style={{...label,display:'flex',alignItems:'center',gap:8,paddingBottom:11}}><input type="checkbox" checked={editDraft.active} onChange={e=>setEditDraft({...editDraft,active:e.target.checked})}/> Categoria ativa para novas corridas</label></div>
    <div style={{display:'flex',justifyContent:'flex-end',gap:9}}><button type="button" style={secondary} onClick={closeEdit}>Cancelar</button><button disabled={busy} style={btn}>{busy?'Salvando...':'Salvar categoria e tarifas'}</button></div>
   </div>
  </form>}

  <div style={{display:'grid',gridTemplateColumns:'minmax(310px,390px) minmax(0,1fr)',gap:16,alignItems:'start'}}>
   <form onSubmit={createCategory} style={{...box,position:'sticky',top:18}}><h2 style={{marginTop:0}}>Nova categoria</h2><p style={{color:'#a1a1aa',fontSize:13}}>Ex.: Econômico, Moto, Premium, Executivo.</p><div style={{display:'grid',gap:9}}>
    <label style={label}>Nome<input required placeholder="Econômico" style={input} value={createDraft.name} onChange={e=>setCreateDraft({...createDraft,name:e.target.value})}/></label>
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:9}}><label style={label}>Cidade<select required style={input} value={createDraft.city_id} onChange={e=>setCreateDraft({...createDraft,city_id:e.target.value})}>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select></label><label style={label}>Tipo de veículo<select style={input} value={createDraft.required_vehicle_type} onChange={e=>setCreateDraft({...createDraft,required_vehicle_type:e.target.value})}><option value="car">Carro</option><option value="motorcycle">Moto</option><option value="">Qualquer veículo</option></select></label></div>
    {fareFields(createDraft,setCreateDraft)}
    <label style={label}>Ícone/foto do veículo no mapa<input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" style={input} onChange={e=>setCreateMarker(e.target.files?.[0]||null)}/></label>
    <button disabled={busy||!cities.length} style={btn}>{busy?'Salvando...':'Criar categoria'}</button>
   </div></form>

   <section style={box}><div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap',marginBottom:12}}><div><h2 style={{margin:0}}>Categorias cadastradas</h2><p style={{color:'#a1a1aa',fontSize:13,margin:'5px 0 0'}}>{items.length} categoria(s). As bloqueadas pela Matriz ficam somente para consulta.</p></div><input placeholder="Buscar categoria..." style={{...input,maxWidth:280}} value={query} onChange={e=>setQuery(e.target.value)}/></div>
    <div style={{display:'grid',gap:10}}>{filtered.map(c=><article key={c.id} style={{...box,padding:14,borderColor:c.locked_by_matrix?'#4b4020':'#292929'}}>
     <div style={{display:'grid',gridTemplateColumns:'58px minmax(0,1fr) auto',gap:12,alignItems:'center'}}>
      <div>{c.map_marker_url||c.icon_url?<img src={c.map_marker_url||c.icon_url||''} alt={c.name} style={{width:52,height:52,borderRadius:'50%',objectFit:'cover',border:'2px solid #ffd400'}}/>:<div style={{width:52,height:52,borderRadius:'50%',background:'#222',display:'grid',placeItems:'center',fontSize:26}}>{c.required_vehicle_type==='motorcycle'?'🏍️':'🚗'}</div>}</div>
      <div><div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><strong style={{fontSize:17}}>{c.name}</strong><span style={{fontSize:11,padding:'3px 7px',borderRadius:99,background:c.active?'#15351e':'#3a2525',color:c.active?'#86efac':'#fca5a5'}}>{c.active?'ATIVA':'INATIVA'}</span>{c.locked_by_matrix&&<span style={{fontSize:11,padding:'3px 7px',borderRadius:99,background:'#4b4020',color:'#ffe66b'}}>BLOQUEADA PELA MATRIZ</span>}</div><div style={{color:'#a1a1aa',fontSize:13,marginTop:4}}>{cityName(c.city_id)} · {c.required_vehicle_type==='motorcycle'?'Moto':c.required_vehicle_type==='car'?'Carro':'Qualquer veículo'}</div></div>
      <div style={{display:'flex',gap:7,flexWrap:'wrap',justifyContent:'flex-end'}}><button disabled={busy||c.locked_by_matrix} style={secondary} onClick={()=>startEdit(c)}>{c.locked_by_matrix?'Somente leitura':'Editar'}</button><button disabled={busy||c.locked_by_matrix} style={{...btn,background:c.active?'#3a2525':'#ffd400',color:c.active?'#fecaca':'#000'}} onClick={()=>void toggle(c)}>{c.active?'Desativar':'Ativar'}</button></div>
     </div>
     <div style={{display:'grid',gridTemplateColumns:'repeat(5,minmax(100px,1fr))',gap:8,marginTop:12,paddingTop:12,borderTop:'1px solid #292929'}}>
      <div><small style={{color:'#71717a'}}>Preço base</small><div style={{fontWeight:800}}>{money(c.base_fare)}</div></div><div><small style={{color:'#71717a'}}>Por km</small><div style={{fontWeight:800}}>{money(c.price_per_km)}</div></div><div><small style={{color:'#71717a'}}>Por minuto</small><div style={{fontWeight:800}}>{money(c.price_per_minute)}</div></div><div><small style={{color:'#71717a'}}>Tarifa mínima</small><div style={{fontWeight:800}}>{money(c.minimum_fare)}</div></div><div><small style={{color:'#71717a'}}>Cancelamento</small><div style={{fontWeight:800}}>{money(c.cancellation_fee)}</div></div>
     </div>
     <div style={{display:'flex',gap:16,flexWrap:'wrap',marginTop:9,color:'#a1a1aa',fontSize:12}}><span>Dinâmica: {Number(c.dynamic_multiplier||1).toFixed(2)}x</span><span>Espera grátis: {Number(c.wait_tolerance_minutes||0)} min</span><span>Após espera: {money(c.waiting_fee_per_minute)}/min</span><span>Alerta desvio: {Number(c.route_deviation_threshold_m||0)} m</span></div>
    </article>)}{!filtered.length&&<div style={{padding:30,textAlign:'center',color:'#71717a'}}>Nenhuma categoria encontrada.</div>}</div>
   </section>
  </div>
 </div></main>
}
