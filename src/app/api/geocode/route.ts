import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

function parseCoord(value:string|null,min:number,max:number){
  if(value===null||value.trim()==='')return null
  const n=Number(value)
  return Number.isFinite(n)&&n>=min&&n<=max?n:null
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

export async function GET(request:NextRequest){
  const q=(request.nextUrl.searchParams.get('q')||'').trim()
  if(q.length<3)return NextResponse.json({error:'Digite pelo menos 3 caracteres.'},{status:400})
  if(q.length>180)return NextResponse.json({error:'Endereço muito longo.'},{status:400})

  const rawContext=(request.nextUrl.searchParams.get('context')||'').trim()
  const context=rawContext.length<=100?rawContext:''
  const lat=parseCoord(request.nextUrl.searchParams.get('lat'),-90,90)
  const lng=parseCoord(request.nextUrl.searchParams.get('lng'),-180,180)

  try{
    let rows:any[]=[]
    let usedLocalSearch=false

    if(lat!==null&&lng!==null){
      // Primeiro procura na região atual usando também cidade/UF quando o app informar.
      const regionalQuery=context?`${q}, ${context}`:q
      rows=await nominatim(buildSearchUrl(regionalQuery,lat,lng,true))
      usedLocalSearch=rows.length>0

      // Se o contexto textual não encontrar, ainda tenta somente pelo raio.
      if(rows.length===0&&context){
        rows=await nominatim(buildSearchUrl(q,lat,lng,true))
        usedLocalSearch=rows.length>0
      }
    }

    // Só depois libera busca nacional, mantendo o texto original para permitir
    // que o passageiro pesquise um destino em outra cidade.
    if(rows.length===0){
      rows=await nominatim(buildSearchUrl(q,lat,lng,false))
    }

    const seen=new Set<string>()
    const results=rows
      .map(r=>({label:String(r.display_name||''),lat:Number(r.lat),lng:Number(r.lon)}))
      .filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lng)&&r.label)
      .filter(r=>{
        const key=`${r.label.toLowerCase()}|${r.lat.toFixed(5)}|${r.lng.toFixed(5)}`
        if(seen.has(key))return false
        seen.add(key)
        return true
      })
      .slice(0,7)

    return NextResponse.json({
      results,
      regionalized:lat!==null&&lng!==null,
      localResults:usedLocalSearch,
      contextApplied:Boolean(context),
      attribution:'© OpenStreetMap contributors'
    })
  }catch{
    return NextResponse.json({error:'Serviço de endereços temporariamente indisponível.'},{status:502})
  }
}
