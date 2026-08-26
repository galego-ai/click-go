-- CLICK-GO: arquitetura oficial com apenas Painel Matriz e Painel Franqueado.
-- Regras de cobrança, inadimplência, suporte e auditoria detalhada.

create table if not exists public.franchise_collection_rules (
  franchise_id uuid primary key references public.franchises(id) on delete cascade,
  alert_before_due_days integer not null default 3 check (alert_before_due_days between 0 and 60),
  restrict_new_drivers_after_days integer not null default 5 check (restrict_new_drivers_after_days between 0 and 180),
  block_new_rides_after_days integer not null default 10 check (block_new_rides_after_days between 0 and 180),
  suspend_operation_after_days integer not null default 30 check (suspend_operation_after_days between 0 and 365),
  auto_reactivate_on_payment boolean not null default true,
  manual_override_until date,
  updated_by uuid references public.profiles(id),
  updated_at timestamptz not null default now(),
  constraint franchise_collection_rule_order_check check (
    restrict_new_drivers_after_days <= block_new_rides_after_days
    and block_new_rides_after_days <= suspend_operation_after_days
  )
);

insert into public.franchise_collection_rules(franchise_id)
select id from public.franchises where deleted_at is null
on conflict(franchise_id) do nothing;

create table if not exists public.franchise_support_sessions (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  matrix_user_id uuid not null references public.profiles(id),
  reason text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb
);
create index if not exists franchise_support_sessions_franchise_idx on public.franchise_support_sessions(franchise_id,started_at desc);
create index if not exists franchise_support_sessions_active_idx on public.franchise_support_sessions(matrix_user_id,active,started_at desc);

create table if not exists public.franchise_invoice_adjustments (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  invoice_id uuid references public.franchise_invoices(id) on delete set null,
  reference_month date not null,
  adjustment_type text not null check (adjustment_type in ('credit','discount','fine','other')),
  description text not null,
  amount numeric(12,2) not null check (amount <> 0),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);
create index if not exists franchise_invoice_adjustments_scope_idx on public.franchise_invoice_adjustments(franchise_id,reference_month,created_at);

alter table public.franchise_collection_rules enable row level security;
alter table public.franchise_support_sessions enable row level security;
alter table public.franchise_invoice_adjustments enable row level security;

grant select,insert,update on public.franchise_collection_rules to authenticated;
grant select,insert,update on public.franchise_support_sessions to authenticated;
grant select,insert,update,delete on public.franchise_invoice_adjustments to authenticated;

drop policy if exists super_admin_collection_rules_all on public.franchise_collection_rules;
create policy super_admin_collection_rules_all on public.franchise_collection_rules
for all to authenticated
using (public.jwt_app_role()='super_admin')
with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_collection_rules_select on public.franchise_collection_rules;
create policy franchise_admin_collection_rules_select on public.franchise_collection_rules
for select to authenticated
using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists super_admin_support_sessions_all on public.franchise_support_sessions;
create policy super_admin_support_sessions_all on public.franchise_support_sessions
for all to authenticated
using (public.jwt_app_role()='super_admin')
with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_support_sessions_select on public.franchise_support_sessions;
create policy franchise_admin_support_sessions_select on public.franchise_support_sessions
for select to authenticated
using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists super_admin_invoice_adjustments_all on public.franchise_invoice_adjustments;
create policy super_admin_invoice_adjustments_all on public.franchise_invoice_adjustments
for all to authenticated
using (public.jwt_app_role()='super_admin')
with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_invoice_adjustments_select on public.franchise_invoice_adjustments;
create policy franchise_admin_invoice_adjustments_select on public.franchise_invoice_adjustments
for select to authenticated
using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists operator_invoice_adjustments_select on public.franchise_invoice_adjustments;
create policy operator_invoice_adjustments_select on public.franchise_invoice_adjustments
for select to authenticated
using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));

