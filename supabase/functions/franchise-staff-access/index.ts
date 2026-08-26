import { createClient } from 'npm:@supabase/supabase-js@2'

const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type'}
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{...cors,'Content-Type':'application/json'}})
const roles=['manager','operator','financial','support','marketing']
const defaults:Record<string,Record<string,boolean>>={
 manager:{operation:true,drivers:true,users:true,pricing:false,finance:true,support:true,marketing:true,reports:true,settings:true},
 operator:{operation:true,drivers:true,users:true,pricing:false,finance:false,support:false,marketing:false,reports:false,settings:false},
 financial:{operation:false,drivers:false,users:false,pricing:false,finance:true,support:false,marketing:false,reports:true,settings:false},
 support:{operation:true,drivers:false,users:true,pricing:false,finance:false,support:true,marketing:false,reports:false,settings:false},
 marketing:{operation:false,drivers:false,users:false,pricing:false,finance:false,support:false,marketing:true,reports:true,settings:false},
}
function tempPassword(){const b=crypto.getRandomValues(new Uint8Array(10));const a='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';let s='';for(const x of b)s+=a[x%a.length];return `Cg!${s}#7`}
function passwordError(v:string){if(v.length<8)return 'A senha deve ter pelo menos 8 caracteres';if(v.length>72)return 'A senha deve ter no máximo 72 caracteres';if(!/[A-Za-z]/.test(v)||!/[0-9]/.test(v))return 'Use letras e números na senha';return null}

