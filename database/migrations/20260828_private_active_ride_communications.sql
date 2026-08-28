-- CLICK-GO: comunicação privada somente durante corrida ativa.
-- Regras:
-- 1) nenhuma notificação push de oferta antes do aceite;
-- 2) somente passageiro + motorista atribuídos recebem notificações vinculadas à corrida;
-- 3) chat só pode ser lido/enviado em accepted, driver_arriving ou in_progress;
-- 4) motorista offline não vê nem aceita oferta pendente;
-- 5) ao ficar offline, ofertas pendentes expiram imediatamente.

-- O status suppressed é usado quando uma entrega já enfileirada perde a validade
-- antes do envio pelo Edge Function.
alter table public.push_delivery_queue
  drop constraint if exists push_delivery_queue_status_check;
alter table public.push_delivery_queue
  add constraint push_delivery_queue_status_check
  check (status in ('queued','sent','partial','failed','no_devices','pending_fcm_configuration','suppressed'));

-- A oferta pré-aceite continua existindo dentro do app para o motorista online,
-- mas nunca vira notificação push.
drop trigger if exists trg_notify_driver_new_offer on public.ride_offers;
drop function if exists private.notify_driver_new_offer();

-- Centraliza a regra: qualquer notificação que tenha ride_id só nasce se a corrida
-- já tiver motorista atribuído, estiver ativa e o destinatário for um dos dois participantes.
create or replace function public.enqueue_user_notification(
  p_user_id uuid,
  p_type text,
  p_title text,
  p_body text,
  p_ride_id uuid default null,
  p_data jsonb default '{}'::jsonb
) returns void
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_ride public.rides%rowtype;
begin
  if p_user_id is null then return; end if;

  if p_ride_id is not null then
    select * into v_ride from public.rides where id=p_ride_id;
    if not found then return; end if;

    if v_ride.driver_id is null
       or v_ride.status::text not in ('accepted','driver_arriving','in_progress')
       or (p_user_id <> v_ride.passenger_id and p_user_id is distinct from v_ride.driver_id) then
      return;
    end if;
  end if;

  insert into public.user_notifications(user_id,ride_id,type,title,body,data)
  values(
    p_user_id,
    p_ride_id,
    p_type,
    left(coalesce(p_title,''),160),
    left(coalesce(p_body,''),600),
    coalesce(p_data,'{}'::jsonb)
  );
end;
$$;
revoke all on function public.enqueue_user_notification(uuid,text,text,text,uuid,jsonb) from public,anon,authenticated;

-- Segunda barreira imediatamente antes de chamar o Edge Function.
create or replace function public.enqueue_user_notification_push()
returns trigger
language plpgsql
security definer
set search_path to 'public','extensions','pg_temp'
as $$
declare
  v_secret text;
begin
  if new.ride_id is not null and not exists(
    select 1
    from public.rides r
    where r.id=new.ride_id
      and r.driver_id is not null
      and r.status::text in ('accepted','driver_arriving','in_progress')
      and (new.user_id=r.passenger_id or new.user_id=r.driver_id)
  ) then
    return new;
  end if;

  if not exists(
    select 1 from public.device_push_tokens t
    where t.user_id=new.user_id and t.active=true
  ) then
    return new;
  end if;

  insert into public.push_delivery_queue(notification_id,status,updated_at)
  values(new.id,'queued',now())
  on conflict(notification_id) do nothing;

  select value into v_secret
  from public.app_internal_secrets
  where key='push_dispatch_secret';

  if v_secret is not null then
    perform net.http_post(
      url:='https://kyaewidapnggmhbsrqch.supabase.co/functions/v1/push-notifications',
      headers:=jsonb_build_object(
        'Content-Type','application/json',
        'x-clickgo-internal-secret',v_secret
      ),
      body:=jsonb_build_object('notification_id',new.id),
      timeout_milliseconds:=5000
    );
  end if;

  return new;
end;
$$;
revoke all on function public.enqueue_user_notification_push() from public,anon,authenticated;

