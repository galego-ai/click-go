import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request:NextRequest){
  const q=(request.nextUrl.searchParams.get('q')||'').trim()
  if(q.length<3)return NextResponse.json({error:'Digite pelo menos 3 caracteres.'},{status:400})
  if(q.length>180)return NextResponse.json({error:'Endereço muito longo.'},{status:400})

  const url=new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('format','jsonv2')
  url.searchParams.set('q',q)
  url.searchParams.set('countrycodes','br')
  url.searchParams.set('limit','5')
  url.searchParams.set('addressdetails','1')

  try{
    const response=await fetch(url,{headers:{'User-Agent':'CLICK-GO/1.0 (+https://click-go-ten.vercel.app)','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.5'},next:{revalidate:86400}})
    if(!response.ok)return NextResponse.json({error:'Serviço de endereços temporariamente indisponível.'},{status:502})
    const rows=await response.json() as any[]
    return NextResponse.json({results:rows.map(r=>({label:String(r.display_name||''),lat:Number(r.lat),lng:Number(r.lon)})).filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lng)),attribution:'© OpenStreetMap contributors'})
  }catch{
    return NextResponse.json({error:'Não foi possível pesquisar o endereço.'},{status:502})
  }
}
