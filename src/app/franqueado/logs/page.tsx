'use client'

import {useEffect,useState} from 'react'
import {supabase} from '@/lib/supabase'

type LogRow={id:number;version:number;source:string;entity:string;action:string;created_at:string}
const sourceLabel:Record<string,string>={matrix:'Matriz',franchise:'Franqueado',staff:'Equipe',driver_app:'App Motorista',passenger_app:'App Passageiro',system:'Sistema'}

export default function FranchiseLogsPage(){
 const[rows,setRows]=useState<LogRow[]>([]),[msg,setMsg]=useState('Carregando logs...')
 useEffect(()=>{void load()},[])
 async function load(){const{data:{user}}=await supabase.auth.getUser();if(!user){setMsg('Sessão não encontrada.');return}const{data:p,error:pe}=await supabase.from('profiles').select('franchise_id').eq('id',user.id).single();if(pe||!p?.franchise_id){setMsg(pe?.message||'Franquia não vinculada.');return}const{data,error}=await supabase.from('configuration_events').select('id,version,source,entity,action,created_at').eq('franchise_id',p.franchise_id).order('created_at',{ascending:false}).limit(200);if(error){setMsg(error.message);return}setRows((data||[]) as LogRow[]);setMsg('')}
 return <div className="regional-home"><div className="regional-heading"><div><div className="eyebrow">Governança local</div><h1>Logs da minha operação</h1><p>O franqueado vê somente eventos vinculados à própria franquia. A Matriz mantém a auditoria global.</p></div><button className="button secondary" onClick={()=>void load()}>Atualizar</button></div>{msg&&<div className="regional-alert">{msg}</div>}<div className="table-wrap"><table className="table"><thead><tr><th>Data/Hora</th><th>Origem</th><th>Ação</th><th>Entidade</th><th>Versão</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={5} className="empty">Nenhum evento registrado.</td></tr>:rows.map(r=><tr key={r.id}><td>{new Date(r.created_at).toLocaleString('pt-BR')}</td><td>{sourceLabel[r.source]||r.source}</td><td>{r.action}</td><td>{r.entity}</td><td>v{r.version}</td></tr>)}</tbody></table></div></div>
}
