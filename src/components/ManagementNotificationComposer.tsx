'use client'

import {useEffect,useMemo,useState} from 'react'
import type {CSSProperties} from 'react'
import {supabase} from '@/lib/supabase'

type TargetApp='driver'|'passenger'|'both'
type SendMode='all'|'selected'
type Recipient={
  user_id:string
  full_name:string
  app_kind:'driver'|'passenger'
  city_name:string|null
  city_state:string|null
  has_active_device:boolean
}
type Campaign={
  id:string
  target_app:TargetApp
  selection_mode:SendMode
  title:string
  body:string
  recipient_count:number
  scope:'matrix'|'franchise'
  created_at:string
}

const card:CSSProperties={background:'#fff',border:'1px solid #e3e3e3',borderRadius:16,padding:18,boxShadow:'0 4px 18px rgba(0,0,0,.035)'}
const label:CSSProperties={display:'block',fontSize:12,fontWeight:800,color:'#555',marginBottom:6}
const input:CSSProperties={width:'100%',border:'1px solid #d7d7d7',borderRadius:10,padding:'11px 12px',fontSize:14,background:'#fff',color:'#111',outline:'none'}
const yellow:CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 15px',fontWeight:900,cursor:'pointer'}

const appLabel=(v:TargetApp|'driver'|'passenger')=>v==='driver'?'Motoristas':v==='passenger'?'Passageiros':'Motoristas + Passageiros'

