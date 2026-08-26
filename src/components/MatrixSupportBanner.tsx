'use client'

import Link from 'next/link'
import {useEffect,useState} from 'react'
import {Headphones,LogOut,MapPin} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Session={id:string;franchise_id:string;franchise_name:string;reason:string;started_at:string;active:boolean;cities:City[]}

export default function MatrixSupportBanner(){
 const[session,setSession]=useState<Session|null>(null),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 async function load(){const{data,error}=await supabase.rpc('matrix_active_support_session');if(error){setMsg(error.message);return}setSession((data||null) as Session|null)}
 useEffect(()=>{void load();const onChange=()=>void load();window.addEventListener('clickgo-support-session-changed',onChange);return()=>window.removeEventListener('clickgo-support-session-changed',onChange)},[])
 async function end(){if(!session)return;setBusy(true);const{error}=await supabase.rpc('matrix_end_support_session',{p_session_id:session.id});setBusy(false);if(error){setMsg(error.message);return}setSession(null);window.dispatchEvent(new Event('clickgo-support-session-changed'))}
 if(!session)return msg?<div style={{padding:'8px 14px',marginBottom:12,border:'1px solid #f0c36a',background:'#fff8dd',borderRadius:10,fontSize:12}}>{msg}</div>:null
 const cities=(session.cities||[]).map(c=>`${c.name}/${c.state}`).join(' · ')
 return <div className="matrix-support-banner"><style>{`.matrix-support-banner{position:sticky;top:0;z-index:70;margin:-28px -28px 20px;padding:11px 18px;background:#ffd400;color:#161616;border-bottom:1px solid #c4a300;box-shadow:0 4px 14px rgba(0,0,0,.08);display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.matrix-support-banner .support-main{display:flex;align-items:center;gap:10px;min-width:0}.matrix-support-banner .support-icon{width:34px;height:34px;border-radius:10px;background:#111;color:#ffd400;display:grid;place-items:center;flex:0 0 auto}.matrix-support-banner strong{display:block;font-size:13px}.matrix-support-banner small{display:block;font-size:11px;opacity:.78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:720px}.matrix-support-banner .support-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.matrix-support-banner a,.matrix-support-banner button{border:1px solid rgba(0,0,0,.25);background:#fff8ce;color:#111;border-radius:8px;padding:7px 9px;font-size:11px;font-weight:700;display:inline-flex;align-items:center;gap:5px}.matrix-support-banner button{cursor:pointer}.matrix-support-banner button.end{background:#111;color:#fff;border-color:#111}@media(max-width:820px){.matrix-support-banner{margin:-18px -18px 16px;position:relative}.matrix-support-banner small{white-space:normal;max-width:none}}`}</style><div className="support-main"><span className="support-icon"><Headphones size={17}/></span><div><strong>MODO SUPORTE ATIVO · Matriz (Suporte) · {session.franchise_name}</strong><small>{cities?`Território: ${cities} · `:''}Motivo: {session.reason} · iniciado {new Date(session.started_at).toLocaleString('pt-BR')}</small></div></div><div className="support-actions"><Link href="/corridas"><MapPin size={13}/>Corridas</Link><Link href="/mapa">Mapa</Link><Link href="/motoristas">Motoristas</Link><Link href="/tarifas">Tarifas</Link><Link href="/suporte">Chamados</Link><button className="end" onClick={()=>void end()} disabled={busy}><LogOut size={13}/>{busy?'Encerrando...':'Encerrar suporte'}</button></div></div>
}
