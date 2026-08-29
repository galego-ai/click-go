alter table public.rides
  add column if not exists driver_payment_confirmed_at timestamptz,
  add column if not exists driver_payment_confirmed_amount numeric,
  add column if not exists driver_payment_confirmed_method text;

comment on column public.rides.driver_payment_confirmed_at is 'Momento em que o motorista confirmou no app o recebimento do valor da corrida.';
comment on column public.rides.driver_payment_confirmed_amount is 'Valor exibido e confirmado pelo motorista antes da avaliação do passageiro.';
comment on column public.rides.driver_payment_confirmed_method is 'Forma de pagamento registrada na corrida no momento da confirmação pelo motorista.';

create or replace function public.confirm_driver_ride_payment(p_ride_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_ride public.rides%rowtype;
  v_amount numeric;
  v_method text;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;

  select * into v_ride
  from public.rides
  where id=p_ride_id and driver_id=v_uid
  for update;
  if not found then raise exception 'Corrida não encontrada para este motorista'; end if;
  if v_ride.status::text <> 'completed' then raise exception 'Finalize a corrida antes de confirmar o recebimento'; end if;

  v_amount:=round(coalesce(v_ride.final_fare,v_ride.estimated_fare,0)::numeric,2);
  v_method:=nullif(trim(coalesce(v_ride.payment_method_preference,'')),'');

  update public.rides
  set driver_payment_confirmed_at=coalesce(driver_payment_confirmed_at,now()),
      driver_payment_confirmed_amount=coalesce(driver_payment_confirmed_amount,v_amount),
      driver_payment_confirmed_method=coalesce(driver_payment_confirmed_method,v_method)
  where id=p_ride_id;

  return jsonb_build_object(
    'ok',true,
    'ride_id',p_ride_id,
    'amount',v_amount,
    'payment_method',v_method,
    'confirmed_at',(select driver_payment_confirmed_at from public.rides where id=p_ride_id)
  );
end;
$function$;

revoke all on function public.confirm_driver_ride_payment(uuid) from public;
grant execute on function public.confirm_driver_ride_payment(uuid) to authenticated;

create or replace function public.submit_driver_passenger_rating(p_ride_id uuid, p_rating integer, p_comment text default null::text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_actor uuid := auth.uid();
  v_ride public.rides%rowtype;
begin
  if v_actor is null then raise exception 'Autenticação obrigatória'; end if;
  if p_rating < 1 or p_rating > 5 then raise exception 'Avaliação deve ficar entre 1 e 5'; end if;

  select * into v_ride from public.rides where id = p_ride_id;
  if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.driver_id <> v_actor then raise exception 'Corrida não pertence a este motorista'; end if;
  if v_ride.status::text <> 'completed' then raise exception 'A corrida precisa estar concluída'; end if;
  if v_ride.driver_payment_confirmed_at is null then raise exception 'Confirme o recebimento do pagamento antes da avaliação'; end if;

  insert into public.driver_passenger_ratings(ride_id, driver_id, passenger_id, rating, comment, created_at, updated_at)
  values (p_ride_id, v_actor, v_ride.passenger_id, p_rating, nullif(btrim(p_comment), ''), now(), now())
  on conflict (ride_id) do update
    set rating = excluded.rating,
        comment = excluded.comment,
        updated_at = now();

  return jsonb_build_object('ok', true, 'passenger_id', v_ride.passenger_id, 'rating', p_rating);
end;
$function$;

create or replace function public.franchise_live_driver_map(p_city_id uuid default null::uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid := auth.uid();
  v_role text;
  v_franchise uuid;
  v_result jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;

  select p.role::text,p.franchise_id into v_role,v_franchise
  from public.profiles p
  where p.id=v_uid and p.active is not false;

  if v_role <> 'franchise_admin' or v_franchise is null then raise exception 'Acesso exclusivo do franqueado'; end if;

  if p_city_id is not null and not exists(
    select 1 from public.franchise_cities fc
    where fc.franchise_id=v_franchise and fc.city_id=p_city_id
  ) then raise exception 'Cidade fora da franquia'; end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'driver_id',d.id,
    'full_name',coalesce(nullif(trim(p.full_name),''),'Motorista sem nome'),
    'online',true,
    'dispatch_online',coalesce(d.online,false),
    'status',d.status::text,
    'activity_state',case when tx.id is not null then 'taximeter' when ar.id is not null then ar.status else 'online' end,
    'active_ride_id',ar.id,
    'taximeter_session_id',tx.id,
    'taximeter_amount',tx.current_amount,
    'online_since',d.online_since,
    'city_id',d.city_id,
    'city_name',c.name,
    'city_state',c.state,
    'lat',coalesce(tx.last_lat,dl.lat),
    'lng',coalesce(tx.last_lng,dl.lng),
    'heading',dl.heading,
    'speed_kmh',dl.speed_kmh,
    'updated_at',coalesce(tx.updated_at,dl.updated_at,d.online_since)
  ) order by coalesce(tx.updated_at,dl.updated_at,d.online_since,d.created_at) desc),'[]'::jsonb)
  into v_result
  from public.drivers d
  join public.profiles p on p.id=d.id
  left join public.cities c on c.id=d.city_id
  left join public.driver_locations dl on dl.driver_id=d.id
  left join lateral (
    select r.id,r.status::text as status
    from public.rides r
    where r.driver_id=d.id and r.status::text in ('accepted','driver_arriving','in_progress')
    order by r.accepted_at desc nulls last limit 1
  ) ar on true
  left join lateral (
    select s.id,s.last_lat,s.last_lng,s.current_amount,s.updated_at
    from public.driver_taximeter_sessions s
    where s.driver_id=d.id and s.status='running'
    order by s.started_at desc limit 1
  ) tx on true
  where d.franchise_id=v_franchise
    and d.status::text='approved'
    and (coalesce(d.online,false)=true or ar.id is not null or tx.id is not null)
    and (p_city_id is null or d.city_id=p_city_id);

  return v_result;
