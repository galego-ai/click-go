'use client'
import { useEffect,useMemo,useState } from 'react'
import { supabase } from '@/lib/supabase'

type DriverRow={id:string;status:string;city_id:string|null;franchise_id:string|null;online:boolean;rating:number|string;created_at:string}
type Franchise={id:string;trade_name:string;active:boolean;deleted_at:string|null;blocked_at:string|null}
type City={id:string;name:string;state:string;active:boolean}
type FranchiseCity={franchise_id:string;city_id:string}
type Assignment={franchise_id:string;city_id:string;reset:boolean}

export default function OperationsManager({kind}:{kind:'drivers'|'rides'}){
 const[rows,setRows]=useState<any[]>([]);const[msg,setMsg]=useState('');const[busy,setBusy]=useState<string|null>(null)
 const[franchises,setFranchises]=useState<Franchise[]>([]);const[cities,setCities]=useState<City[]>([]);const[links,setLinks]=useState<FranchiseCity[]>([]);const[assignments,setAssignments]=useState<Record<string,Assignment>>({})
 const activeFranchises=useMemo(()=>franchises.filter(f=>f.active&&!f.deleted_at&&!f.blocked_at),[franchises])
 const franchiseName=(id:string|null)=>{if(!id)return 'Sem franquia';const f=franchises.find(x=>x.id===id);return f?`${f.trade_name}${!f.active||f.deleted_at||f.blocked_at?' (inativa/excluída)':''}`:id.slice(0,8)+'…'}
 const cityName=(id:string|null)=>{if(!id)return 'Sem cidade';const c=cities.find(x=>x.id===id);return c?`${c.name}/${c.state}`:id.slice(0,8)+'…'}
 const allowedCities=(fid:string)=>{const ids=new Set(links.filter(x=>x.franchise_id===fid).map(x=>x.city_id));return cities.filter(c=>c.active&&ids.has(c.id))}

 async function load(){
  setMsg('')
  if(kind==='rides'){
   const{data,error}=await supabase.from('rides').select('id,passenger_id,driver_id,franchise_id,city_id,status,estimated_fare,final_fare,requested_at').order('requested_at',{ascending:false}).limit(200)
   if(error)setMsg(error.message);else setRows(data||[]);return
  }
  const[d,f,c,l]=await Promise.all([
   supabase.from('drivers').select('id,status,city_id,franchise_id,online,rating,created_at').order('created_at',{ascending:false}).limit(200),
   supabase.from('franchises').select('id,trade_name,active,deleted_at,blocked_at').order('created_at',{ascending:false}),
   supabase.from('cities').select('id,name,state,active').order('name'),
   supabase.from('franchise_cities').select('franchise_id,city_id')
  ])
  if(d.error){setMsg(d.error.message);return}if(f.error){setMsg(f.error.message);return}if(c.error){setMsg(c.error.message);return}if(l.error){setMsg(l.error.message);return}
  const list=(d.data||[]) as DriverRow[];setRows(list);setFranchises((f.data||[]) as Franchise[]);setCities((c.data||[]) as City[]);setLinks((l.data||[]) as FranchiseCity[])
  setAssignments(prev=>{const next={...prev};list.forEach(r=>{if(!next[r.id])next[r.id]={franchise_id:r.franchise_id||'',city_id:r.city_id||'',reset:false}});return next})
 }
 useEffect(()=>{load();const table=kind==='drivers'?'drivers':'rides';const ch=supabase.channel(`admin-${table}`).on('postgres_changes',{event:'*',schema:'public',table},()=>load()).subscribe();return()=>{supabase.removeChannel(ch)}},[kind])
 async function driverStatus(id:string,status:string){setBusy(id);const{error}=await supabase.from('drivers').update({status,online:false}).eq('id',id);setBusy(null);setMsg(error?error.message:'Status atualizado.');if(!error)load()}
 async function reassign(r:DriverRow){const a=assignments[r.id];if(!a?.franchise_id){setMsg('Escolha a franquia correta.');return}if(!a.city_id){setMsg('Escolha uma cidade vinculada à franquia.');return}if(!confirm(a.reset?'Mover este motorista e reabrir a aprovação como PENDENTE?':'Mover este motorista mantendo o status atual?'))return;setBusy(r.id);const{error}=await supabase.rpc('super_admin_reassign_driver',{p_driver_id:r.id,p_franchise_id:a.franchise_id,p_city_id:a.city_id,p_reset_to_pending:a.reset});setBusy(null);setMsg(error?error.message:(a.reset?'Motorista reassociado e enviado novamente para aprovação do franqueado.':'Motorista reassociado com o status preservado.'));if(!error)load()}
 const brl=(v:any)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))

 if(kind==='drivers')return <>
  {!activeFranchises.length&&<div className="card" style={{borderColor:'#a16207',marginBottom:14}}><b>Nenhuma franquia ativa disponível.</b><p className="empty" style={{marginBottom:0}}>Crie uma franquia em <b>Franquias</b>, vincule uma cidade e gere o acesso do franqueado. Depois volte aqui para corrigir vínculos antigos.</p></div>}
  {msg&&<p className="empty">{msg}</p>}
  <div className="table-wrap"><table className="table" style={{minWidth:1180}}><thead><tr><th>Motorista</th><th>Vínculo atual</th><th>Status</th><th>Online</th><th>Avaliação</th><th>Corrigir franquia/cidade</th><th>Ação</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={7} className="empty">Nenhum motorista cadastrado.</td></tr>:(rows as DriverRow[]).map(r=>{const a=assignments[r.id]||{franchise_id:'',city_id:'',reset:false};const currentF=franchises.find(f=>f.id===r.franchise_id);const invalid=!currentF||!currentF.active||!!currentF.deleted_at||!!currentF.blocked_at||!r.city_id;return <tr key={r.id}><td><b>{r.id.slice(0,8)}…</b>{invalid&&<div style={{color:'#fbbf24',fontSize:12,marginTop:4}}>⚠ vínculo precisa de correção</div>}</td><td>{franchiseName(r.franchise_id)}<br/><span className="empty">{cityName(r.city_id)}</span></td><td><select className="input" value={r.status} disabled={busy===r.id} onChange={e=>driverStatus(r.id,e.target.value)}><option value="pending">Pendente</option><option value="approved">Aprovado</option><option value="rejected">Rejeitado</option><option value="blocked">Bloqueado</option></select></td><td><span className={'pill '+(r.online?'green':'')}>{r.online?'Online':'Offline'}</span></td><td>{Number(r.rating||0).toFixed(1)}</td><td><div style={{display:'grid',gap:7,minWidth:300}}><select className="input" value={a.franchise_id} onChange={e=>{const fid=e.target.value;setAssignments({...assignments,[r.id]:{...a,franchise_id:fid,city_id:''}})}}><option value="">Escolha a franquia ativa</option>{activeFranchises.map(f=><option key={f.id} value={f.id}>{f.trade_name}</option>)}</select><select className="input" value={a.city_id} disabled={!a.franchise_id} onChange={e=>setAssignments({...assignments,[r.id]:{...a,city_id:e.target.value}})}><option value="">Escolha a cidade</option>{allowedCities(a.franchise_id).map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select><label style={{fontSize:12,color:'#9ca3af'}}><input type="checkbox" checked={a.reset} onChange={e=>setAssignments({...assignments,[r.id]:{...a,reset:e.target.checked}})}/> Reabrir aprovação como pendente</label></div></td><td><button className="button" disabled={busy===r.id||!a.franchise_id||!a.city_id} onClick={()=>reassign(r)}>{busy===r.id?'Salvando...':'Corrigir vínculo'}</button></td></tr>})}</tbody></table></div>
 </>
 return <><p className="empty">{msg}</p><div className="table-wrap"><table className="table"><thead><tr><th>Corrida</th><th>Cidade</th><th>Franquia</th><th>Passageiro</th><th>Motorista</th><th>Status</th><th>Valor</th><th>Solicitada</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={8} className="empty">Nenhuma corrida registrada.</td></tr>:rows.map(r=><tr key={r.id}><td>{r.id.slice(0,8)}…</td><td>{r.city_id||'—'}</td><td>{r.franchise_id||'—'}</td><td>{r.passenger_id.slice(0,8)}…</td><td>{r.driver_id?r.driver_id.slice(0,8)+'…':'—'}</td><td>{r.status}</td><td>{brl(r.final_fare??r.estimated_fare)}</td><td>{new Date(r.requested_at).toLocaleString('pt-BR')}</td></tr>)}</tbody></table></div></>
}
