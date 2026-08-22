import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

type SearchResult={
  label:string
  name?:string
  subtitle?:string
  category?:string
  kind:'place'|'address'
  lat:number
  lng:number
  distanceKm?:number
}

function parseCoord(value:string|null,min:number,max:number){
  if(value===null||value.trim()==='')return null
  const n=Number(value)
  return Number.isFinite(n)&&n>=min&&n<=max?n:null
}

function normalize(value:string){
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim()
}

function regexEscape(value:string){
  return value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/"/g,'\\"')
}

function buildSearchUrl(q:string,lat:number|null,lng:number|null,bounded:boolean){
  const url=new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('format','jsonv2')
  url.searchParams.set('q',q)
  url.searchParams.set('countrycodes','br')
  url.searchParams.set('limit','7')
  url.searchParams.set('addressdetails','1')

  if(lat!==null&&lng!==null){
    const latDelta=0.30
    const lngDelta=0.32
    url.searchParams.set('viewbox',`${lng-lngDelta},${lat+latDelta},${lng+lngDelta},${lat-latDelta}`)
    url.searchParams.set('bounded',bounded?'1':'0')
  }
  return url
}

async function nominatim(url:URL){
  const response=await fetch(url,{
    headers:{
      'User-Agent':'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)',
      'Accept-Language':'pt-BR,pt;q=0.9,en;q=0.5'
    },
    cache:'no-store'
  })
  if(!response.ok)throw new Error('nominatim_unavailable')
  return await response.json() as any[]
}

function categorySelectors(query:string){
  const q=normalize(query)
  const selectors:string[]=[]
  if(q.includes('farm')||q.includes('drog')) selectors.push('["amenity"="pharmacy"]')
  if(q.includes('merc')||q.includes('super')||q.includes('atacad')) selectors.push('["shop"="supermarket"]','["shop"="convenience"]')
  if(q.includes('hosp')||q.includes('pronto')) selectors.push('["amenity"="hospital"]','["healthcare"="hospital"]')
  if(q.includes('posto')||q.includes('combust')) selectors.push('["amenity"="fuel"]')
  if(q.includes('rest')||q.includes('lanch')||q.includes('pizz')) selectors.push('["amenity"="restaurant"]','["amenity"="fast_food"]')
  if(q.includes('hotel')||q.includes('pous')) selectors.push('["tourism"="hotel"]','["tourism"="guest_house"]')
  if(q.includes('banco')||q.includes('caixa')) selectors.push('["amenity"="bank"]','["amenity"="atm"]')
  if(q.includes('escol')||q.includes('coleg')) selectors.push('["amenity"="school"]','["amenity"="college"]')
  if(q.includes('rodov')||q.includes('terminal')) selectors.push('["amenity"="bus_station"]','["public_transport"="station"]')
  if(q.includes('shop')||q.includes('shopping')) selectors.push('["shop"="mall"]')
  return selectors
}

function overpassQuery(q:string,lat:number,lng:number){
  const radius=15000
  const escaped=regexEscape(q)
  const namedSelectors=[
    'shop','amenity','tourism','leisure','healthcare','office','craft','public_transport'
  ].map(tag=>`nwr(around:${radius},${lat},${lng})["${tag}"]["name"~"${escaped}",i];`)
  const category=categorySelectors(q).map(sel=>`nwr(around:${radius},${lat},${lng})${sel};`)
  return `[out:json][timeout:9];(${[...category,...namedSelectors].join('')});out center tags 45;`
}

function haversine(lat1:number,lng1:number,lat2:number,lng2:number){
  const r=6371
  const dLat=(lat2-lat1)*Math.PI/180
  const dLng=(lng2-lng1)*Math.PI/180
  const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLng/2)**2
  return r*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a))
}

function categoryLabel(tags:any){
  const raw=String(tags.shop||tags.amenity||tags.tourism||tags.leisure||tags.healthcare||tags.office||tags.craft||tags.public_transport||'local')
  const labels:Record<string,string>={
    pharmacy:'Farmácia',supermarket:'Supermercado',convenience:'Conveniência',hospital:'Hospital',fuel:'Posto de combustível',
    restaurant:'Restaurante',fast_food:'Lanchonete',hotel:'Hotel',guest_house:'Pousada',bank:'Banco',atm:'Caixa eletrônico',
    school:'Escola',college:'Faculdade',bus_station:'Rodoviária',station:'Estação',mall:'Shopping'
  }
  return labels[raw]||raw.replaceAll('_',' ')
}

