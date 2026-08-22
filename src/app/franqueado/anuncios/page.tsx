'use client'

import { FormEvent, useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type City={id:string;name:string;state:string}
type Banner={id:string;title:string;image_url:string;target_url:string|null;audience:'passenger'|'driver'|'both';active:boolean;city_id:string|null;starts_at:string|null;ends_at:string|null}

const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}

const audienceLabel=(v:string)=>v==='passenger'?'Passageiro':v==='driver'?'Motorista':'Passageiro e Motorista'

export default function FranchiseAdsPage(){
  const [franchiseId,setFranchiseId]=useState<string|null>(null)
  const [franchiseName,setFranchiseName]=useState('')
  const [cities,setCities]=useState<City[]>([])
  const [banners,setBanners]=useState<Banner[]>([])
  const [busy,setBusy]=useState(false)
  const [msg,setMsg]=useState('')
  const [form,setForm]=useState({title:'',image_url:'',target_url:'',city_id:'',audience:'passenger' as 'passenger'|'driver'|'both',starts_at:'',ends_at:''})

  useEffect(()=>{load()},[])

  async function load(){
    setBusy(true);setMsg('')
    try{
      const {data:{user}}=await supabase.auth.getUser()
      if(!user)throw new Error('Faça login como franqueado.')
      const {data:p,error:pe}=await supabase.from('profiles').select('franchise_id,role').eq('id',user.id).single()
      if(pe)throw pe
      if(!p?.franchise_id||p.role!=='franchise_admin')throw new Error('Acesso exclusivo do franqueado.')
      setFranchiseId(p.franchise_id)
      const [fc,fr,b]=await Promise.all([
        supabase.from('franchise_cities').select('city_id,cities(id,name,state)').eq('franchise_id',p.franchise_id),
        supabase.from('franchises').select('trade_name').eq('id',p.franchise_id).single(),
        supabase.from('advertising_banners').select('id,title,image_url,target_url,audience,active,city_id,starts_at,ends_at').eq('franchise_id',p.franchise_id).order('created_at',{ascending:false}),
      ])
      if(fc.error)throw fc.error;if(fr.error)throw fr.error;if(b.error)throw b.error
      const cityRows=(fc.data||[]).map((x:any)=>x.cities).filter(Boolean) as City[]
      setCities(cityRows);setFranchiseName(fr.data?.trade_name||'')
      setBanners((b.data||[]) as Banner[])
    }catch(e:any){setMsg(e.message||'Erro ao carregar anúncios.')}
    finally{setBusy(false)}
  }

  async function createAd(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!franchiseId)return
    setBusy(true);setMsg('')
    const {error}=await supabase.from('advertising_banners').insert({
      title:form.title.trim(),
      image_url:form.image_url.trim(),
      target_url:form.target_url.trim()||null,
      advertiser_name:franchiseName||null,
      city_id:form.city_id||null,
      franchise_id:franchiseId,
      placement:'home',
      audience:form.audience,
      sort_order:100,
      active:true,
      starts_at:form.starts_at||null,
      ends_at:form.ends_at||null,
    })
    if(error)setMsg(error.message)
    else{
      setMsg('Anúncio publicado somente para a sua franquia.')
      setForm(v=>({...v,title:'',image_url:'',target_url:'',starts_at:'',ends_at:''}))
      await load()
    }
    setBusy(false)
  }

  async function toggle(b:Banner){
    const {error}=await supabase.from('advertising_banners').update({active:!b.active}).eq('id',b.id)
    setMsg(error?error.message:'Anúncio atualizado.')
    if(!error)await load()
  }

  return <main style={{padding:24,color:'#f8fafc',maxWidth:1280,margin:'0 auto'}}>
    <div style={{marginBottom:20}}><div className="eyebrow">Franquia</div><h1 className="title">Anúncios nos apps</h1><p className="subtitle">Escolha Passageiro, Motorista ou Ambos. O anúncio permanece restrito à sua franquia e às cidades que você administra.</p></div>
    {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b',marginBottom:16}}>{msg}</div>}
    <div style={{display:'grid',gridTemplateColumns:'minmax(320px,440px) 1fr',gap:18,alignItems:'start'}}>
      <form onSubmit={createAd} style={box}>
        <h2 style={{marginTop:0}}>Novo anúncio</h2>
        <div style={{display:'grid',gap:11}}>
          <label>Título<input required style={input} value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label>
          <label>URL da imagem<input required type="url" style={input} value={form.image_url} onChange={e=>setForm({...form,image_url:e.target.value})}/></label>
          <label>Link ao clicar<input type="url" style={input} value={form.target_url} onChange={e=>setForm({...form,target_url:e.target.value})}/></label>
          <label>Exibir no app<select style={input} value={form.audience} onChange={e=>setForm({...form,audience:e.target.value as any})}><option value="passenger">Passageiro</option><option value="driver">Motorista</option><option value="both">Passageiro e Motorista</option></select></label>
          <label>Cidade<select style={input} value={form.city_id} onChange={e=>setForm({...form,city_id:e.target.value})}><option value="">Todas as cidades da minha franquia</option>{cities.map(c=><option key={c.id} value={c.id}>{c.name}/{c.state}</option>)}</select></label>
          <label>Início<input type="datetime-local" style={input} value={form.starts_at} onChange={e=>setForm({...form,starts_at:e.target.value})}/></label>
          <label>Fim<input type="datetime-local" style={input} value={form.ends_at} onChange={e=>setForm({...form,ends_at:e.target.value})}/></label>
          <button disabled={busy} style={{...btn,opacity:busy?.6:1}}>{busy?'Salvando...':'Publicar anúncio'}</button>
        </div>
      </form>
      <section>
        <h2 style={{marginTop:0}}>Meus anúncios</h2>
        <div style={{display:'grid',gap:10}}>
          {banners.map(b=><div key={b.id} style={{...box,display:'grid',gridTemplateColumns:'120px 1fr auto',gap:14,alignItems:'center'}}>
            <img src={b.image_url} alt={b.title} style={{width:120,height:72,objectFit:'cover',borderRadius:10,background:'#222'}}/>
            <div><b>{b.title}</b><div style={{color:'#9ca3af',fontSize:13,marginTop:5}}>{audienceLabel(b.audience)} · {b.city_id?(cities.find(c=>c.id===b.city_id)?.name||'Cidade da franquia'):'Todas as cidades'} · {b.active?'Ativo':'Pausado'}</div></div>
            <button onClick={()=>toggle(b)} style={{...btn,background:b.active?'#252525':'#ffd400',color:b.active?'#fff':'#000'}}>{b.active?'Pausar':'Ativar'}</button>
          </div>)}
          {!banners.length&&<div style={box}>Nenhum anúncio cadastrado.</div>}
        </div>
      </section>
    </div>
  </main>
}