-- O franqueado precisa enxergar sua própria fatura CLICK-GO.
drop policy if exists franchise_admin_own_invoices_select on public.franchise_invoices;
create policy franchise_admin_own_invoices_select on public.franchise_invoices
for select to authenticated
using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

-- Transparência: auditoria global para Matriz e somente a própria operação para o franqueado.
drop policy if exists franchise_admin_own_audit_logs_select on public.audit_logs;
create policy franchise_admin_own_audit_logs_select on public.audit_logs
for select to authenticated
using (
  public.jwt_app_role()='franchise_admin'
  and nullif(metadata->>'franchise_id','')::uuid=public.jwt_franchise_id()
);

-- Auditoria crítica com antes/depois.
create or replace function public.capture_critical_audit()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_source text;
  v_reason text;
begin
  if tg_op='INSERT' then
    v_old:=null;
    v_new:=to_jsonb(new);
  elsif tg_op='DELETE' then
    v_old:=to_jsonb(old);
    v_new:=null;
  else
    v_old:=to_jsonb(old);
    v_new:=to_jsonb(new);
  end if;

  v_row:=coalesce(v_new,v_old,'{}'::jsonb);
  begin
    if tg_table_name='franchises' then
      v_franchise:=nullif(v_row->>'id','')::uuid;
    else
      v_franchise:=nullif(v_row->>'franchise_id','')::uuid;
    end if;
  exception when others then v_franchise:=null; end;
  begin v_city:=nullif(v_row->>'city_id','')::uuid; exception when others then v_city:=null; end;
  if v_franchise is null and v_city is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=v_city limit 1;
  end if;

  v_entity_id:=coalesce(v_row->>'id',concat_ws(':',v_row->>'franchise_id',v_row->>'city_id'),v_row->>'franchise_id');
  v_source:=case public.jwt_app_role()
    when 'super_admin' then 'matrix'
    when 'franchise_admin' then 'franchise'
    when 'operator' then 'staff'
    when 'driver' then 'driver_app'
    when 'passenger' then 'passenger_app'
    else 'system' end;
  v_reason:=coalesce(v_row->>'reason',v_row->>'blocked_reason',v_row->>'description',v_row->>'commercial_notes');

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),lower(tg_op),tg_table_name,v_entity_id,
    jsonb_build_object(
      'franchise_id',v_franchise,
      'city_id',v_city,
      'source',v_source,
      'reason',v_reason,
      'old_value',v_old,
      'new_value',v_new
    )
  );
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function public.capture_critical_audit() from public,anon,authenticated;

do $$
declare t text;
begin
  foreach t in array array[
    'franchises','franchise_plans','franchise_subscriptions','franchise_cities',
    'account_blocks','franchise_invoices','franchise_collection_rules',
    'franchise_invoice_adjustments','franchise_support_sessions'
  ] loop
    execute format('drop trigger if exists trg_critical_audit on public.%I',t);
    execute format('create trigger trg_critical_audit after insert or update or delete on public.%I for each row execute function public.capture_critical_audit()',t);
  end loop;
end $$;

-- Melhora os eventos de configuração existentes para também guardar valor anterior e novo.
create or replace function public.bump_configuration_sync()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_scope text;
  v_source text;
  v_version bigint;
  v_actor uuid:=auth.uid();
