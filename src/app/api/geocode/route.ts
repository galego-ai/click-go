import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

function parseCoord(value:string|null,min:number,max:number){
  if(value===null||value.trim()==='')return null
  const n=Number(value)
  return Number.isFinite(n)&&n>=min&&n<=max?n:null
}

export async function GET(request:NextRequest){
  const q=(request.nextUrl.searchParams.get('q')||'').trim()
  if(q.length<3)return NextResponse.json({error:'Digite pelo menos 3 caracteres.'},{status:400})
  if(q.length>180)return NextResponse.json({error:'Endereço muito longo.'},{status:400})

  const lat=parseCoord(request.nextUrl.searchParams.get('lat'),-90,90)
  const lng=parseCoord(request.nextUrl.searchParams.get('lng'),-180,180)
  const url=new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('format','jsonv2')
  url.searchParams.set('q',q)
  url.searchParams.set('countrycodes','br')
  url.searchParams.set('limit','7')
  url.searchParams.set('addressdetails','1')

  // Quando o app conhece a origem, usamos uma caixa aproximada de 45 km
  // apenas como preferência de ranking. bounded=0 permite buscar fora dela
  // se o passageiro informar um endereço mais distante.
  if(lat!==null&&lng!==null){
    const latDelta=0.42
    const lngDelta=0.45
    url.searchParams.set('viewbox',`${lng-lngDelta},${lat+latDelta},${lng+lngDelta},${lat-latDelta}`)
    url.searchParams.set('bounded','0')
  }

  try{
    const response=await fetch(url,{headers:{'User-Agent':'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.5'},cache:'no-store'})
    if(!response.ok)return NextResponse.json({error:'Serviço de endereços temporariamente indisponível.'},{status:502})
    const rows=await response.json() as any[]
    return NextResponse.json({
      results:rows.map(r=>({label:String(r.display_name||''),lat:Number(r.lat),lng:Number(r.lon)})).filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lng)),
      regionalized:lat!==null&&lng!==null,
      attribution:'© OpenStreetMap contributors'
    })
  }catch{
    return NextResponse.json({error:'Não foi possível pesquisar o endereço.'},{status:502})
  }
}