-- Chat: leitura somente pelos dois participantes enquanto a corrida estiver ativa.
drop policy if exists ride_chat_participant_select on public.ride_chat_messages;
create policy ride_chat_participant_select
on public.ride_chat_messages
for select
to authenticated
using (
  exists(
    select 1
    from public.rides r
    where r.id=ride_chat_messages.ride_id
      and r.driver_id is not null
      and r.status::text in ('accepted','driver_arriving','in_progress')
      and ((select auth.uid())=r.passenger_id or (select auth.uid())=r.driver_id)
  )
);

-- A gravação direta continua bloqueada; só o RPC validado pode inserir.
drop policy if exists ride_chat_participant_insert on public.ride_chat_messages;
revoke insert,update,delete on public.ride_chat_messages from anon,authenticated;
grant select on public.ride_chat_messages to authenticated;

create or replace function private.notify_ride_chat_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ride public.rides%rowtype;
  v_recipient uuid;
begin
  select * into v_ride from public.rides where id=new.ride_id;
  if not found then return new; end if;

  if v_ride.driver_id is null
     or v_ride.status::text not in ('accepted','driver_arriving','in_progress') then
    return new;
  end if;

  if new.sender_id=v_ride.passenger_id then
    v_recipient:=v_ride.driver_id;
  elsif new.sender_id=v_ride.driver_id then
    v_recipient:=v_ride.passenger_id;
  else
    return new;
  end if;

  perform public.enqueue_user_notification(
    v_recipient,
    'ride_chat',
    'Nova mensagem da corrida',
    left(new.message,140),
    new.ride_id,
    jsonb_build_object('message_id',new.id,'ride_id',new.ride_id)
  );

  return new;
end;
$$;
revoke all on function private.notify_ride_chat_message() from public,anon,authenticated;

-- Oferta pendente só é visível enquanto o motorista ainda está realmente online.
drop policy if exists ride_offers_driver_select on public.ride_offers;
create policy ride_offers_driver_select
on public.ride_offers
for select
to authenticated
using (
  driver_id=(select auth.uid())
  and (
    status<>'pending'
    or (
      expires_at>now()
      and exists(
        select 1
        from public.drivers d
        join public.driver_locations dl on dl.driver_id=d.id
        where d.id=(select auth.uid())
          and d.online=true
          and d.status='approved'
          and dl.updated_at>=now()-interval '2 minutes'
          and public.driver_can_be_online(d.id)
      )
    )
  )
);

create or replace function public.set_driver_online(
  p_online boolean,
  p_lat double precision default null,
  p_lng double precision default null
) returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_driver public.drivers%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_driver from public.drivers where id=v_uid for update;
  if not found then raise exception 'Cadastro de motorista não encontrado'; end if;

  if p_online then
    if exists(
      select 1 from public.driver_taximeter_sessions s
      where s.driver_id=v_uid and s.status='running'
    ) then
      raise exception 'Finalize ou cancele o taxímetro antes de ficar online para chamadas';
    end if;
    if v_driver.status<>'approved' then
      raise exception 'Seu cadastro precisa estar aprovado para ficar online';
    end if;
    if not public.driver_can_be_online(v_uid) then
      raise exception 'Seu cadastro ou plano ainda não está liberado para operação';
    end if;
    if p_lat is null or p_lng is null
       or p_lat not between -90 and 90
       or p_lng not between -180 and 180 then
      raise exception 'Localização válida é obrigatória para ficar online';
    end if;

    insert into public.driver_locations(driver_id,lat,lng,updated_at)
    values(v_uid,p_lat,p_lng,now())
    on conflict(driver_id) do update
      set lat=excluded.lat,lng=excluded.lng,updated_at=now();

    update public.drivers
    set online=true,online_since=coalesce(online_since,now())
    where id=v_uid;
  else
    -- Primeiro agenda a próxima tentativa das corridas que estavam oferecendo para este motorista.
    update public.ride_dispatch_state s
    set next_dispatch_at=now(),updated_at=now()
    where s.status='active'
      and exists(
        select 1 from public.ride_offers ro
        where ro.ride_id=s.ride_id
          and ro.driver_id=v_uid
          and ro.status='pending'
      );

    -- Em seguida invalida qualquer oferta ainda pendente.
    update public.ride_offers
    set status='expired',responded_at=coalesce(responded_at,now())
    where driver_id=v_uid and status='pending';

    update public.drivers
    set online=false,online_since=null
    where id=v_uid;
  end if;

  return jsonb_build_object('ok',true,'online',p_online);
