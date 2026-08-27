'use client'

import {useEffect,useMemo,useState} from 'react'
import type {CSSProperties} from 'react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Category={
 id:string
 name:string
 city_id:string
 required_vehicle_type:string|null
 active:boolean
 locked_by_matrix:boolean
 base_fare:number|string
 price_per_km:number|string
 price_per_minute:number|string
 minimum_fare:number|string
 dynamic_multiplier:number|string
 taximeter_enabled:boolean
 taximeter_base_fare:number|string|null
 taximeter_price_per_km:number|string|null
 taximeter_price_per_minute:number|string|null
 taximeter_minimum_fare:number|string|null
 taximeter_multiplier:number|string|null
}
type Draft={enabled:boolean;base_fare:string;price_per_km:string;price_per_minute:string;minimum_fare:string;multiplier:string}

const input:CSSProperties={width:'100%',background:'#0b0b0b',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px',boxSizing:'border-box'}
const box:CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const label:CSSProperties={fontSize:12,color:'#a1a1aa',display:'grid',gap:5}
const btn:CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:900,cursor:'pointer'}
const money=(v:number|string|null)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))
const vehicle=(v:string|null)=>v==='motorcycle'?'Moto':v==='car'?'Carro':'Qualquer veículo'

function effective(c:Category):Draft{
 return{
  enabled:c.taximeter_enabled!==false,
  base_fare:String(c.taximeter_base_fare??c.base_fare??0),
  price_per_km:String(c.taximeter_price_per_km??c.price_per_km??0),
  price_per_minute:String(c.taximeter_price_per_minute??c.price_per_minute??0),
  minimum_fare:String(c.taximeter_minimum_fare??c.minimum_fare??0),
  multiplier:String(c.taximeter_multiplier??c.dynamic_multiplier??1),
 }
}

