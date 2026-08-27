import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2.112.4";

const cors={
  "Access-Control-Allow-Origin":"*",
  "Access-Control-Allow-Headers":"authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods":"POST, OPTIONS",
};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,"Content-Type":"application/json"}});
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
const digits=(v:unknown)=>String(v||"").replace(/\D/g,"");
const providerError=(body:any)=>({code:body?.code??body?.error??null,message:body?.error_description??body?.message??body?.data?.message??body?.data?.refusal?.reason??null});

async function billingAuth(){
  const clientId=(Deno.env.get("EFI_BILLING_CLIENT_ID")||Deno.env.get("EFI_CLIENT_ID")||"").trim();
  const clientSecret=(Deno.env.get("EFI_BILLING_CLIENT_SECRET")||Deno.env.get("EFI_CLIENT_SECRET")||"").trim();
  if(!clientId||!clientSecret)throw new Error("Credenciais da API de Cobranças Efí não configuradas");
  const sandbox=(Deno.env.get("EFI_BILLING_SANDBOX")||Deno.env.get("EFI_SANDBOX"))==="true";
  const base=sandbox?"https://cobrancas-h.api.efipay.com.br":"https://cobrancas.api.efipay.com.br";
  const r=await fetch(`${base}/v1/authorize`,{method:"POST",headers:{Authorization:`Basic ${b64(`${clientId}:${clientSecret}`)}`,"Content-Type":"application/json","Accept-Encoding":"identity"},body:JSON.stringify({grant_type:"client_credentials"})});
  const body=await r.json().catch(()=>({}));
  if(!r.ok||!body?.access_token){const e=providerError(body);throw new Error(`Efí Cobranças OAuth ${r.status}: ${e.message||e.code||"falha de autenticação"}`)}
  return {base,sandbox,headers:{Authorization:`Bearer ${body.access_token}`,"Content-Type":"application/json","Accept-Encoding":"identity"}};
}

