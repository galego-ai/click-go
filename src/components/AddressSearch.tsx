'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'

type Result={label:string;lat:number;lng:number}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 13px',fontWeight:800,cursor:'pointer'}

export default function AddressSearch({title,placeholder,onSelect}:{title:string;placeholder:string;onSelect:(r:Result)=>void}){
 const[q,setQ]=useState(''),[results,setResults]=useState<Result[]>([]),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 const abortRef=useRef<AbortController|null>(null),chosenRef=useRef('')

 async function runSearch(term:string){
  if(term.length<3)return
  abortRef.current?.abort();const controller=new AbortController();abortRef.current=controller
  setBusy(true);setMsg('Buscando endereços...')
  try{
   const res=await fetch(`/api/geocode?q=${encodeURIComponent(term)}`,{signal:controller.signal})
   const body=await res.json();if(!res.ok)throw new Error(body.error||'Erro ao buscar endereço.')
   setResults(body.results||[]);setMsg((body.results||[]).length?'Selecione um dos endereços encontrados.':'Nenhum endereço encontrado. Tente incluir cidade e estado.')
  }catch(e:any){if(e?.name!=='AbortError')setMsg(e.message||'Não foi possível pesquisar.')}
  finally{if(abortRef.current===controller)setBusy(false)}
 }

 useEffect(()=>{
  const term=q.trim()
  if(chosenRef.current===term){chosenRef.current='';return}
  if(term.length<3){abortRef.current?.abort();setBusy(false);setResults([]);setMsg(term.length?`Digite mais ${3-term.length} caractere${3-term.length===1?'':'s'} para pesquisar.`:'');return}
  const timer=window.setTimeout(()=>runSearch(term),550)
  return()=>window.clearTimeout(timer)
 },[q])
 useEffect(()=>()=>abortRef.current?.abort(),[])

 async function search(e:FormEvent){e.preventDefault();const term=q.trim();if(term.length<3){setMsg('Digite pelo menos 3 caracteres.');return}await runSearch(term)}
 function choose(r:Result){abortRef.current?.abort();chosenRef.current=r.label;onSelect(r);setQ(r.label);setResults([]);setBusy(false);setMsg('Endereço selecionado.')}
 return <div style={{display:'grid',gap:7}}><b>{title}</b><form onSubmit={search} style={{display:'grid',gridTemplateColumns:'1fr auto',gap:7}}><input value={q} onChange={e=>setQ(e.target.value)} placeholder={placeholder} style={input} autoComplete="off"/><button disabled={busy||q.trim().length<3} style={btn}>{busy?'Buscando...':'Buscar'}</button></form>{results.length>0&&<div style={{display:'grid',gap:6,background:'#0c0c0c',border:'1px solid #292929',borderRadius:12,padding:7}}>{results.map((r,i)=><button type="button" key={`${r.lat}-${r.lng}-${i}`} onClick={()=>choose(r)} style={{textAlign:'left',background:'#171717',color:'#fff',border:'1px solid #292929',borderRadius:9,padding:'10px',cursor:'pointer'}}>{r.label}</button>)}</div>}{msg&&<div style={{fontSize:12,color:'#fde68a'}}>{msg}</div>}<div style={{fontSize:11,color:'#6b7280'}}>Digite 3 letras ou mais · Busca de endereço © OpenStreetMap contributors</div></div>
}