end;
$function$;

create or replace function public.broadcast_driver_location_live()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_city uuid;
  v_online boolean;
  v_activity text;
begin
  select d.city_id,coalesce(d.online,false) into v_city,v_online
  from public.drivers d where d.id=new.driver_id;
  if v_city is null then return new; end if;

  select r.status::text into v_activity
  from public.rides r
  where r.driver_id=new.driver_id and r.status::text in ('accepted','driver_arriving','in_progress')
  order by r.accepted_at desc nulls last limit 1;

  perform realtime.send(
    jsonb_build_object(
      'driver_id',new.driver_id::text,
      'lat',new.lat,
      'lng',new.lng,
      'heading',new.heading,
      'speed_kmh',new.speed_kmh,
      'updated_at',new.updated_at,
      'online',v_online,
      'activity_state',coalesce(v_activity,'online')
    ),
    'location',
    'city:'||v_city::text||':driver-locations',
    true
  );
  return new;
end;
$function$;

revoke all on function public.broadcast_driver_location_live() from public,anon,authenticated;

drop trigger if exists trg_broadcast_driver_location_live on public.driver_locations;
create trigger trg_broadcast_driver_location_live
after insert or update on public.driver_locations
for each row execute function public.broadcast_driver_location_live();

create or replace function public.broadcast_driver_taximeter_live()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
begin
  if new.city_id is null then return new; end if;
  if new.last_lat is null or new.last_lng is null then return new; end if;

  perform realtime.send(
    jsonb_build_object(
      'driver_id',new.driver_id::text,
      'lat',new.last_lat,
      'lng',new.last_lng,
      'heading',null,
      'speed_kmh',null,
      'updated_at',new.updated_at,
      'online',(new.status='running'),
      'activity_state',case when new.status='running' then 'taximeter' else 'offline' end,
      'taximeter_amount',new.current_amount
    ),
    'location',
    'city:'||new.city_id::text||':driver-locations',
    true
  );
  return new;
end;
$function$;

revoke all on function public.broadcast_driver_taximeter_live() from public,anon,authenticated;

drop trigger if exists trg_broadcast_driver_taximeter_live on public.driver_taximeter_sessions;
create trigger trg_broadcast_driver_taximeter_live
after insert or update of last_lat,last_lng,current_amount,status,updated_at on public.driver_taximeter_sessions
for each row execute function public.broadcast_driver_taximeter_live();