begin
  if tg_op='INSERT' then v_old:=null; v_new:=to_jsonb(new);
  elsif tg_op='DELETE' then v_old:=to_jsonb(old); v_new:=null;
  else v_old:=to_jsonb(old); v_new:=to_jsonb(new); end if;
  v_row:=coalesce(v_new,v_old,'{}'::jsonb);
  begin v_franchise:=nullif(v_row->>'franchise_id','')::uuid; exception when others then v_franchise:=null; end;
  begin v_city:=nullif(v_row->>'city_id','')::uuid; exception when others then v_city:=null; end;
  v_entity_id:=coalesce(v_row->>'id',v_row->>'setting_key',v_row->>'franchise_id');
  if v_franchise is null and v_city is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=v_city limit 1;
  end if;
  v_scope:=coalesce(v_franchise::text,'global');
  v_source:=case public.jwt_app_role()
    when 'super_admin' then 'matrix'
    when 'franchise_admin' then 'franchise'
    when 'operator' then 'staff'
    when 'driver' then 'driver_app'
    when 'passenger' then 'passenger_app'
    else 'system' end;

  insert into public.configuration_sync_state(scope_key,franchise_id,version,last_change_at,last_change_source,last_entity,last_actor_id)
  values(v_scope,v_franchise,1,now(),v_source,tg_table_name,v_actor)
  on conflict(scope_key) do update set
    version=public.configuration_sync_state.version+1,
    last_change_at=now(),
    last_change_source=excluded.last_change_source,
    last_entity=excluded.last_entity,
    last_actor_id=excluded.last_actor_id
  returning version into v_version;

  insert into public.configuration_events(franchise_id,city_id,version,source,entity,entity_id,action,payload,actor_id)
  values(v_franchise,v_city,v_version,v_source,tg_table_name,v_entity_id,lower(tg_op),
    jsonb_build_object('changed_at',now(),'old_value',v_old,'new_value',v_new),v_actor);

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_actor,'configuration_'||lower(tg_op),tg_table_name,v_entity_id,
    jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'version',v_version,'source',v_source,'old_value',v_old,'new_value',v_new));

  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function public.bump_configuration_sync() from public,anon,authenticated;

