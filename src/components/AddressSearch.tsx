'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'

type Result={label:string;lat:number;lng:number;distanceKm?:number}
type Point={lat:number;lng:number}
const input:React.CSSProperties={width:'100%',background:'#fff',color:'#111827',border:'1px solid #e5e7eb',borderRadius:18,padding:'16px 18px',fontSize:16,outline:'none',boxShadow:'0 5px 18px rgba(0,0,0,.06)'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:16,padding:'14px 17px',fontWeight:900,cursor:'pointer',minWidth:86}

export default function AddressSearch({title,placeholder,onSelect}:{title:string;placeholder:string;onSelect:(r:Result)=>void}){
 const[q,setQ]=useState(''),[results,setResults]=useState<Result[]>([]),[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[near,setNear]=useState<Point|null>(null)
 const abortRef=useRef<AbortController|null>(null),chosenRef=useRef('')

 useEffect(()=>{if(!navigator.geolocation)return;navigator.geolocation.getCurrentPosition(p=>setNear({lat:p.coords.latitude,lng:p.coords.longitude}),()=>{}, {enableHighAccuracy:false,timeout:6000,maximumAge:60000})},[])

 async function runSearch(term:string){
  if(term.length<3)return
  abortRef.current?.abort();const controller=new AbortController();abortRef.current=controller
  setBusy(true);setMsg(near?'Buscando primeiro os endereços mais próximos...':'Buscando endereços...')
  try{
   const params=new URLSearchParams({q:term});if(near){params.set('lat',String(near.lat));params.set('lng',String(near.lng))}
   const res=await fetch(`/api/geocode?${params.toString()}`,{signal:controller.signal})
   const body=await res.json();if(!res.ok)throw new Error(body.error||'Erro ao buscar endereço.')
   setResults(body.results||[]);setMsg((body.results||[]).length?(near?'Resultados ordenados por proximidade. Toque no endereço correto.':'Toque no endereço correto.'):'Nenhum endereço encontrado. Tente incluir cidade e estado.')
  }catch(e:any){if(e?.name!=='AbortError')setMsg(e.message||'Não foi possível pesquisar.')}
  finally{if(abortRef.current===controller)setBusy(false)}
 }

 useEffect(()=>{const term=q.trim();if(chosenRef.current===term){chosenRef.current='';return}if(term.length<3){abortRef.current?.abort();setBusy(false);setResults([]);setMsg(term.length?`Digite mais ${3-term.length} caractere${3-term.length===1?'':'s'}.`:'');return}const timer=window.setTimeout(()=>runSearch(term),350);return()=>window.clearTimeout(timer)},[q,near?.lat,near?.lng])
 useEffect(()=>()=>abortRef.current?.abort(),[])

 async function search(e:FormEvent){e.preventDefault();const term=q.trim();if(term.length<3){setMsg('Digite pelo menos 3 caracteres ou dígitos.');return}await runSearch(term)}
 function choose(r:Result){abortRef.current?.abort();chosenRef.current=r.label;onSelect(r);setQ(r.label);setResults([]);setBusy(false);setMsg('Endereço selecionado.')}

 return <div style={{display:'grid',gap:8}}>
  <b style={{color:'#111827',fontSize:14}}>{title}</b>
  <form onSubmit={search} style={{display:'grid',gridTemplateColumns:'minmax(0,1fr) auto',gap:8}}>
   <input value={q} onChange={e=>setQ(e.target.value)} placeholder={placeholder} style={input} autoComplete="off" inputMode="search"/>
   <button disabled={busy||q.trim().length<3} style={{...btn,opacity:busy||q.trim().length<3?.55:1}}>{busy?'...':'🔎'}</button>
  </form>
  {near&&<div style={{fontSize:11,color:'#6b7280'}}>📍 Busca aproximada pela sua localização atual.</div>}
  {results.length>0&&<div style={{display:'grid',gap:7,background:'#fff',border:'1px solid #e5e7eb',borderRadius:18,padding:8,boxShadow:'0 12px 35px rgba(0,0,0,.12)',position:'relative',zIndex:20}}>{results.map((r,i)=><button type="button" key={`${r.lat}-${r.lng}-${i}`} onClick={()=>choose(r)} style={{textAlign:'left',background:'#f9fafb',color:'#111827',border:'1px solid #eef0f2',borderRadius:14,padding:'13px 14px',cursor:'pointer',fontSize:14,lineHeight:1.35}}>📍 {r.label}{r.distanceKm!=null?<span style={{display:'block',fontSize:11,color:'#6b7280',marginTop:3}}>aprox. {r.distanceKm.toFixed(1)} km</span>:null}</button>)}</div>}
  {msg&&<div style={{fontSize:12,color:'#6b7280'}}>{msg}</div>}
 </div>
}
