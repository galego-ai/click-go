'use client'
import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type City={id:string;name:string;state:string;active:boolean}
export default function CityManager(){
 const [rows,setRows]=useState<City[]>([]);const [name,setName]=useState('');const [state,setState]=useState('GO');const [msg,setMsg]=useState('')
 async function load(){const {data,error}=await supabase.from('cities').select('id,name,state,active').order('name');if(error){setMsg(error.message);return}setRows(data||[])}
 useEffect(()=>{load()},[])
 async function add(e:React.FormEvent){e.preventDefault();const {error}=await supabase.from('cities').insert({name,state:state.toUpperCase(),country:'BR',active:true});if(error){setMsg(error.message);return}setName('');setMsg('Cidade cadastrada.');load()}
 async function toggle(c:City){await supabase.from('cities').update({active:!c.active}).eq('id',c.id);load()}
 async function remove(id:string){if(!confirm('Excluir esta cidade?'))return;const {error}=await supabase.from('cities').delete().eq('id',id);if(error){setMsg(error.message);return}load()}
 return <><div className="card"><form onSubmit={add}><div className="form-grid"><div className="field"><label>Cidade</label><input className="input" value={name} onChange={e=>setName(e.target.value)} required/></div><div className="field"><label>UF</label><input className="input" maxLength={2} value={state} onChange={e=>setState(e.target.value)} required/></div></div><div className="toolbar" style={{marginTop:14}}><button className="button">Salvar cidade</button></div>{msg&&<p className="empty">{msg}</p>}</form></div><div className="section"><div className="table-wrap"><table className="table"><thead><tr><th>Cidade</th><th>UF</th><th>Status</th><th>Ações</th></tr></thead><tbody>{rows.length===0?<tr><td colSpan={4} className="empty">Nenhuma cidade cadastrada.</td></tr>:rows.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.state}</td><td><span className={'pill '+(c.active?'green':'red')}>{c.active?'Ativa':'Bloqueada'}</span></td><td><div className="toolbar"><button className="button secondary" onClick={()=>toggle(c)}>{c.active?'Bloquear':'Ativar'}</button><button className="button danger" onClick={()=>remove(c.id)}>Excluir</button></div></td></tr>)}</tbody></table></div></div></>
}