end;
$$;
revoke all on function public.set_driver_online(boolean,double precision,double precision) from public,anon;
grant execute on function public.set_driver_online(boolean,double precision,double precision) to authenticated;

create or replace function public.get_driver_pending_offers()
returns table(
  offer_id uuid,
  ride_id uuid,
  expires_at timestamptz,
  distance_to_pickup_km numeric,
  eta_to_pickup_min integer,
  estimated_driver_earning numeric,
  estimated_fare numeric,
  origin_label text,
  origin_lat double precision,
  origin_lng double precision,
  destination_label text,
  destination_lat double precision,
  destination_lng double precision,
  category_name text,
  passenger_id uuid,
  passenger_name text,
  passenger_avatar_url text,
  passenger_rating numeric,
  passenger_rating_count bigint,
  passenger_completed_rides bigint,
  payment_method text
)
language sql
security definer
set search_path to 'public','pg_temp'
as $$
  select
    ro.id,
    ro.ride_id,
    ro.expires_at,
    ro.distance_to_pickup_km,
    ro.eta_to_pickup_min,
    ro.estimated_driver_earning,
    r.estimated_fare,
    r.origin_label,
    r.origin_lat,
    r.origin_lng,
    r.destination_label,
    r.destination_lat,
    r.destination_lng,
    c.name,
    r.passenger_id,
    coalesce(nullif(btrim(p.full_name),''),'Passageiro CLICK-GO') as passenger_name,
    p.avatar_url,
    coalesce(pr.rating,0)::numeric(3,2) as passenger_rating,
    coalesce(pr.rating_count,0)::bigint as passenger_rating_count,
    coalesce(pc.completed_rides,0)::bigint as passenger_completed_rides,
    r.payment_method_preference
  from public.ride_offers ro
  join public.rides r on r.id=ro.ride_id
  left join public.ride_categories c on c.id=r.category_id
  left join public.profiles p on p.id=r.passenger_id
  left join lateral (
    select avg(dpr.rating)::numeric(3,2) as rating,count(*)::bigint as rating_count
    from public.driver_passenger_ratings dpr
    where dpr.passenger_id=r.passenger_id
  ) pr on true
  left join lateral (
    select count(*)::bigint as completed_rides
    from public.rides rr
    where rr.passenger_id=r.passenger_id and rr.status='completed'
  ) pc on true
  where ro.driver_id=(select auth.uid())
    and ro.status='pending'
    and ro.expires_at>now()
    and r.driver_id is null
    and r.status::text in ('requested','searching')
    and exists(
      select 1
      from public.drivers d
      join public.driver_locations dl on dl.driver_id=d.id
      where d.id=(select auth.uid())
        and d.online=true
        and d.status='approved'
        and dl.updated_at>=now()-interval '2 minutes'
        and public.driver_can_be_online(d.id)
    )
  order by ro.expires_at;
$$;
revoke all on function public.get_driver_pending_offers() from public,anon;
grant execute on function public.get_driver_pending_offers() to authenticated;

create or replace function public.respond_to_ride_offer(
  p_offer_id uuid,
  p_accept boolean
) returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_offer public.ride_offers%rowtype;
  v_ride public.rides%rowtype;
  v_driver uuid:=auth.uid();
  v_method text;
