-- CLICK-GO Gestão: base profissional multiempresa / licenciamento por território
-- Mantém compatibilidade com as tabelas existentes e adiciona somente campos/estruturas incrementais.

alter table public.franchises
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists license_status text not null default 'active',
  add column if not exists activation_date date,
  add column if not exists next_due_date date,
  add column if not exists due_day smallint not null default 10,
  add column if not exists contract_status text not null default 'pending',
  add column if not exists contract_reference text,
  add column if not exists territory_type text not null default 'city',
  add column if not exists onboarding_status text not null default 'pending',
  add column if not exists support_mode_enabled boolean not null default true,
  add column if not exists white_label_mode text not null default 'clickgo',
  add column if not exists commercial_notes text;

do $$ begin
  if not exists (select 1 from pg_constraint where conname='franchises_license_status_check') then
    alter table public.franchises add constraint franchises_license_status_check check (license_status in ('pending','active','past_due','suspended','cancelled'));
  end if;
  if not exists (select 1 from pg_constraint where conname='franchises_contract_status_check') then
    alter table public.franchises add constraint franchises_contract_status_check check (contract_status in ('pending','signed','expired','cancelled'));
  end if;
  if not exists (select 1 from pg_constraint where conname='franchises_territory_type_check') then
    alter table public.franchises add constraint franchises_territory_type_check check (territory_type in ('city','multi_city','region'));
  end if;
  if not exists (select 1 from pg_constraint where conname='franchises_onboarding_status_check') then
    alter table public.franchises add constraint franchises_onboarding_status_check check (onboarding_status in ('pending','in_progress','ready','operating'));
  end if;
  if not exists (select 1 from pg_constraint where conname='franchises_due_day_check') then
    alter table public.franchises add constraint franchises_due_day_check check (due_day between 1 and 28);
  end if;
end $$;

alter table public.franchise_plans
  add column if not exists setup_fee numeric(12,2) not null default 0,
  add column if not exists grace_days integer not null default 5,
  add column if not exists max_cities integer,
  add column if not exists enabled_modules jsonb not null default '{"passenger_app":true,"driver_app":true,"dispatch":true,"finance":true,"support":true,"marketing":true,"reports":true}'::jsonb,
  add column if not exists white_label_level text not null default 'brand_locked',
  add column if not exists support_level text not null default 'standard';

do $$ begin
  if not exists (select 1 from pg_constraint where conname='franchise_plans_grace_days_check') then
    alter table public.franchise_plans add constraint franchise_plans_grace_days_check check (grace_days between 0 and 60);
  end if;
  if not exists (select 1 from pg_constraint where conname='franchise_plans_white_label_level_check') then
    alter table public.franchise_plans add constraint franchise_plans_white_label_level_check check (white_label_level in ('brand_locked','controlled','custom'));
  end if;
end $$;

alter table public.franchise_subscriptions
  add column if not exists activated_at timestamptz,
  add column if not exists next_due_date date,
  add column if not exists due_day smallint,
  add column if not exists custom_setup_fee numeric(12,2),
  add column if not exists license_status text not null default 'active';

do $$ begin
  if not exists (select 1 from pg_constraint where conname='franchise_subscriptions_license_status_check') then
    alter table public.franchise_subscriptions add constraint franchise_subscriptions_license_status_check check (license_status in ('pending','active','past_due','suspended','cancelled'));
  end if;
  if not exists (select 1 from pg_constraint where conname='franchise_subscriptions_due_day_check') then
    alter table public.franchise_subscriptions add constraint franchise_subscriptions_due_day_check check (due_day is null or due_day between 1 and 28);
  end if;
end $$;

create table if not exists public.franchise_staff_permissions (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  staff_role text not null default 'operator',
  permissions jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint franchise_staff_permissions_role_check check (staff_role in ('manager','operator','financial','support','marketing'))
);

create index if not exists franchise_staff_permissions_franchise_idx on public.franchise_staff_permissions(franchise_id,active);

