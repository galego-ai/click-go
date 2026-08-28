'use client'

import {useEffect,useState} from 'react'
import {supabase} from '@/lib/supabase'

type Row={franchise_id:string;trade_name:string;legal_name:string|null;active:boolean;license_status:string;taximeter_enabled:boolean;has_override:boolean;locked_by_matrix:boolean;updated_at:string|null}
const card:React.CSSProperties={background:'#fff',border:'1px solid #e5e7eb',borderRadius:16,padding:16}
const btn:React.CSSProperties={border:0,borderRadius:10,padding:'9px 12px',fontWeight:900,cursor:'pointer'}

export default function Page(){
 const[rows,setRows]=useState<Row[]>([]),[msg,setMsg]=useState('Carregando...'),[busy,setBusy]=useState('')
 useEffect(()=>{void load()},[])
 async function load(){const{data,error}=await supabase.rpc('matrix_list_franchise_taximeter_settings');if(error){setMsg(error.message);return}setRows((Array.isArray(data)?data:[]) as Row[]);setMsg('')}
 async function setEnabled(row:Row,enabled:boolean){setBusy(row.franchise_id);const{error}=await supabase.rpc('matrix_set_franchise_taximeter_enabled',{p_franchise_id:row.franchise_id,p_enabled:enabled,p_reason:enabled?'Taxímetro liberado no app do motorista pela Matriz':'Taxímetro removido do app do motorista pela Matriz'});setBusy('');setMsg(error?error.message:(enabled?'Taxímetro liberado para a franquia.':'Taxímetro desativado para a franquia.'));if(!error)await load()}
 return <div style={{maxWidth:1100,margin:'0 auto'}}><div className="topbar compact-topbar"><div><div className="eyebrow">Matriz CLICK-GO</div><h1 className="title">Taxímetro por franquia</h1><p className="subtitle">A Matriz decide em quais franquias o taxímetro aparece e pode ser usado no app Motorista.</p></div></div>{msg&&<div style={{...card,marginBottom:14,borderColor:'#e3c600',background:'#fff9cf'}}>{msg}</div>}<div style={{display:'grid',gap:10}}>{rows.map(r=><div key={r.franchise_id} style={{...card,display:'grid',gridTemplateColumns:'minmax(0,1fr) auto',gap:14,alignItems:'center'}}><div><strong style={{fontSize:16}}>{r.trade_name}</strong><div style={{color:'#6b7280',fontSize:12,marginTop:4}}>{r.legal_name||''} · licença {r.license_status}</div><div style={{marginTop:7}}><span className={'pill '+(r.taximeter_enabled?'green':'red')}>{r.taximeter_enabled?'Taxímetro visível e liberado':'Taxímetro removido/bloqueado'}</span>{r.has_override&&<span style={{marginLeft:7,fontSize:11,color:'#6b7280'}}>regra específica da Matriz</span>}</div></div><div style={{display:'flex',gap:8}}><button disabled={busy===r.franchise_id||r.taximeter_enabled} style={{...btn,background:'#ffd400',color:'#111',opacity:r.taximeter_enabled?.45:1}} onClick={()=>void setEnabled(r,true)}>Colocar taxímetro</button><button disabled={busy===r.franchise_id||!r.taximeter_enabled} style={{...btn,background:'#111827',color:'#fff',opacity:!r.taximeter_enabled?.45:1}} onClick={()=>void setEnabled(r,false)}>Tirar taxímetro</button></div></div>)}{!rows.length&&!msg&&<div style={card}>Nenhuma franquia encontrada.</div>}</div></div>
}
