import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json"}});
const b64url=(bytes:Uint8Array|string)=>{const raw=typeof bytes==='string'?new TextEncoder().encode(bytes):bytes;let s='';for(const b of raw)s+=String.fromCharCode(b);return btoa(s).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'')};
async function accessToken(sa:any){
  const now=Math.floor(Date.now()/1000),head=b64url(JSON.stringify({alg:'RS256',typ:'JWT'})),payload=b64url(JSON.stringify({iss:sa.client_email,scope:'https://www.googleapis.com/auth/firebase.messaging',aud:'https://oauth2.googleapis.com/token',iat:now,exp:now+3600})),input=`${head}.${payload}`;
  const pem=String(sa.private_key||'').replace('-----BEGIN PRIVATE KEY-----','').replace('-----END PRIVATE KEY-----','').replace(/\s/g,'');
  const der=Uint8Array.from(atob(pem),c=>c.charCodeAt(0));
  const key=await crypto.subtle.importKey('pkcs8',der.buffer,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
  const sig=new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,new TextEncoder().encode(input)));
  const res=await fetch('https://oauth2.googleapis.com/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion:`${input}.${b64url(sig)}`})});
  const data=await res.json();if(!res.ok||!data.access_token)throw new Error(data.error_description||data.error||`Google OAuth ${res.status}`);return true;
}
Deno.serve(async(req)=>{
  try{
    const url=Deno.env.get('SUPABASE_URL')||'',service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
    const supabase=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const supplied=req.headers.get('x-clickgo-internal-secret')||'';
    const{data:secretRow}=await supabase.from('app_internal_secrets').select('value').eq('key','push_dispatch_secret').maybeSingle();
    if(!secretRow?.value||supplied!==secretRow.value)return json({ok:false,error:'unauthorized'},401);
    const raw=Deno.env.get('FCM_SERVICE_ACCOUNT_JSON');
    if(!raw)return json({ok:false,configured:false,oauth_ok:false,error:'FCM_SERVICE_ACCOUNT_JSON não configurado'});
    let sa:any;try{sa=JSON.parse(raw)}catch{return json({ok:false,configured:false,oauth_ok:false,error:'FCM_SERVICE_ACCOUNT_JSON inválido'})}
    const structurallyValid=Boolean(sa?.project_id&&sa?.client_email&&sa?.private_key);
    if(!structurallyValid)return json({ok:false,configured:false,oauth_ok:false,error:'Service account incompleto'});
    try{await accessToken(sa);return json({ok:true,configured:true,oauth_ok:true,project_id:sa.project_id})}
    catch(e){return json({ok:false,configured:true,oauth_ok:false,project_id:sa.project_id,error:e instanceof Error?e.message:'Falha Google OAuth'})}
  }catch(e){return json({ok:false,error:e instanceof Error?e.message:String(e)},500)}
});
