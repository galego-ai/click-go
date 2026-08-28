'use client'

import {useEffect,useState} from 'react'
import type {CSSProperties} from 'react'
import {supabase} from '@/lib/supabase'
import ManagementNotificationComposer from '@/components/ManagementNotificationComposer'

type Status={
  fcm_configured:boolean
  fcm_project_id:string|null
  active_devices:number
  queue:Record<string,number>
  total_queue:number
  checked_at:string
}

const box:CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:16,color:'#fff'}
const btn:CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'10px 14px',fontWeight:900,cursor:'pointer'}

export default function PushNotificationsPage(){
  const[data,setData]=useState<Status|null>(null)
  const[busy,setBusy]=useState(false)
  const[msg,setMsg]=useState('')

  useEffect(()=>{void load()},[])

  async function load(){
    setBusy(true);setMsg('')
    const{data:result,error}=await supabase.functions.invoke('push-status',{method:'POST',body:{}})
    setBusy(false)
    if(error){setMsg(error.message);return}
    setData(result as Status)
  }

  const queue=data?.queue||{}
  const sent=queue.sent||0,partial=queue.partial||0,failed=queue.failed||0,pending=(queue.queued||0)+(queue.pending_fcm_configuration||0),noDevices=queue.no_devices||0

  return <div>
    <div className="topbar"><div><div className="eyebrow">Operação da rede</div><h1 className="title">Notificações</h1><p className="subtitle">Envie avisos administrativos aos aplicativos Motorista e Passageiro, para todos ou para pessoas específicas.</p></div></div>

    <ManagementNotificationComposer context="matrix"/>

    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,margin:'22px 0 10px'}}><div><h2 style={{margin:0,fontSize:20}}>Diagnóstico técnico do Push</h2><p style={{margin:'4px 0 0',fontSize:12,color:'#777'}}>Status do Firebase Cloud Messaging e da fila de entrega.</p></div><button onClick={load} disabled={busy} style={btn}>{busy?'Verificando…':'Atualizar diagnóstico'}</button></div>

    <div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:12,marginBottom:14}}>
      <div style={{...box,borderColor:data?.fcm_configured?'#166534':'#854d0e'}}><small style={{color:'#9ca3af'}}>FIREBASE / FCM</small><div style={{fontSize:22,fontWeight:950,color:data?.fcm_configured?'#4ade80':'#fbbf24',marginTop:4}}>{data?.fcm_configured?'CONFIGURADO':'PENDENTE'}</div><div style={{fontSize:11,color:'#9ca3af',marginTop:4}}>{data?.fcm_project_id||'Nenhum service account configurado'}</div></div>
      <div style={box}><small style={{color:'#9ca3af'}}>APARELHOS ATIVOS</small><div style={{fontSize:30,fontWeight:950}}>{data?.active_devices??'—'}</div></div>
      <div style={box}><small style={{color:'#9ca3af'}}>ENVIADOS</small><div style={{fontSize:30,fontWeight:950,color:'#4ade80'}}>{sent}</div><div style={{fontSize:11,color:'#9ca3af'}}>Parciais: {partial}</div></div>
      <div style={box}><small style={{color:'#9ca3af'}}>FILA / FALHAS</small><div style={{fontSize:30,fontWeight:950,color:failed?'#f87171':pending?'#fbbf24':'#e5e7eb'}}>{pending+failed}</div><div style={{fontSize:11,color:'#9ca3af'}}>Pendente {pending} · falha {failed}</div></div>
    </div>

    {!data?.fcm_configured?<section style={{...box,borderColor:'#854d0e',marginBottom:14}}><h2 style={{margin:'0 0 8px',color:'#fbbf24'}}>Configuração externa ainda necessária</h2><p style={{margin:'0 0 10px',color:'#d1d5db',lineHeight:1.55}}>O backend CLICK-GO, a fila e os APKs estão preparados. Para notificações chegarem com o aplicativo fechado, falta conectar um projeto Firebase e cadastrar o service account no ambiente seguro da Edge Function.</p><div style={{display:'grid',gap:6,fontSize:13,color:'#9ca3af'}}><div><b style={{color:'#fff'}}>Supabase Edge Function:</b> FCM_SERVICE_ACCOUNT_JSON</div><div><b style={{color:'#fff'}}>GitHub APKs:</b> CLICKGO_FIREBASE_PROJECT_ID, CLICKGO_FIREBASE_API_KEY e CLICKGO_FIREBASE_SENDER_ID</div><div><b style={{color:'#fff'}}>Motorista:</b> CLICKGO_FIREBASE_DRIVER_APP_ID</div><div><b style={{color:'#fff'}}>Passageiro:</b> CLICKGO_FIREBASE_PASSENGER_APP_ID</div></div></section>:null}

    <section style={box}><h2 style={{marginTop:0}}>Fila de entrega</h2><div style={{display:'grid',gridTemplateColumns:'repeat(5,minmax(0,1fr))',gap:9}}><div><small style={{color:'#9ca3af'}}>AGUARDANDO</small><div style={{fontSize:22,fontWeight:900}}>{pending}</div></div><div><small style={{color:'#9ca3af'}}>ENVIADAS</small><div style={{fontSize:22,fontWeight:900,color:'#4ade80'}}>{sent}</div></div><div><small style={{color:'#9ca3af'}}>PARCIAIS</small><div style={{fontSize:22,fontWeight:900,color:'#fbbf24'}}>{partial}</div></div><div><small style={{color:'#9ca3af'}}>SEM APARELHO</small><div style={{fontSize:22,fontWeight:900}}>{noDevices}</div></div><div><small style={{color:'#9ca3af'}}>FALHAS</small><div style={{fontSize:22,fontWeight:900,color:failed?'#f87171':'#e5e7eb'}}>{failed}</div></div></div><div style={{fontSize:12,color:'#9ca3af',marginTop:12}}>Total registrado na fila: {data?.total_queue??0}{data?.checked_at?` · verificado em ${new Date(data.checked_at).toLocaleString('pt-BR')}`:''}.</div></section>

    {msg?<div style={{...box,borderColor:'#7f1d1d',color:'#fca5a5',marginTop:12}}>{msg}</div>:null}
  </div>
}