-- Demonstrativo oficial da franquia. Cobrança considera apenas corridas concluídas.
create or replace function public.get_franchise_billing_summary(
  p_franchise_id uuid,
  p_reference_month date default date_trunc('month',current_date)::date
)
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_role text:=public.jwt_app_role();
  v_month date:=date_trunc('month',p_reference_month)::date;
  v_sub record;
  v_invoice record;
  v_franchise record;
  v_rides integer:=0;
  v_gross numeric:=0;
  v_overage integer:=0;
  v_monthly numeric:=0;
  v_per_ride numeric:=0;
  v_overage_amount numeric:=0;
  v_percentage_amount numeric:=0;
  v_adjustments numeric:=0;
  v_adjustment_rows jsonb:='[]'::jsonb;
  v_total numeric:=0;
  v_due date;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and p_franchise_id=public.jwt_franchise_id() then null;
  elsif v_role='operator' and p_franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') then null;
  else raise exception 'Acesso não autorizado à fatura'; end if;

  select id,trade_name,due_day,next_due_date into v_franchise
  from public.franchises where id=p_franchise_id and deleted_at is null;
  if not found then raise exception 'Franquia não encontrada'; end if;

  select s.id subscription_id,s.plan_id,p.name plan_name,p.billing_model,
    coalesce(s.custom_monthly_fee,p.monthly_fee,0)::numeric monthly_fee,
    coalesce(s.custom_percentage_rate,p.percentage_rate,0)::numeric percentage_rate,
    coalesce(s.custom_fixed_fee_per_ride,p.fixed_fee_per_ride,0)::numeric fixed_fee_per_ride,
    coalesce(s.custom_included_rides,p.included_rides,0)::integer included_rides,
    coalesce(s.custom_overage_fee_per_ride,p.overage_fee_per_ride,0)::numeric overage_fee_per_ride
  into v_sub
  from public.franchise_subscriptions s
  join public.franchise_plans p on p.id=s.plan_id
  where s.franchise_id=p_franchise_id
    and s.starts_at < (v_month+interval '1 month')
    and (s.ends_at is null or s.ends_at>=v_month)
  order by case when s.status='active' then 0 else 1 end,s.starts_at desc
  limit 1;

  if not found then
    return jsonb_build_object('franchise_id',p_franchise_id,'reference_month',v_month,'has_plan',false,'total_due',0,'adjustments','[]'::jsonb);
  end if;

  select count(*)::int,coalesce(sum(final_fare),0)::numeric
  into v_rides,v_gross
  from public.rides
  where franchise_id=p_franchise_id and status='completed'
    and completed_at>=v_month::timestamptz
    and completed_at<(v_month+interval '1 month')::timestamptz;

  v_monthly:=v_sub.monthly_fee;
  v_overage:=greatest(v_rides-v_sub.included_rides,0);

  if v_sub.billing_model='fixed_per_ride' then
    v_per_ride:=v_rides*v_sub.fixed_fee_per_ride;
  elsif v_sub.billing_model='percentage' then
    v_percentage_amount:=v_gross*v_sub.percentage_rate/100;
  elsif v_sub.billing_model='hybrid' then
    v_per_ride:=v_rides*v_sub.fixed_fee_per_ride;
    v_overage_amount:=v_overage*v_sub.overage_fee_per_ride;
  end if;

  select coalesce(sum(amount),0)::numeric,
         coalesce(jsonb_agg(jsonb_build_object('id',id,'type',adjustment_type,'description',description,'amount',amount,'created_at',created_at) order by created_at),'[]'::jsonb)
  into v_adjustments,v_adjustment_rows
  from public.franchise_invoice_adjustments
  where franchise_id=p_franchise_id and reference_month=v_month;

  select id,total_due,due_date,status,paid_at into v_invoice
  from public.franchise_invoices
  where franchise_id=p_franchise_id and reference_month=v_month
  order by created_at desc limit 1;

  v_due:=coalesce(v_invoice.due_date,(v_month+((greatest(1,least(28,v_franchise.due_day))-1)||' days')::interval)::date);
  v_total:=greatest(v_monthly+v_per_ride+v_overage_amount+v_percentage_amount+v_adjustments,0);

  return jsonb_build_object(
    'franchise_id',p_franchise_id,'franchise_name',v_franchise.trade_name,'reference_month',v_month,'has_plan',true,
    'plan_id',v_sub.plan_id,'plan_name',v_sub.plan_name,'billing_model',v_sub.billing_model,
    'rides_count',v_rides,'gross_ride_value',v_gross,'included_rides',v_sub.included_rides,'overage_rides',v_overage,
    'monthly_fee',v_monthly,'fixed_fee_per_ride',v_sub.fixed_fee_per_ride,'per_ride_amount',v_per_ride,
    'overage_fee_per_ride',v_sub.overage_fee_per_ride,'overage_amount',v_overage_amount,
    'percentage_rate',v_sub.percentage_rate,'percentage_amount',v_percentage_amount,
    'adjustments_total',v_adjustments,'adjustments',v_adjustment_rows,
    'total_due',v_total,'due_date',v_due,
    'invoice_id',v_invoice.id,'invoice_status',coalesce(v_invoice.status,'open'),'paid_at',v_invoice.paid_at
  );
end;
$$;
revoke all on function public.get_franchise_billing_summary(uuid,date) from public,anon;
grant execute on function public.get_franchise_billing_summary(uuid,date) to authenticated;

