alter table public.ride_categories
  add column if not exists route_deviation_threshold_m integer not null default 800;

do $$ begin
  if not exists (select 1 from pg_constraint where conname='ride_categories_route_deviation_threshold_check') then
    alter table public.ride_categories
      add constraint ride_categories_route_deviation_threshold_check
      check (route_deviation_threshold_m between 100 and 5000);
  end if;
end $$;

create table if not exists public.ride_security (
  ride_id uuid primary key references public.rides(id) on delete cascade,
  passenger_id uuid not null references public.profiles(id) on delete cascade,
  pin_code text not null check (pin_code ~ '^[0-9]{4}$'),
  pin_verified_at timestamptz,
  pin_verified_by uuid references public.profiles(id) on delete set null,
  failed_attempts integer not null default 0 check (failed_attempts >= 0),
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.ride_security enable row level security;
revoke all on public.ride_security from anon, authenticated;

create or replace function public.ensure_ride_security()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
begin
  insert into public.ride_security(ride_id,passenger_id,pin_code)
  values(new.id,new.passenger_id,(floor(random()*9000)+1000)::integer::text)
  on conflict(ride_id) do nothing;
  return new;
end;
$$;
revoke all on function public.ensure_ride_security() from public,anon,authenticated;

drop trigger if exists trg_ensure_ride_security on public.rides;
create trigger trg_ensure_ride_security
after insert on public.rides
for each row execute function public.ensure_ride_security();

insert into public.ride_security(ride_id,passenger_id,pin_code)
select r.id,r.passenger_id,(floor(random()*9000)+1000)::integer::text
from public.rides r
where not exists(select 1 from public.ride_security s where s.ride_id=r.id)
on conflict(ride_id) do nothing;

create table if not exists public.user_emergency_contacts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 2 and 100),
  phone text not null check (char_length(regexp_replace(phone,'\\D','','g')) between 8 and 15),
  relationship text,
  is_primary boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists user_emergency_contacts_owner_idx on public.user_emergency_contacts(owner_id,active,is_primary desc);
alter table public.user_emergency_contacts enable row level security;

drop policy if exists emergency_contacts_owner_select on public.user_emergency_contacts;
create policy emergency_contacts_owner_select on public.user_emergency_contacts
for select to authenticated
using ((select auth.uid())=owner_id);

drop policy if exists emergency_contacts_owner_insert on public.user_emergency_contacts;
create policy emergency_contacts_owner_insert on public.user_emergency_contacts
for insert to authenticated
with check ((select auth.uid())=owner_id);

drop policy if exists emergency_contacts_owner_update on public.user_emergency_contacts;
create policy emergency_contacts_owner_update on public.user_emergency_contacts
for update to authenticated
using ((select auth.uid())=owner_id)
with check ((select auth.uid())=owner_id);

drop policy if exists emergency_contacts_owner_delete on public.user_emergency_contacts;
create policy emergency_contacts_owner_delete on public.user_emergency_contacts
for delete to authenticated
using ((select auth.uid())=owner_id);

grant select,insert,update,delete on public.user_emergency_contacts to authenticated;

