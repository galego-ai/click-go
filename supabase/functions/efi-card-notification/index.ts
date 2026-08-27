import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {createClient} from "jsr:@supabase/supabase-js@2.112.4";

const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json"}});
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
async function auth(){
 const id=(Deno.env.get('EFI_BILLING_CLIENT_ID')||Deno.env.get('EFI_CLIENT_ID')||'').trim();
 const secret=(Deno.env.get('EFI_BILLING_CLIENT_SECRET')||Deno.env.get('EFI_CLIENT_SECRET')||'').trim();
 if(!id||!secret)throw new Error('Credenciais Efí Cobranças ausentes');
 const sandbox=(Deno.env.get('EFI_BILLING_SANDBOX')||Deno.env.get('EFI_SANDBOX'))==='true';
 const base=sandbox?'https://cobrancas-h.api.efipay.com.br':'https://cobrancas.api.efipay.com.br';
 const r=await fetch(`${base}/v1/authorize`,{method:'POST',headers:{Authorization:`Basic ${b64(`${id}:${secret}`)}`,'Content-Type':'application/json','Accept-Encoding':'identity'},body:JSON.stringify({grant_type:'client_credentials'})});
 const body=await r.json().catch(()=>({}));if(!r.ok||!body?.access_token)throw new Error(`Efí OAuth ${r.status}`);
 return {base,headers:{Authorization:`Bearer ${body.access_token}`,'Accept-Encoding':'identity'}};
}
function latestStatus(data:any){
 const rows=Array.isArray(data?.data)?data.data:Array.isArray(data)?data:[];
 for(let i=rows.length-1;i>=0;i--){const row=rows[i];const chargeId=Number(row?.identifiers?.charge_id||0);const status=String(row?.status?.current||'').toLowerCase();if(chargeId&&status)return{chargeId,status}}
 return null;
}
Deno.serve(async req=>{
 if(req.method!=='POST')return json({ok:true});
 try{
  const contentType=req.headers.get('content-type')||'';let notification='';
  if(contentType.includes('application/json')){const b=await req.json().catch(()=>({}));notification=String(b?.notification||'')}
  else{const text=await req.text();notification=new URLSearchParams(text).get('notification')||''}
  if(!notification)return json({ok:true,ignored:true});
  const{base,headers}=await auth();const r=await fetch(`${base}/v1/notification/${encodeURIComponent(notification)}`,{headers});const body=await r.json().catch(()=>({}));if(!r.ok)return json({ok:false,error:`Efí notification ${r.status}`},502);
  const latest=latestStatus(body);if(!latest)return json({ok:true,ignored:true});
  const url=Deno.env.get('SUPABASE_URL')||'',service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';if(!url||!service)return json({ok:false,error:'Supabase interno ausente'},500);
  const admin=createClient(url,service);const{data:charge}=await admin.from('ride_card_charges').select('id,payment_id,ride_id,status').eq('charge_id',latest.chargeId).maybeSingle();if(!charge)return json({ok:true,ignored:true});
  const paid=['paid','settled'].includes(latest.status);const authorized=['approved','identified','waiting'].includes(latest.status);const cancelled=['canceled','expired','refunded','contested'].includes(latest.status);const localStatus=paid?'paid':authorized?'authorized':cancelled?'cancelled':'failed';const paidAt=paid?new Date().toISOString():null;
  await admin.from('ride_card_charges').update({status:localStatus,provider_status:latest.status,paid_at:paidAt,raw_response:body}).eq('id',charge.id);
  if(charge.payment_id){await admin.from('payments').update({status:paid?'paid':authorized?'authorized':cancelled?'cancelled':'failed',paid_at:paidAt,provider_reference:String(latest.chargeId)}).eq('id',charge.payment_id)}
  await admin.from('audit_logs').insert({actor_id:null,action:'efi_card_notification',entity:'rides',entity_id:charge.ride_id,metadata:{charge_id:latest.chargeId,provider_status:latest.status,local_status:localStatus}});
  return json({ok:true});
 }catch(error){console.error('efi-card-notification',error);return json({ok:false,error:error instanceof Error?error.message:'Falha no callback Efí'},500)}
});