create or replace function public.get_franchise_collection_state(p_franchise_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_role text:=public.jwt_app_role();
  v_rules public.franchise_collection_rules%rowtype;
  v_franchise public.franchises%rowtype;
  v_overdue integer:=0;
  v_due numeric:=0;
  v_override boolean:=false;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and p_franchise_id=public.jwt_franchise_id() then null;
  elsif v_role='operator' and p_franchise_id=public.staff_franchise_id() then null;
  else raise exception 'Acesso não autorizado'; end if;

  select * into v_franchise from public.franchises where id=p_franchise_id and deleted_at is null;
  select * into v_rules from public.franchise_collection_rules where franchise_id=p_franchise_id;
  if not found then
    v_rules.alert_before_due_days:=3;
    v_rules.restrict_new_drivers_after_days:=5;
    v_rules.block_new_rides_after_days:=10;
    v_rules.suspend_operation_after_days:=30;
    v_rules.auto_reactivate_on_payment:=true;
  end if;

  select coalesce(max(current_date-due_date),0)::int,coalesce(sum(total_due),0)::numeric
  into v_overdue,v_due
  from public.franchise_invoices
  where franchise_id=p_franchise_id and status not in ('paid','cancelled') and due_date<current_date;

  v_override:=v_rules.manual_override_until is not null and v_rules.manual_override_until>=current_date;
  return jsonb_build_object(
    'franchise_id',p_franchise_id,'license_status',v_franchise.license_status,'active',v_franchise.active,
    'overdue_days',v_overdue,'open_overdue_amount',v_due,'manual_override',v_override,'manual_override_until',v_rules.manual_override_until,
    'alert_before_due_days',v_rules.alert_before_due_days,
    'restrict_new_drivers_after_days',v_rules.restrict_new_drivers_after_days,
    'block_new_rides_after_days',v_rules.block_new_rides_after_days,
    'suspend_operation_after_days',v_rules.suspend_operation_after_days,
    'allow_new_drivers',(v_override or v_overdue<=v_rules.restrict_new_drivers_after_days),
    'allow_new_rides',(v_override or v_overdue<=v_rules.block_new_rides_after_days),
    'operation_suspended',((not v_franchise.active) or v_franchise.license_status in ('suspended','cancelled') or (not v_override and v_overdue>v_rules.suspend_operation_after_days))
  );
end;
$$;
revoke all on function public.get_franchise_collection_state(uuid) from public,anon;
grant execute on function public.get_franchise_collection_state(uuid) to authenticated;

-- Suspensão automática agora usa o limiar específico da franquia (padrão 30 dias).
create or replace function public.refresh_franchise_license_statuses()
returns integer
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_count integer:=0;
  rec record;
  v_status text;
  v_overdue_days integer;
  v_suspend_days integer;
  v_override boolean;
begin
  for rec in
    select f.id,f.active,f.license_status,
           s.id subscription_id,
           coalesce(cr.suspend_operation_after_days,30) suspend_days,
           cr.manual_override_until
    from public.franchises f
    left join lateral (
      select s1.* from public.franchise_subscriptions s1
      where s1.franchise_id=f.id and s1.status='active'
      order by s1.starts_at desc limit 1
    ) s on true
    left join public.franchise_collection_rules cr on cr.franchise_id=f.id
    where f.deleted_at is null
  loop
    if rec.license_status='cancelled' then continue; end if;
    if not rec.active then
      v_status:='suspended';
    elsif rec.subscription_id is null then
      v_status:='pending';
    else
      select coalesce(max(current_date-i.due_date),0)::int into v_overdue_days
      from public.franchise_invoices i
      where i.franchise_id=rec.id and i.status not in ('paid','cancelled') and i.due_date<current_date;
      v_suspend_days:=coalesce(rec.suspend_days,30);
      v_override:=rec.manual_override_until is not null and rec.manual_override_until>=current_date;
      if coalesce(v_overdue_days,0)>v_suspend_days and not v_override then v_status:='suspended';
      elsif coalesce(v_overdue_days,0)>0 then v_status:='past_due';
      else v_status:='active'; end if;
    end if;
    update public.franchises set license_status=v_status,updated_at=now() where id=rec.id and license_status is distinct from v_status;
    update public.franchise_subscriptions set license_status=v_status,updated_at=now() where id=rec.subscription_id and license_status is distinct from v_status;
    v_count:=v_count+1;
  end loop;
  return v_count;
end;
$$;
revoke all on function public.refresh_franchise_license_statuses() from public,anon,authenticated;

-- Snapshot da Matriz alinhado ao demonstrativo: somente corridas concluídas e híbrido = taxa por todas + excedente.
create or replace function public.super_admin_franchise_network_snapshot()
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare v_result jsonb;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin'; end if;
  with active_sub as (
    select distinct on (s.franchise_id) s.franchise_id,s.id subscription_id,s.plan_id,s.status subscription_status,s.license_status subscription_license_status,
      coalesce(s.custom_monthly_fee,p.monthly_fee,0) monthly_fee,coalesce(s.custom_percentage_rate,p.percentage_rate,0) percentage_rate,
      coalesce(s.custom_fixed_fee_per_ride,p.fixed_fee_per_ride,0) fixed_fee_per_ride,coalesce(s.custom_included_rides,p.included_rides,0) included_rides,
      coalesce(s.custom_overage_fee_per_ride,p.overage_fee_per_ride,0) overage_fee_per_ride,coalesce(s.custom_setup_fee,p.setup_fee,0) setup_fee,
      coalesce(s.matrix_commission_percentage,p.matrix_commission_percentage,0) matrix_commission_percentage,p.name plan_name,p.billing_model,p.enabled_modules,p.support_level,p.white_label_level,p.grace_days,
      coalesce(s.next_due_date,(date_trunc('month',current_date)+((coalesce(s.due_day,10)-1)||' days')::interval)::date) next_due_date
    from public.franchise_subscriptions s join public.franchise_plans p on p.id=s.plan_id where s.status='active' order by s.franchise_id,s.starts_at desc
  ), ride_month as (
    select franchise_id,count(*)::int rides_month,count(distinct passenger_id)::int passengers_month,coalesce(sum(final_fare),0)::numeric gross_month
    from public.rides where status='completed' and completed_at>=date_trunc('month',now()) group by franchise_id
  ), driver_counts as (
    select franchise_id,count(*)::int drivers,count(*) filter(where online)::int drivers_online,count(*) filter(where status='pending')::int drivers_pending from public.drivers group by franchise_id
  ), admins as (
    select distinct on (franchise_id) franchise_id,id admin_id,full_name admin_name,email admin_email from public.profiles where role='franchise_admin' and active order by franchise_id,created_at
  ), territories as (
    select fc.franchise_id,count(*)::int city_count,jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'state',c.state) order by c.name) cities from public.franchise_cities fc join public.cities c on c.id=fc.city_id group by fc.franchise_id
  ), onboarding as (
    select franchise_id,count(*)::int total_steps,count(*) filter(where completed)::int completed_steps from public.franchise_onboarding_steps group by franchise_id
  ), current_invoice as (
    select distinct on (franchise_id) franchise_id,id invoice_id,total_due,monthly_fee invoice_monthly_fee,usage_fee,matrix_commission,due_date invoice_due_date,status invoice_status from public.franchise_invoices where reference_month=date_trunc('month',current_date)::date order by franchise_id,created_at desc
  ), adjustments as (
    select franchise_id,coalesce(sum(amount),0)::numeric adjustment_total from public.franchise_invoice_adjustments where reference_month=date_trunc('month',current_date)::date group by franchise_id
  ), base as (
    select f.*,s.*,coalesce(r.rides_month,0) rides_month,coalesce(r.passengers_month,0) passengers_month,coalesce(r.gross_month,0) gross_month,
      coalesce(d.drivers,0) drivers,coalesce(d.drivers_online,0) drivers_online,coalesce(d.drivers_pending,0) drivers_pending,a.admin_id,a.admin_name,a.admin_email,
      coalesce(t.city_count,0) city_count,coalesce(t.cities,'[]'::jsonb) cities,coalesce(o.total_steps,0) total_steps,coalesce(o.completed_steps,0) completed_steps,
      i.invoice_id,i.total_due invoice_total_due,i.usage_fee invoice_usage_fee,i.matrix_commission invoice_matrix_commission,i.invoice_due_date,i.invoice_status,
      coalesce(adj.adjustment_total,0) adjustment_total,coalesce(cs.version,0) config_version,cs.last_change_at config_changed_at,cs.last_change_source config_changed_source
    from public.franchises f left join active_sub s on s.franchise_id=f.id left join ride_month r on r.franchise_id=f.id left join driver_counts d on d.franchise_id=f.id left join admins a on a.franchise_id=f.id left join territories t on t.franchise_id=f.id left join onboarding o on o.franchise_id=f.id left join current_invoice i on i.franchise_id=f.id left join adjustments adj on adj.franchise_id=f.id left join public.configuration_sync_state cs on cs.franchise_id=f.id where f.deleted_at is null
  ), calc as (
    select base.*,greatest(rides_month-coalesce(included_rides,0),0)::int overage_rides,
      case when subscription_id is null then 0::numeric
        when billing_model='percentage' then gross_month*coalesce(percentage_rate,0)/100
        when billing_model='hybrid' then (rides_month*coalesce(fixed_fee_per_ride,0))+(greatest(rides_month-coalesce(included_rides,0),0)*coalesce(overage_fee_per_ride,0))
        when billing_model='fixed_per_ride' then rides_month*coalesce(fixed_fee_per_ride,0)
        else 0::numeric end computed_usage_fee
    from base
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',id,'trade_name',trade_name,'legal_name',legal_name,'document',document,'active',active,'contact_name',contact_name,'contact_email',contact_email,'contact_phone',contact_phone,
    'license_status',license_status,'activation_date',activation_date,'next_due_date',coalesce(next_due_date,invoice_due_date),'due_day',due_day,'contract_status',contract_status,'contract_reference',contract_reference,
    'territory_type',territory_type,'onboarding_status',onboarding_status,'support_mode_enabled',support_mode_enabled,'white_label_mode',white_label_mode,'commercial_notes',commercial_notes,
    'subscription_id',subscription_id,'plan_id',plan_id,'plan_name',plan_name,'billing_model',billing_model,'monthly_fee',coalesce(monthly_fee,0),'setup_fee',coalesce(setup_fee,0),'percentage_rate',coalesce(percentage_rate,0),
    'fixed_fee_per_ride',coalesce(fixed_fee_per_ride,0),'included_rides',coalesce(included_rides,0),'overage_fee_per_ride',coalesce(overage_fee_per_ride,0),'matrix_commission_percentage',coalesce(matrix_commission_percentage,0),
    'enabled_modules',coalesce(enabled_modules,'{}'::jsonb),'support_level',support_level,'white_label_level',white_label_level,'cities',cities,'city_count',city_count,'admin_id',admin_id,'admin_name',admin_name,'admin_email',admin_email,
    'drivers',drivers,'drivers_online',drivers_online,'drivers_pending',drivers_pending,'passengers_month',passengers_month,'rides_month',rides_month,'gross_month',gross_month,'overage_rides',overage_rides,
    'computed_usage_fee',computed_usage_fee,'adjustment_total',adjustment_total,'computed_total_due',greatest(coalesce(monthly_fee,0)+computed_usage_fee+adjustment_total,0),
    'invoice_id',invoice_id,'invoice_total_due',invoice_total_due,'invoice_usage_fee',invoice_usage_fee,'invoice_matrix_commission',invoice_matrix_commission,'invoice_status',invoice_status,
    'onboarding_total',total_steps,'onboarding_completed',completed_steps,'config_version',config_version,'config_changed_at',config_changed_at,'config_changed_source',config_changed_source,'created_at',created_at,'updated_at',updated_at
  ) order by created_at desc),'[]'::jsonb) into v_result from calc;
  return v_result;
end;
$$;
revoke all on function public.super_admin_franchise_network_snapshot() from public,anon;
grant execute on function public.super_admin_franchise_network_snapshot() to authenticated;
