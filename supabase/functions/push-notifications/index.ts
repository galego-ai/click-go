import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json"}});
const b64url=(bytes:Uint8Array|string)=>{const raw=typeof bytes==='string'?new TextEncoder().encode(bytes):bytes;let s='';for(const b of raw)s+=String.fromCharCode(b);return btoa(s).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'')};

async function googleAccessToken(sa:any){
  const now=Math.floor(Date.now()/1000);
  const head=b64url(JSON.stringify({alg:'RS256',typ:'JWT'}));
  const payload=b64url(JSON.stringify({iss:sa.client_email,scope:'https://www.googleapis.com/auth/firebase.messaging',aud:'https://oauth2.googleapis.com/token',iat:now,exp:now+3600}));
  const input=`${head}.${payload}`;
  const pem=String(sa.private_key||'').replace('-----BEGIN PRIVATE KEY-----','').replace('-----END PRIVATE KEY-----','').replace(/\s/g,'');
  const der=Uint8Array.from(atob(pem),c=>c.charCodeAt(0));
  const key=await crypto.subtle.importKey('pkcs8',der.buffer,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
  const sig=new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,new TextEncoder().encode(input)));
  const assertion=`${input}.${b64url(sig)}`;
  const res=await fetch('https://oauth2.googleapis.com/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion})});
  const data=await res.json();
  if(!res.ok||!data.access_token)throw new Error(`Google OAuth: ${data.error_description||data.error||res.status}`);
  return data.access_token as string;
}

