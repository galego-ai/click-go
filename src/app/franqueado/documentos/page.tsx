'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { supabase } from '@/lib/supabase'

type Doc={id:string;driver_id:string;document_type:string;file_path:string;status:string;rejection_reason:string|null;created_at:string}
type Profile={id:string;full_name:string|null;email:string|null;phone:string|null}
type Driver={id:string;status:string;franchise_id:string|null}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 13px',fontWeight:800,cursor:'pointer'}

export default function DriverDocumentsPage(){
 const [docs,setDocs]=useState<Doc[]>([]),[profiles,setProfiles]=useState<Profile[]>([]),[drivers,setDrivers]=useState<Driver[]>([]),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 const names=useMemo(()=>Object.fromEntries(profiles.map(p=>[p.id,p])),[profiles])
 useEffect(()=>{load()},[])
 async function load(){setBusy(true);setMsg('');try{
  const {data:{user}}=await supabase.auth.getUser(); if(!user) throw new Error('Faça login como franqueado.')
  const {data:me,error:meErr}=await supabase.from('profiles').select('id,role,franchise_id').eq('id',user.id).single(); if(meErr)throw meErr
  if(!me||me.role!=='franchise_admin'||!me.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
  const {data:d,error:dErr}=await supabase.from('drivers').select('id,status,franchise_id').eq('franchise_id',me.franchise_id); if(dErr)throw dErr
  const ids=(d||[]).map((x:any)=>x.id); setDrivers((d||[]) as Driver[])
  if(!ids.length){setDocs([]);setProfiles([]);return}
  const [{data:documents,error:docErr},{data:people,error:pErr}]=await Promise.all([
   supabase.from('driver_documents').select('id,driver_id,document_type,file_path,status,rejection_reason,created_at').in('driver_id',ids).order('created_at',{ascending:false}),
   supabase.from('profiles').select('id,full_name,email,phone').in('id',ids)
  ])
  if(docErr)throw docErr;if(pErr)throw pErr;setDocs((documents||[]) as Doc[]);setProfiles((people||[]) as Profile[])
 }catch(e:any){setMsg(e.message||'Erro ao carregar documentos.')}finally{setBusy(false)}}
 async function openDoc(doc:Doc){setMsg('');const {data,error}=await supabase.storage.from('driver-documents').createSignedUrl(doc.file_path,300);if(error){setMsg(error.message);return}window.open(data.signedUrl,'_blank','noopener,noreferrer')}
 async function review(doc:Doc,approved:boolean){setBusy(true);setMsg('');let reason:string|null=null;if(!approved){reason=window.prompt('Motivo da reprovação:')||'Documento reprovado pelo franqueado'}const {data:{user}}=await supabase.auth.getUser();const {error}=await supabase.from('driver_documents').update({status:approved?'approved':'rejected',rejection_reason:approved?null:reason,reviewed_by:user?.id||null,reviewed_at:new Date().toISOString()}).eq('id',doc.id);setMsg(error?error.message:(approved?'Documento aprovado.':'Documento reprovado.'));if(!error)await load();setBusy(false)}
 return <main style={{minHeight:'100vh',background:'#080808',color:'#f8fafc',padding:28}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'center',marginBottom:22}}><div><div style={{color:'#ffd400',fontWeight:800,fontSize:12,textTransform:'uppercase'}}>Central do Franqueado</div><h1 style={{margin:'5px 0'}}>Documentos dos motoristas</h1><p style={{color:'#9ca3af',margin:0}}>Analise CNH, CRLV e demais arquivos antes de liberar o motorista.</p></div><div style={{display:'flex',gap:8}}><Link href="/franqueado" style={{...btn,textDecoration:'none'}}>Voltar ao painel</Link><button style={btn} onClick={load}>{busy?'Atualizando...':'Atualizar'}</button></div></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:16}}>{msg}</div>}
  <div style={{display:'grid',gap:12}}>{docs.map(doc=>{const p=names[doc.driver_id];return <div key={doc.id} style={{...box,display:'grid',gridTemplateColumns:'2fr 1.2fr 1fr auto',gap:14,alignItems:'center'}}><div><b>{p?.full_name||'Motorista'}</b><div style={{color:'#9ca3af',fontSize:13}}>{p?.phone||p?.email||doc.driver_id}</div></div><div><div style={{fontWeight:700}}>{doc.document_type}</div><div style={{color:'#9ca3af',fontSize:12}}>{new Date(doc.created_at).toLocaleString('pt-BR')}</div></div><div><span style={{padding:'5px 9px',borderRadius:999,background:'#222'}}>{doc.status}</span>{doc.rejection_reason&&<div style={{color:'#fca5a5',fontSize:12,marginTop:6}}>{doc.rejection_reason}</div>}</div><div style={{display:'flex',gap:7,flexWrap:'wrap'}}><button style={{...btn,background:'#252525',color:'#fff'}} onClick={()=>openDoc(doc)}>Ver arquivo</button>{doc.status==='pending'&&<><button style={btn} onClick={()=>review(doc,true)}>Aprovar</button><button style={{...btn,background:'#3a1b1b',color:'#fff'}} onClick={()=>review(doc,false)}>Reprovar</button></>}</div></div>})}{!docs.length&&<div style={box}>Nenhum documento enviado pelos motoristas desta franquia.</div>}</div>
 </main>
}
