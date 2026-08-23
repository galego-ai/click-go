import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const cors={"access-control-allow-origin":"*","access-control-allow-headers":"authorization, x-client-info, apikey, content-type","access-control-allow-methods":"GET, POST, OPTIONS"};
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{...cors,"content-type":"application/json"}});

Deno.serve(async(req:Request)=>{
  if(req.method==='OPTIONS')return new Response('ok',{headers:cors});
  if(req.method!=='GET'&&req.method!=='POST')return json({error:'method_not_allowed'},405);
  const url=Deno.env.get('SUPABASE_URL');
  const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if(!url||!service)return json({error:'server_configuration_error'},500);
  const authHeader=req.headers.get('authorization')||'';
  const token=authHeader.replace(/^Bearer\s+/i,'').trim();
  if(!token)return json({error:'unauthorized'},401);
  const admin=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
  const{data:userData,error:userError}=await admin.auth.getUser(token);
  if(userError||!userData.user)return json({error:'unauthorized'},401);
  const{data:profile,error:profileError}=await admin.from('profiles').select('role').eq('id',userData.user.id).maybeSingle();
  if(profileError||profile?.role!=='super_admin')return json({error:'forbidden'},403);

  const [{count:activeDevices},{data:queue,error:queueError}]=await Promise.all([
    admin.from('device_push_tokens').select('id',{count:'exact',head:true}).eq('active',true),
    admin.from('push_delivery_queue').select('status')
  ]);
  if(queueError)return json({error:queueError.message},500);
  const counts:Record<string,number>={};
  for(const row of queue||[])counts[row.status]=(counts[row.status]||0)+1;
  const raw=Deno.env.get('FCM_SERVICE_ACCOUNT_JSON')||'';
  let fcmProjectId:string|null=null;
  if(raw){try{const parsed=JSON.parse(raw);fcmProjectId=typeof parsed.project_id==='string'?parsed.project_id:null}catch{}}
  return json({
    fcm_configured:Boolean(raw&&fcmProjectId),
    fcm_project_id:fcmProjectId,
    active_devices:activeDevices||0,
    queue:counts,
    total_queue:(queue||[]).length,
    checked_at:new Date().toISOString()
  });
});