create table if not exists public.franchise_onboarding_steps (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  step_key text not null,
  label text not null,
  sort_order integer not null default 0,
  completed boolean not null default false,
  completed_at timestamptz,
  completed_by uuid references public.profiles(id),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(franchise_id,step_key)
);

create index if not exists franchise_onboarding_steps_franchise_idx on public.franchise_onboarding_steps(franchise_id,sort_order);

create table if not exists public.configuration_sync_state (
  scope_key text primary key,
  franchise_id uuid references public.franchises(id) on delete cascade,
  version bigint not null default 1,
  last_change_at timestamptz not null default now(),
  last_change_source text not null default 'system',
  last_entity text,
  last_actor_id uuid references public.profiles(id),
  unique(franchise_id)
);

create table if not exists public.configuration_events (
  id bigint generated by default as identity primary key,
  franchise_id uuid references public.franchises(id) on delete cascade,
  city_id uuid references public.cities(id) on delete set null,
  version bigint not null,
  source text not null,
  entity text not null,
  entity_id text,
  action text not null,
  payload jsonb not null default '{}'::jsonb,
  actor_id uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists configuration_events_scope_idx on public.configuration_events(franchise_id,created_at desc);
create index if not exists configuration_events_city_idx on public.configuration_events(city_id,created_at desc);

alter table public.franchise_staff_permissions enable row level security;
alter table public.franchise_onboarding_steps enable row level security;
alter table public.configuration_sync_state enable row level security;
alter table public.configuration_events enable row level security;

drop policy if exists super_admin_staff_permissions_all on public.franchise_staff_permissions;
create policy super_admin_staff_permissions_all on public.franchise_staff_permissions
for all using (public.jwt_app_role()='super_admin') with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_staff_permissions_scope on public.franchise_staff_permissions;
create policy franchise_admin_staff_permissions_scope on public.franchise_staff_permissions
for all using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id())
with check (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists super_admin_onboarding_all on public.franchise_onboarding_steps;
create policy super_admin_onboarding_all on public.franchise_onboarding_steps
for all using (public.jwt_app_role()='super_admin') with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_onboarding_scope on public.franchise_onboarding_steps;
create policy franchise_admin_onboarding_scope on public.franchise_onboarding_steps
for all using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id())
with check (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists super_admin_configuration_sync_all on public.configuration_sync_state;
create policy super_admin_configuration_sync_all on public.configuration_sync_state
for all using (public.jwt_app_role()='super_admin') with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_configuration_sync_select on public.configuration_sync_state;
create policy franchise_admin_configuration_sync_select on public.configuration_sync_state
for select using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists super_admin_configuration_events_all on public.configuration_events;
create policy super_admin_configuration_events_all on public.configuration_events
for all using (public.jwt_app_role()='super_admin') with check (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_configuration_events_select on public.configuration_events;
create policy franchise_admin_configuration_events_select on public.configuration_events
for select using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

create or replace function public.ensure_franchise_onboarding(p_franchise_id uuid)
returns void
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.franchise_onboarding_steps(franchise_id,step_key,label,sort_order)
  values
    (p_franchise_id,'registration','Cadastro da empresa e responsável',10),
    (p_franchise_id,'contract','Contrato assinado',20),
    (p_franchise_id,'payment','Implantação / primeira cobrança confirmada',30),
    (p_franchise_id,'territory','Cidade ou região liberada',40),
    (p_franchise_id,'pricing','Tarifas e categorias configuradas',50),
    (p_franchise_id,'administrator','Administrador regional criado',60),
    (p_franchise_id,'drivers','Primeiros motoristas cadastrados',70),
    (p_franchise_id,'operation','Operação liberada',80)
  on conflict(franchise_id,step_key) do nothing;
end;
$$;

create or replace function public.seed_franchise_onboarding_trigger()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  perform public.ensure_franchise_onboarding(new.id);
  return new;
end;
$$;

drop trigger if exists trg_seed_franchise_onboarding on public.franchises;
create trigger trg_seed_franchise_onboarding
after insert on public.franchises
for each row execute function public.seed_franchise_onboarding_trigger();

select public.ensure_franchise_onboarding(id) from public.franchises where deleted_at is null;

-- Marca automaticamente etapas que já podem ser inferidas dos dados existentes.
update public.franchise_onboarding_steps s set completed=true,completed_at=coalesce(completed_at,now())
where step_key='registration' and exists(select 1 from public.franchises f where f.id=s.franchise_id and f.trade_name is not null and f.legal_name is not null);
update public.franchise_onboarding_steps s set completed=true,completed_at=coalesce(completed_at,now())
where step_key='territory' and exists(select 1 from public.franchise_cities fc where fc.franchise_id=s.franchise_id);
update public.franchise_onboarding_steps s set completed=true,completed_at=coalesce(completed_at,now())
where step_key='administrator' and exists(select 1 from public.profiles p where p.franchise_id=s.franchise_id and p.role='franchise_admin' and p.active);
update public.franchise_onboarding_steps s set completed=true,completed_at=coalesce(completed_at,now())
where step_key='drivers' and exists(select 1 from public.drivers d where d.franchise_id=s.franchise_id);
update public.franchise_onboarding_steps s set completed=true,completed_at=coalesce(completed_at,now())
where step_key='pricing' and exists(select 1 from public.ride_categories c where c.franchise_id=s.franchise_id and c.active);

create or replace function public.bump_configuration_sync()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_scope text;
  v_source text;
  v_version bigint;
  v_actor uuid:=auth.uid();
begin
  v_row:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
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
  values(v_franchise,v_city,v_version,v_source,tg_table_name,v_entity_id,lower(tg_op),jsonb_build_object('changed_at',now()),v_actor);

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_actor,'configuration_'||lower(tg_op),tg_table_name,v_entity_id,jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'version',v_version,'source',v_source));

  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;

