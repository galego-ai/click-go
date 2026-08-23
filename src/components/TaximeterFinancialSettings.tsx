'use client'

import { useEffect,useState } from 'react'
import { supabase } from '@/lib/supabase'

type Settings={
 target_franchise_id:string|null
 global_fee_mode:'none'|'fixed'|'percentage'
 global_fee_value:number|string
 allow_franchise_override:boolean
 override_exists:boolean
 override_fee_mode:'none'|'fixed'|'percentage'|null
 override_fee_value:number|string|null
 override_locked_by_matrix:boolean
 effective_fee_mode:'none'|'fixed'|'percentage'
 effective_fee_value:number|string
 effective_source:'global'|'franchise'
 can_edit:boolean
}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:16}
const input:React.CSSProperties={background:'#0b0b0b',color:'#fff',border:'1px solid #333',borderRadius:9,padding:'10px 11px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:9,padding:'10px 14px',fontWeight:900,cursor:'pointer'}
const money=(v:any)=>Number(v||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const rule=(mode:string,value:any)=>mode==='none'?'Sem taxa':mode==='percentage'?`${Number(value||0).toFixed(2)}% por corrida`:`${money(value)} por corrida`

export default function TaximeterFinancialSettings({network=false}:{network?:boolean}){
 const[data,setData]=useState<Settings|null>(null),[mode,setMode]=useState<'none'|'fixed'|'percentage'>('none'),[value,setValue]=useState('0'),[allow,setAllow]=useState(true),[busy,setBusy]=useState(false),[msg,setMsg]=useState('')
 useEffect(()=>{void load()},[])
 async function load(){
  setBusy(true);setMsg('')
  const{data:d,error}=await supabase.rpc('get_taximeter_financial_settings',{p_franchise_id:null})
  setBusy(false)
  if(error){setMsg(error.message);return}
  const s=d as Settings;setData(s)
  if(network){setMode(s.global_fee_mode||'none');setValue(String(s.global_fee_value||0));setAllow(s.allow_franchise_override!==false)}
  else{setMode((s.override_exists?s.override_fee_mode:s.effective_fee_mode)||'none');setValue(String(s.override_exists?s.override_fee_value:s.effective_fee_value||0));setAllow(s.allow_franchise_override!==false)}
 }
 async function save(){
  if(!network&&!data?.can_edit){setMsg('A matriz bloqueou alterações desta configuração.');return}
  const numeric=mode==='none'?0:Number(String(value).replace(',','.'))
  if(!Number.isFinite(numeric)||numeric<0){setMsg('Informe um valor válido.');return}
  if(mode==='percentage'&&numeric>100){setMsg('O percentual deve ficar entre 0 e 100%.');return}
  setBusy(true);setMsg('Salvando configuração...')
  const{error}=await supabase.rpc('set_taximeter_financial_settings',{
   p_fee_mode:mode,p_fee_value:numeric,p_scope:network?'global':'franchise',p_franchise_id:null,p_allow_franchise_override:network?allow:true,p_locked_by_matrix:false
  })
  setBusy(false)
  if(error){setMsg(error.message);return}
  setMsg(network?'Regra financeira da matriz atualizada.':'Regra financeira da franquia atualizada.')
  await load()
 }
 if(!data&&busy)return <div style={box}>Carregando configuração financeira do taxímetro…</div>
 const disabled=busy||(!network&&!data?.can_edit)
 return <section style={{...box,borderColor:'#574900',marginBottom:14}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'start',flexWrap:'wrap'}}><div><div style={{fontSize:12,fontWeight:950,color:'#ffd400'}}>FINANCEIRO DO TAXÍMETRO</div><h2 style={{margin:'4px 0 0'}}>Taxa das corridas livres</h2><p style={{color:'#9ca3af',fontSize:13,margin:'6px 0 0'}}>{network?'Defina a regra padrão da rede. Começa sem cobrança e só passa a descontar depois que você configurar.':'A taxa é descontada da carteira operacional quando houver saldo; sem saldo, vira pendência e não bloqueia a corrida.'}</p></div><div style={{padding:'8px 12px',border:'1px solid #333',borderRadius:12,fontWeight:900,color:'#ffd400'}}>Efetiva: {rule(data?.effective_fee_mode||'none',data?.effective_fee_value||0)}</div></div>
  <div style={{display:'grid',gridTemplateColumns:'minmax(190px,1fr) minmax(150px,220px) auto',gap:10,alignItems:'end',marginTop:14}}>
   <label style={{display:'grid',gap:5,fontSize:12,color:'#9ca3af'}}>Modelo<select disabled={disabled} value={mode} onChange={e=>setMode(e.target.value as any)} style={input}><option value="none">Sem taxa</option><option value="fixed">Valor fixo por corrida</option><option value="percentage">Percentual da corrida</option></select></label>
   <label style={{display:'grid',gap:5,fontSize:12,color:'#9ca3af'}}>{mode==='percentage'?'Percentual (%)':'Valor (R$)'}<input disabled={disabled||mode==='none'} value={value} onChange={e=>setValue(e.target.value)} inputMode="decimal" style={input}/></label>
   <button disabled={disabled} onClick={save} style={{...btn,opacity:disabled?.55:1}}>{busy?'Salvando…':'Salvar regra'}</button>
  </div>
  {network?<label style={{display:'flex',alignItems:'center',gap:9,marginTop:12,fontSize:13,color:'#d1d5db'}}><input type="checkbox" checked={allow} onChange={e=>setAllow(e.target.checked)}/><span>Permitir que cada franqueado defina sua própria taxa do taxímetro. Se desmarcado, prevalece a regra da matriz.</span></label>:<div style={{marginTop:12,fontSize:12,color:data?.can_edit?'#9ca3af':'#fbbf24'}}>{data?.effective_source==='franchise'?'A franquia está usando uma regra própria.':'A franquia está herdando a regra da matriz.'} {!data?.can_edit&&' A matriz bloqueou alterações locais.'}</div>}
  {msg&&<div style={{marginTop:10,fontSize:12,color:'#ffe66b'}}>{msg}</div>}
 </section>
}