create table if not exists public.ride_safety_alerts (
  id uuid primary key default gen_random_uuid(),
  ride_id uuid not null references public.rides(id) on delete cascade,
  reporter_id uuid references public.profiles(id) on delete set null,
  reporter_role text not null check (reporter_role in ('passenger','driver','system')),
  alert_type text not null check (alert_type in ('sos','route_deviation')),
  severity text not null default 'high' check (severity in ('medium','high','critical')),
  lat double precision check (lat is null or lat between -90 and 90),
  lng double precision check (lng is null or lng between -180 and 180),
  distance_from_route_m numeric,
  message text,
  status text not null default 'open' check (status in ('open','resolved')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);
create index if not exists ride_safety_alerts_ride_time_idx on public.ride_safety_alerts(ride_id,created_at desc);
create index if not exists ride_safety_alerts_open_idx on public.ride_safety_alerts(status,created_at desc) where status='open';
alter table public.ride_safety_alerts enable row level security;
revoke all on public.ride_safety_alerts from anon,authenticated;

create or replace function public.get_passenger_ride_safety(p_ride_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_pin text;
  v_verified timestamptz;
  v_contact jsonb:=null;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if not exists(select 1 from public.rides r where r.id=p_ride_id and r.passenger_id=v_uid) then
    raise exception 'Corrida não encontrada para este passageiro';
  end if;
  select s.pin_code,s.pin_verified_at into v_pin,v_verified
  from public.ride_security s where s.ride_id=p_ride_id and s.passenger_id=v_uid;
  select jsonb_build_object('id',c.id,'name',c.name,'phone',c.phone,'relationship',c.relationship)
    into v_contact
  from public.user_emergency_contacts c
  where c.owner_id=v_uid and c.active=true
  order by c.is_primary desc,c.created_at asc
  limit 1;
  return jsonb_build_object('pin',v_pin,'pin_verified_at',v_verified,'primary_contact',v_contact);
end;
$$;
revoke all on function public.get_passenger_ride_safety(uuid) from public,anon;
grant execute on function public.get_passenger_ride_safety(uuid) to authenticated;

create or replace function public.verify_ride_start_pin(p_ride_id uuid,p_pin text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_sec public.ride_security%rowtype;
  v_failed integer;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if not exists(select 1 from public.rides r where r.id=p_ride_id and r.driver_id=v_uid and r.status::text='driver_arriving') then
    raise exception 'Corrida não está aguardando embarque para este motorista';
  end if;
  select * into v_sec from public.ride_security where ride_id=p_ride_id for update;
  if not found then raise exception 'PIN de segurança indisponível'; end if;
  if v_sec.pin_verified_at is not null then return jsonb_build_object('verified',true,'already_verified',true); end if;
  if v_sec.locked_until is not null and v_sec.locked_until>now() then
    return jsonb_build_object('verified',false,'locked',true,'locked_until',v_sec.locked_until);
  end if;
  if coalesce(trim(p_pin),'')=v_sec.pin_code then
    update public.ride_security
      set pin_verified_at=now(),pin_verified_by=v_uid,failed_attempts=0,locked_until=null,updated_at=now()
      where ride_id=p_ride_id;
    insert into public.ride_events(ride_id,driver_id,event_type,metadata)
      values(p_ride_id,v_uid,'pickup_pin_verified',jsonb_build_object('verified_at',now()));
    return jsonb_build_object('verified',true,'already_verified',false);
  end if;
  v_failed:=coalesce(v_sec.failed_attempts,0)+1;
  update public.ride_security
    set failed_attempts=v_failed,
        locked_until=case when v_failed>=5 then now()+interval '5 minutes' else null end,
        updated_at=now()
    where ride_id=p_ride_id;
  return jsonb_build_object('verified',false,'locked',v_failed>=5,'remaining_attempts',greatest(0,5-v_failed));
end;
$$;
revoke all on function public.verify_ride_start_pin(uuid,text) from public,anon;
grant execute on function public.verify_ride_start_pin(uuid,text) to authenticated;

create or replace function public.trigger_ride_sos(p_ride_id uuid,p_lat double precision default null,p_lng double precision default null,p_message text default null)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_ride public.rides%rowtype;
  v_role text;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id;
  if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.passenger_id=v_uid then v_role:='passenger';
  elsif v_ride.driver_id=v_uid then v_role:='driver';
  else raise exception 'Você não participa desta corrida'; end if;
  if v_ride.status::text not in ('accepted','driver_arriving','in_progress') then raise exception 'SOS disponível apenas durante corrida ativa'; end if;
  insert into public.ride_safety_alerts(ride_id,reporter_id,reporter_role,alert_type,severity,lat,lng,message)
    values(p_ride_id,v_uid,v_role,'sos','critical',p_lat,p_lng,nullif(trim(coalesce(p_message,'')),'')) returning id into v_id;
  insert into public.ride_events(ride_id,driver_id,event_type,lat,lng,metadata)
    values(p_ride_id,case when v_role='driver' then v_uid else v_ride.driver_id end,'sos_triggered',p_lat,p_lng,jsonb_build_object('reporter_id',v_uid,'reporter_role',v_role,'alert_id',v_id));
  return jsonb_build_object('ok',true,'alert_id',v_id,'created_at',now());
end;
$$;
revoke all on function public.trigger_ride_sos(uuid,double precision,double precision,text) from public,anon;
grant execute on function public.trigger_ride_sos(uuid,double precision,double precision,text) to authenticated;

create or replace function public.report_route_deviation(p_ride_id uuid,p_lat double precision,p_lng double precision,p_distance_m numeric)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_threshold integer:=800;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select coalesce(c.route_deviation_threshold_m,800)
    into v_threshold
  from public.rides r
  left join public.ride_categories c on c.id=r.category_id
  where r.id=p_ride_id and r.driver_id=v_uid and r.status::text='in_progress';
  if not found then raise exception 'Corrida em andamento não encontrada para este motorista'; end if;
  if coalesce(p_distance_m,0)<v_threshold then
    return jsonb_build_object('reported',false,'threshold_m',v_threshold);
  end if;
  if exists(select 1 from public.ride_safety_alerts a where a.ride_id=p_ride_id and a.alert_type='route_deviation' and a.created_at>now()-interval '5 minutes') then
    return jsonb_build_object('reported',false,'duplicate',true,'threshold_m',v_threshold);
  end if;
  insert into public.ride_safety_alerts(ride_id,reporter_id,reporter_role,alert_type,severity,lat,lng,distance_from_route_m,message)
    values(p_ride_id,v_uid,'system','route_deviation','high',p_lat,p_lng,p_distance_m,'Possível desvio da rota planejada detectado automaticamente.') returning id into v_id;
  insert into public.ride_events(ride_id,driver_id,event_type,lat,lng,metadata)
    values(p_ride_id,v_uid,'route_deviation_detected',p_lat,p_lng,jsonb_build_object('alert_id',v_id,'distance_m',p_distance_m,'threshold_m',v_threshold));
  return jsonb_build_object('reported',true,'alert_id',v_id,'threshold_m',v_threshold);
end;
$$;
revoke all on function public.report_route_deviation(uuid,double precision,double precision,numeric) from public,anon;
grant execute on function public.report_route_deviation(uuid,double precision,double precision,numeric) to authenticated;

create or replace function public.get_ride_safety_alerts(p_ride_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_allowed boolean:=false;
  v_result jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select exists(
    select 1 from public.rides r
    where r.id=p_ride_id and (
      r.passenger_id=v_uid or r.driver_id=v_uid or
      exists(select 1 from public.profiles p where p.id=v_uid and p.role::text='franchise_admin' and p.franchise_id=r.franchise_id) or
      public.jwt_app_role()='super_admin'
    )
  ) into v_allowed;
  if not v_allowed then raise exception 'Sem acesso aos alertas desta corrida'; end if;
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',a.id,'alert_type',a.alert_type,'severity',a.severity,'reporter_role',a.reporter_role,
    'lat',a.lat,'lng',a.lng,'distance_from_route_m',a.distance_from_route_m,'message',a.message,
    'status',a.status,'created_at',a.created_at,'resolved_at',a.resolved_at
  ) order by a.created_at desc),'[]'::jsonb)
  into v_result from public.ride_safety_alerts a where a.ride_id=p_ride_id;
  return v_result;
end;
$$;
revoke all on function public.get_ride_safety_alerts(uuid) from public,anon;
grant execute on function public.get_ride_safety_alerts(uuid) to authenticated;

create or replace function public.advance_driver_ride(p_ride_id uuid,p_action text)
returns jsonb language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();v_ride public.rides%rowtype;v_next public.ride_status;v_commission numeric:=0;v_ride_fee numeric:=0;v_cancel_collection numeric:=0;v_balance numeric:=null;
  v_loc public.driver_locations%rowtype;v_tolerance integer:=300;v_wait_fee numeric:=0.50;v_wait_seconds integer:=0;v_wait_minutes integer:=0;v_wait_charge numeric:=0;v_now timestamptz:=now();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id and driver_id=v_uid for update;if not found then raise exception 'Corrida não encontrada para este motorista'; end if;
  select * into v_loc from public.driver_locations where driver_id=v_uid;
  if p_action='arrived' and v_ride.status='accepted' then
    v_next:='driver_arriving';
    select coalesce(rc.wait_tolerance_minutes,5)*60,coalesce(rc.waiting_fee_per_minute,0.50) into v_tolerance,v_wait_fee from public.ride_categories rc where rc.id=v_ride.category_id;
  elsif p_action='start' and v_ride.status='driver_arriving' then
    if not exists(select 1 from public.ride_security s where s.ride_id=p_ride_id and s.pin_verified_at is not null) then
      raise exception 'Confirme o PIN de 4 dígitos do passageiro antes de iniciar a corrida';
    end if;
    v_next:='in_progress';v_wait_seconds:=greatest(0,floor(extract(epoch from (v_now-coalesce(v_ride.arrived_at,v_now))))::integer-coalesce(v_ride.wait_free_seconds,300));v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;v_wait_charge:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  elsif p_action='complete' and v_ride.status='in_progress' then
    if lower(coalesce(v_ride.payment_method_preference,''))='card_machine' and not exists(select 1 from public.payments where ride_id=p_ride_id and method='card_machine' and status='paid') then raise exception 'Confirme o recebimento na maquininha antes de concluir'; end if;
    v_next:='completed';
  else raise exception 'Transição de corrida inválida';end if;
  update public.rides set status=v_next,
    arrived_at=case when v_next='driver_arriving' then coalesce(arrived_at,v_now) else arrived_at end,
    driver_departed_at=case when v_next='driver_arriving' then coalesce(driver_departed_at,v_now) else driver_departed_at end,
    arrived_lat=case when v_next='driver_arriving' then coalesce(v_loc.lat,arrived_lat) else arrived_lat end,
    arrived_lng=case when v_next='driver_arriving' then coalesce(v_loc.lng,arrived_lng) else arrived_lng end,
    wait_free_seconds=case when v_next='driver_arriving' then v_tolerance else wait_free_seconds end,
    wait_fee_per_minute=case when v_next='driver_arriving' then v_wait_fee else wait_fee_per_minute end,
    wait_charge_amount=case when v_next='in_progress' then v_wait_charge else wait_charge_amount end,
    started_at=case when v_next='in_progress' then v_now else started_at end,
    started_lat=case when v_next='in_progress' then coalesce(v_loc.lat,started_lat) else started_lat end,
    started_lng=case when v_next='in_progress' then coalesce(v_loc.lng,started_lng) else started_lng end,
    completed_at=case when v_next='completed' then v_now else completed_at end,
    completed_lat=case when v_next='completed' then coalesce(v_loc.lat,completed_lat) else completed_lat end,
    completed_lng=case when v_next='completed' then coalesce(v_loc.lng,completed_lng) else completed_lng end,
    final_fare=case when v_next='completed' then round((coalesce(final_fare,estimated_fare,0)+coalesce(wait_charge_amount,0))::numeric,2) else final_fare end
  where id=p_ride_id;
  if v_loc.driver_id is not null then insert into public.ride_location_points(ride_id,driver_id,lat,lng,heading,speed_kmh,phase) values(p_ride_id,v_uid,v_loc.lat,v_loc.lng,v_loc.heading,v_loc.speed_kmh,case p_action when 'arrived' then 'arrived_pickup' when 'start' then 'ride_started' else 'ride_completed' end);end if;
  insert into public.ride_events(ride_id,driver_id,event_type) values(p_ride_id,v_uid,case p_action when 'arrived' then 'driver_arriving' when 'start' then 'ride_started' else 'ride_completed' end);
  if v_next='completed' then
    select coalesce(sum(amount),0) into v_commission from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_commission' and status='settled';
    select coalesce(sum(amount),0) into v_ride_fee from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_fee' and status='settled';
    select coalesce(sum(amount),0) into v_cancel_collection from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='adjustment' and status='settled' and metadata->>'kind'='passenger_cancellation_collection';
    select balance into v_balance from public.driver_operational_wallets where driver_id=v_uid;
  end if;
  return jsonb_build_object('ok',true,'ride_id',p_ride_id,'status',v_next,'payment_method',v_ride.payment_method_preference,'wait_charge_amount',case when v_next='in_progress' then v_wait_charge else coalesce(v_ride.wait_charge_amount,0) end,'direct_collection_commission_debit',v_commission,'per_ride_fee_debit',v_ride_fee,'cancellation_collection_debit',v_cancel_collection,'operational_balance_after',v_balance);
end;
$$;
revoke all on function public.advance_driver_ride(uuid,text) from public,anon;
grant execute on function public.advance_driver_ride(uuid,text) to authenticated;
