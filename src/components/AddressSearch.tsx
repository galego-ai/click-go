'use client'

import { FormEvent, useState } from 'react'

type Result={label:string;lat:number;lng:number}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 13px',fontWeight:800,cursor:'pointer'}

export default function AddressSearch({title,placeholder,onSelect}:{title:string;placeholder:string;onSelect:(r:Result)=>void}){
 const[q,setQ]=useState(''),[results,setResults]=useState<Result[]>([]),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 async function search(e:FormEvent){e.preventDefault();if(q.trim().length<3){setMsg('Digite pelo menos 3 caracteres.');return}setBusy(true);setMsg('');setResults([]);try{const res=await fetch(`/api/geocode?q=${encodeURIComponent(q.trim())}`);const body=await res.json();if(!res.ok)throw new Error(body.error||'Erro ao buscar endereço.');setResults(body.results||[]);if(!(body.results||[]).length)setMsg('Nenhum endereço encontrado. Tente incluir cidade e estado.')}catch(e:any){setMsg(e.message||'Não foi possível pesquisar.')}finally{setBusy(false)}}
 function choose(r:Result){onSelect(r);setQ(r.label);setResults([]);setMsg('Endereço selecionado.')}
 return <div style={{display:'grid',gap:7}}><b>{title}</b><form onSubmit={search} style={{display:'grid',gridTemplateColumns:'1fr auto',gap:7}}><input value={q} onChange={e=>setQ(e.target.value)} placeholder={placeholder} style={input}/><button disabled={busy} style={btn}>{busy?'Buscando...':'Buscar'}</button></form>{results.length>0&&<div style={{display:'grid',gap:6,background:'#0c0c0c',border:'1px solid #292929',borderRadius:12,padding:7}}>{results.map((r,i)=><button type="button" key={`${r.lat}-${r.lng}-${i}`} onClick={()=>choose(r)} style={{textAlign:'left',background:'#171717',color:'#fff',border:'1px solid #292929',borderRadius:9,padding:'10px',cursor:'pointer'}}>{r.label}</button>)}</div>}{msg&&<div style={{fontSize:12,color:'#fde68a'}}>{msg}</div>}<div style={{fontSize:11,color:'#6b7280'}}>Busca de endereço © OpenStreetMap contributors</div></div>
}
