create or replace function public.matrix_active_support_session()
returns jsonb
language plpgsql
stable security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_result jsonb;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.current_active_management_role() is distinct from 'super_admin' then return null; end if;

  select jsonb_build_object(
    'id',s.id,'franchise_id',s.franchise_id,'franchise_name',f.trade_name,'reason',s.reason,
    'started_at',s.started_at,'active',s.active,'cities',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'state',c.state) order by c.name)
      from public.franchise_cities fc join public.cities c on c.id=fc.city_id
      where fc.franchise_id=s.franchise_id
    ),'[]'::jsonb)
  ) into v_result
  from public.franchise_support_sessions s
  join public.franchises f on f.id=s.franchise_id
  where s.matrix_user_id=auth.uid() and s.active
  order by s.started_at desc
  limit 1;

  return v_result;
end;
$function$;

create or replace function public.matrix_create_franchise(
  p_trade_name text,
  p_legal_name text,
  p_document text default null::text,
  p_contact_name text default null::text,
  p_contact_email text default null::text,
  p_contact_phone text default null::text,
  p_territory_type text default 'city'::text,
  p_due_day integer default 10,
  p_plan_id uuid default null::uuid,
  p_reason text default null::text
)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_trade text:=nullif(trim(coalesce(p_trade_name,'')),'');
  v_legal text:=nullif(trim(coalesce(p_legal_name,'')),'');
  v_due integer:=least(28,greatest(1,coalesce(p_due_day,10)));
  v_fid uuid;
  v_plan public.franchise_plans%rowtype;
  v_next_due date;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if v_trade is null or v_legal is null then raise exception 'Nome fantasia e razão social são obrigatórios'; end if;
  if coalesce(p_territory_type,'') not in ('city','multi_city','region') then raise exception 'Tipo de território inválido'; end if;

  if p_plan_id is not null then
    select * into v_plan from public.franchise_plans where id=p_plan_id and active;
    if not found then raise exception 'Plano não encontrado ou inativo'; end if;
  end if;

  perform set_config('app.audit_reason',v_reason,true);

  insert into public.franchises(
    trade_name,legal_name,document,contact_name,contact_email,contact_phone,
    territory_type,due_day,active,license_status,activation_date,next_due_date,onboarding_status
  ) values(
    v_trade,v_legal,nullif(trim(coalesce(p_document,'')),''),nullif(trim(coalesce(p_contact_name,'')),''),
    nullif(trim(coalesce(p_contact_email,'')),''),nullif(trim(coalesce(p_contact_phone,'')),''),
    p_territory_type,v_due,true,case when p_plan_id is null then 'pending' else 'active' end,
    case when p_plan_id is null then null else current_date end,null,'in_progress'
  ) returning id into v_fid;

  if p_plan_id is not null then
    v_next_due:=(date_trunc('month',current_date)+interval '1 month'+((v_due-1)||' days')::interval)::date;
    insert into public.franchise_subscriptions(
      franchise_id,plan_id,status,license_status,matrix_commission_percentage,due_day,next_due_date,starts_at,activated_at
    ) values(
      v_fid,p_plan_id,'active','active',coalesce(v_plan.matrix_commission_percentage,0),v_due,v_next_due,now(),now()
    );
    update public.franchises set next_due_date=v_next_due where id=v_fid;
  end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_created','franchises',v_fid::text,
    jsonb_build_object('franchise_id',v_fid,'trade_name',v_trade,'plan_id',p_plan_id,'due_day',v_due,'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'franchise_id',v_fid,'next_due_date',v_next_due);
end;
$function$;

create or replace function public.matrix_end_support_session(p_session_id uuid default null::uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_session public.franchise_support_sessions%rowtype;
  v_name text;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;

  select * into v_session
  from public.franchise_support_sessions
  where matrix_user_id=auth.uid() and active
    and (p_session_id is null or id=p_session_id)
  order by started_at desc
  limit 1
  for update;

  if not found then return jsonb_build_object('ok',true,'ended',false); end if;

  perform set_config('app.audit_reason',coalesce(v_session.reason,'Encerramento de sessão de suporte'),true);
  update public.franchise_support_sessions set active=false,ended_at=now() where id=v_session.id;
  select trade_name into v_name from public.franchises where id=v_session.franchise_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'support_session_end','franchise_support_sessions',v_session.id::text,
    jsonb_build_object('franchise_id',v_session.franchise_id,'franchise_name',v_name,'session_id',v_session.id,
      'reason',v_session.reason,'source','matrix_support','old_value',jsonb_build_object('active',true,'started_at',v_session.started_at),
      'new_value',jsonb_build_object('active',false,'ended_at',now())));

  return jsonb_build_object('ok',true,'ended',true,'id',v_session.id,'franchise_id',v_session.franchise_id,'franchise_name',v_name);
end;
$function$;

create or replace function public.matrix_extend_franchise_due_date(p_franchise_id uuid, p_days integer, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_invoice uuid;
  v_old_due date;
  v_new_due date;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_days<1 or p_days>180 then raise exception 'Prorrogação deve ser entre 1 e 180 dias'; end if;

  select id,due_date into v_invoice,v_old_due
  from public.franchise_invoices
  where franchise_id=p_franchise_id and status not in ('paid','cancelled')
  order by due_date desc,created_at desc limit 1 for update;
  if v_invoice is null then raise exception 'Nenhuma fatura em aberto encontrada'; end if;

  v_new_due:=v_old_due+p_days;
  perform set_config('app.audit_reason',v_reason,true);
  update public.franchise_invoices set due_date=v_new_due where id=v_invoice;
  update public.franchises set next_due_date=v_new_due,updated_at=now() where id=p_franchise_id;
  update public.franchise_subscriptions set next_due_date=v_new_due,updated_at=now()
   where franchise_id=p_franchise_id and status='active';

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'invoice_due_date_extended','franchise_invoices',v_invoice::text,
    jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('due_date',v_old_due),
      'new_value',jsonb_build_object('due_date',v_new_due,'days_added',p_days),'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'invoice_id',v_invoice,'old_due_date',v_old_due,'new_due_date',v_new_due);
end;
$function$;

create or replace function public.matrix_set_franchise_license(p_franchise_id uuid, p_action text, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_old_status text;
  v_new_status text;
  v_active boolean;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_action not in ('suspend','reactivate','cancel') then raise exception 'Ação inválida'; end if;

  select license_status into v_old_status from public.franchises where id=p_franchise_id and deleted_at is null for update;
  if not found then raise exception 'Franquia não encontrada'; end if;

  if p_action='suspend' then v_new_status:='suspended'; v_active:=false;
  elsif p_action='reactivate' then v_new_status:='active'; v_active:=true;
  else v_new_status:='cancelled'; v_active:=false; end if;

  perform set_config('app.audit_reason',v_reason,true);
  update public.franchises
     set license_status=v_new_status,
         active=v_active,
         blocked_at=case when v_active then null else now() end,
         blocked_reason=case when v_active then null else v_reason end,
         updated_at=now()
   where id=p_franchise_id;

  update public.franchise_subscriptions
     set license_status=v_new_status,
         status=case when p_action='cancel' then 'cancelled' else status end,
         updated_at=now()
   where franchise_id=p_franchise_id and status='active';

  update public.drivers set online=false where franchise_id=p_franchise_id and p_action in ('suspend','cancel');

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'license_'||p_action,'franchises',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('license_status',v_old_status),
      'new_value',jsonb_build_object('license_status',v_new_status,'active',v_active),'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'old_status',v_old_status,'new_status',v_new_status);
end;
$function$;

create or replace function public.matrix_set_franchise_onboarding_step(p_step_id uuid, p_completed boolean, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_step public.franchise_onboarding_steps%rowtype;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  select * into v_step from public.franchise_onboarding_steps where id=p_step_id for update;
  if not found then raise exception 'Etapa de implantação não encontrada'; end if;
  perform set_config('app.audit_reason',v_reason,true);
  update public.franchise_onboarding_steps
     set completed=p_completed,completed_at=case when p_completed then now() else null end,
         completed_by=case when p_completed then auth.uid() else null end,updated_at=now()
   where id=p_step_id;
  update public.franchises f
     set onboarding_status=case
       when not exists(select 1 from public.franchise_onboarding_steps s where s.franchise_id=v_step.franchise_id and s.id<>p_step_id and not s.completed)
            and p_completed then 'completed'
       else 'in_progress' end,
         updated_at=now()
   where f.id=v_step.franchise_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_onboarding_step_updated','franchise_onboarding_steps',p_step_id::text,
    jsonb_build_object('franchise_id',v_step.franchise_id,'step_key',v_step.step_key,'old_completed',v_step.completed,
      'new_completed',p_completed,'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',v_step.franchise_id,'step_id',p_step_id,'completed',p_completed);
end;
$function$;

create or replace function public.matrix_start_support_session(p_franchise_id uuid, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_name text;
  v_enabled boolean;
  v_session public.franchise_support_sessions%rowtype;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Informe o motivo do atendimento de suporte'; end if;

  select trade_name,support_mode_enabled into v_name,v_enabled
  from public.franchises where id=p_franchise_id and deleted_at is null;
  if not found then raise exception 'Franquia não encontrada'; end if;
  if not coalesce(v_enabled,false) then raise exception 'Modo Suporte não está habilitado para esta franquia'; end if;

  perform set_config('app.audit_reason',v_reason,true);
  update public.franchise_support_sessions
     set active=false,ended_at=coalesce(ended_at,now())
   where matrix_user_id=auth.uid() and active;

  insert into public.franchise_support_sessions(franchise_id,matrix_user_id,reason,active,metadata)
  values(p_franchise_id,auth.uid(),v_reason,true,jsonb_build_object('source','matrix_support'))
  returning * into v_session;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'support_session_start','franchise_support_sessions',v_session.id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'franchise_name',v_name,'session_id',v_session.id,
      'reason',v_reason,'source','matrix_support','new_value',jsonb_build_object('active',true,'started_at',v_session.started_at)));

  return jsonb_build_object('id',v_session.id,'franchise_id',p_franchise_id,'franchise_name',v_name,
    'reason',v_reason,'started_at',v_session.started_at,'active',true);
end;
$function$;

create or replace function public.matrix_update_franchise_contract(p_franchise_id uuid, p_status text, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_old text;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_status not in ('pending','signed','expired','cancelled') then raise exception 'Status contratual inválido'; end if;
  select contract_status into v_old from public.franchises where id=p_franchise_id and deleted_at is null for update;
  if not found then raise exception 'Franquia não encontrada'; end if;
  perform set_config('app.audit_reason',v_reason,true);
  update public.franchises set contract_status=p_status,updated_at=now() where id=p_franchise_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_contract_updated','franchises',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('contract_status',v_old),
      'new_value',jsonb_build_object('contract_status',p_status),'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'contract_status',p_status);
end;
$function$;
