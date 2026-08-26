create or replace function public.matrix_activate_franchise_plan(
  p_franchise_id uuid,
  p_plan_id uuid,
  p_due_day integer,
  p_matrix_commission_percentage numeric,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_plan public.franchise_plans%rowtype;
  v_franchise public.franchises%rowtype;
  v_old_subscription public.franchise_subscriptions%rowtype;
  v_due integer;
  v_commission numeric;
  v_next_due date;
  v_new_subscription_id uuid;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da ativação comercial'; end if;

  select * into v_franchise
  from public.franchises
  where id=p_franchise_id and deleted_at is null
  for update;
  if not found then raise exception 'Franquia não encontrada'; end if;

  select * into v_plan
  from public.franchise_plans
  where id=p_plan_id and active;
  if not found then raise exception 'Plano não encontrado ou inativo'; end if;

  v_due:=coalesce(p_due_day,v_franchise.due_day,10);
  if v_due<1 or v_due>28 then raise exception 'Dia de vencimento deve ficar entre 1 e 28'; end if;

  v_commission:=coalesce(p_matrix_commission_percentage,v_plan.matrix_commission_percentage,0);
  if v_commission<0 or v_commission>100 then raise exception 'Comissão da Matriz deve ficar entre 0 e 100'; end if;

  select * into v_old_subscription
  from public.franchise_subscriptions
  where franchise_id=p_franchise_id and status='active'
  order by starts_at desc
  limit 1
  for update;

  if v_franchise.next_due_date is not null
     and v_franchise.next_due_date>=current_date
     and v_due=coalesce(v_franchise.due_day,10) then
    v_next_due:=v_franchise.next_due_date;
  else
    v_next_due:=(date_trunc('month',current_date)+interval '1 month'+((v_due-1)||' days')::interval)::date;
  end if;

  perform set_config('app.audit_reason',v_reason,true);

  update public.franchise_subscriptions
     set status='cancelled',license_status='cancelled',ends_at=now(),updated_at=now()
   where franchise_id=p_franchise_id and status='active';

  insert into public.franchise_subscriptions(
    franchise_id,plan_id,status,license_status,matrix_commission_percentage,
    due_day,next_due_date,starts_at,activated_at
  ) values(
    p_franchise_id,p_plan_id,'active','active',v_commission,
    v_due,v_next_due,now(),now()
  ) returning id into v_new_subscription_id;

  update public.franchises
     set active=true,
         license_status='active',
         activation_date=coalesce(activation_date,current_date),
         due_day=v_due,
         next_due_date=v_next_due,
         blocked_at=null,
         blocked_reason=null,
         updated_at=now()
   where id=p_franchise_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),'franchise_plan_activated','franchise_subscriptions',v_new_subscription_id::text,
    jsonb_build_object(
      'franchise_id',p_franchise_id,
      'old_subscription_id',v_old_subscription.id,
      'old_plan_id',v_old_subscription.plan_id,
      'new_subscription_id',v_new_subscription_id,
      'new_plan_id',p_plan_id,
      'due_day',v_due,
      'next_due_date',v_next_due,
      'matrix_commission_percentage',v_commission,
      'reason',v_reason,
      'source','matrix'
    )
  );

  return jsonb_build_object(
    'ok',true,
    'franchise_id',p_franchise_id,
    'subscription_id',v_new_subscription_id,
    'plan_id',p_plan_id,
    'due_day',v_due,
    'next_due_date',v_next_due,
    'matrix_commission_percentage',v_commission
  );
end;
$$;

create or replace function public.matrix_assign_franchise_plan(
  p_franchise_id uuid,
  p_plan_id uuid,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_due integer;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  select due_day into v_due from public.franchises where id=p_franchise_id and deleted_at is null;
  if not found then raise exception 'Franquia não encontrada'; end if;
  return public.matrix_activate_franchise_plan(p_franchise_id,p_plan_id,v_due,null,p_reason);
end;
$$;

revoke all on function public.matrix_activate_franchise_plan(uuid,uuid,integer,numeric,text) from public,anon;
grant execute on function public.matrix_activate_franchise_plan(uuid,uuid,integer,numeric,text) to authenticated,service_role;
revoke all on function public.matrix_assign_franchise_plan(uuid,uuid,text) from public,anon;
grant execute on function public.matrix_assign_franchise_plan(uuid,uuid,text) to authenticated,service_role;
