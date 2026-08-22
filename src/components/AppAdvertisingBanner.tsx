'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type Banner={
  id:string
  title:string
  image_url:string
  target_url:string|null
  advertiser_name:string|null
  audience:string
}

export default function AppAdvertisingBanner({audience}:{audience:'passenger'|'driver'}){
  const [banners,setBanners]=useState<Banner[]>([])

  useEffect(()=>{
    let mounted=true
    let permissionStatus:PermissionStatus|null=null

    async function fetchBanners(lat?:number,lng?:number){
      const {data:{user}}=await supabase.auth.getUser()
      if(!user||!mounted){if(mounted)setBanners([]);return}
      const {data,error}=await supabase.rpc('get_app_banners',{
        p_audience:audience,
        p_lat:lat??null,
        p_lng:lng??null,
      })
      if(!error&&mounted)setBanners((data||[]) as Banner[])
    }

    function loadPassengerBanners(){
      if(!navigator.geolocation)return
      navigator.geolocation.getCurrentPosition(
        pos=>fetchBanners(pos.coords.latitude,pos.coords.longitude),
        ()=>{if(mounted)setBanners([])},
        {enableHighAccuracy:false,timeout:8000,maximumAge:300000},
      )
    }

    async function load(){
      if(audience==='driver'){
        await fetchBanners()
        return
      }
      if(typeof navigator==='undefined')return
      if(navigator.permissions?.query){
        try{
          permissionStatus=await navigator.permissions.query({name:'geolocation'})
          if(permissionStatus.state==='granted')loadPassengerBanners()
          permissionStatus.onchange=()=>{
            if(permissionStatus?.state==='granted')loadPassengerBanners()
            else if(mounted)setBanners([])
          }
          return
        }catch{}
      }
      // Não abre pedido de localização apenas para publicidade.
    }

    load()
    const {data:listener}=supabase.auth.onAuthStateChange((_event,session)=>{
      if(!session){setBanners([]);return}
      load()
    })

    return()=>{
      mounted=false
      if(permissionStatus)permissionStatus.onchange=null
      listener.subscription.unsubscribe()
    }
  },[audience])

  if(!banners.length)return null

  return <div style={{maxWidth:1180,margin:'14px auto 0',padding:'0 16px'}}>
    <div style={{fontSize:10,textTransform:'uppercase',letterSpacing:'.12em',color:'#737373',marginBottom:6}}>Publicidade</div>
    <div style={{display:'grid',gridTemplateColumns:banners.length>1?'repeat(auto-fit,minmax(240px,1fr))':'1fr',gap:10}}>
      {banners.map(b=>{
        const content=<div style={{background:'#111',border:'1px solid #292929',borderRadius:14,overflow:'hidden'}}>
          <img src={b.image_url} alt={b.title} style={{display:'block',width:'100%',height:150,objectFit:'cover'}}/>
          <div style={{padding:'9px 11px',color:'#f5f5f5',fontSize:13,fontWeight:700}}>{b.title}{b.advertiser_name&&<span style={{fontWeight:400,color:'#8f8f8f'}}> · {b.advertiser_name}</span>}</div>
        </div>
        return b.target_url?<a key={b.id} href={b.target_url} target="_blank" rel="noopener noreferrer" style={{textDecoration:'none'}}>{content}</a>:<div key={b.id}>{content}</div>
      })}
    </div>
  </div>
}