-- Alterações abaixo devem ser percebidas por apps e painéis.
do $$
declare t text;
begin
  foreach t in array array[
    'ride_categories','franchise_settings','advertising_banners','promotions','coupons',
    'franchise_business_hours','franchise_city_payment_settings','franchise_operational_wallet_settings'
  ] loop
    execute format('drop trigger if exists trg_configuration_sync on public.%I',t);
    execute format('create trigger trg_configuration_sync after insert or update or delete on public.%I for each row execute function public.bump_configuration_sync()',t);
  end loop;
end $$;

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
  v_grace integer;
  v_overdue_days integer;
begin
  for rec in
    select f.id,f.active,f.license_status,f.due_day,
           s.id subscription_id,s.status subscription_status,coalesce(s.next_due_date,f.next_due_date) next_due_date,
           coalesce(p.grace_days,5) grace_days
    from public.franchises f
    left join lateral (
      select s1.* from public.franchise_subscriptions s1
      where s1.franchise_id=f.id and s1.status='active'
      order by s1.starts_at desc limit 1
    ) s on true
    left join public.franchise_plans p on p.id=s.plan_id
    where f.deleted_at is null
  loop
    if rec.license_status='cancelled' then continue; end if;
    if not rec.active then
      v_status:='suspended';
    elsif rec.subscription_id is null then
      v_status:='pending';
    else
      select coalesce(max((current_date-i.due_date)),0)::int into v_overdue_days
      from public.franchise_invoices i
      where i.franchise_id=rec.id and i.status not in ('paid','cancelled') and i.due_date<current_date;
      v_grace:=coalesce(rec.grace_days,5);
      if coalesce(v_overdue_days,0)>v_grace then v_status:='suspended';
      elsif coalesce(v_overdue_days,0)>0 then v_status:='past_due';
      else v_status:='active';
      end if;
    end if;
    update public.franchises set license_status=v_status,updated_at=now() where id=rec.id and license_status is distinct from v_status;
    update public.franchise_subscriptions set license_status=v_status,updated_at=now() where id=rec.subscription_id and license_status is distinct from v_status;
    v_count:=v_count+1;
  end loop;
  return v_count;
