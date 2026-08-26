create or replace function public.matrix_create_franchise(
  p_trade_name text,
  p_legal_name text,
  p_document text default null,
  p_contact_name text default null,
  p_contact_email text default null,
  p_contact_phone text default null,
  p_territory_type text default 'city',
  p_due_day integer default 10,
  p_plan_id uuid default null,
  p_reason text default null
)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_trade text:=nullif(trim(coalesce(p_trade_name,'')),'');
  v_legal text:=nullif(trim(coalesce(p_legal_name,'')),'');
  v_due integer:=least(28,greatest(1,coalesce(p_due_day,10)));
  v_fid uuid;
  v_plan public.franchise_plans%rowtype;
  v_next_due date;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if v_trade is null or v_legal is null then raise exception 'Nome fantasia e razão social são obrigatórios'; end if;
  if coalesce(p_territory_type,'') not in ('city','multi_city','region') then raise exception 'Tipo de território inválido'; end if;
  if p_plan_id is not null then
    select * into v_plan from public.franchise_plans where id=p_plan_id and active;
    if not found then raise exception 'Plano não encontrado ou inativo'; end if;
  end if;
  insert into public.franchises(trade_name,legal_name,document,contact_name,contact_email,contact_phone,territory_type,due_day,active,license_status,activation_date,next_due_date,onboarding_status)
  values(v_trade,v_legal,nullif(trim(coalesce(p_document,'')),''),nullif(trim(coalesce(p_contact_name,'')),''),nullif(trim(coalesce(p_contact_email,'')),''),nullif(trim(coalesce(p_contact_phone,'')),''),p_territory_type,v_due,true,case when p_plan_id is null then 'pending' else 'active' end,case when p_plan_id is null then null else current_date end,null,'in_progress') returning id into v_fid;
  if p_plan_id is not null then
    v_next_due:=(date_trunc('month',current_date)+interval '1 month'+((v_due-1)||' days')::interval)::date;
    insert into public.franchise_subscriptions(franchise_id,plan_id,status,license_status,matrix_commission_percentage,due_day,next_due_date,starts_at,activated_at)
    values(v_fid,p_plan_id,'active','active',coalesce(v_plan.matrix_commission_percentage,0),v_due,v_next_due,now(),now());
    update public.franchises set next_due_date=v_next_due where id=v_fid;
  end if;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_created','franchises',v_fid::text,jsonb_build_object('franchise_id',v_fid,'trade_name',v_trade,'plan_id',p_plan_id,'due_day',v_due,'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',v_fid,'next_due_date',v_next_due);
end;
$$;
revoke all on function public.matrix_create_franchise(text,text,text,text,text,text,text,integer,uuid,text) from public,anon;
grant execute on function public.matrix_create_franchise(text,text,text,text,text,text,text,integer,uuid,text) to authenticated,service_role;

create or replace function public.matrix_assign_franchise_plan(p_franchise_id uuid,p_plan_id uuid,p_reason text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),''); v_plan public.franchise_plans%rowtype; v_due integer; v_next_due date; v_old_plan uuid;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  select due_day into v_due from public.franchises where id=p_franchise_id and deleted_at is null for update;
  if not found then raise exception 'Franquia não encontrada'; end if;
  select * into v_plan from public.franchise_plans where id=p_plan_id and active;
  if not found then raise exception 'Plano não encontrado ou inativo'; end if;
  select plan_id into v_old_plan from public.franchise_subscriptions where franchise_id=p_franchise_id and status='active' order by starts_at desc limit 1;
  update public.franchise_subscriptions set status='cancelled',license_status='cancelled',ends_at=now(),updated_at=now() where franchise_id=p_franchise_id and status='active';
  v_due:=least(28,greatest(1,coalesce(v_due,10)));
  v_next_due:=(date_trunc('month',current_date)+interval '1 month'+((v_due-1)||' days')::interval)::date;
  insert into public.franchise_subscriptions(franchise_id,plan_id,status,license_status,matrix_commission_percentage,due_day,next_due_date,starts_at,activated_at)
  values(p_franchise_id,p_plan_id,'active','active',coalesce(v_plan.matrix_commission_percentage,0),v_due,v_next_due,now(),now());
  update public.franchises set active=true,license_status='active',activation_date=coalesce(activation_date,current_date),next_due_date=v_next_due,blocked_at=null,blocked_reason=null,updated_at=now() where id=p_franchise_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_plan_assigned','franchise_subscriptions',p_franchise_id::text,jsonb_build_object('franchise_id',p_franchise_id,'old_plan_id',v_old_plan,'new_plan_id',p_plan_id,'next_due_date',v_next_due,'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'plan_id',p_plan_id,'next_due_date',v_next_due);
end;
$$;
revoke all on function public.matrix_assign_franchise_plan(uuid,uuid,text) from public,anon;
grant execute on function public.matrix_assign_franchise_plan(uuid,uuid,text) to authenticated,service_role;

create or replace function public.matrix_update_franchise_contract(p_franchise_id uuid,p_status text,p_reason text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_reason text:=nullif(trim(coalesce(p_reason,'')),''); v_old text;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_status not in ('pending','signed','expired','cancelled') then raise exception 'Status contratual inválido'; end if;
  select contract_status into v_old from public.franchises where id=p_franchise_id and deleted_at is null for update;
  if not found then raise exception 'Franquia não encontrada'; end if;
  update public.franchises set contract_status=p_status,updated_at=now() where id=p_franchise_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_contract_updated','franchises',p_franchise_id::text,jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('contract_status',v_old),'new_value',jsonb_build_object('contract_status',p_status),'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'contract_status',p_status);
end;
$$;
revoke all on function public.matrix_update_franchise_contract(uuid,text,text) from public,anon;
grant execute on function public.matrix_update_franchise_contract(uuid,text,text) to authenticated,service_role;

create or replace function public.matrix_set_franchise_onboarding_step(p_step_id uuid,p_completed boolean,p_reason text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_reason text:=nullif(trim(coalesce(p_reason,'')),''); v_step public.franchise_onboarding_steps%rowtype;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  select * into v_step from public.franchise_onboarding_steps where id=p_step_id for update;
  if not found then raise exception 'Etapa de implantação não encontrada'; end if;
  update public.franchise_onboarding_steps set completed=p_completed,completed_at=case when p_completed then now() else null end,completed_by=case when p_completed then auth.uid() else null end,updated_at=now() where id=p_step_id;
  update public.franchises f set onboarding_status=case when not exists(select 1 from public.franchise_onboarding_steps s where s.franchise_id=v_step.franchise_id and s.id<>p_step_id and not s.completed) and p_completed then 'completed' else 'in_progress' end,updated_at=now() where f.id=v_step.franchise_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_onboarding_step_updated','franchise_onboarding_steps',p_step_id::text,jsonb_build_object('franchise_id',v_step.franchise_id,'step_key',v_step.step_key,'old_completed',v_step.completed,'new_completed',p_completed,'reason',v_reason,'source','matrix'));
  return jsonb_build_object('ok',true,'franchise_id',v_step.franchise_id,'step_id',p_step_id,'completed',p_completed);
end;
$$;
revoke all on function public.matrix_set_franchise_onboarding_step(uuid,boolean,text) from public,anon;
grant execute on function public.matrix_set_franchise_onboarding_step(uuid,boolean,text) to authenticated,service_role;