export default function ManagementNotificationComposer({context}:{context:'matrix'|'franchise'}){
  const[targetApp,setTargetApp]=useState<TargetApp>('driver')
  const[mode,setMode]=useState<SendMode>('all')
  const[title,setTitle]=useState('')
  const[body,setBody]=useState('')
  const[search,setSearch]=useState('')
  const[recipients,setRecipients]=useState<Recipient[]>([])
  const[selected,setSelected]=useState<string[]>([])
  const[campaigns,setCampaigns]=useState<Campaign[]>([])
  const[loading,setLoading]=useState(false)
  const[sending,setSending]=useState(false)
  const[msg,setMsg]=useState('')
  const[error,setError]=useState('')

  useEffect(()=>{void loadRecipients()},[targetApp])
  useEffect(()=>{void loadCampaigns()},[])

  async function loadRecipients(){
    setLoading(true);setError('');setSelected([])
    const{data,error:e}=await supabase.rpc('management_notification_recipients',{p_target_app:targetApp})
    setLoading(false)
    if(e){setError(e.message);setRecipients([]);return}
    setRecipients((data||[]) as Recipient[])
  }

  async function loadCampaigns(){
    const{data,error:e}=await supabase.rpc('list_management_notification_campaigns',{p_limit:8})
    if(!e)setCampaigns((data||[]) as Campaign[])
  }

  const filtered=useMemo(()=>{
    const q=search.trim().toLowerCase()
    if(!q)return recipients
    return recipients.filter(r=>`${r.full_name} ${r.app_kind} ${r.city_name||''} ${r.city_state||''}`.toLowerCase().includes(q))
  },[recipients,search])
  const activeCount=recipients.filter(r=>r.has_active_device).length
  const selectedCount=selected.length

  function toggle(id:string){
    setSelected(prev=>prev.includes(id)?prev.filter(x=>x!==id):[...prev,id])
  }

  function selectVisible(){
    const ids=filtered.filter(r=>r.has_active_device).map(r=>r.user_id)
    setSelected(prev=>Array.from(new Set([...prev,...ids])))
  }

  async function send(){
    setMsg('');setError('')
    if(title.trim().length<2){setError('Digite um título para a notificação.');return}
    if(body.trim().length<2){setError('Digite a mensagem da notificação.');return}
    if(mode==='selected'&&selectedCount===0){setError('Selecione pelo menos um motorista ou passageiro.');return}
    const destination=mode==='all'?`todos os ${appLabel(targetApp).toLowerCase()} com aplicativo ativo`:`${selectedCount} destinatário(s) selecionado(s)`
    if(!window.confirm(`Enviar “${title.trim()}” para ${destination}?`))return

    setSending(true)
    const{data,error:e}=await supabase.rpc('send_management_notification',{
      p_target_app:targetApp,
      p_title:title.trim(),
      p_body:body.trim(),
      p_recipient_ids:mode==='selected'?selected:null,
    })
    setSending(false)
    if(e){setError(e.message);return}
    const count=Number((data as {recipient_count?:number}|null)?.recipient_count||0)
    setMsg(`Notificação enviada para ${count} destinatário(s).`)
    setTitle('');setBody('');setSelected([])
    await loadCampaigns()
  }

  return <div style={{display:'grid',gap:14,marginBottom:18}}>
    <section style={card}>
      <div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'flex-start',flexWrap:'wrap',marginBottom:18}}>
        <div><div style={{fontSize:11,fontWeight:900,letterSpacing:'.08em',textTransform:'uppercase',color:'#9a7d00'}}>Central de Notificações</div><h2 style={{margin:'5px 0 5px',fontSize:24}}>Disparar notificação para os aplicativos</h2><p style={{margin:0,color:'#666',fontSize:13,lineHeight:1.5,maxWidth:720}}>{context==='matrix'?'A Matriz pode enviar para toda a rede ou escolher motoristas e passageiros específicos.':'O Franqueado pode enviar somente para motoristas e passageiros vinculados à própria operação.'} Estas campanhas são administrativas e ficam separadas das mensagens privadas de corrida.</p></div>
        <div style={{background:'#fff8cc',border:'1px solid #ead163',borderRadius:10,padding:'9px 12px',fontSize:12,color:'#5e5000'}}>🔔 Envio via Firebase / FCM</div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(3,minmax(0,1fr))',gap:9,marginBottom:16}}>
        {(['driver','passenger','both'] as TargetApp[]).map(v=><button key={v} type="button" onClick={()=>setTargetApp(v)} style={{padding:'12px 10px',borderRadius:11,border:targetApp===v?'2px solid #111':'1px solid #ddd',background:targetApp===v?'#ffd400':'#fafafa',fontWeight:900,cursor:'pointer'}}>{v==='driver'?'🚘 Motoristas':v==='passenger'?'👤 Passageiros':'👥 Ambos os apps'}</button>)}
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:9,marginBottom:18}}>
        <label style={{border:mode==='all'?'2px solid #111':'1px solid #ddd',borderRadius:11,padding:12,cursor:'pointer',background:mode==='all'?'#fafafa':'#fff'}}><input type="radio" checked={mode==='all'} onChange={()=>setMode('all')}/> <b style={{marginLeft:5}}>Todos do aplicativo</b><div style={{fontSize:11,color:'#777',margin:'5px 0 0 23px'}}>{loading?'Carregando…':`${activeCount} destinatário(s) com aparelho ativo`}</div></label>
        <label style={{border:mode==='selected'?'2px solid #111':'1px solid #ddd',borderRadius:11,padding:12,cursor:'pointer',background:mode==='selected'?'#fafafa':'#fff'}}><input type="radio" checked={mode==='selected'} onChange={()=>setMode('selected')}/> <b style={{marginLeft:5}}>Escolher pessoas</b><div style={{fontSize:11,color:'#777',margin:'5px 0 0 23px'}}>{selectedCount} selecionado(s)</div></label>
      </div>

      {mode==='selected'?<div style={{border:'1px solid #e3e3e3',borderRadius:12,padding:12,marginBottom:16}}>
        <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:10,flexWrap:'wrap'}}><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar motorista, passageiro ou cidade..." style={{...input,flex:'1 1 260px'}}/><button type="button" onClick={selectVisible} style={{...yellow,padding:'10px 12px'}}>Selecionar visíveis</button><button type="button" onClick={()=>setSelected([])} style={{border:'1px solid #ddd',background:'#fff',borderRadius:10,padding:'10px 12px',fontWeight:800,cursor:'pointer'}}>Limpar</button></div>
        <div style={{maxHeight:310,overflow:'auto',display:'grid',gap:6}}>{filtered.length===0?<div style={{padding:18,textAlign:'center',color:'#777'}}>Nenhum destinatário encontrado.</div>:filtered.map(r=><label key={`${r.app_kind}-${r.user_id}`} style={{display:'grid',gridTemplateColumns:'24px 1fr auto',alignItems:'center',gap:8,padding:'9px 10px',border:'1px solid #eee',borderRadius:9,opacity:r.has_active_device?1:.55,background:'#fff'}}><input type="checkbox" disabled={!r.has_active_device} checked={selected.includes(r.user_id)} onChange={()=>toggle(r.user_id)}/><div><b style={{fontSize:13}}>{r.full_name}</b><div style={{fontSize:11,color:'#777'}}>{r.city_name?`${r.city_name}${r.city_state?`/${r.city_state}`:''}`:'Cidade não informada'}{!r.has_active_device?' · sem aparelho ativo':''}</div></div><span style={{fontSize:10,fontWeight:900,padding:'4px 7px',borderRadius:999,background:r.app_kind==='driver'?'#fff4b3':'#eef2ff',color:'#333'}}>{r.app_kind==='driver'?'MOTORISTA':'PASSAGEIRO'}</span></label>)}</div>
      </div>:null}

      <div style={{display:'grid',gap:12}}>
        <label><span style={label}>Título <small style={{fontWeight:500,color:'#888'}}>({title.length}/120)</small></span><input maxLength={120} value={title} onChange={e=>setTitle(e.target.value)} placeholder="Ex.: Promoção especial CLICK-GO" style={input}/></label>
        <label><span style={label}>Mensagem <small style={{fontWeight:500,color:'#888'}}>({body.length}/500)</small></span><textarea maxLength={500} value={body} onChange={e=>setBody(e.target.value)} placeholder="Digite a mensagem que aparecerá na notificação..." rows={4} style={{...input,resize:'vertical'}}/></label>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'}}><div style={{fontSize:12,color:'#666'}}>{mode==='all'?`Destino: ${appLabel(targetApp)} · todos com app ativo`:`Destino: ${selectedCount} pessoa(s) escolhida(s)`}</div><button onClick={send} disabled={sending||loading} style={{...yellow,opacity:sending||loading?.65:1}}>{sending?'Enviando…':'🔔 Disparar notificação'}</button></div>
      </div>

      {msg?<div style={{marginTop:12,padding:'10px 12px',borderRadius:10,background:'#ecfdf3',border:'1px solid #86efac',color:'#166534',fontSize:13}}>{msg}</div>:null}
      {error?<div style={{marginTop:12,padding:'10px 12px',borderRadius:10,background:'#fff1f2',border:'1px solid #fecdd3',color:'#9f1239',fontSize:13}}>{error}</div>:null}
    </section>

    <section style={card}><h3 style={{margin:'0 0 12px'}}>Últimos disparos</h3>{campaigns.length===0?<div style={{color:'#777',fontSize:13}}>Nenhuma campanha registrada ainda.</div>:<div style={{display:'grid',gap:7}}>{campaigns.map(c=><div key={c.id} style={{display:'grid',gridTemplateColumns:'1fr auto',gap:12,padding:'10px 11px',border:'1px solid #eee',borderRadius:10}}><div><b style={{fontSize:13}}>{c.title}</b><div style={{fontSize:11,color:'#777',marginTop:3}}>{appLabel(c.target_app)} · {c.selection_mode==='all'?'Todos':'Selecionados'} · {c.recipient_count} destinatário(s)</div></div><div style={{fontSize:11,color:'#777',whiteSpace:'nowrap'}}>{new Date(c.created_at).toLocaleString('pt-BR')}</div></div>)}</div>}</section>
  </div>
}
