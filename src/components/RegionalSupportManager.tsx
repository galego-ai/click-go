'use client'

import {useEffect,useState} from 'react'
import {supabase} from '@/lib/supabase'

type Ticket={id:string;requester_id:string|null;subject:string;priority:string;status:string;description:string;created_at:string}
type Profile={id:string;full_name:string|null;phone:string|null;email:string|null;role:string}

export default function RegionalSupportManager(){
 const[rows,setRows]=useState<Ticket[]>([]),[profiles,setProfiles]=useState<Profile[]>([]),[msg,setMsg]=useState('Carregando chamados…')
 async function load(){const[t,p]=await Promise.all([supabase.from('support_tickets').select('id,requester_id,subject,priority,status,description,created_at').order('created_at',{ascending:false}).limit(100),supabase.from('profiles').select('id,full_name,phone,email,role')]);if(t.error){setMsg(t.error.message);return}setRows((t.data||[]) as Ticket[]);setProfiles((p.data||[]) as Profile[]);setMsg('')}
 useEffect(()=>{void load();const ch=supabase.channel('regional-support-live').on('postgres_changes',{event:'*',schema:'public',table:'support_tickets'},()=>void load()).subscribe();return()=>{void supabase.removeChannel(ch)}},[])
 async function changeStatus(id:string,status:string){const{error}=await supabase.from('support_tickets').update({status,updated_at:new Date().toISOString(),closed_at:status==='closed'?new Date().toISOString():null}).eq('id',id);if(error){setMsg(error.message);return}void load()}
 const who=(id:string|null)=>profiles.find(p=>p.id===id)
 return <>{msg&&<div className="regional-alert">{msg}</div>}<div className="card"><div className="section-heading"><div><h2>Chamados da operação</h2><p className="subtitle">Consulte passageiro, motorista e corrida vinculada sem acessar dados de outras franquias.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Assunto</th><th>Solicitante</th><th>Prioridade</th><th>Status</th><th>Aberto em</th><th>Ação</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={6} className="empty">Nenhum chamado aberto para esta operação.</td></tr>:rows.map(t=>{const p=who(t.requester_id);return <tr key={t.id}><td><strong>{t.subject}</strong><br/><span className="empty">{t.description}</span></td><td>{p?.full_name||'Usuário'}<br/><span className="empty">{p?.phone||p?.email||''}</span></td><td><span className={'pill '+(t.priority==='urgent'?'red':t.priority==='high'?'yellow':'')}>{t.priority}</span></td><td>{t.status}</td><td>{new Date(t.created_at).toLocaleString('pt-BR')}</td><td><select className="input" value={t.status} onChange={e=>void changeStatus(t.id,e.target.value)}><option value="open">Aberto</option><option value="in_progress">Em andamento</option><option value="waiting">Aguardando</option><option value="resolved">Resolvido</option><option value="closed">Fechado</option></select></td></tr>})}</tbody></table></div></div></>
}
