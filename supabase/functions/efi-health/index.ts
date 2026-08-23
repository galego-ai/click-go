import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json"}});
const required=["EFI_CLIENT_ID","EFI_CLIENT_SECRET","EFI_CERT_PEM","EFI_KEY_PEM","EFI_PIX_KEY"];
const b64=(v:string)=>btoa(unescape(encodeURIComponent(v)));
const cleanProviderError=(body:any)=>({
  nome: typeof body?.nome==="string"?body.nome:null,
  name: typeof body?.name==="string"?body.name:null,
  mensagem: typeof body?.mensagem==="string"?body.mensagem:null,
  message: typeof body?.message==="string"?body.message:null,
  erro: typeof body?.erro==="string"?body.erro:null,
  error: typeof body?.error==="string"?body.error:null,
});

Deno.serve(async(req)=>{
  try{
    const url=Deno.env.get("SUPABASE_URL")||"";
    const service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
    if(!url||!service)return json({ok:false,error:"Supabase interno não configurado"},500);
    const admin=createClient(url,service);
    const supplied=req.headers.get("x-clickgo-internal-secret")||"";
    const {data:secretRow}=await admin.from("app_internal_secrets").select("value").eq("key","push_dispatch_secret").maybeSingle();
    if(!supplied||!secretRow?.value||supplied!==secretRow.value)return json({ok:false,error:"Não autorizado"},401);

    const missing=required.filter(name=>!(Deno.env.get(name)||"").trim());
    const sandbox=Deno.env.get("EFI_SANDBOX")==="true";
    if(missing.length)return json({ok:false,configured:false,oauth_ok:false,sandbox,missing});

    const id=Deno.env.get("EFI_CLIENT_ID")!;
    const secret=Deno.env.get("EFI_CLIENT_SECRET")!;
    const certChain=Deno.env.get("EFI_CERT_PEM")!;
    const privateKey=Deno.env.get("EFI_KEY_PEM")!;
    const base=sandbox?"https://pix-h.api.efipay.com.br":"https://pix.api.efipay.com.br";
    const client=Deno.createHttpClient({certChain,privateKey});
    const response=await fetch(`${base}/oauth/token`,{method:"POST",client,headers:{Authorization:`Basic ${b64(`${id}:${secret}`)}`,"Content-Type":"application/json","Accept-Encoding":"identity"},body:JSON.stringify({grant_type:"client_credentials"})});
    const body=await response.json().catch(()=>({}));
    if(!response.ok)return json({ok:false,configured:true,oauth_ok:false,sandbox,provider_status:response.status,provider_error:cleanProviderError(body)});
    return json({ok:true,configured:true,oauth_ok:Boolean(body?.access_token),sandbox,provider_status:response.status});
  }catch(error){
    console.error(error);
    return json({ok:false,configured:true,oauth_ok:false,error:error instanceof Error?error.message:"Falha no health-check Efí"},500);
  }
});
