'use client'

import {useEffect,useMemo,useState} from 'react'
import {AlertTriangle, Building2, MapPin, Plus, ShieldCheck, Trash2} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string;active:boolean}
type Franchise={id:string;trade_name:string;license_status:string;active:boolean}
type LinkRow={franchise_id:string;city_id:string}
type Owner={id:string;name:string}

export default function CityManager(){
 const[cities,setCities]=useState<City[]>([]),[franchises,setFranchises]=useState<Franchise[]>([]),[links,setLinks]=useState<LinkRow[]>([])
 const[name,setName]=useState(''),[state,setState]=useState('GO'),[query,setQuery]=useState(''),[msg,setMsg]=useState('')
 const[target,setTarget]=useState<Record<string,string>>({}),[reason,setReason]=useState<Record<string,string>>({}),[busy,setBusy]=useState('')

 async function load(){
  const[c,f,l]=await Promise.all([
   supabase.from('cities').select('id,name,state,active').order('state').order('name'),
   supabase.from('franchises').select('id,trade_name,license_status,active').is('deleted_at',null).order('trade_name'),
   supabase.from('franchise_cities').select('franchise_id,city_id'),
  ])
  const error=c.error||f.error||l.error
  if(error){setMsg(error.message);return}
  setCities((c.data||[]) as City[]);setFranchises((f.data||[]) as Franchise[]);setLinks((l.data||[]) as LinkRow[])
 }
 useEffect(()=>{void load()},[])

 const franchiseMap=useMemo(()=>new Map(franchises.map(f=>[f.id,f])),[franchises])
 const ownerMap=useMemo(()=>{const m=new Map<string,Owner>();for(const x of links){const f=franchiseMap.get(x.franchise_id);if(f)m.set(x.city_id,{id:f.id,name:f.trade_name})}return m},[links,franchiseMap])
 const visible=useMemo(()=>{const q=query.trim().toLowerCase();return !q?cities:cities.filter(c=>`${c.name} ${c.state} ${ownerMap.get(c.id)?.name||''}`.toLowerCase().includes(q))},[cities,query,ownerMap])

 async function add(e:React.FormEvent){e.preventDefault();setBusy('new');const{error}=await supabase.from('cities').insert({name:name.trim(),state:state.trim().toUpperCase(),country:'BR',active:true});setBusy('');if(error){setMsg(error.message);return}setName('');setMsg('Cidade cadastrada e pronta para receber um território.');void load()}
 async function toggle(c:City){setBusy(c.id);const{error}=await supabase.from('cities').update({active:!c.active}).eq('id',c.id);setBusy('');setMsg(error?error.message:`${c.name} ${c.active?'bloqueada':'ativada'}.`);if(!error)void load()}
 async function assign(c:City,override=false){
  const franchiseId=target[c.id];const why=(reason[c.id]||'').trim();if(!franchiseId){setMsg(`Selecione a franquia para ${c.name}.`);return}if(!why){setMsg('Informe a justificativa da alteração territorial.');return}
  setBusy(c.id)
  const{data,error}=await supabase.rpc('matrix_assign_franchise_city',{p_franchise_id:franchiseId,p_city_id:c.id,p_reason:why,p_override:override})
  setBusy('')
  if(error){setMsg(error.message);return}
  const result=data as {ok?:boolean;status?:string;current_franchise_name?:string}
  if(result?.status==='conflict'&&!override){setMsg(`CONFLITO: ${c.name}/${c.state} já pertence à franquia ${result.current_franchise_name}. Use “Sobrescrever território” somente se a Matriz decidiu transferir a cidade.`);return}
  setMsg(result?.status==='overridden'?`Território transferido para a nova franquia. A sobrescrita ficou registrada na auditoria.`:`${c.name}/${c.state} vinculada à franquia selecionada.`)
  setReason(v=>({...v,[c.id]:''}));void load()
 }
 async function removeTerritory(c:City){const owner=ownerMap.get(c.id);if(!owner)return;const why=(reason[c.id]||'').trim();if(!why){setMsg('Informe a justificativa antes de remover um território.');return}if(!confirm(`Remover ${c.name}/${c.state} da franquia ${owner.name}?`))return;setBusy(c.id);const{error}=await supabase.rpc('matrix_remove_franchise_city',{p_franchise_id:owner.id,p_city_id:c.id,p_reason:why});setBusy('');setMsg(error?error.message:'Território removido e registrado na auditoria.');if(!error){setReason(v=>({...v,[c.id]:''}));void load()}}
 async function removeCity(c:City){if(ownerMap.has(c.id)){setMsg('Remova primeiro o vínculo territorial da cidade. A Matriz não pode excluir uma cidade que pertence a uma franquia.');return}if(!confirm(`Excluir definitivamente ${c.name}/${c.state}?`))return;setBusy(c.id);const{error}=await supabase.from('cities').delete().eq('id',c.id);setBusy('');setMsg(error?error.message:'Cidade excluída.');if(!error)void load()}

 return <>
  <div className="card"><div className="section-heading"><div><div className="eyebrow">Cadastro territorial</div><h2>Adicionar cidade à rede</h2><p className="subtitle">Cadastrar uma cidade não dá exclusividade automaticamente. O vínculo com a franquia é feito logo abaixo.</p></div><MapPin size={22}/></div><form onSubmit={add}><div className="form-grid"><div className="field"><label>Cidade</label><input className="input" value={name} onChange={e=>setName(e.target.value)} required placeholder="Ex.: Uruaçu"/></div><div className="field"><label>UF</label><input className="input" maxLength={2} value={state} onChange={e=>setState(e.target.value)} required/></div></div><div className="toolbar" style={{marginTop:14}}><button className="button" disabled={busy==='new'}><Plus size={15}/>{busy==='new'?'Salvando...':'Cadastrar cidade'}</button></div></form></div>

  <div className="section"><div className="card"><div className="section-heading"><div><div className="eyebrow">Exclusividade territorial</div><h2>Gestão de territórios</h2><p className="subtitle">Uma cidade deve pertencer a uma única franquia. Sobrescrições são tratadas como transferência e exigem justificativa.</p></div><ShieldCheck size={22}/></div><div className="field"><label>Buscar cidade ou franquia</label><input className="input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Uruaçu, GO ou nome da franquia"/></div>{msg&&<div className={msg.startsWith('CONFLITO')?'regional-alert':''} style={{marginTop:12}}>{msg}</div>}</div>
  <div className="table-wrap"><table className="table"><thead><tr><th>Cidade/UF</th><th>Status</th><th>Franquia responsável</th><th>Novo vínculo</th><th>Justificativa</th><th>Ações</th></tr></thead><tbody>{visible.length===0?<tr><td colSpan={6} className="empty">Nenhuma cidade encontrada.</td></tr>:visible.map(c=>{const owner=ownerMap.get(c.id);const chosen=target[c.id];const conflict=Boolean(owner&&chosen&&chosen!==owner.id);return <tr key={c.id}><td><strong>{c.name}/{c.state}</strong></td><td><span className={'pill '+(c.active?'green':'red')}>{c.active?'Ativa':'Bloqueada'}</span></td><td>{owner?<span><Building2 size={13} style={{verticalAlign:'-2px',marginRight:5}}/>{owner.name}</span>:<span className="pill">Sem franquia</span>}</td><td><select className="input" value={chosen||owner?.id||''} onChange={e=>setTarget(v=>({...v,[c.id]:e.target.value}))}><option value="">Selecione</option>{franchises.map(f=><option key={f.id} value={f.id}>{f.trade_name}{!f.active?' (inativa)':''}</option>)}</select>{conflict&&<small style={{display:'block',marginTop:5}}><AlertTriangle size={12} style={{verticalAlign:'-2px'}}/> conflito territorial</small>}</td><td><input className="input" value={reason[c.id]||''} onChange={e=>setReason(v=>({...v,[c.id]:e.target.value}))} placeholder="Motivo obrigatório"/></td><td><div className="toolbar">{!owner&&<button className="button" disabled={busy===c.id} onClick={()=>void assign(c,false)}>Liberar</button>}{owner&&chosen&&chosen!==owner.id&&<><button className="button secondary" disabled={busy===c.id} onClick={()=>void assign(c,false)}>Verificar conflito</button><button className="button danger" disabled={busy===c.id} onClick={()=>{if(confirm(`Sobrescrever o território de ${owner.name} e transferir ${c.name}/${c.state}?`))void assign(c,true)}}><AlertTriangle size={14}/>Sobrescrever</button></>}{owner&&(!chosen||chosen===owner.id)&&<button className="button secondary" disabled={busy===c.id} onClick={()=>void removeTerritory(c)}>Remover vínculo</button>}<button className="button secondary" disabled={busy===c.id} onClick={()=>void toggle(c)}>{c.active?'Bloquear cidade':'Ativar cidade'}</button>{!owner&&<button className="button danger" disabled={busy===c.id} onClick={()=>void removeCity(c)}><Trash2 size={14}/>Excluir</button>}</div></td></tr>})}</tbody></table></div></div>
 </>
}