export default function TaximetroTarifasPage(){
 const[cities,setCities]=useState<City[]>([])
 const[items,setItems]=useState<Category[]>([])
 const[drafts,setDrafts]=useState<Record<string,Draft>>({})
 const[msg,setMsg]=useState('')
 const[busy,setBusy]=useState(false)
 const[query,setQuery]=useState('')

 useEffect(()=>{void load()},[])

 const filtered=useMemo(()=>{
  const q=query.trim().toLowerCase()
  if(!q)return items
  return items.filter(c=>`${c.name} ${cityName(c.city_id)} ${vehicle(c.required_vehicle_type)}`.toLowerCase().includes(q))
 },[items,query,cities])

 function cityName(id:string){const c=cities.find(x=>x.id===id);return c?`${c.name}/${c.state}`:'Cidade'}
 function inherited(c:Category){return c.taximeter_base_fare==null&&c.taximeter_price_per_km==null&&c.taximeter_price_per_minute==null&&c.taximeter_minimum_fare==null&&c.taximeter_multiplier==null}

 async function load(){
  setBusy(true);setMsg('')
  try{
   const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login novamente.')
   const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
   const fid=String(p?.franchise_id||user.app_metadata?.franchise_id||'')
   if(!fid)throw new Error('Franquia não identificada.')
   const{data:fc,error:fce}=await supabase.from('franchise_cities').select('city_id').eq('franchise_id',fid);if(fce)throw fce
   const ids=(fc||[]).map(x=>x.city_id).filter((x):x is string=>Boolean(x))
   let cityRows:City[]=[]
   if(ids.length){const{data:cr,error:ce}=await supabase.from('cities').select('id,name,state').in('id',ids).order('name');if(ce)throw ce;cityRows=(cr||[]) as City[]}
   setCities(cityRows)
   const{data,error}=await supabase.from('ride_categories').select('id,name,city_id,required_vehicle_type,active,locked_by_matrix,base_fare,price_per_km,price_per_minute,minimum_fare,dynamic_multiplier,taximeter_enabled,taximeter_base_fare,taximeter_price_per_km,taximeter_price_per_minute,taximeter_minimum_fare,taximeter_multiplier').eq('franchise_id',fid).order('name');if(error)throw error
   const rows=(data||[]) as Category[]
   setItems(rows)
   const next:Record<string,Draft>={};for(const c of rows)next[c.id]=effective(c);setDrafts(next)
  }catch(e){setMsg(e instanceof Error?e.message:'Erro ao carregar tarifas do taxímetro.')}finally{setBusy(false)}
 }

 function change(id:string,key:keyof Draft,value:string|boolean){setDrafts(v=>({...v,[id]:{...(v[id]||{}),[key]:value} as Draft}))}
 function validate(d:Draft){
  const nums=[d.base_fare,d.price_per_km,d.price_per_minute,d.minimum_fare].map(Number)
  if(nums.some(v=>!Number.isFinite(v)||v<0))return 'Informe valores válidos e não negativos.'
  const m=Number(d.multiplier);if(!Number.isFinite(m)||m<1||m>10)return 'O multiplicador deve ficar entre 1 e 10.'
  return ''
 }

 async function save(c:Category){
  const d=drafts[c.id]||effective(c);const bad=validate(d);if(bad){setMsg(bad);return}
  if(c.locked_by_matrix){setMsg('Esta categoria foi bloqueada pela Matriz e não pode ser alterada.');return}
  setBusy(true);setMsg('')
  try{
   const{error}=await supabase.rpc('franchise_save_taximeter_tariff',{p_category_id:c.id,p_payload:{enabled:d.enabled,base_fare:Number(d.base_fare),price_per_km:Number(d.price_per_km),price_per_minute:Number(d.price_per_minute),minimum_fare:Number(d.minimum_fare),multiplier:Number(d.multiplier)}});if(error)throw error
   setMsg(`Tarifa do taxímetro salva para ${c.name}. O app Motorista já usará esses valores na próxima sessão.`);await load()
  }catch(e){setMsg(e instanceof Error?e.message:'Erro ao salvar tarifa do taxímetro.')}finally{setBusy(false)}
 }

 return <div style={{maxWidth:1250,margin:'0 auto',color:'#171717'}}>
  <div className="regional-heading"><div><div style={{color:'#a38600',fontWeight:900}}>OPERAÇÃO · TAXÍMETRO</div><h1>Tarifas do Taxímetro</h1><p>Configure os valores exclusivos usados no taxímetro da tela inicial do app Motorista.</p></div></div>

  <div style={{background:'#fff8ce',border:'1px solid #e2c700',color:'#5c4b00',padding:14,borderRadius:12,marginBottom:16,lineHeight:1.5}}><strong>Estas tarifas são separadas das corridas solicitadas pelo passageiro.</strong><br/>Bandeirada, km, minuto, tarifa mínima e multiplicador configurados aqui são usados somente no modo Taxímetro. Enquanto uma categoria ainda não tiver sido personalizada, o sistema usa os valores das Tarifas Locais como padrão.</div>
  {msg&&<div style={{background:'#111',color:'#ffe66b',border:'1px solid #665600',padding:13,borderRadius:12,marginBottom:16}}>{msg}</div>}

  <div style={{display:'flex',gap:10,alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',marginBottom:14}}>
   <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Buscar categoria, cidade ou veículo..." style={{...input,maxWidth:430}}/>
   <button style={btn} onClick={()=>void load()} disabled={busy}>{busy?'Atualizando...':'Atualizar'}</button>
  </div>

  <div style={{display:'grid',gap:14}}>
   {filtered.map(c=>{const d=drafts[c.id]||effective(c);return <section key={c.id} style={{...box,color:'#fff',opacity:c.active?1:.72}}>
    <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'flex-start',flexWrap:'wrap'}}>
     <div><div style={{color:'#ffd400',fontWeight:900,fontSize:12}}>{cityName(c.city_id)} · {vehicle(c.required_vehicle_type)}</div><h2 style={{margin:'5px 0 2px'}}>{c.name}</h2><div style={{color:'#a1a1aa',fontSize:12}}>{c.locked_by_matrix?'🔒 Bloqueada pela Matriz':inherited(c)?'Usando as Tarifas Locais como padrão':'Tarifa própria do taxímetro configurada'}</div></div>
     <label style={{display:'flex',alignItems:'center',gap:8,fontWeight:800,color:d.enabled?'#8bd99c':'#ff9c9c'}}><input type="checkbox" checked={d.enabled} disabled={c.locked_by_matrix} onChange={e=>change(c.id,'enabled',e.target.checked)}/>Taxímetro {d.enabled?'ativado':'desativado'}</label>
    </div>

    <div style={{display:'grid',gridTemplateColumns:'repeat(5,minmax(0,1fr))',gap:10,marginTop:16}}>
     <label style={label}>Bandeirada / preço base (R$)<input type="number" min="0" step="0.01" disabled={c.locked_by_matrix} style={input} value={d.base_fare} onChange={e=>change(c.id,'base_fare',e.target.value)}/></label>
     <label style={label}>Preço por km (R$)<input type="number" min="0" step="0.01" disabled={c.locked_by_matrix} style={input} value={d.price_per_km} onChange={e=>change(c.id,'price_per_km',e.target.value)}/></label>
     <label style={label}>Preço por minuto (R$)<input type="number" min="0" step="0.01" disabled={c.locked_by_matrix} style={input} value={d.price_per_minute} onChange={e=>change(c.id,'price_per_minute',e.target.value)}/></label>
     <label style={label}>Tarifa mínima (R$)<input type="number" min="0" step="0.01" disabled={c.locked_by_matrix} style={input} value={d.minimum_fare} onChange={e=>change(c.id,'minimum_fare',e.target.value)}/></label>
     <label style={label}>Multiplicador / bandeira<input type="number" min="1" max="10" step="0.01" disabled={c.locked_by_matrix} style={input} value={d.multiplier} onChange={e=>change(c.id,'multiplier',e.target.value)}/></label>
    </div>

    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap',marginTop:14}}>
     <div style={{fontSize:12,color:'#a1a1aa'}}>Prévia: base {money(d.base_fare)} · {money(d.price_per_km)}/km · {money(d.price_per_minute)}/min · mínima {money(d.minimum_fare)} · x{Number(d.multiplier||1).toFixed(2)}</div>
     <button style={{...btn,opacity:c.locked_by_matrix?0.55:1}} disabled={busy||c.locked_by_matrix} onClick={()=>void save(c)}>Salvar tarifa do taxímetro</button>
    </div>
   </section>})}
   {!busy&&filtered.length===0&&<div style={{background:'#fff',border:'1px solid #e2e2e2',padding:20,borderRadius:14,color:'#666'}}>Nenhuma categoria encontrada. Crie primeiro uma categoria em <strong>Tarifas Locais</strong>.</div>}
  </div>
  <style>{`@media(max-width:980px){section>div:nth-of-type(2){grid-template-columns:repeat(2,minmax(0,1fr))!important}}@media(max-width:620px){section>div:nth-of-type(2){grid-template-columns:1fr!important}}`}</style>
 </div>
}
