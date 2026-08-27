'use client'

import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Category={id:string;name:string;city_id:string;cancellation_fee:number|string;locked_by_matrix:boolean}
type City={id:string;name:string;state:string}
type PolicyRow={setting_value:any;locked_by_matrix:boolean;source:string}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const input:React.CSSProperties={width:'100%',background:'#0b0b0b',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})

export default function FranchiseCancellationPage(){
 const[fid,setFid]=useState(''),[cities,setCities]=useState<City[]>([]),[items,setItems]=useState<Category[]>([]),[minutes,setMinutes]=useState('2'),[policy,setPolicy]=useState<PolicyRow|null>(null),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{load()},[])
 async function load(){setBusy(true);setMsg('');try{
  const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login como franqueado.')
  const{data:p,error:pe}=await supabase.from('profiles').select('role,franchise_id').eq('id',user.id).single();if(pe)throw pe
  if(!p||p.role!=='franchise_admin'||!p.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
  setFid(p.franchise_id)
  const[fc,c,s]=await Promise.all([
   supabase.from('franchise_cities').select('city_id,cities(id,name,state)').eq('franchise_id',p.franchise_id),
   supabase.from('ride_categories').select('id,name,city_id,cancellation_fee,locked_by_matrix').eq('franchise_id',p.franchise_id).order('name'),
   supabase.from('franchise_settings').select('setting_value,locked_by_matrix,source').eq('franchise_id',p.franchise_id).eq('setting_key','passenger_cancellation_policy').maybeSingle()
  ])
  if(fc.error)throw fc.error;if(c.error)throw c.error;if(s.error)throw s.error
  setCities((fc.data||[]).map((x:any)=>x.cities).filter(Boolean));setItems((c.data||[]) as Category[])
  const pr=(s.data||null) as PolicyRow|null;setPolicy(pr);const seconds=Number(pr?.setting_value?.free_seconds??120);setMinutes(String(Math.round((seconds/60)*100)/100))
 }catch(e:any){setMsg(e.message||'Erro ao carregar política de cancelamento.')}finally{setBusy(false)}}
 async function savePolicy(){if(!fid)return;if(policy?.locked_by_matrix){setMsg('Este tempo foi bloqueado pela Matriz e não pode ser alterado pela franquia.');return}const n=Number(minutes);if(!Number.isFinite(n)||n<0||n>1440){setMsg('Informe um tempo entre 0 e 1440 minutos.');return}setBusy(true);const seconds=Math.round(n*60);const{error}=await supabase.rpc('franchise_set_passenger_cancellation_policy',{p_free_seconds:seconds});setMsg(error?error.message:`Tempo grátis atualizado para ${n} minuto${n===1?'':'s'} após o motorista iniciar o deslocamento.`);if(!error)await load();setBusy(false)}
 async function saveFee(c:Category){
  if(c.locked_by_matrix){setMsg('Esta categoria está bloqueada pela Matriz.');return}
  const value=Number(c.cancellation_fee);if(!Number.isFinite(value)||value<0){setMsg('Informe uma taxa válida.');return}
  setBusy(true)
  const{error}=await supabase.rpc('franchise_upsert_ride_category',{p_category_id:c.id,p_city_id:c.city_id,p_payload:{cancellation_fee:value}})
  setMsg(error?error.message:`Taxa de ${c.name} atualizada para ${money(value)}.`);if(!error)await load();setBusy(false)
 }
 const cityName=(id:string)=>{const c=cities.find(x=>x.id===id);return c?`${c.name}/${c.state}`:'Cidade'}
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1100,margin:'0 auto',display:'grid',gap:16}}>
  <div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO · Franqueado</div><h1>Cancelamento do passageiro</h1><p style={{color:'#9ca3af'}}>O passageiro pode cancelar sem taxa enquanto o motorista ainda não iniciou o deslocamento. Depois que o motorista tocar em “Iniciar deslocamento”, começa o tempo grátis configurado abaixo. Quando esse tempo termina, a taxa da categoria é registrada e somada à próxima corrida do mesmo passageiro.</p></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b'}}>{msg}</div>}
  <section style={box}><div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'end',flexWrap:'wrap'}}><label style={{display:'grid',gap:6,minWidth:260}}>Tempo grátis após iniciar deslocamento (minutos)<input type="number" min="0" max="1440" step="0.5" value={minutes} disabled={!!policy?.locked_by_matrix} onChange={e=>setMinutes(e.target.value)} style={input}/></label><button disabled={busy||!!policy?.locked_by_matrix} onClick={savePolicy} style={{...btn,opacity:policy?.locked_by_matrix?0.55:1}}>{policy?.locked_by_matrix?'🔒 Bloqueado pela Matriz':busy?'Salvando...':'Salvar tempo grátis'}</button></div><p style={{color:'#9ca3af',fontSize:13,marginBottom:0}}>Exemplo: com 2 minutos, o passageiro continua cancelando grátis durante os primeiros 2 minutos após o motorista iniciar o deslocamento. Depois disso, passa a valer a taxa configurada para a categoria.</p></section>
  <section style={box}><h2>Taxa por categoria</h2><p style={{color:'#9ca3af'}}>A taxa não é cobrada na corrida cancelada. Ela fica pendente e entra automaticamente no valor da próxima corrida solicitada pelo passageiro.</p><div style={{display:'grid',gap:10}}>{items.map((c,i)=><div key={c.id} style={{...box,padding:14,display:'grid',gridTemplateColumns:'2fr 1fr auto',gap:12,alignItems:'end'}}><div><b>{c.name}</b><div style={{color:'#9ca3af',fontSize:12,marginTop:4}}>{cityName(c.city_id)}{c.locked_by_matrix?' · 🔒 Matriz':''}</div></div><label style={{display:'grid',gap:5,fontSize:12}}>Taxa de cancelamento (R$)<input type="number" min="0" step="0.01" disabled={c.locked_by_matrix} value={c.cancellation_fee} onChange={e=>setItems(v=>v.map((x,j)=>j===i?{...x,cancellation_fee:e.target.value}:x))} style={input}/></label><button disabled={busy||c.locked_by_matrix} onClick={()=>saveFee(c)} style={{...btn,opacity:c.locked_by_matrix?0.55:1}}>{c.locked_by_matrix?'Bloqueada':'Salvar taxa'}</button></div>)}{!items.length&&<div style={{color:'#9ca3af'}}>Nenhuma categoria cadastrada. Crie as categorias e tarifas primeiro.</div>}</div></section>
 </div></main>
}
