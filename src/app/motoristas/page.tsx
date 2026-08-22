'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type DriverRow = { id:string; status:string; city_id:string|null; online:boolean; name?:string; city?:string }

export default function Page(){
  const [rows,setRows]=useState<DriverRow[]>([])
  const [loading,setLoading]=useState(true)
  const [message,setMessage]=useState('')

  async function load(){
    setLoading(true)
    const {data:drivers,error}=await supabase.from('drivers').select('id,status,city_id,online').order('created_at',{ascending:false})
    if(error){setMessage(error.message);setLoading(false);return}
    const ids=(drivers||[]).map(d=>d.id)
    const cityIds=[...new Set((drivers||[]).map(d=>d.city_id).filter(Boolean))] as string[]
    const [{data:profiles},{data:cities}]=await Promise.all([
      ids.length?supabase.from('profiles').select('id,full_name').in('id',ids):Promise.resolve({data:[] as any[]}),
      cityIds.length?supabase.from('cities').select('id,name,state').in('id',cityIds):Promise.resolve({data:[] as any[]})
    ])
    const pMap=new Map((profiles||[]).map((p:any)=>[p.id,p.full_name]))
    const cMap=new Map((cities||[]).map((c:any)=>[c.id,`${c.name} - ${c.state}`]))
    setRows((drivers||[]).map((d:any)=>({...d,name:pMap.get(d.id)||'Motorista',city:d.city_id?cMap.get(d.city_id)||'Cidade cadastrada':'Sem cidade'})))
    setLoading(false)
  }

  useEffect(()=>{load()},[])

  async function setStatus(id:string,status:'approved'|'rejected'){
    setMessage('')
    const {data:{user}}=await supabase.auth.getUser()
    const payload:any={status,online:false}
    if(status==='approved'){payload.approved_at=new Date().toISOString();payload.approved_by=user?.id||null;payload.rejection_reason=null}
    else{payload.rejection_reason=window.prompt('Motivo da rejeição:')||'Cadastro rejeitado pelo franqueado';payload.approved_at=null;payload.approved_by=null}
    const {error}=await supabase.from('drivers').update(payload).eq('id',id)
    if(error)setMessage(error.message);else{setMessage(status==='approved'?'Motorista aprovado com sucesso.':'Cadastro rejeitado.');await load()}
  }

  return <><div className="topbar"><div><div className="eyebrow">Operação</div><h1 className="title">Motoristas</h1><p className="subtitle">O franqueado visualiza e valida os motoristas vinculados à sua cidade/franquia.</p></div></div>
  {message&&<div className="card" style={{marginBottom:14}}>{message}</div>}
  <table className="table"><thead><tr><th>Motorista</th><th>Cidade</th><th>Status</th><th>Online</th><th>Ações</th></tr></thead><tbody>{loading?<tr><td colSpan={5} className="empty">Carregando...</td></tr>:rows.length===0?<tr><td colSpan={5} className="empty">Nenhum motorista cadastrado.</td></tr>:rows.map(r=><tr key={r.id}><td>{r.name}</td><td>{r.city}</td><td><span className="pill">{r.status}</span></td><td>{r.online?'Sim':'Não'}</td><td>{r.status==='pending'?<div style={{display:'flex',gap:8}}><button className="button" onClick={()=>setStatus(r.id,'approved')}>Aprovar</button><button onClick={()=>setStatus(r.id,'rejected')} style={{background:'#2a2a2a',color:'#fff',border:'1px solid #444',borderRadius:10,padding:'10px 12px',cursor:'pointer'}}>Rejeitar</button></div>:'—'}</td></tr>)}</tbody></table></>
}
