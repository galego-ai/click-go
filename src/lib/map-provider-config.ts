type MapProviderConfig={
  mapbox_public_token:string|null
  mapbox_enabled:boolean
  google_enabled:boolean
  openstreetmap_enabled:boolean
}

let cache:MapProviderConfig|null=null
let cacheAt=0
const TTL=5*60*1000

export async function getMapProviderConfig():Promise<MapProviderConfig>{
  if(cache&&Date.now()-cacheAt<TTL)return cache
  const fallback:MapProviderConfig={mapbox_public_token:null,mapbox_enabled:true,google_enabled:true,openstreetmap_enabled:true}
  const url=process.env.NEXT_PUBLIC_SUPABASE_URL
  const key=process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
  if(!url||!key)return fallback
  try{
    const res=await fetch(`${url}/rest/v1/rpc/get_public_map_provider_config`,{
      method:'POST',
      headers:{apikey:key,'Content-Type':'application/json'},
      body:'{}',
      cache:'no-store',
      signal:AbortSignal.timeout(4000)
    })
    if(!res.ok)return fallback
    const json=await res.json() as MapProviderConfig[]|MapProviderConfig
    const row=Array.isArray(json)?json[0]:json
    if(!row)return fallback
    cache={
      mapbox_public_token:typeof row.mapbox_public_token==='string'?row.mapbox_public_token:null,
      mapbox_enabled:row.mapbox_enabled!==false,
      google_enabled:row.google_enabled!==false,
      openstreetmap_enabled:row.openstreetmap_enabled!==false
    }
    cacheAt=Date.now()
    return cache
  }catch{return fallback}
}

export async function getMapboxAccessToken(){
  const direct=process.env.MAPBOX_ACCESS_TOKEN||process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN
  if(direct)return direct
  const cfg=await getMapProviderConfig()
  return cfg.mapbox_enabled?cfg.mapbox_public_token:null
}