end;
$$;

-- Executa uma vez ao dia; idempotente para não duplicar job.
do $$
begin
  if exists(select 1 from cron.job where jobname='clickgo-refresh-license-status') then
    perform cron.unschedule('clickgo-refresh-license-status');
  end if;
  perform cron.schedule('clickgo-refresh-license-status','15 3 * * *','select public.refresh_franchise_license_statuses();');
exception when undefined_table or undefined_function then
  null;
end $$;

create or replace function public.get_app_configuration_state(p_franchise_id uuid default null,p_city_id uuid default null)
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_franchise uuid:=p_franchise_id;
  v_state public.configuration_sync_state%rowtype;
  v_result jsonb;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_franchise is null and p_city_id is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=p_city_id limit 1;
  end if;
  if v_franchise is null then
    return jsonb_build_object('version',0,'license_status','active','features','{}'::jsonb,'settings','{}'::jsonb,'categories','[]'::jsonb,'banners','[]'::jsonb);
  end if;
  select * into v_state from public.configuration_sync_state where scope_key=v_franchise::text;
  select jsonb_build_object(
    'franchise_id',f.id,
    'version',coalesce(v_state.version,0),
    'changed_at',v_state.last_change_at,
    'license_status',f.license_status,
    'operation_enabled',(f.active and f.license_status='active'),
    'features',coalesce(p.enabled_modules,'{}'::jsonb),
    'settings',coalesce((select jsonb_object_agg(fs.setting_key,fs.setting_value) from public.franchise_settings fs where fs.franchise_id=f.id),'{}'::jsonb),
    'categories',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'city_id',c.city_id,'name',c.name,'base_fare',c.base_fare,'price_per_km',c.price_per_km,'price_per_minute',c.price_per_minute,'minimum_fare',c.minimum_fare,'cancellation_fee',c.cancellation_fee,'dynamic_multiplier',c.dynamic_multiplier,'vehicle_type',c.required_vehicle_type,'icon_url',c.icon_url,'map_marker_url',c.map_marker_url,'wait_tolerance_minutes',c.wait_tolerance_minutes,'waiting_fee_per_minute',c.waiting_fee_per_minute)) from public.ride_categories c where c.franchise_id=f.id and c.active and (p_city_id is null or c.city_id=p_city_id)),'[]'::jsonb),
    'banners',coalesce((select jsonb_agg(jsonb_build_object('id',b.id,'title',b.title,'image_url',b.image_url,'target_url',b.target_url,'placement',b.placement,'audience',b.audience,'sort_order',b.sort_order)) from public.advertising_banners b where b.franchise_id=f.id and b.active and (p_city_id is null or b.city_id is null or b.city_id=p_city_id) and (b.starts_at is null or b.starts_at<=now()) and (b.ends_at is null or b.ends_at>=now())),'[]'::jsonb),
    'payment_settings',(select to_jsonb(ps)-'updated_by' from public.franchise_city_payment_settings ps where ps.franchise_id=f.id and (p_city_id is null or ps.city_id=p_city_id) order by ps.updated_at desc limit 1)
  ) into v_result
  from public.franchises f
  left join lateral (
    select fp.* from public.franchise_subscriptions s join public.franchise_plans fp on fp.id=s.plan_id
    where s.franchise_id=f.id and s.status='active' order by s.starts_at desc limit 1
  ) p on true
  where f.id=v_franchise and f.deleted_at is null;
  return coalesce(v_result,jsonb_build_object('version',0,'operation_enabled',false));
end;
$$;

grant execute on function public.get_app_configuration_state(uuid,uuid) to authenticated;
grant execute on function public.ensure_franchise_onboarding(uuid) to authenticated;

-- Realtime: eventos de configuração e estado de sincronização são pequenos e próprios para atualização de painel.
do $$ begin
  begin alter publication supabase_realtime add table public.configuration_events; exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.configuration_sync_state; exception when duplicate_object then null; end;
end $$;

select public.refresh_franchise_license_statuses();
