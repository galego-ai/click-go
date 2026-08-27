import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {createClient} from "jsr:@supabase/supabase-js@2.112.4";

const cors={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Headers":"authorization, x-client-info, apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS"};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,"Content-Type":"application/json"}});
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
const money=(v:unknown)=>Number(v||0);
const monthStart=(v:string)=>/^\d{4}-\d{2}(-01)?$/.test(v)?`${v.slice(0,7)}-01`:null;
const providerError=(body:any)=>({code:body?.code??body?.error??null,message:body?.error_description??body?.message??body?.data?.message??null});
const addDays=(iso:string,days:number)=>{const d=new Date(`${iso}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10)};
type CardRow={id:string;invoice_id:string;franchise_id:string;charge_id:number;payment_url:string;amount:number;status:string;provider_status:string|null;paid_at:string|null;created_at:string};

Deno.serve(async req=>{
 if(req.method==="OPTIONS")return new Response("ok",{headers:cors});
 try{
  if(req.method!=="POST")return json({error:"Método não permitido"},405);
  const url=Deno.env.get("SUPABASE_URL")||"",service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
  if(!url||!service)return json({error:"Supabase interno não configurado"},500);
  const authHeader=req.headers.get("Authorization")||"",token=authHeader.replace(/^Bearer\s+/i,"");
  if(!token)return json({error:"Não autenticado"},401);
  const admin=createClient(url,service),{data:userData,error:userError}=await admin.auth.getUser(token),user=userData?.user;
  if(userError||!user)return json({error:"Sessão inválida"},401);
  const{data:profile}=await admin.from("profiles").select("id,role,franchise_id,email").eq("id",user.id).maybeSingle();
  const role=String(user.app_metadata?.role||profile?.role||"");
  if(!["super_admin","franchise_admin","operator"].includes(role))return json({error:"Acesso não autorizado"},403);

  const body=await req.json().catch(()=>({})),action=String(body?.action||"status");
  if(!["create","status"].includes(action))return json({error:"Ação inválida"},400);
  const reference=monthStart(String(body?.reference_month||new Date().toISOString().slice(0,7)));
  if(!reference)return json({error:"Mês de referência inválido"},400);
  let franchiseId=String(body?.franchise_id||"");
  if(role==="franchise_admin"||role==="operator")franchiseId=String(profile?.franchise_id||user.app_metadata?.franchise_id||"");
  if(!franchiseId)return json({error:"Franquia não identificada"},400);
  if(role==="operator"){
   const{data:staff}=await admin.from("franchise_staff_permissions").select("permissions").eq("profile_id",user.id).maybeSingle();
   if(!staff?.permissions?.finance)return json({error:"Sem permissão financeira"},403);
  }

  const materialized=await admin.rpc("materialize_franchise_invoice",{p_franchise_id:franchiseId,p_reference_month:reference});
  if(materialized.error)return json({error:materialized.error.message},500);
  if(!materialized.data)return json({error:"Nenhuma fatura disponível para este período"},400);
  const userClient=createClient(url,service,{global:{headers:{Authorization:authHeader}}});
  const{data:summary,error:summaryError}=await userClient.rpc("get_franchise_billing_summary",{p_franchise_id:franchiseId,p_reference_month:reference});
  if(summaryError)return json({error:summaryError.message},400);
  if(!summary?.has_plan)return json({error:"Nenhum plano contratado neste período"},400);
  const total=money(summary.total_due);
  if(total<=0)return json({error:"A fatura não possui saldo a pagar",summary},400);
  const{data:invoice,error:invoiceError}=await admin.from("franchise_invoices").select("*").eq("id",materialized.data).single();
  if(invoiceError||!invoice)return json({error:invoiceError?.message||"Fatura não encontrada"},500);
  if(invoice.status==="paid")return json({paid:true,invoice,summary,charge:null});

  const{data:existing}=await admin.from("franchise_invoice_card_charges").select("*").eq("invoice_id",invoice.id).order("created_at",{ascending:false}).limit(1).maybeSingle();
  if(action==="status"&&!existing)return json({paid:false,invoice,summary,charge:null});
  if(action==="create"){
   const{data:pixActive}=await admin.from("franchise_invoice_pix_charges").select("id,txid,status").eq("invoice_id",invoice.id).eq("status","active").limit(1).maybeSingle();
   if(pixActive)return json({error:"Esta fatura já possui um Pix ativo. Pague ou aguarde a expiração do Pix antes de gerar cobrança por cartão.",conflict:"pix",pix:pixActive},409);
  }

  const clientId=(Deno.env.get("EFI_BILLING_CLIENT_ID")||Deno.env.get("EFI_CLIENT_ID")||"").trim();
  const clientSecret=(Deno.env.get("EFI_BILLING_CLIENT_SECRET")||Deno.env.get("EFI_CLIENT_SECRET")||"").trim();
  if(!clientId||!clientSecret)return json({error:"API de Emissão de cobranças da Efí não configurada"},503);
  const sandbox=(Deno.env.get("EFI_BILLING_SANDBOX")||Deno.env.get("EFI_SANDBOX"))==="true";
  const base=sandbox?"https://cobrancas-h.api.efipay.com.br":"https://cobrancas.api.efipay.com.br";
  const oauthRes=await fetch(`${base}/v1/authorize`,{method:"POST",headers:{Authorization:`Basic ${b64(`${clientId}:${clientSecret}`)}`,"Content-Type":"application/json","Accept-Encoding":"identity"},body:JSON.stringify({grant_type:"client_credentials"})});
  const oauthBody=await oauthRes.json().catch(()=>({}));
  if(!oauthRes.ok||!oauthBody?.access_token)return json({error:"Falha ao autenticar na API Cobranças da Efí",provider_status:oauthRes.status,provider_error:providerError(oauthBody)},502);
  const headers={Authorization:`Bearer ${oauthBody.access_token}`,"Content-Type":"application/json","Accept-Encoding":"identity"};

  const markPaid=async(charge:CardRow,paidAt:string|null)=>{
   const marked=await admin.rpc("mark_franchise_invoice_paid",{p_invoice_id:invoice.id,p_paid_at:paidAt,p_actor_id:user.id,p_source:role==="super_admin"?"matrix":"franchise",p_method:"card",p_provider_ref:String(charge.charge_id)});
   if(marked.error)throw new Error(marked.error.message);return marked.data;
  };
  const syncCharge=async(charge:CardRow)=>{
   const res=await fetch(`${base}/v1/charge/${encodeURIComponent(String(charge.charge_id))}`,{method:"GET",headers});
   const provider=await res.json().catch(()=>({}));
   if(!res.ok){await admin.from("franchise_invoice_card_charges").update({provider_status:`HTTP_${res.status}`,raw_response:provider,updated_at:new Date().toISOString()}).eq("id",charge.id);return {error:true,status:res.status,provider};}
   const data=provider?.data||{},providerStatus=String(data?.status||"").toLowerCase();
   let local="active";if(["paid","settled"].includes(providerStatus))local="paid";else if(providerStatus==="canceled")local="cancelled";else if(providerStatus==="expired")local="expired";else if(providerStatus==="unpaid")local="unpaid";
   const paidAt=data?.payment?.paid_at||((local==="paid")?new Date().toISOString():null),paymentUrl=data?.payment_url||data?.link||charge.payment_url;
   const updated=await admin.from("franchise_invoice_card_charges").update({status:local,provider_status:providerStatus||charge.provider_status,payment_url:paymentUrl,paid_at:paidAt,raw_response:provider,updated_at:new Date().toISOString()}).eq("id",charge.id).select("*").single();
   let paymentResult=null;if(local==="paid"&&charge.status!=="paid")paymentResult=await markPaid(charge,paidAt);
   return {error:false,charge:updated.data||{...charge,status:local,provider_status:providerStatus,payment_url:paymentUrl,paid_at:paidAt},paid:local==="paid",payment_result:paymentResult};
  };

  if(action==="status"){
   const synced=await syncCharge(existing as CardRow);
   if(synced.error)return json({error:"Falha ao consultar cobrança por cartão na Efí",provider_status:synced.status,provider_error:providerError(synced.provider),charge:existing},502);
   return json({paid:synced.paid,invoice:{...invoice,status:synced.paid?"paid":invoice.status},summary,charge:synced.charge,sandbox,payment_result:synced.payment_result});
  }
  if(existing&&existing.status==="active"){
   if(Math.abs(money(existing.amount)-total)>0.009)return json({error:"A fatura mudou depois da geração do link de cartão. Aguarde a cobrança atual encerrar antes de gerar outra.",charge:existing,summary},409);
   const synced=await syncCharge(existing as CardRow);
   if(!synced.error&&["active","paid"].includes(String(synced.charge?.status)))return json({reused:true,paid:synced.paid,invoice,summary,charge:synced.charge,sandbox,payment_result:synced.payment_result});
  }

  const{data:billing}=await admin.from("franchise_billing_profiles").select("email").eq("franchise_id",franchiseId).maybeSingle();
  const{data:franchise}=await admin.from("franchises").select("trade_name,contact_email").eq("id",franchiseId).single();
  const email=String(billing?.email||franchise?.contact_email||profile?.email||"").trim().toLowerCase();
  if(!email||!email.includes("@"))return json({error:"Cadastre um e-mail válido na franquia para gerar a cobrança por cartão."},422);
  const today=new Date().toISOString().slice(0,10),expireAt=invoice.due_date&&invoice.due_date>=today?invoice.due_date:addDays(today,1);
  const payload={items:[{name:`Fatura CLICK-GO ${reference.slice(0,7)}`,value:Math.max(1,Math.round(total*100)),amount:1}],metadata:{custom_id:`CLICKGO-${invoice.id}`},customer:{email},settings:{payment_method:"credit_card",expire_at:expireAt,request_delivery_address:false,message:`Fatura CLICK-GO ${reference.slice(0,7)}`}};
  const createRes=await fetch(`${base}/v1/charge/one-step/link`,{method:"POST",headers,body:JSON.stringify(payload)}),created=await createRes.json().catch(()=>({}));
  if(!createRes.ok||created?.code!==200||!created?.data?.charge_id||!created?.data?.payment_url)return json({error:"A Efí recusou a criação do link de pagamento por cartão",provider_status:createRes.status,provider_error:providerError(created)},502);
  const data=created.data,chargePayload={invoice_id:invoice.id,franchise_id:franchiseId,created_by:user.id,provider:"efi",charge_id:Number(data.charge_id),payment_url:String(data.payment_url),amount:total,status:"active",provider_status:String(data.status||"link").toLowerCase(),raw_response:created,updated_at:new Date().toISOString()};
  const inserted=await admin.from("franchise_invoice_card_charges").insert(chargePayload).select("*").single();if(inserted.error)return json({error:inserted.error.message},500);
  await admin.from("audit_logs").insert({actor_id:user.id,action:"franchise_invoice_card_link_created",entity:"franchise_invoices",entity_id:invoice.id,metadata:{franchise_id:franchiseId,invoice_id:invoice.id,card_charge_id:inserted.data.id,charge_id:chargePayload.charge_id,amount:total,reference_month:reference,source:role==="super_admin"?"matrix":"franchise"}});
  return json({created:true,paid:false,invoice,summary,charge:inserted.data,sandbox},201);
 }catch(error){console.error(error);return json({error:error instanceof Error?error.message:"Falha inesperada na cobrança por cartão"},500)}
});