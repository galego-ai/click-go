import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json"}});
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
const required=["EFI_CLIENT_ID","EFI_CLIENT_SECRET","EFI_CERT_PEM","EFI_KEY_PEM","EFI_PIX_KEY"];
const providerError=(body:any)=>({nome:body?.nome??body?.name??null,mensagem:body?.mensagem??body?.message??body?.erro??body?.error??null});
const money=(v:unknown)=>Number(v||0);
const monthStart=(v:string)=>/^\d{4}-\d{2}(-01)?$/.test(v)?`${v.slice(0,7)}-01`:null;

type ChargeRow={id:string;invoice_id:string;franchise_id:string;txid:string;location_id:number|null;location:string|null;qrcode:string|null;qrcode_image:string|null;visualization_link:string|null;amount:number;status:string;provider_status:string|null;end_to_end_id:string|null;expires_at:string|null;paid_at:string|null;created_at:string};

Deno.serve(async(req)=>{
 try{
  if(req.method!=="POST")return json({error:"Método não permitido"},405);
  const url=Deno.env.get("SUPABASE_URL")||"";
  const service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
  if(!url||!service)return json({error:"Supabase interno não configurado"},500);
  const authHeader=req.headers.get("Authorization")||"";
  const token=authHeader.replace(/^Bearer\s+/i,"");
  if(!token)return json({error:"Não autenticado"},401);
  const admin=createClient(url,service);
  const {data:userData,error:userError}=await admin.auth.getUser(token);
  const user=userData?.user;
  if(userError||!user)return json({error:"Sessão inválida"},401);
  const {data:profile}=await admin.from("profiles").select("id,role,franchise_id,full_name,email").eq("id",user.id).maybeSingle();
  const role=String(user.app_metadata?.role||profile?.role||"");
  if(!["super_admin","franchise_admin","operator"].includes(role))return json({error:"Acesso não autorizado"},403);

  const body=await req.json().catch(()=>({}));
  const action=String(body?.action||"status");
  if(!["create","status"].includes(action))return json({error:"Ação inválida"},400);
  const reference=monthStart(String(body?.reference_month||new Date().toISOString().slice(0,7)));
  if(!reference)return json({error:"Mês de referência inválido"},400);
  let franchiseId=String(body?.franchise_id||"");
  if(role==="franchise_admin"||role==="operator")franchiseId=String(profile?.franchise_id||user.app_metadata?.franchise_id||"");
  if(!franchiseId)return json({error:"Franquia não identificada"},400);
  if(role==="operator"){
   const {data:staff}=await admin.from("franchise_staff_permissions").select("permissions").eq("profile_id",user.id).maybeSingle();
   if(!staff?.permissions?.finance)return json({error:"Sem permissão financeira"},403);
  }

  const userClient=createClient(url,service,{global:{headers:{Authorization:authHeader}}});
  const {data:summary,error:summaryError}=await userClient.rpc("get_franchise_billing_summary",{p_franchise_id:franchiseId,p_reference_month:reference});
  if(summaryError)return json({error:summaryError.message},400);
  if(!summary?.has_plan)return json({error:"Nenhum plano contratado neste período"},400);
  const total=money(summary.total_due);
  if(total<=0)return json({error:"A fatura não possui saldo a pagar",summary},400);

  let {data:invoice,error:invoiceError}=await admin.from("franchise_invoices").select("*").eq("franchise_id",franchiseId).eq("reference_month",reference).maybeSingle();
  if(invoiceError)return json({error:invoiceError.message},500);
  const due=summary.due_date||null;
  const usage=money(summary.per_ride_amount)+money(summary.overage_amount)+money(summary.percentage_amount);
  if(invoice?.status==="paid")return json({paid:true,invoice,summary,charge:null});
  const invoicePayload={franchise_id:franchiseId,reference_month:reference,rides_count:Number(summary.rides_count||0),gross_ride_value:money(summary.gross_ride_value),monthly_fee:money(summary.monthly_fee),usage_fee:usage,matrix_commission:0,total_due:total,due_date:due,status:due&&due<new Date().toISOString().slice(0,10)?"overdue":"pending"};
  if(invoice){const updated=await admin.from("franchise_invoices").update(invoicePayload).eq("id",invoice.id).select("*").single();if(updated.error)return json({error:updated.error.message},500);invoice=updated.data}
  else{const inserted=await admin.from("franchise_invoices").insert(invoicePayload).select("*").single();if(inserted.error)return json({error:inserted.error.message},500);invoice=inserted.data}

  const missing=required.filter(name=>!(Deno.env.get(name)||"").trim());
  if(missing.length)return json({error:"Efí não está totalmente configurada",missing},503);
  const sandbox=Deno.env.get("EFI_SANDBOX")==="true";
  const base=sandbox?"https://pix-h.api.efipay.com.br":"https://pix.api.efipay.com.br";
  const id=Deno.env.get("EFI_CLIENT_ID")!;
  const secret=Deno.env.get("EFI_CLIENT_SECRET")!;
  const certChain=Deno.env.get("EFI_CERT_PEM")!;
  const privateKey=Deno.env.get("EFI_KEY_PEM")!;
  const pixKey=Deno.env.get("EFI_PIX_KEY")!;
  const client=Deno.createHttpClient({certChain,privateKey});
  const oauthRes=await fetch(`${base}/oauth/token`,{method:"POST",client,headers:{Authorization:`Basic ${b64(`${id}:${secret}`)}`,"Content-Type":"application/json","Accept-Encoding":"identity"},body:JSON.stringify({grant_type:"client_credentials"})});
  const oauthBody=await oauthRes.json().catch(()=>({}));
  if(!oauthRes.ok||!oauthBody?.access_token)return json({error:"Falha ao autenticar na Efí",provider_status:oauthRes.status,provider_error:providerError(oauthBody)},502);
  const providerHeaders={Authorization:`Bearer ${oauthBody.access_token}`,"Content-Type":"application/json","Accept-Encoding":"identity"};

  const syncCharge=async(charge:ChargeRow)=>{
   const res=await fetch(`${base}/v2/cob/${encodeURIComponent(charge.txid)}`,{method:"GET",client,headers:providerHeaders});
   const provider=await res.json().catch(()=>({}));
   if(!res.ok){await admin.from("franchise_invoice_pix_charges").update({provider_status:`HTTP_${res.status}`,raw_response:provider}).eq("id",charge.id);return {error:true,status:res.status,provider};}
   const providerStatus=String(provider?.status||"");
   const pix=Array.isArray(provider?.pix)?provider.pix[0]:null;
   let local="active";
   if(providerStatus==="CONCLUIDA")local="paid";
   else if(providerStatus.includes("REMOVIDA"))local="cancelled";
   else if(charge.expires_at&&Date.parse(charge.expires_at)<Date.now())local="expired";
   const paidAt=pix?.horario||((local==="paid")?new Date().toISOString():null);
   const endToEnd=pix?.endToEndId||pix?.endToEndID||null;
   const update:any={status:local,provider_status:providerStatus,end_to_end_id:endToEnd,raw_response:provider};
   if(paidAt)update.paid_at=paidAt;
   const updated=await admin.from("franchise_invoice_pix_charges").update(update).eq("id",charge.id).select("*").single();
   if(local==="paid"){
    await admin.from("franchise_invoices").update({status:"paid",paid_at:paidAt}).eq("id",invoice.id);
    const {data:rule}=await admin.from("franchise_collection_rules").select("auto_reactivate_on_payment").eq("franchise_id",franchiseId).maybeSingle();
    const autoReactivate=rule?.auto_reactivate_on_payment!==false;
    if(autoReactivate){
     await admin.from("franchises").update({license_status:"active",active:true,blocked_at:null,blocked_reason:null,updated_at:new Date().toISOString()}).eq("id",franchiseId).neq("license_status","cancelled");
     await admin.from("franchise_subscriptions").update({license_status:"active",updated_at:new Date().toISOString()}).eq("franchise_id",franchiseId).eq("status","active");
    }
    await admin.from("audit_logs").insert({actor_id:user.id,action:"franchise_invoice_pix_paid",entity:"franchise_invoices",entity_id:invoice.id,metadata:{franchise_id:franchiseId,invoice_id:invoice.id,txid:charge.txid,amount:charge.amount,end_to_end_id:endToEnd,auto_reactivated:autoReactivate,source:role==="super_admin"?"matrix":"franchise"}});
   }
   return {error:false,charge:updated.data||{...charge,...update},provider_status:providerStatus,paid:local==="paid"};
  };

  const {data:existing}=await admin.from("franchise_invoice_pix_charges").select("*").eq("invoice_id",invoice.id).order("created_at",{ascending:false}).limit(1).maybeSingle();
  if(action==="status"){
   if(!existing)return json({paid:false,invoice,summary,charge:null,sandbox});
   const synced=await syncCharge(existing as ChargeRow);
   if(synced.error)return json({error:"Falha ao consultar cobrança na Efí",provider_status:synced.status,provider_error:providerError(synced.provider),charge:existing},502);
   return json({paid:synced.paid,invoice:{...invoice,status:synced.paid?"paid":invoice.status},summary,charge:synced.charge,sandbox});
  }

  if(existing&&existing.status==="active"){
   if(Math.abs(money(existing.amount)-total)>0.009)return json({error:"A fatura mudou depois da geração do Pix. Encerre ou deixe expirar a cobrança atual antes de gerar outra.",charge:existing,summary},409);
   const synced=await syncCharge(existing as ChargeRow);
   if(!synced.error&&["active","paid"].includes(String(synced.charge?.status)))return json({reused:true,paid:synced.paid,invoice,summary,charge:synced.charge,sandbox});
  }

  const now=Date.now();
  const dueTime=due?Date.parse(`${due}T23:59:59-03:00`):now+7*86400000;
  const expiration=Math.max(3600,Math.min(7*86400,Math.floor((Math.max(dueTime,now+3600000)-now)/1000)));
  const createRes=await fetch(`${base}/v2/cob`,{method:"POST",client,headers:providerHeaders,body:JSON.stringify({calendario:{expiracao:expiration},valor:{original:total.toFixed(2)},chave:pixKey,solicitacaoPagador:`CLICK-GO ${String(summary.franchise_name||"")} ${reference.slice(0,7)}`.slice(0,140)})});
  const created=await createRes.json().catch(()=>({}));
  if(!createRes.ok)return json({error:"A Efí recusou a criação da cobrança Pix",provider_status:createRes.status,provider_error:providerError(created)},502);
  const locationId=created?.loc?.id??null;
  let qr:any={};
  if(locationId){const qrRes=await fetch(`${base}/v2/loc/${locationId}/qrcode`,{method:"GET",client,headers:providerHeaders});qr=await qrRes.json().catch(()=>({}));if(!qrRes.ok)qr={provider_error:providerError(qr),provider_status:qrRes.status};}
  const chargePayload={invoice_id:invoice.id,franchise_id:franchiseId,created_by:user.id,provider:"efi",txid:String(created?.txid||""),location_id:locationId,location:created?.location||created?.loc?.location||null,qrcode:qr?.qrcode||created?.pixCopiaECola||null,qrcode_image:qr?.imagemQrcode||null,visualization_link:qr?.linkVisualizacao||null,amount:total,status:"active",provider_status:String(created?.status||"ATIVA"),expires_at:new Date(now+expiration*1000).toISOString(),raw_response:{charge:created,qrcode:qr}};
  if(!chargePayload.txid)return json({error:"A Efí criou a cobrança sem txid reconhecível",provider_response:providerError(created)},502);
  const inserted=await admin.from("franchise_invoice_pix_charges").insert(chargePayload).select("*").single();
  if(inserted.error)return json({error:inserted.error.message},500);
  await admin.from("audit_logs").insert({actor_id:user.id,action:"franchise_invoice_pix_created",entity:"franchise_invoices",entity_id:invoice.id,metadata:{franchise_id:franchiseId,invoice_id:invoice.id,charge_id:inserted.data.id,txid:chargePayload.txid,amount:total,reference_month:reference,source:role==="super_admin"?"matrix":"franchise"}});
  return json({created:true,paid:false,invoice,summary,charge:inserted.data,sandbox},201);
 }catch(error){console.error(error);return json({error:error instanceof Error?error.message:"Falha inesperada na cobrança Pix"},500)}
});