Deno.serve(async(req)=>{
  if(req.method==="OPTIONS")return new Response("ok",{headers:cors});
  if(req.method!=="POST")return json({error:"Método não permitido"},405);
  try{
    const url=Deno.env.get("SUPABASE_URL")||"",service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
    if(!url||!service)return json({error:"Supabase interno não configurado"},500);
    const admin=createClient(url,service);
    const authHeader=req.headers.get("Authorization")||"";
    const token=authHeader.replace(/^Bearer\s+/i,"");
    if(!token)return json({error:"Não autenticado"},401);
    const {data:userData,error:userError}=await admin.auth.getUser(token);
    const user=userData?.user;
    if(userError||!user)return json({error:"Sessão inválida"},401);
    const {data:profile,error:profileError}=await admin.from("profiles").select("id,role,active,full_name,email,phone,cpf").eq("id",user.id).maybeSingle();
    if(profileError||!profile?.active)return json({error:"Conta inválida ou inativa"},403);

    const input=await req.json().catch(()=>({}));
    const action=String(input?.action||"config");

    if(action==="config"){
      if(profile.role!=="passenger")return json({error:"Acesso exclusivo do passageiro"},403);
      const accountIdentifier=(Deno.env.get("EFI_ACCOUNT_IDENTIFIER")||Deno.env.get("EFI_PAYEE_CODE")||"").trim();
      const sandbox=(Deno.env.get("EFI_BILLING_SANDBOX")||Deno.env.get("EFI_SANDBOX"))==="true";
      return json({configured:Boolean(accountIdentifier),account_identifier:accountIdentifier||null,environment:sandbox?"sandbox":"production"});
    }

    if(action==="save_method"){
      if(profile.role!=="passenger")return json({error:"Acesso exclusivo do passageiro"},403);
      const paymentToken=String(input?.payment_token||"").trim();
      const cardMask=String(input?.card_mask||"").trim();
      const brand=String(input?.brand||"").trim().toLowerCase();
      const last4=digits(cardMask).slice(-4);
      if(paymentToken.length<20||last4.length!==4)return json({error:"Token/cartão retornado pela Efí é inválido"},400);
      if(!["visa","mastercard","master","elo","amex","americanexpress"].includes(brand))return json({error:"Bandeira de cartão não suportada"},400);
      await admin.from("passenger_payment_methods").update({is_default:false}).eq("passenger_id",user.id);
      const inserted=await admin.from("passenger_payment_methods").insert({passenger_id:user.id,method_type:"card",provider:"efi",provider_token:null,brand:brand==="master"?"mastercard":brand==="americanexpress"?"amex":brand,last4,is_default:true,active:true}).select("id,method_type,provider,brand,last4,is_default,active").single();
      if(inserted.error)return json({error:inserted.error.message},400);
      const secured=await admin.from("passenger_card_tokens").upsert({method_id:inserted.data.id,passenger_id:user.id,provider:"efi",provider_token:paymentToken,updated_at:new Date().toISOString()},{onConflict:"method_id"});
      if(secured.error){await admin.from("passenger_payment_methods").delete().eq("id",inserted.data.id);return json({error:"Não foi possível proteger o token do cartão"},500)}
      await admin.from("audit_logs").insert({actor_id:user.id,action:"passenger_card_saved",entity:"passenger_payment_methods",entity_id:inserted.data.id,metadata:{provider:"efi",brand:inserted.data.brand,last4}});
      return json({ok:true,method:inserted.data},201);
    }

    if(action==="delete_method"){
      if(profile.role!=="passenger")return json({error:"Acesso exclusivo do passageiro"},403);
      const methodId=String(input?.method_id||"");
      const {data:method}=await admin.from("passenger_payment_methods").select("id,passenger_id,method_type").eq("id",methodId).maybeSingle();
      if(!method||method.passenger_id!==user.id||method.method_type!=="card")return json({error:"Cartão não encontrado"},404);
      await admin.from("passenger_card_tokens").delete().eq("method_id",methodId).eq("passenger_id",user.id);
      await admin.from("passenger_payment_methods").update({active:false,is_default:false,provider_token:null}).eq("id",methodId);
      await admin.from("audit_logs").insert({actor_id:user.id,action:"passenger_card_removed",entity:"passenger_payment_methods",entity_id:methodId,metadata:{provider:"efi"}});
      return json({ok:true});
    }

    if(action==="charge_ride"){
      const rideId=String(input?.ride_id||"");
      if(!rideId)return json({error:"ride_id obrigatório"},400);
      const {data:ride,error:rideError}=await admin.from("rides").select("id,passenger_id,driver_id,franchise_id,city_id,status,estimated_fare,final_fare,wait_charge_amount,payment_method_preference,payment_method_id").eq("id",rideId).maybeSingle();
      if(rideError||!ride)return json({error:"Corrida não encontrada"},404);
      const allowed=ride.passenger_id===user.id||(profile.role==="driver"&&ride.driver_id===user.id)||profile.role==="super_admin";
      if(!allowed)return json({error:"Sem permissão para cobrar esta corrida"},403);
      if(ride.status!=="completed")return json({error:"O cartão é cobrado somente após a corrida ser concluída"},409);
      if(String(ride.payment_method_preference||"")!=="card")return json({error:"Esta corrida não foi solicitada com cartão no app"},409);
      if(!ride.payment_method_id)return json({error:"A corrida não possui cartão selecionado"},409);

      const {data:existing}=await admin.from("ride_card_charges").select("*").eq("ride_id",ride.id).maybeSingle();
      if(existing?.status==="paid")return json({ok:true,paid:true,reused:true,charge:existing});
      if(existing?.status==="failed"&&profile.role==="driver"&&!input?.retry)return json({ok:false,paid:false,failed:true,charge:existing,error:existing.refusal_reason||"Pagamento recusado. O passageiro precisa tentar novamente."},402);

      const {data:method}=await admin.from("passenger_payment_methods").select("id,passenger_id,provider,brand,last4,active").eq("id",ride.payment_method_id).maybeSingle();
      if(!method||method.passenger_id!==ride.passenger_id||!method.active||method.provider!=="efi")return json({error:"Cartão salvo indisponível"},409);
      const {data:secure}=await admin.from("passenger_card_tokens").select("provider_token").eq("method_id",method.id).eq("passenger_id",ride.passenger_id).maybeSingle();
      if(!secure?.provider_token)return json({error:"Token do cartão não encontrado. Cadastre o cartão novamente."},409);

      const baseAmount=Number(ride.final_fare??ride.estimated_fare??0);
      if(!Number.isFinite(baseAmount)||baseAmount<=0)return json({error:"Valor final da corrida inválido"},400);
      const {data:settings}=await admin.rpc("get_effective_payment_settings",{p_city_id:ride.city_id});
      const paySettings=Array.isArray(settings)?settings[0]:settings;
      const pct=paySettings?.card_fee_bearer==="passenger"?Number(paySettings?.card_surcharge_percentage||0):0;
      const total=Math.round((baseAmount+(baseAmount*pct/100))*100)/100;

      let paymentId=existing?.payment_id||null;
      if(!paymentId){
        const p=await admin.from("payments").insert({ride_id:ride.id,franchise_id:ride.franchise_id,payer_id:ride.passenger_id,beneficiary_id:ride.driver_id,created_by:ride.passenger_id,purpose:"ride",amount:baseAmount,method:"card",status:"pending",provider:"efi"}).select("id").single();
        if(p.error)return json({error:p.error.message},500);
        paymentId=p.data.id;
      }else await admin.from("payments").update({status:"pending",provider:"efi"}).eq("id",paymentId).neq("status","paid");

      if(!existing){
        const c=await admin.from("ride_card_charges").insert({payment_id:paymentId,ride_id:ride.id,passenger_id:ride.passenger_id,method_id:method.id,amount:total,status:"pending",attempts:0}).select("*").single();
        if(c.error)return json({error:c.error.message},500);
      }

      const customerName=String(profile.id===ride.passenger_id?profile.full_name:""||"").trim();
      let customerProfile:any=profile;
      if(profile.id!==ride.passenger_id){const cp=await admin.from("profiles").select("full_name,email,phone,cpf").eq("id",ride.passenger_id).single();customerProfile=cp.data||{};}
      const name=String(customerProfile.full_name||"").trim();
      const cpf=digits(customerProfile.cpf);
      const email=String(customerProfile.email||user.email||"").trim().toLowerCase();
      const phone=digits(customerProfile.phone);
      if(!name||cpf.length!==11||!email.includes("@")||phone.length<10)return json({error:"Complete nome, CPF, e-mail e telefone do passageiro antes de pagar com cartão."},422);

      const {base,headers,sandbox}=await billingAuth();
      const payload={
        items:[{name:`Corrida CLICK-GO ${ride.id.slice(0,8)}`,value:Math.max(1,Math.round(total*100)),amount:1}],
        metadata:{custom_id:`CLICKGO-RIDE-${ride.id}`},
        payment:{credit_card:{customer:{name,cpf,email,phone_number:phone},installments:1,payment_token:secure.provider_token,message:`Corrida CLICK-GO ${ride.id.slice(0,8)}`}}
      };
      const res=await fetch(`${base}/v1/charge/one-step`,{method:"POST",headers,body:JSON.stringify(payload)});
      const body=await res.json().catch(()=>({}));
      const pdata=body?.data||{};
      const providerStatus=String(pdata?.status||"").toLowerCase();
      const chargeId=Number(pdata?.charge_id||0)||null;
      const approved=res.ok&&body?.code===200&&["approved","paid","settled"].includes(providerStatus);
      const refusal=String(pdata?.refusal?.reason||providerError(body).message||"").trim()||null;
      const newStatus=approved?"paid":"failed";
      const paidAt=approved?new Date().toISOString():null;
      const updated=await admin.from("ride_card_charges").update({charge_id:chargeId,amount:total,status:newStatus,provider_status:providerStatus||`HTTP_${res.status}`,refusal_reason:refusal,attempts:Number(existing?.attempts||0)+1,paid_at:paidAt,raw_response:body}).eq("ride_id",ride.id).select("*").single();
      if(approved){
        await admin.from("payments").update({status:"paid",provider_reference:chargeId?String(chargeId):null,paid_at:paidAt}).eq("id",paymentId);
        await admin.from("audit_logs").insert({actor_id:user.id,action:"efi_card_ride_paid",entity:"rides",entity_id:ride.id,metadata:{payment_id:paymentId,charge_id:chargeId,method_id:method.id,base_amount:baseAmount,charged_amount:total,sandbox}});
        return json({ok:true,paid:true,charge:updated.data,base_amount:baseAmount,charged_amount:total,sandbox});
      }
      await admin.from("payments").update({status:"failed",provider_reference:chargeId?String(chargeId):null}).eq("id",paymentId);
      await admin.from("audit_logs").insert({actor_id:user.id,action:"efi_card_ride_failed",entity:"rides",entity_id:ride.id,metadata:{payment_id:paymentId,charge_id:chargeId,method_id:method.id,base_amount:baseAmount,charged_amount:total,provider_status:providerStatus,refusal}});
      return json({ok:false,paid:false,error:refusal||"Pagamento recusado pela Efí",charge:updated.data,provider_status:providerStatus},402);
    }

    return json({error:"Ação inválida"},400);
  }catch(error){
    console.error("efi-card",error);
    return json({error:error instanceof Error?error.message:"Falha inesperada no cartão Efí"},500);
  }
});