function placeAddress(tags:any,context:string){
  const parts:string[]=[]
  const street=String(tags['addr:street']||'').trim()
  const number=String(tags['addr:housenumber']||'').trim()
  if(street)parts.push(number?`${street}, ${number}`:street)
  const suburb=String(tags['addr:suburb']||tags['addr:neighbourhood']||'').trim()
  if(suburb)parts.push(suburb)
  const city=String(tags['addr:city']||'').trim()
  if(city)parts.push(city)
  if(parts.length===0&&context)parts.push(context)
  return parts.join(' · ')
}

async function nearbyPlaces(q:string,lat:number,lng:number,context:string):Promise<SearchResult[]>{
  const body=new URLSearchParams({data:overpassQuery(q,lat,lng)})
  const response=await fetch('https://overpass-api.de/api/interpreter',{
    method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded','User-Agent':'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)'},
    body,
    cache:'no-store',
    signal:AbortSignal.timeout(9500)
  })
  if(!response.ok)return []
  const json=await response.json() as any
  const rows=Array.isArray(json?.elements)?json.elements:[]
  const out:SearchResult[]=[]
  const seen=new Set<string>()
  for(const row of rows){
    const tags=row.tags||{}
    const name=String(tags.name||tags.brand||'').trim()
    if(!name)continue
    const pLat=Number(row.lat??row.center?.lat)
    const pLng=Number(row.lon??row.center?.lon)
    if(!Number.isFinite(pLat)||!Number.isFinite(pLng))continue
    const key=`${name.toLowerCase()}|${pLat.toFixed(4)}|${pLng.toFixed(4)}`
    if(seen.has(key))continue
    seen.add(key)
    const category=categoryLabel(tags)
    const address=placeAddress(tags,context)
    const subtitle=[category,address].filter(Boolean).join(' · ')
    out.push({
      name,subtitle,category,kind:'place',
      label:address?`${name}, ${address}`:name,
      lat:pLat,lng:pLng,distanceKm:haversine(lat,lng,pLat,pLng)
    })
  }
  return out.sort((a,b)=>(a.distanceKm??999)-(b.distanceKm??999)).slice(0,5)
}

export async function GET(request:NextRequest){
  const q=(request.nextUrl.searchParams.get('q')||'').trim()
  if(q.length<3)return NextResponse.json({error:'Digite pelo menos 3 caracteres.'},{status:400})
  if(q.length>180)return NextResponse.json({error:'Endereço muito longo.'},{status:400})

  const rawContext=(request.nextUrl.searchParams.get('context')||'').trim()
  const context=rawContext.length<=100?rawContext:''
  const lat=parseCoord(request.nextUrl.searchParams.get('lat'),-90,90)
  const lng=parseCoord(request.nextUrl.searchParams.get('lng'),-180,180)

  try{
    let addressRows:any[]=[]
    let usedLocalSearch=false
    let places:SearchResult[]=[]

    if(lat!==null&&lng!==null){
      const placePromise=nearbyPlaces(q,lat,lng,context).catch(()=>[])
      const regionalQuery=context?`${q}, ${context}`:q
      addressRows=await nominatim(buildSearchUrl(regionalQuery,lat,lng,true))
      usedLocalSearch=addressRows.length>0
      if(addressRows.length===0&&context){
        addressRows=await nominatim(buildSearchUrl(q,lat,lng,true))
        usedLocalSearch=addressRows.length>0
      }
      places=await placePromise
    }

    if(addressRows.length===0){
      addressRows=await nominatim(buildSearchUrl(q,lat,lng,false))
    }

    const addressResults:SearchResult[]=addressRows.map(r=>({
      label:String(r.display_name||''),
      name:String(r.name||'').trim()||undefined,
      subtitle:String(r.display_name||''),
      category:'Endereço',kind:'address' as const,
      lat:Number(r.lat),lng:Number(r.lon)
    })).filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lng)&&r.label)

    const seen=new Set<string>()
    const results=[...places,...addressResults].filter(r=>{
      const key=`${r.label.toLowerCase()}|${r.lat.toFixed(4)}|${r.lng.toFixed(4)}`
      if(seen.has(key))return false
      seen.add(key)
      return true
    }).slice(0,7)

    return NextResponse.json({
      results,
      regionalized:lat!==null&&lng!==null,
      localResults:usedLocalSearch||places.length>0,
      placesFound:places.length,
      contextApplied:Boolean(context),
      attribution:'© OpenStreetMap contributors'
    })
  }catch{
    return NextResponse.json({error:'Serviço de endereços temporariamente indisponível.'},{status:502})
  }
}
