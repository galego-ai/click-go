import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2.112.4";

const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json"}});
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
const digits=(v:unknown)=>String(v??"").replace(/\D/g,"");
const money=(v:unknown)=>Number(v||0);
const monthStart=(v:string)=>/^\d{4}-\d{2}(-01)?$/.test(v)?`${v.slice(0,7)}-01`:null;
const providerError=(body:any)=>({code:body?.code??body?.error??null,message:body?.error_description??body?.message??body?.data?.message??null});
const addDays=(iso:string,days:number)=>{const d=new Date(`${iso}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10)};

type BillingProfile={franchise_id:string;payer_type:"cpf"|"cnpj";name:string|null;corporate_name:string|null;document:string;email:string;phone:string;street:string;number:string;neighborhood:string;zipcode:string;city:string;state:string;complement:string|null};
type BolixRow={id:string;invoice_id:string;franchise_id:string;charge_id:number;barcode:string|null;pix_qrcode:string|null;pix_qrcode_image:string|null;link:string|null;pdf_url:string|null;amount:number;status:string;provider_status:string|null;due_date:string|null;paid_at:string|null;created_at:string};

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
  const {data:profile}=await admin.from("profiles").select("id,role,franchise_id").eq("id",user.id).maybeSingle();
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

  const {data:existing}=await admin.from("franchise_invoice_bolix_charges").select("*").eq("invoice_id",invoice.id).order("created_at",{ascending:false}).limit(1).maybeSingle();
  if(action==="status"&&!existing)return json({paid:false,invoice,summary,charge:null});
  if(action==="create"){
   const {data:activePix}=await admin.from("franchise_invoice_pix_charges").select("id,txid,status").eq("invoice_id",invoice.id).eq("status","active").order("created_at",{ascending:false}).limit(1).maybeSingle();
   if(activePix)return json({error:"Existe um Pix ativo para esta fatura. Use essa cobrança ou aguarde expirar/cancelar antes de emitir boleto/Bolix.",payment_channel:"pix",txid:activePix.txid},409);
  }

  let bp:BillingProfile|null=null;
  if(action==="create"){
   const {data:billing,error:billingError}=await admin.from("franchise_billing_profiles").select("franchise_id,payer_type,name,corporate_name,document,email,phone,street,number,neighborhood,zipcode,city,state,complement").eq("franchise_id",franchiseId).maybeSingle();
   if(billingError)return json({error:billingError.message},500);
   bp=billing as BillingProfile|null;
   const complete=Boolean(bp&&bp.document&&bp.email&&bp.phone&&bp.street&&bp.number&&bp.neighborhood&&bp.zipcode&&bp.city&&bp.state&&((bp.payer_type==="cpf"&&bp.name)||(bp.payer_type==="cnpj"&&bp.corporate_name)));
   if(!complete)return json({error:"Complete os dados fiscais e o endereço para emitir o boleto.",billing_profile_required:true},422);
  }

  const clientId=(Deno.env.get("EFI_BILLING_CLIENT_ID")||Deno.env.get("EFI_CLIENT_ID")||"").trim();
  const clientSecret=(Deno.env.get("EFI_BILLING_CLIENT_SECRET")||Deno.env.get("EFI_CLIENT_SECRET")||"").trim();
  if(!clientId||!clientSecret)return json({error:"API Cobranças/Bolix da Efí não configurada",missing:[!clientId?"EFI_BILLING_CLIENT_ID/EFI_CLIENT_ID":null,!clientSecret?"EFI_BILLING_CLIENT_SECRET/EFI_CLIENT_SECRET":null].filter(Boolean)},503);
  const sandbox=(Deno.env.get("EFI_BILLING_SANDBOX")||Deno.env.get("EFI_SANDBOX"))==="true";
  const base=sandbox?"https://cobrancas-h.api.efipay.com.br":"https://cobrancas.api.efipay.com.br";
  const oauthRes=await fetch(`${base}/v1/authorize`,{method:"POST",headers:{Authorization:`Basic ${b64(`${clientId}:${clientSecret}`)}`,"Content-Type":"application/json","Accept-Encoding":"identity"},body:JSON.stringify({grant_type:"client_credentials"})});
  const oauthBody=await oauthRes.json().catch(()=>({}));
  if(!oauthRes.ok||!oauthBody?.access_token)return json({error:"Falha ao autenticar na API Cobranças da Efí",provider_status:oauthRes.status,provider_error:providerError(oauthBody)},502);
  const providerHeaders={Authorization:`Bearer ${oauthBody.access_token}`,"Content-Type":"application/json","Accept-Encoding":"identity"};

  const reactivateIfAllowed=async(charge:BolixRow,paidAt:string|null)=>{
   const {data:rule}=await admin.from("franchise_collection_rules").select("auto_reactivate_on_payment").eq("franchise_id",franchiseId).maybeSingle();
   const autoReactivate=rule?.auto_reactivate_on_payment!==false;
   await admin.from("franchise_invoices").update({status:"paid",paid_at:paidAt||new Date().toISOString()}).eq("id",invoice.id);
   if(autoReactivate){
    await admin.from("franchises").update({license_status:"active",active:true,blocked_at:null,blocked_reason:null,updated_at:new Date().toISOString()}).eq("id",franchiseId).neq("license_status","cancelled");
    await admin.from("franchise_subscriptions").update({license_status:"active",updated_at:new Date().toISOString()}).eq("franchise_id",franchiseId).eq("status","active");
   }
   if(charge.status!=="paid")await admin.from("audit_logs").insert({actor_id:user.id,action:"franchise_invoice_bolix_paid",entity:"franchise_invoices",entity_id:invoice.id,metadata:{franchise_id:franchiseId,invoice_id:invoice.id,charge_id:charge.charge_id,amount:charge.amount,auto_reactivated:autoReactivate,source:role==="super_admin"?"matrix":"franchise"}});
   return autoReactivate;
  };

  const syncCharge=async(charge:BolixRow)=>{
   const res=await fetch(`${base}/v1/charge/${encodeURIComponent(String(charge.charge_id))}`,{method:"GET",headers:providerHeaders});
   const body=await res.json().catch(()=>({}));
   if(!res.ok){await admin.from("franchise_invoice_bolix_charges").update({provider_status:`HTTP_${res.status}`,raw_response:body,updated_at:new Date().toISOString()}).eq("id",charge.id);return {error:true,status:res.status,provider:body};}
   const data=body?.data||{};
   const providerStatus=String(data?.status||"").toLowerCase();
   let local="active";
   if(["paid","settled"].includes(providerStatus))local="paid";
   else if(providerStatus==="canceled")local="cancelled";
   else if(providerStatus==="expired")local="expired";
   const banking=data?.payment?.banking_billet||{};
   const paidAt=data?.payment?.paid_at||data?.payment?.received_by_bank_at||((local==="paid")?new Date().toISOString():null);
   const update:any={status:local,provider_status:providerStatus||charge.provider_status,barcode:banking?.barcode||charge.barcode,link:banking?.link||charge.link,pdf_url:banking?.pdf?.charge||charge.pdf_url,pix_qrcode:data?.payment?.pix?.qrcode||charge.pix_qrcode,pix_qrcode_image:data?.payment?.pix?.qrcode_image||charge.pix_qrcode_image,raw_response:body,updated_at:new Date().toISOString()};
   if(paidAt)update.paid_at=paidAt;
   const updated=await admin.from("franchise_invoice_bolix_charges").update(update).eq("id",charge.id).select("*").single();
   let autoReactivate=false;
   if(local==="paid")autoReactivate=await reactivateIfAllowed(charge,paidAt);
   return {error:false,charge:updated.data||{...charge,...update},provider_status:providerStatus,paid:local==="paid",auto_reactivated:autoReactivate};
  };

  if(action==="status"){
   const synced=await syncCharge(existing as BolixRow);
   if(synced.error)return json({error:"Falha ao consultar o boleto na Efí",provider_status:synced.status,provider_error:providerError(synced.provider),charge:existing},502);
   return json({paid:synced.paid,invoice:{...invoice,status:synced.paid?"paid":invoice.status},summary,charge:synced.charge,sandbox,auto_reactivated:synced.auto_reactivated});
  }

  if(existing&&existing.status==="active"){
   if(Math.abs(money(existing.amount)-total)>0.009)return json({error:"A fatura mudou depois da emissão do boleto. Aguarde o vencimento/cancelamento da cobrança atual antes de emitir outra.",charge:existing,summary},409);
   const synced=await syncCharge(existing as BolixRow);
   if(!synced.error&&["active","paid"].includes(String(synced.charge?.status)))return json({reused:true,paid:synced.paid,invoice,summary,charge:synced.charge,sandbox,auto_reactivated:synced.auto_reactivated});
  }

  const today=new Date().toISOString().slice(0,10);
  const effectiveDue=due&&due>today?due:addDays(today,1);
  const customer:any={email:String(bp!.email).trim(),phone_number:digits(bp!.phone),address:{street:String(bp!.street).trim(),number:String(bp!.number).trim(),neighborhood:String(bp!.neighborhood).trim(),zipcode:digits(bp!.zipcode),city:String(bp!.city).trim(),complement:String(bp!.complement||"").trim(),state:String(bp!.state).trim().toUpperCase()}};
  if(bp!.payer_type==="cnpj")customer.juridical_person={corporate_name:String(bp!.corporate_name||"").trim(),cnpj:digits(bp!.document)};
  else{customer.name=String(bp!.name||"").trim();customer.cpf=digits(bp!.document)}
  const cents=Math.max(1,Math.round(total*100));
  const payload={items:[{name:`Fatura CLICK-GO ${reference.slice(0,7)}`,value:cents,amount:1}],metadata:{custom_id:`CLICKGO-${invoice.id}`},payment:{banking_billet:{customer,expire_at:effectiveDue,message:`Fatura CLICK-GO ${reference.slice(0,7)}. Vencimento original: ${due||effectiveDue}.`}}};
  const createRes=await fetch(`${base}/v1/charge/one-step`,{method:"POST",headers:providerHeaders,body:JSON.stringify(payload)});
  const created=await createRes.json().catch(()=>({}));
  if(!createRes.ok||created?.code!==200||!created?.data?.charge_id)return json({error:"A Efí recusou a emissão do boleto/Bolix",provider_status:createRes.status,provider_error:providerError(created)},502);
  const data=created.data;
  const chargePayload={invoice_id:invoice.id,franchise_id:franchiseId,created_by:user.id,provider:"efi",charge_id:Number(data.charge_id),barcode:data.barcode||null,pix_qrcode:data.pix?.qrcode||null,pix_qrcode_image:data.pix?.qrcode_image||null,link:data.billet_link||data.link||null,pdf_url:data.pdf?.charge||null,amount:total,status:"active",provider_status:String(data.status||"waiting").toLowerCase(),due_date:effectiveDue,raw_response:created,updated_at:new Date().toISOString()};
  const inserted=await admin.from("franchise_invoice_bolix_charges").insert(chargePayload).select("*").single();
  if(inserted.error)return json({error:inserted.error.message},500);
  await admin.from("audit_logs").insert({actor_id:user.id,action:"franchise_invoice_bolix_created",entity:"franchise_invoices",entity_id:invoice.id,metadata:{franchise_id:franchiseId,invoice_id:invoice.id,bolix_id:inserted.data.id,charge_id:chargePayload.charge_id,amount:total,reference_month:reference,effective_due_date:effectiveDue,source:role==="super_admin"?"matrix":"franchise"}});
  return json({created:true,paid:false,invoice,summary,charge:inserted.data,sandbox},201);
 }catch(error){console.error(error);return json({error:error instanceof Error?error.message:"Falha inesperada na emissão do boleto"},500)}
});