Deno.serve(async(req)=>{
 if(req.method==='OPTIONS')return new Response('ok',{headers:cors})
 try{
  const token=(req.headers.get('Authorization')||'').replace(/^Bearer\s+/i,'');if(!token)return json({error:'Não autenticado'},401)
  const admin=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,{auth:{autoRefreshToken:false,persistSession:false}})
  const{data:caller}=await admin.auth.getUser(token);if(!caller.user)return json({error:'Sessão inválida'},401)
  const{data:callerProfile}=await admin.from('profiles').select('role,franchise_id,active').eq('id',caller.user.id).maybeSingle();if(!callerProfile?.active)return json({error:'Perfil inativo'},403)
  const appRole=String(caller.user.app_metadata?.role||callerProfile.role||'');const body=await req.json();const action=String(body.action||'')
  if(action==='complete_change'){
   if(appRole!=='operator')return json({error:'Acesso restrito à equipe regional'},403)
   const password=String(body.new_password||'');const pe=passwordError(password);if(pe)return json({error:pe},400)
   const{data:authUser,error:readError}=await admin.auth.admin.getUserById(caller.user.id);if(readError||!authUser.user)throw readError||new Error('Conta não encontrada')
   const{error:updateError}=await admin.auth.admin.updateUserById(caller.user.id,{password,app_metadata:{...authUser.user.app_metadata,role:'operator',franchise_id:callerProfile.franchise_id,must_change_password:false,temp_password_changed_at:new Date().toISOString()}});if(updateError)throw updateError
   await admin.from('audit_logs').insert({actor_id:caller.user.id,action:'staff_complete_temp_password_change',entity:'profiles',entity_id:caller.user.id,metadata:{franchise_id:callerProfile.franchise_id}})
   return json({ok:true})
  }
  let managerFranchise=''
  if(appRole==='operator'){
   const{data:manager}=await admin.from('franchise_staff_permissions').select('franchise_id,staff_role,active').eq('profile_id',caller.user.id).maybeSingle()
   if(!manager?.active||manager.staff_role!=='manager')return json({error:'Somente o gestor pode administrar a equipe'},403)
   managerFranchise=String(manager.franchise_id||'')
  }else if(!['super_admin','franchise_admin'].includes(appRole))return json({error:'Acesso sem permissão para gerenciar equipe'},403)
  const franchiseId=String(body.franchise_id||callerProfile.franchise_id||managerFranchise||'');if(!franchiseId)return json({error:'Franquia obrigatória'},400)
  if(appRole==='franchise_admin'&&String(callerProfile.franchise_id)!==franchiseId)return json({error:'Você só pode gerenciar sua própria equipe'},403)
  if(appRole==='operator'&&managerFranchise!==franchiseId)return json({error:'Você só pode gerenciar sua própria equipe'},403)
  if(action==='set_active'){
   const profileId=String(body.profile_id||'');const active=Boolean(body.active);if(profileId===caller.user.id&&!active)return json({error:'O gestor não pode desativar a própria conta'},400)
   const{data:staff}=await admin.from('franchise_staff_permissions').select('profile_id,franchise_id').eq('profile_id',profileId).maybeSingle();if(!staff||String(staff.franchise_id)!==franchiseId)return json({error:'Funcionário não encontrado'},404)
   await admin.from('franchise_staff_permissions').update({active,updated_at:new Date().toISOString()}).eq('profile_id',profileId);await admin.from('profiles').update({active,updated_at:new Date().toISOString()}).eq('id',profileId)
   await admin.from('audit_logs').insert({actor_id:caller.user.id,action:active?'activate_franchise_staff':'deactivate_franchise_staff',entity:'profiles',entity_id:profileId,metadata:{franchise_id:franchiseId}})
   return json({ok:true})
  }
  if(action!=='create_or_reset')return json({error:'Ação inválida'},400)
  const email=String(body.email||'').trim().toLowerCase();const fullName=String(body.full_name||'').trim();const staffRole=String(body.staff_role||'operator');if(!email||!fullName)return json({error:'Nome e e-mail são obrigatórios'},400);if(!roles.includes(staffRole))return json({error:'Função inválida'},400)
  if(appRole==='operator'&&staffRole==='manager')return json({error:'Somente o administrador da franquia ou a Matriz pode criar outro gestor'},403)
  const supplied=String(body.temporary_password||'').trim();const password=supplied||tempPassword();const pe=passwordError(password);if(pe)return json({error:pe},400)
  const permissions={...defaults[staffRole],...(body.permissions&&typeof body.permissions==='object'?body.permissions:{})};if(staffRole==='manager')permissions.pricing=false;const issuedAt=new Date().toISOString()
  const{data:existing}=await admin.from('profiles').select('id,email,role,franchise_id').eq('email',email).maybeSingle();let userId=existing?.id||'';let created=false
  if(existing){if(existing.role!=='operator'||String(existing.franchise_id)!==franchiseId)return json({error:'Este e-mail já pertence a outro tipo de conta ou operação'},409);const{data:authUser,error:readError}=await admin.auth.admin.getUserById(existing.id);if(readError||!authUser.user)return json({error:'Conta de login inconsistente'},409);const{error:updateError}=await admin.auth.admin.updateUserById(existing.id,{password,app_metadata:{...authUser.user.app_metadata,role:'operator',franchise_id:franchiseId,staff_role:staffRole,must_change_password:true,temp_password_issued_at:issuedAt}});if(updateError)throw updateError
  }else{const{data:createdUser,error:createError}=await admin.auth.admin.createUser({email,password,email_confirm:true,app_metadata:{role:'operator',franchise_id:franchiseId,staff_role:staffRole,must_change_password:true,temp_password_issued_at:issuedAt},user_metadata:{full_name:fullName}});if(createError)throw createError;userId=createdUser.user.id;created=true}
  const{error:profileError}=await admin.from('profiles').upsert({id:userId,full_name:fullName,email,role:'operator',franchise_id:franchiseId,city_id:null,active:true,updated_at:issuedAt});if(profileError){if(created)await admin.auth.admin.deleteUser(userId);throw profileError}
  const{error:permError}=await admin.from('franchise_staff_permissions').upsert({profile_id:userId,franchise_id:franchiseId,staff_role:staffRole,permissions,active:true,created_by:caller.user.id,updated_at:issuedAt});if(permError)throw permError
  await admin.from('audit_logs').insert({actor_id:caller.user.id,action:created?'create_franchise_staff':'reset_franchise_staff_access',entity:'profiles',entity_id:userId,metadata:{franchise_id:franchiseId,email,staff_role:staffRole,permissions,must_change_password:true}})
  return json({ok:true,user_id:userId,email,temporary_password:password,staff_role:staffRole,permissions,created})
 }catch(e){console.error(e);return json({error:e instanceof Error?e.message:'Erro interno'},400)}
})
