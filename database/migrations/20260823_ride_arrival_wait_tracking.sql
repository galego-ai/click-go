alter table public.ride_categories
  add column if not exists wait_tolerance_minutes integer not null default 5,
  add column if not exists waiting_fee_per_minute numeric(10,2) not null default 0.50;

do $$ begin
  if not exists (select 1 from pg_constraint where conname='ride_categories_wait_tolerance_check') then
    alter table public.ride_categories add constraint ride_categories_wait_tolerance_check check (wait_tolerance_minutes between 0 and 120);
  end if;
  if not exists (select 1 from pg_constraint where conname='ride_categories_wait_fee_check') then
    alter table public.ride_categories add constraint ride_categories_wait_fee_check check (waiting_fee_per_minute >= 0);
  end if;
end $$;

alter table public.rides
  add column if not exists arrived_at timestamptz,
  add column if not exists arrived_lat double precision,
  add column if not exists arrived_lng double precision,
  add column if not exists started_lat double precision,
  add column if not exists started_lng double precision,
  add column if not exists completed_lat double precision,
  add column if not exists completed_lng double precision,
  add column if not exists wait_free_seconds integer not null default 300,
  add column if not exists wait_fee_per_minute numeric(10,2) not null default 0.50,
  add column if not exists wait_charge_amount numeric(10,2) not null default 0;

do $$ begin
  if not exists (select 1 from pg_constraint where conname='rides_wait_free_seconds_check') then
    alter table public.rides add constraint rides_wait_free_seconds_check check (wait_free_seconds >= 0);
  end if;
  if not exists (select 1 from pg_constraint where conname='rides_wait_fee_check') then
    alter table public.rides add constraint rides_wait_fee_check check (wait_fee_per_minute >= 0 and wait_charge_amount >= 0);
  end if;
end $$;

create table if not exists public.ride_location_points (
  id bigint generated always as identity primary key,
  ride_id uuid not null references public.rides(id) on delete cascade,
  driver_id uuid not null references public.drivers(id) on delete cascade,
  lat double precision not null check (lat between -90 and 90),
  lng double precision not null check (lng between -180 and 180),
  heading double precision,
  speed_kmh double precision,
  phase text not null,
  recorded_at timestamptz not null default now()
);
create index if not exists ride_location_points_ride_time_idx on public.ride_location_points(ride_id,recorded_at);
create index if not exists ride_location_points_driver_time_idx on public.ride_location_points(driver_id,recorded_at desc);

alter table public.ride_location_points enable row level security;
drop policy if exists ride_location_points_driver_select on public.ride_location_points;
create policy ride_location_points_driver_select on public.ride_location_points for select to authenticated using ((select auth.uid())=driver_id);
drop policy if exists ride_location_points_passenger_select on public.ride_location_points;
create policy ride_location_points_passenger_select on public.ride_location_points for select to authenticated using (exists(select 1 from public.rides r where r.id=ride_location_points.ride_id and r.passenger_id=(select auth.uid())));
drop policy if exists ride_location_points_franchise_select on public.ride_location_points;
create policy ride_location_points_franchise_select on public.ride_location_points for select to authenticated using (exists(select 1 from public.rides r join public.profiles p on p.id=(select auth.uid()) where r.id=ride_location_points.ride_id and p.role='franchise_admin' and p.franchise_id=r.franchise_id));
drop policy if exists ride_location_points_super_admin_select on public.ride_location_points;
create policy ride_location_points_super_admin_select on public.ride_location_points for select to authenticated using (public.jwt_app_role()='super_admin');
grant select on public.ride_location_points to authenticated;

create or replace function public.get_passenger_current_driver_card(p_ride_id uuid)
returns table(driver_id uuid,full_name text,avatar_url text,rating numeric,vehicle_make text,vehicle_model text,vehicle_year integer,vehicle_plate text,vehicle_color text,vehicle_type text)
language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare v_uid uuid:=auth.uid();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if not exists(select 1 from public.rides r where r.id=p_ride_id and r.passenger_id=v_uid and r.driver_id is not null) then raise exception 'Corrida não encontrada para este passageiro'; end if;
  return query
  select r.driver_id,p.full_name,p.avatar_url,d.rating,v.make,v.model,v.year,v.plate,v.color,v.vehicle_type
  from public.rides r
  join public.drivers d on d.id=r.driver_id
  join public.profiles p on p.id=r.driver_id
  left join lateral (select x.make,x.model,x.year,x.plate,x.color,x.vehicle_type from public.vehicles x where x.driver_id=r.driver_id and x.active=true order by x.created_at desc limit 1) v on true
  where r.id=p_ride_id and r.passenger_id=v_uid;
end;
$$;
revoke all on function public.get_passenger_current_driver_card(uuid) from public,anon;
grant execute on function public.get_passenger_current_driver_card(uuid) to authenticated;

create or replace function public.update_driver_location(p_lat double precision,p_lng double precision,p_heading double precision default null,p_speed_kmh double precision default null)
returns void language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare v_uid uuid:=auth.uid();v_last timestamptz;v_ride record;v_last_point timestamptz;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if p_lat is null or p_lng is null or p_lat not between -90 and 90 or p_lng not between -180 and 180 then raise exception 'Localização inválida'; end if;
  if not exists(select 1 from public.drivers d where d.id=v_uid and d.status='approved' and d.online=true) then raise exception 'Motorista precisa estar aprovado e online'; end if;
  select updated_at into v_last from public.driver_locations where driver_id=v_uid;
  if v_last is not null and v_last>now()-interval '5 seconds' then return; end if;
  insert into public.driver_locations(driver_id,lat,lng,heading,speed_kmh,updated_at) values(v_uid,p_lat,p_lng,p_heading,greatest(coalesce(p_speed_kmh,0),0),now())
  on conflict(driver_id) do update set lat=excluded.lat,lng=excluded.lng,heading=excluded.heading,speed_kmh=excluded.speed_kmh,updated_at=now();
  select r.id,r.status::text as status into v_ride from public.rides r where r.driver_id=v_uid and r.status in ('accepted','driver_arriving','in_progress') order by r.accepted_at desc nulls last limit 1;
  if v_ride.id is not null then
    select max(recorded_at) into v_last_point from public.ride_location_points where ride_id=v_ride.id;
    if v_last_point is null or v_last_point<=now()-interval '10 seconds' then
      insert into public.ride_location_points(ride_id,driver_id,lat,lng,heading,speed_kmh,phase) values(v_ride.id,v_uid,p_lat,p_lng,p_heading,greatest(coalesce(p_speed_kmh,0),0),v_ride.status);
    end if;
  end if;
end;
$$;
revoke all on function public.update_driver_location(double precision,double precision,double precision,double precision) from public,anon;
grant execute on function public.update_driver_location(double precision,double precision,double precision,double precision) to authenticated;

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
    v_next:='in_progress';v_wait_seconds:=greatest(0,floor(extract(epoch from (v_now-coalesce(v_ride.arrived_at,v_now))))::integer-coalesce(v_ride.wait_free_seconds,300));v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;v_wait_charge:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  elsif p_action='complete' and v_ride.status='in_progress' then
    if lower(coalesce(v_ride.payment_method_preference,''))='card_machine' and not exists(select 1 from public.payments where ride_id=p_ride_id and method='card_machine' and status='paid') then raise exception 'Confirme o recebimento na maquininha antes de concluir'; end if;
    v_next:='completed';
  else raise exception 'Transição de corrida inválida';end if;
  update public.rides set status=v_next,
    arrived_at=case when v_next='driver_arriving' then coalesce(arrived_at,v_now) else arrived_at end,
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
