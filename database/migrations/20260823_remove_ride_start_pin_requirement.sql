CREATE OR REPLACE FUNCTION public.advance_driver_ride(p_ride_id uuid, p_action text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
  v_uid uuid:=auth.uid();v_ride public.rides%rowtype;v_next public.ride_status;v_commission numeric:=0;v_ride_fee numeric:=0;v_cancel_collection numeric:=0;v_balance numeric:=null;
  v_loc public.driver_locations%rowtype;v_tolerance integer:=300;v_wait_fee numeric:=0.50;v_wait_seconds integer:=0;v_wait_minutes integer:=0;v_wait_charge numeric:=0;v_now timestamptz:=now();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id and driver_id=v_uid for update;
  if not found then raise exception 'Corrida não encontrada para este motorista'; end if;
  select * into v_loc from public.driver_locations where driver_id=v_uid;

  if p_action='arrived' and v_ride.status='accepted' then
    v_next:='driver_arriving';
    select coalesce(rc.wait_tolerance_minutes,5)*60,coalesce(rc.waiting_fee_per_minute,0.50)
      into v_tolerance,v_wait_fee
      from public.ride_categories rc where rc.id=v_ride.category_id;
  elsif p_action='start' and v_ride.status='driver_arriving' then
    v_next:='in_progress';
    v_wait_seconds:=greatest(0,floor(extract(epoch from (v_now-coalesce(v_ride.arrived_at,v_now))))::integer-coalesce(v_ride.wait_free_seconds,300));
    v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;
    v_wait_charge:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  elsif p_action='complete' and v_ride.status='in_progress' then
    if lower(coalesce(v_ride.payment_method_preference,''))='card_machine'
       and not exists(select 1 from public.payments where ride_id=p_ride_id and method='card_machine' and status='paid') then
      raise exception 'Confirme o recebimento na maquininha antes de concluir';
    end if;
    v_next:='completed';
  else
    raise exception 'Transição de corrida inválida';
  end if;

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

  if v_loc.driver_id is not null then
    insert into public.ride_location_points(ride_id,driver_id,lat,lng,heading,speed_kmh,phase)
    values(p_ride_id,v_uid,v_loc.lat,v_loc.lng,v_loc.heading,v_loc.speed_kmh,
      case p_action when 'arrived' then 'arrived_pickup' when 'start' then 'ride_started' else 'ride_completed' end);
  end if;

  insert into public.ride_events(ride_id,driver_id,event_type)
  values(p_ride_id,v_uid,case p_action when 'arrived' then 'driver_arriving' when 'start' then 'ride_started' else 'ride_completed' end);

  if v_next='completed' then
    select coalesce(sum(amount),0) into v_commission from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_commission' and status='settled';
    select coalesce(sum(amount),0) into v_ride_fee from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_fee' and status='settled';
    select coalesce(sum(amount),0) into v_cancel_collection from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='adjustment' and status='settled' and metadata->>'kind'='passenger_cancellation_collection';
    select balance into v_balance from public.driver_operational_wallets where driver_id=v_uid;
  end if;

  return jsonb_build_object(
    'ok',true,'ride_id',p_ride_id,'status',v_next,'payment_method',v_ride.payment_method_preference,
    'wait_charge_amount',case when v_next='in_progress' then v_wait_charge else coalesce(v_ride.wait_charge_amount,0) end,
    'direct_collection_commission_debit',v_commission,'per_ride_fee_debit',v_ride_fee,
    'cancellation_collection_debit',v_cancel_collection,'operational_balance_after',v_balance
  );
end;
$function$;