Deno.serve(async(req:Request)=>{
  if(req.method!=='POST')return json({error:'method_not_allowed'},405);

  const url=Deno.env.get('SUPABASE_URL')!;
  const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const supabase=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});

  const supplied=req.headers.get('x-clickgo-internal-secret')||'';
  const{data:secretRow}=await supabase.from('app_internal_secrets').select('value').eq('key','push_dispatch_secret').maybeSingle();
  if(!secretRow?.value||supplied!==secretRow.value)return json({error:'unauthorized'},401);

  let body:any={};
  try{body=await req.json()}catch{return json({error:'invalid_json'},400)}
  const notificationId=Number(body.notification_id);
  if(!Number.isFinite(notificationId))return json({error:'notification_id_required'},400);

  const{data:n,error:ne}=await supabase
    .from('user_notifications')
    .select('id,user_id,ride_id,type,title,body,data')
    .eq('id',notificationId)
    .maybeSingle();

  if(ne||!n){
    await supabase.from('push_delivery_queue').update({status:'failed',attempts:1,last_error:'Notificação não encontrada',updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    return json({error:'notification_not_found'},404);
  }

  const markSuppressed=async(reason:string)=>{
    const payload={status:'suppressed',attempts:1,sent_count:0,failed_count:0,last_error:reason.slice(0,1500),updated_at:new Date().toISOString()};
    const{error}=await supabase.from('push_delivery_queue').update(payload).eq('notification_id',notificationId);
    if(error){
      await supabase.from('push_delivery_queue').update({status:'failed',attempts:1,last_error:`suppressed:${reason}`.slice(0,1500),updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    }
  };

  let deliveryAppKind:string|null=null;
  if(n.ride_id){
    const{data:ride,error:re}=await supabase
      .from('rides')
      .select('passenger_id,driver_id,status')
      .eq('id',n.ride_id)
      .maybeSingle();

    const active=!!ride&&!!ride.driver_id&&['accepted','driver_arriving','in_progress'].includes(String(ride.status));
    const participant=!!ride&&(n.user_id===ride.passenger_id||n.user_id===ride.driver_id);

    if(re||!active||!participant){
      await markSuppressed('ride_not_active_or_recipient_not_participant');
      return json({status:'suppressed',reason:'ride_not_active_or_recipient_not_participant'});
    }

    deliveryAppKind=n.user_id===ride.driver_id?'driver':'passenger';
  }else if(String(n.type||'')==='management_broadcast'){
    const candidate=String(n.data?.target_app||'').toLowerCase();
    if(!['driver','passenger'].includes(candidate)){
      await markSuppressed('management_broadcast_without_valid_target_app');
      return json({status:'suppressed',reason:'management_broadcast_without_valid_target_app'});
    }
    deliveryAppKind=candidate;
  }

  let tokenQuery=supabase
    .from('device_push_tokens')
    .select('id,token,app_kind,platform')
    .eq('user_id',n.user_id)
    .eq('active',true);
  if(deliveryAppKind)tokenQuery=tokenQuery.eq('app_kind',deliveryAppKind);

  const{data:tokens,error:te}=await tokenQuery;
  if(te)return json({error:te.message},500);
  if(!tokens?.length){
    await supabase.from('push_delivery_queue').update({status:'no_devices',attempts:1,updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    return json({status:'no_devices'});
  }

  const raw=Deno.env.get('FCM_SERVICE_ACCOUNT_JSON');
  if(!raw){
    await supabase.from('push_delivery_queue').update({status:'pending_fcm_configuration',attempts:1,last_error:'FCM_SERVICE_ACCOUNT_JSON não configurado',updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    return json({status:'pending_fcm_configuration'});
  }

  let sa:any;
  try{sa=JSON.parse(raw)}catch{
    await supabase.from('push_delivery_queue').update({status:'failed',attempts:1,last_error:'FCM_SERVICE_ACCOUNT_JSON inválido',updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    return json({error:'invalid_fcm_service_account'},500);
  }

  try{
    const access=await googleAccessToken(sa);
    let sent=0,failed=0;
    const errors:string[]=[];

    for(const t of tokens){
      const data:Record<string,string>={
        type:String(n.type||''),
        notification_id:String(n.id),
        ride_id:n.ride_id?String(n.ride_id):'',
        title:String(n.title||''),
        body:String(n.body||'')
      };
      if(n.data&&typeof n.data==='object'){
        for(const[k,v]of Object.entries(n.data))data[k]=typeof v==='string'?v:JSON.stringify(v);
      }

      const android:any={priority:'high',notification:{channel_id:'clickgo_updates',sound:'default'}};
      // Comunicação de corrida é efêmera. Campanhas administrativas não usam TTL 0
      // e podem chegar normalmente ao usuário quando o aparelho voltar à rede.
      if(n.ride_id)android.ttl='0s';

      const message={token:t.token,notification:{title:n.title,body:n.body},data,android};
      const res=await fetch(`https://fcm.googleapis.com/v1/projects/${encodeURIComponent(sa.project_id)}/messages:send`,{
        method:'POST',
        headers:{authorization:`Bearer ${access}`,'content-type':'application/json'},
        body:JSON.stringify({message})
      });

      const txt=await res.text();
      if(res.ok){
        sent++;
      }else{
        failed++;
        errors.push(`${res.status}:${txt.slice(0,220)}`);
        if(txt.includes('UNREGISTERED')||txt.includes('registration-token-not-registered')){
          await supabase.from('device_push_tokens').update({active:false,updated_at:new Date().toISOString()}).eq('id',t.id);
        }
      }
    }

    await supabase.from('push_delivery_queue').update({
      status:failed===0?'sent':sent>0?'partial':'failed',
      attempts:1,
      sent_count:sent,
      failed_count:failed,
      last_error:errors.length?errors.join(' | ').slice(0,1500):null,
      updated_at:new Date().toISOString()
    }).eq('notification_id',notificationId);

    return json({status:failed===0?'sent':sent>0?'partial':'failed',sent,failed,ride_scoped:!!n.ride_id,app_kind:deliveryAppKind});
  }catch(e){
    const m=e instanceof Error?e.message:String(e);
    await supabase.from('push_delivery_queue').update({status:'failed',attempts:1,last_error:m.slice(0,1500),updated_at:new Date().toISOString()}).eq('notification_id',notificationId);
    return json({error:m},500);
  }
});
