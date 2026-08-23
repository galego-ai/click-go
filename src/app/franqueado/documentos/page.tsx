'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { supabase } from '@/lib/supabase'

type Doc={id:string;driver_id:string;document_type:string;file_path:string;status:string;rejection_reason:string|null;created_at:string}
type Profile={id:string;full_name:string|null;email:string|null;phone:string|null;avatar_url:string|null}
type Driver={id:string;status:string;franchise_id:string|null;approved_at:string|null;rejection_reason:string|null}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 13px',fontWeight:800,cursor:'pointer'}

export default function DriverDocumentsPage(){
 const[docs,setDocs]=useState<Doc[]>([]),[profiles,setProfiles]=useState<Profile[]>([]),[drivers,setDrivers]=useState<Driver[]>([]),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 const names=useMemo(()=>Object.fromEntries(profiles.map(p=>[p.id,p])),[profiles])
 const docsByDriver=useMemo(()=>{const m:Record<string,Doc[]>={};docs.forEach(d=>{m[d.driver_id]=[...(m[d.driver_id]||[]),d]});return m},[docs])
 useEffect(()=>{load()},[])
 async function load(){setBusy(true);setMsg('');try{
  const{data:{user}}=await supabase.auth.getUser();if(!user)throw new Error('Faça login como franqueado.')
  const{data:me,error:meErr}=await supabase.from('profiles').select('id,role,franchise_id').eq('id',user.id).single();if(meErr)throw meErr
  if(!me||me.role!=='franchise_admin'||!me.franchise_id)throw new Error('Acesso exclusivo do franqueado.')
  const{data:d,error:dErr}=await supabase.from('drivers').select('id,status,franchise_id,approved_at,rejection_reason').eq('franchise_id',me.franchise_id).order('created_at',{ascending:false});if(dErr)throw dErr
  const ids=(d||[]).map((x:any)=>x.id);setDrivers((d||[]) as Driver[])
  if(!ids.length){setDocs([]);setProfiles([]);return}
  const[{data:documents,error:docErr},{data:people,error:pErr}]=await Promise.all([
   supabase.from('driver_documents').select('id,driver_id,document_type,file_path,status,rejection_reason,created_at').in('driver_id',ids).order('created_at',{ascending:false}),
   supabase.from('profiles').select('id,full_name,email,phone,avatar_url').in('id',ids)
  ])
  if(docErr)throw docErr;if(pErr)throw pErr;setDocs((documents||[]) as Doc[]);setProfiles((people||[]) as Profile[])
 }catch(e:any){setMsg(e.message||'Erro ao carregar motoristas.')}finally{setBusy(false)}}
 async function openDoc(doc:Doc){setMsg('');const{data,error}=await supabase.storage.from('driver-documents').createSignedUrl(doc.file_path,300);if(error){setMsg(error.message);return}window.open(data.signedUrl,'_blank','noopener,noreferrer')}
 async function review(doc:Doc,approved:boolean){setBusy(true);setMsg('');let reason:string|null=null;if(!approved){reason=window.prompt('Motivo da reprovação:')||'Documento reprovado pelo franqueado'}const{data:{user}}=await supabase.auth.getUser();const{error}=await supabase.from('driver_documents').update({status:approved?'approved':'rejected',rejection_reason:approved?null:reason,reviewed_by:user?.id||null,reviewed_at:new Date().toISOString()}).eq('id',doc.id);setMsg(error?error.message:(approved?(doc.document_type==='profile_photo'?'Foto real conferida e aprovada.':'Documento aprovado.'):'Documento reprovado.'));if(!error)await load();setBusy(false)}
 async function decideDriver(driver:Driver,approved:boolean){
  setMsg('');const p=names[driver.id];const list=docsByDriver[driver.id]||[];const photoApproved=list.some(d=>d.document_type==='profile_photo'&&d.status==='approved')
  if(approved){if(!p?.avatar_url){setMsg('A foto de perfil real é obrigatória antes da aprovação.');return}if(!list.length){setMsg('Este motorista ainda não enviou documentos.');return}if(!photoApproved){setMsg('Confira e aprove primeiro o documento “profile_photo” para confirmar a foto real do motorista.');return}if(list.some(d=>d.status!=='approved')){setMsg('Todos os documentos precisam estar aprovados antes da liberação.');return}}
  let reason:string|null=null;if(!approved){reason=window.prompt('Motivo da reprovação do motorista:')||'Cadastro reprovado pelo franqueado'}
  if(!confirm(approved?'Liberar este motorista para operar na franquia?':'Reprovar este motorista?'))return
  setBusy(true);const{error}=await supabase.rpc('franchise_review_driver',{p_driver_id:driver.id,p_approve:approved,p_reason:reason});setBusy(false);setMsg(error?error.message:(approved?'Motorista aprovado e liberado para operar.':'Motorista reprovado.'));if(!error)await load()
 }
 return <main style={{minHeight:'100vh',background:'#080808',color:'#f8fafc',padding:28}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'center',marginBottom:22}}><div><div style={{color:'#ffd400',fontWeight:800,fontSize:12,textTransform:'uppercase'}}>Central do Franqueado</div><h1 style={{margin:'5px 0'}}>Aprovação de motoristas</h1><p style={{color:'#9ca3af',margin:0}}>Confira a foto real do perfil, aprove a foto como documento, analise os demais documentos e só então libere o motorista.</p></div><div style={{display:'flex',gap:8}}><Link href="/franqueado" style={{...btn,textDecoration:'none'}}>Voltar ao painel</Link><button style={btn} onClick={load}>{busy?'Atualizando...':'Atualizar'}</button></div></div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:16}}>{msg}</div>}
  <div style={{display:'grid',gap:16}}>{drivers.map(driver=>{const p=names[driver.id];const list=docsByDriver[driver.id]||[];const allApproved=list.length>0&&list.every(d=>d.status==='approved');const photoApproved=list.some(d=>d.document_type==='profile_photo'&&d.status==='approved');const canApprove=!!p?.avatar_url&&photoApproved&&allApproved;return <section key={driver.id} style={{...box,borderColor:driver.status==='approved'?'#176b45':driver.status==='rejected'?'#6b1f1f':'#4b4b22'}}>
   <div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'flex-start',flexWrap:'wrap'}}><div style={{display:'flex',gap:14,alignItems:'center'}}>{p?.avatar_url?<img src={p.avatar_url} alt="Foto real do motorista" style={{width:78,height:78,borderRadius:'50%',objectFit:'cover',border:'3px solid #ffd400'}}/>:<div style={{width:78,height:78,borderRadius:'50%',display:'grid',placeItems:'center',background:'#2a1717',border:'2px solid #7f1d1d',color:'#fca5a5',fontSize:11,textAlign:'center',padding:6}}>FOTO OBRIGATÓRIA AUSENTE</div>}<div><h3 style={{margin:'0 0 4px'}}>{p?.full_name||'Motorista'}</h3><div style={{color:'#9ca3af',fontSize:13}}>{p?.phone||p?.email||driver.id}</div><div style={{marginTop:8}}>Status: <b>{driver.status}</b>{driver.rejection_reason&&<span style={{color:'#fca5a5'}}> · {driver.rejection_reason}</span>}</div></div></div><div style={{display:'flex',gap:8,flexWrap:'wrap'}}>{driver.status!=='approved'&&<button style={{...btn,opacity:canApprove?1:.55}} onClick={()=>decideDriver(driver,true)}>Aprovar motorista</button>}<button style={{...btn,background:'#3a1b1b',color:'#fff'}} onClick={()=>decideDriver(driver,false)}>Reprovar motorista</button></div></div>
   <div style={{marginTop:12,color:canApprove?'#86efac':'#fde68a',fontSize:13}}>{p?.avatar_url?'✓ Foto presente':'• Falta foto de perfil'} · {photoApproved?'✓ Foto real conferida pelo franqueado':'• Foto real ainda não aprovada'} · {allApproved?'✓ Documentos aprovados':'• Existem documentos pendentes/reprovados'}</div>
   <div style={{marginTop:14,display:'grid',gap:8}}>{list.length?list.map(doc=><div key={doc.id} style={{background:'#0d0d0d',border:doc.document_type==='profile_photo'?'2px solid #665600':'1px solid #272727',borderRadius:12,padding:12,display:'grid',gridTemplateColumns:'1.4fr 1fr auto',gap:12,alignItems:'center'}}><div><b>{doc.document_type==='profile_photo'?'📷 Foto real de perfil':doc.document_type}</b><div style={{color:'#9ca3af',fontSize:12}}>{new Date(doc.created_at).toLocaleString('pt-BR')}</div></div><div><span style={{padding:'5px 9px',borderRadius:999,background:'#222'}}>{doc.status}</span>{doc.rejection_reason&&<div style={{color:'#fca5a5',fontSize:12,marginTop:6}}>{doc.rejection_reason}</div>}</div><div style={{display:'flex',gap:7,flexWrap:'wrap'}}><button style={{...btn,background:'#252525',color:'#fff'}} onClick={()=>openDoc(doc)}>Ver</button>{doc.status==='pending'&&<><button style={btn} onClick={()=>review(doc,true)}>{doc.document_type==='profile_photo'?'Aprovar foto real':'Aprovar documento'}</button><button style={{...btn,background:'#3a1b1b',color:'#fff'}} onClick={()=>review(doc,false)}>Reprovar</button></>}</div></div>):<div style={{color:'#9ca3af'}}>Nenhum documento enviado ainda.</div>}</div>
  </section>})}{!drivers.length&&<div style={box}>Nenhum motorista cadastrado nesta franquia.</div>}</div>
 </main>
}
