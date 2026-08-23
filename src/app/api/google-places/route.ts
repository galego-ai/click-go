import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(req:NextRequest){
 const key=process.env.GOOGLE_PLACES_API_KEY
 if(!key)return NextResponse.json({configured:false,places:[],message:'Google Places ainda não configurado no servidor.'},{status:503})
 const lat=Number(req.nextUrl.searchParams.get('lat'));const lng=Number(req.nextUrl.searchParams.get('lng'));const radius=Math.min(Math.max(Number(req.nextUrl.searchParams.get('radius')||1200),100),3000)
 if(!Number.isFinite(lat)||!Number.isFinite(lng))return NextResponse.json({error:'Latitude/longitude inválidas.'},{status:400})
 try{
  const response=await fetch('https://places.googleapis.com/v1/places:searchNearby',{method:'POST',headers:{'Content-Type':'application/json','X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.id,places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.googleMapsUri,places.primaryTypeDisplayName'},body:JSON.stringify({maxResultCount:12,rankPreference:'DISTANCE',languageCode:'pt-BR',regionCode:'BR',locationRestriction:{circle:{center:{latitude:lat,longitude:lng},radius}}}),cache:'no-store'})
  const raw=await response.json()
  if(!response.ok)return NextResponse.json({error:raw?.error?.message||'Falha no Google Places.'},{status:response.status})
  const places=(raw.places||[]).map((p:any)=>({id:p.id,name:p.displayName?.text||'Local',address:p.formattedAddress||'',phone:p.nationalPhoneNumber||'',lat:p.location?.latitude,lng:p.location?.longitude,type:p.primaryTypeDisplayName?.text||'',googleMapsUri:p.googleMapsUri||''})).filter((p:any)=>Number.isFinite(p.lat)&&Number.isFinite(p.lng))
  return NextResponse.json({configured:true,places,attribution:'Google Places'})
 }catch(e){return NextResponse.json({error:e instanceof Error?e.message:'Falha ao consultar empresas próximas.'},{status:500})}
}