begin
  if v_driver is null then raise exception 'not_authenticated'; end if;

  select * into v_offer
  from public.ride_offers
  where id=p_offer_id and driver_id=v_driver
  for update;
  if not found then raise exception 'offer_not_found'; end if;

  if v_offer.status<>'pending' or v_offer.expires_at<=now() then
    if v_offer.status='pending' then
      update public.ride_offers
      set status='expired',responded_at=now()
      where id=p_offer_id;
    end if;
    return jsonb_build_object('ok',false,'reason','expired');
  end if;

  if not p_accept then
    update public.ride_offers
    set status='rejected',responded_at=now()
    where id=p_offer_id;
    update public.drivers
    set consecutive_refusals=consecutive_refusals+1
    where id=v_driver;
    if not exists(
      select 1 from public.ride_offers
      where ride_id=v_offer.ride_id and status='pending' and expires_at>now()
    ) then
      update public.ride_dispatch_state
      set next_dispatch_at=now(),updated_at=now()
      where ride_id=v_offer.ride_id and status='active';
      perform public.dispatch_ride(v_offer.ride_id);
    end if;
    return jsonb_build_object('ok',true,'accepted',false);
  end if;

  -- Aceite só é válido se o motorista ainda estiver online no exato momento do toque.
  if not exists(
    select 1
    from public.drivers d
    join public.driver_locations dl on dl.driver_id=d.id
    where d.id=v_driver
      and d.online=true
      and d.status='approved'
      and dl.updated_at>=now()-interval '2 minutes'
      and public.driver_can_be_online(d.id)
  ) then
    update public.ride_offers
    set status='expired',responded_at=now()
    where id=p_offer_id;
    update public.ride_dispatch_state
    set next_dispatch_at=now(),updated_at=now()
    where ride_id=v_offer.ride_id and status='active';
    perform public.dispatch_ride(v_offer.ride_id);
    return jsonb_build_object('ok',false,'reason','driver_offline');
  end if;

  select * into v_ride
  from public.rides
  where id=v_offer.ride_id
  for update;
  v_method:=lower(coalesce(v_ride.payment_method_preference,'cash'));

  if not public.driver_can_be_online(v_driver) then
    update public.ride_offers
    set status='expired',responded_at=now()
    where id=p_offer_id;
    return jsonb_build_object('ok',false,'reason','wallet_or_driver_unavailable');
  end if;

  if not public.driver_can_accept_payment_method(v_driver,v_method) then
    update public.ride_offers
    set status='expired',responded_at=now()
    where id=p_offer_id;
    if v_method='card_machine' then
      return jsonb_build_object('ok',false,'reason','card_machine_not_authorized');
    end if;
    if v_method='cash' then
      return jsonb_build_object('ok',false,'reason','wallet_or_driver_unavailable');
    end if;
    return jsonb_build_object('ok',false,'reason','payment_method_unavailable');
  end if;

  if v_ride.driver_id is not null or v_ride.status not in ('requested','searching') then
    update public.ride_offers
    set status='expired',responded_at=now()
    where id=p_offer_id;
    return jsonb_build_object('ok',false,'reason','already_taken');
  end if;

  update public.rides
  set driver_id=v_driver,status='accepted',accepted_at=now()
  where id=v_offer.ride_id;

  update public.ride_offers
  set status='accepted',responded_at=now()
  where id=p_offer_id;

  update public.ride_offers
  set status='expired',responded_at=coalesce(responded_at,now())
  where ride_id=v_offer.ride_id and id<>p_offer_id and status='pending';

  update public.ride_dispatch_state
  set status='accepted',next_dispatch_at=null,updated_at=now()
  where ride_id=v_offer.ride_id;

  update public.drivers
  set consecutive_refusals=0
  where id=v_driver;

  insert into public.ride_events(ride_id,driver_id,event_type)
  values(v_offer.ride_id,v_driver,'offer_accepted');

  return jsonb_build_object('ok',true,'accepted',true,'ride_id',v_offer.ride_id);
end;
$$;
revoke all on function public.respond_to_ride_offer(uuid,boolean) from public,anon;
grant execute on function public.respond_to_ride_offer(uuid,boolean) to authenticated;

-- Remove notificações antigas que ainda poderiam aparecer como não lidas fora da janela ativa.
delete from public.user_notifications n
where n.ride_id is not null
  and n.read_at is null
  and not exists(
    select 1
    from public.rides r
    where r.id=n.ride_id
      and r.driver_id is not null
      and r.status::text in ('accepted','driver_arriving','in_progress')
      and (n.user_id=r.passenger_id or n.user_id=r.driver_id)
  );
