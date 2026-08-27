'use client'

import Link from 'next/link'
import {useEffect,useMemo,useState} from 'react'
import {supabase} from '@/lib/supabase'

type Row={driver_id:string;driver_name:string;driver_status:string;vehicle_id:string|null;vehicle_make:string|null;vehicle_model:string|null;vehicle_plate:string|null;vehicle_type:string|null;category_id:string;category_name:string;required_vehicle_type:string|null;category_active:boolean;assigned:boolean}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 14px',fontWeight:800,cursor:'pointer',textDecoration:'none'}

function technicalType(value:string|null){return value==='motorcycle'?'Moto':value==='car'?'Automóvel':'Não definido'}

export default function MotoristasCategoriasPage(){
 const[rows,setRows]=useState<Row[]>([]),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{load()},[])
 async function load(){setBusy(true);setMsg('');try{const{data,error}=await supabase.rpc('franchise_driver_category_matrix');if(error)throw error;setRows((data||[]) as Row[])}catch(e:any){setMsg(e.message||'Não foi possível carregar motoristas e categorias.')}finally{setBusy(false)}}
 const groups=useMemo(()=>{const m=new Map<string,Row[]>();for(const r of rows){const a=m.get(r.driver_id)||[];a.push(r);m.set(r.driver_id,a)}return [...m.entries()]},[rows])
 async function setCategory(r:Row,enabled:boolean){setBusy(true);setMsg('');try{const{error}=await supabase.rpc('franchise_set_driver_category',{p_driver_id:r.driver_id,p_category_id:r.category_id,p_enabled:enabled});if(error)throw error;setMsg(enabled?'Categoria associada ao motorista.':'Categoria removida do motorista.');await load()}catch(e:any){setMsg(e.message||'Erro ao atualizar categoria.')}finally{setBusy(false)}}
 return <main style={{minHeight:'100vh',background:'#080808',color:'#fff',padding:24}}><div style={{maxWidth:1100,margin:'0 auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap',marginBottom:20}}><div><div style={{color:'#ffd400',fontWeight:900}}>CLICK-GO</div><h1 style={{margin:'6px 0'}}>Categorias por motorista</h1><p style={{color:'#9ca3af',margin:0}}>Habilite todas as categorias que cada motorista pode atender. A lista vem das categorias configuradas para a cidade, como Econômico, Conforto, Premium, Moto, SUV, Executivo, Van e outras criadas pela operação.</p></div><div style={{display:'flex',gap:8}}><Link href="/franqueado/categorias" style={btn}>Categorias e preços</Link><Link href="/franqueado" style={{...btn,background:'#292929',color:'#fff'}}>Painel</Link></div></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:15}}>{msg}</div>}
  {busy&&!rows.length&&<div style={box}>Carregando...</div>}
  <div style={{display:'grid',gap:14}}>{groups.map(([driverId,list])=>{const d=list[0];const type=d.vehicle_type||'';return <section key={driverId} style={box}><div style={{display:'grid',gridTemplateColumns:'1.4fr .8fr',gap:16,alignItems:'start'}}><div><h2 style={{margin:'0 0 5px'}}>{d.driver_name}</h2><div style={{color:'#9ca3af'}}>{d.driver_status} · {[d.vehicle_make,d.vehicle_model,d.vehicle_plate].filter(Boolean).join(' · ')||'Sem veículo ativo'}</div></div><div style={{...box,padding:12}}><div style={{fontSize:12,color:'#9ca3af'}}>Tipo técnico do veículo</div><b>{technicalType(type)}</b><div style={{fontSize:11,color:'#777',marginTop:4}}>Usado somente para compatibilidade interna. As categorias abaixo definem quais corridas o motorista recebe.</div></div></div><div style={{height:1,background:'#292929',margin:'16px 0'}}/><div style={{fontWeight:800,marginBottom:4}}>Categorias disponíveis para este motorista</div><div style={{fontSize:12,color:'#9ca3af',marginBottom:10}}>Marque uma ou várias categorias permitidas pela operação.</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(210px,1fr))',gap:9}}>{list.map(r=>{const compatible=!r.required_vehicle_type||r.required_vehicle_type===type;return <label key={r.category_id} style={{display:'flex',gap:10,alignItems:'center',padding:12,border:r.assigned?'1px solid #ffd400':'1px solid #333',borderRadius:12,opacity:r.category_active&&compatible?1:.5,background:r.assigned?'#1d1a00':'transparent'}}><input type="checkbox" checked={!!r.assigned} disabled={busy||!r.category_active||!compatible||!d.vehicle_id} onChange={e=>setCategory(r,e.target.checked)}/><span><b>{r.category_name}</b><small style={{display:'block',color:'#9ca3af'}}>{!r.category_active?'Desativada pela operação':!compatible?`Incompatível com ${technicalType(type)}`:'Disponível'}</small></span></label>})}</div></section>})}{!busy&&!groups.length&&<div style={box}>Nenhum motorista cadastrado nesta franquia.</div>}</div>
 </div></main>
}
